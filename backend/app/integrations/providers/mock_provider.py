from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from app.integrations.providers.base import FlightProvider
from app.schemas.flight import FlightSearchParams

logger = logging.getLogger(__name__)


class MockProvider(FlightProvider):
    """Return realistic mock flight-offer payloads that match the Amadeus shape."""

    def __init__(self, data_file: str | None = None) -> None:
        base_dir = Path(__file__).resolve().parents[2]
        default_path = base_dir / "mock_data" / "flights.json"
        self._data_file = Path(data_file or default_path)
        self._offers = self._load_offers()

    def _load_offers(self) -> list[dict[str, Any]]:
        if not self._data_file.exists():
            return []
        with self._data_file.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return payload.get("data", [])

    async def search_flights(self, params: FlightSearchParams) -> dict[str, Any]:
        filtered = [offer for offer in self._offers if self._matches(params, offer)]
        filtered = sorted(filtered, key=lambda offer: self._price_value(offer))
        filtered = filtered[: params.max_results]
        return {"data": filtered, "dictionaries": self._dictionaries()}

    def _matches(self, params: FlightSearchParams, offer: dict[str, Any]) -> bool:
        itinerary = offer.get("itineraries", [{}])[0]
        segments = itinerary.get("segments", [])
        if not segments:
            return False

        first_segment = segments[0]
        last_segment = segments[-1]
        if first_segment.get("departure", {}).get("iataCode") != params.origin.upper():
            return False
        if last_segment.get("arrival", {}).get("iataCode") != params.destination.upper():
            return False

        travel_class = offer.get("travelerPricings", [{}])[0].get(
            "fareDetailsBySegment", []
        )
        requested_class = params.travel_class.value
        if travel_class and isinstance(travel_class[0], dict):
            cabin = travel_class[0].get("cabin")
            if cabin and cabin != requested_class:
                return False

        if params.non_stop:
            return len(segments) == 1 and len(itinerary.get("segments", [])) == 1

        return True

    def _price_value(self, offer: dict[str, Any]) -> float:
        price_block = offer.get("price", {})
        grand_total = price_block.get("grandTotal") or price_block.get("total")
        if isinstance(grand_total, (int, float)):
            return float(grand_total)
        if isinstance(grand_total, str):
            try:
                return float(grand_total)
            except ValueError:
                return float("inf")
        return float("inf")

    def _dictionaries(self) -> dict[str, Any]:
        return {
            "carriers": {
                "EK": "Emirates",
                "AI": "Air India",
                "6E": "IndiGo",
                "QR": "Qatar Airways",
                "SQ": "Singapore Airlines",
                "LH": "Lufthansa",
                "EY": "Etihad",
                "BA": "British Airways",
            },
            "aircraft": {
                "77W": "Boeing 777-300ER",
                "320": "Airbus A320",
                "321": "Airbus A321",
                "788": "Boeing 787-8",
                "359": "Airbus A350-900",
                "772": "Boeing 777-200",
            },
        }
