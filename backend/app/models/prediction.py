import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, func
from sqlalchemy.orm import relationship
from app.database.session import Base

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    flight_search_id = Column(String(36), ForeignKey("flight_searches.id"), nullable=False)
    predicted_price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False)  # e.g., 'USD', 'EUR'
    model_version = Column(String(20), nullable=False, default='v1.0.0')
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="predictions")
    flight_search = relationship("FlightSearch", back_populates="predictions")