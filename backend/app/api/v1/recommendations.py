from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from app.schemas.flight import FlightResponse
from app.services.recommendation import RecommendationService
from app.core.dependencies import get_db, get_current_user
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/recommendations",
    tags=["recommendations"],
    responses={404: {"description": "Not found"}},
)


class FlightRecommendationRequest(BaseModel):
    flights: List[FlightResponse]


class FlightRecommendationResponse(BaseModel):
    recommendations: List[dict]


@router.post("/", response_model=List[dict])
async def get_flight_recommendations(
    request: FlightRecommendationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get flight recommendations ranked by a scoring algorithm.
    Takes a list of flight results and returns them ranked with scores and explanations.

    Requires authentication.
    """
    try:
        # Validate input
        if not isinstance(request.flights, list) or not request.flights:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No flights provided for recommendation"
            )

        # Create recommendation service
        recommendation_service = RecommendationService(db)

        # Rank the flights
        recommendations = recommendation_service.rank_flights(request.flights, str(current_user.id))

        logger.info(f"Generated {len(recommendations)} flight recommendations for user {current_user.id}")
        return recommendations

    except ValueError as e:
        logger.error(f"Validation error in recommendation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except HTTPException:
        # Re-raise HTTPException to preserve the original status code
        raise
    except Exception as e:
        logger.error(f"Recommendation endpoint error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Recommendation service unavailable"
        )


# Alternative endpoint that accepts a flight search request and performs search + recommendation
# This avoids requiring the client to send flight data back
from app.schemas.flight import FlightSearchRequest
from app.services.flight import search_flights


class FlightSearchAndRecommendRequest:
    """Request model for flight search and recommendation."""
    def __init__(self, search_request: FlightSearchRequest):
        self.search_request = search_request


@router.post("/search", response_model=List[dict])
async def search_and_recommend_flights(
    search_request: FlightSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Search for flights and get recommendations in one call.
    This avoids requiring the client to send flight data back to the server.

    Requires authentication.
    """
    try:
        logger.info(f"Processing search and recommendation request for user {current_user.id}")

        # Search for flights using the existing flight service
        flights = await search_flights(search_request)

        # Ensure flights is a list
        if not isinstance(flights, list):
            flights = []

        if not flights:
            return []

        # Create recommendation service
        recommendation_service = RecommendationService(db)

        # Rank the flights
        recommendations = recommendation_service.rank_flights(flights, str(current_user.id))

        logger.info(f"Generated {len(recommendations)} flight recommendations for user {current_user.id}")
        return recommendations

    except HTTPException:
        # Re-raise HTTPException to preserve the original status code
        raise
    except Exception as e:
        logger.error(f"Search and recommendation endpoint error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search and recommendation service unavailable: {str(e)}"
        )