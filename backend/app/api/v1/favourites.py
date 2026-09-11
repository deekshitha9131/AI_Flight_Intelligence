from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, get_db
from app.models.favourite import Favourite
from app.models.user import User
from app.schemas.favourite import FavouriteCreate, FavouriteResponse

router = APIRouter(prefix="/favourites", tags=["favourites"])

@router.get("", response_model=list[FavouriteResponse])
def list_favourites(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Favourite).filter(Favourite.user_id == str(current_user.id)).order_by(Favourite.created_at.desc()).all()

@router.post("", response_model=FavouriteResponse, status_code=status.HTTP_201_CREATED)
def create_favourite(payload: FavouriteCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.query(Favourite).filter(Favourite.user_id == str(current_user.id), Favourite.flight_id == payload.flight_id).first()
    if existing:
        return existing
    favourite = Favourite(user_id=str(current_user.id), **payload.model_dump())
    db.add(favourite)
    db.commit()
    db.refresh(favourite)
    return favourite

@router.delete("/{flight_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_favourite(flight_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    favourite = db.query(Favourite).filter(Favourite.user_id == str(current_user.id), Favourite.flight_id == flight_id).first()
    if not favourite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Favourite not found")
    db.delete(favourite)
    db.commit()