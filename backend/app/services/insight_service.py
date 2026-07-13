from __future__ import annotations

import json
import logging
from uuid import UUID

from app.repositories.prediction_repository import PredictionRepository
from app.repositories.preference_repository import PreferenceRepository
from app.schemas.insights import InsightItem, SmartInsightsResponse

logger = logging.getLogger(__name__)


class InsightService:
    """Generate AI-powered travel insights for a user.

    Insights are derived from:
    - The user's prediction history (cheapest routes, expensive routes, etc.)
    - The user's preference profile (frequent destinations, budget range)
    - General heuristics (best booking windows, seasonal patterns)
    """

    def __init__(
        self,
        prediction_repo: PredictionRepository,
        preference_repo: PreferenceRepository,
    ) -> None:
        self._prediction_repo = prediction_repo
        self._preference_repo = preference_repo

    def get_insights(self, *, user_id: UUID) -> SmartInsightsResponse:
        """Return a list of personalised AI insights for the user."""
        insights: list[InsightItem] = []

        # Fetch recent predictions for this user
        predictions, _ = self._prediction_repo.get_paginated_by_user(
            user_id=user_id, offset=0, limit=100
        )

        profile = self._preference_repo.get_by_user(user_id=user_id)

        # ---- Insight 1: Cheapest route ----
        if predictions:
            cheapest = min(predictions, key=lambda p: p.predicted_price)
            insights.append(
                InsightItem(
                    title="Your Cheapest Route",
                    description=(
                        f"Your most affordable predicted route is "
                        f"{cheapest.origin} → {cheapest.destination} at "
                        f"{cheapest.currency} {cheapest.predicted_price:.2f}."
                    ),
                    category="route",
                    value=f"{cheapest.currency} {cheapest.predicted_price:.2f}",
                )
            )

        # ---- Insight 2: Most expensive route ----
        if predictions:
            priciest = max(predictions, key=lambda p: p.predicted_price)
            insights.append(
                InsightItem(
                    title="Most Expensive Route Searched",
                    description=(
                        f"{priciest.origin} → {priciest.destination} is your priciest route "
                        f"at {priciest.currency} {priciest.predicted_price:.2f}. "
                        "Consider alternative airports or flexible dates."
                    ),
                    category="route",
                    value=f"{priciest.currency} {priciest.predicted_price:.2f}",
                )
            )

        # ---- Insight 3: Potential savings ----
        if predictions:
            total_savings = sum(p.estimated_savings or 0 for p in predictions)
            if total_savings > 0:
                insights.append(
                    InsightItem(
                        title="Potential Savings Available",
                        description=(
                            f"By booking now instead of waiting, you could save up to "
                            f"{predictions[0].currency} {total_savings:.2f} across your recent searches."
                        ),
                        category="savings",
                        value=f"{predictions[0].currency} {total_savings:.2f}",
                    )
                )

        # ---- Insight 4: Preferred cabin upgrade opportunity ----
        if profile and profile.preferred_cabin == "ECONOMY" and predictions:
            avg_price = sum(p.predicted_price for p in predictions) / len(predictions)
            business_est = avg_price * 3.2
            insights.append(
                InsightItem(
                    title="Business Class Upgrade Estimate",
                    description=(
                        f"Upgrading to Business Class on your typical routes would cost "
                        f"approximately {predictions[0].currency} {business_est:.2f} — "
                        "worth it for long-haul flights."
                    ),
                    category="savings",
                    value=f"~{predictions[0].currency} {business_est:.2f}",
                )
            )

        # ---- Insight 5: Best booking window ----
        insights.append(
            InsightItem(
                title="Best Booking Window",
                description=(
                    "Research shows booking 6–8 weeks before departure typically yields "
                    "the best prices. Last-minute bookings (under 2 weeks) cost 30–50% more."
                ),
                category="timing",
                value="6–8 weeks ahead",
            )
        )

        # ---- Insight 6: Frequent destination ----
        if profile:
            destinations = _parse_list(profile.favorite_destinations)
            if destinations:
                insights.append(
                    InsightItem(
                        title="Your Most Searched Destination",
                        description=(
                            f"You frequently search for flights to {destinations[0]}. "
                            "Set a price alert to get notified when fares drop."
                        ),
                        category="general",
                        value=destinations[0],
                    )
                )

        # ---- Insight 7: Alternative airport suggestion ----
        if predictions:
            route = f"{predictions[0].origin} → {predictions[0].destination}"
            insights.append(
                InsightItem(
                    title="Consider Alternative Airports",
                    description=(
                        f"For your {route} route, nearby airports may offer cheaper fares. "
                        "Expanding your search radius by 50–100 km can save 10–25%."
                    ),
                    category="savings",
                    value="10–25% savings",
                )
            )

        # ---- Insight 8: Travel statistics ----
        if profile:
            insights.append(
                InsightItem(
                    title="Your Travel Activity",
                    description=(
                        f"You have made {profile.total_searches} flight searches on this platform. "
                        f"Your preferred cabin class is {profile.preferred_cabin}."
                    ),
                    category="general",
                    value=f"{profile.total_searches} searches",
                )
            )

        logger.info(
            "InsightService.get_insights | user=%s insights=%d", user_id, len(insights)
        )

        return SmartInsightsResponse(
            success=True,
            message="AI insights generated successfully.",
            data=insights,
            count=len(insights),
        )


def _parse_list(value: str) -> list:
    try:
        return json.loads(value) if value else []
    except Exception:
        return []
