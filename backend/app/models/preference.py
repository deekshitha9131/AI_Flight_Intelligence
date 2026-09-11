import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, func, Float
from sqlalchemy.orm import relationship
from app.database.session import Base

class Preference(Base):
    __tablename__ = "preferences"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True)
    preferred_cabin = Column(String(20), nullable=True)  # e.g., 'ECONOMY'
    preferred_currency = Column(String(3), nullable=True)  # e.g., 'USD'
    preferred_airport = Column(String(10), nullable=True)  # IATA code
    preferred_time = Column(String(20), nullable=True)  # e.g., 'morning', 'evening'
    min_price = Column(Float, nullable=True)  # minimum preferred price
    max_price = Column(Float, nullable=True)  # maximum preferred price
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="preferences")