from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.integrations.providers.base import FlightProvider
from app.models.flight_search import FlightSearch
from app.schemas.flight import FlightSearchParams
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class SearchRepository:
    """Repository layer for flight search operations.

    Responsibilities:
    - Invoke the configured flight provider for flight-offer requests.
    - Return the raw provider response without transformation.
    - Persist a FlightSearch history record to the database.
    - Propagate provider exceptions unchanged to the service layer.
    """

    def __init__(self, provider: FlightProvider, db: Session) -> None:
        self._provider = provider
        self._db = db

    async def fetch_flight_offers(
        self, *, params: FlightSearchParams
    ) -> dict[str, Any]:
        """Call the configured flight provider and return the raw response.

        Args:
            params: Validated flight search parameters.

        Returns:
            Raw provider response dict.
        """
        logger.debug(
            "SearchRepository.fetch_flight_offers | origin=%s destination=%s date=%s",
            params.origin,
            params.destination,
            params.departure_date,
        )

        return await self._provider.search_flights(params)

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
