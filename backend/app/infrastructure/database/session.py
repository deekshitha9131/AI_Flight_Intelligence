"""Async session factory and the FastAPI database dependency.

Distinct from engine.py: the engine owns the connection pool for the
whole process; this module owns *sessions* — the per-unit-of-work
object services and repositories actually talk to. `get_db_session` is
the concrete FastAPI dependency every router/service depends on
(re-exported through app/core/di_container.py as `DbSession`) — it
lives here, next to the sessionmaker it wraps, rather than in the DI
module itself, so the database layer is self-contained and testable
without importing anything FastAPI-specific except this one function.
"""

from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Build the session factory bound to the given engine.

    `expire_on_commit=False` because API responses commonly read
    attributes off an entity right after committing it (e.g. returning
    the just-approved draft) — without this, SQLAlchemy would trigger a
    fresh (and here, unwanted) DB round-trip to refresh those attributes
    immediately after commit.

    `autoflush=False` — flushes happen explicitly (on commit, or
    wherever a repository/service chooses to flush), not implicitly
    before every query. Implicit autoflush is a common source of
    surprising partial writes inside a multi-step unit of work; making
    it explicit keeps transaction boundaries exactly where the Unit of
    Work pattern says they should be (a later phase).
    """
    return async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        autoflush=False,
    )


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a request-scoped database session.

    The session factory itself is built once at startup and stored on
    `app.state.db_session_factory` (see app/main.py's lifespan); this
    function only opens one session per request against that shared
    factory and guarantees it's closed when the request finishes,
    success or failure.
    """
    session_factory = request.app.state.db_session_factory
    async with session_factory() as session:
        yield session
