from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.favorite_flight import FavoriteFlight

logger = logging.getLogger(__name__)


class FavoriteRepository:
    """Repository layer for favourite flight persistence operations.

    Every query is scoped to a user_id so data from one user can never
    leak to another, even if a bug exists in the service layer.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def create(
        self,
        *,
        user_id: UUID,
        flight_offer_id: str,
        airline: str,
        origin: str,
        destination: str,
        departure: str,
        arrival: str,
        price: float,
        currency: str,
    ) -> FavoriteFlight:
        """Persist a new favourite flight record and return it."""
        record = FavoriteFlight(
            user_id=user_id,
            flight_offer_id=flight_offer_id,
            airline=airline,
            origin=origin,
            destination=destination,
            departure=departure,
            arrival=arrival,
            price=price,
            currency=currency,
        )
        self._db.add(record)
        self._db.flush()
        logger.info(
            "FavoriteRepository.create | user=%s offer=%s id=%s",
            user_id,
            flight_offer_id,
            record.id,
        )
        return record

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def exists(self, *, user_id: UUID, flight_offer_id: str) -> bool:
        """Return True when the user has already saved this offer."""
        count: int = (
            self._db.scalar(
                select(func.count())
                .select_from(FavoriteFlight)
                .where(
                    FavoriteFlight.user_id == user_id,
                    FavoriteFlight.flight_offer_id == flight_offer_id,
                )
            )
            or 0
        )
        return count > 0

    def get_by_id(self, *, record_id: UUID, user_id: UUID) -> FavoriteFlight | None:
        """Return a single favourite owned by the user, or None."""
        return self._db.scalar(
            select(FavoriteFlight).where(
                FavoriteFlight.id == record_id,
                FavoriteFlight.user_id == user_id,
            )
        )

    def get_all_by_user(
        self,
        *,
        user_id: UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[FavoriteFlight], int]:
        """Return a page of favourites for a user, sorted newest-first.

        Returns:
            A tuple of (records, total_count).
        """
        base_filter = FavoriteFlight.user_id == user_id

        total: int = (
            self._db.scalar(
                select(func.count()).select_from(FavoriteFlight).where(base_filter)
            )
            or 0
        )

        records = list(
            self._db.scalars(
                select(FavoriteFlight)
                .where(base_filter)
                .order_by(FavoriteFlight.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        )

        logger.debug(
            "FavoriteRepository.get_all_by_user | user=%s offset=%d limit=%d total=%d",
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
        """Delete a single favourite owned by the user.

        Returns:
            True if a row was deleted, False if no matching record existed.
        """
        result = self._db.execute(
            delete(FavoriteFlight).where(
                FavoriteFlight.id == record_id,
                FavoriteFlight.user_id == user_id,
            )
        )
        self._db.flush()
        deleted = result.rowcount > 0
        logger.info(
            "FavoriteRepository.delete_one | user=%s record=%s deleted=%s",
            user_id,
            record_id,
            deleted,
        )
        return deleted
