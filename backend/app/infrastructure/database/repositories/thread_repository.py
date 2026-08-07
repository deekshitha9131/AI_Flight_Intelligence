"""Thread repository — concrete SQLAlchemy implementation.

Implements IThreadRepository. Same simplification note as
UserRepository: no Unit of Work yet, so this commits its own change
directly rather than leaving the transaction boundary to a caller.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.thread import Thread
from app.infrastructure.database.models.thread import ThreadModel


def _to_entity(model: ThreadModel) -> Thread:
    return Thread(
        id=model.id,
        user_id=model.user_id,
        gmail_thread_id=model.gmail_thread_id,
        subject=model.subject,
        snippet=model.snippet,
        history_id=model.history_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class ThreadRepository:
    """See IThreadRepository for the contract this class implements."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_gmail_thread_id(self, user_id: UUID, gmail_thread_id: str) -> Thread | None:
        stmt = select(ThreadModel).where(
            ThreadModel.user_id == user_id, ThreadModel.gmail_thread_id == gmail_thread_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model is not None else None

    async def upsert(
        self,
        *,
        user_id: UUID,
        gmail_thread_id: str,
        subject: str | None,
        snippet: str | None,
        history_id: str | None,
    ) -> Thread:
        stmt = select(ThreadModel).where(
            ThreadModel.user_id == user_id, ThreadModel.gmail_thread_id == gmail_thread_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            model = ThreadModel(
                user_id=user_id,
                gmail_thread_id=gmail_thread_id,
                subject=subject,
                snippet=snippet,
                history_id=history_id,
            )
            self._session.add(model)
        else:
            model.subject = subject
            model.snippet = snippet
            if history_id is not None:
                model.history_id = history_id

        await self._session.commit()
        await self._session.refresh(model)
        return _to_entity(model)