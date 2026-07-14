from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.exceptions.base import ExternalAPIException, NotFoundException
from app.integrations.amadeus.exceptions import (
    AmadeusAuthException,
    AmadeusConnectionException,
    AmadeusException,
    AmadeusNotFoundException,
    AmadeusPermissionException,
    AmadeusRateLimitException,
    AmadeusServerException,
    AmadeusTimeoutException,
)
from app.repositories.search_repository import SearchRepository
from app.schemas.flight import FlightResult, FlightSearchParams, FlightSegment

logger = logging.getLogger(__name__)


class FlightService:
    """Business logic for flight search.

    Responsibilities:
    - Orchestrate the search: call repository → transform → persist history.
    - Transform raw Amadeus flight-offer payloads into clean FlightResult models.
    - Map AmadeusException subclasses to AppException subclasses.
    - Raise NotFoundException when Amadeus returns zero offers.
    """

    def __init__(self, repository: SearchRepository) -> None:
        self._repository = repository

    async def search_flights(
        self,
        *,
        params: FlightSearchParams,
        user_id: UUID,
    ) -> tuple[list[FlightResult], str]:
        """Execute a flight search and persist the search history.

        Args:
            params:  Validated flight search parameters.
            user_id: UUID of the authenticated requesting user.

        Returns:
            A tuple of (list[FlightResult], search_id_str).

        Raises:
            NotFoundException:    No flights found for the given parameters.
            ExternalAPIException: Any Amadeus API error.
        """
        logger.info(
            "FlightService.search_flights | user=%s origin=%s destination=%s date=%s",
            user_id,
            params.origin,
            params.destination,
            params.departure_date,
        )

        try:
            raw = await self._repository.fetch_flight_offers(params=params)
        except AmadeusNotFoundException:
            raise NotFoundException(
                message=f"No flights found from {params.origin} to {params.destination} "
                f"on {params.departure_date}."
            )
        except AmadeusRateLimitException as exc:
            logger.warning("Amadeus rate limit hit during flight search.")
            raise ExternalAPIException(
                message="Flight search is temporarily unavailable due to rate limiting. "
                "Please try again shortly."
            ) from exc
        except (AmadeusTimeoutException, AmadeusConnectionException) as exc:
            logger.error("Amadeus connectivity issue during flight search: %s", exc)
            raise ExternalAPIException(
                message="Flight search service is temporarily unreachable."
            ) from exc
        except AmadeusPermissionException as exc:
            logger.error("Amadeus permission denied during flight search.")
            raise ExternalAPIException(
                message="Flight search is not available with the current API credentials."
            ) from exc
        except AmadeusAuthException as exc:
            logger.error("Amadeus authentication failed during flight search: %s", exc)
            raise ExternalAPIException(
                message="Flight search is temporarily unavailable because authentication failed."
            ) from exc
        except AmadeusServerException as exc:
            logger.error("Amadeus server error during flight search: %s", exc)
            raise ExternalAPIException(
                message="Flight search service encountered an unexpected error."
            ) from exc
        except AmadeusException as exc:
            logger.error("Unhandled Amadeus error during flight search: %s", exc)
            raise ExternalAPIException(
                message="Flight search service encountered an unexpected error."
            ) from exc

        results = _transform_offers(raw, currency=params.currency)

        if not results:
            raise NotFoundException(
                message=f"No flights found from {params.origin} to {params.destination} "
                f"on {params.departure_date}."
            )

        # Persist search history — fire-and-forget style; a failure here must
        # not prevent the user from receiving their results.
        try:
            record = self._repository.save_search_history(
                user_id=user_id,
                params=params,
                result_count=len(results),
            )
            search_id = str(record.id)
        except Exception as exc:
            logger.error("Failed to persist flight search history: %s", exc)
            search_id = ""

        logger.info(
            "FlightService.search_flights | user=%s found=%d search_id=%s",
            user_id,
            len(results),
            search_id,
        )
        return results, search_id


# ---------------------------------------------------------------------------
# Transformation helpers
# ---------------------------------------------------------------------------


def _transform_offers(raw: dict[str, Any], *, currency: str) -> list[FlightResult]:
    """Convert a raw Amadeus flight-offers response into FlightResult models."""
    offers: list[Any] = raw.get("data", [])
    dictionaries: dict[str, Any] = raw.get("dictionaries", {})
    results: list[FlightResult] = []

    for offer in offers:
        result = _parse_offer(offer, dictionaries=dictionaries, currency=currency)
        if result is not None:
            results.append(result)

    return results


