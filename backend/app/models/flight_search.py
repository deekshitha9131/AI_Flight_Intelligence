from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class FlightSearch(Base):
    """Persisted record of a user's flight search parameters and timestamp.

    Only the search intent is stored — never individual flight results,
    prices, or seat availability, which are volatile and owned by Amadeus.
    """

    __tablename__ = "flight_searches"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Route
    origin: Mapped[str] = mapped_column(String(3), nullable=False)
    destination: Mapped[str] = mapped_column(String(3), nullable=False)
    departure_date: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # ISO date YYYY-MM-DD
    return_date: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Passengers
    adults: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    children: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    infants: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Preferences
    travel_class: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ECONOMY"
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    non_stop: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    max_results: Mapped[int] = mapped_column(Integer, nullable=False, default=10)

    # Metadata
    result_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    searched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
