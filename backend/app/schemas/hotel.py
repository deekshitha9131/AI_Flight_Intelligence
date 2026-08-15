from __future__ import annotations

from datetime import date, datetime, timezone
from pydantic import BaseModel, Field, field_validator, model_validator


class HotelSearchParams(BaseModel):
    """Validated query parameters for searching hotels."""

    destination: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="City name or IATA code for the hotel location (e.g. HYD, DXB, London).",
        examples=["DXB"],
    )
    check_in_date: date | None = Field(
        None,
        description="Check-in date (YYYY-MM-DD).",
        examples=["2025-12-01"],
    )
    check_out_date: date | None = Field(
        None,
        description="Check-out date (YYYY-MM-DD).",
        examples=["2025-12-05"],
    )
    guests: int = Field(
        1,
        ge=1,
        le=10,
        description="Number of guests.",
    )
    rooms: int = Field(
        1,
        ge=1,
        le=5,
        description="Number of rooms.",
    )
    currency: str = Field(
        "USD",
        min_length=3,
        max_length=3,
        description="Currency code for hotel pricing.",
    )
    max_results: int = Field(
        10,
        ge=1,
        le=50,
        description="Maximum number of hotel results to return.",
    )

    @field_validator("destination", mode="before")
    @classmethod
    def normalise_destination(cls, value: str) -> str:
        return str(value).strip().upper()

    @model_validator(mode="after")
    def validate_dates(self) -> HotelSearchParams:
        if self.check_in_date and self.check_out_date:
            if self.check_out_date <= self.check_in_date:
                raise ValueError("Check-out date must be after check-in date.")
        return self


class RoomInfo(BaseModel):
    """Room details for a hotel offer."""

    room_type: str = Field(..., description="Type of room (e.g. Deluxe Suite, Standard King).")
    bed_type: str = Field(..., description="Bed configuration (e.g. 1 King Bed, 2 Twin Beds).")
    max_occupancy: int = Field(..., description="Maximum guest capacity.")


class HotelResult(BaseModel):
    """A single hotel result model."""

    hotel_id: str = Field(..., description="Unique identifier for the hotel.")
    name: str = Field(..., description="Hotel name.")
    city: str = Field(..., description="City or location name.")
    location: str = Field(..., description="Full address or location string.")
    rating: float = Field(..., description="Star rating or review score (1.0 - 5.0).")
    price_per_night: float = Field(..., description="Price per night for the room.")
    total_price: float = Field(..., description="Total price for the duration.")
    currency: str = Field(..., description="ISO currency code.")
    room_info: RoomInfo = Field(..., description="Room configuration details.")
    amenities: list[str] = Field(default_factory=list, description="Available hotel amenities.")
    available_rooms: int = Field(..., description="Number of available rooms.")
    is_available: bool = Field(True, description="Availability flag.")
    image_url: str | None = Field(None, description="Hotel preview image link.")


class HotelSearchResponse(BaseModel):
    """Envelope for GET /api/v1/hotels/search."""

    success: bool
    message: str
    data: list[HotelResult]
    count: int = Field(..., description="Total hotels matching search criteria.")
