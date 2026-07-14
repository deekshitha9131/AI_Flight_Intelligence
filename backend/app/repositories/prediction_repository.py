from __future__ import annotations

import logging
from uuid import UUID

from app.models.prediction_history import PredictionHistory
from sqlalchemy import func, select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class PredictionRepository:
    """Repository layer for ML prediction history persistence."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(
        self,
        *,
        user_id: UUID,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str | None,
        airline: str | None,
        cabin_class: str,
        adults: int,
        children: int,
        infants: int,
        stops: int | None,
        trip_type: str,
        currency: str,
        predicted_price: float,
        price_range_low: float,
        price_range_high: float,
        confidence_score: float | None,
        estimated_savings: float | None,
        suggested_booking_window: str | None,
        model_version: str,
        processing_time_ms: float | None,
    ) -> PredictionHistory:
        """Persist a new prediction record and return it."""
        record = PredictionHistory(
            user_id=user_id,
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            airline=airline,
            cabin_class=cabin_class,
            adults=adults,
            children=children,
            infants=infants,
            stops=stops,
            trip_type=trip_type,
            currency=currency,
            predicted_price=predicted_price,
            price_range_low=price_range_low,
            price_range_high=price_range_high,
            confidence_score=confidence_score,
            estimated_savings=estimated_savings,
            suggested_booking_window=suggested_booking_window,
            model_version=model_version,
            processing_time_ms=processing_time_ms,
        )
        self._db.add(record)
        self._db.flush()
        logger.info(
            "PredictionRepository.create | user=%s id=%s price=%.2f",
            user_id,
            record.id,
            predicted_price,
        )
        return record

    def get_by_id(self, *, record_id: UUID, user_id: UUID) -> PredictionHistory | None:
        """Return a single prediction owned by the user, or None."""
        return self._db.scalar(
            select(PredictionHistory).where(
                PredictionHistory.id == record_id,
                PredictionHistory.user_id == user_id,
            )
        )

    def get_paginated_by_user(
        self,
        *,
        user_id: UUID,
        offset: int,
        limit: int,
    ) -> tuple[list[PredictionHistory], int]:
        """Return a page of predictions for a user, newest-first."""
        base_filter = PredictionHistory.user_id == user_id

        total: int = (
            self._db.scalar(
                select(func.count()).select_from(PredictionHistory).where(base_filter)
            )
            or 0
        )

        records = list(
            self._db.scalars(
                select(PredictionHistory)
                .where(base_filter)
                .order_by(PredictionHistory.predicted_at.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        return records, total

    def get_recent_by_route(
        self,
        *,
        origin: str,
        destination: str,
        limit: int = 30,
    ) -> list[PredictionHistory]:
        """Return recent predictions for a route (all users), newest-first."""
        return list(
            self._db.scalars(
                select(PredictionHistory)
                .where(
                    PredictionHistory.origin == origin,
                    PredictionHistory.destination == destination,
                )
                .order_by(PredictionHistory.predicted_at.desc())
                .limit(limit)
            )
        )
