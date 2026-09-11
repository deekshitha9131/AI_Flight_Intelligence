from sqlalchemy.orm import Session
from app.models.preference import Preference
from app.schemas.preference import PreferenceCreate, PreferenceUpdate


def get_preference_by_user_id(db: Session, user_id: str):
    return db.query(Preference).filter(Preference.user_id == user_id).first()


def create_preference(db: Session, preference: PreferenceCreate, user_id: str):
    db_preference = Preference(
        **preference.dict(),
        user_id=user_id
    )
    db.add(db_preference)
    db.commit()
    db.refresh(db_preference)
    return db_preference


def update_preference(db: Session, user_id: str, preference: PreferenceUpdate):
    db_preference = get_preference_by_user_id(db, user_id)
    if db_preference:
        update_data = preference.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_preference, key, value)
        db.commit()
        db.refresh(db_preference)
    return db_preference