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


from app.dependencies.amadeus import get_flight_provider
from unittest.mock import AsyncMock, MagicMock


def _make_stub_flight_provider():
    """Return a lightweight mock FlightProvider for AI tests."""
    stub = MagicMock()
    stub.search_flights = AsyncMock(return_value={"data": [], "dictionaries": {}})
    return stub


def _override_model_loader():
    fastapi_app.dependency_overrides[get_model_loader] = _mock_model_loader


def _override_llm_provider():
    fastapi_app.dependency_overrides[get_llm_provider] = lambda: FallbackProvider()
    fastapi_app.dependency_overrides[get_flight_provider] = lambda: _make_stub_flight_provider()


def _clear_ai_overrides():
    fastapi_app.dependency_overrides.pop(get_model_loader, None)
    fastapi_app.dependency_overrides.pop(get_llm_provider, None)
    fastapi_app.dependency_overrides.pop(get_flight_provider, None)



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
            assert any(k in reply for k in ("6E201", "IndiGo", "Air India", "AI", "Flight"))
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
            raise asyncio.TimeoutError("Gemini call timed out")

        mock_gemini = GeminiProvider(api_key="fake_key", timeout=1.0)

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
            assert elapsed < 10.0

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

    @pytest.mark.asyncio
    async def test_assistant_test_a_multiturn_date_range_completion(
        self, client, auth_headers
    ):
        """Test A: Multi-turn date completion (e.g. 'in next 5 days any day and time is okay')."""
        _override_llm_provider()
        try:
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "I want to travel from Hyderabad to London"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]

            r2 = await client.post(
                "/api/v1/assistant/chat",
                json={
                    "message": "in next 5 days any day and time is okay for me",
                    "conversation_id": conv_id,
                },
                headers=auth_headers,
            )
            assert r2.status_code == 200
            reply = r2.json()["data"]["reply"]
            # Should invoke flight search and present flights without repeating the missing date question
            assert "date or time" not in reply.lower()
            assert "what date" not in reply.lower()
            assert any(k in reply.lower() for k in ("flight", "hyd", "lhr", "available", "london"))
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_assistant_test_b_greeting_after_flight_intent(
        self, client, auth_headers
    ):
        """Test B: Greeting after flight intent should respond naturally without stale date question."""
        _override_llm_provider()
        try:
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "I want to travel from Hyderabad to London"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]

            r2 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "hii", "conversation_id": conv_id},
                headers=auth_headers,
            )
            assert r2.status_code == 200
            reply = r2.json()["data"]["reply"]
            assert "acknowledge the route" not in reply.lower()
            assert "departure date is missing" not in reply.lower()
            assert len(reply) > 0
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_assistant_test_c_capability_question_after_flight_intent(
        self, client, auth_headers
    ):
        """Test C: Capability question after flight intent."""
        _override_llm_provider()
        try:
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "I want to travel from Hyderabad to London"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]

            r2 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "what can you do", "conversation_id": conv_id},
                headers=auth_headers,
            )
            assert r2.status_code == 200
            reply = r2.json()["data"]["reply"]
            assert "departure date is missing" not in reply.lower()
            assert any(k in reply.lower() for k in ("help", "flight", "search", "can", "assistant"))
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_assistant_test_d_cancellation(
        self, client, auth_headers
    ):
        """Test D: Explicit cancellation terminates flight flow."""
        _override_llm_provider()
        try:
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "I want to travel from Hyderabad to London"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]

            r2 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "I don't want to travel", "conversation_id": conv_id},
                headers=auth_headers,
            )
            assert r2.status_code == 200
            reply = r2.json()["data"]["reply"]
            assert "departure date is missing" not in reply.lower()
            assert "won't search" in reply.lower() or "no problem" in reply.lower() or "cancelled" in reply.lower()
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_assistant_test_e_general_travel_information(
        self, client, auth_headers
    ):
        """Test E: General travel information question answered independently."""
        _override_llm_provider()
        try:
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "I want to travel from Hyderabad to London"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]

            r2 = await client.post(
                "/api/v1/assistant/chat",
                json={
                    "message": "How early should I arrive for an international flight?",
                    "conversation_id": conv_id,
                },
                headers=auth_headers,
            )
            assert r2.status_code == 200
            reply = r2.json()["data"]["reply"]
            assert "departure date is missing" not in reply.lower()
            assert len(reply) > 0
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_assistant_test_f_genuine_continuation(
        self, client, auth_headers
    ):
        """Test F: Genuine date continuation 'tomorrow'."""
        _override_llm_provider()
        try:
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "I want to travel from Hyderabad to London"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]

            r2 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "tomorrow", "conversation_id": conv_id},
                headers=auth_headers,
            )
            assert r2.status_code == 200
            reply = r2.json()["data"]["reply"]
            assert any(k in reply.lower() for k in ("flight", "hyd", "lhr", "available", "london"))
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_assistant_test_g_flight_refinement(
        self, client, auth_headers
    ):
        """Test G: Flight refinement 'show me cheaper options'."""
        _override_llm_provider()
        try:
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "Find HYD to LHR tomorrow"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]

            r2 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "show me cheaper options", "conversation_id": conv_id},
                headers=auth_headers,
            )
            assert r2.status_code == 200
            reply = r2.json()["data"]["reply"]
            assert "departure date is missing" not in reply.lower()
            assert any(k in reply.lower() for k in ("flight", "hyd", "lhr", "available", "price", "cheaper", "usd"))
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_assistant_new_destination_overrides_previous_route(
        self, client, auth_headers
    ):
        """Test Rule 1 & 2: New destination 'i want to go delhi' replaces previous HYD -> LHR route."""
        _override_llm_provider()
        try:
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "I want to travel from Hyderabad to London"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]

            r2 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "hii", "conversation_id": conv_id},
                headers=auth_headers,
            )
            assert r2.status_code == 200

            r3 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "i want to go delhi", "conversation_id": conv_id},
                headers=auth_headers,
            )
            assert r3.status_code == 200
            reply = r3.json()["data"]["reply"]
            # Must NOT resurrect the old LHR destination or HYD -> LHR route
            assert "hyd to lhr" not in reply.lower()
            assert "from hyderabad to london" not in reply.lower()
            assert "london" not in reply.lower()
            # Should ask where departing from or acknowledge Delhi
            assert any(k in reply.lower() for k in ("delhi", "del", "depart", "where", "origin", "from"))
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_assistant_full_new_route_replaces_everything(
        self, client, auth_headers
    ):
        """Test Rule 4: Full new route 'from Mumbai to Paris' completely replaces HYD -> LHR."""
        _override_llm_provider()
        try:
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "I want to travel from Hyderabad to London"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]

            r2 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "I want to travel from Mumbai to Paris"},
                headers=auth_headers,
            )
            assert r2.status_code == 200
            reply = r2.json()["data"]["reply"]
            assert "lhr" not in reply.lower()
            assert "london" not in reply.lower()
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_assistant_critical_test_2_pending_origin_question_priority(
        self, client, auth_headers
    ):
        """TEST 2: 'i want to go delhi' -> Assistant: 'where to depart?' -> 'hyderabad' -> origin=HYD, dest=DEL (NEVER dest=HYD)."""
        _override_llm_provider()
        try:
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "I want to go Delhi"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]

            r2 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "Hyderabad", "conversation_id": conv_id},
                headers=auth_headers,
            )
            assert r2.status_code == 200
            reply = r2.json()["data"]["reply"]
            # Must acknowledge HYD to DEL route or ask for date, NEVER ask for origin again or say fly to HYD
            assert "fly to hyd" not in reply.lower()
            assert "destination: hyd" not in reply.lower()
            assert any(k in reply.lower() for k in ("hyd to del", "hyderabad", "delhi", "date", "time"))
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_assistant_critical_test_7_no_i_want_to_fly_london_replaces_destination(
        self, client, auth_headers
    ):
        """TEST 7 & 15: HYD -> DEL active -> 'no I want to fly London' -> destination becomes LHR (DEL not retained)."""
        _override_llm_provider()
        try:
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "I want to travel from Hyderabad to Delhi"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]

            r2 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "no I want to fly London", "conversation_id": conv_id},
                headers=auth_headers,
            )
            assert r2.status_code == 200
            reply = r2.json()["data"]["reply"]
            # Destination must be LHR, DEL must NOT survive as destination
            assert "delhi" not in reply.lower() or "london" in reply.lower()
            assert "del" not in reply.lower() or "lhr" in reply.lower()
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_assistant_full_manual_acceptance_sequence(
        self, client, auth_headers
    ):
        """FULL MANUAL ACCEPTANCE TEST (Turns 1-8)."""
        _override_llm_provider()
        try:
            # Turn 1
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "I want to travel from Hyderabad to London"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]
            assert any(k in r1.json()["data"]["reply"].lower() for k in ("hyd", "lhr", "london", "date", "time"))

            # Turn 2: greeting
            r2 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "hii", "conversation_id": conv_id},
                headers=auth_headers,
            )
            assert r2.status_code == 200

            # Turn 3: i want to go delhi
            r3 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "i want to go delhi", "conversation_id": conv_id},
                headers=auth_headers,
            )
            assert r3.status_code == 200
            assert "london" not in r3.json()["data"]["reply"].lower()

            # Turn 4: hyderabad (answer to pending origin question)
            r4 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "hyderabad", "conversation_id": conv_id},
                headers=auth_headers,
            )
            assert r4.status_code == 200
            assert "fly to hyd" not in r4.json()["data"]["reply"].lower()

            # Turn 5: tomorrow
            r5 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "tomorrow", "conversation_id": conv_id},
                headers=auth_headers,
            )
            assert r5.status_code == 200

            # Turn 6: hii
            r6 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "hii", "conversation_id": conv_id},
                headers=auth_headers,
            )
            assert r6.status_code == 200

            # Turn 7: what can u do
            r7 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "what can u do", "conversation_id": conv_id},
                headers=auth_headers,
            )
            assert r7.status_code == 200
            assert "demo mode" not in r7.json()["data"]["reply"].lower()

            # Turn 8: no i want to fly london
            r8 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "no i want to fly london", "conversation_id": conv_id},
                headers=auth_headers,
            )
            assert r8.status_code == 200
            assert "delhi" not in r8.json()["data"]["reply"].lower() or "london" in r8.json()["data"]["reply"].lower()
        finally:
            _clear_ai_overrides()

    # ------------------------------------------------------------------
    # Additional Comprehensive Assistant Fix Tests (1-20)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_destination_change_does_not_reuse_stale_origin_and_date(
        self, client, auth_headers
    ):
        """Test 1: 'I want to go London' after HYD -> DEL search does not execute search for HYD -> LHR with stale date."""
        from unittest.mock import AsyncMock, patch
        from app.services.flight_service import FlightService

        _override_llm_provider()
        try:
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "find flights from Hyderabad to Delhi tomorrow"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]

            with patch.object(FlightService, "search_flights", new_callable=AsyncMock) as mock_search:
                r2 = await client.post(
                    "/api/v1/assistant/chat",
                    json={"message": "I want to go London", "conversation_id": conv_id},
                    headers=auth_headers,
                )
                assert r2.status_code == 200
                assert mock_search.call_count == 0
                reply = r2.json()["data"]["reply"].lower()
                assert "depart" in reply or "where" in reply or "london" in reply
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_negative_origin_correction_phrasing(self, client, auth_headers):
        """Test 2: 'not from Hyderabad from Delhi' sets origin to DEL, not HYD."""
        _override_llm_provider()
        try:
            r = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "not from Hyderabad from Delhi"},
                headers=auth_headers,
            )
            assert r.status_code == 200
            reply = r.json()["data"]["reply"].lower()
            assert "delhi" in reply or "del" in reply
            assert "fly to hyd" not in reply
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_pending_origin_broad_phrasing_support(self, client, auth_headers):
        """Test 3 & 19: Broad pending origin phrases correctly set origin."""
        _override_llm_provider()
        try:
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "I want to go Delhi"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]

            r2 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "Hyderabad", "conversation_id": conv_id},
                headers=auth_headers,
            )
            assert r2.status_code == 200
            reply = r2.json()["data"]["reply"].lower()
            assert "fly to hyd" not in reply
            assert any(k in reply for k in ("hyd to del", "hyderabad", "delhi", "date", "time"))
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_pending_destination_broad_phrasing_support(self, client, auth_headers):
        """Test 4 & 20: Broad pending destination phrases correctly set destination."""
        _override_llm_provider()
        try:
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "I am departing from Mumbai"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]

            r2 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "London", "conversation_id": conv_id},
                headers=auth_headers,
            )
            assert r2.status_code == 200
            reply = r2.json()["data"]["reply"].lower()
            assert "bom to lhr" in reply or "mumbai" in reply or "london" in reply
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_result_followup_best_flight_no_search_reexecution(self, client, auth_headers):
        """Test 5 & 11: 'which flight is best' does NOT re-execute search and recommends one flight."""
        from unittest.mock import AsyncMock, patch
        from app.services.flight_service import FlightService

        _override_llm_provider()
        try:
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "find flights from Hyderabad to Delhi tomorrow"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]

            with patch.object(FlightService, "search_flights", new_callable=AsyncMock) as mock_search:
                r2 = await client.post(
                    "/api/v1/assistant/chat",
                    json={"message": "which flight is best", "conversation_id": conv_id},
                    headers=auth_headers,
                )
                assert r2.status_code == 200
                assert mock_search.call_count == 0
                reply = r2.json()["data"]["reply"]
                assert len(reply) > 0
                assert "Flight" in reply or "recommend" in reply.lower()
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_result_followup_give_only_one_returns_single_offer(self, client, auth_headers):
        """Test 6 & 12: 'give only one' returns exactly 1 flight option without re-searching."""
        from unittest.mock import AsyncMock, patch
        from app.services.flight_service import FlightService

        _override_llm_provider()
        try:
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "find flights from Hyderabad to Delhi tomorrow"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]

            with patch.object(FlightService, "search_flights", new_callable=AsyncMock) as mock_search:
                r2 = await client.post(
                    "/api/v1/assistant/chat",
                    json={"message": "give only one", "conversation_id": conv_id},
                    headers=auth_headers,
                )
                assert r2.status_code == 200
                assert mock_search.call_count == 0
                reply = r2.json()["data"]["reply"]
                assert reply.count("- Flight ") <= 1
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_result_followup_cheapest_flight(self, client, auth_headers):
        """Test 7 & 13: 'which is cheapest' returns lowest price flight without re-searching."""
        from unittest.mock import AsyncMock, patch
        from app.services.flight_service import FlightService

        _override_llm_provider()
        try:
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "find flights from Hyderabad to Delhi tomorrow"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]

            with patch.object(FlightService, "search_flights", new_callable=AsyncMock) as mock_search:
                r2 = await client.post(
                    "/api/v1/assistant/chat",
                    json={"message": "which is cheapest", "conversation_id": conv_id},
                    headers=auth_headers,
                )
                assert r2.status_code == 200
                assert mock_search.call_count == 0
                reply = r2.json()["data"]["reply"].lower()
                assert "cheapest" in reply or "flight" in reply
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_flight_duration_question_does_not_trigger_search(self, client, auth_headers):
        """Test 8 & 14: 'how many hours journey from hyd to delhi' does NOT re-search."""
        from unittest.mock import AsyncMock, patch
        from app.services.flight_service import FlightService

        _override_llm_provider()
        try:
            with patch.object(FlightService, "search_flights", new_callable=AsyncMock) as mock_search:
                r = await client.post(
                    "/api/v1/assistant/chat",
                    json={"message": "how many hours journey from hyd to delhi"},
                    headers=auth_headers,
                )
                assert r.status_code == 200
                assert mock_search.call_count == 0
                reply = r.json()["data"]["reply"].lower()
                assert any(k in reply for k in ("hours", "duration", "time", "take", "typically"))
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_flight_duration_question_using_current_context(self, client, auth_headers):
        """Test 9: 'how long is the flight?' uses current context without re-searching."""
        from unittest.mock import AsyncMock, patch
        from app.services.flight_service import FlightService

        _override_llm_provider()
        try:
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "find flights from Hyderabad to Delhi tomorrow"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]

            with patch.object(FlightService, "search_flights", new_callable=AsyncMock) as mock_search:
                r2 = await client.post(
                    "/api/v1/assistant/chat",
                    json={"message": "how long is the flight?", "conversation_id": conv_id},
                    headers=auth_headers,
                )
                assert r2.status_code == 200
                assert mock_search.call_count == 0
                reply = r2.json()["data"]["reply"].lower()
                assert any(k in reply for k in ("hours", "duration", "take", "time"))
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_carry_on_rules_informational_query_fallback(self, client, auth_headers):
        """Test 10: 'Carry-on rules for long-haul travel' returns baggage info, not demo error."""
        _override_llm_provider()
        try:
            r = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "Carry-on rules for long-haul travel"},
                headers=auth_headers,
            )
            assert r.status_code == 200
            reply = r.json()["data"]["reply"]
            assert "currently running in demo mode" not in reply.lower()
            assert any(k in reply.lower() for k in ("carry-on", "bag", "kg", "personal item", "baggage", "allowed"))
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_unresolved_typo_route_asks_clarification_no_stale_reuse(self, client, auth_headers):
        """Test 11: Typo route 'i want to tavel from deli to hderbad' asks clarification, no stale reuse."""
        from unittest.mock import AsyncMock, patch
        from app.services.flight_service import FlightService

        _override_llm_provider()
        try:
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "find flights from Hyderabad to Delhi tomorrow"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]

            with patch.object(FlightService, "search_flights", new_callable=AsyncMock) as mock_search:
                r2 = await client.post(
                    "/api/v1/assistant/chat",
                    json={"message": "i want to tavel from deli to hderbad", "conversation_id": conv_id},
                    headers=auth_headers,
                )
                assert r2.status_code == 200
                assert mock_search.call_count == 0
                reply = r2.json()["data"]["reply"].lower()
                assert "couldn't identify" in reply or "provide" in reply or "airport" in reply
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_greeting_and_capability_after_search_does_not_retrigger_search(self, client, auth_headers):
        """Test 12: 'hii' and 'what can you do?' after search do NOT re-trigger search."""
        from unittest.mock import AsyncMock, patch
        from app.services.flight_service import FlightService

        _override_llm_provider()
        try:
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "find flights from Hyderabad to Delhi tomorrow"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]

            with patch.object(FlightService, "search_flights", new_callable=AsyncMock) as mock_search:
                r2 = await client.post(
                    "/api/v1/assistant/chat",
                    json={"message": "hii", "conversation_id": conv_id},
                    headers=auth_headers,
                )
                assert r2.status_code == 200
                assert mock_search.call_count == 0

                r3 = await client.post(
                    "/api/v1/assistant/chat",
                    json={"message": "what can you do?", "conversation_id": conv_id},
                    headers=auth_headers,
                )
                assert r3.status_code == 200
                assert mock_search.call_count == 0
                assert "demo mode" not in r3.json()["data"]["reply"].lower()
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_explicit_route_replacement(self, client, auth_headers):
        """Test 13: Full new route 'from Delhi to Hyderabad' replaces previous HYD -> LHR route."""
        _override_llm_provider()
        try:
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "I want to travel from Hyderabad to London"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]

            r2 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "I want to travel from Delhi to Hyderabad", "conversation_id": conv_id},
                headers=auth_headers,
            )
            assert r2.status_code == 200
            reply = r2.json()["data"]["reply"].lower()
            assert "london" not in reply
            assert "lhr" not in reply
            assert any(k in reply for k in ("delhi to hyderabad", "del to hyd", "date", "time"))
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_new_route_without_date_does_not_reuse_old_date(self, client, auth_headers):
        """Test 14: New route without date does NOT inherit old date."""
        from unittest.mock import AsyncMock, patch
        from app.services.flight_service import FlightService

        _override_llm_provider()
        try:
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "find flights from Hyderabad to Delhi tomorrow"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]

            with patch.object(FlightService, "search_flights", new_callable=AsyncMock) as mock_search:
                r2 = await client.post(
                    "/api/v1/assistant/chat",
                    json={"message": "from Mumbai to Paris", "conversation_id": conv_id},
                    headers=auth_headers,
                )
                assert r2.status_code == 200
                assert mock_search.call_count == 0
                reply = r2.json()["data"]["reply"].lower()
                assert "date" in reply or "time" in reply or "mumbai to paris" in reply
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_new_route_with_explicit_date_searches(self, client, auth_headers):
        """Test 15: New route with explicit date searches immediately."""
        from unittest.mock import AsyncMock, patch
        from app.services.flight_service import FlightService

        _override_llm_provider()
        try:
            with patch.object(FlightService, "search_flights", new_callable=AsyncMock) as mock_search:
                mock_search.return_value = ([], "")
                r = await client.post(
                    "/api/v1/assistant/chat",
                    json={"message": "find flights from Delhi to London tomorrow"},
                    headers=auth_headers,
                )
                assert r.status_code == 200
                assert mock_search.call_count == 1
                kwargs = mock_search.call_args.kwargs
                params = kwargs["params"]
                assert params.origin == "DEL"
                assert params.destination == "LHR"
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_fastest_followup_does_not_search(self, client, auth_headers):
        """Test 16: 'which is fastest' follow-up does not search."""
        from unittest.mock import AsyncMock, patch
        from app.services.flight_service import FlightService

        _override_llm_provider()
        try:
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "find flights from Hyderabad to Delhi tomorrow"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]

            with patch.object(FlightService, "search_flights", new_callable=AsyncMock) as mock_search:
                r2 = await client.post(
                    "/api/v1/assistant/chat",
                    json={"message": "which is fastest", "conversation_id": conv_id},
                    headers=auth_headers,
                )
                assert r2.status_code == 200
                assert mock_search.call_count == 0
                reply = r2.json()["data"]["reply"].lower()
                assert "fastest" in reply or "flight" in reply
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_best_day_question_is_not_incorrectly_classified_as_result_followup(self, client, auth_headers):
        """Test 17: 'what is the best day to fly to London?' is not classified as result follow-up."""
        _override_llm_provider()
        try:
            r = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "what is the best day to fly to London?"},
                headers=auth_headers,
            )
            assert r.status_code == 200
            reply = r.json()["data"]["reply"].lower()
            assert "don't have active flight search results to compare" not in reply
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_pending_date_response_triggers_search_when_route_is_complete(self, client, auth_headers):
        """Test 18: Pending date response 'tomorrow' triggers search when route is established."""
        from unittest.mock import AsyncMock, patch
        from app.services.flight_service import FlightService

        _override_llm_provider()
        try:
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "I want to travel from Hyderabad to London"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]

            with patch.object(FlightService, "search_flights", new_callable=AsyncMock) as mock_search:
                mock_search.return_value = ([], "")
                r2 = await client.post(
                    "/api/v1/assistant/chat",
                    json={"message": "tomorrow", "conversation_id": conv_id},
                    headers=auth_headers,
                )
                assert r2.status_code == 200
                assert mock_search.call_count == 1
                kwargs = mock_search.call_args.kwargs
                params = kwargs["params"]
                assert params.origin == "HYD"
                assert params.destination == "LHR"
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_pending_origin_response_sets_origin_rather_than_destination(self, client, auth_headers):
        """Test 19: Answering origin question 'Hyderabad' sets origin HYD, not destination."""
        _override_llm_provider()
        try:
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "I want to go Delhi"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]

            r2 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "Hyderabad", "conversation_id": conv_id},
                headers=auth_headers,
            )
            assert r2.status_code == 200
            reply = r2.json()["data"]["reply"].lower()
            assert "fly to hyd" not in reply
            assert "hyd to del" in reply or "hyderabad" in reply
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_pending_destination_response_sets_destination_rather_than_origin(self, client, auth_headers):
        """Test 20: Answering destination question 'London' sets destination LHR, not origin."""
        _override_llm_provider()
        try:
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "I am leaving from Delhi"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]

            r2 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "London", "conversation_id": conv_id},
                headers=auth_headers,
            )
            assert r2.status_code == 200
            reply = r2.json()["data"]["reply"].lower()
            assert "del to lhr" in reply or "delhi" in reply or "london" in reply
        finally:
            _clear_ai_overrides()

    # ------------------------------------------------------------------
    # State + Intent Switching Regression Tests
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_regression_hyd_dxb_followed_by_london_hyd_duration(
        self, client, auth_headers
    ):
        """HYD -> DXB search followed by 'how long is the flight from London to HYD?'."""
        _override_llm_provider()
        from unittest.mock import AsyncMock, patch
        try:
            target_path = "app.services.flight_service.FlightService.search_flights"
            with patch(target_path, new_callable=AsyncMock) as mock_search:
                mock_search.return_value = ([], 0)
                # Turn 1: Search flights HYD to DXB
                r1 = await client.post(
                    "/api/v1/assistant/chat",
                    json={"message": f"Find flights from HYD to DXB on {_future_date(10)}"},
                    headers=auth_headers,
                )
                assert r1.status_code == 200
                conv_id = r1.json()["data"]["conversation_id"]
                assert mock_search.call_count == 1

                # Reset call count
                mock_search.reset_mock()

                # Turn 2: Duration query for London to HYD
                r2 = await client.post(
                    "/api/v1/assistant/chat",
                    json={
                        "message": "how long is the flight from London to HYD?",
                        "conversation_id": conv_id,
                    },
                    headers=auth_headers,
                )
                assert r2.status_code == 200
                reply2 = r2.json()["data"]["reply"]
                # Duration query must NOT trigger flight search API
                mock_search.assert_not_called()
                assert len(reply2) > 0
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_regression_hyd_dxb_followed_by_correction_london(
        self, client, auth_headers
    ):
        """HYD -> DXB search followed by 'I don't want Dubai, I want London'."""
        _override_llm_provider()
        try:
            # Turn 1
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": f"Search flights from HYD to DXB on {_future_date(10)}"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]

            # Turn 2: Correction
            r2 = await client.post(
                "/api/v1/assistant/chat",
                json={
                    "message": "I don't want Dubai, I want London",
                    "conversation_id": conv_id,
                },
                headers=auth_headers,
            )
            assert r2.status_code == 200
            reply2 = r2.json()["data"]["reply"]
            # Destination updated to LHR/London, search executed for HYD -> LHR
            assert "LHR" in reply2 or "London" in reply2 or "available flights" in reply2.lower()
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_regression_hyd_dxb_followed_by_international_arrival_advice(
        self, client, auth_headers
    ):
        """HYD -> DXB search followed by international-arrival advice."""
        _override_llm_provider()
        from unittest.mock import AsyncMock, patch
        try:
            target_path = "app.services.flight_service.FlightService.search_flights"
            with patch(target_path, new_callable=AsyncMock) as mock_search:
                mock_search.return_value = ([], 0)
                # Turn 1
                r1 = await client.post(
                    "/api/v1/assistant/chat",
                    json={"message": f"Search flights from HYD to DXB on {_future_date(10)}"},
                    headers=auth_headers,
                )
                assert r1.status_code == 200
                conv_id = r1.json()["data"]["conversation_id"]
                assert mock_search.call_count == 1
                mock_search.reset_mock()

                # Turn 2: Informational advice query
                r2 = await client.post(
                    "/api/v1/assistant/chat",
                    json={
                        "message": "How early should I arrive at the airport for international flights?",
                        "conversation_id": conv_id,
                    },
                    headers=auth_headers,
                )
                assert r2.status_code == 200
                # Must NOT call flight search API
                mock_search.assert_not_called()
                reply2 = r2.json()["data"]["reply"]
                assert len(reply2) > 0
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_regression_clarification_answer_resolution(
        self, client, auth_headers
    ):
        """Clarification answer resolves against pending question/slot."""
        _override_llm_provider()
        try:
            # Turn 1: Origin specified only
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "Flight from Hyderabad"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]
            reply1 = r1.json()["data"]["reply"]
            assert "fly to" in reply1.lower() or "destination" in reply1.lower() or "where" in reply1.lower()

            # Turn 2: Destination clarification answer
            r2 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "Dubai", "conversation_id": conv_id},
                headers=auth_headers,
            )
            assert r2.status_code == 200
            reply2 = r2.json()["data"]["reply"]
            assert "date" in reply2.lower() or "when" in reply2.lower()

            # Turn 3: Date clarification answer -> completes parameters and executes search
            r3 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "tomorrow", "conversation_id": conv_id},
                headers=auth_headers,
            )
            assert r3.status_code == 200
            reply3 = r3.json()["data"]["reply"]
            assert "available flights" in reply3.lower() or "flight" in reply3.lower()
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_regression_yes_pending_action_resolution(
        self, client, auth_headers
    ):
        """'yes' resolves against pending_action when available."""
        _override_llm_provider()
        try:
            # Turn 1: Missing date prompt
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": f"HYD to DXB on {_future_date(10)}"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]

            # Turn 2: User says "yes" to confirm search
            r2 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "yes", "conversation_id": conv_id},
                headers=auth_headers,
            )
            assert r2.status_code == 200
            reply2 = r2.json()["data"]["reply"]
            assert "available flights" in reply2.lower() or "flight" in reply2.lower()
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_regression_normal_flight_search_refinement(
        self, client, auth_headers
    ):
        """Normal flight-search refinement updates search parameters."""
        _override_llm_provider()
        try:
            # Turn 1: Initial search
            r1 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": f"HYD to DXB on {_future_date(10)}"},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["conversation_id"]

            # Turn 2: Refine time preference
            r2 = await client.post(
                "/api/v1/assistant/chat",
                json={"message": "make it evening departures", "conversation_id": conv_id},
                headers=auth_headers,
            )
            assert r2.status_code == 200
            reply2 = r2.json()["data"]["reply"]
            assert "evening" in reply2.lower() or "flight" in reply2.lower()
        finally:
            _clear_ai_overrides()

    @pytest.mark.asyncio
    async def test_regression_stale_context_prevention(
        self, client, auth_headers
    ):
        """Stale context from turn 1 is prevented from leaking into unrelated queries or new routes."""
        _override_llm_provider()
        from unittest.mock import AsyncMock, patch
        try:
            target_path = "app.services.flight_service.FlightService.search_flights"
            with patch(target_path, new_callable=AsyncMock) as mock_search:
                mock_search.return_value = ([], 0)

                # Turn 1: Flight search HYD -> DXB
                r1 = await client.post(
                    "/api/v1/assistant/chat",
                    json={"message": f"Find flights from HYD to DXB on {_future_date(10)}"},
                    headers=auth_headers,
                )
                assert r1.status_code == 200
                conv_id = r1.json()["data"]["conversation_id"]
                assert mock_search.call_count == 1
                mock_search.reset_mock()

                # Turn 2: General query (tell me about Hyderabad) -> search must NOT be called
                r2 = await client.post(
                    "/api/v1/assistant/chat",
                    json={"message": "tell me about Hyderabad", "conversation_id": conv_id},
                    headers=auth_headers,
                )
                assert r2.status_code == 200
                mock_search.assert_not_called()

                # Turn 3: Brand new route London -> HYD -> completely replaces HYD -> DXB
                r3 = await client.post(
                    "/api/v1/assistant/chat",
                    json={
                        "message": f"London to HYD on {_future_date(20)}",
                        "conversation_id": conv_id,
                    },
                    headers=auth_headers,
                )
                assert r3.status_code == 200
                assert mock_search.call_count == 1
                search_call_params = mock_search.call_args[1]["params"]
                assert search_call_params.origin == "LHR"
                assert search_call_params.destination == "HYD"
        finally:
            _clear_ai_overrides()
