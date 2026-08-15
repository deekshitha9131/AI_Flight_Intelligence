"""
test_hotels.py
---------------
Integration tests for GET /api/v1/hotels/search.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestHotelSearch:
    async def test_search_hotels_success(self, client: AsyncClient) -> None:
        response = await client.get(
            "/api/v1/hotels/search",
            params={
                "destination": "DXB",
                "check_in_date": "2030-12-01",
                "check_out_date": "2030-12-05",
                "guests": 2,
                "rooms": 1,
            },
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["success"] is True
        assert data["count"] > 0
        hotels = data["data"]
        assert len(hotels) > 0
        first_hotel = hotels[0]
        assert "hotel_id" in first_hotel
        assert "name" in first_hotel
        assert "price_per_night" in first_hotel
        assert "total_price" in first_hotel
        assert "rating" in first_hotel
        assert "room_info" in first_hotel
        assert "amenities" in first_hotel

    async def test_search_hotels_invalid_dates_returns_400(self, client: AsyncClient) -> None:
        response = await client.get(
            "/api/v1/hotels/search",
            params={
                "destination": "HYD",
                "check_in_date": "2030-12-10",
                "check_out_date": "2030-12-05",
            },
        )
        assert response.status_code == 400
