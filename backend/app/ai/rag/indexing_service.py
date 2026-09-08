from app.ai.preprocessing.email_preprocessor import EmailPreprocessor
from app.ai.rag.chunker import EmailChunker
from app.ai.rag.embedding import EmbeddingService
from app.domain.entities.email import Email
from app.infrastructure.database.repositories.email_chunk_repository import (
    ChunkWithEmbedding,
    EmailChunkRepository,
)


class EmailIndexingService:
    def __init__(
        self,
        *,
        preprocessor: EmailPreprocessor,
        chunker: EmailChunker,
        embedding_service: EmbeddingService,
        chunk_repository: EmailChunkRepository,
    ) -> None:
        self._preprocessor = preprocessor
        self._chunker = chunker
        self._embedding_service = embedding_service
        self._chunk_repository = chunk_repository

    async def index_email(self, email: Email) -> int:
        preprocessed = self._preprocessor.preprocess(email)
        chunks = self._chunker.chunk(preprocessed)

        if not chunks:
            await self._chunk_repository.replace_chunks_for_email(
                email_id=email.id,
                thread_id=email.thread_id,
                user_id=email.user_id,
                received_at=email.received_at,
                chunks=[],
            )
            return 0

        embeddings = await self._embedding_service.embed_texts([chunk.content for chunk in chunks])

        chunks_with_embeddings = [
            ChunkWithEmbedding(
                chunk_index=chunk.chunk_index, content=chunk.content, embedding=embedding
            )
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]

        stored = await self._chunk_repository.replace_chunks_for_email(
            email_id=email.id,
            thread_id=email.thread_id,
            user_id=email.user_id,
            received_at=email.received_at,
            chunks=chunks_with_embeddings,
        )
        return len(stored)
