import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import Mock, MagicMock
from sqlalchemy.orm import Session
from app.services.recommendation import RecommendationService, RECOMMENDATION_TOP_N
from app.schemas.flight import FlightResponse
from app.models.preference import Preference
from datetime import datetime, timedelta


@pytest.fixture
def db_session():
    """Create a mock database session for testing."""
    return Mock(spec=Session)


@pytest.fixture
def recommendation_service(db_session):
    """Create a RecommendationService instance for testing."""
    return RecommendationService(db_session)


@pytest.fixture
def sample_flights():
    """Create sample flight responses for testing."""
    # Use a fixed time for deterministic testing
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
            duration=300,  #  # 5 hours
            stops=1,
            price=180.0,
            currency="USD"
        ),
        FlightResponse(
            id="flight3",
            airline="Airline C",
            flight_number="CC300",
            origin="JFK",
            destination="LAX",
            departure_time=base_time + timedelta(hours=4),
            arrival_time=base_time + timedelta(hours=9),
            duration=300,  # 5 hours
            stops=2,
            price=150.0,
            currency="USD"
        )
    ]


def test_recommendation_service_initialization(recommendation_service):
    """Test that the recommendation service initializes correctly."""
    assert recommendation_service is not None
    assert hasattr(recommendation_service, 'weights')
    assert recommendation_service.weights['price'] == 0.40
    assert recommendation_service.weights['duration'] == 0.25
    assert recommendation_service.weights['stops'] == 0.20
    assert recommendation_service.weights['departure_time'] == 0.15


def test_normalize_score(recommendation_service):
    """Test the _normalize_score helper method."""
    # Test normal case
    score = recommendation_service._normalize_score(15, 10, 20)
    assert score == 0.5  # (20-15)/(20-10) = 5/10 = 0.5

    # Test minimum value (should get 1.0)
    score = recommendation_service._normalize_score(10, 10, 20)
    assert score == 1.0  # (20-10)/(20-10) = 10/10 = 1.0

    # Test maximum value (should get 0.0)
    score = recommendation_service._normalize_score(20, 10, 20)
    assert score == 0.0  # (20-20)/(20-10) = 0/10 = 0.0

    # Test edge case where min == max
    score = recommendation_service._normalize_score(15, 15, 15)
    assert score == 0.5  # Should return neutral score


def test_calculate_price_score(recommendation_service, sample_flights):
    """Test price score calculation."""
    # Flight 3 has lowest price (150) -> should get highest score
    # Flight 2 has middle price (180) -> should get middle score
    # Flight 1 has highest price (200) -> should get lowest score
    scores = recommendation_service._calculate_price_score(sample_flights)

    assert len(scores) == 3
    assert scores[2] > scores[1] > scores[0]  # flight3 > flight2 > flight1
    assert scores[2] == 1.0  # Lowest price gets score 1.0
    assert scores[0] == 0.0  # Highest price gets score 0.0


def test_calculate_duration_score(recommendation_service, sample_flights):
    """Test duration score calculation."""
    # All flights have same duration (300) -> should all get neutral score
    scores = recommendation_service._calculate_duration_score(sample_flights)

    assert len(scores) == 3
    assert all(score == 0.5 for score in scores)  # All should be 0.5


def test_calculate_stops_score(recommendation_service, sample_flights):
    """Test stops score calculation."""
    # Flight 1 has 0 stops (best) -> should get highest score
    # Flight 2 has 1 stop (middle) -> should get middle score
    # Flight 3 has 2 stops (worst) -> should get lowest score
    scores = recommendation_service._calculate_stops_score(sample_flights)

    assert len(scores) == 3
    assert scores[0] > scores[1] > scores[2]  # flight1 > flight2 > flight3
    assert scores[0] == 1.0  # Fewest stops gets score 1.0
    assert scores[2] == 0.0  # Most stops gets score 0.0


def test_calculate_departure_time_score_no_preference(recommendation_service, sample_flights, db_session):
    """Test departure time score when no user preference is set."""
    # Setup mock to return no preferences
    db_session.query.return_value.filter.return_value.first.return_value = None

    scores = recommendation_service._calculate_departure_time_score(sample_flights, "user123")

    assert len(scores) == 3
    assert all(score == 0.5 for score in scores)  # All should be neutral


def test_calculate_departure_time_score_with_preference(recommendation_service, sample_flights, db_session):
    """Test departure time score when user preference is set."""
    # Setup mock to return user preference for morning flights
    mock_preference = Mock(spec=Preference)
    mock_preference.preferred_time = "morning"
    db_session.query.return_value.filter.return_value.first.return_value = mock_preference

    # Flight times:
    # Flight 1: departs at base_time (10:00 AM) -> morning
    # Flight 2: departs at base_time + 2 hours (12:00 PM) -> afternoon
    # Flight 3: departs at base_time + 4 hours (2:00 PM) -> afternoon

    scores = recommendation_service._calculate_departure_time_score(sample_flights, "user123")

    assert len(scores) == 3
    assert scores[0] == 1.0  # Morning flight matches preference
    assert scores[1] == 0.5  # Afternoon flight doesn't match
    assert scores[2] == 0.5  # Afternoon flight doesn't match


