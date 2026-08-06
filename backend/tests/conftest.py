"""Shared pytest fixtures.

Two distinct testing strategies live side by side here, matching the
two test directories:

- `tests/unit/` — fast, no live infrastructure required. Uses
  `unit_client`, which builds the real FastAPI app but overrides its
  DB/Redis dependencies with in-memory fakes (see tests/utils.py) via
  `app.dependency_overrides`. Crucially, this never triggers the
  app's lifespan (no `with TestClient(app) as client:`), so it never
  attempts a real Postgres/Redis connection at all — only whichever
  specific dependency a given test overrides is ever touched.

- `tests/integration/` — real Postgres/Redis required. Uses
  `integration_client` and `db_engine`, which run the actual lifespan
  and connect to whatever `DATABASE_URL`/`REDIS_URL` the environment
  provides. These skip gracefully (not fail) when no live database is
  reachable, since that's the honest, correct behavior outside CI/
  `docker compose` — a missing dependency in a sandboxed environment is
  not the same thing as a bug.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator

import pytest
import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import Settings, get_settings
from app.infrastructure.database.engine import create_db_engine, dispose_engine
from app.main import create_app


@pytest.fixture(scope="session")
def settings() -> Settings:
    """The application's real settings, sourced the same way the app itself sources them."""
    return get_settings()


# ---------------------------------------------------------------------------
# Unit fixtures — no live infrastructure
# ---------------------------------------------------------------------------


@pytest.fixture
def app_no_lifespan() -> FastAPI:
    """A fresh FastAPI app instance, per test, with its lifespan never entered.

    Function-scoped (not session-scoped) specifically so
    `app.dependency_overrides` set by one test can never leak into
    another — each test gets a clean app and clears its own overrides
    implicitly by simply not reusing the instance.
    """
    return create_app()


@pytest.fixture
def unit_client(app_no_lifespan: FastAPI) -> Generator[TestClient, None, None]:
    """A TestClient whose app never runs startup/shutdown.

    Deliberately NOT used as a context manager (`with TestClient(app)`)
    — entering that context is what triggers lifespan, which would try
    to open a real database connection. Any route this client calls
    must have its infrastructure-touching dependencies overridden by
    the test itself (see tests/utils.py's override helpers), or it will
    fail with an AttributeError on `request.app.state`, which is the
    correct failure mode: it means the test forgot to override a
    dependency it depends on, not a bug in this fixture.

    `raise_server_exceptions=False` is required, not optional: by
    default TestClient re-raises an unhandled exception in the test
    process itself (for debugging convenience), which bypasses the
    app's own exception handlers entirely — exactly the thing several
    tests in this suite exist to verify actually runs.
    """
    client = TestClient(app_no_lifespan, raise_server_exceptions=False)
    yield client
    app_no_lifespan.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Integration fixtures — real Postgres / Redis, skip gracefully if absent
# ---------------------------------------------------------------------------


async def _postgres_reachable(settings: Settings) -> bool:
    engine = create_db_engine(settings)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001 — reachability probe, any failure means "not reachable"
        return False
    finally:
        await dispose_engine(engine)


async def _redis_reachable(settings: Settings) -> bool:
    client = redis.from_url(settings.redis_url, socket_connect_timeout=2)
    try:
        return bool(await client.ping())
    except Exception:  # noqa: BLE001
        return False
    finally:
        await client.aclose()


@pytest.fixture(scope="session")
def db_available(settings: Settings) -> bool:
    """True if a real Postgres instance is reachable at settings.database_url.

    Session-scoped — the reachability check runs once per test session,
    not once per test, since it's the same answer every time within a
    single run and a network round-trip per test would be wasteful.
    """
    return asyncio.run(_postgres_reachable(settings))


@pytest.fixture(scope="session")
def redis_available(settings: Settings) -> bool:
    """True if a real Redis instance is reachable at settings.redis_url."""
    return asyncio.run(_redis_reachable(settings))


@pytest.fixture
async def db_engine(settings: Settings, db_available: bool) -> AsyncGenerator[AsyncEngine, None]:
    """A real database engine, for integration tests. Skips if unreachable."""
    if not db_available:
        pytest.skip("No live Postgres reachable at DATABASE_URL — skipping integration test.")
    engine = create_db_engine(settings)
    yield engine
    await dispose_engine(engine)


@pytest.fixture
def integration_client(
    app_no_lifespan: FastAPI, db_available: bool, redis_available: bool
) -> Generator[TestClient, None, None]:
    """A TestClient that runs the real lifespan against real Postgres/Redis.

    Skips (not fails) when either dependency is unreachable — this is
    the fixture integration tests use when they want to exercise the
    application exactly as it runs in docker-compose, including the
    pgvector extension bootstrap in app/main.py's lifespan.
    """
    if not db_available:
        pytest.skip("No live Postgres reachable at DATABASE_URL — skipping integration test.")
    if not redis_available:
        pytest.skip("No live Redis reachable at REDIS_URL — skipping integration test.")

    with TestClient(app_no_lifespan) as client:
        yield client
