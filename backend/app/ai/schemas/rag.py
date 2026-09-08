from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class EmailChunk:
    chunk_index: int
    content: str


@dataclass
class RetrievedChunk:
    email_id: UUID
    thread_id: UUID
    chunk_index: int
    content: str
    received_at: datetime
    similarity: float


@dataclass
class EmailContextSection:
    email_id: UUID
    thread_id: UUID
    received_at: datetime
    chunks: list[RetrievedChunk]
    text: str


@dataclass
class RAGContext:

    sections: list[EmailContextSection] = field(default_factory=list)
    text: str = ""

    @property
    def is_empty(self) -> bool:
        return len(self.sections) == 0
