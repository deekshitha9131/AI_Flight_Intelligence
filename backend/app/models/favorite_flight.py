from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.database.base import Base
from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column


class FavoriteFlight(Base):
    """A flight offer saved as a favourite by an authenticated user.

    The unique constraint on (user_id, flight_offer_id) prevents the same
    offer from being saved twice by the same user.
    """

    __tablename__ = "favorite_flights"
    __table_args__ = (
        UniqueConstraint("user_id", "flight_offer_id", name="uq_favorite_user_offer"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Amadeus offer identifier — used to detect duplicates
    flight_offer_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Denormalised snapshot of the offer at save time
    airline: Mapped[str] = mapped_column(String(10), nullable=False)
    origin: Mapped[str] = mapped_column(String(3), nullable=False)
    destination: Mapped[str] = mapped_column(String(3), nullable=False)
    departure: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # ISO datetime string
    arrival: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # ISO datetime string
    price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
