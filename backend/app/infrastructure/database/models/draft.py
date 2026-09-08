from datetime import datetime
from uuid import UUID

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums.draft_status import DraftStatus
from app.infrastructure.database.base import Base
from app.infrastructure.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DraftModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "drafts"

    email_id: Mapped[UUID] = mapped_column(
        ForeignKey("emails.id", ondelete="CASCADE"), nullable=False, index=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[DraftStatus] = mapped_column(
        SQLEnum(
            DraftStatus,
            name="draft_status",
            native_enum=True,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        default=DraftStatus.GENERATED,
        server_default=DraftStatus.GENERATED.value,
    )