from __future__ import annotations

import pytest
from app.repositories.airport_repository import AirportRepository
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestAirportRepository:
    async def test_search_by_iata_code(self) -> None:
        repo = AirportRepository(client=None)
        res = await repo.search(keyword="HYD")
        data = res.get("data", [])
        assert len(data) >= 1
        assert data[0]["iataCode"] == "HYD"
        assert data[0]["address"]["cityName"] == "Hyderabad"

    async def test_search_by_city(self) -> None:
        repo = AirportRepository(client=None)
        res = await repo.search(keyword="Mumbai")
        data = res.get("data", [])
        assert len(data) >= 1
        assert any(item["iataCode"] == "BOM" for item in data)

    async def test_search_by_airport_name(self) -> None:
        repo = AirportRepository(client=None)
        res = await repo.search(keyword="Heathrow")
        data = res.get("data", [])
        assert len(data) >= 1
        assert any(item["iataCode"] == "LHR" for item in data)

    async def test_case_insensitive_search(self) -> None:
        repo = AirportRepository(client=None)
        res1 = await repo.search(keyword="hyd")
        res2 = await repo.search(keyword="HYD")
        assert res1["data"] == res2["data"]

    async def test_unknown_three_letter_code_returns_no_fabricated_airport(self) -> None:
        """Verify that searching an unknown 3-letter code like 'XYZ' or 'ABC' returns NO fabricated airport."""
        repo = AirportRepository(client=None)
        res_xyz = await repo.search(keyword="XYZ")
        assert res_xyz.get("data") == []

        res_abc = await repo.search(keyword="ABC")
        assert res_abc.get("data") == []

        res_aaa = await repo.search(keyword="AAA")
        assert res_aaa.get("data") == []


class TestAirportEndpoint:
    async def test_api_airport_search_success(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/airports/search", params={"keyword": "HYD"})
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["count"] >= 1
        assert body["data"][0]["iata_code"] == "HYD"

    async def test_api_airport_search_unknown_code_returns_404(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/airports/search", params={"keyword": "XYZ"})
        assert response.status_code == 404

    async def test_api_airport_search_short_keyword_returns_422(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/airports/search", params={"keyword": "a"})
        assert response.status_code == 422
