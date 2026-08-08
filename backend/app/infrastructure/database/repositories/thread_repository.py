from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dto.thread import ThreadSummary
from app.domain.entities.email import Email
from app.domain.entities.thread import Thread
from app.infrastructure.database.models.email import EmailModel
from app.infrastructure.database.models.thread import ThreadModel
from app.infrastructure.database.repositories.email_repository import SortOrder
from app.infrastructure.database.repositories.email_repository import (
    _to_entity as _email_to_entity,
)


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

   

    async def get_by_id(self, thread_id: UUID, user_id: UUID) -> Thread | None:
        
        stmt = select(ThreadModel).where(ThreadModel.id == thread_id, ThreadModel.user_id == user_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model is not None else None

    async def list_by_user(
        self, user_id: UUID, *, page: int = 1, page_size: int = 25, sort: SortOrder = "newest"
    ) -> list[ThreadSummary]:
       
        if page < 1:
            raise ValueError(f"page must be >= 1, got {page}")
        if page_size < 1:
            raise ValueError(f"page_size must be >= 1, got {page_size}")

        email_count_subquery = (
            select(func.count(EmailModel.id))
            .where(EmailModel.thread_id == ThreadModel.id)
            .correlate(ThreadModel)
            .scalar_subquery()
        )

        order_column = (
            ThreadModel.updated_at.desc() if sort == "newest" else ThreadModel.updated_at.asc()
        )
        stmt = (
            select(ThreadModel, email_count_subquery.label("email_count"))
            .where(ThreadModel.user_id == user_id)
            .order_by(order_column)
            .limit(page_size)
            .offset((page - 1) * page_size)
        )

        result = await self._session.execute(stmt)
        return [
            ThreadSummary(
                id=model.id,
                gmail_thread_id=model.gmail_thread_id,
                subject=model.subject,
                snippet=model.snippet,
                updated_at=model.updated_at,
                email_count=email_count,
            )
            for model, email_count in result.all()
        ]

    async def count_by_user(self, user_id: UUID) -> int:
        stmt = select(func.count()).select_from(ThreadModel).where(ThreadModel.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def get_thread_emails(self, thread_id: UUID, user_id: UUID) -> list[Email]:
       
        stmt = (
            select(EmailModel)
            .where(EmailModel.thread_id == thread_id, EmailModel.user_id == user_id)
            .order_by(EmailModel.received_at.asc())
        )
        result = await self._session.execute(stmt)
        return [_email_to_entity(model) for model in result.scalars().all()]

    async def count_thread_emails(self, thread_id: UUID, user_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(EmailModel)
            .where(EmailModel.thread_id == thread_id, EmailModel.user_id == user_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()