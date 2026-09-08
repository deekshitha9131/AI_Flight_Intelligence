from collections.abc import Coroutine
from typing import Any, TypeVar

import structlog
from celery import Task

from app.core.config import get_settings
from app.workers import worker_state

logger = structlog.get_logger(__name__)

T = TypeVar("T")

_settings = get_settings()

DEFAULT_TASK_RETRY_KWARGS: dict[str, Any] = {
    "autoretry_for": (ConnectionError, TimeoutError, OSError),
    "retry_backoff": True,
    "retry_backoff_max": _settings.celery_retry_backoff_max,
    "retry_jitter": True,
    "max_retries": _settings.celery_max_retries,
}


class BaseTask(Task):  # type: ignore[misc]
    abstract = True

    def run_async(self, coro: Coroutine[Any, Any, T]) -> T:

        loop = worker_state.get_worker_loop()
        return loop.run_until_complete(coro)

    def on_success(self, retval: Any, task_id: str, args: Any, kwargs: Any) -> None:
        logger.info("task_succeeded", task_name=self.name, task_id=task_id)
        super().on_success(retval, task_id, args, kwargs)

    def on_retry(self, exc: Exception, task_id: str, args: Any, kwargs: Any, einfo: Any) -> None:
        logger.warning(
            "task_retrying",
            task_name=self.name,
            task_id=task_id,
            error=str(exc),
            error_type=type(exc).__name__,
        )
        super().on_retry(exc, task_id, args, kwargs, einfo)

    def on_failure(self, exc: Exception, task_id: str, args: Any, kwargs: Any, einfo: Any) -> None:
        logger.error(
            "task_failed",
            task_name=self.name,
            task_id=task_id,
            error=str(exc),
            error_type=type(exc).__name__,
        )
        super().on_failure(exc, task_id, args, kwargs, einfo)
