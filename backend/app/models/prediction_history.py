from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class PredictionHistory(Base):
    """Persisted record of a single ML price prediction request.

    Stores the input features, predicted price, confidence interval, and
    model metadata so predictions can be audited and analysed over time.
    """

    __tablename__ = "prediction_history"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Input features
    origin: Mapped[str] = mapped_column(String(3), nullable=False)
    destination: Mapped[str] = mapped_column(String(3), nullable=False)
    departure_date: Mapped[str] = mapped_column(String(10), nullable=False)
    return_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    airline: Mapped[str | None] = mapped_column(String(10), nullable=True)
    cabin_class: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ECONOMY"
    )
    adults: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    children: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    infants: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stops: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trip_type: Mapped[str] = mapped_column(
        String(10), nullable=False, default="ONE_WAY"
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    # Prediction outputs
    predicted_price: Mapped[float] = mapped_column(Float, nullable=False)
    price_range_low: Mapped[float] = mapped_column(Float, nullable=False)
    price_range_high: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_savings: Mapped[float | None] = mapped_column(Float, nullable=True)
    suggested_booking_window: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    model_version: Mapped[str] = mapped_column(
        String(50), nullable=False, default="1.0.0"
    )
    processing_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    predicted_at: Mapped[datetime] = mapped_column(
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
