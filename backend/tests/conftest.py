"""
conftest.py
-----------
Shared pytest fixtures for the entire test suite.

Session-scoped fixtures:
  - test_engine   : SQLAlchemy engine bound to TEST_DATABASE_URL.
  - tables        : Creates all schema tables once; drops them after the
                    session ends.

Function-scoped fixtures:
  - db_session    : Wraps every test in a SAVEPOINT (nested transaction).
                    The outer transaction is never committed, so every test
                    starts with a clean slate without recreating tables.
  - app           : FastAPI application with get_db overridden to use the
                    test session, ensuring the HTTP layer and assertions
                    share the same in-flight transaction.
  - client        : httpx AsyncClient bound to the overridden app.

Helper factories (also fixtures):
  - user_payload  : Returns a factory function that builds valid registration
                    request dicts, with optional field overrides.
  - registered_user : Registers a user via the API and returns the response
                    data dict.
  - auth_headers  : Logs in and returns {"Authorization": "Bearer <token>"}
                    ready to pass to any protected endpoint.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]

load_dotenv(BASE_DIR / ".env", override=True)

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.base import Base
from app.database.session import get_db
from app.main import app as fastapi_app

# ---------------------------------------------------------------------------
# Test database URL — must be set in the environment before running tests.
# Example: TEST_DATABASE_URL=postgresql://user:pass@localhost/ai_flight_test
# Falls back to DATABASE_URL with a "_test" suffix as a convenience default.
# ---------------------------------------------------------------------------
_TEST_DATABASE_URL: str = os.environ.get(
    "TEST_DATABASE_URL",
    os.environ.get("DATABASE_URL", ""),
)

if not _TEST_DATABASE_URL:
    raise RuntimeError(
        "Set TEST_DATABASE_URL before running tests. "
        "Example: TEST_DATABASE_URL=postgresql://user:pass@localhost/ai_flight_test"
    )


# ---------------------------------------------------------------------------
# Session-scoped engine & table creation
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def test_engine() -> Generator[Engine, None, None]:
    """Create a SQLAlchemy engine for the test database."""
    engine = create_engine(
        _TEST_DATABASE_URL,
        pool_pre_ping=True,
        future=True,
    )
    yield engine
    engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def tables(test_engine: Engine) -> Generator[None, None, None]:
    """Create all tables before the test session; drop them afterwards."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


# ---------------------------------------------------------------------------
# Per-test savepoint isolation
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_session(test_engine: Engine) -> Generator[Session, None, None]:
    """
    Yield a database session wrapped in a savepoint.

    Strategy:
      1. Open a connection and begin an outer transaction (never committed).
      2. Start a SAVEPOINT so the ORM session can issue its own BEGIN/COMMIT
         without actually committing to the database.
      3. After the test, roll back to the savepoint, then roll back the outer
         transaction — leaving the database in its original state.
    """
    connection = test_engine.connect()
    outer_transaction = connection.begin()

    TestingSessionLocal = sessionmaker(
        bind=connection,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )
    session = TestingSessionLocal()

    # Re-open the savepoint every time the session issues a COMMIT so that
    # the ORM's flush/commit cycle works normally inside the test.
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session: Session, transaction: Any) -> None:
        if transaction.nested and not transaction._parent.nested:
            session.begin_nested()

    session.begin_nested()  # initial SAVEPOINT

    yield session

    session.close()
    outer_transaction.rollback()
    connection.close()


# ---------------------------------------------------------------------------
# FastAPI app with injected test session
# ---------------------------------------------------------------------------


@pytest.fixture()
def app(db_session: Session):
    """Return the FastAPI app with get_db overridden to use the test session."""

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    yield fastapi_app
    fastapi_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Async HTTP client
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Yield an httpx AsyncClient wired to the test app."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Payload factory
# ---------------------------------------------------------------------------


@pytest.fixture()
def user_payload():
    """
    Return a factory that builds a valid registration payload dict.

    Usage:
        payload = user_payload()                        # defaults
        payload = user_payload(email="x@example.com")  # override any field
    """

    def _factory(**overrides: Any) -> dict[str, Any]:
        base: dict[str, Any] = {
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane.doe@example.com",
            "password": "Secure@123",
        }
        base.update(overrides)
        return base

    return _factory


# ---------------------------------------------------------------------------
# Registered user helper
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def registered_user(client: AsyncClient, user_payload) -> dict[str, Any]:
    """Register a default user and return the response data dict."""
    response = await client.post("/api/v1/auth/register", json=user_payload())
    assert response.status_code == 201, response.text
    return response.json()["data"]


@pytest_asyncio.fixture()
async def another_registered_user(
    client: AsyncClient,
    user_payload,
) -> dict[str, Any]:
    """
    Register a second user for cross-user isolation tests.
    """
    payload = user_payload(
        first_name="John",
        last_name="Smith",
        email="john.smith@example.com",
    )

    response = await client.post(
        "/api/v1/auth/register",
        json=payload,
    )

    assert response.status_code == 201, response.text
    return response.json()["data"]


# ---------------------------------------------------------------------------
# Auth headers helper
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def auth_headers(
    client: AsyncClient, user_payload, registered_user
) -> dict[str, str]:
    """
    Log in the default registered user and return bearer auth headers.

    Depends on `registered_user` to ensure the user exists first.
    """
    payload = user_payload()
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert response.status_code == 200, response.text
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
