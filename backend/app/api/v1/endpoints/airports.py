from __future__ import annotations

import logging

from app.dependencies.amadeus import get_amadeus_client
from app.integrations.amadeus.client import AmadeusClient
from app.repositories.airport_repository import AirportRepository
from app.schemas.airport import AirportSearchResponse
from app.services.airport_service import AirportService
from fastapi import APIRouter, Depends, Query, status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/airports", tags=["airports"])


@router.get(
    "/search",
    response_model=AirportSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search airports by keyword",
    description=(
        "Search for airports using a free-text keyword. "
        "Accepts IATA codes (e.g. `HYD`, `DXB`), city names (e.g. `Hyderabad`, `Dubai`), "
        "or partial airport names. "
        "Returns a list of matching airports with IATA code, name, city, country, "
        "and geographic coordinates where available.\n\n"
        "**Errors**\n"
        "- `400` — keyword is blank or fails length validation\n"
        "- `404` — no airports matched the keyword\n"
        "- `429` — Amadeus rate limit exceeded\n"
        "- `500` — unexpected server error"
    ),
    responses={
        400: {"description": "Invalid or blank keyword."},
        404: {"description": "No airports found for the given keyword."},
        429: {"description": "Amadeus API rate limit exceeded."},
        500: {"description": "Unexpected server error."},
    },
)
async def search_airports(
    keyword: str = Query(
        ...,
        min_length=2,
        max_length=50,
        description="IATA code, city name, or airport name to search for.",
        example=["Hyderabad"],
    ),
    amadeus_client: AmadeusClient = Depends(get_amadeus_client),
) -> AirportSearchResponse:
    """Return a list of airports matching the provided keyword."""
    repository = AirportRepository(client=amadeus_client)
    service = AirportService(repository=repository)

    airports = await service.search_airports(keyword=keyword)

    return AirportSearchResponse(
        success=True,
        message="Airports retrieved successfully.",
        data=airports,
        count=len(airports),
    )
