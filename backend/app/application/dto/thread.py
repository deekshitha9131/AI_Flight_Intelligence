"""Thread DTOs.

`ThreadSummary` is the result shape of ThreadRepository.list_by_user —
each thread's own fields plus a per-thread `email_count` computed in
SQL via a correlated subquery, never counted in Python. Kept as a
dataclass here rather than folded into the domain entity
(app/domain/entities/thread.py), since `email_count` is a query-result
concern specific to the "list threads" use case, not an intrinsic
property of a Thread the way `subject` or `gmail_thread_id` are.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class ThreadSummary:
    id: UUID
    gmail_thread_id: str
    subject: str | None
    snippet: str | None
    updated_at: datetime
    email_count: int
