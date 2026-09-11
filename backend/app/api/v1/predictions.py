from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.prediction import PredictionRequest, PredictionResponse
from app.services.prediction import PredictionService
from app.core.dependencies import get_db, get_current_user
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/predictions",
    tags=["predictions"],
    responses={404: {"description": "Not found"}},
)

# We will create the prediction service per request to have access to the db session
@router.post("/", response_model=PredictionResponse)
async def create_prediction(
    prediction_request: PredictionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    flight_search_id: str = None  # This would typically come from a previous flight search
):
    """
    Create a price prediction for a flight.
    Requires authentication and a valid flight_search_id.
    """
    try:
        # In a real implementation, flight_search_id would come from the request body or query params
        # For now, we'll require it as a query parameter or we could modify the endpoint design
        # Let's assume it's passed as a query parameter for simplicity in this implementation

        if not flight_search_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="flight_search_id is required"
            )

        # Verify the flight search belongs to the current user
        from app.repositories.flight_search import FlightSearchRepository
        flight_search_repo = FlightSearchRepository(db)
        flight_search = flight_search_repo.get_by_id(flight_search_id, str(current_user.id))

        if not flight_search:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flight search not found or access denied"
            )

        # Create prediction service instance
        prediction_service = PredictionService(db)

        # Generate the prediction
        result = prediction_service.predict_price(
            prediction_request,
            str(current_user.id),
            flight_search_id
        )

        return result

    except ValueError as e:
        logger.error(f"Validation error in prediction: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction endpoint error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prediction service unavailable"
        )

@router.get("/", response_model=dict)
async def get_prediction_service_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get information about the prediction service and model.
    """
    try:
        prediction_service = PredictionService(db)
        info = prediction_service.get_model_info()
        return info
    except Exception as e:
        logger.error(f"Error getting prediction service info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve prediction service information"
        )

@router.get("/history", response_model=list)
async def get_prediction_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50
):
    """
    Get prediction history for the current user.
    """
    try:
        from app.repositories.prediction import PredictionRepository
        prediction_repo = PredictionRepository(db)
        predictions = prediction_repo.get_by_user_id(str(current_user.id), limit=limit)

        # Convert to response format
        result = []
        for pred in predictions:
            result.append({
                "id": pred.id,
                "predicted_price": float(pred.predicted_price),
                "currency": pred.currency,
                "is_estimate": True,
                "model_version": pred.model_version,
                "created_at": pred.created_at
            })

        return result
    except Exception as e:
        logger.error(f"Error retrieving prediction history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve prediction history"
        )