from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class EmailChunkRecord:
    id: UUID
    email_id: UUID
    thread_id: UUID
    user_id: UUID
    chunk_index: int
    content: str
    embedding: list[float]
    received_at: datetime
    created_at: datetime
    updated_at: datetime
