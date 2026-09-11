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
from app.models import user, conversation, message, flight_search, prediction, preference
from app.schemas.flight import FlightSearchRequest, FlightResponse
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_flight_api.db"

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

class TestFlightSearchAPI:
    """Test cases for the flight search API endpoint."""

    def test_search_flights_success(self, client):
        """Test successful flight search returns normalized flight data."""
        # Mock the flight service to return sample flight data
        mock_flights = [
            FlightResponse(
                id="test123",
                airline="Test Air",
                flight_number="TA123",
                origin="JFK",
                destination="LAX",
                departure_time=datetime.now(),
                arrival_time=datetime.now() + timedelta(hours=5),
                duration=300,
                stops=0,
                price=299.99,
                currency="USD"
            )
        ]

        # Patch the search_flights function where it's imported and used
        with patch('app.api.v1.flight.search_flights', return_value=mock_flights) as mock_search:
            print(f"Mock search_flights called: {mock_search}")
            print(f"Mock search_flights is called: {mock_search.called}")
            response = client.post(
                "/api/v1/flights/search",
                json={
                    "origin": "JFK",
                    "destination": "LAX",
                    "departure_date": (datetime.now() + timedelta(days=7)).isoformat(),
                    "passengers": 1,
                    "cabin_class": "ECONOMY",
                    "currency": "USD"
                }
            )
            print(f"Mock search_flights called: {mock_search.called}")
            if mock_search.called:
                print(f"Mock call args: {mock_search.call_args}")
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["origin"] == "JFK"
            assert data[0]["destination"] == "LAX"
            assert data[0]["price"] == 299.99
            assert data[0]["currency"] == "USD"

    def test_search_flights_empty_results(self, client):
        """Test flight search with no results returns empty list."""
        with patch('app.api.v1.flight.search_flights', return_value=[]) as mock_search:
            print(f"Mock search_flights called: {mock_search.called}")
            response = client.post(
                "/api/v1/flights/search",
                json={
                    "origin": "JFK",
                    "destination": "LAX",
                    "departure_date": (datetime.now() + timedelta(days=7)).isoformat(),
                    "passengers": 1,
                    "cabin_class": "ECONOMY",
                    "currency": "USD"
                }
            )
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 0

    def test_search_flights_provider_error(self, client):
        """Test flight search handles provider errors gracefully."""
        with patch('app.api.v1.flight.search_flights', side_effect=Exception("Provider error")):
            response = client.post(
                "/api/v1/flights/search",
                json={
                    "origin": "JFK",
                    "destination": "LAX",
                    "departure_date": (datetime.now() + timedelta(days=7)).isoformat(),
                    "passengers": 1,
                    "cabin_class": "ECONOMY",
                    "currency": "USD"
                }
            )

            assert response.status_code == 503
            assert "Flight search unavailable" in response.json()["detail"]

    def test_search_flights_missing_authentication(self, client):
        """Test that authentication is required for flight search."""
        # Remove the authentication override for this test
        app.dependency_overrides.clear()

        response = client.post(
            "/api/v1/flights/search",
            json={
                "origin": "JFK",
                "destination": "LAX",
                "departure_date": (datetime.now() + timedelta(days=7)).isoformat(),
                "passengers": 1,
                "cabin_class": "ECONOMY",
                "currency": "USD"
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

    def test_search_flights_invalid_origin(self, client):
        """Test that invalid origin IATA code is rejected."""
        response = client.post(
            "/api/v1/flights/search",
            json={
                "origin": "JF",  # Too short (2 chars instead of 3)
                "destination": "LAX",
                "departure_date": (datetime.now() + timedelta(days=7)).isoformat(),
                "passengers": 1,
                "cabin_class": "ECONOMY",
                "currency": "USD"
            }
        )

        # Should return 422 for validation error
        assert response.status_code == 422

        # Verify provider was not called by checking that we don't get 503
        assert response.status_code != 503

    def test_search_flights_invalid_destination(self, client):
        """Test that invalid destination IATA code is rejected."""
        response = client.post(
            "/api/v1/flights/search",
            json={
                "origin": "JFK",
                "destination": "LAXX",  # Too long
                "departure_date": (datetime.now() + timedelta(days=7)).isoformat(),
                "passengers": 1,
                "cabin_class": "ECONOMY",
                "currency": "USD"
            }
        )

        # Should return 422 for validation error
        assert response.status_code == 422

    def test_search_flights_same_origin_destination(self, client):
        """Test that same origin and destination is rejected."""
        with patch('app.api.v1.flight.search_flights') as mock_search:
            response = client.post(
                "/api/v1/flights/search",
                json={
                    "origin": "JFK",
                    "destination": "JFK",  # Same as origin
                    "departure_date": (datetime.now() + timedelta(days=7)).isoformat(),
                    "passengers": 1,
                    "cabin_class": "ECONOMY",
                    "currency": "USD"
                }
            )

            # Should return 400 for bad request (business logic validation)
            assert response.status_code == 400
            # Verify provider was not called
            mock_search.assert_not_called()

    def test_search_flights_invalid_passengers(self, client):
        """Test that invalid passenger count is rejected."""
        # Too many passengers
        response = client.post(
            "/api/v1/flights/search",
            json={
                "origin": "JFK",
                "destination": "LAX",
                "departure_date": (datetime.now() + timedelta(days=7)).isoformat(),
                "passengers": 10,  # More than allowed 9
                "cabin_class": "ECONOMY",
                "currency": "USD"
            }
        )
        assert response.status_code == 422

        # Too few passengers
        response = client.post(
            "/api/v1/flights/search",
            json={
                "origin": "JFK",
                "destination": "LAX",
                "departure_date": (datetime.now() + timedelta(days=7)).isoformat(),
                "passengers": 0,  # Less than minimum 1
                "cabin_class": "ECONOMY",
                "currency": "USD"
            }
        )
        assert response.status_code == 422

    def test_search_flights_invalid_currency(self, client):
        """Test that invalid currency code is rejected."""
        response = client.post(
            "/api/v1/flights/search",
            json={
                "origin": "JFK",
                "destination": "LAX",
                "departure_date": (datetime.now() + timedelta(days=7)).isoformat(),
                "passengers": 1,
                "cabin_class": "ECONOMY",
                "currency": "US"  # Too short
            }
        )

        # Should return 422 for validation error
        assert response.status_code == 422

    def test_search_flights_roundtrip(self, client):
        """Test flight search with return date (roundtrip)."""
        mock_flights = [
            FlightResponse(
                id="outbound123",
                airline="Test Air",
                flight_number="TA123",
                origin="JFK",
                destination="LAX",
                departure_time=datetime.now(),
                arrival_time=datetime.now() + timedelta(hours=5),
                duration=300,
                stops=0,
                price=150.00,
                currency="USD"
            ),
            FlightResponse(
                id="return123",
                airline="Test Air",
                flight_number="TA456",
                origin="LAX",
                destination="JFK",
                departure_time=datetime.now() + timedelta(days=7),
                arrival_time=datetime.now() + timedelta(days=7, hours=5),
                duration=300,
                stops=0,
                price=150.00,
                currency="USD"
            )
        ]

        with patch('app.api.v1.flight.search_flights', return_value=mock_flights) as mock_search:
            response = client.post(
                "/api/v1/flights/search",
                json={
                    "origin": "JFK",
                    "destination": "LAX",
                    "departure_date": (datetime.now() + timedelta(days=7)).isoformat(),
                    "return_date": (datetime.now() + timedelta(days=14)).isoformat(),
                    "passengers": 1,
                    "cabin_class": "ECONOMY",
                    "currency": "USD"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            # First flight should be outbound
            assert data[0]["origin"] == "JFK"
            assert data[0]["destination"] == "LAX"
            # Second flight should be return
            assert data[1]["origin"] == "LAX"
            assert data[1]["destination"] == "JFK"

if __name__ == "__main__":
    pytest.main([__file__])