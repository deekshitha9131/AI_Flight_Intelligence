"""Per-worker-process infrastructure resources.

FastAPI's application stores its engine, session factory, and Redis
client on `app.state`, built once in the lifespan startup (see
app/main.py). Celery worker processes have no equivalent object — each
worker is a separate OS process (Celery's default "prefork" pool forks
multiple child processes per container), so this module plays the same
role `app.state` plays for the API: build these resources exactly once
per process, and hand them out to tasks that need them.

Initialization happens via the `worker_process_init` Celery signal (see
app/core/celery_app.py), which fires once in each forked child process
after the fork completes — not in the parent process before forking,
which matters specifically for the async DB engine: an open
asyncpg connection forked across processes is not safe to share, so
resources must be created fresh in each child, never inherited from
the parent.
"""

import asyncio

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.infrastructure.cache.redis_client import close_redis_client, create_redis_client
from app.infrastructure.database.engine import create_db_engine, dispose_engine
from app.infrastructure.database.session import create_session_factory

# See app/infrastructure/cache/redis_client.py's module docstring for
# why every `redis.Redis` annotation below is bare (not `Redis[str]`)
# with an explicit `# type: ignore[type-arg]` — subscripting it is a
# real runtime TypeError with the installed redis-py version, not just
# a style choice.
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
_redis_client: redis.Redis | None = None  # type: ignore[type-arg]


def init_worker_resources(settings: Settings) -> None:
    """Build this process's engine, session factory, and Redis client.

    Called once per forked worker process via the `worker_process_init`
    signal. Safe to call at most once per process — calling it twice
    would leak the previously created engine's connection pool.
    """
    global _engine, _session_factory, _redis_client
    _engine = create_db_engine(settings)
    _session_factory = create_session_factory(_engine)
    _redis_client = create_redis_client(settings)


def dispose_worker_resources() -> None:
    """Release this process's engine and Redis client.

    Called once per worker process via the `worker_process_shutdown`
    signal. Wraps the async disposal calls in `asyncio.run` since Celery
    signal handlers themselves are synchronous.
    """

    async def _dispose() -> None:
        if _redis_client is not None:
            await close_redis_client(_redis_client)
        if _engine is not None:
            await dispose_engine(_engine)

    asyncio.run(_dispose())


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return this process's session factory.

    Raises rather than silently returning None if called before
    `init_worker_resources` has run — a task trying to use the database
    before the worker has finished starting up is a bug worth failing
    loudly on, not a case to paper over.
    """
    if _session_factory is None:
        raise RuntimeError(
            "Worker database resources are not initialized. This should "
            "only happen if a task runs before worker_process_init has "
            "completed, which indicates a startup-ordering bug."
        )
    return _session_factory


def get_redis_client() -> redis.Redis:  # type: ignore[type-arg]
    """Return this process's Redis client. See `get_session_factory` for the failure mode."""
    if _redis_client is None:
        raise RuntimeError(
            "Worker Redis resources are not initialized. This should only "
            "happen if a task runs before worker_process_init has "
            "completed, which indicates a startup-ordering bug."
        )
    return _redis_client
