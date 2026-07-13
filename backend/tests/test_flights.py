"""
test_flights.py
---------------
Integration tests for GET /api/v1/flights/search.

All Amadeus API calls are intercepted by overriding the AmadeusClient
dependency — no real HTTP requests are made.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from app.dependencies.amadeus import get_amadeus_client
from app.integrations.amadeus.exceptions import (
    AmadeusNotFoundException,
    AmadeusRateLimitException,
)

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_AMADEUS_FLIGHT_RESPONSE: dict[str, Any] = {
    "data": [
        {
            "id": "offer-1",
            "itineraries": [
                {
                    "duration": "PT2H15M",
                    "segments": [
                        {
                            "departure": {
                                "iataCode": "HYD",
                                "at": "2030-12-01T10:30:00",
                            },
                            "arrival": {"iataCode": "DXB", "at": "2030-12-01T12:45:00"},
                            "carrierCode": "EK",
                            "number": "512",
                            "duration": "PT2H15M",
                            "aircraft": {"code": "77W"},
                        }
                    ],
                }
            ],
            "price": {"grandTotal": "299.99", "currency": "USD"},
            "travelerPricings": [
                {
                    "travelerType": "ADULT",
                    "price": {"total": "299.99"},
                    "fareDetailsBySegment": [{"cabin": "ECONOMY"}],
                }
            ],
            "numberOfBookableSeats": 5,
        }
    ],
    "dictionaries": {
        "carriers": {"EK": "Emirates"},
        "aircraft": {"77W": "Boeing 777-300ER"},
    },
}

_EMPTY_AMADEUS_RESPONSE: dict[str, Any] = {"data": [], "dictionaries": {}}


def _mock_amadeus(response: dict[str, Any]):
    """Return a mock AmadeusClient whose request() returns the given response."""
    client = MagicMock()
    client.request = AsyncMock(return_value=response)
    return client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFlightSearchValidation:
    async def test_missing_origin_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        response = await client.get(
            "/api/v1/flights/search",
            params={"destination": "DXB", "departure_date": "2030-05-01"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_invalid_iata_code_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        response = await client.get(
            "/api/v1/flights/search",
            params={
                "origin": "INVALID",
                "destination": "DXB",
                "departure_date": "2030-12-01",
            },
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_past_departure_date_returns_400(
        self, client: AsyncClient, auth_headers: dict, app
    ) -> None:
        mock = _mock_amadeus(_AMADEUS_FLIGHT_RESPONSE)
        app.dependency_overrides[get_amadeus_client] = lambda: mock

        response = await client.get(
            "/api/v1/flights/search",
            params={
                "origin": "HYD",
                "destination": "DXB",
                "departure_date": "2020-01-01",
            },
            headers=auth_headers,
        )
        app.dependency_overrides.pop(get_amadeus_client, None)
        assert response.status_code == 400

    async def test_return_date_before_departure_returns_400(
        self, client: AsyncClient, auth_headers: dict, app
    ) -> None:
        mock = _mock_amadeus(_AMADEUS_FLIGHT_RESPONSE)
        app.dependency_overrides[get_amadeus_client] = lambda: mock

        response = await client.get(
            "/api/v1/flights/search",
            params={
                "origin": "HYD",
                "destination": "DXB",
                "departure_date": "2030-12-10",
                "return_date": "2030-12-01",
            },
            headers=auth_headers,
        )
        app.dependency_overrides.pop(get_amadeus_client, None)
        assert response.status_code == 400

    async def test_same_origin_destination_returns_400(
        self, client: AsyncClient, auth_headers: dict, app
    ) -> None:
        mock = _mock_amadeus(_AMADEUS_FLIGHT_RESPONSE)
        app.dependency_overrides[get_amadeus_client] = lambda: mock

        response = await client.get(
            "/api/v1/flights/search",
            params={
                "origin": "HYD",
                "destination": "HYD",
                "departure_date": "2030-12-01",
            },
            headers=auth_headers,
        )
        app.dependency_overrides.pop(get_amadeus_client, None)
        assert response.status_code == 400

    async def test_unauthenticated_returns_401(self, client: AsyncClient) -> None:
        response = await client.get(
            "/api/v1/flights/search",
            params={
                "origin": "HYD",
                "destination": "DXB",
                "departure_date": "2030-12-01",
            },
        )
        assert response.status_code == 401


class TestFlightSearchSuccess:
    async def test_successful_search_returns_200(
        self, client: AsyncClient, auth_headers: dict, app
    ) -> None:
        mock = _mock_amadeus(_AMADEUS_FLIGHT_RESPONSE)
        app.dependency_overrides[get_amadeus_client] = lambda: mock

        response = await client.get(
            "/api/v1/flights/search",
            params={
                "origin": "HYD",
                "destination": "DXB",
                "departure_date": "2030-12-01",
            },
            headers=auth_headers,
        )
        app.dependency_overrides.pop(get_amadeus_client, None)

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["count"] == 1
        assert len(body["data"]) == 1

    async def test_response_shape(
        self, client: AsyncClient, auth_headers: dict, app
    ) -> None:
        mock = _mock_amadeus(_AMADEUS_FLIGHT_RESPONSE)
        app.dependency_overrides[get_amadeus_client] = lambda: mock

        response = await client.get(
            "/api/v1/flights/search",
            params={
                "origin": "HYD",
                "destination": "DXB",
                "departure_date": "2030-12-01",
            },
            headers=auth_headers,
        )
        app.dependency_overrides.pop(get_amadeus_client, None)

        flight = response.json()["data"][0]
        assert flight["flight_id"] == "offer-1"
        assert flight["origin"] == "HYD"
        assert flight["destination"] == "DXB"
        assert flight["price"] == 299.99
        assert flight["currency"] == "USD"
        assert flight["stops"] == 0
        assert "search_id" in response.json()

    async def test_no_flights_returns_404(
        self, client: AsyncClient, auth_headers: dict, app
    ) -> None:
        mock = _mock_amadeus(_EMPTY_AMADEUS_RESPONSE)
        app.dependency_overrides[get_amadeus_client] = lambda: mock

        response = await client.get(
            "/api/v1/flights/search",
            params={
                "origin": "HYD",
                "destination": "DXB",
                "departure_date": "2030-12-01",
            },
            headers=auth_headers,
        )
        app.dependency_overrides.pop(get_amadeus_client, None)
        assert response.status_code == 404

    async def test_amadeus_rate_limit_returns_502(
        self, client: AsyncClient, auth_headers: dict, app
    ) -> None:
        mock = MagicMock()
        mock.request = AsyncMock(side_effect=AmadeusRateLimitException())
        app.dependency_overrides[get_amadeus_client] = lambda: mock

        response = await client.get(
            "/api/v1/flights/search",
            params={
                "origin": "HYD",
                "destination": "DXB",
                "departure_date": "2030-12-01",
            },
            headers=auth_headers,
        )
        app.dependency_overrides.pop(get_amadeus_client, None)
        assert response.status_code == 502

    async def test_lowercase_iata_is_normalised(
        self, client: AsyncClient, auth_headers: dict, app
    ) -> None:
        mock = _mock_amadeus(_AMADEUS_FLIGHT_RESPONSE)
        app.dependency_overrides[get_amadeus_client] = lambda: mock

        response = await client.get(
            "/api/v1/flights/search",
            params={
                "origin": "hyd",
                "destination": "dxb",
                "departure_date": "2030-12-01",
            },
            headers=auth_headers,
        )
        app.dependency_overrides.pop(get_amadeus_client, None)
        assert response.status_code == 200
