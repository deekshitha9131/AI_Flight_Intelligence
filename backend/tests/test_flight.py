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
from app.services.flight import DuffelProvider
from datetime import datetime, timedelta

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_flight.db"

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
    yield TestClient(app)
    app.dependency_overrides.clear()

def test_flight_search_request_schema():
    """Test that the FlightSearchRequest schema works correctly."""
    # Valid request
    request = FlightSearchRequest(
        origin="JFK",
        destination="LAX",
        departure_date=datetime.now() + timedelta(days=7),
        passengers=1,
        cabin_class="ECONOMY",
        currency="USD"
    )
    assert request.origin == "JFK"
    assert request.destination == "LAX"
    assert request.passengers == 1
    assert request.cabin_class == "ECONOMY"
    assert request.currency == "USD"
    assert request.return_date is None

    # Valid request with return date
    request_roundtrip = FlightSearchRequest(
        origin="JFK",
        destination="LAX",
        departure_date=datetime.now() + timedelta(days=7),
        return_date=datetime.now() + timedelta(days=14),
        passengers=2,
        cabin_class="BUSINESS",
        currency="USD"
    )
    assert request_roundtrip.return_date is not None

def test_flight_search_request_validation():
    """Test validation of FlightSearchRequest."""
    # Invalid IATA codes (too short)
    with pytest.raises(Exception):
        FlightSearchRequest(
            origin="JFK",  # Valid
            destination="LA",  # Invalid - too short
            departure_date=datetime.now() + timedelta(days=7),
            passengers=1,
            cabin_class="ECONOMY",
            currency="USD"
        )

    # Invalid IATA codes (too long)
    with pytest.raises(Exception):
        FlightSearchRequest(
            origin="JFK",
            destination="LAXX",  # Invalid - too long
            departure_date=datetime.now() + timedelta(days=7),
            passengers=1,
            cabin_class="ECONOMY",
            currency="USD"
        )

    # Invalid passengers (too many)
    with pytest.raises(Exception):
        FlightSearchRequest(
            origin="JFK",
            destination="LAX",
            departure_date=datetime.now() + timedelta(days=7),
            passengers=10,  # Invalid - more than 9
            cabin_class="ECONOMY",
            currency="USD"
        )

    # Invalid currency (too short)
    with pytest.raises(Exception):
        FlightSearchRequest(
            origin="JFK",
            destination="LAX",
            departure_date=datetime.now() + timedelta(days=7),
            passengers=1,
            cabin_class="ECONOMY",
            currency="US"  # Invalid - too short
        )

