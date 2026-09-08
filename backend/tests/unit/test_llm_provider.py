from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import pytest

from app.ai.providers.llm_provider import LLMProvider
from app.ai.schemas.ai_understanding import AIUnderstandingResult
from app.ai.schemas.preprocessing import PreprocessedEmail
from app.core.config import Settings
from app.domain.exceptions.ai import AIConfigurationError, AIProviderError, InvalidAIResponseError

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
    "ANTHROPIC_API_KEY": "test-anthropic-key",
}


def _settings(monkeypatch: pytest.MonkeyPatch, **overrides: str) -> Settings:
    env = {**BASE_ENV, **overrides}
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return Settings(_env_file=None)  # type: ignore[call-arg]


def _preprocessed_email(**overrides) -> PreprocessedEmail:
    defaults = dict(
        sender="jane@example.com",
        recipients=["bob@example.com"],
        subject="Flight Cancelled",
        body="Your flight booking has been cancelled. Please contact us immediately.",
        truncated=False,
    )
    defaults.update(overrides)
    return PreprocessedEmail(**defaults)


def _valid_tool_input(**overrides) -> dict:
    defaults = dict(
        category="travel",
        intent="cancellation",
        urgency="high",
        sentiment="negative",
        entities=[{"type": "organization", "value": "Airline"}],
        summary="Flight booking was cancelled.",
        confidence=0.94,
    )
    defaults.update(overrides)
    return defaults


def _tool_use_response(tool_input: dict) -> SimpleNamespace:
    tool_use_block = SimpleNamespace(type="tool_use", name="record_email_understanding", input=tool_input)
    return SimpleNamespace(content=[tool_use_block])


def _text_response(text: str) -> SimpleNamespace:
    text_block = SimpleNamespace(type="text", text=text)
    return SimpleNamespace(content=[text_block])

@patch("app.ai.providers.llm_provider.AsyncAnthropic")
async def test_understand_email_returns_validated_result(
    mock_anthropic_cls: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=_tool_use_response(_valid_tool_input()))
    mock_anthropic_cls.return_value = mock_client

    provider = LLMProvider(_settings(monkeypatch))
    result = await provider.understand_email(_preprocessed_email())

    assert isinstance(result, AIUnderstandingResult)
    assert result.category.value == "travel"
    assert result.confidence == 0.94


@patch("app.ai.providers.llm_provider.AsyncAnthropic")
async def test_understand_email_uses_configured_model(
    mock_anthropic_cls: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=_tool_use_response(_valid_tool_input()))
    mock_anthropic_cls.return_value = mock_client

    settings = _settings(monkeypatch, LLM_CLASSIFICATION_MODEL="claude-haiku-test")
    provider = LLMProvider(settings)
    await provider.understand_email(_preprocessed_email())

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-haiku-test"


@patch("app.ai.providers.llm_provider.AsyncAnthropic")
async def test_understand_email_forces_structured_tool_use(
    mock_anthropic_cls: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=_tool_use_response(_valid_tool_input()))
    mock_anthropic_cls.return_value = mock_client

    provider = LLMProvider(_settings(monkeypatch))
    await provider.understand_email(_preprocessed_email())

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["tool_choice"] == {"type": "tool", "name": "record_email_understanding"}
    assert call_kwargs["tools"][0]["name"] == "record_email_understanding"


@patch("app.ai.providers.llm_provider.AsyncAnthropic")
async def test_prompt_includes_email_content(
    mock_anthropic_cls: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=_tool_use_response(_valid_tool_input()))
    mock_anthropic_cls.return_value = mock_client

    provider = LLMProvider(_settings(monkeypatch))
    email = _preprocessed_email(subject="Unique Subject XYZ")
    await provider.understand_email(email)

    call_kwargs = mock_client.messages.create.call_args.kwargs
    user_message = call_kwargs["messages"][0]["content"]
    assert "Unique Subject XYZ" in user_message
    assert email.sender in user_message


