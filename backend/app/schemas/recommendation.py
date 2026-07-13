from __future__ import annotations

from pydantic import BaseModel, Field


class RecommendedFlight(BaseModel):
    """A single recommended flight offer."""

    origin: str = Field(..., description="Departure IATA code.")
    destination: str = Field(..., description="Arrival IATA code.")
    airline: str = Field(..., description="IATA airline code.")
    cabin_class: str = Field(..., description="Recommended cabin class.")
    estimated_price: float = Field(
        ..., description="Estimated price based on ML prediction."
    )
    currency: str = Field(..., description="Currency of the estimated price.")
    reason: str = Field(..., description="Why this flight was recommended.")
    score: float = Field(..., description="Recommendation relevance score (0–1).")


class RecommendedDestination(BaseModel):
    """A single recommended destination."""

    iata_code: str = Field(..., description="IATA airport code.")
    city: str = Field(..., description="City name.")
    country: str = Field(..., description="Country name.")
    estimated_price: float = Field(..., description="Estimated round-trip price.")
    currency: str
    reason: str = Field(..., description="Why this destination was recommended.")
    score: float = Field(..., description="Relevance score (0–1).")
    best_travel_month: str | None = Field(None, description="Best month to visit.")


class RecommendedAirline(BaseModel):
    """A single recommended airline."""

    iata_code: str = Field(..., description="IATA airline code.")
    name: str = Field(..., description="Airline name.")
    reason: str = Field(..., description="Why this airline was recommended.")
    avg_price: float = Field(
        ..., description="Average price for this airline on preferred routes."
    )
    currency: str
    score: float = Field(..., description="Relevance score (0–1).")


class RecommendedDeal(BaseModel):
    """A time-sensitive deal recommendation."""

    origin: str
    destination: str
    airline: str
    cabin_class: str
    estimated_price: float
    currency: str
    discount_pct: float = Field(
        ..., description="Estimated discount vs. average price (%)."
    )
    valid_until: str | None = Field(None, description="Deal expiry hint (ISO date).")
    reason: str
    score: float


class FlightRecommendationsResponse(BaseModel):
    """Response for GET /api/v1/recommendations."""

    success: bool
    message: str
    data: list[RecommendedFlight]
    count: int


class DestinationRecommendationsResponse(BaseModel):
    """Response for GET /api/v1/recommendations/destinations."""

    success: bool
    message: str
    data: list[RecommendedDestination]
    count: int


class AirlineRecommendationsResponse(BaseModel):
    """Response for GET /api/v1/recommendations/airlines."""

    success: bool
    message: str
    data: list[RecommendedAirline]
    count: int


class DealsRecommendationsResponse(BaseModel):
    """Response for GET /api/v1/recommendations/deals."""

    success: bool
    message: str
    data: list[RecommendedDeal]
    count: int