def _parse_offer(
    offer: dict[str, Any],
    *,
    dictionaries: dict[str, Any],
    currency: str,
) -> FlightResult | None:
    """Parse a single Amadeus flight offer into a FlightResult.

    Returns None and logs a warning on any parsing failure so one malformed
    offer never breaks the entire response.
    """
    try:
        offer_id: str = offer.get("id", "")
        itineraries: list[Any] = offer.get("itineraries", [])
        if not itineraries:
            return None

        is_round_trip = len(itineraries) > 1

        # Use the outbound itinerary for top-level route/time fields.
        outbound = itineraries[0]
        all_segments: list[FlightSegment] = []

        for itinerary in itineraries:
            for seg in itinerary.get("segments", []):
                parsed = _parse_segment(seg, dictionaries=dictionaries)
                if parsed:
                    all_segments.append(parsed)

        if not all_segments:
            return None

        first_seg = all_segments[0]
        last_seg = all_segments[-1]

        stops = sum(max(len(itin.get("segments", [])) - 1, 0) for itin in itineraries)

        # Price
        price_block: dict[str, Any] = offer.get("price", {})
        total_price = _safe_float(
            price_block.get("grandTotal") or price_block.get("total"), 0.0
        )
        price_currency = price_block.get("currency", currency)

        traveler_pricings: list[Any] = offer.get("travelerPricings", [])
        price_per_adult = _extract_adult_price(traveler_pricings, fallback=total_price)

        # Seats
        available_seats: int | None = _safe_int(offer.get("numberOfBookableSeats"))

        # Travel class — read from first traveler pricing if present
        travel_class = _extract_travel_class(traveler_pricings)

        # Duration of outbound itinerary
        duration = outbound.get("duration", "")

        return FlightResult(
            flight_id=offer_id,
            origin=first_seg.origin,
            destination=last_seg.destination,
            departure_time=first_seg.departure_time,
            arrival_time=last_seg.arrival_time,
            duration=duration,
            stops=stops,
            segments=all_segments,
            travel_class=travel_class,
            price=total_price,
            currency=price_currency,
            price_per_adult=price_per_adult,
            available_seats=available_seats,
            booking_link=None,
            is_round_trip=is_round_trip,
        )
    except Exception:
        logger.warning("Failed to parse Amadeus flight offer: %r", offer.get("id"))
        return None


def _parse_segment(
    seg: dict[str, Any],
    *,
    dictionaries: dict[str, Any],
) -> FlightSegment | None:
    """Parse a single itinerary segment."""
    try:
        departure: dict[str, Any] = seg.get("departure", {})
        arrival: dict[str, Any] = seg.get("arrival", {})
        carrier_code: str = seg.get("carrierCode", "")
        flight_number: str = f"{carrier_code}{seg.get('number', '')}"

        airline_name: str | None = dictionaries.get("carriers", {}).get(carrier_code)
        aircraft_code: str = seg.get("aircraft", {}).get("code", "")
        aircraft_name: str | None = (
            dictionaries.get("aircraft", {}).get(aircraft_code) or aircraft_code or None
        )

        return FlightSegment(
            flight_number=flight_number,
            airline=carrier_code,
            airline_name=airline_name,
            origin=departure.get("iataCode", ""),
            destination=arrival.get("iataCode", ""),
            departure_time=_parse_datetime(departure.get("at", "")),
            arrival_time=_parse_datetime(arrival.get("at", "")),
            duration=seg.get("duration", ""),
            aircraft=aircraft_name,
        )
    except Exception:
        logger.warning("Failed to parse flight segment: %r", seg)
        return None


def _extract_adult_price(
    traveler_pricings: list[Any],
    *,
    fallback: float,
) -> float:
    """Return the total price for the first ADULT traveler pricing entry."""
    for tp in traveler_pricings:
        if tp.get("travelerType") == "ADULT":
            price = tp.get("price", {})
            value = _safe_float(price.get("total") or price.get("base"), None)
            if value is not None:
                return value
    return fallback


def _extract_travel_class(traveler_pricings: list[Any]) -> str:
    """Return the cabin class from the first fare detail segment."""
    for tp in traveler_pricings:
        for fd in tp.get("fareDetailsBySegment", []):
            cabin = fd.get("cabin")
            if cabin:
                return str(cabin)
    return "ECONOMY"


def _parse_datetime(value: str) -> datetime:
    """Parse an ISO 8601 datetime string from Amadeus into a UTC datetime."""
    if not value:
        return datetime.now(timezone.utc)
    try:
        # Amadeus returns offsets like "2025-12-01T10:30:00" (no Z) or with offset
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return datetime.now(timezone.utc)


def _safe_float(value: Any, default: float | None = None) -> float:
    if value is None:
        return default  # type: ignore[return-value]
    try:
        return float(value)
    except (TypeError, ValueError):
        return default  # type: ignore[return-value]


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
