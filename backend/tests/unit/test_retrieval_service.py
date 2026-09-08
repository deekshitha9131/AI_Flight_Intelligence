from datetime import UTC, datetime
from uuid import uuid4

from app.ai.rag.retrieval import RetrievalService
from app.core.constants import TOP_K
from app.domain.entities.user import User
from app.domain.enums.user_status import UserStatus
from app.infrastructure.database.repositories.email_chunk_repository import SimilarChunk


def _user() -> User:
    return User(
        id=uuid4(),
        email="user@example.com",
        full_name="Test User",
        google_sub_id="sub-1",
        status=UserStatus.ACTIVE,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


class FakeEmbeddingService:
    def __init__(self) -> None:
        self.embed_text_calls: list[str] = []

    async def embed_text(self, text: str) -> list[float]:
        self.embed_text_calls.append(text)
        return [0.1, 0.2, 0.3]


class FakeChunkRepository:
    def __init__(self, results: list[SimilarChunk] | None = None) -> None:
        self._results = results or []
        self.similarity_search_calls: list[dict] = []

    async def similarity_search(self, *, user_id, query_embedding, top_k):
        self.similarity_search_calls.append(
            {"user_id": user_id, "query_embedding": query_embedding, "top_k": top_k}
        )
        return self._results


def _similar_chunk(**overrides) -> SimilarChunk:
    defaults = dict(
        email_id=uuid4(),
        thread_id=uuid4(),
        chunk_index=0,
        content="relevant content",
        received_at=datetime.now(UTC),
        distance=0.1,
    )
    defaults.update(overrides)
    return SimilarChunk(**defaults)


async def test_retrieve_embeds_the_query() -> None:
    user = _user()
    embedding_service = FakeEmbeddingService()
    chunk_repository = FakeChunkRepository()
    service = RetrievalService(
        embedding_service=embedding_service, chunk_repository=chunk_repository
    )

    await service.retrieve_relevant_chunks(user, query="flight cancellation")

    assert embedding_service.embed_text_calls == ["flight cancellation"]


async def test_retrieve_scopes_search_to_the_authenticated_user() -> None:
    user = _user()
    embedding_service = FakeEmbeddingService()
    chunk_repository = FakeChunkRepository()
    service = RetrievalService(
        embedding_service=embedding_service, chunk_repository=chunk_repository
    )

    await service.retrieve_relevant_chunks(user, query="anything")

    assert chunk_repository.similarity_search_calls[0]["user_id"] == user.id


async def test_retrieve_uses_top_k_constant_by_default() -> None:
    user = _user()
    chunk_repository = FakeChunkRepository()
    service = RetrievalService(
        embedding_service=FakeEmbeddingService(), chunk_repository=chunk_repository
    )

    await service.retrieve_relevant_chunks(user, query="anything")

    assert chunk_repository.similarity_search_calls[0]["top_k"] == TOP_K


async def test_retrieve_honors_explicit_top_k_override() -> None:
    user = _user()
    chunk_repository = FakeChunkRepository()
    service = RetrievalService(
        embedding_service=FakeEmbeddingService(), chunk_repository=chunk_repository
    )

    await service.retrieve_relevant_chunks(user, query="anything", top_k=2)

    assert chunk_repository.similarity_search_calls[0]["top_k"] == 2


async def test_retrieve_converts_distance_to_similarity() -> None:
    user = _user()
    chunk_repository = FakeChunkRepository(results=[_similar_chunk(distance=0.2)])
    service = RetrievalService(
        embedding_service=FakeEmbeddingService(), chunk_repository=chunk_repository
    )

    results = await service.retrieve_relevant_chunks(user, query="anything")

    assert results[0].similarity == 0.8


async def test_retrieve_preserves_chunk_fields() -> None:
    user = _user()
    email_id = uuid4()
    similar = _similar_chunk(email_id=email_id, chunk_index=3, content="specific text")
    chunk_repository = FakeChunkRepository(results=[similar])
    service = RetrievalService(
        embedding_service=FakeEmbeddingService(), chunk_repository=chunk_repository
    )

    results = await service.retrieve_relevant_chunks(user, query="anything")

    assert results[0].email_id == email_id
    assert results[0].chunk_index == 3
    assert results[0].content == "specific text"
