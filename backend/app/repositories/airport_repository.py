from __future__ import annotations

import logging
from typing import Any

from app.integrations.amadeus.client import AmadeusClient

logger = logging.getLogger(__name__)

# Amadeus Location Search endpoint — returns airports, cities, and points of interest.
# subType=AIRPORT restricts results to airports only.
_LOCATION_SEARCH_PATH = "/v1/reference-data/locations"


class AirportRepository:
    """Repository layer for airport data sourced from the Amadeus API.

    Responsibilities:
    - Own the Amadeus endpoint path and query parameter construction.
    - Return the raw API response without any transformation.
    - Propagate AmadeusException subclasses to the service layer unchanged.
    """

    def __init__(self, client: AmadeusClient) -> None:
        self._client = client

    async def search(self, *, keyword: str) -> dict[str, Any]:
        """Fetch raw airport search results from the Amadeus Location API.

        Args:
            keyword: Free-text search term (IATA code, city name, or airport name).

        Returns:
            Raw Amadeus API response dict containing a ``data`` list.

        Raises:
            AmadeusException subclasses — propagated as-is for the service to map.
        """
        logger.debug("AirportRepository.search | keyword=%r", keyword)

        return await self._client.request(
            "GET",
            _LOCATION_SEARCH_PATH,
            params={
                "keyword": keyword,
                "subType": "AIRPORT",
            },
        )
