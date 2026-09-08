import secrets
import uuid

import redis.asyncio as redis

_SESSION_KEY_PREFIX = "session:"


class SessionStore:
    def __init__(self, *, redis_client: redis.Redis, ttl_seconds: int) -> None:
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
        val = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
        try:
            return uuid.UUID(val)
        except ValueError:
            return None

    async def delete_session(self, session_id: str) -> None:
        await self._redis.delete(f"{_SESSION_KEY_PREFIX}{session_id}")
