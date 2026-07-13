from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.amadeus import get_amadeus_client
from app.dependencies.auth import get_current_user
from app.integrations.amadeus.client import AmadeusClient
from app.models.user import User
from app.repositories.search_repository import SearchRepository
from app.schemas.flight import FlightSearchParams, FlightSearchResponse, TravelClass
from app.services.flight_service import FlightService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/flights", tags=["flights"])


@router.get(
    "/search",
    response_model=FlightSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search available flights",
    description=(
        "Search for available flight offers between two airports on a given date. "
        "Supports one-way and round-trip searches, multiple passenger types, "
        "cabin class selection, and currency conversion.\n\n"
        "**Authentication required** — include a valid `Bearer` token.\n\n"
        "**Validation rules**\n"
        "- `origin` / `destination` must be 3-letter IATA codes\n"
        "- `departure_date` cannot be in the past\n"
        "- `return_date` must be after `departure_date`\n"
        "- `adults` minimum 1, maximum 9\n"
        "- Total passengers (adults + children + infants) ≤ 9\n"
        "- `infants` cannot exceed `adults`\n\n"
        "**Errors**\n"
        "- `400` — validation failure\n"
        "- `401` — missing or invalid JWT token\n"
        "- `404` — no flights found\n"
        "- `429` — Amadeus rate limit exceeded\n"
        "- `500` — unexpected server error"
    ),
    responses={
        400: {"description": "Validation error — invalid parameters."},
        401: {"description": "Authentication required."},
        404: {"description": "No flights found for the given search criteria."},
        429: {"description": "Amadeus API rate limit exceeded."},
        500: {"description": "Unexpected server error."},
    },
)
async def search_flights(
    # ------------------------------------------------------------------ route
    origin: Annotated[
        str,
        Query(
            min_length=3,
            max_length=3,
            description="IATA code of the departure airport.",
            example=["HYD"],
        ),
    ],
    destination: Annotated[
        str,
        Query(
            min_length=3,
            max_length=3,
            description="IATA code of the arrival airport.",
            example=["DXB"],
        ),
    ],
    departure_date: Annotated[
        str,
        Query(
            description="Departure date in YYYY-MM-DD format.",
            example=["2025-12-01"],
        ),
    ],
    # ---------------------------------------------------------------- optional
    return_date: Annotated[
        str | None,
        Query(
            description="Return date for round trips (YYYY-MM-DD).",
            example=["2025-12-10"],
        ),
    ] = None,
    # -------------------------------------------------------------- passengers
    adults: Annotated[
        int,
        Query(ge=1, le=9, description="Number of adult passengers (age 12+)."),
    ] = 1,
    children: Annotated[
        int,
        Query(ge=0, le=9, description="Number of child passengers (age 2–11)."),
    ] = 0,
    infants: Annotated[
        int,
        Query(ge=0, le=9, description="Number of infant passengers (under age 2)."),
    ] = 0,
    # ------------------------------------------------------------- preferences
    travel_class: Annotated[
        TravelClass,
        Query(description="Cabin class: ECONOMY, PREMIUM_ECONOMY, BUSINESS, or FIRST."),
    ] = TravelClass.ECONOMY,
    currency: Annotated[
        str,
        Query(
            min_length=3,
            max_length=3,
            description="ISO 4217 currency code for prices.",
            example=["USD"],
        ),
    ] = "USD",
    non_stop: Annotated[
        bool,
        Query(description="Return only non-stop flights when true."),
    ] = False,
    max_results: Annotated[
        int,
        Query(ge=1, le=50, description="Maximum number of offers to return (1–50)."),
    ] = 10,
    # --------------------------------------------------------------- injected
    current_user: User = Depends(get_current_user),
    amadeus_client: AmadeusClient = Depends(get_amadeus_client),
    db: Session = Depends(get_db),
) -> FlightSearchResponse:
    """Return available flight offers matching the search criteria."""
    from datetime import date

    def _parse_date(value: str, field: str) -> date:
        try:
            return date.fromisoformat(value)
        except ValueError:
            from app.exceptions.base import ValidationException

            raise ValidationException(
                message=f"Invalid date format for '{field}'. Expected YYYY-MM-DD."
            )

    params = FlightSearchParams(
        origin=origin,
        destination=destination,
        departure_date=_parse_date(departure_date, "departure_date"),
        return_date=_parse_date(return_date, "return_date") if return_date else None,
        adults=adults,
        children=children,
        infants=infants,
        travel_class=travel_class,
        currency=currency,
        non_stop=non_stop,
        max_results=max_results,
    )

    repository = SearchRepository(amadeus_client=amadeus_client, db=db)
    service = FlightService(repository=repository)

    flights, search_id = await service.search_flights(
        params=params,
        user_id=current_user.id,
    )

    return FlightSearchResponse(
        success=True,
        message="Flights retrieved successfully.",
        data=flights,
        count=len(flights),
        search_id=search_id,
    )