async def test_missing_api_key_raises_configuration_error(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(monkeypatch, ANTHROPIC_API_KEY="")
    provider = LLMProvider(settings)

    with pytest.raises(AIConfigurationError):
        await provider.understand_email(_preprocessed_email())


@patch("app.ai.providers.llm_provider.AsyncAnthropic")
async def test_provider_api_failure_raises_ai_provider_error(
    mock_anthropic_cls: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(
        side_effect=anthropic.APIConnectionError(request=MagicMock())
    )
    mock_anthropic_cls.return_value = mock_client

    provider = LLMProvider(_settings(monkeypatch))

    with pytest.raises(AIProviderError):
        await provider.understand_email(_preprocessed_email())


@patch("app.ai.providers.llm_provider.AsyncAnthropic")
async def test_missing_tool_use_block_raises_invalid_response_error(
    mock_anthropic_cls: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_client = MagicMock()
    text_only_response = SimpleNamespace(content=[SimpleNamespace(type="text", text="I cannot help.")])
    mock_client.messages.create = AsyncMock(return_value=text_only_response)
    mock_anthropic_cls.return_value = mock_client

    provider = LLMProvider(_settings(monkeypatch))

    with pytest.raises(InvalidAIResponseError):
        await provider.understand_email(_preprocessed_email())


@patch("app.ai.providers.llm_provider.AsyncAnthropic")
async def test_invalid_enum_value_raises_invalid_response_error(
    mock_anthropic_cls: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_client = MagicMock()
    bad_input = _valid_tool_input(category="not-a-real-category")
    mock_client.messages.create = AsyncMock(return_value=_tool_use_response(bad_input))
    mock_anthropic_cls.return_value = mock_client

    provider = LLMProvider(_settings(monkeypatch))

    with pytest.raises(InvalidAIResponseError):
        await provider.understand_email(_preprocessed_email())


@patch("app.ai.providers.llm_provider.AsyncAnthropic")
async def test_out_of_range_confidence_raises_invalid_response_error(
    mock_anthropic_cls: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_client = MagicMock()
    bad_input = _valid_tool_input(confidence=1.5)
    mock_client.messages.create = AsyncMock(return_value=_tool_use_response(bad_input))
    mock_anthropic_cls.return_value = mock_client

    provider = LLMProvider(_settings(monkeypatch))

    with pytest.raises(InvalidAIResponseError):
        await provider.understand_email(_preprocessed_email())


@patch("app.ai.providers.llm_provider.AsyncAnthropic")
async def test_missing_required_field_raises_invalid_response_error(
    mock_anthropic_cls: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_client = MagicMock()
    bad_input = _valid_tool_input()
    del bad_input["summary"]
    mock_client.messages.create = AsyncMock(return_value=_tool_use_response(bad_input))
    mock_anthropic_cls.return_value = mock_client

    provider = LLMProvider(_settings(monkeypatch))

    with pytest.raises(InvalidAIResponseError):
        await provider.understand_email(_preprocessed_email())


@patch("app.ai.providers.llm_provider.AsyncAnthropic")
async def test_client_is_built_once_and_memoized(
    mock_anthropic_cls: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=_tool_use_response(_valid_tool_input()))
    mock_anthropic_cls.return_value = mock_client

    provider = LLMProvider(_settings(monkeypatch))
    await provider.understand_email(_preprocessed_email())
    await provider.understand_email(_preprocessed_email())

    assert mock_anthropic_cls.call_count == 1
    

@patch("app.ai.providers.llm_provider.AsyncAnthropic")
async def test_generate_text_returns_text_content(
    mock_anthropic_cls: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=_text_response("Thanks for reaching out."))
    mock_anthropic_cls.return_value = mock_client

    provider = LLMProvider(_settings(monkeypatch))
    result = await provider.generate_text(
        system_prompt="You are a drafting assistant.", user_prompt="Draft a reply.", model="claude-sonnet-5"
    )

    assert result == "Thanks for reaching out."


@patch("app.ai.providers.llm_provider.AsyncAnthropic")
async def test_generate_text_uses_given_model(
    mock_anthropic_cls: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=_text_response("Reply text."))
    mock_anthropic_cls.return_value = mock_client

    provider = LLMProvider(_settings(monkeypatch))
    await provider.generate_text(
        system_prompt="System.", user_prompt="User.", model="claude-drafting-test-model"
    )

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-drafting-test-model"


@patch("app.ai.providers.llm_provider.AsyncAnthropic")
async def test_generate_text_passes_system_and_user_prompts(
    mock_anthropic_cls: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=_text_response("Reply."))
    mock_anthropic_cls.return_value = mock_client

    provider = LLMProvider(_settings(monkeypatch))
    await provider.generate_text(
        system_prompt="Distinctive system instructions.",
        user_prompt="Distinctive user content.",
        model="claude-sonnet-5",
    )

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["system"] == "Distinctive system instructions."
    assert call_kwargs["messages"][0]["content"] == "Distinctive user content."


@patch("app.ai.providers.llm_provider.AsyncAnthropic")
async def test_generate_text_does_not_use_tool_use(
    mock_anthropic_cls: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """generate_text is a free-text call — no tools/tool_choice, unlike
    understand_email's forced structured output."""
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=_text_response("Reply."))
    mock_anthropic_cls.return_value = mock_client

    provider = LLMProvider(_settings(monkeypatch))
    await provider.generate_text(system_prompt="S", user_prompt="U", model="claude-sonnet-5")

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert "tools" not in call_kwargs
    assert "tool_choice" not in call_kwargs


async def test_generate_text_missing_api_key_raises_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings(monkeypatch, ANTHROPIC_API_KEY="")
    provider = LLMProvider(settings)

    with pytest.raises(AIConfigurationError):
        await provider.generate_text(system_prompt="S", user_prompt="U", model="claude-sonnet-5")


@patch("app.ai.providers.llm_provider.AsyncAnthropic")
async def test_generate_text_provider_failure_raises_ai_provider_error(
    mock_anthropic_cls: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(
        side_effect=anthropic.APIConnectionError(request=MagicMock())
    )
    mock_anthropic_cls.return_value = mock_client

    provider = LLMProvider(_settings(monkeypatch))

    with pytest.raises(AIProviderError):
        await provider.generate_text(system_prompt="S", user_prompt="U", model="claude-sonnet-5")


@patch("app.ai.providers.llm_provider.AsyncAnthropic")
async def test_generate_text_missing_text_block_raises_invalid_response_error(
    mock_anthropic_cls: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_client = MagicMock()
    tool_only_response = SimpleNamespace(
        content=[SimpleNamespace(type="tool_use", name="unexpected", input={})]
    )
    mock_client.messages.create = AsyncMock(return_value=tool_only_response)
    mock_anthropic_cls.return_value = mock_client

    provider = LLMProvider(_settings(monkeypatch))

    with pytest.raises(InvalidAIResponseError):
        await provider.generate_text(system_prompt="S", user_prompt="U", model="claude-sonnet-5")