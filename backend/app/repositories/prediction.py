from sqlalchemy.orm import Session
from app.models.prediction import Prediction
from typing import Optional

class PredictionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: str, flight_search_id: str, predicted_price: float, currency: str, model_version: str = "v1.0.0") -> Prediction:
        prediction = Prediction(
            id=str(__import__('uuid').uuid4()),
            user_id=user_id,
            flight_search_id=flight_search_id,
            predicted_price=predicted_price,
            currency=currency,
            model_version=model_version
        )
        self.db.add(prediction)
        self.db.commit()
        self.db.refresh(prediction)
        return prediction

    def get_by_id(self, prediction_id: str, user_id: str) -> Optional[Prediction]:
        return self.db.query(Prediction).filter(
            Prediction.id == prediction_id,
            Prediction.user_id == user_id
        ).first()

    def get_by_user_id(self, user_id: str, limit: int = 100) -> list:
        return self.db.query(Prediction).filter(
            Prediction.user_id == user_id
        ).order_by(Prediction.created_at.desc()).limit(limit).all()