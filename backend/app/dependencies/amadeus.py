from __future__ import annotations

from app.integrations.amadeus.client import AmadeusClient
from fastapi import Request


def get_amadeus_client(request: Request) -> AmadeusClient:
    """Return the shared AmadeusClient stored on application state."""
    return getattr(request.app.state, "amadeus", None)
