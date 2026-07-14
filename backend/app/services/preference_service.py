from __future__ import annotations

import json
import logging
import statistics
from collections import Counter
from uuid import UUID

from app.exceptions.base import NotFoundException
from app.repositories.preference_repository import PreferenceRepository
from app.repositories.search_history_repository import SearchHistoryRepository
from app.schemas.insights import UserPreferenceItem, UserPreferenceResponse
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_TOP_N = 5  # number of top items to keep per preference list


class PreferenceService:
    """Derive and persist user preference profiles from search history.

    Called:
    - On-demand via GET /api/v1/ai/preferences (returns current profile).
    - As a background task after every flight search to keep the profile fresh.
    """

    def __init__(
        self,
        preference_repo: PreferenceRepository,
        search_history_repo: SearchHistoryRepository,
    ) -> None:
        self._pref_repo = preference_repo
        self._history_repo = search_history_repo

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_preferences(self, *, user_id: UUID) -> UserPreferenceResponse:
        """Return the current preference profile for the user.

        If no profile exists yet, compute it from search history first.
        """
        profile = self._pref_repo.get_by_user(user_id=user_id)
        if profile is None:
            profile = self._compute_and_save(user_id=user_id)

        return UserPreferenceResponse(
            success=True,
            message="User preferences retrieved successfully.",
            data=_to_item(profile),
        )

    def refresh_preferences(self, *, user_id: UUID) -> None:
        """Recompute and persist the preference profile from search history.

        Designed to be called as a fire-and-forget background task.
        """
        try:
            self._compute_and_save(user_id=user_id)
            logger.info(
                "PreferenceService.refresh_preferences | user=%s updated.", user_id
            )
        except Exception as exc:
            logger.error(
                "PreferenceService.refresh_preferences | user=%s failed: %s",
                user_id,
                exc,
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _compute_and_save(self, *, user_id: UUID):
        """Derive preference signals from all search history and upsert."""
        # Fetch all history (large limit — preferences are a full-scan operation)
        records, _ = self._history_repo.get_paginated_by_user(
            user_id=user_id, offset=0, limit=1000
        )

        destinations = Counter(r.destination for r in records)
        origins = Counter(r.origin for r in records)
        cabins = Counter(r.travel_class for r in records)
        currencies = Counter(r.currency for r in records)
        months = Counter(
            int(r.departure_date[5:7])
            for r in records
            if r.departure_date and len(r.departure_date) >= 7
        )

        preferred_cabin = cabins.most_common(1)[0][0] if cabins else "ECONOMY"
        preferred_currency = currencies.most_common(1)[0][0] if currencies else "USD"

        top_destinations = [d for d, _ in destinations.most_common(_TOP_N)]
        top_origins = [o for o, _ in origins.most_common(_TOP_N)]
        top_months = [m for m, _ in months.most_common(6)]

        # Budget signals — not available from search history alone; use None
        avg_budget = None
        min_budget = None
        max_budget = None

        profile = self._pref_repo.upsert(
            user_id=user_id,
            preferred_airlines=[],
            favorite_destinations=top_destinations,
            frequent_origins=top_origins,
            avg_budget=avg_budget,
            min_budget=min_budget,
            max_budget=max_budget,
            preferred_cabin=preferred_cabin,
            total_searches=len(records),
            preferred_departure_time=None,
            preferred_months=top_months,
            preferred_currency=preferred_currency,
        )
        return profile


# ---------------------------------------------------------------------------
# Mapper
# ---------------------------------------------------------------------------


def _to_item(profile) -> UserPreferenceItem:
    return UserPreferenceItem(
        id=profile.id,
        user_id=profile.user_id,
        preferred_airlines=_parse_json_list(profile.preferred_airlines),
        favorite_destinations=_parse_json_list(profile.favorite_destinations),
        frequent_origins=_parse_json_list(profile.frequent_origins),
        avg_budget=profile.avg_budget,
        min_budget=profile.min_budget,
        max_budget=profile.max_budget,
        preferred_cabin=profile.preferred_cabin,
        total_searches=profile.total_searches,
        preferred_departure_time=profile.preferred_departure_time,
        preferred_months=_parse_json_list(profile.preferred_months),
        preferred_currency=profile.preferred_currency,
        updated_at=profile.updated_at,
    )


def _parse_json_list(value: str) -> list:
    try:
        return json.loads(value) if value else []
    except Exception:
        return []
