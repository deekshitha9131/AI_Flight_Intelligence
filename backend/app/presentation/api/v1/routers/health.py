"""Health check endpoints (versioned).

Distinct from the root, unversioned `/health` liveness probe registered
directly in app/main.py: this endpoint is a *readiness* check — it
verifies the app can actually reach its dependencies, not just that the
process is running. Container orchestrators use liveness to decide
"should I restart this container"; readiness answers "should traffic be
routed to it right now." Conflating the two means a slow database
briefly takes the container down entirely instead of just pausing
traffic to it — this split avoids that.
"""

from typing import Any

from fastapi import APIRouter
from sqlalchemy import text

from app.core.constants import HEALTH_STATUS_DEGRADED, HEALTH_STATUS_OK, OpenAPITags
from app.core.di_container import DbSession, RedisClient
from app.infrastructure.cache.redis_client import ping_redis

router = APIRouter(prefix="/health", tags=[OpenAPITags.HEALTH])


@router.get(
    "/ready",
    summary="Readiness check",
    description="Verifies the API can reach PostgreSQL and Redis. "
    "Used by orchestration to decide whether to route traffic here.",
)
async def readiness_check(db: DbSession, redis_client: RedisClient) -> dict[str, Any]:
    # The ignore above is required at this usage site specifically —
    # see app/infrastructure/cache/redis_client.py's module docstring.
    # mypy re-checks RedisClient's expansion (Annotated[redis.Redis, ...])
    # here, not at its definition in app/core/di_container.py, which is
    # why the ignore lives on this line rather than there.
    checks: dict[str, str] = {}

    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = HEALTH_STATUS_OK
    except Exception:  # noqa: BLE001 — readiness check must never itself raise
        checks["database"] = HEALTH_STATUS_DEGRADED

    checks["redis"] = HEALTH_STATUS_OK if await ping_redis(redis_client) else HEALTH_STATUS_DEGRADED

    overall = (
        HEALTH_STATUS_OK
        if all(v == HEALTH_STATUS_OK for v in checks.values())
        else HEALTH_STATUS_DEGRADED
    )

    return {"status": overall, "checks": checks}
