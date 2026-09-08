"""Thread repository interface.

Protocol, same pattern as IUserRepository/IEmailRepository —
application-layer code depends on this, never on the concrete
infrastructure/database/repositories/thread_repository.py directly.
Phase 3 (Task 3.3) established `get_by_gmail_thread_id`/`upsert`, both
unchanged. Phase 4 (Task 4.4) adds the listing/detail surface the
/threads API reads through.
"""

from typing import Literal, Protocol
from uuid import UUID

from app.application.dto.thread import ThreadSummary
from app.domain.entities.email import Email
from app.domain.entities.thread import Thread

SortOrder = Literal["newest", "oldest"]


class IThreadRepository(Protocol):
    async def get_by_gmail_thread_id(
        self, user_id: UUID, gmail_thread_id: str
    ) -> Thread | None: ...

    async def upsert(
        self,
        *,
        user_id: UUID,
        gmail_thread_id: str,
        subject: str | None,
        snippet: str | None,
        history_id: str | None,
    ) -> Thread:
        """Create the thread if it doesn't exist for this user, or update
        its subject/snippet/history_id if it does. Never raises on a
        repeat call with the same (user_id, gmail_thread_id)."""
        ...

    async def get_by_id(self, thread_id: UUID, user_id: UUID) -> Thread | None:
        """Look up a thread by database ID, scoped to `user_id` in the
        query itself. Returns None both for "doesn't exist" and "exists
        but belongs to someone else" — the caller cannot and must not
        try to tell those apart."""
        ...

    async def list_by_user(
        self, user_id: UUID, *, page: int = 1, page_size: int = 25, sort: SortOrder = "newest"
    ) -> list[ThreadSummary]:
        """List a user's threads, paginated and sorted by recent
        activity (`updated_at`), each with its email_count computed in
        the same query."""
        ...

    async def count_by_user(self, user_id: UUID) -> int: ...

    async def get_thread_emails(self, thread_id: UUID, user_id: UUID) -> list[Email]:
        """Return every email in a thread, oldest first — the caller is
        responsible for having already verified ownership via
        `get_by_id`; `user_id` here is defense in depth, not the
        primary ownership check."""
        ...

    async def count_thread_emails(self, thread_id: UUID, user_id: UUID) -> int: ...
