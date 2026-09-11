import uuid
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database.session import Base

class FlightSearch(Base):
    __tablename__ = "flight_searches"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    origin = Column(String(10), nullable=False)  # IATA code, e.g., 'JFK'
    destination = Column(String(10), nullable=False)  # IATA code
    departure_date = Column(DateTime(timezone=True), nullable=False)
    return_date = Column(DateTime(timezone=True), nullable=True)
    passengers = Column(Integer, nullable=False, default=1)
    cabin_class = Column(String(20), nullable=False)  # e.g., 'ECONOMY', 'BUSINESS'
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="flight_searches")
    predictions = relationship("Prediction", back_populates="flight_search", cascade="all, delete-orphan")