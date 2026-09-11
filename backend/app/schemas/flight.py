from pydantic import BaseModel, Field, ConfigDict, validator
from typing import List, Optional
from datetime import datetime

class FlightSearchRequest(BaseModel):
    origin: str = Field(..., min_length=3, max_length=3)  # IATA code
    destination: str = Field(..., min_length=3, max_length=3)  # IATA code
    departure_date: datetime
    return_date: Optional[datetime] = None
    passengers: int = Field(..., ge=1, le=9)
    cabin_class: str  # e.g., ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST
    currency: str = Field(..., min_length=3, max_length=3)  # ISO 4217 currency code

    @validator('return_date')
    def return_date_must_be_after_departure_date(cls, v, values):
        if v is not None:
            departure_date = values.get('departure_date')
            if departure_date is not None and v <= departure_date:
                raise ValueError('Return date must be after departure date')
        return v

class FlightSegment(BaseModel):
    id: Optional[str] = None
    airline: str
    flight_number: str
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime

class FareOption(BaseModel):
    id: str
    price: float
    currency: str

class FlightResponse(BaseModel):
    id: str
    airline: str
    flight_number: str
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    duration: int  # in minutes
    stops: int
    price: float
    currency: str
    itinerary_id: Optional[str] = None
    segments: List[FlightSegment] = Field(default_factory=list)
    return_segments: List[FlightSegment] = Field(default_factory=list)
    return_departure_time: Optional[datetime] = None
    return_arrival_time: Optional[datetime] = None
    return_duration: Optional[int] = None
    return_stops: Optional[int] = None
    fare_options: List[FareOption] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)