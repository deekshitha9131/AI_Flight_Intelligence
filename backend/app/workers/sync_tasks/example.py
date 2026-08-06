"""Example background task.

Not part of the shipped feature set — this establishes and exercises
the pattern every real task on the `sync` queue (and, by the same
shape, every task on every other queue) will follow once Gmail sync
logic exists in a later implementation phase: a `@celery_app.task`
using `BaseTask`, opting into the shared retry defaults explicitly, and
bridging into async infrastructure via `self.run_async(...)`.

Kept deliberately small and side-effect-free (it only logs) so it's
safe to actually invoke against a running stack to verify the whole
pipeline — broker, worker, routing, retry, logging — end to end before
any real business logic exists to test it against.
"""

from typing import cast

import structlog

from app.core.celery_app import celery_app
from app.workers import worker_state
from app.workers.base import DEFAULT_TASK_RETRY_KWARGS, BaseTask

logger = structlog.get_logger(__name__)


async def _touch_redis(message: str) -> str:
    """A trivial async operation, standing in for real async I/O.

    Real sync tasks will do something like this shape: open a session
    from `worker_state.get_session_factory()`, call a repository/service
    method, commit. This function exists only to prove the async bridge
    actually reaches shared infrastructure, not just `asyncio.run` on
    its own.
    """
    client = worker_state.get_redis_client()
    key = "example_task:last_message"
    await client.set(key, message, ex=300)
    stored_value = await client.get(key)
    # We just set this key unconditionally above, so it is always
    # present — the cast (not a plain `assert is not None`) is
    # necessary because `get_redis_client()` returns a bare
    # `redis.Redis` (see app/infrastructure/cache/redis_client.py's
    # module docstring for why it can't be parameterized), which means
    # `.get()` returns `Any` per the stub, not `str | None`. Asserting
    # non-None narrows an Optional; it does nothing to Any, which mypy
    # already treats as compatible with everything.
    return cast(str, stored_value)


# Celery's task decorator is unstubbed, hence the ignore below.
@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.workers.sync_tasks.example_log_task",
    base=BaseTask,
    bind=True,
    **DEFAULT_TASK_RETRY_KWARGS,
)
def example_log_task(self: BaseTask, message: str) -> dict[str, str]:
    """Log a message, round-tripping it through Redis via the async bridge.

    Args:
        message: Arbitrary text to log and store. Exists purely to give
            the task an argument to pass, exercising Celery's argument
            serialization path (JSON, per celery_app.conf) alongside
            everything else.
    """
    logger.info("example_task_started", message=message, task_id=self.request.id)

    stored_value = self.run_async(_touch_redis(message))

    logger.info("example_task_completed", stored_value=stored_value, task_id=self.request.id)
    return {"status": "completed", "message": stored_value}
