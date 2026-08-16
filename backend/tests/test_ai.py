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
from unittest.mock import MagicMock
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

    @pytest.mark.asyncio
    async def test_assistant_greeting_does_not_trigger_flight_search(
        self, client, auth_headers
    ):
        _override_llm_provider()
        try:
            r = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "hi"},
                headers=auth_headers,
            )
            assert r.status_code == 200
            reply = r.json()["data"]["reply"]
            assert len(reply) > 0
            assert "available flights" not in reply.lower()
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_assistant_multiturn_hyd_to_del_today_7pm(
        self, client, auth_headers
    ):
        _override_llm_provider()
        try:
            # Turn 1
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "I have to go Delhi from Hyderabad"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]
            reply1 = r1.json()["data"]["reply"]
            assert "HYD" in reply1 and "DEL" in reply1

            # Turn 2
            r2 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "today by 7pm", "conversation_id": conv_id},
                headers=auth_headers,
            )
            assert r2.status_code == 200
            reply2 = r2.json()["data"]["reply"]
            assert "available flights" in reply2.lower() or "flight" in reply2.lower()
            assert "HYD" in reply2 and "DEL" in reply2
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_assistant_multiturn_context_preservation_hyd_to_bom(
        self, client, auth_headers
    ):
        _override_llm_provider()
        try:
            # Turn 1
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "I want to travel from Hyderabad to Mumbai"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]

            # Turn 2 with typo
            r2 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "tomorrow morning", "conversation_id": conv_id},
                headers=auth_headers,
            )
            assert r2.status_code == 200
            reply = r2.json()["data"]["reply"]
            assert len(reply) > 0
            assert "available flights" in reply.lower() or "flight" in reply.lower()
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_assistant_multiturn_context_preservation_del_to_dxb(
        self, client, auth_headers
    ):
        _override_llm_provider()
        try:
            # Turn 1
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "Delhi to Dubai"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]

            # Turn 2
            r2 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "next Monday", "conversation_id": conv_id},
                headers=auth_headers,
            )
            assert r2.status_code == 200
            reply = r2.json()["data"]["reply"]
            assert len(reply) > 0
            assert "available flights" in reply.lower() or "flight" in reply.lower()
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_assistant_one_turn_request_executes_search(
        self, client, auth_headers
    ):
        _override_llm_provider()
        try:
            msg = "I need a flight from Hyderabad to Mumbai tomorrow morning"
            r = await client.post(
                "/api/v1/assistant/chat",
                json={"message": msg},
                headers=auth_headers,
            )
            assert r.status_code == 200
            reply = r.json()["data"]["reply"]
            assert "HYD" in reply or "Hyderabad" in reply
            assert "BOM" in reply or "Mumbai" in reply
            assert "google flights" not in reply.lower()
            assert "live booking feed" not in reply.lower()
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_assistant_missing_date_asks_clarification(
        self, client, auth_headers
    ):
        _override_llm_provider()
        try:
            r = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "I want to go from Delhi to Hyderabad"},
                headers=auth_headers,
            )
            assert r.status_code == 200
            reply = r.json()["data"]["reply"]
            assert "DEL" in reply and "HYD" in reply
            assert "date" in reply.lower() or "time" in reply.lower()
            assert "google flights" not in reply.lower()
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_assistant_no_results_handled_honestly(
        self, client, auth_headers
    ):
        _override_llm_provider()
        from unittest.mock import AsyncMock, patch
        try:
            target_path = "app.services.flight_service.FlightService.search_flights"
            with patch(target_path, new_callable=AsyncMock) as mock_search:
                mock_search.return_value = ([], 0)
                r = await client.post(
                    "/api/v1/assistant/chat",
                    json={"message": "Hyderabad to Mumbai tomorrow morning"},
                    headers=auth_headers,
                )
                assert r.status_code == 200
                reply = r.json()["data"]["reply"]
                assert (
                    "no matching flights" in reply.lower()
                    or "no flights" in reply.lower()
                )
                assert "google flights" not in reply.lower()
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_assistant_search_failure_handled_honestly(
        self, client, auth_headers
    ):
        _override_llm_provider()
        from unittest.mock import AsyncMock, patch
        try:
            target_path = "app.services.flight_service.FlightService.search_flights"
            with patch(target_path, new_callable=AsyncMock) as mock_search:
                mock_search.side_effect = Exception("Database timeout")
                r = await client.post(
                    "/api/v1/assistant/chat",
                    json={"message": "Hyderabad to Mumbai tomorrow morning"},
                    headers=auth_headers,
                )
                assert r.status_code == 200
                reply = r.json()["data"]["reply"]
                assert (
                    "couldn't complete" in reply.lower()
                    or "failed" in reply.lower()
                    or "no flights" in reply.lower()
                )
                assert "google flights" not in reply.lower()
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_assistant_general_conversation_does_not_trigger_search(
        self, client, auth_headers
    ):
        _override_llm_provider()
        from unittest.mock import AsyncMock, patch
        try:
            target_path = "app.services.flight_service.FlightService.search_flights"
            with patch(target_path, new_callable=AsyncMock) as mock_search:
                r = await client.post(
                    "/api/v1/assistant/chat",
                    json={"message": "tell me about Hyderabad"},
                    headers=auth_headers,
                )
                assert r.status_code == 200
                mock_search.assert_not_called()
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_gemini_succeeds_returns_flight_results(
        self, client, auth_headers
    ):
        from app.ai.llm_provider import GeminiProvider
        from app.dependencies.ai import get_llm_provider
        from app.main import app as fastapi_app
        from unittest.mock import AsyncMock

        mock_gemini = AsyncMock(spec=GeminiProvider)
        mock_gemini.complete.return_value = (
            "Here are flights for HYD to BOM: Flight 6E201 (IndiGo) at 06:00.",
            50,
        )
        fastapi_app.dependency_overrides[get_llm_provider] = lambda: mock_gemini
        try:
            r = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "Hyderabad to Mumbai tomorrow morning"},
                headers=auth_headers,
            )
            assert r.status_code == 200
            reply = r.json()["data"]["reply"]
            assert "6E201" in reply or "IndiGo" in reply
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_gemini_timeout_falls_back_in_time_bound(
        self, client, auth_headers
    ):
        import asyncio
        import time
        from app.ai.llm_provider import GeminiProvider
        from app.dependencies.ai import get_llm_provider
        from app.main import app as fastapi_app
        from unittest.mock import patch

        async def slow_complete(*args, **kwargs):
            await asyncio.sleep(5.0)
            return "Slow response", 10

        mock_gemini = GeminiProvider(api_key="fake_key")
        fastapi_app.dependency_overrides[get_llm_provider] = lambda: mock_gemini

        t0 = time.monotonic()
        try:
            with patch.object(mock_gemini, "complete", side_effect=slow_complete):
                r = await client.post(
                    "/api/v1/assistant/chat",
                    json={"message": "Hyderabad to Mumbai tomorrow morning"},
                    headers=auth_headers,
                )
            elapsed = time.monotonic() - t0
            assert r.status_code == 200
            assert elapsed < 4.5
            reply = r.json()["data"]["reply"]
            assert "HYD" in reply or "Hyderabad" in reply
            assert "BOM" in reply or "Mumbai" in reply
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_gemini_network_failure_falls_back_gracefully(
        self, client, auth_headers
    ):
        from app.ai.llm_provider import GeminiProvider
        from app.dependencies.ai import get_llm_provider
        from app.main import app as fastapi_app
        from unittest.mock import patch

        mock_gemini = GeminiProvider(api_key="fake_key")
        fastapi_app.dependency_overrides[get_llm_provider] = lambda: mock_gemini

        try:
            with patch.object(
                mock_gemini,
                "complete",
                side_effect=Exception("Connection refused by Google API"),
            ):
                r = await client.post(
                    "/api/v1/assistant/chat",
                    json={"message": "Hyderabad to Mumbai tomorrow morning"},
                    headers=auth_headers,
                )
            assert r.status_code == 200
            reply = r.json()["data"]["reply"]
            assert "HYD" in reply or "Hyderabad" in reply
            assert "BOM" in reply or "Mumbai" in reply
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_gemini_unavailable_normal_chat_falls_back(
        self, client, auth_headers
    ):
        from app.ai.llm_provider import GeminiProvider
        from app.dependencies.ai import get_llm_provider
        from app.main import app as fastapi_app
        from unittest.mock import patch

        mock_gemini = GeminiProvider(api_key="fake_key")
        fastapi_app.dependency_overrides[get_llm_provider] = lambda: mock_gemini

        try:
            with patch.object(
                mock_gemini,
                "complete",
                side_effect=Exception("API Unreachable"),
            ):
                r = await client.post(
                    "/api/v1/assistant/chat",
                    json={"message": "hi"},
                    headers=auth_headers,
                )
            assert r.status_code == 200
            reply = r.json()["data"]["reply"]
            assert len(reply) > 0
            assert "assistant" in reply.lower() or "hello" in reply.lower()
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_gemini_timeout_multiturn_preserves_context_and_flights(
        self, client, auth_headers
    ):
        import asyncio
        from app.ai.llm_provider import GeminiProvider
        from app.dependencies.ai import get_llm_provider
        from app.main import app as fastapi_app
        from unittest.mock import patch

        async def slow_complete(*args, **kwargs):
            await asyncio.sleep(5.0)

        mock_gemini = GeminiProvider(api_key="fake_key")
        fastapi_app.dependency_overrides[get_llm_provider] = lambda: mock_gemini

        try:
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "I want to travel from Hyderabad to Mumbai"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]

            with patch.object(mock_gemini, "complete", side_effect=slow_complete):
                r2 = await client.post(
                    "/api/v1/assistant/chat",
                    json={
                        "message": "tomorrow morning",
                        "conversation_id": conv_id,
                    },
                    headers=auth_headers,
                )
            assert r2.status_code == 200
            reply = r2.json()["data"]["reply"]
            assert "HYD" in reply or "Hyderabad" in reply
            assert "BOM" in reply or "Mumbai" in reply
        finally:
            _clear_ai_overrides()
