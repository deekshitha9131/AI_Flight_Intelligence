from __future__ import annotations

import logging
from typing import Annotated

from app.schemas.hotel import HotelSearchParams, HotelSearchResponse
from app.services.hotel_service import HotelService
from fastapi import APIRouter, Query, status
from pydantic import ValidationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hotels", tags=["hotels"])


@router.get(
    "/search",
    response_model=HotelSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search mock hotel offers",
    description=(
        "Search for available hotels in a target destination city or airport location.\n\n"
        "Returns realistic mock hotel availability with price per night, total stay cost, "
        "ratings, room info, and amenities."
    ),
    responses={
        400: {"description": "Invalid query parameters."},
        500: {"description": "Unexpected server error."},
    },
)
async def search_hotels(
    destination: Annotated[
        str,
        Query(
            min_length=2,
            max_length=50,
            description="City name or IATA code for location (e.g. HYD, DXB, London).",
            example="DXB",
        ),
    ],
    check_in_date: Annotated[
        str | None,
        Query(description="Check-in date in YYYY-MM-DD format.", example="2025-12-01"),
    ] = None,
    check_out_date: Annotated[
        str | None,
        Query(description="Check-out date in YYYY-MM-DD format.", example="2025-12-05"),
    ] = None,
    guests: Annotated[
        int,
        Query(ge=1, le=10, description="Number of guests."),
    ] = 1,
    rooms: Annotated[
        int,
        Query(ge=1, le=5, description="Number of rooms."),
    ] = 1,
    currency: Annotated[
        str,
        Query(min_length=3, max_length=3, description="ISO 4217 currency code."),
    ] = "USD",
    max_results: Annotated[
        int,
        Query(ge=1, le=50, description="Maximum number of hotel results to return."),
    ] = 10,
) -> HotelSearchResponse:
    """Return available mock hotels matching the search criteria."""
    from datetime import date
    from app.exceptions.base import ValidationException

    def _parse_date(value: str | None, field: str) -> date | None:
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise ValidationException(
                message=f"Invalid date format for '{field}'. Expected YYYY-MM-DD."
            )

    try:
        params = HotelSearchParams(
            destination=destination,
            check_in_date=_parse_date(check_in_date, "check_in_date"),
            check_out_date=_parse_date(check_out_date, "check_out_date"),
            guests=guests,
            rooms=rooms,
            currency=currency,
            max_results=max_results,
        )
    except ValidationError as exc:
        raise ValidationException(
            message="Invalid hotel search parameters.",
            details={"errors": exc.errors()},
        )

    service = HotelService()
    hotels = await service.search_hotels(params=params)

    return HotelSearchResponse(
        success=True,
        message="Hotels retrieved successfully.",
        data=hotels,
        count=len(hotels),
    )
