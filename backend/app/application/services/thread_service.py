"""ThreadService.

Reads the locally stored thread/conversation view: a paginated list of
thread summaries (each with an email_count) and a single thread's full
detail (thread metadata + all its emails, chronological order). Per
Phase 4's two-repository split, this service works exclusively through
ThreadRepository — including for a thread's own emails, since
ThreadRepository.get_thread_emails is the method that owns that read
(see that method's own docstring for why it isn't routed through
EmailRepository instead).

Ownership enforcement lives entirely inside
ThreadRepository.get_by_id's SQL (scoped by user_id) — this service
never fetches a thread and checks `.user_id` in Python.
"""

from uuid import UUID

from app.application.dto.thread import ThreadSummary
from app.domain.entities.email import Email
from app.domain.entities.thread import Thread
from app.domain.entities.user import User
from app.domain.exceptions.thread import ThreadNotFoundError
from app.infrastructure.database.repositories.email_repository import SortOrder
from app.infrastructure.database.repositories.thread_repository import ThreadRepository


class ThreadService:
    def __init__(self, *, thread_repository: ThreadRepository) -> None:
        self._thread_repository = thread_repository

    async def list_threads(
        self, user: User, *, page: int, page_size: int, sort: SortOrder
    ) -> tuple[list[ThreadSummary], int]:
        """Return (page of thread summaries, total thread count) for the
        authenticated user."""
        items = await self._thread_repository.list_by_user(
            user.id, page=page, page_size=page_size, sort=sort
        )
        total = await self._thread_repository.count_by_user(user.id)
        return items, total

    async def get_thread(self, user: User, thread_id: UUID) -> tuple[Thread, list[Email]]:
        """Return (thread, its emails in chronological order), enforcing
        that the thread belongs to `user`.

        Raises ThreadNotFoundError (404) both when the thread genuinely
        doesn't exist and when it exists but belongs to someone else —
        the two cases are indistinguishable by design, per Task 4.4's
        explicit "do not leak existence" requirement.
        """
        thread = await self._thread_repository.get_by_id(thread_id, user.id)
        if thread is None:
            raise ThreadNotFoundError(f"No thread found with id {thread_id}.")

        emails = await self._thread_repository.get_thread_emails(thread_id, user.id)
        return thread, emails
