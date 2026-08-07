"""Thread repository interface.

Protocol, same pattern as IUserRepository — application-layer code
depends on this, never on the concrete
infrastructure/database/repositories/thread_repository.py directly.
"""

from typing import Protocol
from uuid import UUID

from app.domain.entities.thread import Thread


class IThreadRepository(Protocol):
    async def get_by_gmail_thread_id(self, user_id: UUID, gmail_thread_id: str) -> Thread | None: ...

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
        repeat call with the same (user_id, gmail_thread_id) — this is
        what makes running sync twice safe."""
        ...