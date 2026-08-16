from __future__ import annotations

import copy
import json
import logging
from pathlib import Path
from typing import Any

from app.integrations.providers.base import FlightProvider
from app.schemas.flight import FlightSearchParams

logger = logging.getLogger(__name__)


class MockProvider(FlightProvider):
    """Return realistic mock flight-offer payloads matching Amadeus structure."""

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
        if not filtered:
            filtered = self._generate_dynamic_offers(params)

        dep_str = params.departure_date.isoformat()
        arr_str = params.return_date.isoformat() if params.return_date else None

        updated_offers = []
        for offer in filtered:
            off = copy.deepcopy(offer)
            itineraries = off.get("itineraries", [])
            if itineraries:
                outbound = itineraries[0]
                for seg in outbound.get("segments", []):
                    dep_at = seg.get("departure", {}).get("at", "")
                    time_part = dep_at.split("T")[1] if "T" in dep_at else "08:00:00"
                    seg["departure"]["at"] = f"{dep_str}T{time_part}"

                    arr_at = seg.get("arrival", {}).get("at", "")
                    arr_time = arr_at.split("T")[1] if "T" in arr_at else "10:30:00"
                    seg["arrival"]["at"] = f"{dep_str}T{arr_time}"
            if len(itineraries) > 1 and arr_str:
                inbound = itineraries[1]
                for seg in inbound.get("segments", []):
                    dep_at = seg.get("departure", {}).get("at", "")
                    time_part = dep_at.split("T")[1] if "T" in dep_at else "12:00:00"
                    seg["departure"]["at"] = f"{arr_str}T{time_part}"

                    arr_at = seg.get("arrival", {}).get("at", "")
                    arr_time = arr_at.split("T")[1] if "T" in arr_at else "14:30:00"
                    seg["arrival"]["at"] = f"{arr_str}T{arr_time}"
            updated_offers.append(off)

        updated_offers = sorted(
            updated_offers, key=lambda offer: self._price_value(offer)
        )
        updated_offers = updated_offers[: params.max_results]
        return {"data": updated_offers, "dictionaries": self._dictionaries()}

    def _generate_dynamic_offers(
        self, params: FlightSearchParams
    ) -> list[dict[str, Any]]:
        """Generate realistic mock flight offers when static JSON lacks the route."""
        dep_str = params.departure_date.isoformat()
        arr_str = params.return_date.isoformat() if params.return_date else None

        # Deterministic base price from origin + destination
        seed = abs(hash(f"{params.origin}{params.destination}"))
        base_price = 120.0 + (seed % 250)

        airlines = [
            ("6E", "201", "320"),
            ("AI", "505", "321"),
            ("EK", "512", "77W"),
        ]
        offers = []

        for i, (carrier, flight_num, aircraft) in enumerate(airlines):
            price = round(base_price + (i * 35.5), 2)
            dep_hour = 6 + (i * 5)
            arr_hour = dep_hour + 2

            offer = {
                "id": f"mock-offer-dyn-{i+1}",
                "itineraries": [
                    {
                        "duration": "PT2H30M",
                        "segments": [
                            {
                                "departure": {
                                    "iataCode": params.origin.upper(),
                                    "at": f"{dep_str}T{dep_hour:02d}:00:00",
                                },
                                "arrival": {
                                    "iataCode": params.destination.upper(),
                                    "at": f"{dep_str}T{arr_hour:02d}:30:00",
                                },
                                "carrierCode": carrier,
                                "number": flight_num,
                                "duration": "PT2H30M",
                                "aircraft": {"code": aircraft},
                            }
                        ],
                    }
                ],
                "price": {
                    "grandTotal": str(price),
                    "currency": params.currency.upper(),
                },
                "travelerPricings": [
                    {
                        "travelerType": "ADULT",
                        "price": {"total": str(price)},
                        "fareDetailsBySegment": [
                            {"cabin": params.travel_class.value}
                        ],
                    }
                ],
                "numberOfBookableSeats": 7 - i,
            }

            if arr_str:
                offer["itineraries"].append(
                    {
                        "duration": "PT2H30M",
                        "segments": [
                            {
                                "departure": {
                                    "iataCode": params.destination.upper(),
                                    "at": f"{arr_str}T10:00:00",
                                },
                                "arrival": {
                                    "iataCode": params.origin.upper(),
                                    "at": f"{arr_str}T12:30:00",
                                },
                                "carrierCode": carrier,
                                "number": str(int(flight_num) + 1),
                                "duration": "PT2H30M",
                                "aircraft": {"code": aircraft},
                            }
                        ],
                    }
                )

            offers.append(offer)

        return offers

    def _matches(self, params: FlightSearchParams, offer: dict[str, Any]) -> bool:
        itinerary = offer.get("itineraries", [{}])[0]
        segments = itinerary.get("segments", [])
        if not segments:
            return False

        first_segment = segments[0]
        last_segment = segments[-1]
        orig = first_segment.get("departure", {}).get("iataCode")
        dest = last_segment.get("arrival", {}).get("iataCode")
        if orig != params.origin.upper() or dest != params.destination.upper():
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
