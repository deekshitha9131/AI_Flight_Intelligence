from __future__ import annotations

from pydantic import BaseModel, Field


class AirportResult(BaseModel):
    """A single airport entry returned by the search endpoint."""

    airport_code: str = Field(..., description="IATA airport code (e.g. HYD, DXB).")
    airport_name: str = Field(..., description="Full name of the airport.")
    city: str = Field(..., description="City served by the airport.")
    country: str = Field(..., description="Country where the airport is located.")
    iata_code: str = Field(..., description="IATA code — identical to airport_code.")
    latitude: float | None = Field(
        None, description="Geographic latitude, if available."
    )
    longitude: float | None = Field(
        None, description="Geographic longitude, if available."
    )


class AirportSearchResponse(BaseModel):
    """Standard envelope returned by GET /api/v1/airports/search."""

    success: bool
    message: str
    data: list[AirportResult]
    count: int = Field(..., description="Total number of airports returned.")
