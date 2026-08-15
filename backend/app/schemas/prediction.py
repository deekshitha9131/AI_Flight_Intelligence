from __future__ import annotations

import re
from datetime import date, datetime, time, timezone
from enum import Enum
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from pydantic import BaseModel, Field, field_validator, model_validator


class TripType(str, Enum):
    ONE_WAY = "ONE_WAY"
    ROUND_TRIP = "ROUND_TRIP"


class PredictPriceRequest(BaseModel):
    """Input features for the ML price prediction endpoint."""

    origin: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Departure IATA code.",
        examples=["HYD"],
    )
    destination: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Arrival IATA code.",
        examples=["DXB"],
    )
    departure_date: date = Field(
        ..., description="Departure date (YYYY-MM-DD).", examples=["2025-12-01"]
    )
    return_date: date | None = Field(
        None, description="Return date for round trips.", examples=["2025-12-10"]
    )
    airline: str | None = Field(
        None, max_length=10, description="Preferred IATA airline code.", examples=["EK"]
    )
    cabin_class: str = Field(
        "ECONOMY", description="Cabin class.", examples=["ECONOMY"]
    )
    adults: int = Field(1, ge=1, le=9, description="Adult passengers.")
    children: int = Field(0, ge=0, le=9, description="Child passengers.")
    infants: int = Field(0, ge=0, le=9, description="Infant passengers.")
    stops: int | None = Field(None, ge=0, le=5, description="Maximum number of stops.")
    duration_minutes: int | None = Field(
        None, ge=1, le=3000, description="Total journey duration in minutes."
    )
    departure_time: time | None = Field(
        None, description="Scheduled departure local time."
    )
    arrival_time: time | None = Field(None, description="Scheduled arrival local time.")
    trip_type: TripType = Field(TripType.ONE_WAY, description="ONE_WAY or ROUND_TRIP.")
    currency: str = Field(
        "USD", min_length=3, max_length=3, description="ISO 4217 currency code."
    )

    @field_validator("origin", "destination", mode="before")
    @classmethod
    def normalise_iata(cls, value: str) -> str:
        upper = str(value).strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", upper):
            raise ValueError("Must be a 3-letter IATA airport code.")
        return upper

    @field_validator("currency", mode="before")
    @classmethod
    def normalise_currency(cls, value: str) -> str:
        upper = str(value).strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", upper):
            raise ValueError("Must be a 3-letter ISO 4217 currency code.")
        return upper

    @field_validator("departure_date", mode="after")
    @classmethod
    def departure_not_in_past(cls, value: date) -> date:
        if value < datetime.now(timezone.utc).date():
            raise ValueError("Departure date cannot be in the past.")
        return value

    @model_validator(mode="after")
    def cross_field_checks(self) -> PredictPriceRequest:
        if self.origin == self.destination:
            raise ValueError("Origin and destination must be different.")
        if self.return_date is not None and self.return_date <= self.departure_date:
            raise ValueError("Return date must be after departure date.")
        if self.trip_type == TripType.ROUND_TRIP and self.return_date is None:
            raise ValueError("return_date is required for ROUND_TRIP.")
        return self


class PredictPriceResponse(BaseModel):
    """Response envelope for POST /api/v1/ai/predict-price."""

    success: bool
    message: str
    data: PredictionResult


class PredictionResult(BaseModel):
    """Detailed prediction output returned to the caller."""
    model_config = ConfigDict(protected_namespaces=())
    prediction_id: UUID = Field(..., description="Unique ID of this prediction record.")
    predicted_price: float = Field(..., description="ML-predicted total price.")
    currency: str = Field(..., description="Currency of the predicted price.")
    confidence_score: float | None = Field(
        None, description="Model confidence (0–1), if available."
    )
    price_range_low: float = Field(
        ..., description="Lower bound of the predicted price range."
    )
    price_range_high: float = Field(
        ..., description="Upper bound of the predicted price range."
    )
    estimated_savings: float | None = Field(
        None, description="Estimated savings vs. average market price."
    )
    suggested_booking_window: str | None = Field(
        None, description="Recommended days-before-departure to book."
    )
    model_version: str = Field(..., description="Version of the ML model used.")
    processing_time_ms: float = Field(
        ..., description="Server-side processing time in milliseconds."
    )
    predicted_at: datetime = Field(..., description="UTC timestamp of the prediction.")


# Rebuild forward reference
PredictPriceResponse.model_rebuild()
