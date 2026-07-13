from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.refresh_token import RefreshToken


def hash_refresh_token(token: str) -> str:
    """Return the SHA-256 hex digest of a raw refresh token."""
    return hashlib.sha256(token.encode()).hexdigest()


def verify_refresh_token(token: str, token_hash: str) -> bool:
    """Return True if the raw token matches the stored hash."""
    return hashlib.sha256(token.encode()).hexdigest() == token_hash


class RefreshTokenRepository:
    """Repository layer for refresh token persistence operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        device_name: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> RefreshToken:
        """Persist a new hashed refresh token record."""
        record = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            device_name=device_name,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.session.add(record)
        self.session.flush()
        return record

    def get_by_hash(self, *, token_hash: str) -> RefreshToken | None:
        """Return a refresh token record by its hash, if present."""
        statement = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        return self.session.scalar(statement)

    def revoke(self, *, record: RefreshToken) -> RefreshToken:
        """Mark a refresh token as revoked."""
        record.revoked_at = datetime.now(timezone.utc)
        self.session.add(record)
        self.session.flush()
        return record
