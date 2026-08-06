"""Session store.

Per the frozen auth flow: "Backend issues an httpOnly session cookie
(opaque session ID, session state in Redis — not a JWT holding Gmail
scopes client-side)." This module is that Redis-backed state. The
session cookie itself carries nothing but an unguessable random ID —
all it can do on its own is look up whether a session exists; it holds
no claims, so revoking a session (logout) is a single Redis delete, not
something that has to wait out a token's expiry the way revoking a JWT
would.

A note on the `# type: ignore[type-arg]` below: see
app/infrastructure/cache/redis_client.py's module docstring for the
full explanation — `redis.Redis` cannot be subscripted at runtime with
the installed redis-py version, so every annotation using it is bare,
with mypy's resulting complaint suppressed explicitly.
"""

import secrets
import uuid

import redis.asyncio as redis

_SESSION_KEY_PREFIX = "session:"


class SessionStore:
    def __init__(
        self, *, redis_client: redis.Redis, ttl_seconds: int  # type: ignore[type-arg]
    ) -> None:
        self._redis = redis_client
        self._ttl_seconds = ttl_seconds

    async def create_session(self, user_id: uuid.UUID) -> str:
        """Create a new session for a user, returning the opaque session ID
        to set as the cookie value."""
        session_id = secrets.token_urlsafe(32)
        await self._redis.setex(
            f"{_SESSION_KEY_PREFIX}{session_id}", self._ttl_seconds, str(user_id)
        )
        return session_id

    async def get_user_id(self, session_id: str) -> uuid.UUID | None:
        """Resolve a session ID to a user ID, or None if the session doesn't
        exist or has expired."""
        raw = await self._redis.get(f"{_SESSION_KEY_PREFIX}{session_id}")
        if raw is None:
            return None
        try:
            return uuid.UUID(raw)
        except ValueError:
            # A malformed value in Redis is not a valid session, full
            # stop — treat it the same as "no session" rather than
            # raising and turning a data-integrity issue into a 500 for
            # every request carrying this cookie.
            return None

    async def delete_session(self, session_id: str) -> None:
        """Invalidate a session immediately — this is what makes logout a
        real revocation, not just a client-side cookie clear that leaves
        the session usable until it naturally expires."""
        await self._redis.delete(f"{_SESSION_KEY_PREFIX}{session_id}")
