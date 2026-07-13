from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SearchHistoryItem(BaseModel):
    """A single search history record returned by the API."""

    id: UUID = Field(..., description="Unique identifier of the search record.")
    origin: str = Field(..., description="IATA code of the departure airport.")
    destination: str = Field(..., description="IATA code of the arrival airport.")
    departure_date: str = Field(..., description="Departure date (YYYY-MM-DD).")
    return_date: str | None = Field(
        None, description="Return date (YYYY-MM-DD), null for one-way."
    )
    adults: int = Field(..., description="Number of adult passengers.")
    children: int = Field(..., description="Number of child passengers.")
    infants: int = Field(..., description="Number of infant passengers.")
    travel_class: str = Field(..., description="Cabin class searched.")
    currency: str = Field(..., description="Currency code used for the search.")
    non_stop: bool = Field(
        ..., description="Whether only non-stop flights were requested."
    )
    result_count: int = Field(..., description="Number of flight offers returned.")
    search_timestamp: datetime = Field(
        ..., description="UTC timestamp when the search was performed."
    )

    model_config = {"from_attributes": True}


class PaginationMeta(BaseModel):
    """Pagination metadata included in list responses."""

    page: int = Field(..., description="Current page number (1-based).")
    page_size: int = Field(..., description="Number of items per page.")
    total_items: int = Field(
        ..., description="Total number of search records for this user."
    )
    total_pages: int = Field(..., description="Total number of pages.")
    has_next: bool = Field(..., description="True when a next page exists.")
    has_previous: bool = Field(..., description="True when a previous page exists.")


class SearchHistoryListResponse(BaseModel):
    """Paginated list of search history records."""

    success: bool
    message: str
    data: list[SearchHistoryItem]
    pagination: PaginationMeta


class SearchHistoryDetailResponse(BaseModel):
    """Single search history record response."""

    success: bool
    message: str
    data: SearchHistoryItem


class DeleteResponse(BaseModel):
    """Response returned after a successful delete operation."""

    success: bool
    message: str
