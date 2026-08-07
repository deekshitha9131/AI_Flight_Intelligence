"""Email and Attachment domain entities. Zero framework dependency."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class Attachment:
    id: UUID
    email_id: UUID
    gmail_attachment_id: str
    filename: str
    mime_type: str
    size: int


@dataclass
class Email:
    id: UUID
    thread_id: UUID
    user_id: UUID
    gmail_message_id: str
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
    created_at: datetime
    updated_at: datetime
    attachments: list[Attachment] = field(default_factory=list)