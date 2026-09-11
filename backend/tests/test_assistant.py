import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database.session import Base
from app.core.config import settings
from app.core.dependencies import get_db, get_current_user
from app.models import user, conversation, message
from app.schemas.assistant import AssistantChatRequest, AssistantResponse, FlightIntent
from app.schemas.flight import FlightResponse
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_assistant.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    yield TestingSessionLocal()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = override_get_db

    # Override get_current_user to return a mock user for authenticated endpoints
    class MockUser:
        id = "test-user"
        email = "test@example.com"
        is_active = True

    def override_get_current_user():
        return MockUser()

    app.dependency_overrides[get_current_user] = override_get_current_user
    yield TestClient(app)
    app.dependency_overrides.clear()

class TestAssistantAPI:
    """Test cases for the assistant API endpoint."""

    @pytest.mark.parametrize("message", ["what can you do", "what are your features", "how can you help"])
    def test_assistant_capabilities_do_not_request_flight_fields(self, client, message):
        response = client.post("/api/v1/assistant/chat", json={"message": message})
        assert response.status_code == 200
        data = response.json()
        assert data["requires_clarification"] is False
        assert "flights page" in data["message"].lower()
        assert "what city" not in data["message"].lower()

    def test_assistant_general_question_is_answered_directly(self, client):
        response = client.post("/api/v1/assistant/chat", json={"message": "What is a nonstop flight?"})
        assert response.status_code == 200
        assert "without landing" in response.json()["message"].lower()

    def test_assistant_search_missing_date_asks_only_for_date(self, client):
        response = client.post(
            "/api/v1/assistant/chat",
            json={"message": "Find cheap flights from Hyderabad to Delhi"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["requires_clarification"] is True
        assert "date" in data["message"].lower() or "when" in data["message"].lower()
        assert "origin" not in data["message"].lower()

    def test_assistant_date_follow_up_is_classified_as_search(self):
        service = __import__("app.services.assistant", fromlist=["AssistantService"]).AssistantService
        assistant = service.__new__(service)
        history = [type("Message", (), {"role": "user", "content": "Find cheap flights from Hyderabad to Delhi"})()]
        assert assistant._classify_intent("September 29, 2026", history) == "FLIGHT_SEARCH"

    def test_assistant_correction_is_not_routed_to_search(self, client):
        response = client.post(
            "/api/v1/assistant/chat",
            json={"message": "I can get the flights from the Flights page."},
        )
        assert response.status_code == 200
        data = response.json()
        assert "better place" in data["message"].lower()
        assert data["requires_clarification"] is False

    def test_assistant_updates_destination_from_correction(self, client):
        service = __import__("app.services.assistant", fromlist=["AssistantService"]).AssistantService
        assistant = service.__new__(service)
        previous = [
            type("Message", (), {"role": "user", "content": "Find flights from HYD to BLR on September 29"})()
        ]
        intent = FlightIntent(intent="FLIGHT_SEARCH", origin="HYD", destination=None, departure_date=None)
        merged = assistant._merge_context(intent, previous, "Actually, make that Mumbai.")
        assert merged.origin == "HYD"
        assert merged.destination == "BOM"
        assert merged.departure_date is not None

    @pytest.mark.parametrize("message", ["hi", "hello", "hii", "hey", "good morning"])
    def test_assistant_handles_greetings_without_flight_fields(self, client, message):
        response = client.post(
            "/api/v1/assistant/chat",
            json={"message": message, "conversation_id": None},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["requires_clarification"] is False
        assert data["flight_results"] is None
        assert "flight assistant" in data["message"].lower()
        assert "origin" not in data["message"].lower()

    def test_assistant_answers_general_nonstop_question(self, client):
        response = client.post(
            "/api/v1/assistant/chat",
            json={"message": "What does a nonstop flight mean?"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["requires_clarification"] is False
        assert "without landing" in data["message"].lower()

    def test_assistant_endpoint_success(self, client):
        """Test successful assistant response with flight search."""
        # Mock the flight understanding service to return a complete FlightIntent
        mock_intent = FlightIntent(
            intent="flight_search",
            origin="HYD",
            destination="DEL",
            departure_date=datetime(2026, 8, 30, 10, 0, 0),
            return_date=None,
            passengers=1,
            cabin="ECONOMY",
            time_preference=None,
            price_preference=None
        )

        # Mock flight search results
        mock_flights = [
            FlightResponse(
                id="test123",
                airline="Test Air",
                flight_number="TA123",
                origin="HYD",
                destination="DEL",
                departure_time=datetime(2026, 8, 30, 10, 0, 0),
                arrival_time=datetime(2026, 8, 30, 12, 0, 0),
                duration=120,
                stops=0,
                price=4500.0,
                currency="INR"
            )
        ]

        with patch('app.services.assistant.extract_flight_intent', return_value=mock_intent) as mock_extract, \
             patch('app.services.assistant.search_flights', return_value=mock_flights) as mock_search, \
             patch('app.ai.llm.generate_structured', return_value="I found 1 flight from Hyderabad to Delhi.") as mock_llm:

            response = client.post(
                "/api/v1/assistant/chat",
                json={
                    "message": "Find me a flight from Hyderabad to Delhi tomorrow",
                    "conversation_id": None
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert "conversation_id" in data
            assert data["requires_clarification"] == False
            assert data["flight_results"] is not None
            assert len(data["flight_results"]) == 1
            assert data["flight_results"][0]["origin"] == "HYD"
            assert data["flight_results"][0]["destination"] == "DEL"

    def test_assistant_missing_origin(self, client):
        """Test assistant handling missing origin information."""
        # Mock the flight understanding service to return incomplete FlightIntent
        mock_intent = FlightIntent(
            intent="flight_search",
            origin=None,
            destination="DEL",
            departure_date=datetime(2026, 8, 30, 10, 0, 0),
            return_date=None,
            passengers=1,
            cabin="ECONOMY",
            time_preference=None,
            price_preference=None
        )

        with patch('app.services.assistant.extract_flight_intent', return_value=mock_intent) as mock_extract:
            response = client.post(
                "/api/v1/assistant/chat",
                json={
                    "message": "I want to fly to Delhi tomorrow",
                    "conversation_id": None
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["requires_clarification"] == True
            assert data["flight_results"] is None
            assert "origin" in data["message"].lower() or "from" in data["message"].lower()

    def test_assistant_missing_destination(self, client):
        """Test assistant handling missing destination information."""
        # Mock the flight understanding service to return incomplete FlightIntent
        mock_intent = FlightIntent(
            intent="flight_search",
            origin="HYD",
            destination=None,
            departure_date=datetime(2026, 8, 30, 10, 0, 0),
            return_date=None,
            passengers=1,
            cabin="ECONOMY",
            time_preference=None,
            price_preference=None
        )

        with patch('app.services.assistant.extract_flight_intent', return_value=mock_intent) as mock_extract:
            response = client.post(
                "/api/v1/assistant/chat",
                json={
                    "message": "I want to fly from Hyderabad tomorrow",
                    "conversation_id": None
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["requires_clarification"] == True
            assert data["flight_results"] is None
            assert "destination" in data["message"].lower() or "where" in data["message"].lower() or "to" in data["message"].lower()

    def test_assistant_missing_date(self, client):
        """Test assistant handling missing date information."""
        # Mock the flight understanding service to return incomplete FlightIntent
        mock_intent = FlightIntent(
            intent="flight_search",
            origin="HYD",
            destination="DEL",
            departure_date=None,
            return_date=None,
            passengers=1,
            cabin="ECONOMY",
            time_preference=None,
            price_preference=None
        )

        with patch('app.services.assistant.extract_flight_intent', return_value=mock_intent) as mock_extract:
            response = client.post(
                "/api/v1/assistant/chat",
                json={
                    "message": "I want to fly from Hyderabad to Delhi",
                    "conversation_id": None
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["requires_clarification"] == True
            assert data["flight_results"] is None
            assert "when" in data["message"].lower() or "date" in data["message"].lower()

    def test_assistant_no_flights_found(self, client):
        """Test assistant handling when no flights are found."""
        # Mock the flight understanding service to return a complete FlightIntent
        mock_intent = FlightIntent(
            intent="flight_search",
            origin="HYD",
            destination="DEL",
            departure_date=datetime(2026, 8, 30, 10, 0, 0),
            return_date=None,
            passengers=1,
            cabin="ECONOMY",
            time_preference=None,
            price_preference=None
        )

        # Mock empty flight search results
        mock_flights = []

        with patch('app.services.assistant.extract_flight_intent', return_value=mock_intent) as mock_extract, \
             patch('app.services.assistant.search_flights', return_value=mock_flights) as mock_search, \
             patch('app.ai.llm.generate_structured', return_value="I couldn't find any flights matching your search.") as mock_llm:

            response = client.post(
                "/api/v1/assistant/chat",
                json={
                    "message": "Find me a flight from Hyderabad to Delhi tomorrow",
                    "conversation_id": None
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["requires_clarification"] == False
            assert data["flight_results"] is not None
            assert len(data["flight_results"]) == 0
            assert "couldn't find" in data["message"].lower() or "no flights" in data["message"].lower()

    def test_assistant_provider_failure(self, client):
        """Test assistant handling flight provider failures."""
        # Mock the flight understanding service to return a complete FlightIntent
        mock_intent = FlightIntent(
            intent="flight_search",
            origin="HYD",
            destination="DEL",
            departure_date=datetime(2026, 8, 30, 10, 0, 0),
            return_date=None,
            passengers=1,
            cabin="ECONOMY",
            time_preference=None,
            price_preference=None
        )

        with patch('app.services.assistant.extract_flight_intent', return_value=mock_intent) as mock_extract, \
             patch('app.services.assistant.search_flights', side_effect=Exception("Provider error")) as mock_search:

            response = client.post(
                "/api/v1/assistant/chat",
                json={
                    "message": "Find me a flight from Hyderabad to Delhi tomorrow",
                    "conversation_id": None
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["requires_clarification"] == False
            assert data["flight_results"] is None
            assert "unable to retrieve" in data["message"].lower() or "try again" in data["message"].lower()

    def test_assistant_understanding_failure(self, client):
        """Test assistant handling flight understanding failures."""
        with patch('app.services.assistant.extract_flight_intent', side_effect=Exception("AI error")) as mock_extract:
            response = client.post(
                "/api/v1/assistant/chat",
                json={
                    "message": "Find me a flight from Hyderabad to Delhi tomorrow",
                    "conversation_id": None
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["requires_clarification"] == False
            assert data["flight_results"] is None
            assert "provider is unavailable" in data["message"].lower() or "couldn't understand" in data["message"].lower()

    def test_assistant_provider_failure_is_reported(self, client):
        """Provider failures remain distinguishable from invalid user intent."""
        with patch(
            'app.services.assistant.extract_flight_intent',
            side_effect=RuntimeError("AI understanding failed: Gemini model 'gemini-2.5-flash' failed to generate content: model unavailable")
        ):
            response = client.post(
                "/api/v1/assistant/chat",
                json={"message": "Find a flight from Hyderabad to Delhi tomorrow"}
            )

        assert response.status_code == 200
        assert "AI understanding provider is unavailable" in response.json()["message"]
        assert "gemini-2.5-flash" in response.json()["message"]

    def test_assistant_llm_response_failure(self, client):
        """Test assistant handling LLM response generation failures."""
        # Mock the flight understanding service to return a complete FlightIntent
        mock_intent = FlightIntent(
            intent="flight_search",
            origin="HYD",
            destination="DEL",
            departure_date=datetime(2026, 8, 30, 10, 0, 0),
            return_date=None,
            passengers=1,
            cabin="ECONOMY",
            time_preference=None,
            price_preference=None
        )

        # Mock flight search results
        mock_flights = [
            FlightResponse(
                id="test123",
                airline="Test Air",
                flight_number="TA123",
                origin="HYD",
                destination="DEL",
                departure_time=datetime(2026, 8, 30, 10, 0, 0),
                arrival_time=datetime(2026, 8, 30, 12, 0, 0),
                duration=120,
                stops=0,
                price=4500.0,
                currency="INR"
            )
        ]

        with patch('app.services.assistant.extract_flight_intent', return_value=mock_intent) as mock_extract, \
             patch('app.services.assistant.search_flights', return_value=mock_flights) as mock_search, \
             patch('app.ai.llm.generate_structured', side_effect=Exception("LLM error")) as mock_llm:

            response = client.post(
                "/api/v1/assistant/chat",
                json={
                    "message": "Find me a flight from Hyderabad to Delhi tomorrow",
                    "conversation_id": None
                }
            )

            assert response.status_code == 200
            data = response.json()
            # Should still return flight results even if LLM fails
            assert data["requires_clarification"] == False
            assert data["flight_results"] is not None
            assert len(data["flight_results"]) == 1
            # Should have a fallback message
            assert "found" in data["message"].lower() and "flight" in data["message"].lower()

    def test_assistant_requires_authentication(self, client):
        """Test that authentication is required for assistant endpoint."""
        # Remove the authentication override for this test
        app.dependency_overrides.clear()

        response = client.post(
            "/api/v1/assistant/chat",
            json={
                "message": "Find me a flight from Hyderabad to Delhi tomorrow",
                "conversation_id": None
            }
        )

        # Should return 401 when no authentication provided
        assert response.status_code == 401

        # Restore the override for other tests
        def override_get_current_user():
            class MockUser:
                id = "test-user"
                email = "test@example.com"
                is_active = True
            return MockUser()
        app.dependency_overrides[get_current_user] = override_get_current_user

if __name__ == "__main__":
    pytest.main([__file__])