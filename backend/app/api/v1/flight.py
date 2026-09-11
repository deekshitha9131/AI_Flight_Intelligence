from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.schemas.flight import FlightSearchRequest, FlightResponse
from app.services.flight import search_flights
from app.core.dependencies import get_db, get_current_user
from app.models.user import User
from app.repositories.flight_search import FlightSearchRepository
from typing import List
import asyncio

router = APIRouter(
    prefix="/flights",
    tags=["flights"],
    responses={404: {"description": "Not found"}},
)

@router.post("/search", response_model=List[FlightResponse])
async def search_flights_endpoint(
    search_request: FlightSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Search for flights.
    Requires authentication.
    """
    # Validate that origin and destination are not the same
    if search_request.origin.upper() == search_request.destination.upper():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Origin and destination cannot be the same"
        )

    try:
        # Create a flight search record to get an ID for predictions
        flight_search_repo = FlightSearchRepository(db)
        flight_search = flight_search_repo.create(
            user_id=str(current_user.id),
            origin=search_request.origin,
            destination=search_request.destination,
            departure_date=search_request.departure_date,
            return_date=search_request.return_date,
            passengers=search_request.passengers,
            cabin_class=search_request.cabin_class
        )

        # Call the async flight search service directly
        flights = await search_flights(search_request)

        # Return flights with flight search ID in header
        response = JSONResponse(content=jsonable_encoder(flights))
        response.headers["X-Flight-Search-ID"] = flight_search.id
        return response
    except Exception as e:
        # Log the error for debugging (in production, use proper logging)
        # For now, we'll raise a service unavailable error
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Flight search unavailable: {str(e)}"
        )