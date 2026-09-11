import httpx
import hashlib
import logging
from typing import List, Optional
from app.core.config import settings
from app.schemas.flight import FareOption, FlightSearchRequest, FlightResponse, FlightSegment
from datetime import datetime, timedelta
import isodate

logger = logging.getLogger(__name__)
MAX_FLIGHT_RESULTS = 15

class DuffelProvider:
    """Duffel API flight provider."""

    def __init__(self):
        self.base_url = settings.DUFFEL_BASE_URL
        self.api_key = settings.FLIGHT_API_KEY
        self.timeout = settings.DUFFEL_TIMEOUT
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Duffel-Version": "v2",
            "Content-Type": "application/json",
        }

    async def search_flights(self, request: FlightSearchRequest) -> List[FlightResponse]:
        """
        Search for flights using Duffel API.

        Args:
            request: Normalized flight search request.

        Returns:
            List of normalized flight responses.

        Raises:
            Exception: If there is an error communicating with the provider.
        """
        self.api_key = settings.FLIGHT_API_KEY
        self.headers["Authorization"] = f"Bearer {self.api_key}"

        if not self.api_key or self.api_key.startswith("your-"):
            logger.error("Duffel API key not configured")
            raise Exception("Flight provider not configured")

        # Prepare Duffel request for offer requests
        offer_request_data = {
            "data": {
                "slices": [
                    {
                        "origin": request.origin,
                        "destination": request.destination,
                        "departure_date": request.departure_date.date().isoformat(),
                    }
                ],
                "passengers": [
                    {"type": "adult"} for _ in range(request.passengers)
                ],
                "cabin_class": request.cabin_class.lower(),
                "currency": request.currency,
            }
        }

        if request.return_date:
            offer_request_data["data"]["slices"].append({
                "origin": request.destination,
                "destination": request.origin,
                "departure_date": request.return_date.date().isoformat(),
            })

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Create offer request
                response = await client.post(
                    f"{self.base_url}/offer_requests",
                    json=offer_request_data,
                    headers=self.headers,
                )
                response.raise_for_status()
                offer_request = response.json()

                # Get the offer request ID to fetch offers
                offer_request_id = offer_request.get("id") or offer_request.get("data", {}).get("id")
                if not offer_request_id:
                    raise Exception("Flight provider returned no offer request ID")

                # Fetch the offer request, including its offers.
                offer_response = await client.get(
                    f"{self.base_url}/offer_requests/{offer_request_id}?view=offers",
                    headers=self.headers,
                )
                offer_response.raise_for_status()
                offer_request_data = offer_response.json().get("data", {})
                offers_data = {"data": offer_request_data.get("offers", [])}

                # Normalize the response
                return self._normalize_offers(offers_data, request)

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from Duffel: {e.response.status_code} - {e.response.text}")
            # Try to provide more detailed error information
            try:
                error_detail = e.response.json()
                raise Exception(f"Flight provider error: {e.response.status_code} - {error_detail.get('title', 'Unknown error')}")
            except:
                raise Exception(f"Flight provider error: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Request error to Duffel: {str(e)}")
            raise Exception(f"Flight provider unavailable: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in Duffel provider: {str(e)}")
            raise Exception(f"Flight provider error: {str(e)}")

    def _normalize_offers(self, offers_data: dict, request: FlightSearchRequest) -> List[FlightResponse]:
        """
        Normalize Duffel offers into our internal flight representation.

        Args:
            offers_data: Raw response from Duffel API.
            request: Original search request.

        Returns:
            List of normalized FlightResponse objects.
        """
        grouped_flights = {}
        skipped_offers = 0
        offers = offers_data.get("data", [])

        # Duffel offers data structure: {"data": [offer1, offer2, ...]}
        for offer in offers:
            try:
                slices = offer.get("slices", [])
                if not slices:
                    raise ValueError("offer has no slices")

                normalized_slices = []
                for slice_data in slices:
                    normalized_slices.append(self._normalize_slice(slice_data))

                itinerary_key = "||".join(
                    ";".join(self._segment_identity(segment) for segment in slice_segments)
                    for slice_segments in normalized_slices
                )
                if not itinerary_key:
                    raise ValueError("offer has no usable segments")

                itinerary_id = hashlib.sha256(itinerary_key.encode("utf-8")).hexdigest()[:16]
                price = float(offer.get("total_amount", "0"))
                currency = offer.get("total_currency", request.currency)
                fare_option = FareOption(
                    id=str(offer.get("id", itinerary_id)),
                    price=price,
                    currency=currency,
                )

                if itinerary_key not in grouped_flights:
                    outbound = normalized_slices[0]
                    return_slice = normalized_slices[1] if len(normalized_slices) > 1 else None
                    grouped_flights[itinerary_key] = self._build_flight(
                        itinerary_id,
                        outbound,
                        return_slice,
                        price,
                        currency,
                        fare_option,
                    )
                else:
                    flight = grouped_flights[itinerary_key]
                    flight.fare_options.append(fare_option)
                    if price < flight.price:
                        flight.price = price
            except Exception as e:
                skipped_offers += 1
                logger.warning(f"Skipping offer due to normalization error: {str(e)}")
                continue

        flights = list(grouped_flights.values())
        fare_count = sum(len(flight.fare_options) for flight in flights)
        flights.sort(key=lambda flight: (
            flight.price,
            flight.stops,
            flight.duration,
            flight.departure_time,
        ))
        shortlisted_flights = flights[:MAX_FLIGHT_RESULTS]
        logger.info(
            "Duffel offers received: %d; unique itineraries: %d; fare offers: %d; "
            "shortlisted itineraries: %d; skipped invalid offers: %d",
            len(offers), len(flights), fare_count, len(shortlisted_flights), skipped_offers,
        )
        return shortlisted_flights

    def _normalize_slice(self, slice_data: dict) -> List[FlightSegment]:
        segments = slice_data.get("segments", [])
        if not segments:
            raise ValueError("slice has no segments")

        normalized = []
        for segment in segments:
            carrier = segment.get("marketing_carrier") or segment.get("operating_carrier") or {}
            carrier_code = carrier.get("iata_code") or carrier.get("icao_code") or carrier.get("name")
            flight_number = self._extract_flight_number(segment, carrier_code)
            origin = self._extract_airport_code(segment.get("origin"))
            destination = self._extract_airport_code(segment.get("destination"))
            required = (
                carrier_code, flight_number, origin, destination,
                segment.get("departing_at"), segment.get("arriving_at"),
            )
            if not all(required):
                raise ValueError("segment is missing itinerary identity fields")
            normalized.append(FlightSegment(
                id=segment.get("id"),
                airline=carrier.get("name", "Unknown"),
                flight_number=flight_number,
                origin=origin,
                destination=destination,
                departure_time=self._parse_datetime(segment["departing_at"]),
                arrival_time=self._parse_datetime(segment["arriving_at"]),
            ))
        return normalized

    def _extract_flight_number(self, segment: dict, carrier_code: Optional[str]) -> Optional[str]:
        provider_number = segment.get("marketing_carrier_flight_number") or segment.get("number")
        if not provider_number:
            return None
        provider_number = str(provider_number)
        if carrier_code and provider_number.upper().startswith(str(carrier_code).upper()):
            return provider_number
        return f"{carrier_code or ''}{provider_number}"

    def _extract_airport_code(self, airport: Optional[dict]) -> Optional[str]:
        if not airport:
            return None
        return airport.get("iata_code") or airport.get("airport", {}).get("iata_code")

    def _segment_identity(self, segment: FlightSegment) -> str:
        return "|".join((
            segment.airline, segment.flight_number, segment.origin,
            segment.destination, segment.departure_time.isoformat(),
            segment.arrival_time.isoformat(),
        ))

    def _slice_duration(self, segments: List[FlightSegment], slice_data: Optional[dict] = None) -> int:
        if slice_data and slice_data.get("duration"):
            try:
                duration = isodate.parse_duration(slice_data["duration"])
                return int(duration.total_seconds() / 60)
            except Exception:
                pass
        if not segments:
            return 0
        return int((segments[-1].arrival_time - segments[0].departure_time).total_seconds() / 60)

    def _build_flight(
        self,
        itinerary_id: str,
        outbound: List[FlightSegment],
        return_segments: Optional[List[FlightSegment]],
        price: float,
        currency: str,
        fare_option: FareOption,
    ) -> FlightResponse:
        return FlightResponse(
            id=itinerary_id,
            itinerary_id=itinerary_id,
            airline=", ".join(dict.fromkeys(segment.airline for segment in outbound)),
            flight_number=" / ".join(segment.flight_number for segment in outbound),
            origin=outbound[0].origin,
            destination=outbound[-1].destination,
            departure_time=outbound[0].departure_time,
            arrival_time=outbound[-1].arrival_time,
            duration=self._slice_duration(outbound),
            stops=len(outbound) - 1,
            price=price,
            currency=currency,
            segments=outbound,
            return_segments=return_segments or [],
            return_departure_time=return_segments[0].departure_time if return_segments else None,
            return_arrival_time=return_segments[-1].arrival_time if return_segments else None,
            return_duration=self._slice_duration(return_segments) if return_segments else None,
            return_stops=len(return_segments) - 1 if return_segments else None,
            fare_options=[fare_option],
        )

    def _parse_datetime(self, date_string: Optional[str]) -> datetime:
        """Parse datetime string from Duffel API."""
        if not date_string:
            return datetime.utcnow()
        try:
            # Handle various datetime formats from Duffel
            if date_string.endswith('Z'):
                date_string = date_string[:-1] + '+00:00'
            return datetime.fromisoformat(date_string)
        except Exception:
            return datetime.utcnow()

# Create a singleton instance
duffel_provider = DuffelProvider()

# Convenience function for external use
async def search_flights(request: FlightSearchRequest) -> List[FlightResponse]:
    """
    Search for flights using the configured provider.

    Args:
        request: Normalized flight search request.

    Returns:
        List of normalized flight responses.
    """
    return await duffel_provider.search_flights(request)