from app.api.v1.endpoints import (
    ai,
    airports,
    assistant,
    auth,
    bookings,
    favorites,
    flights,
    health,
    hotels,
    recommendations,
    search_history,
)
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1")
router.include_router(health.router)
router.include_router(auth.router)
router.include_router(airports.router)
router.include_router(flights.router)
router.include_router(hotels.router)
router.include_router(search_history.router)
router.include_router(favorites.router)
router.include_router(bookings.router)
router.include_router(ai.router)
router.include_router(recommendations.router)
router.include_router(assistant.router)

