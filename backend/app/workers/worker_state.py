import asyncio

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.infrastructure.cache.redis_client import close_redis_client, create_redis_client
from app.infrastructure.database.engine import create_db_engine, dispose_engine
from app.infrastructure.database.session import create_session_factory

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
_redis_client: redis.Redis | None = None  # type: ignore[type-arg]


def init_worker_resources(settings: Settings) -> None:
    global _engine, _session_factory, _redis_client
    _engine = create_db_engine(settings)
    _session_factory = create_session_factory(_engine)
    _redis_client = create_redis_client(settings)


async def dispose_worker_resources_async() -> None:
    """Release this process's engine and Redis client asynchronously."""

    global _engine, _session_factory, _redis_client

    if _redis_client is not None:
        await close_redis_client(_redis_client)
        _redis_client = None

    if _engine is not None:
        await dispose_engine(_engine)
        _engine = None

    _session_factory = None


def dispose_worker_resources() -> None:
    """Release worker resources from a synchronous Celery signal handler."""

    asyncio.run(dispose_worker_resources_async())


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