def test_rank_flights_single_flight(recommendation_service, db_session):
    """Test ranking with a single flight."""
    # Setup mock to return no preferences (neutral scoring)
    db_session.query.return_value.filter.return_value.first.return_value = None

    base_time = datetime(2026, 8, 30, 10, 0, 0)
    flights = [
        FlightResponse(
            id="flight1",
            airline="Test Air",
            flight_number="TA100",
            origin="JFK",
            destination="LAX",
            departure_time=base_time,
            arrival_time=base_time + timedelta(hours=5),
            duration=300,
            stops=0,
            price=200.0,
            currency="USD"
        )
    ]

    result = recommendation_service.rank_flights(flights, "user123")

    assert len(result) == 1
    assert result[0]["flight"].id == "flight1"
    assert result[0]["score"] == 0.5  # Neutral score for single flight
    assert "Recommended because" in result[0]["explanation"]


def test_rank_flights_multiple_flights(recommendation_service, sample_flights, db_session):
    """Test ranking with multiple flights."""
    # Setup mock to return no preferences (neutral scoring for time)
    db_session.query.return_value.filter.return_value.first.return_value = None

    result = recommendation_service.rank_flights(sample_flights, "user123")

    assert len(result) == 3

    # With equal durations and no time preference, ranking should be:
    # Flight 3: price=150 (best), stops=2 (worst)
    # Flight 2: price=180 (middle), stops=1 (middle)
    # Flight 1: price=200 (worst), stops=0 (best)
    #
    # Price weight: 0.4, Stops weight: 0.2
    # Flight 1: price_score=0.0, stops_score=1.0 -> 0.4*0.0 + 0.2*1.0 = 0.2
    # Flight 2: price_score=0.5, stops_score=0.5 -> 0.4*0.5 + 0.2*0.5 = 0.3
    # Flight 3: price_score=1.0, stops_score=0.0 -> 0.4*1.0 + 0.2*0.0 = 0.4
    #
    # So ranking should be: Flight 3, Flight 2, Flight 1 (highest to lowest score)

    assert result[0]["flight"].id == "flight3"  # Highest score
    assert result[1]["flight"].id == "flight2"  # Middle score
    assert result[2]["flight"].id == "flight1"  # Lowest score

    # Scores should be decreasing
    assert result[0]["score"] > result[1]["score"] > result[2]["score"]

    # All should have explanations
    for item in result:
        assert "Recommended because" in item["explanation"]


def test_rank_flights_empty_list(recommendation_service, db_session):
    """Test ranking with empty flight list."""
    result = recommendation_service.rank_flights([], "user123")
    assert result == []

def test_rank_flights_returns_configured_top_n(recommendation_service, db_session, sample_flights):
    db_session.query.return_value.filter.return_value.first.return_value = None
    flights = sample_flights * 4
    result = recommendation_service.rank_flights(flights, "user123")
    assert len(result) == RECOMMENDATION_TOP_N

def test_rank_flights_uses_itinerary_candidates_not_fare_variants(recommendation_service, db_session):
    db_session.query.return_value.filter.return_value.first.return_value = None
    base_time = datetime(2026, 9, 29, 8, 0, 0)
    itinerary = FlightResponse(
        id="itinerary-1", itinerary_id="itinerary-1", airline="Test Air",
        flight_number="TA123", origin="HYD", destination="DEL",
        departure_time=base_time, arrival_time=base_time + timedelta(hours=2),
        duration=120, stops=0, price=100.0, currency="USD",
        fare_options=[
            {"id": "offer-a", "price": 100.0, "currency": "USD"},
            {"id": "offer-b", "price": 125.0, "currency": "USD"},
        ],
    )
    result = recommendation_service.rank_flights([itinerary], "user123")
    assert len(result) == 1
    assert result[0]["flight"].id == "itinerary-1"


def test_generate_explanation(recommendation_service, sample_flights, db_session):
    """Test explanation generation."""
    # Setup mock preferences
    mock_preference = Mock(spec=Preference)
    mock_preference.preferred_time = "morning"
    db_session.query.return_value.filter.return_value.first.return_value = mock_preference

    flight = sample_flights[0]  # First flight
    explanation = recommendation_service._generate_explanation(
        flight, 0.8, 0.6, 0.9, 0.7, "user123"
    )

    assert isinstance(explanation, str)
    assert len(explanation) > 0
    assert "Recommended because" in explanation
    assert explanation.endswith(".")


if __name__ == "__main__":
    pytest.main([__file__])