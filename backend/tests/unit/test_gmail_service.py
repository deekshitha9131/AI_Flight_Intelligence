"""Tests for app/application/services/gmail_service.py.

Fakes every collaborator except EmailParser, which runs for real
against hand-built Gmail-shaped message dicts — this is what makes the
"parser failure" test exercise the actual GmailParseError path rather
than a mocked one, matching test_auth_service.py's philosophy of
faking the network boundary, not the logic under test.
"""

import base64
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


def _b64url(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")


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
        granted_scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )


def _raw_message(message_id: str, thread_id: str, *, valid: bool = True) -> dict:
    if not valid:
        # Missing "id" — EmailParser.parse_message raises GmailParseError.
        return {
            "threadId": thread_id,
            "internalDate": "1735689600000",
            "payload": {"mimeType": "text/plain", "headers": [], "body": {}},
        }
    return {
        "id": message_id,
        "threadId": thread_id,
        "snippet": "Hello there",
        "internalDate": "1735689600000",
        "labelIds": ["INBOX"],
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "Subject", "value": "Test subject"},
                {"name": "From", "value": "sender@example.com"},
                {"name": "To", "value": "user@example.com"},
            ],
            "body": {"data": _b64url("Hello there.")},
        },
    }


class FakeGmailClient:
    """Stands in for GmailClient — list_messages/get_message return
    fixtures the test controls directly, no real network or Google
    SDK call involved."""

    def __init__(self, *, pages: list[dict], messages_by_id: dict[str, dict]) -> None:
        self._pages = pages
        self._messages_by_id = messages_by_id
        self._page_index = 0
        self.list_calls: list[str | None] = []
        self.raise_on_list: Exception | None = None

    async def list_messages(self, *, query=None, label_ids=None, page_token=None, max_results=100):
        self.list_calls.append(page_token)
        if self.raise_on_list is not None:
            raise self.raise_on_list
        page = self._pages[self._page_index]
        self._page_index += 1
        return page

    async def get_message(self, message_id: str, *, format: str = "full"):
        return self._messages_by_id[message_id]


class FakeUserRepository:
    def __init__(self, *, oauth_token: OAuthToken | None) -> None:
        self._oauth_token = oauth_token

    async def get_oauth_tokens(self, user_id) -> OAuthToken | None:
        return self._oauth_token


