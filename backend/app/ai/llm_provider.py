from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an expert AI travel assistant for AI Flight Intelligence.
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
        max_tokens: int = 1024,
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
        model: str = "gemini-3.1-flash-lite",
        base_url: str = "",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    async def complete(
        self,
        *,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
    ) -> tuple[str, int | None]:
        t0 = time.monotonic()
        logger.info("[LLM START] GeminiProvider.complete | model=%s", self._model)
        try:
            from google.genai import types

            client = self._get_client()

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
                contents = [
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text="Hello")],
                    )
                ]

            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                max_output_tokens=max_tokens,
                temperature=0.7,
                http_options=types.HttpOptions(timeout=3000),
            )

            logger.info("[LLM DISPATCH] generate_content initiating...")
            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=self._model,
                    contents=contents,
                    config=config,
                ),
                timeout=3.0,
            )

            elapsed_ms = (time.monotonic() - t0) * 1000
            reply = response.text or ""
            tokens = (
                response.usage_metadata.total_token_count
                if response.usage_metadata
                else None
            )
            logger.info(
                "[LLM SUCCESS] model=%s tokens=%s elapsed=%.2fms",
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
    """Fallback provider used when no LLM API key is configured or during tests."""

    async def complete(
        self,
        *,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
    ) -> tuple[str, int | None]:
        sys_content = next(
            (m["content"] for m in messages if m.get("role") == "system"),
            "",
        )
        user_msg = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"),
            "",
        )

        if "REAL FLIGHT SEARCH RESULTS for " in sys_content:
            parts = sys_content.split("REAL FLIGHT SEARCH RESULTS for ")
            if len(parts) > 1:
                results_block = parts[1].split("\n\nPresent these")[0].strip()
                lines = [
                    line.strip()
                    for line in results_block.split("\n")
                    if line.strip()
                ]
                header_line = lines[0] if lines else "your request"
                flight_lines = [item for item in lines if item.startswith("-")]
                reply = (
                    f"Here are the available flights for {header_line}:\n"
                    + "\n".join(flight_lines)
                )
                return reply, None

        if "FLIGHT SEARCH STATUS: " in sys_content:
            parts = sys_content.split("FLIGHT SEARCH STATUS: ")
            if len(parts) > 1:
                status_text = parts[1].split(". Inform the user")[0].strip()
                return status_text, None

        if "Route understood: " in sys_content:
            parts = sys_content.split("Route understood: ")
            if len(parts) > 1:
                route_text = parts[1].split(". Departure date is missing.")[0].strip()
                return (
                    f"I understand you want to fly from {route_text}. "
                    "What date or time would you like to depart?"
                ), None

        greetings = {
            "hi", "hello", "hey", "hii", "good morning", "good afternoon",
            "good evening", "thanks", "thank you", "what can you do?", "help"
        }
        if user_msg.strip().lower() in greetings:
            return (
                "Hello! I am your AI travel assistant for AI Flight "
                "Intelligence Platform. How can I help you with your flight "
                "search or travel plans today?"
            ), None

        reply = (
            f'I received your message: "{user_msg[:100]}". '
            "The AI assistant is currently running in demo mode. "
            "Please configure GEMINI_API_KEY for full conversational AI capabilities."
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
        default_model = "gemini-3.1-flash-lite"
        model_setting = getattr(settings, "gemini_model", default_model)
        model: str = (model_setting or default_model).strip()
        base_url: str = (getattr(settings, "gemini_base_url", "") or "").strip()
        logger.info("LLM provider: Gemini (model=%s)", model)
        return GeminiProvider(api_key=api_key, model=model, base_url=base_url)

    logger.warning("LLM provider: FallbackProvider (no GEMINI_API_KEY configured).")
    return FallbackProvider()


def get_system_prompt() -> str:
    """Return the system prompt injected at the start of every conversation."""
    from datetime import date
    today_str = date.today().isoformat()
    return f"{_SYSTEM_PROMPT}\n\nToday's date is {today_str}."
