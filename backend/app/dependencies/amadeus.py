from __future__ import annotations

import inspect
import logging
from typing import Any

from app.core.config import get_settings
from app.integrations.amadeus.client import AmadeusClient
from app.integrations.providers.amadeus_provider import AmadeusProvider
from app.integrations.providers.base import FlightProvider
from app.integrations.providers.duffel_provider import DuffelProvider
from fastapi import Request

logger = logging.getLogger(__name__)


def get_amadeus_client(request: Request) -> AmadeusClient:
    """Return the shared AmadeusClient stored on application state."""
    return getattr(request.app.state, "amadeus", None)


def _resolve_override(override: Any, request: Request) -> Any:
    """Call an override with or without a request argument."""
    try:
        signature = inspect.signature(override)
    except (TypeError, ValueError):
        return override(request)

    if len(signature.parameters) == 0:
        return override()
    return override(request)


def get_flight_provider(request: Request) -> FlightProvider:
    """Return the configured flight provider implementation.

    Provider resolution order:
    1. Dependency overrides (for tests).
    2. Explicit ``FLIGHT_PROVIDER`` setting (``duffel`` or ``amadeus``).
    3. Duffel token presence as implicit selection.
    4. RuntimeError if no provider can be resolved — NO silent mock fallback.
    """
    settings = get_settings()
    provider_name = settings.flight_provider.lower()

    overrides = getattr(request.app, "dependency_overrides", {})
    if get_flight_provider in overrides:
        return _resolve_override(overrides[get_flight_provider], request)

    if get_amadeus_client in overrides:
        client = _resolve_override(overrides[get_amadeus_client], request)
        if client is not None:
            return AmadeusProvider(client)

    if provider_name == "duffel":
        return DuffelProvider()

    if provider_name == "amadeus":
        client = get_amadeus_client(request)
        if client is not None:
            return AmadeusProvider(client)
        logger.error("FLIGHT_PROVIDER is 'amadeus' but no AmadeusClient is available.")
        raise RuntimeError(
            "Flight provider is set to 'amadeus' but the Amadeus client is not initialised. "
            "Check AMADEUS_API_KEY / AMADEUS_API_SECRET configuration."
        )

    # Implicit fallback: if a Duffel token is available, use Duffel.
    if settings.duffel_token:
        return DuffelProvider()

    raise RuntimeError(
        f"Cannot resolve flight provider (FLIGHT_PROVIDER={settings.flight_provider!r}). "
        "Set FLIGHT_PROVIDER=duffel and provide DUFFEL_ACCESS_TOKEN."
    )

