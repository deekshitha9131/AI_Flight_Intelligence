from __future__ import annotations

import logging
import statistics
from calendar import month_name
from collections import defaultdict

from app.repositories.prediction_repository import PredictionRepository
from app.schemas.price_trend import DayTrend, MonthTrend, PriceTrendResult

logger = logging.getLogger(__name__)

_DAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]
_TIME_BUCKETS = ["morning", "afternoon", "evening", "night"]


class PriceTrendService:
    """Analyse historical prediction data to surface price trend insights.

    When fewer than 5 predictions exist for a route, synthetic trend data is
    generated from the statistical fallback so the endpoint always returns a
    useful response.
    """

    def __init__(self, repository: PredictionRepository) -> None:
        self._repository = repository

    def get_price_trend(
        self,
        *,
        origin: str,
        destination: str,
        currency: str = "USD",
    ) -> PriceTrendResult:
        """Return price trend analysis for a route."""
        logger.info(
            "PriceTrendService.get_price_trend | %s→%s currency=%s",
            origin,
            destination,
            currency,
        )

        records = self._repository.get_recent_by_route(
            origin=origin, destination=destination, limit=60
        )

        prices = [r.predicted_price for r in records]

        if len(prices) < 5:
            # Not enough data — generate synthetic trend
            prices = _synthetic_prices(origin, destination, n=30)

        avg_price = statistics.mean(prices)
        low = min(prices)
        high = max(prices)
        stdev = statistics.stdev(prices) if len(prices) > 1 else 0.0

        trend_direction = _classify_trend(prices)
        volatility = _classify_volatility(stdev, avg_price)
        demand = _estimate_demand(avg_price, low, high)

        weekly = _build_weekly_trend(records, avg_price)
        monthly = _build_monthly_trend(records, avg_price)

        best_day = min(weekly, key=lambda d: d.avg_price).day if weekly else "Tuesday"
        best_time = "morning"  # heuristic — refine with real departure-time data

        return PriceTrendResult(
            origin=origin,
            destination=destination,
            currency=currency,
            trend_direction=trend_direction,
            lowest_predicted_fare=round(low, 2),
            highest_predicted_fare=round(high, 2),
            average_fare=round(avg_price, 2),
            best_booking_day=best_day,
            best_booking_time=best_time,
            demand_estimation=demand,
            price_volatility=volatility,
            weekly_trend=weekly,
            monthly_trend=monthly,
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _classify_trend(prices: list[float]) -> str:
    if len(prices) < 2:
        return "stable"
    first_half = statistics.mean(prices[: len(prices) // 2])
    second_half = statistics.mean(prices[len(prices) // 2 :])
    delta_pct = (second_half - first_half) / first_half if first_half else 0
    if delta_pct > 0.05:
        return "increasing"
    if delta_pct < -0.05:
        return "decreasing"
    return "stable"


def _classify_volatility(stdev: float, avg: float) -> str:
    if avg == 0:
        return "low"
    cv = stdev / avg  # coefficient of variation
    if cv < 0.1:
        return "low"
    if cv < 0.25:
        return "medium"
    return "high"


def _estimate_demand(avg: float, low: float, high: float) -> str:
    spread = high - low
    if spread < avg * 0.15:
        return "low"
    if spread < avg * 0.35:
        return "medium"
    return "high"


def _build_weekly_trend(records: list, avg_price: float) -> list[DayTrend]:
    """Aggregate predictions by day-of-week."""
    day_prices: dict[int, list[float]] = defaultdict(list)
    for r in records:
        try:
            from datetime import date

            d = date.fromisoformat(r.departure_date)
            day_prices[d.weekday()].append(r.predicted_price)
        except Exception:
            pass

    if not day_prices:
        # Synthetic weekly pattern
        base = avg_price
        return [
            DayTrend(
                day=_DAY_NAMES[i],
                avg_price=round(base * factor, 2),
                relative_index=round(factor, 3),
            )
            for i, factor in enumerate([0.95, 0.92, 0.97, 1.00, 1.08, 1.12, 1.05])
        ]

    result = []
    for dow in range(7):
        prices = day_prices.get(dow, [avg_price])
        day_avg = statistics.mean(prices)
        result.append(
            DayTrend(
                day=_DAY_NAMES[dow],
                avg_price=round(day_avg, 2),
                relative_index=round(day_avg / avg_price, 3) if avg_price else 1.0,
            )
        )
    return result


def _build_monthly_trend(records: list, avg_price: float) -> list[MonthTrend]:
    """Aggregate predictions by calendar month."""
    month_prices: dict[int, list[float]] = defaultdict(list)
    for r in records:
        try:
            from datetime import date

            d = date.fromisoformat(r.departure_date)
            month_prices[d.month].append(r.predicted_price)
        except Exception:
            pass

    if not month_prices:
        # Synthetic monthly pattern (peak in Dec/Jan, low in Sep/Oct)
        factors = [
            1.15,
            1.10,
            1.05,
            1.00,
            0.98,
            1.02,
            1.05,
            1.08,
            0.92,
            0.90,
            0.95,
            1.20,
        ]
        return [
            MonthTrend(
                month=m,
                month_name=month_name[m],
                avg_price=round(avg_price * factors[m - 1], 2),
                relative_index=round(factors[m - 1], 3),
            )
            for m in range(1, 13)
        ]

    result = []
    for m in range(1, 13):
        prices = month_prices.get(m, [avg_price])
        m_avg = statistics.mean(prices)
        result.append(
            MonthTrend(
                month=m,
                month_name=month_name[m],
                avg_price=round(m_avg, 2),
                relative_index=round(m_avg / avg_price, 3) if avg_price else 1.0,
            )
        )
    return result


def _synthetic_prices(origin: str, destination: str, n: int = 30) -> list[float]:
    """Generate plausible synthetic prices for a route when no data exists."""
    import random

    seed = abs(hash(f"{origin}{destination}")) % 10000
    rng = random.Random(seed)
    base = rng.uniform(200, 900)
    return [round(base + rng.gauss(0, base * 0.1), 2) for _ in range(n)]
