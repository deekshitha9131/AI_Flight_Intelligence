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
    
    task_track_started=True,
    task_time_limit=settings.celery_task_time_limit,
    task_soft_time_limit=settings.celery_task_soft_time_limit,
    
    task_acks_late=True,
    task_reject_on_worker_lost=True,
   
    worker_prefetch_multiplier=1,
   
    result_expires=3600,
)


celery_app.conf.task_routes = {
    "app.workers.sync_tasks.*": {"queue": "sync"},
    "app.workers.classification_tasks.*": {"queue": "classification"},
    "app.workers.ai_tasks.*": {"queue": "ai_orchestration"},
    "app.workers.send_tasks.*": {"queue": "send"},
    "app.workers.notification_tasks.*": {"queue": "notifications"},
   
    "app.workers.health_tasks.*": {"queue": "notifications"},
}


celery_app.conf.beat_schedule = {
    "worker-health-check": {
        "task": "app.workers.health_tasks.check_worker_health",
        "schedule": 60.0,  # seconds
    },
}


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
