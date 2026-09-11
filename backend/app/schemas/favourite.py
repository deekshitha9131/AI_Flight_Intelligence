from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class FavouriteCreate(BaseModel):
    flight_id: str = Field(..., max_length=100)
    airline: str
    flight_number: str
    origin: str = Field(..., min_length=3, max_length=3)
    destination: str = Field(..., min_length=3, max_length=3)
    departure_time: datetime
    arrival_time: datetime
    duration: int = Field(..., ge=0)
    stops: int = Field(..., ge=0)
    price: float = Field(..., ge=0)
    currency: str = Field(..., min_length=3, max_length=3)

class FavouriteResponse(FavouriteCreate):
    id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)