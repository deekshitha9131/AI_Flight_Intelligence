"""
test_favorites.py
-----------------
Integration tests for the favourite flights endpoints:

  POST   /api/v1/flights/favorites
  GET    /api/v1/flights/favorites
  DELETE /api/v1/flights/favorites/{id}
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAVORITE_PAYLOAD: dict[str, Any] = {
    "flight_offer_id": "offer-abc-123",
    "airline": "EK",
    "origin": "HYD",
    "destination": "DXB",
    "departure": "2025-12-01T10:30:00",
    "arrival": "2025-12-01T12:45:00",
    "price": 299.99,
    "currency": "USD",
}


async def _save_favorite(
    client: AsyncClient,
    headers: dict,
    payload: dict | None = None,
) -> dict[str, Any]:
    """Helper: POST a favourite and return the response body."""
    response = await client.post(
        "/api/v1/flights/favorites",
        json=payload or _FAVORITE_PAYLOAD,
        headers=headers,
    )
    return response


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


class TestFavoritesAuth:
    async def test_save_without_token_returns_401(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/flights/favorites", json=_FAVORITE_PAYLOAD
        )
        assert response.status_code == 401

    async def test_list_without_token_returns_401(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/flights/favorites")
        assert response.status_code == 401

    async def test_delete_without_token_returns_401(self, client: AsyncClient) -> None:
        import uuid

        response = await client.delete(f"/api/v1/flights/favorites/{uuid.uuid4()}")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Save favourite
# ---------------------------------------------------------------------------


class TestSaveFavorite:
    async def test_save_returns_201(
        self, client: AsyncClient, auth_headers: dict, registered_user
    ) -> None:
        response = await _save_favorite(client, auth_headers)
        assert response.status_code == 201

    async def test_save_response_shape(
        self, client: AsyncClient, auth_headers: dict, registered_user
    ) -> None:
        response = await _save_favorite(client, auth_headers)
        body = response.json()

        assert body["success"] is True
        data = body["data"]
        assert data["flight_offer_id"] == _FAVORITE_PAYLOAD["flight_offer_id"]
        assert data["airline"] == "EK"
        assert data["origin"] == "HYD"
        assert data["destination"] == "DXB"
        assert data["price"] == 299.99
        assert data["currency"] == "USD"
        assert "id" in data
        assert "created_at" in data

    async def test_duplicate_save_returns_409(
        self, client: AsyncClient, auth_headers: dict, registered_user
    ) -> None:
        await _save_favorite(client, auth_headers)
        response = await _save_favorite(client, auth_headers)
        assert response.status_code == 409

    async def test_save_different_offers_both_succeed(
        self, client: AsyncClient, auth_headers: dict, registered_user
    ) -> None:
        r1 = await _save_favorite(client, auth_headers)
        r2 = await _save_favorite(
            client,
            auth_headers,
            {**_FAVORITE_PAYLOAD, "flight_offer_id": "offer-xyz-999"},
        )
        assert r1.status_code == 201
        assert r2.status_code == 201

    async def test_save_missing_required_field_returns_422(
        self, client: AsyncClient, auth_headers: dict, registered_user
    ) -> None:
        payload = {k: v for k, v in _FAVORITE_PAYLOAD.items() if k != "airline"}
        response = await client.post(
            "/api/v1/flights/favorites", json=payload, headers=auth_headers
        )
        assert response.status_code == 422

    async def test_save_negative_price_returns_422(
        self, client: AsyncClient, auth_headers: dict, registered_user
    ) -> None:
        response = await client.post(
            "/api/v1/flights/favorites",
            json={**_FAVORITE_PAYLOAD, "price": -10.0},
            headers=auth_headers,
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# List favourites
# ---------------------------------------------------------------------------


class TestListFavorites:
    async def test_empty_list_returns_200(
        self, client: AsyncClient, auth_headers: dict, registered_user
    ) -> None:
        response = await client.get("/api/v1/flights/favorites", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"] == []
        assert body["count"] == 0

    async def test_saved_favorite_appears_in_list(
        self, client: AsyncClient, auth_headers: dict, registered_user
    ) -> None:
        await _save_favorite(client, auth_headers)
        response = await client.get("/api/v1/flights/favorites", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 1
        assert (
            body["data"][0]["flight_offer_id"] == _FAVORITE_PAYLOAD["flight_offer_id"]
        )

    async def test_pagination_page_size(
        self, client: AsyncClient, auth_headers: dict, registered_user
    ) -> None:
        for i in range(3):
            await _save_favorite(
                client,
                auth_headers,
                {**_FAVORITE_PAYLOAD, "flight_offer_id": f"offer-{i}"},
            )

        response = await client.get(
            "/api/v1/flights/favorites",
            params={"page": 1, "page_size": 2},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert len(response.json()["data"]) == 2


# ---------------------------------------------------------------------------
# Delete favourite
# ---------------------------------------------------------------------------


class TestDeleteFavorite:
    async def test_delete_returns_200(
        self, client: AsyncClient, auth_headers: dict, registered_user
    ) -> None:
        save_resp = await _save_favorite(client, auth_headers)
        record_id = save_resp.json()["data"]["id"]

        response = await client.delete(
            f"/api/v1/flights/favorites/{record_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    async def test_deleted_favorite_not_in_list(
        self, client: AsyncClient, auth_headers: dict, registered_user
    ) -> None:
        save_resp = await _save_favorite(client, auth_headers)
        record_id = save_resp.json()["data"]["id"]

        await client.delete(
            f"/api/v1/flights/favorites/{record_id}", headers=auth_headers
        )

        list_resp = await client.get("/api/v1/flights/favorites", headers=auth_headers)
        assert list_resp.json()["count"] == 0

    async def test_delete_nonexistent_returns_404(
        self, client: AsyncClient, auth_headers: dict, registered_user
    ) -> None:
        import uuid

        response = await client.delete(
            f"/api/v1/flights/favorites/{uuid.uuid4()}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_cannot_delete_another_users_favorite(
        self,
        client: AsyncClient,
        auth_headers: dict,
        registered_user,
        user_payload,
    ) -> None:
        # Save a favourite as user A
        save_resp = await _save_favorite(client, auth_headers)
        record_id = save_resp.json()["data"]["id"]

        # Register and log in as user B
        await client.post(
            "/api/v1/auth/register",
            json=user_payload(email="user_b@example.com"),
        )
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "user_b@example.com", "password": "Secure@123"},
        )
        token_b = login_resp.json()["data"]["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # User B tries to delete user A's favourite
        response = await client.delete(
            f"/api/v1/flights/favorites/{record_id}",
            headers=headers_b,
        )
        assert response.status_code == 404
