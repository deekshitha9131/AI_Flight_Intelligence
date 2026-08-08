import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
async def eager_celery_app(redis_available: bool, settings):  # type: ignore[no-untyped-def]
    if not redis_available:
        pytest.skip("No live Redis reachable at REDIS_URL — skipping Celery integration test.")

    from app.core.celery_app import celery_app
    from app.workers import worker_state

    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True

    worker_state.init_worker_resources(settings)

    try:
        yield celery_app
    finally:
        await worker_state.dispose_worker_resources_async()

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
    assert result.result["redis"] in ("ok", "error")
