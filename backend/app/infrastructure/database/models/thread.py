"""Thread ORM model.

Simplified Phase 3 schema: `user_id` lives directly on `threads` (no
`mailboxes` table yet — see the migration's module docstring). Mapped
to/from the domain entity (app/domain/entities/thread.py) exclusively
by ThreadRepository, per this project's Clean Architecture rule.
"""

from uuid import UUID

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base
from app.infrastructure.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ThreadModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "threads"
    __table_args__ = (
        UniqueConstraint("user_id", "gmail_thread_id", name="uq_threads_user_id_gmail_thread_id"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    gmail_thread_id: Mapped[str] = mapped_column(String(64), nullable=False)
    subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    history_id: Mapped[str | None] = mapped_column(String(64), nullable=True)