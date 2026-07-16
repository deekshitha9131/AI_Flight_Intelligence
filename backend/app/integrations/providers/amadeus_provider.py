from __future__ import annotations

import logging
from typing import Any

from app.integrations.amadeus.client import AmadeusClient
from app.integrations.providers.base import FlightProvider
from app.schemas.flight import FlightSearchParams

logger = logging.getLogger(__name__)

_FLIGHT_OFFERS_PATH = "/v2/shopping/flight-offers"


class AmadeusProvider(FlightProvider):
    """Concrete provider implementation that wraps the existing AmadeusClient."""

    def __init__(self, amadeus_client: AmadeusClient) -> None:
        self._amadeus = amadeus_client

    async def search_flights(self, params: FlightSearchParams) -> dict[str, Any]:
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
            "AmadeusProvider.search_flights | origin=%s destination=%s date=%s",
            params.origin,
            params.destination,
            params.departure_date,
        )

        return await self._amadeus.request("GET", _FLIGHT_OFFERS_PATH, params=query)
