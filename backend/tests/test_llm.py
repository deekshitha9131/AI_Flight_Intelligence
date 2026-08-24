import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from app.ai.llm_provider import (
    FallbackProvider,
    GeminiProvider,
    build_llm_provider,
    classify_llm_exception,
)


def test_build_llm_provider_with_api_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-12345")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

    from app.core.config import get_settings

    get_settings(reload=True)

    provider = build_llm_provider()
    assert isinstance(provider, GeminiProvider)
    assert provider._api_key == "test-key-12345"
    assert provider._model == "gemini-3.1-flash-lite"
    assert provider._timeout >= 10.0


def test_build_llm_provider_without_api_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")

    from app.core.config import get_settings

    get_settings(reload=True)

    provider = build_llm_provider()
    assert isinstance(provider, FallbackProvider)
    assert provider._reason == "missing_api_key"


def test_gemini_provider_timeout_configuration():
    provider = GeminiProvider(api_key="test-key", timeout=30.0)
    assert provider._timeout == 30.0
    assert provider._timeout >= 10.0


@pytest.mark.asyncio
async def test_gemini_provider_complete_success():
    provider = GeminiProvider(api_key="test-key", model="gemini-flash-latest", timeout=30.0)

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
    provider = GeminiProvider(api_key="test-key", model="gemini-flash-latest", timeout=30.0)

    mock_client = AsyncMock()
    mock_client.aio.models.generate_content.side_effect = RuntimeError("API error")

    with patch("google.genai.Client", return_value=mock_client):
        with pytest.raises(RuntimeError, match="API error"):
            await provider.complete(
                messages=[{"role": "user", "content": "Hi"}], max_tokens=100
            )


# Error classification tests (A-H)
def test_missing_api_key_classification():
    reply = classify_llm_exception(exc=None, is_configured=False)
    assert "configure GEMINI_API_KEY" in reply or "demo mode" in reply


def test_gemini_400_error_classification():
    class Dummy400Error(Exception):
        code = 400
        status = "INVALID_ARGUMENT"
        message = "Manually set deadline 3s is too short."

    reply = classify_llm_exception(exc=Dummy400Error(), is_configured=True)
    assert "400 Invalid Argument" in reply
    assert "configure GEMINI_API_KEY" not in reply


def test_gemini_401_error_classification():
    class Dummy401Error(Exception):
        code = 401
        status = "UNAUTHENTICATED"
        message = "Invalid API key"

    reply = classify_llm_exception(exc=Dummy401Error(), is_configured=True)
    assert "401" in reply or "authentication failed" in reply.lower()
    assert "configure GEMINI_API_KEY" not in reply


def test_gemini_403_error_classification():
    class Dummy403Error(Exception):
        code = 403
        status = "PERMISSION_DENIED"
        message = "API key not allowed"

    reply = classify_llm_exception(exc=Dummy403Error(), is_configured=True)
    assert "403" in reply or "permission denied" in reply.lower()
    assert "configure GEMINI_API_KEY" not in reply


def test_gemini_429_error_classification():
    class Dummy429Error(Exception):
        code = 429
        status = "RESOURCE_EXHAUSTED"
        message = "Quota exceeded"

    reply = classify_llm_exception(exc=Dummy429Error(), is_configured=True)
    assert "429" in reply or "quota" in reply.lower() or "rate limit" in reply.lower()
    assert "configure GEMINI_API_KEY" not in reply


def test_gemini_timeout_classification():
    reply = classify_llm_exception(exc=asyncio.TimeoutError(), is_configured=True)
    assert "timed out" in reply.lower()
    assert "configure GEMINI_API_KEY" not in reply


def test_gemini_generic_network_error_classification():
    reply = classify_llm_exception(exc=ConnectionRefusedError("Connection refused"), is_configured=True)
    assert "network or provider error" in reply.lower() or "unavailable" in reply.lower()
    assert "configure GEMINI_API_KEY" not in reply


@pytest.mark.asyncio
async def test_fallback_provider_uses_error_classification():
    class Dummy400(Exception):
        code = 400
        status = "INVALID_ARGUMENT"

    fallback = FallbackProvider(error=Dummy400())
    reply, tokens = await fallback.complete(messages=[{"role": "user", "content": "whats wrong"}])
    assert "400 Invalid Argument" in reply
    assert "configure GEMINI_API_KEY" not in reply

