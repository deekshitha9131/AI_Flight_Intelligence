from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas.ai_understanding import AIUnderstandingResult
from app.domain.entities.email_ai_understanding import EmailAIUnderstanding
from app.infrastructure.database.models.email_ai_understanding import EmailAIUnderstandingModel


def _to_entity(model: EmailAIUnderstandingModel) -> EmailAIUnderstanding:
    return EmailAIUnderstanding(
        id=model.id,
        email_id=model.email_id,
        category=model.category,
        intent=model.intent,
        urgency=model.urgency,
        sentiment=model.sentiment,
        entities=list(model.entities),
        summary=model.summary,
        confidence=model.confidence,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class EmailAIUnderstandingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email_id(self, email_id: UUID) -> EmailAIUnderstanding | None:
        stmt = select(EmailAIUnderstandingModel).where(
            EmailAIUnderstandingModel.email_id == email_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model is not None else None

    async def upsert(self, email_id: UUID, result: AIUnderstandingResult) -> EmailAIUnderstanding:
        stmt = select(EmailAIUnderstandingModel).where(
            EmailAIUnderstandingModel.email_id == email_id
        )
        query_result = await self._session.execute(stmt)
        model = query_result.scalar_one_or_none()

        entities_payload = [entity.model_dump() for entity in result.entities]

        if model is None:
            model = EmailAIUnderstandingModel(
                email_id=email_id,
                category=result.category.value,
                intent=result.intent.value,
                urgency=result.urgency.value,
                sentiment=result.sentiment.value,
                entities=entities_payload,
                summary=result.summary,
                confidence=result.confidence,
            )
            self._session.add(model)
        else:
            model.category = result.category.value
            model.intent = result.intent.value
            model.urgency = result.urgency.value
            model.sentiment = result.sentiment.value
            model.entities = entities_payload
            model.summary = result.summary
            model.confidence = result.confidence

        await self._session.commit()
        await self._session.refresh(model)
        return _to_entity(model)
