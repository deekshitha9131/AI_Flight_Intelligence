from dataclasses import dataclass

from app.ai.schemas.ai_understanding import AIUnderstandingResult
from app.ai.schemas.rag import RAGContext
from app.domain.entities.email import Email


@dataclass
class DraftContext:
    email: Email
    understanding: AIUnderstandingResult
    retrieved_context: RAGContext
    instructions: str | None = None


class DraftContextBuilder:
    def build_context(
        self,
        *,
        email: Email,
        understanding: AIUnderstandingResult,
        retrieved_context: RAGContext | None = None,
        instructions: str | None = None,
    ) -> DraftContext:
        return DraftContext(
            email=email,
            understanding=understanding,
            retrieved_context=retrieved_context if retrieved_context is not None else RAGContext(),
            instructions=instructions,
        )