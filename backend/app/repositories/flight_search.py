from sqlalchemy.orm import Session
from app.models.flight_search import FlightSearch
from typing import Optional, List
from datetime import datetime

class FlightSearchRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: str, origin: str, destination: str, departure_date: datetime,
               return_date: Optional[datetime] = None, passengers: int = 1,
               cabin_class: str = "ECONOMY") -> FlightSearch:
        flight_search = FlightSearch(
            id=str(__import__('uuid').uuid4()),
            user_id=user_id,
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            passengers=passengers,
            cabin_class=cabin_class
        )
        self.db.add(flight_search)
        self.db.commit()
        self.db.refresh(flight_search)
        return flight_search

    def get_by_id(self, flight_search_id: str, user_id: str) -> Optional[FlightSearch]:
        return self.db.query(FlightSearch).filter(
            FlightSearch.id == flight_search_id,
            FlightSearch.user_id == user_id
        ).first()

    def get_by_user_id(self, user_id: str, limit: int = 100) -> List[FlightSearch]:
        return self.db.query(FlightSearch).filter(
            FlightSearch.user_id == user_id
        ).order_by(FlightSearch.created_at.desc()).limit(limit).all()