"""Thread domain entity. Zero framework dependency, same rule as
app/domain/entities/user.py — no SQLAlchemy import here.
"""

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
    