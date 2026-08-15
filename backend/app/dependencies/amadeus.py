from __future__ import annotations

import inspect
from typing import Any

from app.core.config import get_settings
from app.integrations.amadeus.client import AmadeusClient
from app.integrations.providers.amadeus_provider import AmadeusProvider
from app.integrations.providers.base import FlightProvider
from app.integrations.providers.mock_provider import MockProvider
from fastapi import Request


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
    """Return the configured flight provider implementation (defaults to MockProvider)."""
    settings = get_settings()
    provider_name = settings.flight_provider.lower()

    overrides = getattr(request.app, "dependency_overrides", {})
    if get_flight_provider in overrides:
        return _resolve_override(overrides[get_flight_provider], request)

    if get_amadeus_client in overrides:
        client = _resolve_override(overrides[get_amadeus_client], request)
        if client is not None:
            return AmadeusProvider(client)
        return MockProvider()

    if provider_name == "amadeus":
        client = get_amadeus_client(request)
        if client is not None:
            return AmadeusProvider(client)

    return MockProvider()
