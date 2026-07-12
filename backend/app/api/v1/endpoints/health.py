from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Return health status for monitoring and readiness checks."""
    return HealthResponse(
        status="healthy",
        application="AI Flight Intelligence Platform",
        version="1.0.0",
    )
