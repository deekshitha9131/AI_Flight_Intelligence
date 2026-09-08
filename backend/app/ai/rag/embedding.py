import openai
from openai import AsyncOpenAI

from app.core.config import Settings
from app.core.constants import EMBEDDING_DIMENSIONS
from app.domain.exceptions.ai import AIConfigurationError, EmbeddingProviderError


class EmbeddingService:
    """Client construction is lazy and memoized, same pattern as
    GmailClient and LLMProvider — the API key is only required, and
    only checked, at first actual use."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: AsyncOpenAI | None = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            if not self._settings.openai_api_key:
                raise AIConfigurationError(
                    "OPENAI_API_KEY is not configured. Set it in the environment "
                    "before using RAG embeddings."
                )
            self._client = AsyncOpenAI(api_key=self._settings.openai_api_key)
        return self._client

    def _validate_dimensions(self, embedding: list[float]) -> None:
        if len(embedding) != EMBEDDING_DIMENSIONS:
            raise EmbeddingProviderError(
                f"Embedding provider returned {len(embedding)} dimensions, "
                f"expected {EMBEDDING_DIMENSIONS}. Check EMBEDDING_MODEL matches "
                "the dimensionality configured in app/core/constants.py."
            )

    async def embed_text(self, text: str) -> list[float]:
        """Embed a single piece of text — used for retrieval queries
        (Task 6.6), which have exactly one query string per call."""
        client = self._get_client()
        try:
            response = await client.embeddings.create(
                model=self._settings.embedding_model, input=text
            )
        except openai.APIError as exc:
            raise EmbeddingProviderError(f"Embedding request failed: {exc}") from exc

        embedding = list(response.data[0].embedding)
        self._validate_dimensions(embedding)
        return embedding

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts in one call — used for indexing
        (Task 6.5), where one email's chunks are embedded together
        rather than with one API round trip per chunk."""
        if not texts:
            return []

        client = self._get_client()
        try:
            response = await client.embeddings.create(
                model=self._settings.embedding_model, input=texts
            )
        except openai.APIError as exc:
            raise EmbeddingProviderError(f"Embedding request failed: {exc}") from exc

        embeddings = [list(item.embedding) for item in response.data]
        for embedding in embeddings:
            self._validate_dimensions(embedding)
        return embeddings
