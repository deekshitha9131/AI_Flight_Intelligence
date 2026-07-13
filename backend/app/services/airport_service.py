from __future__ import annotations

import logging
from typing import Any

from app.exceptions.base import (
    ExternalAPIException,
    NotFoundException,
    ValidationException,
)
from app.integrations.amadeus.exceptions import (
    AmadeusConnectionException,
    AmadeusNotFoundException,
    AmadeusPermissionException,
    AmadeusRateLimitException,
    AmadeusServerException,
    AmadeusTimeoutException,
)
from app.repositories.airport_repository import AirportRepository
from app.schemas.airport import AirportResult

logger = logging.getLogger(__name__)


class AirportService:
    """Business logic for airport search and autocomplete.

    Responsibilities:
    - Validate the keyword before hitting the external API.
    - Delegate the raw API call to AirportRepository.
    - Transform the raw Amadeus payload into clean AirportResult models.
    - Map AmadeusException subclasses to AppException subclasses so the
      global exception handler can produce consistent error responses.
    - Raise NotFoundException when the API returns zero results.
    """

    def __init__(self, repository: AirportRepository) -> None:
        self._repository = repository

    async def search_airports(self, *, keyword: str) -> list[AirportResult]:
        """Search for airports matching the given keyword.

        Args:
            keyword: Free-text search term — IATA code, city name, or airport name.

        Returns:
            List of AirportResult objects ordered as returned by Amadeus.

        Raises:
            ValidationException:   keyword is blank after stripping whitespace.
            NotFoundException:     Amadeus returned zero matching airports.
            ExternalAPIException:  Any Amadeus API error (rate limit, server error, etc.).
        """
        cleaned = keyword.strip()
        if not cleaned:
            raise ValidationException(message="Search keyword must not be blank.")

        logger.info("AirportService.search_airports | keyword=%r", cleaned)

        try:
            raw = await self._repository.search(keyword=cleaned)
        except (AmadeusNotFoundException,):
            raise NotFoundException(message=f"No airports found for '{cleaned}'.")
        except AmadeusRateLimitException as exc:
            logger.warning("Amadeus rate limit hit during airport search.")
            raise ExternalAPIException(
                message="Airport search is temporarily unavailable due to rate limiting. Please try again shortly."
            ) from exc
        except (AmadeusTimeoutException, AmadeusConnectionException) as exc:
            logger.error("Amadeus connectivity issue during airport search: %s", exc)
            raise ExternalAPIException(
                message="Airport search service is temporarily unreachable."
            ) from exc
        except AmadeusPermissionException as exc:
            logger.error("Amadeus permission denied during airport search.")
            raise ExternalAPIException(
                message="Airport search is not available with the current API credentials."
            ) from exc
        except AmadeusServerException as exc:
            logger.error("Amadeus server error during airport search: %s", exc)
            raise ExternalAPIException(
                message="Airport search service encountered an unexpected error."
            ) from exc

        results = _transform(raw)

        if not results:
            raise NotFoundException(message=f"No airports found for '{cleaned}'.")

        logger.info(
            "AirportService.search_airports | keyword=%r returned %d result(s).",
            cleaned,
            len(results),
        )
        return results


# ---------------------------------------------------------------------------
# Transformation helpers — kept private; only the service uses them
# ---------------------------------------------------------------------------


def _transform(raw: dict[str, Any]) -> list[AirportResult]:
    """Convert a raw Amadeus location response into a list of AirportResult models."""
    entries: list[Any] = raw.get("data", [])
    results: list[AirportResult] = []

    for entry in entries:
        result = _parse_entry(entry)
        if result is not None:
            results.append(result)

    return results


def _parse_entry(entry: dict[str, Any]) -> AirportResult | None:
    """Parse a single Amadeus location entry into an AirportResult.

    Returns None and logs a warning if the entry is missing required fields,
    so one malformed record never breaks the entire response.
    """
    try:
        iata_code: str = entry.get("iataCode", "").strip()
        if not iata_code:
            return None

        name: str = entry.get("name", "").strip() or iata_code
        address: dict[str, Any] = entry.get("address", {})
        city: str = (
            address.get("cityName", "").strip() or address.get("cityCode", "").strip()
        )
        country: str = (
            address.get("countryName", "").strip()
            or address.get("countryCode", "").strip()
        )

        geo: dict[str, Any] = entry.get("geoCode", {})
        latitude: float | None = _safe_float(geo.get("latitude"))
        longitude: float | None = _safe_float(geo.get("longitude"))

        return AirportResult(
            airport_code=iata_code,
            airport_name=name,
            city=city,
            country=country,
            iata_code=iata_code,
            latitude=latitude,
            longitude=longitude,
        )
    except Exception:
        logger.warning("Failed to parse Amadeus airport entry: %r", entry)
        return None


def _safe_float(value: Any) -> float | None:
    """Coerce a value to float, returning None if conversion fails."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
