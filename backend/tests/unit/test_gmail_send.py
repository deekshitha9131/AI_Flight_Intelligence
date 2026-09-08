"""Tests for GmailClient.send_email (app/infrastructure/gmail/client.py).

Mocks googleapiclient's `build()` entirely, same philosophy as
test_gmail_client.py — no live Gmail API call is ever made. These
tests additionally decode the Base64URL `raw` payload actually sent to
Gmail, to verify the MIME message itself (headers, body parts) is
built correctly, not just that `send` was called.
"""

import base64
from datetime import UTC, datetime, timedelta
from email import message_from_bytes
from unittest.mock import MagicMock, patch
from uuid import uuid4

import httplib2
import pytest
from googleapiclient.errors import HttpError

from app.core.config import Settings
from app.domain.entities.oauth_token import OAuthToken
from app.domain.exceptions.gmail import GmailAPIError
from app.infrastructure.gmail.client import GmailClient

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


def _oauth_token() -> OAuthToken:
    return OAuthToken(
        user_id=uuid4(),
        access_token="fake-access-token",
        refresh_token="fake-refresh-token",
        token_expiry=datetime.now(UTC) + timedelta(hours=1),
        granted_scopes=["https://www.googleapis.com/auth/gmail.send"],
    )


def _client(monkeypatch: pytest.MonkeyPatch) -> GmailClient:
    return GmailClient(oauth_token=_oauth_token(), settings=_settings(monkeypatch))


def _http_error(status: int) -> HttpError:
    return HttpError(httplib2.Response({"status": status}), b'{"error": "mocked"}')


def _decode_sent_raw(call_kwargs: dict) -> bytes:
    """Decode the Base64URL `raw` field from a captured `.send(...)` call
    back into the underlying MIME bytes, so tests can assert on the
    actual message content Gmail would have received."""
    raw = call_kwargs["body"]["raw"]
    padding_needed = -len(raw) % 4
    return base64.urlsafe_b64decode(raw + "=" * padding_needed)


@patch("app.infrastructure.gmail.client.build")
async def test_send_new_message_with_both_bodies(
    mock_build: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_service = MagicMock()
    mock_service.users.return_value.messages.return_value.send.return_value.execute.return_value = {
        "id": "sent-1",
        "threadId": "new-thread-1",
    }
    mock_build.return_value = mock_service

    client = _client(monkeypatch)
    result = await client.send_email(
        to=["bob@example.com"],
        cc=["carol@example.com"],
        bcc=["dave@example.com"],
        subject="Project Update",
        body_text="Hello, plain version.",
        body_html="<p>Hello, HTML version.</p>",
    )

    assert result["id"] == "sent-1"
    assert result["threadId"] == "new-thread-1"

    send_call = mock_service.users.return_value.messages.return_value.send
    call_kwargs = send_call.call_args.kwargs
    assert call_kwargs["userId"] == "me"
    assert "threadId" not in call_kwargs["body"]  # no thread_id passed -> new conversation

    mime_bytes = _decode_sent_raw(call_kwargs)
    message = message_from_bytes(mime_bytes)

    assert message["To"] == "bob@example.com"
    assert message["Cc"] == "carol@example.com"
    assert message["Bcc"] == "dave@example.com"
    assert message["Subject"] == "Project Update"
    assert message.is_multipart() is True

    parts = {
        part.get_content_type(): part.get_payload(decode=True).decode("utf-8")
        for part in message.walk()
        if not part.is_multipart()
    }
    assert "Hello, plain version." in parts["text/plain"]
    assert "<p>Hello, HTML version.</p>" in parts["text/html"]


@patch("app.infrastructure.gmail.client.build")
async def test_send_reply_includes_thread_id(
    mock_build: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_service = MagicMock()
    mock_service.users.return_value.messages.return_value.send.return_value.execute.return_value = {
        "id": "sent-2",
        "threadId": "existing-thread-1",
    }
    mock_build.return_value = mock_service

    client = _client(monkeypatch)
    result = await client.send_email(
        to=["bob@example.com"],
        subject="Re: Project Update",
        body_text="Sounds good.",
        thread_id="existing-thread-1",
    )

    assert result["threadId"] == "existing-thread-1"
    call_kwargs = mock_service.users.return_value.messages.return_value.send.call_args.kwargs
    assert call_kwargs["body"]["threadId"] == "existing-thread-1"


@patch("app.infrastructure.gmail.client.build")
async def test_send_plain_text_only_produces_single_part_message(
    mock_build: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_service = MagicMock()
    mock_service.users.return_value.messages.return_value.send.return_value.execute.return_value = {
        "id": "sent-3",
        "threadId": "t3",
    }
    mock_build.return_value = mock_service

    client = _client(monkeypatch)
    await client.send_email(
        to=["bob@example.com"], subject="Plain only", body_text="Just plain text."
    )

    call_kwargs = mock_service.users.return_value.messages.return_value.send.call_args.kwargs
    mime_bytes = _decode_sent_raw(call_kwargs)
    message = message_from_bytes(mime_bytes)

    assert message.is_multipart() is False
    assert message.get_content_type() == "text/plain"
    assert "Just plain text." in message.get_payload(decode=True).decode("utf-8")


@patch("app.infrastructure.gmail.client.build")
async def test_send_html_only_produces_single_part_message(
    mock_build: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_service = MagicMock()
    mock_service.users.return_value.messages.return_value.send.return_value.execute.return_value = {
        "id": "sent-4",
        "threadId": "t4",
    }
    mock_build.return_value = mock_service

    client = _client(monkeypatch)
    await client.send_email(
        to=["bob@example.com"], subject="HTML only", body_html="<p>Just HTML.</p>"
    )

    call_kwargs = mock_service.users.return_value.messages.return_value.send.call_args.kwargs
    mime_bytes = _decode_sent_raw(call_kwargs)
    message = message_from_bytes(mime_bytes)

    assert message.is_multipart() is False
    assert message.get_content_type() == "text/html"
    assert "<p>Just HTML.</p>" in message.get_payload(decode=True).decode("utf-8")


@patch("app.infrastructure.gmail.client.build")
async def test_send_without_cc_or_bcc_omits_those_headers(
    mock_build: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_service = MagicMock()
    mock_service.users.return_value.messages.return_value.send.return_value.execute.return_value = {
        "id": "sent-5",
        "threadId": "t5",
    }
    mock_build.return_value = mock_service

    client = _client(monkeypatch)
    await client.send_email(to=["bob@example.com"], subject="No cc/bcc", body_text="Body.")

    call_kwargs = mock_service.users.return_value.messages.return_value.send.call_args.kwargs
    mime_bytes = _decode_sent_raw(call_kwargs)
    message = message_from_bytes(mime_bytes)

    assert message["Cc"] is None
    assert message["Bcc"] is None


@patch("app.infrastructure.gmail.client.build")
async def test_send_raises_gmail_api_error_on_gmail_failure(
    mock_build: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_service = MagicMock()
    mock_service.users.return_value.messages.return_value.send.return_value.execute.side_effect = (
        _http_error(500)
    )
    mock_build.return_value = mock_service

    client = _client(monkeypatch)
    with pytest.raises(GmailAPIError):
        await client.send_email(to=["bob@example.com"], subject="Will fail", body_text="Body.")
