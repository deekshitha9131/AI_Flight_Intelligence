from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import openai
import pytest

from app.ai.rag.embedding import EmbeddingService
from app.core.config import Settings
from app.core.constants import EMBEDDING_DIMENSIONS
from app.domain.exceptions.ai import AIConfigurationError, EmbeddingProviderError

BASE_ENV = {
    "APP_ENV": "development",
    "APP_DEBUG": "true",
    "APP_SECRET_KEY": "dev-secret",
    "DATABASE_URL": "postgresql+asyncpg://u:p@h:5432/d",
    "REDIS_URL": "redis://h:6379/0",
    "CELERY_BROKER_URL": "redis://h:6379/1",
    "CELERY_RESULT_BACKEND": "redis://h:6379/1",
    "TOKEN_ENCRYPTION_KEY": "test-token-encryption-key-value",
    "CORS_ORIGINS": "http://localhost:5173",
    "OPENAI_API_KEY": "test-openai-key",
}


def _settings(monkeypatch: pytest.MonkeyPatch, **overrides: str) -> Settings:
    env = {**BASE_ENV, **overrides}
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return Settings(_env_file=None)  # type: ignore[call-arg]


def _embedding_response(vectors: list[list[float]]) -> SimpleNamespace:
    return SimpleNamespace(data=[SimpleNamespace(embedding=v) for v in vectors])


def _valid_vector() -> list[float]:
    return [0.1] * EMBEDDING_DIMENSIONS


@patch("app.ai.rag.embedding.AsyncOpenAI")
async def test_embed_text_returns_vector(
    mock_openai_cls: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_client = MagicMock()
    mock_client.embeddings.create = AsyncMock(return_value=_embedding_response([_valid_vector()]))
    mock_openai_cls.return_value = mock_client

    service = EmbeddingService(_settings(monkeypatch))
    result = await service.embed_text("hello world")

    assert len(result) == EMBEDDING_DIMENSIONS
    call_kwargs = mock_client.embeddings.create.call_args.kwargs
    assert call_kwargs["input"] == "hello world"


@patch("app.ai.rag.embedding.AsyncOpenAI")
async def test_embed_text_uses_configured_model(
    mock_openai_cls: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_client = MagicMock()
    mock_client.embeddings.create = AsyncMock(return_value=_embedding_response([_valid_vector()]))
    mock_openai_cls.return_value = mock_client

    settings = _settings(monkeypatch, EMBEDDING_MODEL="custom-embedding-model")
    service = EmbeddingService(settings)
    await service.embed_text("hello")

    call_kwargs = mock_client.embeddings.create.call_args.kwargs
    assert call_kwargs["model"] == "custom-embedding-model"


@patch("app.ai.rag.embedding.AsyncOpenAI")
async def test_embed_texts_returns_one_vector_per_input(
    mock_openai_cls: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_client = MagicMock()
    mock_client.embeddings.create = AsyncMock(
        return_value=_embedding_response([_valid_vector(), _valid_vector(), _valid_vector()])
    )
    mock_openai_cls.return_value = mock_client

    service = EmbeddingService(_settings(monkeypatch))
    results = await service.embed_texts(["a", "b", "c"])

    assert len(results) == 3
    for vector in results:
        assert len(vector) == EMBEDDING_DIMENSIONS


async def test_embed_texts_with_empty_list_returns_empty_without_calling_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = EmbeddingService(_settings(monkeypatch))
    result = await service.embed_texts([])
    assert result == []


async def test_missing_api_key_raises_configuration_error(monkeypatch: pytest.MonkeyPatch) -> None:
    service = EmbeddingService(_settings(monkeypatch, OPENAI_API_KEY=""))

    with pytest.raises(AIConfigurationError):
        await service.embed_text("hello")


@patch("app.ai.rag.embedding.AsyncOpenAI")
async def test_provider_api_failure_raises_embedding_provider_error(
    mock_openai_cls: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_client = MagicMock()
    mock_client.embeddings.create = AsyncMock(
        side_effect=openai.APIConnectionError(request=MagicMock())
    )
    mock_openai_cls.return_value = mock_client

    service = EmbeddingService(_settings(monkeypatch))

    with pytest.raises(EmbeddingProviderError):
        await service.embed_text("hello")


@patch("app.ai.rag.embedding.AsyncOpenAI")
async def test_wrong_dimensionality_raises_embedding_provider_error(
    mock_openai_cls: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_client = MagicMock()
    mock_client.embeddings.create = AsyncMock(return_value=_embedding_response([[0.1, 0.2, 0.3]]))
    mock_openai_cls.return_value = mock_client

    service = EmbeddingService(_settings(monkeypatch))

    with pytest.raises(EmbeddingProviderError):
        await service.embed_text("hello")


@patch("app.ai.rag.embedding.AsyncOpenAI")
async def test_client_is_built_once_and_memoized(
    mock_openai_cls: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_client = MagicMock()
    mock_client.embeddings.create = AsyncMock(return_value=_embedding_response([_valid_vector()]))
    mock_openai_cls.return_value = mock_client

    service = EmbeddingService(_settings(monkeypatch))
    await service.embed_text("first")
    await service.embed_text("second")

    assert mock_openai_cls.call_count == 1
