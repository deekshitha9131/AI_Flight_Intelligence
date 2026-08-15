from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.schemas.hotel import HotelResult, HotelSearchParams, RoomInfo

logger = logging.getLogger(__name__)


class HotelService:
    """Service layer for mock hotel search operations."""

    def __init__(self, data_file: str | Path | None = None) -> None:
        if data_file is None:
            base_dir = Path(__file__).resolve().parents[1]
            self._data_file = base_dir / "mock_data" / "hotels.json"
        else:
            self._data_file = Path(data_file)
        self._hotels = self._load_hotels()

    def _load_hotels(self) -> list[dict[str, Any]]:
        if not self._data_file.exists():
            logger.warning("Hotels data file %s not found, returning empty list.", self._data_file)
            return []
        try:
            with self._data_file.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            return payload.get("hotels", [])
        except Exception as exc:
            logger.error("Failed to load hotels mock data: %s", exc)
            return []

    async def search_hotels(self, params: HotelSearchParams) -> list[HotelResult]:
        """Search hotels by destination city, dates, guests, and currency."""
        logger.info(
            "HotelService.search_hotels | destination=%s check_in=%s check_out=%s guests=%d",
            params.destination,
            params.check_in_date,
            params.check_out_date,
            params.guests,
        )

        query = params.destination.upper().strip()
        matched: list[HotelResult] = []

        # Calculate stay duration in nights (default 1 night if dates omitted)
        nights = 1
        if params.check_in_date and params.check_out_date:
            delta = (params.check_out_date - params.check_in_date).days
            nights = max(delta, 1)

        for h in self._hotels:
            city_code = str(h.get("city", "")).upper()
            name = str(h.get("name", "")).upper()
            location = str(h.get("location", "")).upper()

            # Match if IATA code or city name matches query
            if query in city_code or query in name or query in location:
                room_raw = h.get("room_info", {})
                room_info = RoomInfo(
                    room_type=room_raw.get("room_type", "Standard Room"),
                    bed_type=room_raw.get("bed_type", "1 Double Bed"),
                    max_occupancy=room_raw.get("max_occupancy", 2),
                )

                price_per_night = float(h.get("price_per_night", 100.0))
                total_price = price_per_night * nights * params.rooms

                result = HotelResult(
                    hotel_id=h.get("hotel_id", "htl-unknown"),
                    name=h.get("name", "Mock Luxury Hotel"),
                    city=h.get("city", params.destination),
                    location=h.get("location", "City Center"),
                    rating=float(h.get("rating", 4.5)),
                    price_per_night=price_per_night,
                    total_price=total_price,
                    currency=params.currency,
                    room_info=room_info,
                    amenities=h.get("amenities", ["Wi-Fi", "Air Conditioning"]),
                    available_rooms=int(h.get("available_rooms", 5)),
                    is_available=bool(h.get("is_available", True)),
                    image_url=h.get("image_url"),
                )
                matched.append(result)

        # Fallback generic mock if no specific city match found
        if not matched:
            matched.append(
                HotelResult(
                    hotel_id=f"htl-{query.lower()}-001",
                    name=f"Grand {params.destination.capitalize()} Hotel",
                    city=params.destination,
                    location=f"Central District, {params.destination}",
                    rating=4.6,
                    price_per_night=125.0,
                    total_price=125.0 * nights * params.rooms,
                    currency=params.currency,
                    room_info=RoomInfo(
                        room_type="Deluxe Executive Suite",
                        bed_type="1 King Bed",
                        max_occupancy=max(params.guests, 2),
                    ),
                    amenities=["Free Wi-Fi", "Swimming Pool", "24/7 Room Service", "Breakfast Included"],
                    available_rooms=10,
                    is_available=True,
                    image_url="https://images.unsplash.com/photo-1566073771259-6a8506099945",
                )
            )

        return matched[: params.max_results]
