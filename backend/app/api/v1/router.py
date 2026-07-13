from fastapi import APIRouter

from app.api.v1.endpoints import (
    ai,
    airports,
    assistant,
    auth,
    favorites,
    flights,
    health,
    recommendations,
    search_history,
)

router = APIRouter(prefix="/api/v1")
router.include_router(health.router)
router.include_router(auth.router)
router.include_router(airports.router)
router.include_router(flights.router)
router.include_router(search_history.router)
router.include_router(favorites.router)
router.include_router(ai.router)
router.include_router(recommendations.router)
router.include_router(assistant.router)
