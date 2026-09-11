from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas.preference import PreferenceCreate, PreferenceInDB
from app.services.preference import get_preference, create_or_update_preference
from app.core.dependencies import get_db, get_current_user
from app.models.user import User

router = APIRouter(
    prefix="/preferences",
    tags=["preferences"],
    responses={404: {"description": "Not found"}},
)

@router.get("/", response_model=PreferenceInDB)
def get_user_preference(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the current user's preferences.
    Creates an empty preference record when none exists yet.
    """
    preference = get_preference(db, current_user.id)
    if preference is None:
        preference = create_or_update_preference(
            db,
            current_user.id,
            PreferenceCreate(),
        )
    return preference

@router.put("/", response_model=PreferenceInDB)
def create_or_update_user_preference(
    preference: PreferenceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create or update the current user's preferences.
    """
    db_preference = create_or_update_preference(
        db,
        current_user.id,
        preference
    )
    return db_preference
