from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class UserPreferenceItem(BaseModel):
    """Serialised user preference profile."""

    id: UUID
    user_id: UUID
    preferred_airlines: list[str] = Field(default_factory=list)
    favorite_destinations: list[str] = Field(default_factory=list)
    frequent_origins: list[str] = Field(default_factory=list)
    avg_budget: float | None = None
    min_budget: float | None = None
    max_budget: float | None = None
    preferred_cabin: str
    total_searches: int
    preferred_departure_time: str | None = None
    preferred_months: list[int] = Field(default_factory=list)
    preferred_currency: str
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserPreferenceResponse(BaseModel):
    """Response for GET /api/v1/ai/preferences."""

    success: bool
    message: str
    data: UserPreferenceItem


class InsightItem(BaseModel):
    """A single AI-generated travel insight."""

    title: str
    description: str
    category: str = Field(
        ..., description="'savings' | 'route' | 'timing' | 'airline' | 'general'."
    )
    value: str | None = Field(
        None, description="Quantified value if applicable (e.g. '30%')."
    )


class SmartInsightsResponse(BaseModel):
    """Response for GET /api/v1/ai/insights."""

    success: bool
    message: str
    data: list[InsightItem]
    count: int
