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

        if self.is_deleted:
            raise BusinessValidationError(
                "Cannot activate a deleted user.", code="CANNOT_ACTIVATE_DELETED_USER"
            )
        self.status = UserStatus.ACTIVE

    def deactivate(self) -> None:

        self.status = UserStatus.INACTIVE
