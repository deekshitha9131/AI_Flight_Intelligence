from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import get_settings
from jose import JWTError, jwt

settings = get_settings()


def create_access_token(
    *, user_id: str, email: str, role: str, expires_delta: int | None = None
) -> str:
    """Create a signed JWT access token for an authenticated user."""
    expire_minutes = expires_delta or settings.access_token_expire_minutes
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=expire_minutes)
    payload: dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "role": role,
        "jti": secrets.token_hex(8),
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(*, user_id: str) -> tuple[str, datetime]:
    """Create a signed JWT refresh token and return it with its expiry datetime."""
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=settings.refresh_token_expire_days)
    payload: dict[str, Any] = {
        "sub": user_id,
        "jti": secrets.token_hex(16),
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token, expires


def decode_access_token(*, token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token."""
    try:
        return jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
    except JWTError as exc:
        raise ValueError("Invalid token") from exc


def decode_refresh_token(*, token: str) -> dict[str, Any]:
    """Decode and validate a JWT refresh token."""
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
    except JWTError as exc:
        raise ValueError("Invalid refresh token") from exc
    if payload.get("type") != "refresh":
        raise ValueError("Invalid refresh token")
    return payload
