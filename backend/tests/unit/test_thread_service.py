"""Tests for app/application/services/thread_service.py.

Fakes ThreadRepository entirely — pure orchestration/ownership test.
Real repository behavior (pagination, sorting, email_count computation,
SQL-level ownership scoping) is covered by
tests/integration/test_thread_repository.py.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.application.dto.thread import ThreadSummary
from app.application.services.thread_service import ThreadService
from app.domain.entities.email import Email
from app.domain.entities.thread import Thread
from app.domain.entities.user import User
from app.domain.enums.user_status import UserStatus
from app.domain.exceptions.thread import ThreadNotFoundError


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


def _thread(*, user_id, thread_id=None) -> Thread:
    return Thread(
        id=thread_id or uuid4(),
        user_id=user_id,
        gmail_thread_id="gmail-thread-1",
        subject="Subject",
        snippet="snippet",
        history_id=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _email(*, thread_id, user_id) -> Email:
    return Email(
        id=uuid4(),
        thread_id=thread_id,
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


class FakeThreadRepository:
    def __init__(self, *, threads: list[Thread] | None = None, emails_by_thread: dict | None = None) -> None:
        self._threads = {t.id: t for t in (threads or [])}
        self._emails_by_thread = emails_by_thread or {}
        self.list_by_user_calls: list[dict] = []
        self.get_by_id_calls: list[tuple] = []
        self.get_thread_emails_calls: list[tuple] = []

    async def get_by_id(self, thread_id, user_id):
        self.get_by_id_calls.append((thread_id, user_id))
        thread = self._threads.get(thread_id)
        if thread is None or thread.user_id != user_id:
            return None
        return thread

    async def list_by_user(self, user_id, **kwargs):
        self.list_by_user_calls.append({"user_id": user_id, **kwargs})
        return [
            ThreadSummary(
                id=t.id, gmail_thread_id=t.gmail_thread_id, subject=t.subject,
                snippet=t.snippet, updated_at=t.updated_at, email_count=0,
            )
            for t in self._threads.values() if t.user_id == user_id
        ]

    async def count_by_user(self, user_id):
        return len([t for t in self._threads.values() if t.user_id == user_id])

    async def get_thread_emails(self, thread_id, user_id):
        self.get_thread_emails_calls.append((thread_id, user_id))
        return self._emails_by_thread.get(thread_id, [])


async def test_list_threads_passes_params_through() -> None:
    user = _user()
    repo = FakeThreadRepository(threads=[_thread(user_id=user.id)])
    service = ThreadService(thread_repository=repo)

    await service.list_threads(user, page=2, page_size=10, sort="oldest")

    assert repo.list_by_user_calls[0] == {"user_id": user.id, "page": 2, "page_size": 10, "sort": "oldest"}


async def test_list_threads_returns_items_and_total() -> None:
    user = _user()
    repo = FakeThreadRepository(threads=[_thread(user_id=user.id), _thread(user_id=user.id)])
    service = ThreadService(thread_repository=repo)

    items, total = await service.list_threads(user, page=1, page_size=20, sort="newest")

    assert len(items) == 2
    assert total == 2


async def test_get_thread_returns_thread_and_emails() -> None:
    user = _user()
    thread = _thread(user_id=user.id)
    email = _email(thread_id=thread.id, user_id=user.id)
    repo = FakeThreadRepository(threads=[thread], emails_by_thread={thread.id: [email]})
    service = ThreadService(thread_repository=repo)

    result_thread, result_emails = await service.get_thread(user, thread.id)

    assert result_thread.id == thread.id
    assert result_emails == [email]


async def test_get_thread_raises_for_nonexistent_thread() -> None:
    user = _user()
    repo = FakeThreadRepository()
    service = ThreadService(thread_repository=repo)

    with pytest.raises(ThreadNotFoundError):
        await service.get_thread(user, uuid4())


async def test_get_thread_raises_for_another_users_thread() -> None:
    owner = _user()
    other_user = _user()
    thread = _thread(user_id=owner.id)
    repo = FakeThreadRepository(threads=[thread])
    service = ThreadService(thread_repository=repo)

    with pytest.raises(ThreadNotFoundError):
        await service.get_thread(other_user, thread.id)


async def test_get_thread_does_not_fetch_emails_when_ownership_check_fails() -> None:
    """Confirms the service short-circuits on ThreadNotFoundError rather
    than calling get_thread_emails first — no reason to query emails
    for a thread the caller was just denied access to."""
    other_user = _user()
    thread = _thread(user_id=_user().id)
    repo = FakeThreadRepository(threads=[thread])
    service = ThreadService(thread_repository=repo)

    with pytest.raises(ThreadNotFoundError):
        await service.get_thread(other_user, thread.id)

    assert repo.get_thread_emails_calls == []