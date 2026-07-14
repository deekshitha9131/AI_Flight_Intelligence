from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.database.base import Base
from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class UserPreferenceProfile(Base):
    """Learned preference profile for a user, derived from search history.

    One row per user.  Updated incrementally after every flight search so
    the recommendation engine always has fresh signal.
    """

    __tablename__ = "user_preference_profiles"
    __table_args__ = (UniqueConstraint("user_id", name="uq_preference_user"),)

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Aggregated preference signals (JSON-serialised lists / scalars)
    preferred_airlines: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    favorite_destinations: Mapped[str] = mapped_column(
        Text, nullable=False, default="[]"
    )
    frequent_origins: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    # Budget signals
    avg_budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_budget: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Cabin preference — most-used class
    preferred_cabin: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ECONOMY"
    )

    # Travel frequency — total searches recorded
    total_searches: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Preferred departure time bucket: "morning" | "afternoon" | "evening" | "night"
    preferred_departure_time: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )

    # Preferred travel months (JSON list of month numbers 1-12)
    preferred_months: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    # Preferred currency
    preferred_currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="USD"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User",
        foreign_keys=[user_id],
        lazy="raise",
    )
