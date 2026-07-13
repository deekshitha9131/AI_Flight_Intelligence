from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.flight_search import FlightSearch

logger = logging.getLogger(__name__)


class SearchHistoryRepository:
    """Repository layer for search history persistence operations.

    All queries are scoped to a specific user_id so that data from one user
    can never leak to another, even if a bug exists in the service layer.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get_by_id(self, *, record_id: UUID, user_id: UUID) -> FlightSearch | None:
        """Return a single search record owned by the given user, or None."""
        statement = select(FlightSearch).where(
            FlightSearch.id == record_id,
            FlightSearch.user_id == user_id,
        )
        return self._db.scalar(statement)

    def get_paginated_by_user(
        self,
        *,
        user_id: UUID,
        offset: int,
        limit: int,
    ) -> tuple[list[FlightSearch], int]:
        """Return a page of search records for a user, sorted newest-first.

        Returns:
            A tuple of (records, total_count).
        """
        base_filter = FlightSearch.user_id == user_id

        total: int = (
            self._db.scalar(
                select(func.count()).select_from(FlightSearch).where(base_filter)
            )
            or 0
        )

        records = list(
            self._db.scalars(
                select(FlightSearch)
                .where(base_filter)
                .order_by(FlightSearch.searched_at.desc())
                .offset(offset)
                .limit(limit)
            )
        )

        logger.debug(
            "SearchHistoryRepository.get_paginated_by_user | user=%s offset=%d limit=%d total=%d",
            user_id,
            offset,
            limit,
            total,
        )
        return records, total

    # ------------------------------------------------------------------
    # Deletes
    # ------------------------------------------------------------------

    def delete_one(self, *, record_id: UUID, user_id: UUID) -> bool:
        """Delete a single search record owned by the user.

        Returns:
            True if a row was deleted, False if no matching record existed.
        """
        statement = delete(FlightSearch).where(
            FlightSearch.id == record_id,
            FlightSearch.user_id == user_id,
        )
        result = self._db.execute(statement)
        self._db.flush()

        deleted = result.rowcount > 0
        logger.info(
            "SearchHistoryRepository.delete_one | user=%s record=%s deleted=%s",
            user_id,
            record_id,
            deleted,
        )
        return deleted

    def delete_all_by_user(self, *, user_id: UUID) -> int:
        """Delete all search records for a user.

        Returns:
            Number of rows deleted.
        """
        statement = delete(FlightSearch).where(FlightSearch.user_id == user_id)
        result = self._db.execute(statement)
        self._db.flush()

        count: int = result.rowcount
        logger.info(
            "SearchHistoryRepository.delete_all_by_user | user=%s deleted=%d",
            user_id,
            count,
        )
        return count
