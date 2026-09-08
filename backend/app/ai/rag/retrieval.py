from app.ai.rag.embedding import EmbeddingService
from app.ai.schemas.rag import RetrievedChunk
from app.core.constants import TOP_K
from app.domain.entities.user import User
from app.infrastructure.database.repositories.email_chunk_repository import EmailChunkRepository


class RetrievalService:
    def __init__(
        self, *, embedding_service: EmbeddingService, chunk_repository: EmailChunkRepository
    ) -> None:
        self._embedding_service = embedding_service
        self._chunk_repository = chunk_repository

    async def retrieve_relevant_chunks(
        self, user: User, *, query: str, top_k: int = TOP_K
    ) -> list[RetrievedChunk]:
        """Return the `top_k` chunks most similar to `query`, scoped
        entirely to `user`'s own emails."""
        query_embedding = await self._embedding_service.embed_text(query)

        results = await self._chunk_repository.similarity_search(
            user_id=user.id, query_embedding=query_embedding, top_k=top_k
        )

        return [
            RetrievedChunk(
                email_id=result.email_id,
                thread_id=result.thread_id,
                chunk_index=result.chunk_index,
                content=result.content,
                received_at=result.received_at,
                similarity=1.0 - result.distance,
            )
            for result in results
        ]
