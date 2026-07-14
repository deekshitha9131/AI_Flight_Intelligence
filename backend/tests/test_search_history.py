"""
test_search_history.py
----------------------
Integration tests for the search history endpoints:

  GET    /api/v1/flights/history
  GET    /api/v1/flights/history/{id}
  DELETE /api/v1/flights/history/{id}
  DELETE /api/v1/flights/history
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import pytest
from app.models.flight_search import FlightSearch
from sqlalchemy.orm import Session

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _insert_history(db: Session, user_id: Any, **overrides: Any) -> FlightSearch:
    """Directly insert a FlightSearch row for test setup."""
    record = FlightSearch(
        user_id=user_id,
        origin=overrides.get("origin", "HYD"),
        destination=overrides.get("destination", "DXB"),
        departure_date=overrides.get("departure_date", "2025-12-01"),
        return_date=overrides.get("return_date", None),
        adults=overrides.get("adults", 1),
        children=overrides.get("children", 0),
        infants=overrides.get("infants", 0),
        travel_class=overrides.get("travel_class", "ECONOMY"),
        currency=overrides.get("currency", "USD"),
        non_stop=overrides.get("non_stop", False),
        max_results=overrides.get("max_results", 10),
        result_count=overrides.get("result_count", 5),
        searched_at=overrides.get("searched_at", datetime.now(timezone.utc)),
    )
    db.add(record)
    db.flush()
    return record


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


class TestSearchHistoryAuth:
    async def test_list_without_token_returns_401(self, client) -> None:
        response = await client.get("/api/v1/flights/history")
        assert response.status_code == 401

    async def test_get_by_id_without_token_returns_401(self, client) -> None:
        response = await client.get(f"/api/v1/flights/history/{uuid.uuid4()}")
        assert response.status_code == 401

    async def test_delete_without_token_returns_401(self, client) -> None:
        response = await client.delete(f"/api/v1/flights/history/{uuid.uuid4()}")
        assert response.status_code == 401

    async def test_clear_without_token_returns_401(self, client) -> None:
        response = await client.delete("/api/v1/flights/history")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# List history
# ---------------------------------------------------------------------------


class TestListSearchHistory:
    async def test_empty_history_returns_200(
        self, client, auth_headers, registered_user
    ) -> None:
        response = await client.get("/api/v1/flights/history", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"] == []
        assert body["pagination"]["total_items"] == 0

    async def test_inserted_record_appears_in_list(
        self, client, auth_headers, registered_user, db_session
    ) -> None:
        _insert_history(db_session, user_id=uuid.UUID(registered_user["id"]))

        response = await client.get("/api/v1/flights/history", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["pagination"]["total_items"] == 1
        assert body["data"][0]["origin"] == "HYD"

    async def test_pagination_meta_is_correct(
        self, client, auth_headers, registered_user, db_session
    ) -> None:
        uid = uuid.UUID(registered_user["id"])
        for i in range(5):
            _insert_history(db_session, user_id=uid, origin=f"H{i:02d}"[:3])

        response = await client.get(
            "/api/v1/flights/history",
            params={"page": 1, "page_size": 2},
            headers=auth_headers,
        )
        assert response.status_code == 200
        pagination = response.json()["pagination"]
        assert pagination["page"] == 1
        assert pagination["page_size"] == 2
        assert pagination["total_items"] == 5
        assert pagination["total_pages"] == 3
        assert pagination["has_next"] is True
        assert pagination["has_previous"] is False

    async def test_sorted_newest_first(
        self, client, auth_headers, registered_user, db_session
    ) -> None:
        from datetime import timedelta

        uid = uuid.UUID(registered_user["id"])
        now = datetime.now(timezone.utc)
        _insert_history(
            db_session, user_id=uid, origin="AAA", searched_at=now - timedelta(hours=2)
        )
        _insert_history(db_session, user_id=uid, origin="BBB", searched_at=now)

        response = await client.get("/api/v1/flights/history", headers=auth_headers)
        data = response.json()["data"]
        assert data[0]["origin"] == "BBB"
        assert data[1]["origin"] == "AAA"

    async def test_other_users_history_not_visible(
        self,
        client,
        auth_headers,
        registered_user,
        another_registered_user,
        db_session,
    ) -> None:
        # Insert history for a different (non-existent) user UUID
        _insert_history(
            db_session,
            user_id=uuid.UUID(another_registered_user["id"]),
        )

        response = await client.get("/api/v1/flights/history", headers=auth_headers)
        assert response.json()["pagination"]["total_items"] == 0


# ---------------------------------------------------------------------------
# Get by ID
# ---------------------------------------------------------------------------


class TestGetSearchHistoryById:
    async def test_get_own_record_returns_200(
        self, client, auth_headers, registered_user, db_session
    ) -> None:
        record = _insert_history(db_session, user_id=uuid.UUID(registered_user["id"]))

        response = await client.get(
            f"/api/v1/flights/history/{record.id}", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["data"]["id"] == str(record.id)

    async def test_get_nonexistent_returns_404(
        self, client, auth_headers, registered_user
    ) -> None:
        response = await client.get(
            f"/api/v1/flights/history/{uuid.uuid4()}", headers=auth_headers
        )
        assert response.status_code == 404

    async def test_cannot_access_other_users_record(
        self,
        client,
        auth_headers,
        registered_user,
        another_registered_user,
        db_session,
    ) -> None:
        record = _insert_history(
            db_session,
            user_id=uuid.UUID(another_registered_user["id"]),
        )

        response = await client.get(
            f"/api/v1/flights/history/{record.id}", headers=auth_headers
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Delete one
# ---------------------------------------------------------------------------


class TestDeleteSearchHistoryRecord:
    async def test_delete_own_record_returns_200(
        self, client, auth_headers, registered_user, db_session
    ) -> None:
        record = _insert_history(db_session, user_id=uuid.UUID(registered_user["id"]))

        response = await client.delete(
            f"/api/v1/flights/history/{record.id}", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    async def test_deleted_record_not_in_list(
        self, client, auth_headers, registered_user, db_session
    ) -> None:
        record = _insert_history(db_session, user_id=uuid.UUID(registered_user["id"]))
        await client.delete(
            f"/api/v1/flights/history/{record.id}", headers=auth_headers
        )

        response = await client.get("/api/v1/flights/history", headers=auth_headers)
        assert response.json()["pagination"]["total_items"] == 0

    async def test_delete_nonexistent_returns_404(
        self, client, auth_headers, registered_user
    ) -> None:
        response = await client.delete(
            f"/api/v1/flights/history/{uuid.uuid4()}", headers=auth_headers
        )
        assert response.status_code == 404

    async def test_cannot_delete_other_users_record(
        self,
        client,
        auth_headers,
        registered_user,
        another_registered_user,
        db_session,
    ) -> None:
        record = _insert_history(
            db_session,
            user_id=uuid.UUID(another_registered_user["id"]),
        )

        response = await client.delete(
            f"/api/v1/flights/history/{record.id}", headers=auth_headers
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Clear all
# ---------------------------------------------------------------------------


class TestClearSearchHistory:
    async def test_clear_empty_history_is_idempotent(
        self, client, auth_headers, registered_user
    ) -> None:
        response = await client.delete("/api/v1/flights/history", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["success"] is True

    async def test_clear_removes_all_records(
        self, client, auth_headers, registered_user, db_session
    ) -> None:
        uid = uuid.UUID(registered_user["id"])
        for _ in range(3):
            _insert_history(db_session, user_id=uid)

        await client.delete("/api/v1/flights/history", headers=auth_headers)

        response = await client.get("/api/v1/flights/history", headers=auth_headers)
        assert response.json()["pagination"]["total_items"] == 0

    async def test_clear_only_affects_current_user(
        self,
        client,
        auth_headers,
        registered_user,
        another_registered_user,
        db_session,
    ) -> None:
        other_uid = uuid.UUID(another_registered_user["id"])
        _insert_history(
            db_session,
            user_id=uuid.UUID(another_registered_user["id"]),
        )

        await client.delete("/api/v1/flights/history", headers=auth_headers)

        # The other user's record must still exist
        from sqlalchemy import select

        remaining = db_session.scalar(
            select(FlightSearch).where(FlightSearch.user_id == other_uid)
        )
        assert remaining is not None
