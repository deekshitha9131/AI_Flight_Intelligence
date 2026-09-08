from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.application.dto.thread import ThreadSummary
from app.core.di_container import get_current_user, get_thread_service
from app.domain.entities.email import Email
from app.domain.entities.thread import Thread
from app.domain.entities.user import User
from app.domain.enums.user_status import UserStatus
from app.domain.exceptions.base import DomainError
from app.domain.exceptions.thread import ThreadNotFoundError
from app.presentation.api.v1.routers.threads import router
from app.presentation.exception_handlers import domain_error_handler


def _fake_user() -> User:
    return User(
        id=uuid4(),
        email="user@example.com",
        full_name="Test User",
        google_sub_id="sub-1",
        status=UserStatus.ACTIVE,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _fake_thread(user_id: UUID) -> Thread:
    return Thread(
        id=uuid4(),
        user_id=user_id,
        gmail_thread_id="t1",
        subject="Thread Subject",
        snippet="Thread snippet",
        history_id="100",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _fake_email(user_id: UUID, thread_id: UUID) -> Email:
    return Email(
        id=uuid4(),
        thread_id=thread_id,
        user_id=user_id,
        gmail_message_id="m1",
        sender="sender@example.com",
        recipients=["user@example.com"],
        cc=[],
        bcc=[],
        subject="Thread Subject",
        snippet="Email snippet",
        body_text="Body text",
        body_html=None,
        received_at=datetime.now(UTC),
        is_read=True,
        is_starred=False,
        has_attachments=False,
        label_ids=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def client_and_mock_service():
    user = _fake_user()
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.add_exception_handler(DomainError, domain_error_handler)

    mock_service = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_thread_service] = lambda: mock_service

    client = TestClient(app)
    return client, mock_service, user


def test_list_threads_success(client_and_mock_service):
    client, mock_service, user = client_and_mock_service

    t1 = _fake_thread(user.id)
    summary = ThreadSummary(
        id=t1.id,
        gmail_thread_id=t1.gmail_thread_id,
        subject=t1.subject,
        snippet=t1.snippet,
        updated_at=t1.updated_at,
        email_count=2,
    )

    mock_service.list_threads.return_value = ([summary], 1)

    response = client.get("/api/v1/threads?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["email_count"] == 2


def test_get_thread_success(client_and_mock_service):
    client, mock_service, user = client_and_mock_service

    thread = _fake_thread(user.id)
    email = _fake_email(user.id, thread.id)

    mock_service.get_thread.return_value = (thread, [email])

    response = client.get(f"/api/v1/threads/{thread.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(thread.id)
    assert len(data["emails"]) == 1


def test_get_thread_not_found(client_and_mock_service):
    client, mock_service, user = client_and_mock_service

    mock_service.get_thread.side_effect = ThreadNotFoundError("Thread not found")

    thread_id = uuid4()
    response = client.get(f"/api/v1/threads/{thread_id}")
    assert response.status_code == 404
