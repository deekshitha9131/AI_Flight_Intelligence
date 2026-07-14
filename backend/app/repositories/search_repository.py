from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.integrations.amadeus.client import AmadeusClient
from app.models.flight_search import FlightSearch
from app.schemas.flight import FlightSearchParams
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_FLIGHT_OFFERS_PATH = "/v2/shopping/flight-offers"


class SearchRepository:
    """Repository layer for flight search operations.

    Responsibilities:
    - Own the Amadeus flight-offers endpoint path and parameter mapping.
    - Return the raw Amadeus response without transformation.
    - Persist a FlightSearch history record to the database.
    - Propagate AmadeusException subclasses unchanged to the service layer.
    """

    def __init__(self, amadeus_client: AmadeusClient, db: Session) -> None:
        self._amadeus = amadeus_client
        self._db = db

    async def fetch_flight_offers(
        self, *, params: FlightSearchParams
    ) -> dict[str, Any]:
        """Call the Amadeus Flight Offers Search API and return the raw response.

        Args:
            params: Validated flight search parameters.

        Returns:
            Raw Amadeus API response dict.

        Raises:
            AmadeusException subclasses — propagated as-is.
        """
        query: dict[str, Any] = {
            "originLocationCode": params.origin,
            "destinationLocationCode": params.destination,
            "departureDate": params.departure_date.isoformat(),
            "adults": params.adults,
            "travelClass": params.travel_class.value,
            "currencyCode": params.currency,
            "nonStop": str(params.non_stop).lower(),
            "max": params.max_results,
        }

        if params.return_date is not None:
            query["returnDate"] = params.return_date.isoformat()
        if params.children:
            query["children"] = params.children
        if params.infants:
            query["infants"] = params.infants

        logger.debug(
            "SearchRepository.fetch_flight_offers | origin=%s destination=%s date=%s",
            params.origin,
            params.destination,
            params.departure_date,
        )

        return await self._amadeus.request("GET", _FLIGHT_OFFERS_PATH, params=query)

    def save_search_history(
        self,
        *,
        user_id: UUID,
        params: FlightSearchParams,
        result_count: int,
    ) -> FlightSearch:
        """Persist a flight search record for the authenticated user.

        Args:
            user_id:      UUID of the authenticated user.
            params:       Validated search parameters.
            result_count: Number of flight offers returned by Amadeus.

        Returns:
            The persisted FlightSearch ORM instance.
        """
        record = FlightSearch(
            user_id=user_id,
            origin=params.origin,
            destination=params.destination,
            departure_date=params.departure_date.isoformat(),
            return_date=params.return_date.isoformat() if params.return_date else None,
            adults=params.adults,
            children=params.children,
            infants=params.infants,
            travel_class=params.travel_class.value,
            currency=params.currency,
            non_stop=params.non_stop,
            max_results=params.max_results,
            result_count=result_count,
        )
        self._db.add(record)
        self._db.flush()

        logger.info(
            "SearchRepository.save_search_history | user_id=%s search_id=%s results=%d",
            user_id,
            record.id,
            result_count,
        )
        return record
