from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Thread:
    id: UUID
    user_id: UUID
    gmail_thread_id: str
    subject: str | None
    snippet: str | None
    history_id: str | None
    created_at: datetime
    updated_at: datetime
