"""Email request/response schemas.

The API contract boundary for the /emails/* endpoints. `EmailSummary`
(list items) and `EmailDetail` are deliberately two separate schemas,
not one schema with optional fields — a list response returning full
bodies for every row would be wasteful. `EmailSearchQueryParams`
(Task 4.3) mirrors `EmailQueryParams`' pagination fields exactly and
reuses `EmailListResponse` for its result shape, per the task's own
"reuse existing schemas" instruction — search is not a distinct
resource, just a differently-filtered read of the same inbox.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.infrastructure.database.repositories.email_repository import SortOrder


class EmailQueryParams(BaseModel):
    """Query parameters for GET /emails. A plain (non-request-body)
    model so FastAPI can validate each query param individually while
    still giving the router one typed object to work with, rather than
    five separate `Query(...)` parameters repeated at the call site."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort: SortOrder = Field(default="newest")
    unread: bool | None = Field(default=None)
    starred: bool | None = Field(default=None)
    has_attachments: bool | None = Field(default=None)


class EmailSearchQueryParams(BaseModel):
    """Query parameters for GET /emails/search.

    `q` deliberately has no `min_length` constraint here — an
    empty/whitespace-only query is a *business* rule ("a blank search
    isn't meaningful"), not a request-shape rule, so it's enforced by
    EmailService (raising InvalidSearchQueryError, mapped to 422) not
    by Pydantic (which would raise the less-informative generic
    VALIDATION_ERROR/400 for a shape violation instead).
    """

    q: str
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class AttachmentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    mime_type: str
    size: int


class EmailSummary(BaseModel):
    """One row in the inbox list — deliberately narrow, per Task 4.2's
    "do not return unnecessary database fields" instruction. Reused
    as-is for search results (Task 4.3)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    gmail_message_id: str
    thread_id: UUID
    sender: str
    subject: str | None
    snippet: str
    received_at: datetime
    is_read: bool
    is_starred: bool
    has_attachments: bool


class EmailListResponse(BaseModel):
    """Reused, unchanged, for both GET /emails and GET /emails/search —
    the two endpoints answer "here's a page of your emails," differing
    only in how that page was selected."""

    items: list[EmailSummary]
    page: int
    page_size: int
    total: int


class EmailDetail(BaseModel):
    """Full email detail — everything EmailSummary has, plus body
    content, full recipient lists, labels, and attachment metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    gmail_message_id: str
    thread_id: UUID
    sender: str
    recipients: list[str]
    cc: list[str]
    bcc: list[str]
    subject: str | None
    snippet: str
    body_text: str | None
    body_html: str | None
    received_at: datetime
    is_read: bool
    is_starred: bool
    has_attachments: bool
    label_ids: list[str]
    attachments: list[AttachmentSummary]
