from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.database.base import Base
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class RecommendationLog(Base):
    """Log of a recommendation batch served to a user.

    Each row represents one recommendation event (e.g. a call to
    GET /api/v1/recommendations) and stores the recommendation type,
    the serialised payload, and the reasoning used to generate it.
    """

    __tablename__ = "recommendation_logs"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # "flights" | "destinations" | "airlines" | "deals"
    recommendation_type: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True
    )

    # JSON-serialised list of recommended items
    payload: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    # Human-readable explanation of why these were recommended
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    user: Mapped["User"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User",
        foreign_keys=[user_id],
        lazy="raise",
    )
