from __future__ import annotations

from pydantic import BaseModel, Field


class DayTrend(BaseModel):
    """Price trend for a single day of the week."""

    day: str = Field(..., description="Day name (e.g. Monday).")
    avg_price: float = Field(..., description="Average predicted price on this day.")
    relative_index: float = Field(
        ..., description="Price index relative to weekly average (1.0 = average)."
    )


class MonthTrend(BaseModel):
    """Price trend for a single calendar month."""

    month: int = Field(..., description="Month number (1–12).")
    month_name: str = Field(..., description="Month name (e.g. January).")
    avg_price: float = Field(..., description="Average predicted price in this month.")
    relative_index: float = Field(
        ..., description="Price index relative to annual average."
    )


class PriceTrendResult(BaseModel):
    """Aggregated price trend analysis for a route."""

    origin: str = Field(..., description="Departure IATA code.")
    destination: str = Field(..., description="Arrival IATA code.")
    currency: str = Field(..., description="Currency of all price values.")
    trend_direction: str = Field(
        ..., description="'increasing' | 'decreasing' | 'stable'."
    )
    lowest_predicted_fare: float = Field(
        ..., description="Lowest predicted fare across the analysis window."
    )
    highest_predicted_fare: float = Field(
        ..., description="Highest predicted fare across the analysis window."
    )
    average_fare: float = Field(..., description="Mean predicted fare.")
    best_booking_day: str = Field(
        ..., description="Day of the week with the lowest average price."
    )
    best_booking_time: str = Field(
        ..., description="Time-of-day bucket with the lowest average price."
    )
    demand_estimation: str = Field(..., description="'low' | 'medium' | 'high'.")
    price_volatility: str = Field(..., description="'low' | 'medium' | 'high'.")
    weekly_trend: list[DayTrend] = Field(
        ..., description="Per-day-of-week price breakdown."
    )
    monthly_trend: list[MonthTrend] = Field(
        ..., description="Per-month price breakdown."
    )


class PriceTrendResponse(BaseModel):
    """Response envelope for GET /api/v1/ai/price-trend."""

    success: bool
    message: str
    data: PriceTrendResult
