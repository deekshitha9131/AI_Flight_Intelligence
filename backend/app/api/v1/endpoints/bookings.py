from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from app.dependencies.auth import get_current_user
from app.models.user import User
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bookings", tags=["bookings"])


class BookingPayload(BaseModel):
    flight_offer_id: str = Field(..., min_length=1)
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    email: str = Field(..., min_length=1)
    travelers: int = Field(default=1, ge=1, le=9)


class BookingRecord(BaseModel):
    id: str
    flight_offer_id: str
    status: str
    amount: float
    currency: str
    created_at: str


class BookingListResponse(BaseModel):
    success: bool
    message: str
    data: list[BookingRecord]


class BookingDetailResponse(BaseModel):
    success: bool
    message: str
    data: BookingRecord


# In-memory storage for bookings during development session
_in_memory_bookings: dict[str, list[dict]] = {}


@router.get(
    "",
    response_model=BookingListResponse,
    status_code=status.HTTP_200_OK,
    summary="List user bookings",
    description="Return all flight bookings created by the authenticated user.",
)
async def list_bookings(
    current_user: User = Depends(get_current_user),
) -> BookingListResponse:
    """Return bookings for the active user."""
    user_id = str(current_user.id)
    records = _in_memory_bookings.get(user_id, [])
    return BookingListResponse(
        success=True,
        message="Bookings retrieved successfully.",
        data=[BookingRecord(**rec) for rec in records],
    )


@router.post(
    "",
    response_model=BookingDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new flight booking",
    description="Reserve a flight offer for the authenticated user.",
)
async def create_booking(
    payload: BookingPayload,
    current_user: User = Depends(get_current_user),
) -> BookingDetailResponse:
    """Create a new booking record."""
    user_id = str(current_user.id)
    new_record = {
        "id": str(uuid4()),
        "flight_offer_id": payload.flight_offer_id,
        "status": "CONFIRMED",
        "amount": 450.0,
        "currency": "USD",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if user_id not in _in_memory_bookings:
        _in_memory_bookings[user_id] = []
    _in_memory_bookings[user_id].insert(0, new_record)

    logger.info("Booking created for user %s: %s", user_id, new_record["id"])

    return BookingDetailResponse(
        success=True,
        message="Booking created successfully.",
        data=BookingRecord(**new_record),
    )
