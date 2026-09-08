"""Tests for GmailService.send_email (app/application/services/gmail_service.py).

GmailClient is faked entirely — this tests orchestration only (does
GmailService resolve the connection correctly and map the response),
not MIME construction, which is already covered by test_gmail_send.py.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.application.services.gmail_service import GmailService
from app.core.config import Settings
from app.domain.entities.oauth_token import OAuthToken
from app.domain.entities.user import User
from app.domain.enums.user_status import UserStatus
from app.domain.exceptions.gmail import GmailAPIError, GmailNotConnectedError

BASE_ENV = {
    "APP_ENV": "development",
    "APP_DEBUG": "true",
    "APP_SECRET_KEY": "dev-secret",
    "DATABASE_URL": "postgresql+asyncpg://u:p@h:5432/d",
    "REDIS_URL": "redis://h:6379/0",
    "CELERY_BROKER_URL": "redis://h:6379/1",
    "CELERY_RESULT_BACKEND": "redis://h:6379/1",
    "TOKEN_ENCRYPTION_KEY": "test-token-encryption-key-value",
    "CORS_ORIGINS": "http://localhost:5173",
    "GOOGLE_CLIENT_ID": "test-client-id",
    "GOOGLE_CLIENT_SECRET": "test-client-secret",
}


def _settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    for key, value in BASE_ENV.items():
        monkeypatch.setenv(key, value)
    return Settings(_env_file=None)  # type: ignore[call-arg]


def _user() -> User:
    return User(
        id=uuid4(),
        email="user@example.com",
        full_name="Test User",
        google_sub_id="sub-1",
        status=UserStatus.ACTIVE,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _oauth_token(user_id) -> OAuthToken:
    return OAuthToken(
        user_id=user_id,
        access_token="fake-access-token",
        refresh_token="fake-refresh-token",
        token_expiry=datetime.now(UTC) + timedelta(hours=1),
        granted_scopes=["https://www.googleapis.com/auth/gmail.send"],
    )


class FakeGmailClient:
    def __init__(self) -> None:
        self.send_email_calls: list[dict] = []
        self.response_to_return = {"id": "sent-1", "threadId": "thread-1"}
        self.raise_on_send: Exception | None = None

    async def send_email(self, **kwargs):
        self.send_email_calls.append(kwargs)
        if self.raise_on_send is not None:
            raise self.raise_on_send
        return self.response_to_return


class FakeUserRepository:
    def __init__(self, *, oauth_token: OAuthToken | None) -> None:
        self._oauth_token = oauth_token

    async def get_oauth_tokens(self, user_id) -> OAuthToken | None:
        return self._oauth_token


def _make_service(
    monkeypatch: pytest.MonkeyPatch,
    *,
    gmail_client: FakeGmailClient,
    oauth_token: OAuthToken | None,
) -> GmailService:
    service = GmailService(
        user_repository=FakeUserRepository(oauth_token=oauth_token),
        thread_repository=None,  # not used by send_email
        email_repository=None,  # not used by send_email
        settings=_settings(monkeypatch),
    )
    monkeypatch.setattr(
        "app.application.services.gmail_service.GmailClient",
        lambda *, oauth_token, settings: gmail_client,
    )
    return service


async def test_send_email_success(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _user()
    gmail_client = FakeGmailClient()
    service = _make_service(
        monkeypatch, gmail_client=gmail_client, oauth_token=_oauth_token(user.id)
    )

    result = await service.send_email(
        user, to=["bob@example.com"], subject="Hi", body_text="Hello there."
    )

    assert result.success is True
    assert result.gmail_message_id == "sent-1"
    assert result.gmail_thread_id == "thread-1"
    assert gmail_client.send_email_calls[0]["to"] == ["bob@example.com"]
    assert gmail_client.send_email_calls[0]["thread_id"] is None


async def test_send_email_reply_passes_thread_id_through(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _user()
    gmail_client = FakeGmailClient()
    gmail_client.response_to_return = {"id": "sent-2", "threadId": "existing-thread"}
    service = _make_service(
        monkeypatch, gmail_client=gmail_client, oauth_token=_oauth_token(user.id)
    )

    result = await service.send_email(
        user,
        to=["bob@example.com"],
        subject="Re: Hi",
        body_text="Following up.",
        thread_id="existing-thread",
    )

    assert result.gmail_thread_id == "existing-thread"
    assert gmail_client.send_email_calls[0]["thread_id"] == "existing-thread"


async def test_send_email_raises_when_gmail_not_connected(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _user()
    gmail_client = FakeGmailClient()
    service = _make_service(monkeypatch, gmail_client=gmail_client, oauth_token=None)

    with pytest.raises(GmailNotConnectedError):
        await service.send_email(user, to=["bob@example.com"], subject="Hi", body_text="Hello.")

    assert gmail_client.send_email_calls == []


async def test_send_email_propagates_gmail_api_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _user()
    gmail_client = FakeGmailClient()
    gmail_client.raise_on_send = GmailAPIError("Gmail returned a 500.")
    service = _make_service(
        monkeypatch, gmail_client=gmail_client, oauth_token=_oauth_token(user.id)
    )

    with pytest.raises(GmailAPIError):
        await service.send_email(user, to=["bob@example.com"], subject="Hi", body_text="Hello.")


async def test_send_email_falls_back_to_requested_thread_id_if_response_omits_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Defensive case: if Gmail's response ever omitted threadId (it
    doesn't in practice, but this guards the fallback logic itself),
    the result should still report the thread_id the caller asked for."""
    user = _user()
    gmail_client = FakeGmailClient()
    gmail_client.response_to_return = {"id": "sent-3"}  # no threadId key
    service = _make_service(
        monkeypatch, gmail_client=gmail_client, oauth_token=_oauth_token(user.id)
    )

    result = await service.send_email(
        user,
        to=["bob@example.com"],
        subject="Re: Hi",
        body_text="Body.",
        thread_id="requested-thread",
    )

    assert result.gmail_thread_id == "requested-thread"
