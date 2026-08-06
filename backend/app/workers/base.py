"""Base Celery task class and shared retry defaults.

Every task in the project subclasses `BaseTask` (via `base=BaseTask` on
the `@celery_app.task` decorator, not by inheriting a decorator itself —
Celery tasks are registered instances, not plain classes). It provides
three things every task needs and would otherwise reimplement:

1. Structured logging on failure/success/retry, in the same JSON schema
   the API uses (app/core/logging_config.py) — a task failure and an
   API error are both just "something went wrong," and should be
   equally easy to find in aggregated logs.
2. `run_async()` — bridges an async coroutine into Celery's synchronous
   task execution model. The project's infrastructure (DB sessions,
   Redis) is async throughout; Celery tasks are called synchronously.
3. `DEFAULT_TASK_RETRY_KWARGS` — the retry policy every task opts into
   explicitly via decorator kwargs (see app/workers/health_tasks.py and
   app/workers/sync_tasks/example.py for the pattern). Explicit
   decorator kwargs are used rather than relying on Celery picking up
   retry attributes from the base class automatically, which is
   version-sensitive and easy to get silently wrong — explicit is
   simply more reliable here.
"""

import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

import structlog
from celery import Task

from app.core.config import get_settings

logger = structlog.get_logger(__name__)

T = TypeVar("T")

_settings = get_settings()

# Every task that opts in spreads this into its decorator:
#   @celery_app.task(base=BaseTask, bind=True, **DEFAULT_TASK_RETRY_KWARGS)
#
# `autoretry_for` is deliberately narrow — only exception types that
# represent a TRANSIENT infrastructure failure (a dropped connection,
# a timeout) belong here. A domain exception (e.g. a future
# DraftAlreadySentError) represents a business-logic outcome that will
# be exactly as wrong on the fourth attempt as the first; retrying it
# only burns worker time and, on the AI orchestration queue, real LLM
# cost. Any task needing a different retry policy overrides these
# kwargs explicitly rather than silently inheriting a mismatched default.
DEFAULT_TASK_RETRY_KWARGS: dict[str, Any] = {
    "autoretry_for": (ConnectionError, TimeoutError, OSError),
    "retry_backoff": True,
    "retry_backoff_max": _settings.celery_retry_backoff_max,
    "retry_jitter": True,
    "max_retries": _settings.celery_max_retries,
}


class BaseTask(Task):  # type: ignore[misc]
    """Shared base class for every Celery task in the project.

    The `type: ignore[misc]` is required because Celery ships no type
    stubs — mypy sees `Task` itself as `Any`, which makes subclassing
    it technically untypeable. This is a known, accepted gap in
    Celery's ecosystem (not something specific to this project), and
    is scoped to exactly this one line rather than disabling checking
    for the whole file.
    """

    abstract = True

    def run_async(self, coro: Coroutine[Any, Any, T]) -> T:
        """Run an async coroutine to completion from inside a sync task body.

        Each call creates and tears down its own event loop via
        `asyncio.run`. Deliberately simple rather than maintaining one
        persistent loop per worker process: Celery's prefork pool runs
        one task at a time per process, so there's no concurrency to
        gain from a shared loop, and a fresh loop per task avoids an
        entire class of "loop already closed" / cross-task leaked-state
        bugs that a shared loop can introduce.
        """
        return asyncio.run(coro)

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
