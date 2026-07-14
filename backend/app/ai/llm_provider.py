from __future__ import annotations

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an expert AI travel assistant for the AI Flight Intelligence Platform.
You help users with:
- Flight search and booking advice
- Fare rules and baggage policies
- Destination recommendations and travel planning
- Price trends and best booking windows
- Alternative airports and airlines
- Travel tips and visa information

Be concise, helpful, and accurate. When you don't know something, say so clearly.
Always prioritise the user's budget and preferences."""


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def complete(
        self,
        *,
        messages: list[dict[str, str]],
        max_tokens: int = 512,
    ) -> tuple[str, int | None]:
        """Generate a completion.

        Args:
            messages:   List of {"role": ..., "content": ...} dicts.
            max_tokens: Maximum tokens to generate.

        Returns:
            Tuple of (reply_text, tokens_used_or_None).
        """


class OpenAIProvider(LLMProvider):
    """OpenAI ChatCompletion provider."""

    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo") -> None:
        self._api_key = api_key
        self._model = model

    async def complete(
        self,
        *,
        messages: list[dict[str, str]],
        max_tokens: int = 512,
    ) -> tuple[str, int | None]:
        try:
            from openai import AsyncOpenAI  # type: ignore[import]

            client = AsyncOpenAI(api_key=self._api_key)
            response = await client.chat.completions.create(
                model=self._model,
                messages=messages,  # type: ignore[arg-type]
                max_tokens=max_tokens,
                temperature=0.7,
            )
            reply = response.choices[0].message.content or ""
            tokens = response.usage.total_tokens if response.usage else None
            logger.debug(
                "OpenAIProvider.complete | model=%s tokens=%s", self._model, tokens
            )
            return reply, tokens
        except Exception as exc:
            logger.error("OpenAIProvider.complete | error: %s", exc)
            raise


class FallbackProvider(LLMProvider):
    """No-op provider used when no LLM API key is configured."""

    async def complete(
        self,
        *,
        messages: list[dict[str, str]],
        max_tokens: int = 512,
    ) -> tuple[str, int | None]:
        user_msg = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"),
            "",
        )
        reply = (
            f'I received your message: "{user_msg[:100]}". '
            "The AI assistant is currently running in demo mode — no LLM API key is configured. "
            "Please add OPENAI_API_KEY to your .env file to enable full assistant capabilities."
        )
        logger.debug("FallbackProvider.complete | returning demo response.")
        return reply, None


def build_llm_provider() -> LLMProvider:
    """Construct the appropriate LLM provider from application settings."""
    from app.core.config import get_settings

    settings = get_settings()
    api_key: str = getattr(settings, "openai_api_key", "")

    if api_key:
        model: str = getattr(settings, "openai_model", "gpt-3.5-turbo")
        logger.info("LLM provider: OpenAI (model=%s)", model)
        return OpenAIProvider(api_key=api_key, model=model)

    logger.warning("LLM provider: FallbackProvider (no OPENAI_API_KEY configured).")
    return FallbackProvider()


def get_system_prompt() -> str:
    """Return the system prompt injected at the start of every conversation."""
    return _SYSTEM_PROMPT
