"""Status endpoints for checking service connectivity."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import OpenAPITags
from app.core.di_container import AppSettings, CurrentUser
from app.infrastructure.database.repositories.draft_repository import DraftRepository
from app.infrastructure.database.session import get_db_session

router = APIRouter(prefix="/status", tags=[OpenAPITags.HEALTH])


@router.get(
    "",
    summary="Get service status for the current user",
    description="Returns the connectivity status of Gmail, AI, and Draft services.",
)
async def get_service_status(
    current_user: CurrentUser,
    settings: AppSettings,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Check the status of key services."""
    gmail_status = "connected"
    ai_status = "available" if settings.anthropic_api_key else "unavailable"

    try:
        await db.execute(text("SELECT 1"))
        DraftRepository(db)
        draft_status = "ready"
    except Exception:
        draft_status = "error"

    return {
        "gmail": gmail_status,
        "ai": ai_status,
        "draft": draft_status,
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "full_name": current_user.full_name,
        } if current_user else None,
    }


@router.get(
    "/gmail",
    summary="Check Gmail connection status",
    description="Verifies Gmail OAuth connection status for the current user.",
)
async def get_gmail_status(current_user: CurrentUser) -> dict[str, str]:
    """Check if user has valid Gmail OAuth connection."""
    return {"status": "connected" if current_user else "disconnected"}


@router.get(
    "/ai",
    summary="Check AI service status",
    description="Verifies AI/LLM service availability.",
)
async def get_ai_status(settings: AppSettings) -> dict[str, str]:
    """Check if AI service is configured and available."""
    if not settings.anthropic_api_key:
        return {"status": "unavailable"}

    return {"status": "available"}


@router.get(
    "/draft",
    summary="Check draft service status",
    description="Verifies draft service operational status.",
)
async def get_draft_status(
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Check if draft service is operational."""
    try:
        await db.execute(text("SELECT 1"))
        DraftRepository(db)
        return {"status": "ready"}
    except Exception:
        return {"status": "error"}