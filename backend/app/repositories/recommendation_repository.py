from __future__ import annotations

import json
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.recommendation_log import RecommendationLog

logger = logging.getLogger(__name__)


class RecommendationRepository:
    """Repository layer for recommendation log persistence."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(
        self,
        *,
        user_id: UUID,
        recommendation_type: str,
        payload: list,
        reasoning: str | None = None,
    ) -> RecommendationLog:
        """Persist a recommendation event."""
        record = RecommendationLog(
            user_id=user_id,
            recommendation_type=recommendation_type,
            payload=json.dumps(payload),
            reasoning=reasoning,
        )
        self._db.add(record)
        self._db.flush()
        logger.info(
            "RecommendationRepository.create | user=%s type=%s count=%d",
            user_id,
            recommendation_type,
            len(payload),
        )
        return record

    def get_latest_by_user_and_type(
        self,
        *,
        user_id: UUID,
        recommendation_type: str,
    ) -> RecommendationLog | None:
        """Return the most recent recommendation log for a user+type pair."""
        return self._db.scalar(
            select(RecommendationLog)
            .where(
                RecommendationLog.user_id == user_id,
                RecommendationLog.recommendation_type == recommendation_type,
            )
            .order_by(RecommendationLog.created_at.desc())
            .limit(1)
        )
