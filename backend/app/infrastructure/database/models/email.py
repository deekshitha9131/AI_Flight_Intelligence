from datetime import datetime
from uuid import UUID

from sqlalchemy import ARRAY, Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base
from app.infrastructure.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.infrastructure.database.models.attachment import AttachmentModel


class EmailModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "emails"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "gmail_message_id", name="uq_emails_user_id_gmail_message_id"
        ),
    )

    thread_id: Mapped[UUID] = mapped_column(
        ForeignKey("threads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    gmail_message_id: Mapped[str] = mapped_column(String(64), nullable=False)
    sender: Mapped[str] = mapped_column(String(255), nullable=False)
    recipients: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    cc: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    bcc: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    snippet: Mapped[str] = mapped_column(Text, nullable=False)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_starred: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_attachments: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    label_ids: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)

    attachments: Mapped[list[AttachmentModel]] = relationship(
        back_populates="email",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    