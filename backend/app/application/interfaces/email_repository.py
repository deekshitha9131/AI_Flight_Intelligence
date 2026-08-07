"""Email repository interface.

Owns both `emails` and `attachments` — attachments have no independent
existence from their parent email, same reasoning IUserRepository uses
for owning `oauth_tokens`.
"""

from typing import Protocol
from uuid import UUID

from app.application.dto.gmail import ParsedEmail
from app.domain.entities.email import Email


class IEmailRepository(Protocol):
    async def get_by_gmail_message_id(self, user_id: UUID, gmail_message_id: str) -> Email | None: ...

    async def upsert(
        self, *, thread_id: UUID, user_id: UUID, parsed: ParsedEmail
    ) -> tuple[Email, bool]:
        """Create the email (with its attachments) if it doesn't exist for
        this user, or replace its fields (and attachment set) if it
        does. Returns (entity, was_created) — `was_created` is False on
        a repeat sync of the same message, which is what makes running
        sync twice idempotent rather than duplicating rows."""
        ...