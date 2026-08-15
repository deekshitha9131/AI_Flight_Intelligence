from __future__ import annotations

import logging
from typing import Any

from app.integrations.amadeus.client import AmadeusClient

logger = logging.getLogger(__name__)

# Amadeus Location Search endpoint — returns airports, cities, and points of interest.
# subType=AIRPORT restricts results to airports only.
_LOCATION_SEARCH_PATH = "/v1/reference-data/locations"


class AirportRepository:
    """Repository layer for airport data sourced from the Amadeus API with mock fallback."""

    def __init__(self, client: AmadeusClient | None) -> None:
        self._client = client

    async def search(self, *, keyword: str) -> dict[str, Any]:
        """Fetch raw airport search results from the Amadeus Location API or fallback mock data."""
        logger.debug("AirportRepository.search | keyword=%r", keyword)

        if self._client is None:
            logger.info("AirportRepository.search | AmadeusClient is None, using mock airport search for %r", keyword)
            return self._mock_search(keyword)

        try:
            return await self._client.request(
                "GET",
                _LOCATION_SEARCH_PATH,
                params={
                    "keyword": keyword,
                    "subType": "AIRPORT",
                },
            )
        except Exception as exc:
            logger.warning("Amadeus airport search failed (%s), falling back to mock airport search for %r", exc, keyword)
            return self._mock_search(keyword)

    def _mock_search(self, keyword: str) -> dict[str, Any]:
        term = keyword.strip().lower()
        matches = []
        for ap in _MOCK_AIRPORTS:
            code = ap["iataCode"].lower()
            name = ap["name"].lower()
            city = ap["address"]["cityName"].lower()
            country = ap["address"]["countryName"].lower()
            if term == code or term in name or term in city or term in country:
                matches.append(ap)
        return {"data": matches}


_MOCK_AIRPORTS: list[dict[str, Any]] = [
    {
        "type": "location",
        "subType": "AIRPORT",
        "name": "Rajiv Gandhi International Airport",
        "detailedName": "HYDERABAD/IN:RAJIV GANDHI INTL",
        "id": "AHYD",
        "iataCode": "HYD",
        "geoCode": {"latitude": 17.2403, "longitude": 78.4294},
        "address": {"cityName": "Hyderabad", "cityCode": "HYD", "countryName": "India", "countryCode": "IN"},
    },
    {
        "type": "location",
        "subType": "AIRPORT",
        "name": "Indira Gandhi International Airport",
        "detailedName": "DELHI/IN:INDIRA GANDHI INTL",
        "id": "ADEL",
        "iataCode": "DEL",
        "geoCode": {"latitude": 28.5562, "longitude": 77.1000},
        "address": {"cityName": "Delhi", "cityCode": "DEL", "countryName": "India", "countryCode": "IN"},
    },
    {
        "type": "location",
        "subType": "AIRPORT",
        "name": "Chhatrapati Shivaji Maharaj International Airport",
        "detailedName": "MUMBAI/IN:CHHATRAPATI SHIVAJI INTL",
        "id": "ABOM",
        "iataCode": "BOM",
        "geoCode": {"latitude": 19.0896, "longitude": 72.8656},
        "address": {"cityName": "Mumbai", "cityCode": "BOM", "countryName": "India", "countryCode": "IN"},
    },
    {
        "type": "location",
        "subType": "AIRPORT",
        "name": "Kempegowda International Airport",
        "detailedName": "BENGALURU/IN:KEMPEGOWDA INTL",
        "id": "ABLR",
        "iataCode": "BLR",
        "geoCode": {"latitude": 13.1986, "longitude": 77.7066},
        "address": {"cityName": "Bengaluru", "cityCode": "BLR", "countryName": "India", "countryCode": "IN"},
    },
    {
        "type": "location",
        "subType": "AIRPORT",
        "name": "Dubai International Airport",
        "detailedName": "DUBAI/AE:DUBAI INTL",
        "id": "ADXB",
        "iataCode": "DXB",
        "geoCode": {"latitude": 25.2532, "longitude": 55.3657},
        "address": {"cityName": "Dubai", "cityCode": "DXB", "countryName": "United Arab Emirates", "countryCode": "AE"},
    },
    {
        "type": "location",
        "subType": "AIRPORT",
        "name": "London Heathrow Airport",
        "detailedName": "LONDON/GB:HEATHROW",
        "id": "ALHR",
        "iataCode": "LHR",
        "geoCode": {"latitude": 51.4700, "longitude": -0.4543},
        "address": {"cityName": "London", "cityCode": "LON", "countryName": "United Kingdom", "countryCode": "GB"},
    },
    {
        "type": "location",
        "subType": "AIRPORT",
        "name": "John F. Kennedy International Airport",
        "detailedName": "NEW YORK/US:JOHN F KENNEDY INTL",
        "id": "AJFK",
        "iataCode": "JFK",
        "geoCode": {"latitude": 40.6413, "longitude": -73.7781},
        "address": {"cityName": "New York", "cityCode": "NYC", "countryName": "United States", "countryCode": "US"},
    },
    {
        "type": "location",
        "subType": "AIRPORT",
        "name": "San Francisco International Airport",
        "detailedName": "SAN FRANCISCO/US:SAN FRANCISCO INTL",
        "id": "ASFO",
        "iataCode": "SFO",
        "geoCode": {"latitude": 37.6213, "longitude": -122.3790},
        "address": {"cityName": "San Francisco", "cityCode": "SFO", "countryName": "United States", "countryCode": "US"},
    },
    {
        "type": "location",
        "subType": "AIRPORT",
        "name": "Singapore Changi Airport",
        "detailedName": "SINGAPORE/SG:CHANGI",
        "id": "ASIN",
        "iataCode": "SIN",
        "geoCode": {"latitude": 1.3644, "longitude": 103.9915},
        "address": {"cityName": "Singapore", "cityCode": "SIN", "countryName": "Singapore", "countryCode": "SG"},
    },
    {
        "type": "location",
        "subType": "AIRPORT",
        "name": "Suvarnabhumi Airport",
        "detailedName": "BANGKOK/TH:SUVARNABHUMI",
        "id": "ABKK",
        "iataCode": "BKK",
        "geoCode": {"latitude": 13.6900, "longitude": 100.7501},
        "address": {"cityName": "Bangkok", "cityCode": "BKK", "countryName": "Thailand", "countryCode": "TH"},
    },
    {
        "type": "location",
        "subType": "AIRPORT",
        "name": "Frankfurt Airport",
        "detailedName": "FRANKFURT/DE:FRANKFURT MAIN",
        "id": "AFRA",
        "iataCode": "FRA",
        "geoCode": {"latitude": 50.0379, "longitude": 8.5622},
        "address": {"cityName": "Frankfurt", "cityCode": "FRA", "countryName": "Germany", "countryCode": "DE"},
    },
    {
        "type": "location",
        "subType": "AIRPORT",
        "name": "Amsterdam Airport Schiphol",
        "detailedName": "AMSTERDAM/NL:SCHIPHOL",
        "id": "AAMS",
        "iataCode": "AMS",
        "geoCode": {"latitude": 52.3105, "longitude": 4.7683},
        "address": {"cityName": "Amsterdam", "cityCode": "AMS", "countryName": "Netherlands", "countryCode": "NL"},
    },
]

