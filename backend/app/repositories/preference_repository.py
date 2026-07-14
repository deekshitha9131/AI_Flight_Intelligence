from __future__ import annotations

import json
import logging
from uuid import UUID

from app.models.user_preference import UserPreferenceProfile
from sqlalchemy import select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class PreferenceRepository:
    """Repository layer for user preference profile persistence."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_user(self, *, user_id: UUID) -> UserPreferenceProfile | None:
        """Return the preference profile for a user, or None."""
        return self._db.scalar(
            select(UserPreferenceProfile).where(
                UserPreferenceProfile.user_id == user_id
            )
        )

    def upsert(
        self,
        *,
        user_id: UUID,
        preferred_airlines: list[str],
        favorite_destinations: list[str],
        frequent_origins: list[str],
        avg_budget: float | None,
        min_budget: float | None,
        max_budget: float | None,
        preferred_cabin: str,
        total_searches: int,
        preferred_departure_time: str | None,
        preferred_months: list[int],
        preferred_currency: str,
    ) -> UserPreferenceProfile:
        """Create or update the preference profile for a user."""
        from datetime import datetime, timezone

        record = self.get_by_user(user_id=user_id)
        if record is None:
            record = UserPreferenceProfile(user_id=user_id)
            self._db.add(record)

        record.preferred_airlines = json.dumps(preferred_airlines)
        record.favorite_destinations = json.dumps(favorite_destinations)
        record.frequent_origins = json.dumps(frequent_origins)
        record.avg_budget = avg_budget
        record.min_budget = min_budget
        record.max_budget = max_budget
        record.preferred_cabin = preferred_cabin
        record.total_searches = total_searches
        record.preferred_departure_time = preferred_departure_time
        record.preferred_months = json.dumps(preferred_months)
        record.preferred_currency = preferred_currency
        record.updated_at = datetime.now(timezone.utc)

        self._db.flush()
        logger.info(
            "PreferenceRepository.upsert | user=%s searches=%d", user_id, total_searches
        )
        return record
