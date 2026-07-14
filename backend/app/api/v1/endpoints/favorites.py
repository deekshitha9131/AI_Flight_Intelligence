from __future__ import annotations

import logging
from uuid import UUID

from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.repositories.favorite_repository import FavoriteRepository
from app.schemas.favorite import (
    FavoriteDeleteResponse,
    FavoriteDetailResponse,
    FavoriteListResponse,
    SaveFavoriteRequest,
)
from app.services.favorite_service import FavoriteService
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/flights/favorites", tags=["favorites"])


@router.post(
    "",
    response_model=FavoriteDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save a flight to favourites",
    description=(
        "Save a flight offer to the authenticated user's favourites list. "
        "Saving the same offer twice returns `409 Conflict`.\n\n"
        "**Authentication required.**\n\n"
        "**Errors**\n"
        "- `401` — missing or invalid JWT token\n"
        "- `409` — flight offer already in favourites"
    ),
    responses={
        401: {"description": "Authentication required."},
        409: {"description": "Flight offer already saved in favourites."},
    },
)
async def save_favorite(
    payload: SaveFavoriteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FavoriteDetailResponse:
    """Save a flight offer as a favourite for the authenticated user."""
    service = FavoriteService(repository=FavoriteRepository(db=db))
    return service.save_favorite(user_id=current_user.id, payload=payload)


@router.get(
    "",
    response_model=FavoriteListResponse,
    status_code=status.HTTP_200_OK,
    summary="List favourite flights",
    description=(
        "Return a paginated list of the authenticated user's saved favourite flights, "
        "sorted newest-first.\n\n"
        "**Authentication required.**"
    ),
    responses={
        401: {"description": "Authentication required."},
    },
)
async def list_favorites(
    page: int = Query(1, ge=1, description="Page number (1-based)."),
    page_size: int = Query(10, ge=1, le=100, description="Records per page."),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FavoriteListResponse:
    """Return the authenticated user's paginated list of favourite flights."""
    service = FavoriteService(repository=FavoriteRepository(db=db))
    return service.get_favorites(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )


@router.delete(
    "/{record_id}",
    response_model=FavoriteDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove a favourite flight",
    description=(
        "Remove a specific flight from the authenticated user's favourites. "
        "Users can only delete their own records.\n\n"
        "**Authentication required.**"
    ),
    responses={
        401: {"description": "Authentication required."},
        404: {"description": "Favourite flight not found."},
    },
)
async def delete_favorite(
    record_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FavoriteDeleteResponse:
    """Remove a favourite flight record owned by the authenticated user."""
    service = FavoriteService(repository=FavoriteRepository(db=db))
    return service.delete_favorite(
        record_id=record_id,
        user_id=current_user.id,
    )
