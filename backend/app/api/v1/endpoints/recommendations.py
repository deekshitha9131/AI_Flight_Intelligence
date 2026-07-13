from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query, status

from app.dependencies.ai import get_recommendation_service
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.recommendation import (
    AirlineRecommendationsResponse,
    DealsRecommendationsResponse,
    DestinationRecommendationsResponse,
    FlightRecommendationsResponse,
)
from app.services.recommendation_service import RecommendationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get(
    "",
    response_model=FlightRecommendationsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get personalised flight recommendations",
    description=(
        "Return personalised flight recommendations based on the user's search history, "
        "preferred cabin class, frequent routes, and ML price predictions.\\n\\n"
        "**Authentication required.**"
    ),
    responses={401: {"description": "Authentication required."}},
)
def get_flight_recommendations(
    limit: int = Query(
        5, ge=1, le=20, description="Maximum number of recommendations."
    ),
    current_user: User = Depends(get_current_user),
    service: RecommendationService = Depends(get_recommendation_service),
) -> FlightRecommendationsResponse:
    """Return personalised flight recommendations for the authenticated user."""
    return service.get_flight_recommendations(user_id=current_user.id, limit=limit)


@router.get(
    "/destinations",
    response_model=DestinationRecommendationsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get destination recommendations",
    description=(
        "Return personalised destination recommendations with estimated round-trip prices "
        "and best travel months.\\n\\n"
        "**Authentication required.**"
    ),
    responses={401: {"description": "Authentication required."}},
)
def get_destination_recommendations(
    limit: int = Query(6, ge=1, le=20, description="Maximum number of destinations."),
    current_user: User = Depends(get_current_user),
    service: RecommendationService = Depends(get_recommendation_service),
) -> DestinationRecommendationsResponse:
    """Return personalised destination recommendations."""
    return service.get_destination_recommendations(user_id=current_user.id, limit=limit)


@router.get(
    "/airlines",
    response_model=AirlineRecommendationsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get airline recommendations",
    description=(
        "Return personalised airline recommendations based on preferred routes and "
        "average predicted prices.\\n\\n"
        "**Authentication required.**"
    ),
    responses={401: {"description": "Authentication required."}},
)
def get_airline_recommendations(
    limit: int = Query(5, ge=1, le=20, description="Maximum number of airlines."),
    current_user: User = Depends(get_current_user),
    service: RecommendationService = Depends(get_recommendation_service),
) -> AirlineRecommendationsResponse:
    """Return personalised airline recommendations."""
    return service.get_airline_recommendations(user_id=current_user.id, limit=limit)


@router.get(
    "/deals",
    response_model=DealsRecommendationsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get deal recommendations",
    description=(
        "Return time-sensitive deal recommendations with estimated discount percentages "
        "compared to average predicted prices.\\n\\n"
        "**Authentication required.**"
    ),
    responses={401: {"description": "Authentication required."}},
)
def get_deal_recommendations(
    limit: int = Query(5, ge=1, le=20, description="Maximum number of deals."),
    current_user: User = Depends(get_current_user),
    service: RecommendationService = Depends(get_recommendation_service),
) -> DealsRecommendationsResponse:
    """Return deal recommendations for the authenticated user."""
    return service.get_deal_recommendations(user_id=current_user.id, limit=limit)
