"""User domain entity.

Deliberately separate from the SQLAlchemy model in
app/infrastructure/database/models/user.py — per this project's own
Clean Architecture rules (established in the frozen engineering
blueprint), a repository never returns a raw ORM model past the
infrastructure boundary; it maps to a domain entity. This class has
zero framework dependency: no SQLAlchemy import, no Pydantic import,
nothing that ties it to how a User happens to be persisted or
serialized. That's what makes it unit-testable with no database and no
FastAPI app involved at all (see tests/unit/test_user_entity.py).
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.enums.user_status import UserStatus
from app.domain.exceptions.base import BusinessValidationError


@dataclass
class User:
    id: UUID
    email: str
    full_name: str
    google_sub_id: str
    status: UserStatus
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE and not self.is_deleted

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def activate(self) -> None:
        """Mark the user active.

        Raises if the user is soft-deleted — a deleted account has no
        meaningful "active" state to transition into; reactivating one
        would be masking a deletion rather than reversing a status
        change, and those are different operations that shouldn't share
        a method.
        """
        if self.is_deleted:
            raise BusinessValidationError(
                "Cannot activate a deleted user.", code="CANNOT_ACTIVATE_DELETED_USER"
            )
        self.status = UserStatus.ACTIVE

    def deactivate(self) -> None:
        """Mark the user inactive. Idempotent — deactivating an already-inactive
        user is a no-op, not an error; there's no meaningful illegal
        transition to guard against here, unlike activation."""
        self.status = UserStatus.INACTIVE
