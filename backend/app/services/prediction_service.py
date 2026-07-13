from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from uuid import UUID

from app.ai.model_loader import ModelLoader
from app.exceptions.base import ValidationException
from app.repositories.prediction_repository import PredictionRepository
from app.schemas.prediction import PredictionResult, PredictPriceRequest

logger = logging.getLogger(__name__)

# Cabin class → ordinal encoding (must match training pipeline)
_CABIN_ENCODING = {"ECONOMY": 0, "PREMIUM_ECONOMY": 1, "BUSINESS": 2, "FIRST": 3}

# Booking window advice thresholds (days before departure)
_BOOKING_WINDOWS = [
    (90, "Book now — prices are likely to rise significantly closer to departure."),
    (60, "Good time to book — prices are stable but may increase in 2–4 weeks."),
    (30, "Book soon — prices typically rise sharply within 30 days of departure."),
    (14, "Book immediately — last-minute prices are usually 30–50% higher."),
    (0, "Very last minute — expect premium pricing. Book now if you must travel."),
]

# Variance factor for price range (±15 % of predicted price)
_RANGE_FACTOR = 0.15


class PredictionService:
    """Business logic for ML-powered flight price prediction.

    Responsibilities
    ----------------
    - Build the feature dict from the validated request.
    - Call ModelLoader.predict() and measure latency.
    - Derive price range, estimated savings, and booking window advice.
    - Persist the prediction to PredictionHistory.
    - Map errors to AppException subclasses.
    """

    def __init__(
        self,
        repository: PredictionRepository,
        model_loader: ModelLoader,
    ) -> None:
        self._repository = repository
        self._model_loader = model_loader

    def predict(
        self,
        *,
        request: PredictPriceRequest,
        user_id: UUID,
    ) -> PredictionResult:
        """Run price prediction and persist the result.

        Args:
            request:  Validated prediction request.
            user_id:  Authenticated user UUID.

        Returns:
            PredictionResult with price, range, confidence, and metadata.

        Raises:
            ValidationException: Feature engineering produced invalid inputs.
        """
        logger.info(
            "PredictionService.predict | user=%s %s→%s %s",
            user_id,
            request.origin,
            request.destination,
            request.departure_date,
        )

        features = self._build_features(request)
        start = time.monotonic()
        predicted_price, confidence = self._model_loader.predict(features)
        processing_ms = (time.monotonic() - start) * 1000

        if predicted_price <= 0:
            raise ValidationException(
                message="Prediction produced an invalid price. Please check your inputs."
            )

        price_range_low = round(predicted_price * (1 - _RANGE_FACTOR), 2)
        price_range_high = round(predicted_price * (1 + _RANGE_FACTOR), 2)

        days_until = features.get("days_until_departure", 30)
        booking_window = _suggest_booking_window(days_until)
        estimated_savings = _estimate_savings(predicted_price, days_until)

        record = self._repository.create(
            user_id=user_id,
            origin=request.origin,
            destination=request.destination,
            departure_date=request.departure_date.isoformat(),
            return_date=(
                request.return_date.isoformat() if request.return_date else None
            ),
            airline=request.airline,
            cabin_class=request.cabin_class,
            adults=request.adults,
            children=request.children,
            infants=request.infants,
            stops=request.stops,
            trip_type=request.trip_type.value,
            currency=request.currency,
            predicted_price=predicted_price,
            price_range_low=price_range_low,
            price_range_high=price_range_high,
            confidence_score=confidence,
            estimated_savings=estimated_savings,
            suggested_booking_window=booking_window,
            model_version=self._model_loader.model_version,
            processing_time_ms=processing_ms,
        )

        logger.info(
            "PredictionService.predict | id=%s price=%.2f confidence=%s ms=%.1f",
            record.id,
            predicted_price,
            confidence,
            processing_ms,
        )

        return PredictionResult(
            prediction_id=record.id,
            predicted_price=round(predicted_price, 2),
            currency=request.currency,
            confidence_score=round(confidence, 4) if confidence is not None else None,
            price_range_low=price_range_low,
            price_range_high=price_range_high,
            estimated_savings=estimated_savings,
            suggested_booking_window=booking_window,
            model_version=self._model_loader.model_version,
            processing_time_ms=round(processing_ms, 2),
            predicted_at=record.predicted_at,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_features(request: PredictPriceRequest) -> dict[str, object]:
        """Convert the request into a feature dict for the model."""
        today = datetime.now(timezone.utc).date()
        days_until = (request.departure_date - today).days

        is_round_trip = 1 if request.return_date is not None else 0

        # Simple ordinal encoding — replace with label encoder from pipeline
        # when a trained model is available.
        origin_enc = abs(hash(request.origin)) % 500
        dest_enc = abs(hash(request.destination)) % 500
        airline_enc = abs(hash(request.airline or "")) % 200

        cabin_enc = _CABIN_ENCODING.get(request.cabin_class.upper(), 0)
        departure_hour = request.departure_time.hour if request.departure_time else 8
        arrival_hour = request.arrival_time.hour if request.arrival_time else 10

        return {
            "origin": request.origin,
            "destination": request.destination,
            "origin_encoded": origin_enc,
            "destination_encoded": dest_enc,
            "days_until_departure": max(0, days_until),
            "is_round_trip": is_round_trip,
            "adults": request.adults,
            "children": request.children,
            "infants": request.infants,
            "cabin_class": request.cabin_class,
            "cabin_class_encoded": cabin_enc,
            "stops": request.stops or 0,
            "flight_duration_minutes": request.duration_minutes or 180,
            "departure_hour": departure_hour,
            "arrival_hour": arrival_hour,
            "departure_month": request.departure_date.month,
            "departure_day_of_week": request.departure_date.weekday(),
            "airline_encoded": airline_enc,
        }


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _suggest_booking_window(days_until: int) -> str:
    """Return a human-readable booking window recommendation."""
    for threshold, advice in _BOOKING_WINDOWS:
        if days_until >= threshold:
            return advice
    return _BOOKING_WINDOWS[-1][1]


def _estimate_savings(predicted_price: float, days_until: int) -> float | None:
    """Estimate potential savings if the user books now vs. waiting."""
    if days_until <= 0:
        return None
    # Prices typically rise ~2% per week in the last 8 weeks
    weeks_remaining = min(days_until / 7, 8)
    savings_pct = weeks_remaining * 0.02
    return round(predicted_price * savings_pct, 2)
