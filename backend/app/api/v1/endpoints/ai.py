from __future__ import annotations

import logging
from typing import Annotated

from app.dependencies.ai import (
    get_insight_service,
    get_prediction_service,
    get_preference_service,
    get_price_trend_service,
)
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.insights import SmartInsightsResponse, UserPreferenceResponse
from app.schemas.prediction import PredictPriceRequest, PredictPriceResponse
from app.schemas.price_trend import PriceTrendResponse
from app.services.insight_service import InsightService
from app.services.prediction_service import PredictionService
from app.services.preference_service import PreferenceService
from app.services.price_trend_service import PriceTrendService
from fastapi import APIRouter, BackgroundTasks, Depends, Query, status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post(
    "/predict-price",
    response_model=PredictPriceResponse,
    status_code=status.HTTP_200_OK,
    summary="Predict flight price",
    description=(
        "Use the trained ML model to predict the price of a flight based on route, "
        "dates, cabin class, and passenger count.\\n\\n"
        "**Authentication required.**\\n\\n"
        "The prediction is persisted to history and can be retrieved later.\\n\\n"
        "**Errors**\\n"
        "- `400` — validation failure\\n"
        "- `401` — missing or invalid JWT token\\n"
        "- `500` — model inference error"
    ),
    responses={
        400: {"description": "Validation error."},
        401: {"description": "Authentication required."},
        500: {"description": "Model inference error."},
    },
)
def predict_price(
    payload: PredictPriceRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    service: PredictionService = Depends(get_prediction_service),
    preference_service: PreferenceService = Depends(get_preference_service),
) -> PredictPriceResponse:
    """Predict the price of a flight using the trained ML model."""
    result = service.predict(request=payload, user_id=current_user.id)

    # Refresh preference profile in the background after each prediction
    background_tasks.add_task(
        preference_service.refresh_preferences, user_id=current_user.id
    )

    return PredictPriceResponse(
        success=True,
        message="Price prediction completed successfully.",
        data=result,
    )


@router.get(
    "/price-trend",
    response_model=PriceTrendResponse,
    status_code=status.HTTP_200_OK,
    summary="Get price trend analysis",
    description=(
        "Analyse historical ML predictions for a route to surface price trends, "
        "volatility, best booking day, and monthly patterns.\\n\\n"
        "**Authentication required.**"
    ),
    responses={
        401: {"description": "Authentication required."},
    },
)
def get_price_trend(
    origin: Annotated[
        str,
        Query(
            min_length=3,
            max_length=3,
            description="Departure IATA code.",
            example=["HYD"],
        ),
    ],
    destination: Annotated[
        str,
        Query(
            min_length=3,
            max_length=3,
            description="Arrival IATA code.",
            example=["DXB"],
        ),
    ],
    currency: Annotated[
        str,
        Query(
            min_length=3, max_length=3, description="Currency code.", example=["USD"]
        ),
    ] = "USD",
    current_user: User = Depends(get_current_user),
    service: PriceTrendService = Depends(get_price_trend_service),
) -> PriceTrendResponse:
    """Return price trend analysis for a route."""
    result = service.get_price_trend(
        origin=origin.upper(),
        destination=destination.upper(),
        currency=currency.upper(),
    )
    return PriceTrendResponse(
        success=True,
        message="Price trend analysis completed successfully.",
        data=result,
    )


@router.get(
    "/preferences",
    response_model=UserPreferenceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user preference profile",
    description=(
        "Return the AI-learned preference profile for the authenticated user. "
        "The profile is derived from search history and updated automatically.\\n\\n"
        "**Authentication required.**"
    ),
    responses={
        401: {"description": "Authentication required."},
    },
)
def get_preferences(
    current_user: User = Depends(get_current_user),
    service: PreferenceService = Depends(get_preference_service),
) -> UserPreferenceResponse:
    """Return the authenticated user's learned preference profile."""
    return service.get_preferences(user_id=current_user.id)


@router.get(
    "/insights",
    response_model=SmartInsightsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get AI travel insights",
    description=(
        "Generate personalised AI insights including cheapest routes, potential savings, "
        "booking window recommendations, and travel statistics.\\n\\n"
        "**Authentication required.**"
    ),
    responses={
        401: {"description": "Authentication required."},
    },
)
def get_insights(
    current_user: User = Depends(get_current_user),
    service: InsightService = Depends(get_insight_service),
) -> SmartInsightsResponse:
    """Return AI-generated travel insights for the authenticated user."""
    return service.get_insights(user_id=current_user.id)
