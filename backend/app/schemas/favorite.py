from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SaveFavoriteRequest(BaseModel):
    """Request body for saving a flight offer as a favourite."""

    flight_offer_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Amadeus flight offer identifier.",
        examples=["1"],
    )
    airline: str = Field(
        ...,
        min_length=2,
        max_length=10,
        description="IATA airline code (e.g. EK, AI).",
        examples=["EK"],
    )
    origin: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Departure IATA airport code.",
        examples=["HYD"],
    )
    destination: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Arrival IATA airport code.",
        examples=["DXB"],
    )
    departure: str = Field(
        ...,
        description="Departure datetime as ISO 8601 string.",
        examples=["2025-12-01T10:30:00"],
    )
    arrival: str = Field(
        ...,
        description="Arrival datetime as ISO 8601 string.",
        examples=["2025-12-01T12:45:00"],
    )
    price: float = Field(
        ...,
        gt=0,
        description="Total price for all passengers.",
        examples=[299.99],
    )
    currency: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="ISO 4217 currency code.",
        examples=["USD"],
    )


class FavoriteFlightItem(BaseModel):
    """A single favourite flight record returned by the API."""

    id: UUID = Field(..., description="Unique identifier of the favourite record.")
    flight_offer_id: str = Field(..., description="Amadeus offer identifier.")
    airline: str = Field(..., description="IATA airline code.")
    origin: str = Field(..., description="Departure IATA airport code.")
    destination: str = Field(..., description="Arrival IATA airport code.")
    departure: str = Field(..., description="Departure datetime (ISO 8601).")
    arrival: str = Field(..., description="Arrival datetime (ISO 8601).")
    price: float = Field(..., description="Total price.")
    currency: str = Field(..., description="Currency code.")
    created_at: datetime = Field(
        ..., description="UTC timestamp when the favourite was saved."
    )

    model_config = {"from_attributes": True}


class FavoriteListResponse(BaseModel):
    """Paginated list of favourite flights."""

    success: bool
    message: str
    data: list[FavoriteFlightItem]
    count: int = Field(..., description="Total number of favourites returned.")


class FavoriteDetailResponse(BaseModel):
    """Single favourite flight response."""

    success: bool
    message: str
    data: FavoriteFlightItem


class FavoriteDeleteResponse(BaseModel):
    """Response returned after a successful delete operation."""

    success: bool
    message: str
