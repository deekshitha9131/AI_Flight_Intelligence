"""
tests/test_ai.py
----------------
Tests for all AI modules:
  - POST /api/v1/ai/predict-price
  - GET  /api/v1/ai/price-trend
  - GET  /api/v1/ai/preferences
  - GET  /api/v1/ai/insights
  - GET  /api/v1/recommendations
  - GET  /api/v1/recommendations/destinations
  - GET  /api/v1/recommendations/airlines
  - GET  /api/v1/recommendations/deals
  - POST /api/v1/assistant/chat
  - GET  /api/v1/assistant/conversations
  - GET  /api/v1/assistant/conversations/{id}
  - DELETE /api/v1/assistant/conversations/{id}

All tests use the savepoint-based DB isolation from conftest.py.
ModelLoader and LLMProvider are overridden via dependency_overrides so
no real ML model or LLM API key is required.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.ai.llm_provider import FallbackProvider
from app.ai.model_loader import ModelLoader
from app.dependencies.ai import get_llm_provider, get_model_loader
from app.main import app as fastapi_app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _future_date(days: int = 60) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def _mock_model_loader() -> ModelLoader:
    loader = MagicMock(spec=ModelLoader)
    loader.predict.return_value = (450.00, 0.82)
    loader.model_version = "test-1.0.0"
    loader.is_fallback = False
    return loader


def _override_model_loader():
    fastapi_app.dependency_overrides[get_model_loader] = _mock_model_loader


def _override_llm_provider():
    fastapi_app.dependency_overrides[get_llm_provider] = lambda: FallbackProvider()


def _clear_ai_overrides():
    fastapi_app.dependency_overrides.pop(get_model_loader, None)
    fastapi_app.dependency_overrides.pop(get_llm_provider, None)


# ---------------------------------------------------------------------------
# Prediction tests
# ---------------------------------------------------------------------------


class TestPredictPrice:
    """Tests for POST /api/v1/ai/predict-price."""

    @pytest.mark.asyncio
    async def test_predict_price_success(self, client, auth_headers):
        _override_model_loader()
        try:
            payload = {
                "origin": "HYD",
                "destination": "DXB",
                "departure_date": _future_date(60),
                "cabin_class": "ECONOMY",
                "adults": 1,
                "trip_type": "ONE_WAY",
                "currency": "USD",
            }
            response = await client.post(
                "/api/v1/ai/predict-price", json=payload, headers=auth_headers
            )
            assert response.status_code == 200, response.text
            data = response.json()
            assert data["success"] is True
            result = data["data"]
            assert result["predicted_price"] > 0
            assert result["price_range_low"] <= result["predicted_price"]
            assert result["price_range_high"] >= result["predicted_price"]
            assert result["model_version"] == "test-1.0.0"
            assert "prediction_id" in result
            assert "predicted_at" in result
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_predict_price_requires_auth(self, client):
        payload = {
            "origin": "HYD",
            "destination": "DXB",
            "departure_date": _future_date(60),
            "trip_type": "ONE_WAY",
            "currency": "USD",
        }
        response = await client.post("/api/v1/ai/predict-price", json=payload)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_predict_price_same_origin_destination(self, client, auth_headers):
        _override_model_loader()
        try:
            payload = {
                "origin": "HYD",
                "destination": "HYD",
                "departure_date": _future_date(60),
                "trip_type": "ONE_WAY",
                "currency": "USD",
            }
            response = await client.post(
                "/api/v1/ai/predict-price", json=payload, headers=auth_headers
            )
            assert response.status_code == 422
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_predict_price_past_date(self, client, auth_headers):
        _override_model_loader()
        try:
            payload = {
                "origin": "HYD",
                "destination": "DXB",
                "departure_date": "2020-01-01",
                "trip_type": "ONE_WAY",
                "currency": "USD",
            }
            response = await client.post(
                "/api/v1/ai/predict-price", json=payload, headers=auth_headers
            )
            assert response.status_code == 422
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_predict_price_round_trip_missing_return_date(
        self, client, auth_headers
    ):
        _override_model_loader()
        try:
            payload = {
                "origin": "HYD",
                "destination": "DXB",
                "departure_date": _future_date(60),
                "trip_type": "ROUND_TRIP",
                "currency": "USD",
            }
            response = await client.post(
                "/api/v1/ai/predict-price", json=payload, headers=auth_headers
            )
            assert response.status_code == 422
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_predict_price_round_trip_success(self, client, auth_headers):
        _override_model_loader()
        try:
            payload = {
                "origin": "HYD",
                "destination": "DXB",
                "departure_date": _future_date(60),
                "return_date": _future_date(70),
                "trip_type": "ROUND_TRIP",
                "currency": "USD",
            }
            response = await client.post(
                "/api/v1/ai/predict-price", json=payload, headers=auth_headers
            )
            assert response.status_code == 200
            assert response.json()["success"] is True
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_predict_price_iata_normalised(self, client, auth_headers):
        """Lowercase IATA codes should be accepted and normalised."""
        _override_model_loader()
        try:
            payload = {
                "origin": "hyd",
                "destination": "dxb",
                "departure_date": _future_date(60),
                "trip_type": "ONE_WAY",
                "currency": "usd",
            }
            response = await client.post(
                "/api/v1/ai/predict-price", json=payload, headers=auth_headers
            )
            assert response.status_code == 200
        finally:
            _clear_ai_overrides()


# ---------------------------------------------------------------------------
# Price trend tests
# ---------------------------------------------------------------------------


class TestPriceTrend:
    """Tests for GET /api/v1/ai/price-trend."""

    @pytest.mark.asyncio
    async def test_price_trend_success(self, client, auth_headers):
        response = await client.get(
            "/api/v1/ai/price-trend",
            params={"origin": "HYD", "destination": "DXB", "currency": "USD"},
            headers=auth_headers,
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["success"] is True
        result = data["data"]
        assert result["origin"] == "HYD"
        assert result["destination"] == "DXB"
        assert result["trend_direction"] in ("increasing", "decreasing", "stable")
        assert len(result["weekly_trend"]) == 7
        assert len(result["monthly_trend"]) == 12

    @pytest.mark.asyncio
    async def test_price_trend_requires_auth(self, client):
        response = await client.get(
            "/api/v1/ai/price-trend",
            params={"origin": "HYD", "destination": "DXB"},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Preferences tests
# ---------------------------------------------------------------------------


class TestPreferences:
    """Tests for GET /api/v1/ai/preferences."""

    @pytest.mark.asyncio
    async def test_get_preferences_success(self, client, auth_headers):
        response = await client.get("/api/v1/ai/preferences", headers=auth_headers)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["success"] is True
        pref = data["data"]
        assert "preferred_cabin" in pref
        assert "total_searches" in pref
        assert isinstance(pref["preferred_airlines"], list)

    @pytest.mark.asyncio
    async def test_get_preferences_requires_auth(self, client):
        response = await client.get("/api/v1/ai/preferences")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Insights tests
# ---------------------------------------------------------------------------


class TestInsights:
    """Tests for GET /api/v1/ai/insights."""

    @pytest.mark.asyncio
    async def test_get_insights_success(self, client, auth_headers):
        response = await client.get("/api/v1/ai/insights", headers=auth_headers)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)
        assert data["count"] == len(data["data"])

    @pytest.mark.asyncio
    async def test_get_insights_requires_auth(self, client):
        response = await client.get("/api/v1/ai/insights")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Recommendation tests
# ---------------------------------------------------------------------------


class TestRecommendations:
    """Tests for GET /api/v1/recommendations/*."""

    @pytest.mark.asyncio
    async def test_flight_recommendations(self, client, auth_headers):
        _override_model_loader()
        try:
            response = await client.get("/api/v1/recommendations", headers=auth_headers)
            assert response.status_code == 200, response.text
            data = response.json()
            assert data["success"] is True
            assert isinstance(data["data"], list)
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_destination_recommendations(self, client, auth_headers):
        _override_model_loader()
        try:
            response = await client.get(
                "/api/v1/recommendations/destinations", headers=auth_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            for dest in data["data"]:
                assert "iata_code" in dest
                assert "city" in dest
                assert "estimated_price" in dest
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_airline_recommendations(self, client, auth_headers):
        _override_model_loader()
        try:
            response = await client.get(
                "/api/v1/recommendations/airlines", headers=auth_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_deal_recommendations(self, client, auth_headers):
        _override_model_loader()
        try:
            response = await client.get(
                "/api/v1/recommendations/deals", headers=auth_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            for deal in data["data"]:
                assert deal["discount_pct"] > 0
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_recommendations_require_auth(self, client):
        for path in [
            "/api/v1/recommendations",
            "/api/v1/recommendations/destinations",
            "/api/v1/recommendations/airlines",
            "/api/v1/recommendations/deals",
        ]:
            response = await client.get(path)
            assert response.status_code == 401, f"Expected 401 for {path}"


# ---------------------------------------------------------------------------
# Assistant tests
# ---------------------------------------------------------------------------


class TestAssistant:
    """Tests for POST /api/v1/assistant/chat and conversation management."""

    @pytest.mark.asyncio
    async def test_chat_new_conversation(self, client, auth_headers):
        _override_llm_provider()
        try:
            response = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "What is the cheapest time to fly to Dubai?"},
                headers=auth_headers,
            )
            assert response.status_code == 200, response.text
            data = response.json()
            assert data["success"] is True
            assert "conversation_id" in data["data"]
            assert len(data["data"]["reply"]) > 0
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_chat_continue_conversation(self, client, auth_headers):
        _override_llm_provider()
        try:
            # Start conversation
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "Hello"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]

            # Continue it
            r2 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "Tell me more.", "conversation_id": conv_id},
                headers=auth_headers,
            )
            assert r2.status_code == 200
            assert r2.json()["data"]["conversation_id"] == conv_id
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_chat_invalid_conversation_id(self, client, auth_headers):
        _override_llm_provider()
        try:
            response = await client.post(
                "/api/v1/assistant/chat",
                json={
                    "message": "Hello",
                    "conversation_id": str(uuid4()),
                },
                headers=auth_headers,
            )
            assert response.status_code == 404
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_list_conversations(self, client, auth_headers):
        _override_llm_provider()
        try:
            # Create a conversation first
            await client.post(
                "/api/v1/assistant/chat",
                json={"message": "Hi"},
                headers=auth_headers,
            )
            response = await client.get(
                "/api/v1/assistant/conversations", headers=auth_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["count"] >= 1
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_get_conversation_detail(self, client, auth_headers):
        _override_llm_provider()
        try:
            r = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "What are the baggage rules for Emirates?"},
                headers=auth_headers,
            )
            conv_id = r.json()["data"]["conversation_id"]

            response = await client.get(
                f"/api/v1/assistant/conversations/{conv_id}",
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["messages"]) >= 2  # user + assistant
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_delete_conversation(self, client, auth_headers):
        _override_llm_provider()
        try:
            r = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "Delete me"},
                headers=auth_headers,
            )
            conv_id = r.json()["data"]["conversation_id"]

            del_response = await client.delete(
                f"/api/v1/assistant/conversations/{conv_id}",
                headers=auth_headers,
            )
            assert del_response.status_code == 200
            assert del_response.json()["success"] is True

            # Verify it's gone
            get_response = await client.get(
                f"/api/v1/assistant/conversations/{conv_id}",
                headers=auth_headers,
            )
            assert get_response.status_code == 404
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_conversation(self, client, auth_headers):
        response = await client.delete(
            f"/api/v1/assistant/conversations/{uuid4()}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_chat_requires_auth(self, client):
        response = await client.post(
            "/api/v1/assistant/chat",
            json={"message": "Hello"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_chat_cross_user_isolation(self, client, user_payload):
        """User A cannot access User B's conversations."""
        _override_llm_provider()
        try:
            # Register and log in user A
            await client.post(
                "/api/v1/auth/register", json=user_payload(email="user_a@example.com")
            )
            r_a = await client.post(
                "/api/v1/auth/login",
                json={"email": "user_a@example.com", "password": "Secure@123"},
            )
            headers_a = {
                "Authorization": f"Bearer {r_a.json()['data']['access_token']}"
            }

            # Register and log in user B
            await client.post(
                "/api/v1/auth/register", json=user_payload(email="user_b@example.com")
            )
            r_b = await client.post(
                "/api/v1/auth/login",
                json={"email": "user_b@example.com", "password": "Secure@123"},
            )
            headers_b = {
                "Authorization": f"Bearer {r_b.json()['data']['access_token']}"
            }

            # User A creates a conversation
            r = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "Private message"},
                headers=headers_a,
            )
            conv_id = r.json()["data"]["conversation_id"]

            # User B tries to access it
            response = await client.get(
                f"/api/v1/assistant/conversations/{conv_id}",
                headers=headers_b,
            )
            assert response.status_code == 404
        finally:
            _clear_ai_overrides()
