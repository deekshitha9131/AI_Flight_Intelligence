from __future__ import annotations

import logging
import time
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


class GeminiProvider(LLMProvider):
    """Google Gemini ChatCompletion provider via official google-genai SDK."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.6-flash",
        base_url: str = "",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url

    async def complete(
        self,
        *,
        messages: list[dict[str, str]],
        max_tokens: int = 512,
    ) -> tuple[str, int | None]:
        t0 = time.monotonic()
        logger.info("[LLM START] GeminiProvider.complete | model=%s", self._model)
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self._api_key)

            system_instruction: str | None = None
            contents = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "system":
                    system_instruction = content
                else:
                    gemini_role = "model" if role == "assistant" else "user"
                    contents.append(
                        types.Content(
                            role=gemini_role,
                            parts=[types.Part.from_text(text=content)],
                        )
                    )

            if not contents:
                contents = [types.Content(role="user", parts=[types.Part.from_text(text="Hello")])]

            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                max_output_tokens=max_tokens,
                temperature=0.7,
            )

            logger.info("[LLM DISPATCH] client.aio.models.generate_content initiating...")
            response = await client.aio.models.generate_content(
                model=self._model,
                contents=contents,
                config=config,
            )

            elapsed_ms = (time.monotonic() - t0) * 1000
            reply = response.text or ""
            tokens = (
                response.usage_metadata.total_token_count
                if response.usage_metadata
                else None
            )
            logger.info(
                "[LLM SUCCESS] GeminiProvider.complete | model=%s tokens=%s elapsed=%.2fms",
                self._model,
                tokens,
                elapsed_ms,
            )
            return reply, tokens
        except Exception as exc:
            elapsed_ms = (time.monotonic() - t0) * 1000
            logger.error(
                "[LLM ERROR] GeminiProvider failed after %.2fms: %s",
                elapsed_ms,
                exc,
                exc_info=True,
            )
            raise exc


class OpenAIProvider(GeminiProvider):
    """Backwards compatibility alias mapping OpenAIProvider to GeminiProvider."""

    pass


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
            "Please add GEMINI_API_KEY to your .env file to enable full assistant capabilities."
        )
        logger.debug("FallbackProvider.complete | returning demo response.")
        return reply, None


def build_llm_provider() -> LLMProvider:
    """Construct the appropriate LLM provider from application settings."""
    from app.core.config import get_settings

    settings = get_settings()
    api_key: str = (getattr(settings, "gemini_api_key", "") or "").strip() or (
        getattr(settings, "openai_api_key", "") or ""
    ).strip()

    if api_key:
        model: str = (getattr(settings, "gemini_model", "gemini-3.6-flash") or "gemini-3.6-flash").strip()
        base_url: str = (getattr(settings, "gemini_base_url", "") or "").strip()
        logger.info("LLM provider: Gemini (model=%s)", model)
        return GeminiProvider(api_key=api_key, model=model, base_url=base_url)

    logger.warning("LLM provider: FallbackProvider (no GEMINI_API_KEY configured).")
    return FallbackProvider()


def get_system_prompt() -> str:
    """Return the system prompt injected at the start of every conversation."""
    return _SYSTEM_PROMPT
