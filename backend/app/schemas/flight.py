from __future__ import annotations

import re
from datetime import date, datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class TravelClass(str, Enum):
    ECONOMY = "ECONOMY"
    PREMIUM_ECONOMY = "PREMIUM_ECONOMY"
    BUSINESS = "BUSINESS"
    FIRST = "FIRST"


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------


class FlightSearchParams(BaseModel):
    """Validated query parameters for the flight search endpoint."""

    origin: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="IATA code of the departure airport (e.g. HYD, DEL).",
        examples=["HYD"],
    )
    destination: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="IATA code of the arrival airport (e.g. DXB, LHR).",
        examples=["DXB"],
    )
    departure_date: date = Field(
        ...,
        description="Departure date in YYYY-MM-DD format. Cannot be in the past.",
        examples=["2025-12-01"],
    )
    return_date: date | None = Field(
        None,
        description="Return date for round trips (YYYY-MM-DD). Must be after departure_date.",
        examples=["2025-12-10"],
    )
    adults: int = Field(
        1,
        ge=1,
        le=9,
        description="Number of adult passengers (age 12+). Minimum 1, maximum 9.",
    )
    children: int = Field(
        0,
        ge=0,
        le=9,
        description="Number of child passengers (age 2–11).",
    )
    infants: int = Field(
        0,
        ge=0,
        le=9,
        description="Number of infant passengers (under age 2). Cannot exceed adults.",
    )
    travel_class: TravelClass = Field(
        TravelClass.ECONOMY,
        description="Cabin class: ECONOMY, PREMIUM_ECONOMY, BUSINESS, or FIRST.",
    )
    currency: str = Field(
        "USD",
        min_length=3,
        max_length=3,
        description="ISO 4217 currency code for prices (e.g. USD, EUR, INR).",
        examples=["USD"],
    )
    non_stop: bool = Field(
        False,
        description="When true, only direct (non-stop) flights are returned.",
    )
    max_results: int = Field(
        10,
        ge=1,
        le=50,
        description="Maximum number of flight offers to return (1–50).",
    )

    @field_validator("origin", "destination", mode="before")
    @classmethod
    def normalise_iata(cls, value: str) -> str:
        """Uppercase and validate that the value is exactly 3 letters."""
        upper = str(value).strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", upper):
            raise ValueError("Must be a 3-letter IATA airport code (e.g. HYD, DXB).")
        return upper

    @field_validator("currency", mode="before")
    @classmethod
    def normalise_currency(cls, value: str) -> str:
        upper = str(value).strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", upper):
            raise ValueError(
                "Must be a 3-letter ISO 4217 currency code (e.g. USD, EUR)."
            )
        return upper

    @field_validator("departure_date", mode="after")
    @classmethod
    def departure_not_in_past(cls, value: date) -> date:
        if value < datetime.now(timezone.utc).date():
            raise ValueError("Departure date cannot be in the past.")
        return value

    @model_validator(mode="after")
    def cross_field_validation(self) -> FlightSearchParams:
        if self.return_date is not None and self.return_date <= self.departure_date:
            raise ValueError("Return date must be after departure date.")
        if self.origin == self.destination:
            raise ValueError("Origin and destination airports must be different.")
        total_passengers = self.adults + self.children + self.infants
        if total_passengers > 9:
            raise ValueError("Total number of passengers cannot exceed 9.")
        if self.infants > self.adults:
            raise ValueError("Number of infants cannot exceed number of adults.")
        return self


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------


class FlightSegment(BaseModel):
    """A single flight leg within an itinerary."""

    flight_number: str = Field(
        ..., description="Airline code + flight number (e.g. EK512)."
    )
    airline: str = Field(..., description="IATA airline code (e.g. EK, AI).")
    airline_name: str | None = Field(
        None, description="Full airline name, if available."
    )
    origin: str = Field(..., description="Departure IATA airport code.")
    destination: str = Field(..., description="Arrival IATA airport code.")
    departure_time: datetime = Field(..., description="Scheduled departure (UTC).")
    arrival_time: datetime = Field(..., description="Scheduled arrival (UTC).")
    duration: str = Field(
        ..., description="Segment duration in ISO 8601 format (e.g. PT2H30M)."
    )
    aircraft: str | None = Field(None, description="Aircraft type code, if available.")


class FlightResult(BaseModel):
    """A single flight offer returned by the search endpoint."""

    flight_id: str = Field(..., description="Unique offer identifier from Amadeus.")
    origin: str = Field(..., description="Departure IATA airport code.")
    destination: str = Field(..., description="Arrival IATA airport code.")
    departure_time: datetime = Field(
        ..., description="First segment departure time (UTC)."
    )
    arrival_time: datetime = Field(..., description="Last segment arrival time (UTC).")
    duration: str = Field(..., description="Total journey duration in ISO 8601 format.")
    stops: int = Field(..., description="Number of stops (0 = non-stop).")
    segments: list[FlightSegment] = Field(..., description="Individual flight legs.")
    travel_class: str = Field(..., description="Cabin class for this offer.")
    price: float = Field(..., description="Total price for all passengers.")
    currency: str = Field(..., description="ISO 4217 currency code.")
    price_per_adult: float = Field(..., description="Price per adult passenger.")
    available_seats: int | None = Field(
        None, description="Remaining bookable seats, if disclosed."
    )
    booking_link: str | None = Field(
        None, description="Deep-link to booking page, if available."
    )
    is_round_trip: bool = Field(
        ..., description="True when the offer includes a return itinerary."
    )


class FlightSearchResponse(BaseModel):
    """Standard envelope returned by GET /api/v1/flights/search."""

    success: bool
    message: str
    data: list[FlightResult]
    count: int = Field(..., description="Number of flight offers returned.")
    search_id: str = Field(
        ..., description="Persisted search record identifier (UUID)."
    )
