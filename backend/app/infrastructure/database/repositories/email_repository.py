"""Email repository — concrete SQLAlchemy implementation.

Implements IEmailRepository. Owns `attachments` alongside `emails` —
see the interface's own docstring for why. Same simplification note as
UserRepository/ThreadRepository re: committing directly, no Unit of
Work yet.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dto.gmail import ParsedEmail
from app.domain.entities.email import Attachment, Email
from app.infrastructure.database.models.attachment import AttachmentModel
from app.infrastructure.database.models.email import EmailModel

# Gmail's own well-known label IDs for read/starred state — used to
# derive `is_read`/`is_starred` from the label list every parsed
# message already carries, rather than requiring a second Gmail call.
_UNREAD_LABEL = "UNREAD"
_STARRED_LABEL = "STARRED"


def _to_entity(model: EmailModel) -> Email:
    return Email(
        id=model.id,
        thread_id=model.thread_id,
        user_id=model.user_id,
        gmail_message_id=model.gmail_message_id,
        sender=model.sender,
        recipients=list(model.recipients),
        cc=list(model.cc),
        bcc=list(model.bcc),
        subject=model.subject,
        snippet=model.snippet,
        body_text=model.body_text,
        body_html=model.body_html,
        received_at=model.received_at,
        is_read=model.is_read,
        is_starred=model.is_starred,
        has_attachments=model.has_attachments,
        label_ids=list(model.label_ids),
        created_at=model.created_at,
        updated_at=model.updated_at,
        attachments=[
            Attachment(
                id=a.id,
                email_id=a.email_id,
                gmail_attachment_id=a.gmail_attachment_id,
                filename=a.filename,
                mime_type=a.mime_type,
                size=a.size,
            )
            for a in model.attachments
        ],
    )


class EmailRepository:
    """See IEmailRepository for the contract this class implements."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_gmail_message_id(self, user_id: UUID, gmail_message_id: str) -> Email | None:
        stmt = select(EmailModel).where(
            EmailModel.user_id == user_id, EmailModel.gmail_message_id == gmail_message_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model is not None else None

    async def upsert(
        self, *, thread_id: UUID, user_id: UUID, parsed: ParsedEmail
    ) -> tuple[Email, bool]:
        stmt = select(EmailModel).where(
            EmailModel.user_id == user_id, EmailModel.gmail_message_id == parsed.gmail_message_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        was_created = model is None

        is_read = _UNREAD_LABEL not in parsed.label_ids
        is_starred = _STARRED_LABEL in parsed.label_ids

        if model is None:
            model = EmailModel(
                thread_id=thread_id,
                user_id=user_id,
                gmail_message_id=parsed.gmail_message_id,
                sender=parsed.sender,
                recipients=parsed.recipients,
                cc=parsed.cc,
                bcc=parsed.bcc,
                subject=parsed.subject,
                snippet=parsed.snippet,
                body_text=parsed.body_text,
                body_html=parsed.body_html,
                received_at=parsed.internal_date,
                is_read=is_read,
                is_starred=is_starred,
                has_attachments=parsed.has_attachments,
                label_ids=parsed.label_ids,
            )
            self._session.add(model)
        else:
            model.sender = parsed.sender
            model.recipients = parsed.recipients
            model.cc = parsed.cc
            model.bcc = parsed.bcc
            model.subject = parsed.subject
            model.snippet = parsed.snippet
            model.body_text = parsed.body_text
            model.body_html = parsed.body_html
            model.is_read = is_read
            model.is_starred = is_starred
            model.has_attachments = parsed.has_attachments
            model.label_ids = parsed.label_ids
            # Replace the attachment set wholesale rather than diffing —
            # a re-synced message's attachments are re-derived from the
            # current Gmail payload every time, so stale rows from a
            # previous sync (e.g. one Gmail itself later edited) must
            # not linger. `cascade="all, delete-orphan"` on the ORM
            # relationship (see EmailModel) is what makes `.clear()`
            # actually delete the orphaned rows on flush/commit.
            model.attachments.clear()

        for attachment in parsed.attachments:
            model.attachments.append(
                AttachmentModel(
                    gmail_attachment_id=attachment.attachment_id,
                    filename=attachment.filename,
                    mime_type=attachment.mime_type,
                    size=attachment.size,
                )
            )

        await self._session.commit()
        await self._session.refresh(model, attribute_names=["attachments"])
        return _to_entity(model), was_created