class FakeThreadRepository:
    def __init__(self) -> None:
        self._threads: dict[tuple, object] = {}
        self.upsert_calls = 0

    async def get_by_gmail_thread_id(self, user_id, gmail_thread_id):
        return self._threads.get((user_id, gmail_thread_id))

    async def upsert(self, *, user_id, gmail_thread_id, subject, snippet, history_id):
        from app.domain.entities.thread import Thread

        self.upsert_calls += 1
        key = (user_id, gmail_thread_id)
        existing = self._threads.get(key)
        thread = Thread(
            id=existing.id if existing else uuid4(),
            user_id=user_id,
            gmail_thread_id=gmail_thread_id,
            subject=subject,
            snippet=snippet,
            history_id=history_id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self._threads[key] = thread
        return thread


class FakeEmailRepository:
    def __init__(self) -> None:
        self._emails: dict[tuple, object] = {}
        self.upsert_calls = 0

    async def get_by_gmail_message_id(self, user_id, gmail_message_id):
        return self._emails.get((user_id, gmail_message_id))

    async def upsert(self, *, thread_id, user_id, parsed):
        from app.domain.entities.email import Email

        self.upsert_calls += 1
        key = (user_id, parsed.gmail_message_id)
        was_created = key not in self._emails
        email = Email(
            id=uuid4(),
            thread_id=thread_id,
            user_id=user_id,
            gmail_message_id=parsed.gmail_message_id,
            sender=parsed.sender,
            recipients=parsed.recipients,
            cc=parsed.cc,
            bcc=parsed.bcc,
            subject=parsed.subject,
            snippet=parsed.snippet,
            body_text=parsed.body_text,
            body_html=parsed.body_html,
            received_at=parsed.internal_date,
            is_read=True,
            is_starred=False,
            has_attachments=parsed.has_attachments,
            label_ids=parsed.label_ids,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self._emails[key] = email
        return email, was_created


def _make_service(
    monkeypatch: pytest.MonkeyPatch,
    *,
    gmail_client: FakeGmailClient,
    oauth_token: OAuthToken | None,
    thread_repository: FakeThreadRepository | None = None,
    email_repository: FakeEmailRepository | None = None,
) -> tuple[GmailService, FakeThreadRepository, FakeEmailRepository]:
    thread_repository = thread_repository or FakeThreadRepository()
    email_repository = email_repository or FakeEmailRepository()
    service = GmailService(
        user_repository=FakeUserRepository(oauth_token=oauth_token),
        thread_repository=thread_repository,
        email_repository=email_repository,
        settings=_settings(monkeypatch),
    )
    monkeypatch.setattr(
        "app.application.services.gmail_service.GmailClient",
        lambda *, oauth_token, settings: gmail_client,
    )
    return service, thread_repository, email_repository


async def test_sync_mailbox_raises_when_gmail_not_connected(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _user()
    gmail_client = FakeGmailClient(pages=[], messages_by_id={})
    service, _, _ = _make_service(monkeypatch, gmail_client=gmail_client, oauth_token=None)

    with pytest.raises(GmailNotConnectedError):
        await service.sync_mailbox(user)


async def test_sync_mailbox_success(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _user()
    messages_by_id = {
        "m1": _raw_message("m1", "t1"),
        "m2": _raw_message("m2", "t1"),
    }
    pages = [
        {"messages": [{"id": "m1", "threadId": "t1"}, {"id": "m2", "threadId": "t1"}]},
    ]
    gmail_client = FakeGmailClient(pages=pages, messages_by_id=messages_by_id)
    service, thread_repo, email_repo = _make_service(
        monkeypatch, gmail_client=gmail_client, oauth_token=_oauth_token(user.id)
    )

    summary = await service.sync_mailbox(user)

    assert summary.success is True
    assert summary.emails_synced == 2
    assert summary.threads_synced == 1  # both messages share thread t1
    assert summary.emails_skipped == 0
    assert summary.next_page_token is None
    assert email_repo.upsert_calls == 2


async def test_sync_mailbox_empty_mailbox(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _user()
    gmail_client = FakeGmailClient(pages=[{"messages": []}], messages_by_id={})
    service, _, email_repo = _make_service(
        monkeypatch, gmail_client=gmail_client, oauth_token=_oauth_token(user.id)
    )

    summary = await service.sync_mailbox(user)

    assert summary.success is True
    assert summary.threads_synced == 0
    assert summary.emails_synced == 0
    assert summary.next_page_token is None
    assert email_repo.upsert_calls == 0


async def test_sync_mailbox_twice_does_not_duplicate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Running sync twice against the same fake repositories must not
    grow the underlying store beyond one row per message — this is the
    unit-level analogue of the integration-level unique-constraint
    guarantee the migration enforces."""
    user = _user()
    messages_by_id = {"m1": _raw_message("m1", "t1")}
    pages_first = [{"messages": [{"id": "m1", "threadId": "t1"}]}]
    gmail_client_1 = FakeGmailClient(pages=pages_first, messages_by_id=messages_by_id)
    thread_repo = FakeThreadRepository()
    email_repo = FakeEmailRepository()

    service_1, _, _ = _make_service(
        monkeypatch,
        gmail_client=gmail_client_1,
        oauth_token=_oauth_token(user.id),
        thread_repository=thread_repo,
        email_repository=email_repo,
    )
    first_summary = await service_1.sync_mailbox(user)

    pages_second = [{"messages": [{"id": "m1", "threadId": "t1"}]}]
    gmail_client_2 = FakeGmailClient(pages=pages_second, messages_by_id=messages_by_id)
    service_2, _, _ = _make_service(
        monkeypatch,
        gmail_client=gmail_client_2,
        oauth_token=_oauth_token(user.id),
        thread_repository=thread_repo,
        email_repository=email_repo,
    )
    second_summary = await service_2.sync_mailbox(user)

    assert first_summary.emails_synced == 1
    assert second_summary.emails_synced == 1
    # Same underlying stores across both runs — exactly one thread and
    # one email row exist, not two.
    assert len(thread_repo._threads) == 1
    assert len(email_repo._emails) == 1


async def test_sync_mailbox_propagates_gmail_api_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _user()
    gmail_client = FakeGmailClient(pages=[{"messages": []}], messages_by_id={})
    gmail_client.raise_on_list = GmailAPIError("Gmail returned a 500.")
    service, _, _ = _make_service(
        monkeypatch, gmail_client=gmail_client, oauth_token=_oauth_token(user.id)
    )

    with pytest.raises(GmailAPIError):
        await service.sync_mailbox(user)


async def test_sync_mailbox_skips_unparseable_message_without_failing_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _user()
    messages_by_id = {
        "bad": _raw_message("bad", "t1", valid=False),
        "good": _raw_message("good", "t1"),
    }
    pages = [{"messages": [{"id": "bad", "threadId": "t1"}, {"id": "good", "threadId": "t1"}]}]
    gmail_client = FakeGmailClient(pages=pages, messages_by_id=messages_by_id)
    service, _, email_repo = _make_service(
        monkeypatch, gmail_client=gmail_client, oauth_token=_oauth_token(user.id)
    )

    summary = await service.sync_mailbox(user)

    assert summary.emails_skipped == 1
    assert summary.emails_synced == 1
    assert email_repo.upsert_calls == 1


async def test_sync_mailbox_resumes_with_page_token(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _user()
    messages_by_id = {"m1": _raw_message("m1", "t1")}
    pages = [{"messages": [{"id": "m1", "threadId": "t1"}], "nextPageToken": "page-2"}]
    gmail_client = FakeGmailClient(pages=pages, messages_by_id=messages_by_id)
    service, _, _ = _make_service(
        monkeypatch, gmail_client=gmail_client, oauth_token=_oauth_token(user.id)
    )

    summary = await service.sync_mailbox(user, page_token="page-1")

    assert gmail_client.list_calls == ["page-1"]
    assert summary.next_page_token == "page-2"