def test_flight_response_schema():
    """Test that the FlightResponse schema works correctly."""
    from datetime import datetime
    flight = FlightResponse(
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
    assert flight.id == "test123"
    assert flight.airline == "Test Air"
    assert flight.flight_number == "TA123"
    assert flight.origin == "JFK"
    assert flight.destination == "LAX"
    assert flight.price == 299.99
    assert flight.currency == "USD"

def _duffel_segment(segment_id, number, origin, destination, departure, arrival, carrier="6E", provider_number=False):
    return {
        "id": segment_id,
        "marketing_carrier": {"iata_code": carrier, "name": "Test Air"},
        ("marketing_carrier_flight_number" if provider_number else "number"): f"{carrier}{number}" if provider_number else number,
        "origin": {"iata_code": origin},
        "destination": {"iata_code": destination},
        "departing_at": departure,
        "arriving_at": arrival,
    }

def _duffel_offer(offer_id, slices, amount):
    return {"id": offer_id, "slices": slices, "total_amount": str(amount), "total_currency": "USD"}

def test_provider_groups_same_itinerary_and_preserves_fares():
    provider = DuffelProvider()
    request = FlightSearchRequest(
        origin="HYD", destination="DEL", departure_date=datetime(2026, 9, 29),
        passengers=1, cabin_class="ECONOMY", currency="USD"
    )
    base_slice = {"origin": {"iata_code": "HYD"}, "destination": {"iata_code": "DEL"}, "segments": [
        _duffel_segment("s1", "123", "HYD", "DEL", "2026-09-29T08:00:00Z", "2026-09-29T10:00:00Z")
    ]}
    flights = provider._normalize_offers({"data": [
        _duffel_offer("offer-a", [base_slice], 100),
        _duffel_offer("offer-b", [base_slice], 120),
    ]}, request)
    assert len(flights) == 1
    assert flights[0].price == 100
    assert len(flights[0].fare_options) == 2

def test_provider_keeps_different_departures_as_distinct_itineraries():
    provider = DuffelProvider()
    request = FlightSearchRequest(
        origin="HYD", destination="DEL", departure_date=datetime(2026, 9, 29),
        passengers=1, cabin_class="ECONOMY", currency="USD"
    )
    def make_slice(departure, arrival, number):
        return {"origin": {"iata_code": "HYD"}, "destination": {"iata_code": "DEL"}, "segments": [
            _duffel_segment(f"{number}-segment", number, "HYD", "DEL", departure, arrival)
        ]}
    flights = provider._normalize_offers({"data": [
        _duffel_offer("offer-a", [make_slice("2026-09-29T08:00:00Z", "2026-09-29T10:00:00Z", "123")], 100),
        _duffel_offer("offer-b", [make_slice("2026-09-29T10:00:00Z", "2026-09-29T12:00:00Z", "123")], 110),
    ]}, request)
    assert len(flights) == 2

def test_provider_limits_sorted_unique_itineraries_after_deduplication():
    provider = DuffelProvider()
    request = FlightSearchRequest(
        origin="HYD", destination="DEL", departure_date=datetime(2026, 9, 29),
        passengers=1, cabin_class="ECONOMY", currency="USD"
    )

    def make_offer(index, price):
        departure_hour = 1 + index
        return _duffel_offer(f"offer-{index}", [{
            "origin": {"iata_code": "HYD"},
            "destination": {"iata_code": "DEL"},
            "segments": [_duffel_segment(
                f"segment-{index}", str(100 + index), "HYD", "DEL",
                f"2026-09-29T{departure_hour:02d}:00:00Z",
                f"2026-09-29T{departure_hour + 2:02d}:00:00Z",
            )],
        }], price)

    flights = provider._normalize_offers(
        {"data": [make_offer(index, 200 - index) for index in range(20)]}, request
    )

    assert len(flights) == 15
    assert [flight.price for flight in flights] == sorted(flight.price for flight in flights)
    assert len({flight.flight_number for flight in flights}) == 15

def test_provider_preserves_connections_and_round_trip_as_one_itinerary():
    provider = DuffelProvider()
    request = FlightSearchRequest(
        origin="HYD", destination="DEL", departure_date=datetime(2026, 9, 29),
        return_date=datetime(2026, 10, 3), passengers=1, cabin_class="ECONOMY", currency="USD"
    )
    outbound = {"origin": {"iata_code": "HYD"}, "destination": {"iata_code": "DEL"}, "segments": [
        _duffel_segment("out-1", "123", "HYD", "BOM", "2026-09-29T08:00:00Z", "2026-09-29T10:00:00Z"),
        _duffel_segment("out-2", "456", "BOM", "DEL", "2026-09-29T11:00:00Z", "2026-09-29T13:00:00Z"),
    ]}
    inbound = {"origin": {"iata_code": "DEL"}, "destination": {"iata_code": "HYD"}, "segments": [
        _duffel_segment("ret-1", "789", "DEL", "HYD", "2026-10-03T08:00:00Z", "2026-10-03T10:00:00Z", "AI"),
    ]}
    flights = provider._normalize_offers({"data": [_duffel_offer("round-trip", [outbound, inbound], 300)]}, request)
    assert len(flights) == 1
    assert len(flights[0].segments) == 2
    assert flights[0].stops == 1
    assert len(flights[0].return_segments) == 1

def test_provider_accepts_duffel_marketing_carrier_flight_number():
    provider = DuffelProvider()
    request = FlightSearchRequest(
        origin="HYD", destination="DEL", departure_date=datetime(2026, 9, 29),
        passengers=1, cabin_class="ECONOMY", currency="USD"
    )
    offer = _duffel_offer("offer-live-shape", [{
        "origin": {"iata_code": "HYD"},
        "destination": {"iata_code": "DEL"},
        "segments": [_duffel_segment("s-live", "123", "HYD", "DEL", "2026-09-29T08:00:00Z", "2026-09-29T10:00:00Z", provider_number=True)],
    }], 100)
    flights = provider._normalize_offers({"data": [offer]}, request)
    assert len(flights) == 1
    assert flights[0].flight_number == "6E123"

@pytest.mark.skip(reason="Requires actual Duffel API credentials")
def test_flight_provider_integration():
    """Test flight provider integration (requires real API key)."""
    # This test would require actual Duffel API credentials
    # For now, we skip it since we don't have real credentials in test environment
    pass

def test_flight_endpoint_without_provider(client):
    """Test that the flight endpoint handles missing provider gracefully."""
    from datetime import timedelta

    # First test authentication requirement
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

    # Then test with authentication but missing provider
    # Temporarily override the API key to simulate missing credentials
    original_key = settings.FLIGHT_API_KEY
    settings.FLIGHT_API_KEY = "your-test-key"

    try:
        # Test with authentication but missing provider credentials
        # We'll use the test client's ability to override dependencies
        # Create a simple mock user object
        class MockUser:
            id = "test-user"
            email = "test@example.com"
            is_active = True

        def override_get_current_user():
            return MockUser()

        app.dependency_overrides[get_current_user] = override_get_current_user

        # Test with authentication but missing provider credentials
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
        # Should return 503 when provider is not configured
        assert response.status_code == 503
        assert "Flight search unavailable" in response.json()["detail"]

        # Clean up override
        app.dependency_overrides.clear()
    finally:
        # Restore original key
        settings.FLIGHT_API_KEY = original_key