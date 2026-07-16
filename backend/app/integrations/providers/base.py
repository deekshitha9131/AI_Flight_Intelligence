from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.schemas.flight import FlightSearchParams


class FlightProvider(ABC):
    """Abstract provider interface for flight search backends."""

    @abstractmethod
    async def search_flights(self, params: FlightSearchParams) -> dict[str, Any]:
        """Execute a flight search and return the raw provider response."""
        raise NotImplementedError
