"""Worker health check.

The API's readiness endpoint (app/presentation/api/v1/routers/health.py)
answers "can the API reach its dependencies." This task answers the
equivalent question from a worker process's perspective — a worker can
be alive (the process is running, Celery's own liveness ping succeeds)
while still unable to reach Postgres or Redis, and that distinction
matters operationally the same way it does for the API.

Scheduled via `celery_app.conf.beat_schedule` (app/core/celery_app.py)
to run every 60 seconds. Its result is logged, not stored anywhere
queryable yet — a later phase may persist failures somewhere an ops
dashboard can alert on, but logging is a correct, complete starting
point on its own.
"""

import structlog
from sqlalchemy import text

from app.core.celery_app import celery_app
from app.workers import worker_state
from app.workers.base import DEFAULT_TASK_RETRY_KWARGS, BaseTask

logger = structlog.get_logger(__name__)


async def _check_database() -> bool:
    session_factory = worker_state.get_session_factory()
    async with session_factory() as session:
        await session.execute(text("SELECT 1"))
    return True


async def _check_redis() -> bool:
    client = worker_state.get_redis_client()
    return bool(await client.ping())


# Celery's task decorator is unstubbed, hence the ignore below.
@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.workers.health_tasks.check_worker_health",
    base=BaseTask,
    bind=True,
    **DEFAULT_TASK_RETRY_KWARGS,
)
def check_worker_health(self: BaseTask) -> dict[str, str]:
    """Check this worker process's connectivity to Postgres and Redis.

    Deliberately does not raise on a failed dependency check — a
    database or Redis outage is exactly the situation this task exists
    to *observe and log*, not to itself fail loudly over (that would
    just add "task failed" noise on top of an outage that's already
    visible elsewhere, e.g. the API's own readiness check).
    """
    db_status = "ok"
    redis_status = "ok"

    try:
        self.run_async(_check_database())
    except Exception as exc:  # noqa: BLE001 — deliberately broad, see docstring
        db_status = "error"
        logger.warning("worker_health_database_check_failed", error=str(exc))

    try:
        self.run_async(_check_redis())
    except Exception as exc:  # noqa: BLE001
        redis_status = "error"
        logger.warning("worker_health_redis_check_failed", error=str(exc))

    result = {"database": db_status, "redis": redis_status}
    logger.info("worker_health_check_complete", **result)
    return result
