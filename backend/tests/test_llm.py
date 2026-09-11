import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.ai.llm import GeminiLLMProvider, LLMProviderError
from app.core.config import settings


def test_configured_model_is_supported_project_model():
    assert settings.LLM_MODEL == "gemini-3.6-flash"


@pytest.mark.asyncio
async def test_gemini_provider_generates_with_configured_model():
    response = Mock(text='{"intent":"flight_search"}')
    model = Mock()
    model.generate_content.return_value = response

    with patch('app.ai.llm.genai.configure') as configure, patch(
        'app.ai.llm.genai.GenerativeModel', return_value=model
    ) as model_factory:
        provider = GeminiLLMProvider()
        result = await provider.generate_structured('extract intent')

    configure.assert_called_once()
    model_factory.assert_called_once_with(settings.LLM_MODEL)
    model.generate_content.assert_called_once_with('extract intent')
    assert result == response.text


@pytest.mark.asyncio
async def test_gemini_provider_preserves_unsupported_model_error():
    model = Mock()
    model.generate_content.side_effect = Exception(
        "404 models/gemini-pro is not found for API version v1beta"
    )

    with patch('app.ai.llm.genai.configure'), patch(
        'app.ai.llm.genai.GenerativeModel', return_value=model
    ):
        provider = GeminiLLMProvider()
        with pytest.raises(LLMProviderError, match="Gemini model") as error:
            await provider.generate_structured('extract intent')

    assert settings.LLM_MODEL in str(error.value) or 'gemini-pro' in str(error.value)
