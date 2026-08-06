"""pgvector column type helper.

Per the frozen vector-store decision (PostgreSQL + pgvector, no separate
vector database), any model needing to store an embedding — future
`emails.embedding`, `memory_thread.embedding` — declares it using
`embedding_column()` from this module rather than importing
`pgvector.sqlalchemy.Vector` directly at every call site. Centralizing
it here means the embedding dimensionality is enforced consistently
(from `EMBEDDING_DIMENSIONS`, app/core/constants.py) and a future model
change to the embedding model only requires updating that one constant.
"""

from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import EMBEDDING_DIMENSIONS


def embedding_column(*, nullable: bool = True) -> Mapped[list[float] | None]:
    """Return a mapped pgvector column sized to the configured embedding model.

    Nullable by default — a row (e.g. a newly-ingested email) commonly
    exists before its embedding has been computed by the async
    embedding worker; the column is populated after the fact, not at
    insert time.
    """
    return mapped_column(Vector(EMBEDDING_DIMENSIONS), nullable=nullable)
