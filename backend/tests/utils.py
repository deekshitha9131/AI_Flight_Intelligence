"""Testing utilities shared across the test suite.

Home for the fake infrastructure stubs `tests/unit/` tests use to
exercise endpoint logic without a live database or Redis, plus small
assertion helpers so every test checking the standard error envelope
(app/presentation/exception_handlers.py) does it the same way.
"""

from typing import Any

from fastapi import FastAPI
from httpx import Response

from app.core.di_container import get_redis
from app.infrastructure.database.session import get_db_session


class FakeAsyncSession:
    """Stands in for an AsyncSession in tests that only need to know
    whether a query succeeded or raised — never touches a real database.

    Configure failure by passing `raise_on_execute=SomeException()`;
    the readiness endpoint's `except Exception` catch (by design — a
    health check must never itself crash) is what a test like this
    verifies actually engages.
    """

    def __init__(self, raise_on_execute: Exception | None = None) -> None:
        self._raise_on_execute = raise_on_execute

    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        if self._raise_on_execute is not None:
            raise self._raise_on_execute
        return None


class FakeRedisClient:
    """Stands in for a redis.asyncio.Redis in tests that only need `.ping()`."""

    def __init__(self, ping_result: bool = True, raise_on_ping: Exception | None = None) -> None:
        self._ping_result = ping_result
        self._raise_on_ping = raise_on_ping

    async def ping(self) -> bool:
        if self._raise_on_ping is not None:
            raise self._raise_on_ping
        return self._ping_result


def override_db_session(app: FastAPI, session: FakeAsyncSession) -> None:
    """Override the app's DB session dependency with a fake for one test.

    `get_db_session` is a FastAPI dependency declared as an async
    generator (it `yield`s a session) — the override must match that
    shape, or FastAPI's dependency resolution will not treat it as
    equivalent.
    """

    async def _override():  # type: ignore[no-untyped-def]
        yield session

    app.dependency_overrides[get_db_session] = _override


def override_redis(app: FastAPI, client: FakeRedisClient) -> None:
    """Override the app's Redis dependency with a fake for one test."""
    app.dependency_overrides[get_redis] = lambda: client


def assert_error_envelope(response: Response, *, status_code: int, code: str) -> dict:
    """Assert a response matches the standard error envelope shape and
    return the parsed body, so a test can make additional assertions
    (e.g. on `error.message`) without re-parsing.
    """
    assert (
        response.status_code == status_code
    ), f"Expected status {status_code}, got {response.status_code}: {response.text}"
    body = response.json()
    assert "error" in body, f"Response missing 'error' envelope: {body}"
    assert body["error"]["code"] == code, f"Expected code {code!r}, got {body['error']['code']!r}"
    assert "request_id" in body["error"], "Error envelope missing request_id"
    assert "message" in body["error"], "Error envelope missing message"
    return body
