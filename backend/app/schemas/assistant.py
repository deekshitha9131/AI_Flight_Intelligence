from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.schemas.flight import FlightResponse

class FlightIntent(BaseModel):
    intent: str = Field(
        ...,
        description=(
            "The user's intent: GREETING, FLIGHT_SEARCH, FLIGHT_COMPARISON, "
            "PRICE_PREDICTION, RECOMMENDATION, GENERAL_FLIGHT_QUESTION, "
            "FOLLOW_UP, or UNKNOWN"
        ),
    )
    origin: Optional[str] = Field(None, description="Origin airport IATA code (e.g., 'HYD')")
    destination: Optional[str] = Field(None, description="Destination airport IATA code (e.g., 'DEL')")
    departure_date: Optional[datetime] = Field(None, description="Department date and time")
    return_date: Optional[datetime] = Field(None, description="Return date and time (for roundtrip)")
    passengers: int = Field(1, description="Number of passengers", ge=1, le=9)
    cabin: str = Field("ECONOMY", description="Cabin class (e.g., 'ECONOMY', 'BUSINESS')")
    time_preference: Optional[str] = Field(None, description="Time of day preference (e.g., 'morning', 'afternoon')")
    price_preference: Optional[str] = Field(None, description="Price preference (e.g., 'cheap', 'budget')")

    model_config = ConfigDict(from_attributes=True)


class AssistantChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class AssistantResponse(BaseModel):
    message: str
    conversation_id: str
    flight_results: Optional[List[FlightResponse]] = None
    requires_clarification: bool = False
    clarification_questions: Optional[List[str]] = None

    model_config = ConfigDict(from_attributes=True)