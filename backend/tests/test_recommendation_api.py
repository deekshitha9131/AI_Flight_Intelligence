import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database.session import Base
from app.core.config import settings
from app.core.dependencies import get_db, get_current_user
from app.schemas.flight import FlightResponse, FlightSearchRequest
from app.models import user, preference
from unittest.mock import patch, AsyncMock
from datetime import datetime, timedelta

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_recommendation.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, bind=engine)

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

@pytest.fixture
def sample_flights():
    """Create sample flight responses for testing."""
    base_time = datetime(2026, 8, 30, 10, 0, 0)  # 10:00 AM (morning)
    return [
        FlightResponse(
            id="flight1",
            airline="Airline A",
            flight_number="AA100",
            origin="JFK",
            destination="LAX",
            departure_time=base_time,
            arrival_time=base_time + timedelta(hours=5),
            duration=300,  # 5 hours
            stops=0,
            price=200.0,
            currency="USD"
        ),
        FlightResponse(
            id="flight2",
            airline="Airline B",
            flight_number="BB200",
            origin="JFK",
            destination="LAX",
            departure_time=base_time + timedelta(hours=2),
            arrival_time=base_time + timedelta(hours=7),
            duration=300,  # 5 hours
            stops=1,
            price=180.0,
            currency="USD"
        )
    ]

class TestRecommendationAPI:
    """Test cases for the flight recommendation API endpoint."""

    def test_get_flight_recommendations_success(self, client, sample_flights):
        """Test successful flight recommendation."""
        with patch('app.api.v1.recommendations.RecommendationService') as mock_service_class:
            # Setup mock service instance
            mock_service = Mock()
            mock_service_class.return_value = mock_service

            # Setup mock return value
            mock_service.rank_flights.return_value = [
                {
                    "flight": sample_flights[1].model_dump(mode='json'),
                    "score": 0.6,
                    "explanation": "Recommended because it has a relatively low price and one stop."
                },
                {
                    "flight": sample_flights[0].model_dump(mode='json'),
                    "score": 0.4,
                    "explanation": "Recommended because it has a moderate price and no stops."
                }
            ]

            response = client.post(
                "/api/v1/recommendations/",
                json={"flights": [flight.model_dump(mode='json') for flight in sample_flights]}
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["score"] == 0.6
            assert data[1]["score"] == 0.4
            assert "Recommended because" in data[0]["explanation"]

            # Verify the service was called correctly
            mock_service_class.assert_called_once()
            mock_service.rank_flights.assert_called_once()

    def test_get_flight_recommendations_empty_list(self, client):
        """Test recommendation with empty flight list."""
        response = client.post(
            "/api/v1/recommendations/",
            json={"flights": []}
        )

        assert response.status_code == 400
        assert "No flights provided for recommendation" in response.json()["detail"]

    def test_get_flight_recommendations_no_auth(self, client):
        """Test that authentication is required for recommendations."""
        # Remove the authentication override for this test
        app.dependency_overrides.clear()

        response = client.post(
            "/api/v1/recommendations/",
            json=[]
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

    def test_search_and_recommend_flights_success(self, client):
        """Test successful search and recommendation."""
        # Mock the flight search service
        mock_flights = [
            FlightResponse(
                id="flight1",
                airline="Test Air",
                flight_number="TA100",
                origin="JFK",
                destination="LAX",
                departure_time=datetime.now(),
                arrival_time=datetime.now() + timedelta(hours=5),
                duration=300,
                stops=0,
                price=200.0,
                currency="USD"
            )
        ]

        with patch('app.api.v1.recommendations.search_flights', return_value=mock_flights) as mock_search:
            with patch('app.api.v1.recommendations.RecommendationService') as mock_service_class:
                # Setup mock service instance
                mock_service = Mock()
                mock_service_class.return_value = mock_service

                # Setup mock return value: single flight gets neutral score 0.5
                mock_service.rank_flights.return_value = [
                    {
                        "flight": mock_flights[0].model_dump(),
                        "score": 0.5,
                        "explanation": "Recommended because it has a moderate price, it has a reasonable travel duration, and it has no stops."
                    }
                ]

                search_request = {
                    "origin": "JFK",
                    "destination": "LAX",
                    "departure_date": (datetime.now() + timedelta(days=7)).isoformat(),
                    "passengers": 1,
                    "cabin_class": "ECONOMY",
                    "currency": "USD"
                }

                response = client.post(
                    "/api/v1/recommendations/search",
                    json=search_request
                )

                assert response.status_code == 200
                data = response.json()
                assert len(data) == 1
                assert data[0]["score"] == 0.5
                assert "Recommended because" in data[0]["explanation"]
                # Check the specific explanation for single flight with no preference
                assert data[0]["explanation"] == "Recommended because it has a moderate price, it has a reasonable travel duration, and it has no stops."

                # Verify both services were called
                mock_search.assert_called_once()
                mock_service_class.assert_called_once()
                mock_service.rank_flights.assert_called_once()

    def test_search_and_recommend_flights_no_results(self, client):
        """Test search and recommendation when no flights are found."""
        with patch('app.api.v1.recommendations.search_flights', return_value=[]):
            search_request = {
                "origin": "JFK",
                "destination": "LAX",
                "departure_date": (datetime.now() + timedelta(days=7)).isoformat(),
                "passengers": 1,
                "cabin_class": "ECONOMY",
                "currency": "USD"
            }

            response = client.post(
                "/api/v1/recommendations/search",
                json=search_request
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 0  # Should return empty list

    def test_search_and_recommend_flights_provider_error(self, client):
        """Test search and recommendation handles provider errors gracefully."""
        with patch('app.services.flight.search_flights', side_effect=Exception("Provider error")):
            search_request = {
                "origin": "JFK",
                "destination": "LAX",
                "departure_date": (datetime.now() + timedelta(days=7)).isoformat(),
                "passengers": 1,
                "cabin_class": "ECONOMY",
                "currency": "USD"
            }

            response = client.post(
                "/api/v1/recommendations/search",
                json=search_request
            )

            assert response.status_code == 500
            assert "Search and recommendation service unavailable" in response.json()["detail"]

    def test_search_and_recommend_flights_no_auth(self, client):
        """Test that authentication is required for search and recommendation."""
        # Remove the authentication override for this test
        app.dependency_overrides.clear()

        search_request = {
            "origin": "JFK",
            "destination": "LAX",
            "departure_date": (datetime.now() + timedelta(days=7)).isoformat(),
            "passengers": 1,
            "cabin_class": "ECONOMY",
            "currency": "USD"
        }

        response = client.post(
            "/api/v1/recommendations/search",
            json=search_request
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