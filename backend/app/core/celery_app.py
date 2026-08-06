"""Celery application instance.

This is the object every worker container in docker-compose.yml points
at (`celery -A app.core.celery_app worker -Q <queue>`) and the object
`celery-beat` runs its scheduler against (`celery -A app.core.celery_app
beat`). One Celery app for the whole project; queue segmentation
happens through task routing, not through multiple Celery app instances.
"""

import structlog
from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown

from app.core.config import get_settings
from app.core.logging_config import configure_logging
from app.workers import worker_state

settings = get_settings()
logger = structlog.get_logger(__name__)

celery_app = Celery(
    "ai_email_assistant",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Surfaces a "started" state (not just pending/success/failure) —
    # useful for the notifications queue, where the frontend may want
    # to show "AI is drafting a reply" rather than a flat spinner.
    task_track_started=True,
    task_time_limit=settings.celery_task_time_limit,
    task_soft_time_limit=settings.celery_task_soft_time_limit,
    # Acknowledge a task only after it completes (success or failure),
    # not the moment it's received. Combined with
    # task_reject_on_worker_lost, this means a worker process that dies
    # mid-task (OOM kill, container restart) puts the task back on the
    # queue for another worker to pick up, rather than silently losing
    # it — critical for anything touching drafts/sends, acceptable
    # overhead everywhere else.
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # One task at a time per worker process before fetching the next.
    # The alternative (prefetching several) is a real problem
    # specifically on the ai_orchestration queue: prefetching would let
    # one worker process hold several expensive LLM-bound tasks
    # simultaneously in its buffer, defeating the queue's whole purpose
    # of bounding concurrent AI cost.
    worker_prefetch_multiplier=1,
    # Task results expire after an hour — results are consulted for a
    # task's immediate outcome (did the sync job succeed), not kept as
    # a long-term record. Long-term state belongs in Postgres
    # (agent_runs, send_log), not in Redis result backend entries.
    result_expires=3600,
)

# Task routing: every task's queue is determined by which module it's
# defined in, matching the segmented worker containers in
# docker-compose.yml. This is what guarantees a slow AI run can never
# starve sync processing — they are different queues, consumed by
# different worker processes, full stop.
celery_app.conf.task_routes = {
    "app.workers.sync_tasks.*": {"queue": "sync"},
    "app.workers.classification_tasks.*": {"queue": "classification"},
    "app.workers.ai_tasks.*": {"queue": "ai_orchestration"},
    "app.workers.send_tasks.*": {"queue": "send"},
    "app.workers.notification_tasks.*": {"queue": "notifications"},
    # Health/system tasks piggyback on the lightest existing queue
    # rather than justifying a sixth dedicated worker container for one
    # periodic check — consistent with the project's documented
    # avoid-over-engineering principle.
    "app.workers.health_tasks.*": {"queue": "notifications"},
}

# Beat schedule — periodic tasks. Empty beyond the health check today;
# later phases add the token-refresh sweep, memory refresh, and nightly
# analytics aggregation here, following the same pattern.
celery_app.conf.beat_schedule = {
    "worker-health-check": {
        "task": "app.workers.health_tasks.check_worker_health",
        "schedule": 60.0,  # seconds
    },
}

# Task discovery: each queue's task module is a package (sync_tasks/,
# classification_tasks/, etc.) potentially holding several task files
# over time — see app/core/task_discovery.py for why Celery's own
# autodiscover_tasks (which only imports a single file conventionally
# named `tasks.py` per package) doesn't fit that shape, and would
# silently miss anything not named exactly that.
from app.core.task_discovery import discover_tasks  # noqa: E402

discover_tasks(
    [
        "app.workers.sync_tasks",
        "app.workers.classification_tasks",
        "app.workers.ai_tasks",
        "app.workers.send_tasks",
        "app.workers.notification_tasks",
    ]
)
# health_tasks.py is a single top-level module, not a per-queue
# package, so it's imported directly — this is what actually registers
# `check_worker_health`, referenced in beat_schedule above.
from app.workers import health_tasks  # noqa: E402,F401


# Celery's signal decorators are unstubbed, hence the ignore below.
@worker_process_init.connect  # type: ignore[untyped-decorator]
def _on_worker_process_init(**kwargs: object) -> None:
    """Runs once in each forked worker process, before it accepts any task.

    Mirrors app/main.py's lifespan startup, but for Celery: each worker
    process needs its own logging configuration and its own database
    engine / Redis client (see app/workers/worker_state.py for why these
    can't be inherited from the parent process across a fork).
    """
    configure_logging()
    worker_state.init_worker_resources(settings)
    logger.info("celery_worker_process_ready", app_env=settings.app_env)


# Same stub gap as worker_process_init above.
@worker_process_shutdown.connect  # type: ignore[untyped-decorator]
def _on_worker_process_shutdown(**kwargs: object) -> None:
    """Runs once in each worker process as it shuts down."""
    worker_state.dispose_worker_resources()
    logger.info("celery_worker_process_shutdown")
