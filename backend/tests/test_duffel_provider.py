from __future__ import annotations

from datetime import date
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import get_settings
from app.integrations.amadeus.exceptions import (
    AmadeusAuthException,
    AmadeusConnectionException,
    AmadeusNotFoundException,
    AmadeusRateLimitException,
    AmadeusServerException,
    AmadeusTimeoutException,
)
from app.integrations.providers.duffel_provider import DuffelProvider
from app.schemas.flight import FlightSearchParams, TravelClass
import httpx

pytestmark = pytest.mark.asyncio


@pytest.fixture
def valid_params() -> FlightSearchParams:
    return FlightSearchParams(
        origin="HYD",
        destination="BOM",
        departure_date=date(2026, 9, 1),
        adults=1,
        travel_class=TravelClass.ECONOMY,
        currency="INR",
    )


@pytest.fixture
def mock_duffel_response() -> dict[str, Any]:
    return {
        "data": {
            "id": "orq_00001",
            "offers": [
                {
                    "id": "off_00001",
                    "total_amount": "4500.00",
                    "total_currency": "INR",
                    "owner": {"iata_code": "6E", "name": "IndiGo"},
                    "slices": [
                        {
                            "duration": "PT1H30M",
                            "origin": {"iata_code": "HYD", "name": "Rajiv Gandhi Intl"},
                            "destination": {"iata_code": "BOM", "name": "Chhatrapati Shivaji Intl"},
                            "segments": [
                                {
                                    "id": "seg_1",
                                    "origin": {"iata_code": "HYD"},
                                    "destination": {"iata_code": "BOM"},
                                    "departing_at": "2026-09-01T08:00:00",
                                    "arriving_at": "2026-09-01T09:30:00",
                                    "operating_carrier": {"iata_code": "6E", "name": "IndiGo"},
                                    "marketing_carrier": {"iata_code": "6E", "name": "IndiGo"},
                                    "marketing_carrier_flight_number": "6E501",
                                    "duration": "PT1H30M",
                                    "aircraft": {"iata_code": "320", "name": "Airbus A320"},
                                    "passengers": [{"cabin_class": "economy"}],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    }


@pytest.fixture
def mock_duffel_connecting_response() -> dict[str, Any]:
    return {
        "data": {
            "id": "orq_00002",
            "offers": [
                {
                    "id": "off_00002",
                    "total_amount": "550.00",
                    "total_currency": "USD",
                    "owner": {"iata_code": "EK", "name": "Emirates"},
                    "slices": [
                        {
                            "duration": "PT8H45M",
                            "origin": {"iata_code": "HYD"},
                            "destination": {"iata_code": "LHR"},
                            "segments": [
                                {
                                    "id": "seg_10",
                                    "origin": {"iata_code": "HYD"},
                                    "destination": {"iata_code": "DXB"},
                                    "departing_at": "2026-09-01T04:00:00",
                                    "arriving_at": "2026-09-01T07:30:00",
                                    "marketing_carrier": {"iata_code": "EK", "name": "Emirates"},
                                    "marketing_carrier_flight_number": "EK527",
                                    "duration": "PT4H00M",
                                    "aircraft": {"iata_code": "77W", "name": "Boeing 777-300ER"},
                                    "passengers": [{"cabin_class": "business"}],
                                },
                                {
                                    "id": "seg_11",
                                    "origin": {"iata_code": "DXB"},
                                    "destination": {"iata_code": "LHR"},
                                    "departing_at": "2026-09-01T09:30:00",
                                    "arriving_at": "2026-09-01T14:15:00",
                                    "marketing_carrier": {"iata_code": "EK", "name": "Emirates"},
                                    "marketing_carrier_flight_number": "EK001",
                                    "duration": "PT4H45M",
                                    "aircraft": {"iata_code": "388", "name": "Airbus A380-800"},
                                    "passengers": [{"cabin_class": "business"}],
                                },
                            ],
                        }
                    ],
                }
            ],
        }
    }


class TestDuffelProvider:
    async def test_search_flights_success(
        self, valid_params: FlightSearchParams, mock_duffel_response: dict[str, Any]
    ) -> None:
        provider = DuffelProvider(api_token="test_token")
        mock_res = httpx.Response(201, json=mock_duffel_response)

        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_res):
            result = await provider.search_flights(valid_params)

        assert "data" in result
        assert "dictionaries" in result
        assert len(result["data"]) == 1

        offer = result["data"][0]
        assert offer["id"] == "off_00001"
        assert offer["price"]["grandTotal"] == "4500.00"
        assert offer["price"]["currency"] == "INR"
        assert len(offer["itineraries"]) == 1
        assert len(offer["itineraries"][0]["segments"]) == 1

        seg = offer["itineraries"][0]["segments"][0]
        assert seg["departure"]["iataCode"] == "HYD"
        assert seg["arrival"]["iataCode"] == "BOM"
        assert seg["carrierCode"] == "6E"
        assert seg["number"] == "6E501"

    async def test_search_flights_connecting_segments(
        self, mock_duffel_connecting_response: dict[str, Any]
    ) -> None:
        params = FlightSearchParams(
            origin="HYD",
            destination="LHR",
            departure_date=date(2026, 9, 1),
            adults=1,
            travel_class=TravelClass.BUSINESS,
            currency="USD",
        )
        provider = DuffelProvider(api_token="test_token")
        mock_res = httpx.Response(201, json=mock_duffel_connecting_response)

        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_res):
            result = await provider.search_flights(params)

        assert len(result["data"]) == 1
        offer = result["data"][0]
        assert offer["id"] == "off_00002"
        assert offer["price"]["currency"] == "USD"
        segments = offer["itineraries"][0]["segments"]
        assert len(segments) == 2
        assert segments[0]["departure"]["iataCode"] == "HYD"
        assert segments[0]["arrival"]["iataCode"] == "DXB"
        assert segments[1]["departure"]["iataCode"] == "DXB"
        assert segments[1]["arrival"]["iataCode"] == "LHR"

    async def test_missing_api_token_raises_auth_exception(
        self, valid_params: FlightSearchParams
    ) -> None:
        provider = DuffelProvider(api_token="")
        with pytest.raises(AmadeusAuthException):
            await provider.search_flights(valid_params)

    async def test_http_401_raises_auth_exception(
        self, valid_params: FlightSearchParams
    ) -> None:
        provider = DuffelProvider(api_token="bad_token")
        mock_res = httpx.Response(401, json={"errors": [{"message": "Unauthorized"}]})

        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_res):
            with pytest.raises(AmadeusAuthException):
                await provider.search_flights(valid_params)

    async def test_http_429_raises_rate_limit_exception(
        self, valid_params: FlightSearchParams
    ) -> None:
        provider = DuffelProvider(api_token="test_token")
        mock_res = httpx.Response(429, json={"errors": [{"message": "Rate limit exceeded"}]})

        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_res):
            with pytest.raises(AmadeusRateLimitException):
                await provider.search_flights(valid_params)

    async def test_timeout_raises_timeout_exception(
        self, valid_params: FlightSearchParams
    ) -> None:
        provider = DuffelProvider(api_token="test_token")

        with patch.object(
            httpx.AsyncClient, "post", new_callable=AsyncMock, side_effect=httpx.TimeoutException("Timeout")
        ):
            with pytest.raises(AmadeusTimeoutException):
                await provider.search_flights(valid_params)

    async def test_connection_error_raises_connection_exception(
        self, valid_params: FlightSearchParams
    ) -> None:
        provider = DuffelProvider(api_token="test_token")

        with patch.object(
            httpx.AsyncClient, "post", new_callable=AsyncMock, side_effect=httpx.RequestError("Conn error")
        ):
            with pytest.raises(AmadeusConnectionException):
                await provider.search_flights(valid_params)

    async def test_zero_offers_returns_empty_data(
        self, valid_params: FlightSearchParams
    ) -> None:
        provider = DuffelProvider(api_token="test_token")
        mock_res = httpx.Response(201, json={"data": {"offers": []}})

        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_res):
            result = await provider.search_flights(valid_params)

        assert result["data"] == []
