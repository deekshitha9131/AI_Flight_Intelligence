"""Tests for app/main.py's liveness endpoint and
app/presentation/api/v1/routers/health.py's readiness endpoint.

All infra-free — every case here overrides the DB/Redis dependencies
with fakes (tests/utils.py), so this file never touches a real
Postgres or Redis connection and runs the same way on a laptop with
nothing running as it does in CI.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.constants import HEALTH_STATUS_DEGRADED, HEALTH_STATUS_OK
from tests.utils import FakeAsyncSession, FakeRedisClient, override_db_session, override_redis


def test_liveness_check_returns_ok(unit_client: TestClient) -> None:
    """The root /health endpoint must answer instantly with no dependency checks."""
    response = unit_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": HEALTH_STATUS_OK}


def test_readiness_check_when_all_healthy(
    app_no_lifespan: FastAPI, unit_client: TestClient
) -> None:
    override_db_session(app_no_lifespan, FakeAsyncSession())
    override_redis(app_no_lifespan, FakeRedisClient(ping_result=True))

    response = unit_client.get("/api/v1/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == HEALTH_STATUS_OK
    assert body["checks"]["database"] == HEALTH_STATUS_OK
    assert body["checks"]["redis"] == HEALTH_STATUS_OK


def test_readiness_check_when_database_unreachable(
    app_no_lifespan: FastAPI, unit_client: TestClient
) -> None:
    override_db_session(
        app_no_lifespan, FakeAsyncSession(raise_on_execute=ConnectionError("db down"))
    )
    override_redis(app_no_lifespan, FakeRedisClient(ping_result=True))

    response = unit_client.get("/api/v1/health/ready")

    # Readiness reports 200 even when degraded — the endpoint's job is
    # to describe the current state accurately, not to itself fail as
    # an HTTP error. An orchestrator reads the body to decide what to
    # do; a 5xx here would conflate "I answered your question" with
    # "the answer is bad news," which are different things.
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == HEALTH_STATUS_DEGRADED
    assert body["checks"]["database"] == HEALTH_STATUS_DEGRADED
    assert body["checks"]["redis"] == HEALTH_STATUS_OK


def test_readiness_check_when_redis_unreachable(
    app_no_lifespan: FastAPI, unit_client: TestClient
) -> None:
    override_db_session(app_no_lifespan, FakeAsyncSession())
    override_redis(app_no_lifespan, FakeRedisClient(ping_result=False))

    response = unit_client.get("/api/v1/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == HEALTH_STATUS_DEGRADED
    assert body["checks"]["database"] == HEALTH_STATUS_OK
    assert body["checks"]["redis"] == HEALTH_STATUS_DEGRADED


def test_readiness_check_when_both_unreachable(
    app_no_lifespan: FastAPI, unit_client: TestClient
) -> None:
    override_db_session(app_no_lifespan, FakeAsyncSession(raise_on_execute=TimeoutError()))
    override_redis(app_no_lifespan, FakeRedisClient(raise_on_ping=ConnectionError()))

    response = unit_client.get("/api/v1/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == HEALTH_STATUS_DEGRADED
    assert body["checks"] == {"database": HEALTH_STATUS_DEGRADED, "redis": HEALTH_STATUS_DEGRADED}
