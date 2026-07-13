from __future__ import annotations

import json
import logging
from uuid import UUID

from app.ai.model_loader import ModelLoader
from app.repositories.preference_repository import PreferenceRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.schemas.recommendation import (
    AirlineRecommendationsResponse,
    DealsRecommendationsResponse,
    DestinationRecommendationsResponse,
    FlightRecommendationsResponse,
    RecommendedAirline,
    RecommendedDeal,
    RecommendedDestination,
    RecommendedFlight,
)

logger = logging.getLogger(__name__)

# Popular destinations used when the user has no history
_POPULAR_DESTINATIONS = [
    ("DXB", "Dubai", "UAE"),
    ("LHR", "London", "UK"),
    ("SIN", "Singapore", "Singapore"),
    ("BKK", "Bangkok", "Thailand"),
    ("CDG", "Paris", "France"),
    ("JFK", "New York", "USA"),
    ("NRT", "Tokyo", "Japan"),
    ("SYD", "Sydney", "Australia"),
]

_POPULAR_AIRLINES = [
    ("EK", "Emirates"),
    ("SQ", "Singapore Airlines"),
    ("QR", "Qatar Airways"),
    ("AI", "Air India"),
    ("BA", "British Airways"),
    ("LH", "Lufthansa"),
]


class RecommendationService:
    """Generate personalised recommendations using preference profiles and ML."""

    def __init__(
        self,
        preference_repo: PreferenceRepository,
        recommendation_repo: RecommendationRepository,
        model_loader: ModelLoader,
    ) -> None:
        self._pref_repo = preference_repo
        self._rec_repo = recommendation_repo
        self._model_loader = model_loader

    # ------------------------------------------------------------------
    # Flight recommendations
    # ------------------------------------------------------------------

    def get_flight_recommendations(
        self,
        *,
        user_id: UUID,
        limit: int = 5,
    ) -> FlightRecommendationsResponse:
        """Return personalised flight recommendations."""
        profile = self._pref_repo.get_by_user(user_id=user_id)

        origins = _parse_list(profile.frequent_origins if profile else "[]") or ["DEL"]
        destinations = _parse_list(profile.favorite_destinations if profile else "[]")
        if not destinations:
            destinations = [d[0] for d in _POPULAR_DESTINATIONS[:3]]

        cabin = profile.preferred_cabin if profile else "ECONOMY"
        currency = profile.preferred_currency if profile else "USD"

        results: list[RecommendedFlight] = []
        for dest in destinations[:limit]:
            origin = origins[0] if origins else "DEL"
            features = _build_features(origin, dest, cabin)
            price, _ = self._model_loader.predict(features)
            results.append(
                RecommendedFlight(
                    origin=origin,
                    destination=dest,
                    airline=_pick_airline(origin, dest),
                    cabin_class=cabin,
                    estimated_price=round(price, 2),
                    currency=currency,
                    reason=f"Based on your frequent searches from {origin}.",
                    score=round(0.9 - len(results) * 0.05, 2),
                )
            )

        self._rec_repo.create(
            user_id=user_id,
            recommendation_type="flights",
            payload=[r.model_dump() for r in results],
            reasoning="Derived from user search history and ML price predictions.",
        )

        return FlightRecommendationsResponse(
            success=True,
            message="Flight recommendations generated successfully.",
            data=results,
            count=len(results),
        )

    # ------------------------------------------------------------------
    # Destination recommendations
    # ------------------------------------------------------------------

    def get_destination_recommendations(
        self,
        *,
        user_id: UUID,
        limit: int = 6,
    ) -> DestinationRecommendationsResponse:
        """Return personalised destination recommendations."""
        profile = self._pref_repo.get_by_user(user_id=user_id)
        visited = set(_parse_list(profile.favorite_destinations if profile else "[]"))
        currency = profile.preferred_currency if profile else "USD"
        cabin = profile.preferred_cabin if profile else "ECONOMY"
        origin = (
            _parse_list(profile.frequent_origins if profile else "[]") or ["DEL"]
        )[0]

        results: list[RecommendedDestination] = []
        for iata, city, country in _POPULAR_DESTINATIONS:
            if len(results) >= limit:
                break
            features = _build_features(origin, iata, cabin)
            price, _ = self._model_loader.predict(features)
            reason = (
                "Popular destination you haven't explored yet."
                if iata not in visited
                else "A destination you've searched before — great time to revisit."
            )
            results.append(
                RecommendedDestination(
                    iata_code=iata,
                    city=city,
                    country=country,
                    estimated_price=round(price * 1.85, 2),  # round-trip estimate
                    currency=currency,
                    reason=reason,
                    score=round(0.95 - len(results) * 0.05, 2),
                    best_travel_month=_best_month(iata),
                )
            )

        self._rec_repo.create(
            user_id=user_id,
            recommendation_type="destinations",
            payload=[r.model_dump() for r in results],
        )

        return DestinationRecommendationsResponse(
            success=True,
            message="Destination recommendations generated successfully.",
            data=results,
            count=len(results),
        )

    # ------------------------------------------------------------------
    # Airline recommendations
    # ------------------------------------------------------------------

    def get_airline_recommendations(
        self,
        *,
        user_id: UUID,
        limit: int = 5,
    ) -> AirlineRecommendationsResponse:
        """Return personalised airline recommendations."""
        profile = self._pref_repo.get_by_user(user_id=user_id)
        preferred = set(_parse_list(profile.preferred_airlines if profile else "[]"))
        currency = profile.preferred_currency if profile else "USD"
        origin = (
            _parse_list(profile.frequent_origins if profile else "[]") or ["DEL"]
        )[0]
        dest = (
            _parse_list(profile.favorite_destinations if profile else "[]") or ["DXB"]
        )[0]

        results: list[RecommendedAirline] = []
        for iata, name in _POPULAR_AIRLINES[:limit]:
            features = _build_features(origin, dest, "ECONOMY")
            features["airline_encoded"] = abs(hash(iata)) % 200
            price, _ = self._model_loader.predict(features)
            reason = (
                "One of your preferred airlines."
                if iata in preferred
                else f"Highly rated airline for {origin}→{dest} routes."
            )
            results.append(
                RecommendedAirline(
                    iata_code=iata,
                    name=name,
                    reason=reason,
                    avg_price=round(price, 2),
                    currency=currency,
                    score=round(0.9 - len(results) * 0.04, 2),
                )
            )

        self._rec_repo.create(
            user_id=user_id,
            recommendation_type="airlines",
            payload=[r.model_dump() for r in results],
        )

        return AirlineRecommendationsResponse(
            success=True,
            message="Airline recommendations generated successfully.",
            data=results,
            count=len(results),
        )

    # ------------------------------------------------------------------
    # Deal recommendations
    # ------------------------------------------------------------------

    def get_deal_recommendations(
        self,
        *,
        user_id: UUID,
        limit: int = 5,
    ) -> DealsRecommendationsResponse:
        """Return time-sensitive deal recommendations."""
        profile = self._pref_repo.get_by_user(user_id=user_id)
        currency = profile.preferred_currency if profile else "USD"
        cabin = profile.preferred_cabin if profile else "ECONOMY"
        origin = (
            _parse_list(profile.frequent_origins if profile else "[]") or ["DEL"]
        )[0]

        results: list[RecommendedDeal] = []
        for iata, city, _ in _POPULAR_DESTINATIONS[:limit]:
            features = _build_features(origin, iata, cabin)
            features["days_until_departure"] = 45  # mid-range booking
            price, _ = self._model_loader.predict(features)
            discount = round(10 + (abs(hash(iata)) % 20), 1)  # 10–30%
            results.append(
                RecommendedDeal(
                    origin=origin,
                    destination=iata,
                    airline=_pick_airline(origin, iata),
                    cabin_class=cabin,
                    estimated_price=round(price * (1 - discount / 100), 2),
                    currency=currency,
                    discount_pct=discount,
                    valid_until=None,
                    reason=f"Limited-time deal to {city} — {discount:.0f}% below average.",
                    score=round(0.95 - len(results) * 0.05, 2),
                )
            )

        self._rec_repo.create(
            user_id=user_id,
            recommendation_type="deals",
            payload=[r.model_dump() for r in results],
        )

        return DealsRecommendationsResponse(
            success=True,
            message="Deal recommendations generated successfully.",
            data=results,
            count=len(results),
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _parse_list(value: str) -> list:
    try:
        return json.loads(value) if value else []
    except Exception:
        return []


def _build_features(origin: str, destination: str, cabin: str) -> dict:
    return {
        "origin": origin,
        "destination": destination,
        "origin_encoded": abs(hash(origin)) % 500,
        "destination_encoded": abs(hash(destination)) % 500,
        "days_until_departure": 30,
        "is_round_trip": 0,
        "adults": 1,
        "children": 0,
        "infants": 0,
        "cabin_class": cabin,
        "cabin_class_encoded": {
            "ECONOMY": 0,
            "PREMIUM_ECONOMY": 1,
            "BUSINESS": 2,
            "FIRST": 3,
        }.get(cabin, 0),
        "stops": 0,
        "departure_month": 6,
        "departure_day_of_week": 1,
        "airline_encoded": 0,
    }


def _pick_airline(origin: str, destination: str) -> str:
    """Pick a plausible airline for a route based on a deterministic hash."""
    idx = abs(hash(f"{origin}{destination}")) % len(_POPULAR_AIRLINES)
    return _POPULAR_AIRLINES[idx][0]


def _best_month(iata: str) -> str:
    months = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    return months[abs(hash(iata)) % 12]
