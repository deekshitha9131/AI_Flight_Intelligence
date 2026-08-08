"""Thread request/response schemas.

The API contract boundary for the /threads/* endpoints. `EmailDetail`
(app/presentation/api/v1/schemas/email.py, Task 4.2) is reused as-is
for the emails embedded in a thread's detail response — a slight
superset of Task 4.4's requested email field list (it also carries
`thread_id`, `label_ids`, and attachment metadata), which is harmless
extra data and avoids defining a near-duplicate schema, per this
phase's repeated "reuse existing schemas" instruction.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.infrastructure.database.repositories.email_repository import SortOrder
from app.presentation.api.v1.schemas.email import EmailDetail


class ThreadQueryParams(BaseModel):
    """Query parameters for GET /threads."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort: SortOrder = Field(default="newest")


class ThreadSummarySchema(BaseModel):
    """One row in the thread list — metadata plus email_count, never
    the emails themselves. Per Task 4.4's own instruction: "the list
    must not load full email bodies.\""""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    gmail_thread_id: str
    subject: str | None
    snippet: str | None
    updated_at: datetime
    email_count: int


class ThreadListResponse(BaseModel):
    items: list[ThreadSummarySchema]
    page: int
    page_size: int
    total: int


class ThreadDetailResponse(BaseModel):
    """Thread metadata plus every email in the thread, chronological
    order. Not constructed via `from_attributes` — the router builds
    this directly from ThreadService's (Thread, list[Email]) tuple
    return, since no single ORM/domain object naturally has an
    `emails` attribute to validate against."""

    id: UUID
    gmail_thread_id: str
    subject: str | None
    snippet: str | None
    created_at: datetime
    updated_at: datetime
    emails: list[EmailDetail]