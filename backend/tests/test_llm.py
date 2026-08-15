"""
tests/test_llm.py
------------------
Regression tests for Gemini provider configuration, initialization, and fallback logic.
"""

from unittest.mock import AsyncMock, patch

import pytest
from app.ai.llm_provider import FallbackProvider, GeminiProvider, build_llm_provider


def test_build_llm_provider_with_api_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-12345")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.6-flash")

    from app.core.config import get_settings

    get_settings(reload=True)

    provider = build_llm_provider()
    assert isinstance(provider, GeminiProvider)
    assert provider._api_key == "test-key-12345"
    assert provider._model == "gemini-3.6-flash"


def test_build_llm_provider_without_api_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")

    from app.core.config import get_settings

    get_settings(reload=True)

    provider = build_llm_provider()
    assert isinstance(provider, FallbackProvider)


@pytest.mark.asyncio
async def test_gemini_provider_complete_success():
    provider = GeminiProvider(api_key="test-key", model="gemini-flash-latest")

    mock_response = AsyncMock()
    mock_response.text = "Hello! I am your AI flight assistant."
    mock_response.usage_metadata.total_token_count = 42

    mock_client = AsyncMock()
    mock_client.aio.models.generate_content.return_value = mock_response

    with patch("google.genai.Client", return_value=mock_client):
        reply, tokens = await provider.complete(
            messages=[{"role": "user", "content": "Hi"}], max_tokens=100
        )
        assert reply == "Hello! I am your AI flight assistant."
        assert tokens == 42


@pytest.mark.asyncio
async def test_gemini_provider_complete_raises_on_error():
    provider = GeminiProvider(api_key="test-key", model="gemini-flash-latest")

    mock_client = AsyncMock()
    mock_client.aio.models.generate_content.side_effect = RuntimeError("API error")

    with patch("google.genai.Client", return_value=mock_client):
        with pytest.raises(RuntimeError, match="API error"):
            await provider.complete(
                messages=[{"role": "user", "content": "Hi"}], max_tokens=100
            )
