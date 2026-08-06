"""Async SQLAlchemy engine construction.

The engine owns the connection pool — it is built exactly once per
process, at application startup (see app/main.py's lifespan), and
disposed exactly once at shutdown. Nothing in this module holds
module-level global state; `create_db_engine` is a pure function so a
test can build its own engine against a test database without touching
anything here.
"""

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import Settings


def create_db_engine(settings: Settings) -> AsyncEngine:
    """Build the async SQLAlchemy engine from settings.

    Pool configuration, explained:
    - `pool_size`: number of connections kept open and ready per
      process. Sized per-process, not per-cluster — with N horizontally
      scaled API replicas, actual total connections to Postgres is
      roughly N * (pool_size + max_overflow), which matters when
      setting Postgres's own `max_connections`.
    - `max_overflow`: additional connections allowed beyond pool_size
      under burst load, closed once no longer needed rather than kept
      warm.
    - `pool_timeout`: how long a request waits for a connection to
      free up before failing loudly — better than an unbounded wait
      that silently stalls a request.
    - `pool_recycle`: connections older than this (seconds) are
      discarded and replaced, guarding against a database or
      load-balancer silently dropping long-lived idle connections
      (a common failure mode with managed Postgres and cloud LBs).
    - `pool_pre_ping`: issues a lightweight "is this connection still
      alive" check before handing a pooled connection to a query —
      without it, the first query on a connection that died in the
      background fails outright instead of transparently reconnecting.
    """
    return create_async_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout,
        pool_recycle=settings.database_pool_recycle,
        pool_pre_ping=True,
        echo=settings.app_debug,
    )


async def dispose_engine(engine: AsyncEngine) -> None:
    """Cleanly close every pooled connection on application shutdown."""
    await engine.dispose()
