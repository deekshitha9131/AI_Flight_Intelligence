"""Dependency injection providers.

FastAPI's `Depends()` mechanism *is* this project's DI container — there
is no separate custom container class, because FastAPI's own dependency
resolution already gives us construction, request-scoping, and override-
for-testing for free. What this module provides is centralization: every
provider a router might need is importable from here, resolved from
`request.app.state` (populated once at startup — see app/main.py) or
from a dedicated infrastructure module. No router or service ever
constructs an engine, session, Redis client, or service directly; they
only ever declare `db: DbSession`, `current_user: CurrentUser`, etc.

As application/domain/infrastructure layers are built out in later
phases, their provider functions follow the same pattern established
here for auth: a thin function resolving collaborators via `Depends()`,
composed into the next layer up.
"""

from functools import lru_cache
from typing import Annotated
from app.application.services.gmail_service import GmailService
from app.infrastructure.database.repositories.email_repository import EmailRepository
from app.infrastructure.database.repositories.thread_repository import ThreadRepository
import httpx
import redis.asyncio as redis
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.auth_service import AuthService
from app.core.config import Settings, get_settings
from app.core.constants import SESSION_COOKIE_NAME
from app.core.security import TokenCipher
from app.domain.entities.user import User
from app.infrastructure.cache.session_store import SessionStore
from app.infrastructure.database.repositories.user_repository import UserRepository
from app.infrastructure.database.session import get_db_session
from app.infrastructure.gmail.oauth_client import GoogleOAuthClient


def get_redis(request: Request) -> redis.Redis:  # type: ignore[type-arg]
    """Return the process-wide Redis client.

    Unlike the DB session, a single Redis client instance is safe to
    share across concurrent requests — the redis-py async client
    manages its own connection pool internally.

    The `# type: ignore[type-arg]` on the return type is required, not
    optional — see app/infrastructure/cache/redis_client.py's module
    docstring for the full explanation. Short version: `redis.Redis` is
    not actually subscriptable at runtime in the installed redis-py
    version, and FastAPI's dependency resolution evaluates this
    function's annotations directly (`inspect.signature(fn,
    eval_str=True)`), so even a string-quoted `"redis.Redis[str]"`
    annotation crashes the app at startup the first time this function
    is registered as a dependency — this is not a style preference,
    it was a real, reproduced crash.
    """
    return request.app.state.redis_client  # type: ignore[no-any-return]


def get_http_client(request: Request) -> httpx.AsyncClient:
    """Return the process-wide httpx client (see app/main.py's lifespan),
    used for outbound calls to external services — currently just
    Google's OAuth endpoints."""
    return request.app.state.http_client  # type: ignore[no-any-return]


def get_settings_dependency() -> Settings:
    """FastAPI-dependency wrapper around the cached settings singleton.

    Exists as a thin wrapper (rather than routers calling
    `get_settings()` directly) so settings can be overridden in tests
    via FastAPI's `app.dependency_overrides`, the same way every other
    dependency in this module can be.
    """
    return get_settings()


@lru_cache
def get_token_cipher() -> TokenCipher:
    """Return the process-wide TokenCipher.

    Cached like `get_settings()` — a TokenCipher is stateless once
    built from a key, so there's nothing to gain from reconstructing it
    (and re-deriving the Fernet key) on every request.
    """
    return TokenCipher(get_settings())


def get_user_repository(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    token_cipher: Annotated[TokenCipher, Depends(get_token_cipher)],
) -> UserRepository:
    return UserRepository(db, token_cipher)


def get_oauth_client(
    settings: Annotated[Settings, Depends(get_settings_dependency)],
    http_client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
) -> GoogleOAuthClient:
    return GoogleOAuthClient(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        redirect_uri=settings.google_redirect_uri,
        http_client=http_client,
    )


def get_session_store(
    redis_client: Annotated[redis.Redis, Depends(get_redis)],  # type: ignore[type-arg]
    settings: Annotated[Settings, Depends(get_settings_dependency)],
) -> SessionStore:
    return SessionStore(redis_client=redis_client, ttl_seconds=settings.session_ttl_seconds)


def get_auth_service(
    oauth_client: Annotated[GoogleOAuthClient, Depends(get_oauth_client)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    session_store: Annotated[SessionStore, Depends(get_session_store)],
) -> AuthService:
    return AuthService(
        oauth_client=oauth_client,
        user_repository=user_repository,
        session_store=session_store,
    )


async def get_current_user(
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    """Resolve the caller's session cookie to a User, or raise
    SessionNotFoundError (401) — the dependency any future protected
    route declares as `current_user: CurrentUser`.
    """
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    return await auth_service.get_current_user(session_id)


# Reusable typed aliases — routers annotate parameters as
# `db: DbSession` instead of repeating
# `Annotated[AsyncSession, Depends(get_db_session)]` at every call site.
# `get_db_session` itself lives in app/infrastructure/database/session.py,
# next to the sessionmaker it wraps — imported and re-exported here so
# every other dependency provider is still discoverable from one place.
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
RedisClient = Annotated[redis.Redis, Depends(get_redis)]
AppSettings = Annotated[Settings, Depends(get_settings_dependency)]
CurrentUser = Annotated[User, Depends(get_current_user)]

def get_thread_repository(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ThreadRepository:
    return ThreadRepository(db)


def get_email_repository(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> EmailRepository:
    return EmailRepository(db)


def get_gmail_service(
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    thread_repository: Annotated[ThreadRepository, Depends(get_thread_repository)],
    email_repository: Annotated[EmailRepository, Depends(get_email_repository)],
    settings: Annotated[Settings, Depends(get_settings_dependency)],
) -> GmailService:
    # GmailClient itself is intentionally NOT a DI-provided dependency
    # (unlike GoogleOAuthClient) — it needs a specific user's OAuth
    # tokens, which GmailService only knows once it's handed a User at
    # call time, not at request-dependency-resolution time. GmailService
    # builds it internally (see sync_mailbox) for exactly this reason.
    return GmailService(
        user_repository=user_repository,
        thread_repository=thread_repository,
        email_repository=email_repository,
        settings=settings,
    )
