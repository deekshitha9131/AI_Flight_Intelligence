from __future__ import annotations

import logging
import math
from uuid import UUID

from app.exceptions.base import ConflictException, NotFoundException
from app.repositories.favorite_repository import FavoriteRepository
from app.schemas.favorite import (
    FavoriteDeleteResponse,
    FavoriteDetailResponse,
    FavoriteFlightItem,
    FavoriteListResponse,
    SaveFavoriteRequest,
)
from app.schemas.search_history import PaginationMeta

logger = logging.getLogger(__name__)

_MAX_PAGE_SIZE = 100


class FavoriteService:
    """Business logic for favourite flight management.

    Responsibilities:
    - Prevent duplicate favourites per user via ConflictException.
    - Enforce ownership: users can only access their own records.
    - Map ORM models to clean Pydantic response schemas.
    - Raise NotFoundException for missing or unauthorised records.
    """

    def __init__(self, repository: FavoriteRepository) -> None:
        self._repository = repository

    def save_favorite(
        self,
        *,
        user_id: UUID,
        payload: SaveFavoriteRequest,
    ) -> FavoriteDetailResponse:
        """Save a flight offer as a favourite for the authenticated user.

        Raises:
            ConflictException: The user has already saved this offer.
        """
        if self._repository.exists(
            user_id=user_id,
            flight_offer_id=payload.flight_offer_id,
        ):
            raise ConflictException(
                message="This flight offer is already in your favourites."
            )

        record = self._repository.create(
            user_id=user_id,
            flight_offer_id=payload.flight_offer_id,
            airline=payload.airline,
            origin=payload.origin.upper(),
            destination=payload.destination.upper(),
            departure=payload.departure,
            arrival=payload.arrival,
            price=payload.price,
            currency=payload.currency.upper(),
        )

        logger.info(
            "FavoriteService.save_favorite | user=%s offer=%s",
            user_id,
            payload.flight_offer_id,
        )

        return FavoriteDetailResponse(
            success=True,
            message="Flight saved to favourites.",
            data=_to_item(record),
        )

    def get_favorites(
        self,
        *,
        user_id: UUID,
        page: int,
        page_size: int,
    ) -> FavoriteListResponse:
        """Return a paginated list of favourites for the authenticated user."""
        page = max(1, page)
        page_size = max(1, min(page_size, _MAX_PAGE_SIZE))
        offset = (page - 1) * page_size

        records, total = self._repository.get_all_by_user(
            user_id=user_id,
            offset=offset,
            limit=page_size,
        )

        logger.info(
            "FavoriteService.get_favorites | user=%s page=%d size=%d total=%d",
            user_id,
            page,
            page_size,
            total,
        )

        return FavoriteListResponse(
            success=True,
            message="Favourite flights retrieved successfully.",
            data=[_to_item(r) for r in records],
            count=total,
        )

    def delete_favorite(
        self,
        *,
        record_id: UUID,
        user_id: UUID,
    ) -> FavoriteDeleteResponse:
        """Delete a single favourite owned by the authenticated user.

        Raises:
            NotFoundException: Record does not exist or belongs to another user.
        """
        deleted = self._repository.delete_one(record_id=record_id, user_id=user_id)
        if not deleted:
            raise NotFoundException(message="Favourite flight not found.")

        logger.info(
            "FavoriteService.delete_favorite | user=%s record=%s",
            user_id,
            record_id,
        )

        return FavoriteDeleteResponse(
            success=True,
            message="Favourite flight removed successfully.",
        )


# ---------------------------------------------------------------------------
# Private mapper
# ---------------------------------------------------------------------------


def _to_item(record: object) -> FavoriteFlightItem:
    """Map a FavoriteFlight ORM instance to a FavoriteFlightItem schema."""
    return FavoriteFlightItem(
        id=record.id,  # type: ignore[attr-defined]
        flight_offer_id=record.flight_offer_id,  # type: ignore[attr-defined]
        airline=record.airline,  # type: ignore[attr-defined]
        origin=record.origin,  # type: ignore[attr-defined]
        destination=record.destination,  # type: ignore[attr-defined]
        departure=record.departure,  # type: ignore[attr-defined]
        arrival=record.arrival,  # type: ignore[attr-defined]
        price=record.price,  # type: ignore[attr-defined]
        currency=record.currency,  # type: ignore[attr-defined]
        created_at=record.created_at,  # type: ignore[attr-defined]
    )
