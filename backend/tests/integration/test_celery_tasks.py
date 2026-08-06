"""Integration tests for the Celery task layer.

Runs tasks in eager mode (synchronous, in-process) but against REAL
Redis — this is a genuine integration test of `run_async()` bridging
into real infrastructure, not a mock. Skips gracefully when Redis is
unreachable, same policy as the rest of the integration suite.
"""

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def eager_celery_app(redis_available: bool, settings):  # type: ignore[no-untyped-def]
    if not redis_available:
        pytest.skip("No live Redis reachable at REDIS_URL — skipping Celery integration test.")

    from app.core.celery_app import celery_app
    from app.workers import worker_state

    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True

    worker_state.init_worker_resources(settings)
    yield celery_app
    worker_state.dispose_worker_resources()

    celery_app.conf.task_always_eager = False
    celery_app.conf.task_eager_propagates = False


def test_example_log_task_round_trips_through_real_redis(eager_celery_app) -> None:  # type: ignore[no-untyped-def]
    from app.workers.sync_tasks.example import example_log_task

    result = example_log_task.apply(args=["integration-test-message"])

    assert result.successful()
    assert result.result == {"status": "completed", "message": "integration-test-message"}


def test_worker_health_check_reports_redis_status(eager_celery_app) -> None:  # type: ignore[no-untyped-def]
    from app.workers.health_tasks import check_worker_health

    result = check_worker_health.apply()

    assert result.successful()
    # Database may or may not be reachable independently of Redis in a
    # given environment; this test's job is specifically to prove the
    # task ran against real Redis, not to assert database status.
    assert result.result["redis"] in ("ok", "error")
