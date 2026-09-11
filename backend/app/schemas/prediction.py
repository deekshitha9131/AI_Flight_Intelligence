from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.prediction import Prediction

class PredictionRequest(BaseModel):
    origin: str = Field(..., min_length=3, max_length=3)  # IATA code
    destination: str = Field(..., min_length=3, max_length=3)  # IATA code
    departure_date: datetime
    passengers: int = Field(..., ge=1, le=9)
    cabin_class: str  # e.g., ECONOMY, BUSINESS
    currency: str = Field(..., min_length=3, max_length=3)  # ISO 4217 currency code
    airline: str  # Airline name from Duffel response
    flight_number: str  # Flight number from Duffel response
    departure_time: str  # HH:MM format (e.g., "14:30")
    arrival_time: str  # HH:MM format (e.g., "16:45")
    duration_minutes: int = Field(..., ge=0)  # Duration in minutes
    stops: int = Field(..., ge=0)  # Number of stops (0, 1, 2, ...)

    model_config = ConfigDict(from_attributes=True)

class PredictionResponse(BaseModel):
    predicted_price: float
    currency: str
    is_estimate: bool = True
    model_version: str = Field(alias='model_version')

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )

class PredictionResponseWithID(BaseModel):
    id: str
    predicted_price: float
    currency: str
    is_estimate: bool = True
    model_version: str = Field(alias='model_version')
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )