"""OAuthToken ORM model.

Deliberately its own table, not columns bolted onto `users` — token
rotation/compromise handling should never risk touching identity rows,
and this table's lifecycle (created on first login, updated on every
token refresh) is different enough from `users` (created once, rarely
updated) to warrant the separation. Owned and queried exclusively
through UserRepository (per the frozen simplified-architecture decision
to consolidate `users`/`oauth_tokens`/`user_settings` into one
repository) — there is no separate OAuthTokenRepository.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import ARRAY, DateTime, ForeignKey, LargeBinary, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base
from app.infrastructure.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class OAuthTokenModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "oauth_tokens"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # one active token set per user, per the frozen schema (v1 — single mailbox)
    )
    access_token_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    refresh_token_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    token_expiry: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    granted_scopes: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
