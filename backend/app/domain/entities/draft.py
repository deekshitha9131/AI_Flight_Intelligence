from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.enums.draft_status import DraftStatus


@dataclass
class Draft:
    id: UUID
    email_id: UUID
    body: str
    status: DraftStatus
    created_at: datetime
    updated_at: datetime