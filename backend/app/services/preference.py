from sqlalchemy.orm import Session
from app.repositories.preference import get_preference_by_user_id, create_preference, update_preference
from app.schemas.preference import PreferenceCreate, PreferenceUpdate, PreferenceInDB


def get_preference(db: Session, user_id: str):
    """
    Get preference for a user.
    Returns None if no preference exists.
    """
    db_preference = get_preference_by_user_id(db, user_id)
    if db_preference:
        return PreferenceInDB.model_validate(db_preference)
    return None


def create_or_update_preference(db: Session, user_id: str, preference: PreferenceCreate):
    """
    Create a new preference for the user if none exists,
    otherwise update the existing one.
    """
    db_preference = get_preference_by_user_id(db, user_id)
    if db_preference:
        # Update existing
        updated_preference = update_preference(db, user_id, preference)
        return PreferenceInDB.model_validate(updated_preference)
    else:
        # Create new
        created_preference = create_preference(db, preference, user_id)
        return PreferenceInDB.model_validate(created_preference)