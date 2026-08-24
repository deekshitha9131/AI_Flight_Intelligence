from __future__ import annotations

import logging
from typing import Any

import httpx
from app.core.config import get_settings
from app.integrations.amadeus.exceptions import (
    AmadeusAuthException,
    AmadeusConnectionException,
    AmadeusException,
    AmadeusNotFoundException,
    AmadeusRateLimitException,
    AmadeusServerException,
    AmadeusTimeoutException,
)
from app.integrations.providers.base import FlightProvider
from app.schemas.flight import FlightSearchParams

logger = logging.getLogger(__name__)


class DuffelProvider(FlightProvider):
    """Flight data provider implementation using the Duffel Air API (v2)."""

    def __init__(self, api_token: str | None = None) -> None:
        settings = get_settings()
        raw_token = api_token if api_token is not None else settings.duffel_token
        self._api_token = raw_token.strip()
        self._base_url = settings.duffel_base_url.rstrip("/")
        self._timeout = settings.duffel_timeout_seconds


    async def search_flights(self, params: FlightSearchParams) -> dict[str, Any]:
        """Execute flight search via Duffel API and return normalized response payload."""
        if not self._api_token:
            logger.error("Duffel API token is missing.")
            raise AmadeusAuthException("Duffel API access token is missing or not configured.")

        url = f"{self._base_url}/air/offer_requests"
        headers = {
            "Authorization": f"Bearer {self._api_token}",
            "Duffel-Version": "v2",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        cabin_map = {
            "ECONOMY": "economy",
            "PREMIUM_ECONOMY": "premium_economy",
            "BUSINESS": "business",
            "FIRST": "first",
        }
        cabin_class = cabin_map.get(params.travel_class.value, "economy")

        slices = [
            {
                "origin": params.origin.upper(),
                "destination": params.destination.upper(),
                "departure_date": params.departure_date.isoformat(),
            }
        ]

        if params.return_date:
            slices.append(
                {
                    "origin": params.destination.upper(),
                    "destination": params.origin.upper(),
                    "departure_date": params.return_date.isoformat(),
                }
            )

        passengers = [{"type": "adult"} for _ in range(params.adults)]
        if params.children:
            passengers.extend([{"type": "child"} for _ in range(params.children)])
        if params.infants:
            passengers.extend([{"type": "infant_without_seat"} for _ in range(params.infants)])

        payload = {
            "data": {
                "cabin_class": cabin_class,
                "slices": slices,
                "passengers": passengers,
            }
        }

        logger.info(
            "DuffelProvider.search_flights | origin=%s dest=%s date=%s cabin=%s passengers=%d",
            params.origin,
            params.destination,
            params.departure_date,
            cabin_class,
            len(passengers),
        )

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            logger.error("Duffel API search request timed out: %s", exc)
            raise AmadeusTimeoutException("Duffel API request timed out.") from exc
        except httpx.RequestError as exc:
            logger.error("Duffel API connectivity error: %s", exc)
            raise AmadeusConnectionException("Could not connect to Duffel API.") from exc

        if response.status_code == 401 or response.status_code == 403:
            logger.error("Duffel API authentication failed (status %d)", response.status_code)
            raise AmadeusAuthException("Duffel API authentication failed.")
        elif response.status_code == 429:
            logger.warning("Duffel API rate limit exceeded.")
            raise AmadeusRateLimitException("Duffel API rate limit exceeded.")
        elif response.status_code == 404:
            raise AmadeusNotFoundException(
                f"No flights found from {params.origin} to {params.destination}."
            )
        elif response.status_code >= 400:
            logger.error("Duffel API error HTTP %d: %s", response.status_code, response.text)
            raise AmadeusServerException(
                f"Duffel API error response (HTTP {response.status_code})."
            )

        try:
            body = response.json()
        except Exception as exc:
            logger.error("Failed to decode Duffel API JSON response: %s", exc)
            raise AmadeusServerException("Malformed response from Duffel API.") from exc

        return self._normalize_response(body, params=params)

    def _normalize_response(
        self, body: dict[str, Any], *, params: FlightSearchParams
    ) -> dict[str, Any]:
        """Convert Duffel response into standard internal payload format."""
        data_block = body.get("data", {})
        if isinstance(data_block, dict):
            offers = data_block.get("offers", [])
        elif isinstance(data_block, list):
            offers = data_block
        else:
            offers = []

        if not offers:
            logger.info("Duffel API returned 0 offers.")
            return {"data": [], "dictionaries": {"carriers": {}, "aircraft": {}}}

        normalized_offers = []
        carriers_dict: dict[str, str] = {}
        aircraft_dict: dict[str, str] = {}

        for offer in offers:
            try:
                norm_offer, c_dict, a_dict = self._normalize_single_offer(
                    offer, default_currency=params.currency
                )
                if norm_offer:
                    normalized_offers.append(norm_offer)
                    carriers_dict.update(c_dict)
                    aircraft_dict.update(a_dict)
            except Exception as exc:
                logger.warning("Error normalizing Duffel offer %r: %s", offer.get("id"), exc)

        normalized_offers = normalized_offers[: params.max_results]
        logger.info("DuffelProvider successfully normalized %d offers.", len(normalized_offers))

        return {
            "data": normalized_offers,
            "dictionaries": {
                "carriers": carriers_dict,
                "aircraft": aircraft_dict,
            },
        }

    def _normalize_single_offer(
        self, offer: dict[str, Any], *, default_currency: str
    ) -> tuple[dict[str, Any] | None, dict[str, str], dict[str, str]]:
        offer_id = str(offer.get("id", ""))
        total_amount = offer.get("total_amount")
        total_currency = str(offer.get("total_currency") or default_currency).upper()
        slices = offer.get("slices", [])

        if not offer_id or not slices or total_amount is None:
            return None, {}, {}

        price_val = str(total_amount)
        owner = offer.get("owner", {})
        owner_code = str(owner.get("iata_code", "")).upper()
        owner_name = str(owner.get("name", ""))

        carriers_dict: dict[str, str] = {}
        aircraft_dict: dict[str, str] = {}

        if owner_code and owner_name:
            carriers_dict[owner_code] = owner_name

        itineraries = []
        first_segment_cabin = "ECONOMY"

        for slice_item in slices:
            slice_duration = slice_item.get("duration", "")
            raw_segments = slice_item.get("segments", [])
            norm_segments = []

            for seg in raw_segments:
                orig_code = str(seg.get("origin", {}).get("iata_code", "")).upper()
                dest_code = str(seg.get("destination", {}).get("iata_code", "")).upper()
                departing_at = str(seg.get("departing_at", ""))
                arriving_at = str(seg.get("arriving_at", ""))
                seg_duration = str(seg.get("duration", ""))

                marketing_carrier = seg.get("marketing_carrier") or {}
                operating_carrier = seg.get("operating_carrier") or {}
                carrier_code = (
                    marketing_carrier.get("iata_code")
                    or operating_carrier.get("iata_code")
                    or owner_code
                )
                carrier_code = str(carrier_code).upper()

                carrier_name = (
                    marketing_carrier.get("name")
                    or operating_carrier.get("name")
                    or owner_name
                )
                if carrier_code and carrier_name:
                    carriers_dict[carrier_code] = carrier_name

                flight_num = (
                    seg.get("marketing_carrier_flight_number")
                    or seg.get("operating_carrier_flight_number")
                    or ""
                )

                aircraft_info = seg.get("aircraft") or {}
                aircraft_code = (
                    aircraft_info.get("iata_code")
                    or aircraft_info.get("code")
                    or aircraft_info.get("name")
                    or "77W"
                )
                aircraft_code = str(aircraft_code).upper()
                aircraft_name = aircraft_info.get("name") or aircraft_code
                if aircraft_code and aircraft_name:
                    aircraft_dict[aircraft_code] = aircraft_name

                # Extract cabin class if present in segment passengers
                seg_passengers = seg.get("passengers", [])
                if seg_passengers and isinstance(seg_passengers, list):
                    c_class = seg_passengers[0].get("cabin_class")
                    if c_class:
                        first_segment_cabin = str(c_class).upper()

                norm_segments.append(
                    {
                        "departure": {"iataCode": orig_code, "at": departing_at},
                        "arrival": {"iataCode": dest_code, "at": arriving_at},
                        "carrierCode": carrier_code,
                        "number": str(flight_num),
                        "duration": seg_duration or slice_duration,
                        "aircraft": {"code": aircraft_code},
                    }
                )

            if norm_segments:
                itineraries.append(
                    {
                        "duration": slice_duration,
                        "segments": norm_segments,
                    }
                )

        if not itineraries:
            return None, {}, {}

        normalized_offer = {
            "id": offer_id,
            "itineraries": itineraries,
            "price": {
                "grandTotal": price_val,
                "currency": total_currency,
            },
            "travelerPricings": [
                {
                    "travelerType": "ADULT",
                    "price": {"total": price_val},
                    "fareDetailsBySegment": [{"cabin": first_segment_cabin}],
                }
            ],
            "numberOfBookableSeats": 5,
        }

        return normalized_offer, carriers_dict, aircraft_dict
