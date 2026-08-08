from functools import lru_cache
from typing import Annotated
from app.application.services.gmail_service import GmailService
from app.infrastructure.database.repositories.email_repository import EmailRepository
from app.infrastructure.database.repositories.thread_repository import ThreadRepository
import httpx
import redis.asyncio as redis
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.application.services.email_service import EmailService
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
    
    return request.app.state.redis_client  # type: ignore[no-any-return]


def get_http_client(request: Request) -> httpx.AsyncClient:
    
    return request.app.state.http_client  # type: ignore[no-any-return]


def get_settings_dependency() -> Settings:
    
    return get_settings()


@lru_cache
def get_token_cipher() -> TokenCipher:
    
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
   
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    return await auth_service.get_current_user(session_id)


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
    
    return GmailService(
        user_repository=user_repository,
        thread_repository=thread_repository,
        email_repository=email_repository,
        settings=settings,
    )


def get_email_service(
    email_repository: Annotated[EmailRepository, Depends(get_email_repository)],
) -> EmailService:
    return EmailService(email_repository=email_repository)

# --- additional import, merged into the existing import block ---
from app.application.services.thread_service import ThreadService


# --- additional provider, added after get_email_service ---
# (get_thread_repository already exists from Task 3.3 — reused as-is)


def get_thread_service(
    thread_repository: Annotated[ThreadRepository, Depends(get_thread_repository)],
) -> ThreadService:
    return ThreadService(thread_repository=thread_repository)