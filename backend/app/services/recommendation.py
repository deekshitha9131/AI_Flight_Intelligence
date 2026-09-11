"""
Recommendation service for ranking flight results.
"""
from typing import List, Optional
from datetime import datetime
from app.schemas.flight import FlightResponse
from app.models.preference import Preference
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)
RECOMMENDATION_TOP_N = 5


class RecommendationService:
    """Service for ranking flight recommendations using a deterministic scoring algorithm."""

    def __init__(self, db: Session):
        self.db = db

        # Weights for different factors in the recommendation score
        # These weights sum to 1.0 (100%)
        self.weights = {
            'price': 0.40,      # 40% weight for price
            'duration': 0.25,   # 25% weight for duration
            'stops': 0.20,      # 20% weight for number of stops
            'departure_time': 0.15  # 15% weight for departure time preference
        }

        # Weights for the new preference factors (used when new preferences are set)
        self.new_weights = {
            'price': 0.32,      # 32% weight for price
            'duration': 0.20,   # 20% weight for duration
            'stops': 0.16,      # 16% weight for stops
            'departure_time': 0.12,  # 12% weight for departure time preference
            'price_range': 0.10,  # 10% weight for price range preference
            'airport_match': 0.10   # 10% weight for airport match preference
        }

    def _normalize_score(self, value: float, min_val: float, max_val: float) -> float:
        """
        Normalize a value to a 0-1 range where 1 is best.

        Args:
            value: The value to normalize
            min_val: Minimum value in the dataset
            max_val: Maximum value in the dataset

        Returns:
            Normalized score between 0 and 1
        """
        if max_val == min_val:
            # All values are the same, return neutral score
            return 0.5

        # For factors where lower is better (price, duration, stops), we invert
        # For factors where higher is better, we keep as is
        return (max_val - value) / (max_val - min_val)

    def _calculate_price_score(self, flights: List[FlightResponse]) -> List[float]:
        """
        Calculate price scores for flights.
        Lower price gets higher score.

        Args:
            flights: List of flight responses

        Returns:
            List of price scores (0-1) for each flight
        """
        if not flights:
            return []

        prices = [flight.price for flight in flights]
        min_price = min(prices)
        max_price = max(prices)

        scores = []
        for flight in flights:
            score = self._normalize_score(flight.price, min_price, max_price)
            scores.append(score)

        return scores

    def _calculate_duration_score(self, flights: List[FlightResponse]) -> List[float]:
        """
        Calculate duration scores for flights.
        Shorter duration gets higher score.

        Args:
            flights: List of flight responses

        Returns:
            List of duration scores (0-1) for each flight
        """
        if not flights:
            return []

        durations = [flight.duration for flight in flights]
        min_duration = min(durations)
        max_duration = max(durations)

        scores = []
        for flight in flights:
            score = self._normalize_score(flight.duration, min_duration, max_duration)
            scores.append(score)

        return scores

    def _calculate_stops_score(self, flights: List[FlightResponse]) -> List[float]:
        """
        Calculate stops scores for flights.
        Fewer stops gets higher score.

        Args:
            flights: List of flight responses

        Returns:
            List of stops scores (0-1) for each flight
        """
        if not flights:
            return []

        stops_list = [flight.stops for flight in flights]
        min_stops = min(stops_list)
        max_stops = max(stops_list)

        scores = []
        for flight in flights:
            score = self._normalize_score(flight.stops, min_stops, max_stops)
            scores.append(score)

        return scores

    def _calculate_departure_time_score(self, flights: List[FlightResponse], user_id: str) -> List[float]:
        """
        Calculate departure time scores for flights based on user preferences.
        If no preference is set, returns neutral scores (0.5).

        Args:
            flights: List of flight responses
            user_id: ID of the user to get preferences for

        Returns:
            List of departure time scores (0-1) for each flight
        """
        if not flights:
            return []

        # Get user preferences
        user_preferences = self.db.query(Preference).filter(Preference.user_id == user_id).first()

        # If no preferences set, return neutral scores
        if not user_preferences or not user_preferences.preferred_time:
            return [0.5] * len(flights)

        preferred_time = user_preferences.preferred_time.lower()

        # Define time periods for scoring
        def get_time_period(dt: datetime) -> str:
            hour = dt.hour
            if 5 <= hour < 12:
                return "morning"
            elif 12 <= hour < 17:
                return "afternoon"
            elif 17 <= hour < 21:
                return "evening"
            else:
                return "night"

        scores = []
        for flight in flights:
            flight_period = get_time_period(flight.departure_time)
            # Give higher score (1.0) if matches preference, neutral (0.5) otherwise
            if flight_period == preferred_time:
                scores.append(1.0)
            else:
                scores.append(0.5)

        return scores

    def _has_new_preferences(self, user_preferences: Optional[Preference]) -> bool:
        """
        Check if the user has set any of the new preferences that affect ranking.
        New preferences: preferred_cabin, preferred_airport, min_price, max_price.
        We ignore preferred_currency (no exchange rate data) and preferred_cabin (no cabin data in FlightResponse).
        Actually, we ignore preferred_cabin because we don't have cabin data.
        So we only consider preferred_airport, min_price, max_price.
        """
        if not user_preferences:
            return False
        return (
            user_preferences.preferred_airport is not None
            or user_preferences.min_price is not None
            or user_preferences.max_price is not None
        )

    def _calculate_price_range_score(self, flights: List[FlightResponse], min_price: Optional[float], max_price: Optional[float]) -> List[float]:
        """
        Calculate price range scores for flights based on user's preferred price range.
        Returns a score between 0 and 1, where 1 is best (price within preferred range).

        Args:
            flights: List of flight responses
            min_price: User's preferred minimum price (can be None)
            max_price: User's preferred maximum price (can be None)

        Returns:
            List of price range scores (0-1) for each flight
        """
        if not flights:
            return []

        # If no price range preference set, return neutral scores
        if min_price is None and max_price is None:
            return [1.0] * len(flights)

        scores = []
        for flight in flights:
            price = flight.price
            if min_price is not None and max_price is not None:
                # Both min and max set
                if price < min_price:
                    # Below min price
                    if min_price > 0:
                        # Avoid division by zero
                        distance = min_price - price
                        max_distance = min_price  # Assume max distance is min_price (price=0 gives score 0)
                        score = max(0.0, 1.0 - distance / max_distance)
                    else:
                        score = 0.0
                elif price > max_price:
                    # Above max price
                    if max_price > 0:
                        distance = price - max_price
                        max_distance = max_price  # Assume max distance is max_price (price=2*max_price gives score 0)
                        score = max(0.0, 1.0 - distance / max_distance)
                    else:
                        score = 0.0
                else:
                    # Within range
                    score = 1.0
            elif min_price is not None:
                # Only min price set
                if price < min_price:
                    if min_price > 0:
                        distance = min_price - price
                        max_distance = min_price
                        score = max(0.0, 1.0 - distance / max_distance)
                    else:
                        score = 0.0
                else:
                    score = 1.0
            else:  # only max_price is set
                if price > max_price:
                    if max_price > 0:
                        distance = price - max_price
                        max_distance = max_price
                        score = max(0.0, 1.0 - distance / max_distance)
                    else:
                        score = 0.0
                else:
                    score = 1.0
            scores.append(score)
        return scores

    def _calculate_airport_match_score(self, flights: List[FlightResponse], preferred_airport: Optional[str]) -> List[float]:
        """
        Calculate airport match scores for flights.
        Returns 1.0 if flight's origin matches preferred_airport, else 0.5.

        Args:
            flights: List of flight responses
            preferred_airport: User's preferred airport IATA code (can be None)

        Returns:
            List of airport match scores (0-1) for each flight
        """
        if not flights:
            return []

        if not preferred_airport:
            # No preference set, return neutral scores
            return [0.5] * len(flights)

        preferred_airport = preferred_airport.upper()
        scores = []
        for flight in flights:
            if flight.origin.upper() == preferred_airport:
                scores.append(1.0)
            else:
                scores.append(0.5)
        return scores

    def _generate_explanation(self, flight: FlightResponse, price_score: float, duration_score: float,
                            stops_score: float, time_score: float,
                            price_range_score: Optional[float] = None, airport_match_score: Optional[float] = None,
                            user_preferences: Optional[Preference] = None) -> str:
        """
        Generate a human-readable explanation for why a flight was recommended.

        Args:
            flight: The flight response
            price_score: Normalized price score (0-1)
            duration_score: Normalized duration score (0-1)
            stops_score: Normalized stops score (0-1)
            time_score: Departure time score (0-1)
            price_range_score: Price range score (0-1) or None
            airport_match_score: Airport match score (0-1) or None
            user_preferences: User's preferences object or None

        Returns:
            Explanation string
        """
        explanations = []

        # Get user preferences for context
        preferred_time = user_preferences.preferred_time if user_preferences else None
        preferred_currency = user_preferences.preferred_currency if user_preferences else None
        preferred_cabin = user_preferences.preferred_cabin if user_preferences else None
        preferred_airport = user_preferences.preferred_airport if user_preferences else None
        min_price = user_preferences.min_price if user_preferences else None
        max_price = user_preferences.max_price if user_preferences else None

        # Check price factor (relative price among results)
        if price_score >= 0.8:
            explanations.append("it has one of the lowest prices")
        elif price_score >= 0.6:
            explanations.append("it has a relatively low price")
        elif price_score >= 0.4:
            explanations.append("it has a moderate price")
        else:
            explanations.append("it is priced higher than other options")

        # Check duration factor
        if duration_score >= 0.8:
            explanations.append("it has a short travel duration")
        elif duration_score >= 0.6:
            explanations.append("it has a reasonable travel duration")
        elif duration_score >= 0.4:
            explanations.append("it has a lengthy travel duration")
        else:
            explanations.append("it has a very long travel duration")

        # Check stops factor
        if flight.stops == 0:
            explanations.append("it has no stops")
        elif flight.stops == 1:
            explanations.append("it has only one stop")
        else:
            explanations.append(f"it has {flight.stops} stops")

        # Check departure time factor if preference exists
        if preferred_time:
            # Determine time period of flight
            hour = flight.departure_time.hour
            if 5 <= hour < 12:
                flight_period = "morning"
            elif 12 <= hour < 17:
                flight_period = "afternoon"
            elif 17 <= hour < 21:
                flight_period = "evening"
            else:
                flight_period = "night"

            if flight_period == preferred_time:
                explanations.append(f"it matches your preferred {preferred_time} travel time")
            else:
                explanations.append(f"it does not match your preferred {preferred_time} travel time")

        # Check price range factor if preference exists
        if price_range_score is not None:
            if min_price is not None or max_price is not None:
                # Build range string
                range_parts = []
                if min_price is not None:
                    range_parts.append(f"≥{min_price}")
                if max_price is not None:
                    range_parts.append(f"≤{max_price}")
                range_str = " ".join(range_parts) if range_parts else ""
                if price_range_score > 0.7:
                    explanations.append(f"it is within your preferred price range {range_str}")
                else:
                    explanations.append(f"it is outside your preferred price range {range_str}")

        # Check airport match factor if preference exists
        if airport_match_score is not None:
            if preferred_airport is not None:
                if airport_match_score > 0.7:
                    explanations.append(f"it matches your preferred airport {preferred_airport}")
                else:
                    explanations.append(f"it does not match your preferred airport {preferred_airport}")

        # Combine explanations into a coherent sentence
        if len(explanations) == 1:
            reason = explanations[0]
        elif len(explanations) == 2:
            reason = f"{explanations[0]} and {explanations[1]}"
        else:
            reason = f"{', '.join(explanations[:-1])}, and {explanations[-1]}"

        # Capitalize first letter and add period
        reason = reason.capitalize() + "."

        return f"Recommended because {reason}"

    def rank_flights(self, flights: List[FlightResponse], user_id: str) -> List[dict]:
        """
        Rank flights using the recommendation algorithm.

        Args:
            flights: List of flight responses to rank
            user_id: ID of the user (for preferences)

        Returns:
            List of dictionaries containing flight, score, and explanation
        """
        if not flights:
            return []

        # Get user preferences
        user_preferences = self.db.query(Preference).filter(Preference.user_id == user_id).first()

        # Check if we have any new preferences set (that we support for ranking)
        if not self._has_new_preferences(user_preferences):
            # Use existing logic (backward compatibility)
            # Handle single flight case
            if len(flights) == 1:
                flight = flights[0]
                explanation = self._generate_explanation(flight, 0.5, 0.5, 0.5, 0.5, None, None, user_preferences)
                return [{
                    "flight": flight,
                    "score": 0.5,
                    "explanation": explanation
                }]

            # Calculate scores for each factor
            price_scores = self._calculate_price_score(flights)
            duration_scores = self._calculate_duration_score(flights)
            stops_scores = self._calculate_stops_score(flights)
            time_scores = self._calculate_departure_time_score(flights, user_id)

            # Calculate weighted scores and rank
            ranked_flights = []
            for i, flight in enumerate(flights):
                # Calculate weighted score
                weighted_score = (
                    self.weights['price'] * price_scores[i] +
                    self.weights['duration'] * duration_scores[i] +
                    self.weights['stops'] * stops_scores[i] +
                    self.weights['departure_time'] * time_scores[i]
                )

                # Generate explanation
                explanation = self._generate_explanation(
                    flight, price_scores[i], duration_scores[i],
                    stops_scores[i], time_scores[i], None, None, user_preferences
                )

                ranked_flights.append({
                    "flight": flight,
                    "score": round(weighted_score, 3),
                    "explanation": explanation
                })

            # Sort by score descending (highest score first)
            ranked_flights.sort(key=lambda x: x["score"], reverse=True)

            recommendations = ranked_flights[:RECOMMENDATION_TOP_N]
            logger.info(
                "Recommendation candidates: %d; recommendations returned: %d",
                len(flights), len(recommendations),
            )
            return recommendations
        else:
            # Use new logic with additional preference factors
            # Handle single flight case
            if len(flights) == 1:
                flight = flights[0]
                # For single flight, all scores are neutral
                explanation = self._generate_explanation(flight, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, user_preferences)
                return [{
                    "flight": flight,
                    "score": 0.5,
                    "explanation": explanation
                }]

            # Calculate scores for each factor
            price_scores = self._calculate_price_score(flights)
            duration_scores = self._calculate_duration_score(flights)
            stops_scores = self._calculate_stops_score(flights)
            time_scores = self._calculate_departure_time_score(flights, user_id)
            price_range_scores = self._calculate_price_range_score(
                flights,
                user_preferences.min_price if user_preferences else None,
                user_preferences.max_price if user_preferences else None
            )
            airport_match_scores = self._calculate_airport_match_score(
                flights,
                user_preferences.preferred_airport if user_preferences else None
            )

            # Calculate weighted scores and rank
            ranked_flights = []
            for i, flight in enumerate(flights):
                # Calculate weighted score using new weights
                weighted_score = (
                    self.new_weights['price'] * price_scores[i] +
                    self.new_weights['duration'] * duration_scores[i] +
                    self.new_weights['stops'] * stops_scores[i] +
                    self.new_weights['departure_time'] * time_scores[i] +
                    self.new_weights['price_range'] * price_range_scores[i] +
                    self.new_weights['airport_match'] * airport_match_scores[i]
                )

                # Generate explanation
                explanation = self._generate_explanation(
                    flight, price_scores[i], duration_scores[i],
                    stops_scores[i], time_scores[i],
                    price_range_scores[i], airport_match_scores[i],
                    user_preferences
                )

                ranked_flights.append({
                    "flight": flight,
                    "score": round(weighted_score, 3),
                    "explanation": explanation
                })

            # Sort by score descending (highest score first)
            ranked_flights.sort(key=lambda x: x["score"], reverse=True)

            recommendations = ranked_flights[:RECOMMENDATION_TOP_N]
            logger.info(
                "Recommendation candidates: %d; recommendations returned: %d",
                len(flights), len(recommendations),
            )
            return recommendations