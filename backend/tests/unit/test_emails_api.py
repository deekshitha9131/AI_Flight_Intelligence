"""Tests for app/presentation/api/v1/routers/emails.py.

Same dependency_overrides pattern as every other router test in this
suite — no live database, Redis, or Gmail involved. Exercises
EmailQueryParams' own Pydantic validation (page/page_size bounds)
purely through the HTTP layer, same as test_send_email_api.py does for
GmailSendRequest.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.di_container import get_current_user, get_email_service
from app.domain.entities.email import Email
from app.domain.entities.user import User
from app.domain.enums.user_status import UserStatus
from app.domain.exceptions.email import EmailNotFoundError


def _fake_current_user() -> User:
    return User(
        id=uuid4(),
        email="user@example.com",
        full_name="Test User",
        google_sub_id="sub-1",
        status=UserStatus.ACTIVE,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _email(*, user_id, email_id=None, **overrides) -> Email:
    defaults = dict(
        id=email_id or uuid4(),
        thread_id=uuid4(),
        user_id=user_id,
        gmail_message_id="m1",
        sender="sender@example.com",
        recipients=["user@example.com"],
        cc=[],
        bcc=[],
        subject="Subject",
        snippet="snippet",
        body_text="body",
        body_html=None,
        received_at=datetime.now(UTC),
        is_read=True,
        is_starred=False,
        has_attachments=False,
        label_ids=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return Email(**defaults)


class FakeEmailService:
    def __init__(self) -> None:
        self.items_to_return: list[Email] = []
        self.total_to_return = 0
        self.email_to_return: Email | None = None
        self.raise_on_get: Exception | None = None
        self.list_calls: list[dict] = []
        self.get_calls: list = []

    async def list_emails(self, user, **kwargs):
        self.list_calls.append(kwargs)
        return self.items_to_return, self.total_to_return

    async def get_email(self, user, email_id):
        self.get_calls.append(email_id)
        if self.raise_on_get is not None:
            raise self.raise_on_get
        return self.email_to_return


@pytest.fixture
def fake_email_service(app_no_lifespan: FastAPI) -> FakeEmailService:
    service = FakeEmailService()
    app_no_lifespan.dependency_overrides[get_email_service] = lambda: service
    app_no_lifespan.dependency_overrides[get_current_user] = _fake_current_user
    return service


def test_list_emails_returns_paginated_response(
    app_no_lifespan: FastAPI, unit_client: TestClient, fake_email_service: FakeEmailService
) -> None:
    user_id = uuid4()
    fake_email_service.items_to_return = [_email(user_id=user_id)]
    fake_email_service.total_to_return = 1

    response = unit_client.get("/api/v1/emails")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["total"] == 1
    assert "gmail_message_id" in body["items"][0]
    assert "body_text" not in body["items"][0]  # summary excludes body content


def test_list_emails_passes_query_params_through(
    app_no_lifespan: FastAPI, unit_client: TestClient, fake_email_service: FakeEmailService
) -> None:
    response = unit_client.get(
        "/api/v1/emails?page=2&page_size=5&unread=true&starred=true&has_attachments=false&sort=oldest"
    )

    assert response.status_code == 200
    call = fake_email_service.list_calls[0]
    assert call["page"] == 2
    assert call["page_size"] == 5
    assert call["sort"] == "oldest"
    assert call["is_read"] is False  # unread=true -> is_read=False
    assert call["is_starred"] is True
    assert call["has_attachments"] is False


def test_list_emails_omitted_filters_are_none(
    app_no_lifespan: FastAPI, unit_client: TestClient, fake_email_service: FakeEmailService
) -> None:
    response = unit_client.get("/api/v1/emails")

    assert response.status_code == 200
    call = fake_email_service.list_calls[0]
    assert call["is_read"] is None
    assert call["is_starred"] is None
    assert call["has_attachments"] is None


def test_list_emails_rejects_page_below_one(
    app_no_lifespan: FastAPI, unit_client: TestClient, fake_email_service: FakeEmailService
) -> None:
    response = unit_client.get("/api/v1/emails?page=0")

    assert response.status_code == 400


def test_list_emails_rejects_page_size_above_max(
    app_no_lifespan: FastAPI, unit_client: TestClient, fake_email_service: FakeEmailService
) -> None:
    response = unit_client.get("/api/v1/emails?page_size=101")

    assert response.status_code == 400


def test_list_emails_requires_authentication(app_no_lifespan: FastAPI, unit_client: TestClient) -> None:
    service = FakeEmailService()
    app_no_lifespan.dependency_overrides[get_email_service] = lambda: service

    response = unit_client.get("/api/v1/emails")

    assert response.status_code == 401


def test_get_email_returns_detail(
    app_no_lifespan: FastAPI, unit_client: TestClient, fake_email_service: FakeEmailService
) -> None:
    user_id = uuid4()
    email = _email(user_id=user_id, subject="Detail subject", body_text="Full body content")
    fake_email_service.email_to_return = email

    response = unit_client.get(f"/api/v1/emails/{email.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["subject"] == "Detail subject"
    assert body["body_text"] == "Full body content"
    assert "recipients" in body
    assert "attachments" in body
    assert fake_email_service.get_calls == [email.id]


def test_get_email_returns_404_for_missing_email(
    app_no_lifespan: FastAPI, unit_client: TestClient, fake_email_service: FakeEmailService
) -> None:
    fake_email_service.raise_on_get = EmailNotFoundError("No email found.")

    response = unit_client.get(f"/api/v1/emails/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "EMAIL_NOT_FOUND"


def test_get_email_returns_404_for_another_users_email(
    app_no_lifespan: FastAPI, unit_client: TestClient, fake_email_service: FakeEmailService
) -> None:
    """Same 404 as a genuinely missing email — the API layer has no way
    to distinguish the two cases, which is exactly the point."""
    fake_email_service.raise_on_get = EmailNotFoundError("No email found.")

    response = unit_client.get(f"/api/v1/emails/{uuid4()}")

    assert response.status_code == 404


def test_get_email_requires_authentication(app_no_lifespan: FastAPI, unit_client: TestClient) -> None:
    service = FakeEmailService()
    app_no_lifespan.dependency_overrides[get_email_service] = lambda: service

    response = unit_client.get(f"/api/v1/emails/{uuid4()}")

    assert response.status_code == 401


def test_get_email_rejects_non_uuid_path_param(
    app_no_lifespan: FastAPI, unit_client: TestClient, fake_email_service: FakeEmailService
) -> None:
    response = unit_client.get("/api/v1/emails/not-a-uuid")

    assert response.status_code == 400