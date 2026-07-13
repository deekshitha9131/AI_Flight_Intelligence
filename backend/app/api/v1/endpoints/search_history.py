from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.repositories.search_history_repository import SearchHistoryRepository
from app.schemas.search_history import (
    DeleteResponse,
    SearchHistoryDetailResponse,
    SearchHistoryListResponse,
)
from app.services.search_history_service import SearchHistoryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/flights/history", tags=["search-history"])


@router.get(
    "",
    response_model=SearchHistoryListResponse,
    status_code=status.HTTP_200_OK,
    summary="List flight search history",
    description=(
        "Return a paginated list of the authenticated user's past flight searches, "
        "sorted newest-first.\n\n"
        "**Authentication required.**"
    ),
    responses={
        401: {"description": "Authentication required."},
    },
)
async def list_search_history(
    page: int = Query(1, ge=1, description="Page number (1-based)."),
    page_size: int = Query(10, ge=1, le=100, description="Records per page."),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SearchHistoryListResponse:
    """Return the authenticated user's paginated search history."""
    service = SearchHistoryService(repository=SearchHistoryRepository(db=db))
    return service.get_user_search_history(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{record_id}",
    response_model=SearchHistoryDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a single search history record",
    description=(
        "Return a single flight search record by its UUID. "
        "Users can only access their own records.\n\n"
        "**Authentication required.**"
    ),
    responses={
        401: {"description": "Authentication required."},
        404: {"description": "Search history record not found."},
    },
)
async def get_search_history_record(
    record_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SearchHistoryDetailResponse:
    """Return a single search history record owned by the authenticated user."""
    service = SearchHistoryService(repository=SearchHistoryRepository(db=db))
    return service.get_search_by_id(
        record_id=record_id,
        user_id=current_user.id,
    )


@router.delete(
    "/{record_id}",
    response_model=DeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a single search history record",
    description=(
        "Delete a specific flight search record by its UUID. "
        "Users can only delete their own records.\n\n"
        "**Authentication required.**"
    ),
    responses={
        401: {"description": "Authentication required."},
        404: {"description": "Search history record not found."},
    },
)
async def delete_search_history_record(
    record_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeleteResponse:
    """Delete a single search history record owned by the authenticated user."""
    service = SearchHistoryService(repository=SearchHistoryRepository(db=db))
    return service.delete_search_history(
        record_id=record_id,
        user_id=current_user.id,
    )


@router.delete(
    "",
    response_model=DeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Clear all search history",
    description=(
        "Delete all flight search records for the authenticated user. "
        "This operation is idempotent — it succeeds even when there is no history.\n\n"
        "**Authentication required.**"
    ),
    responses={
        401: {"description": "Authentication required."},
    },
)
async def clear_search_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeleteResponse:
    """Delete all search history records for the authenticated user."""
    service = SearchHistoryService(repository=SearchHistoryRepository(db=db))
    return service.clear_search_history(user_id=current_user.id)
