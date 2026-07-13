from __future__ import annotations

import logging
import math
from uuid import UUID

from app.exceptions.base import NotFoundException
from app.repositories.search_history_repository import SearchHistoryRepository
from app.schemas.search_history import (
    DeleteResponse,
    PaginationMeta,
    SearchHistoryDetailResponse,
    SearchHistoryItem,
    SearchHistoryListResponse,
)

logger = logging.getLogger(__name__)

_DEFAULT_PAGE_SIZE = 10
_MAX_PAGE_SIZE = 100


class SearchHistoryService:
    """Business logic for user search history management.

    Responsibilities:
    - Enforce ownership: users can only access their own records.
    - Calculate pagination metadata.
    - Map ORM models to clean Pydantic response schemas.
    - Raise NotFoundException for missing or unauthorised records.
    """

    def __init__(self, repository: SearchHistoryRepository) -> None:
        self._repository = repository

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_user_search_history(
        self,
        *,
        user_id: UUID,
        page: int,
        page_size: int,
    ) -> SearchHistoryListResponse:
        """Return a paginated list of search records for the authenticated user.

        Args:
            user_id:   UUID of the requesting user.
            page:      1-based page number.
            page_size: Number of records per page (capped at _MAX_PAGE_SIZE).

        Returns:
            SearchHistoryListResponse with data and pagination metadata.
        """
        page = max(1, page)
        page_size = max(1, min(page_size, _MAX_PAGE_SIZE))
        offset = (page - 1) * page_size

        records, total = self._repository.get_paginated_by_user(
            user_id=user_id,
            offset=offset,
            limit=page_size,
        )

        total_pages = max(1, math.ceil(total / page_size)) if total else 1

        items = [_to_item(r) for r in records]

        logger.info(
            "SearchHistoryService.get_user_search_history | user=%s page=%d size=%d total=%d",
            user_id,
            page,
            page_size,
            total,
        )

        return SearchHistoryListResponse(
            success=True,
            message="Search history retrieved successfully.",
            data=items,
            pagination=PaginationMeta(
                page=page,
                page_size=page_size,
                total_items=total,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_previous=page > 1,
            ),
        )

    def get_search_by_id(
        self,
        *,
        record_id: UUID,
        user_id: UUID,
    ) -> SearchHistoryDetailResponse:
        """Return a single search record owned by the authenticated user.

        Raises:
            NotFoundException: Record does not exist or belongs to another user.
        """
        record = self._repository.get_by_id(record_id=record_id, user_id=user_id)
        if record is None:
            raise NotFoundException(message="Search history record not found.")

        logger.info(
            "SearchHistoryService.get_search_by_id | user=%s record=%s",
            user_id,
            record_id,
        )

        return SearchHistoryDetailResponse(
            success=True,
            message="Search history record retrieved successfully.",
            data=_to_item(record),
        )

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def delete_search_history(
        self,
        *,
        record_id: UUID,
        user_id: UUID,
    ) -> DeleteResponse:
        """Delete a single search record owned by the authenticated user.

        Raises:
            NotFoundException: Record does not exist or belongs to another user.
        """
        deleted = self._repository.delete_one(record_id=record_id, user_id=user_id)
        if not deleted:
            raise NotFoundException(message="Search history record not found.")

        logger.info(
            "SearchHistoryService.delete_search_history | user=%s record=%s",
            user_id,
            record_id,
        )

        return DeleteResponse(
            success=True,
            message="Search history record deleted successfully.",
        )

    def clear_search_history(self, *, user_id: UUID) -> DeleteResponse:
        """Delete all search records for the authenticated user.

        Returns a success response even when the user had no history,
        making the operation safely idempotent.
        """
        count = self._repository.delete_all_by_user(user_id=user_id)

        logger.info(
            "SearchHistoryService.clear_search_history | user=%s deleted=%d",
            user_id,
            count,
        )

        return DeleteResponse(
            success=True,
            message=f"Search history cleared. {count} record(s) deleted.",
        )


# ---------------------------------------------------------------------------
# Private mapper
# ---------------------------------------------------------------------------


def _to_item(record: object) -> SearchHistoryItem:
    """Map a SearchHistory ORM instance to a SearchHistoryItem schema."""
    return SearchHistoryItem(
        id=record.id,  # type: ignore[attr-defined]
        origin=record.origin,  # type: ignore[attr-defined]
        destination=record.destination,  # type: ignore[attr-defined]
        departure_date=record.departure_date,  # type: ignore[attr-defined]
        return_date=record.return_date,  # type: ignore[attr-defined]
        adults=record.adults,  # type: ignore[attr-defined]
        children=record.children,  # type: ignore[attr-defined]
        infants=record.infants,  # type: ignore[attr-defined]
        travel_class=record.travel_class,  # type: ignore[attr-defined]
        currency=record.currency,  # type: ignore[attr-defined]
        non_stop=record.non_stop,  # type: ignore[attr-defined]
        result_count=record.result_count,  # type: ignore[attr-defined]
        search_timestamp=record.searched_at,  # type: ignore[attr-defined]
    )
