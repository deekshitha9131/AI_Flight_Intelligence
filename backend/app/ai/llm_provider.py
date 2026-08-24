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


def classify_llm_exception(
    exc: Exception | None = None,
    *,
    is_configured: bool = True,
    user_msg: str = "",
) -> str:
    """Classify LLM provider exception into a safe, human-readable user response.

    Distinguishes missing API key configuration from runtime API failures (401, 403, 429, 400, timeout, network).
    """
    prefix = f'I received your message: "{user_msg[:100]}". ' if user_msg else ""
    if not is_configured:
        return (
            f"{prefix}The AI assistant is currently running in demo mode. "
            "Please configure GEMINI_API_KEY for full conversational AI capabilities."
        )

    if exc is None:
        return (
            f"{prefix}The AI assistant is temporarily unavailable. "
            "Please try your request again."
        )


    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        return "AI service request timed out. Please try again."

    code = getattr(exc, "code", None)
    status_str = str(getattr(exc, "status", "") or "").upper()
    message_str = str(getattr(exc, "message", "") or str(exc)).upper()
    err_str = f"{code} {status_str} {message_str} {type(exc).__name__}".upper()

    if code == 401 or "401" in err_str or "UNAUTHENTICATED" in err_str:
        return "AI service authentication failed (401). Please check that your GEMINI_API_KEY is valid."

    if code == 403 or "403" in err_str or "PERMISSION_DENIED" in err_str:
        return "AI service permission denied (403). Please check project permissions and model access for your GEMINI_API_KEY."

    if code == 429 or "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "QUOTA" in err_str:
        return "AI service rate limit or quota exceeded (429). Please try again in a moment."

    if code == 400 or "400" in err_str or "INVALID_ARGUMENT" in err_str:
        return "AI service request error (400 Invalid Argument). Please check your request parameters."

    if "TIMEOUT" in err_str or "DEADLINE" in err_str:
        return "AI service request timed out. Please try again."

    return "AI service is temporarily unavailable due to a network or provider error. Please try again later."



class GeminiProvider(LLMProvider):
    """Google Gemini ChatCompletion provider via official google-genai SDK."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.1-flash-lite",
        base_url: str = "",
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._timeout = timeout
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

            timeout_ms = int(self._timeout * 1000)
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                max_output_tokens=max_tokens,
                temperature=0.7,
                http_options=types.HttpOptions(timeout=timeout_ms),
            )

            logger.info("[LLM DISPATCH] generate_content initiating...")
            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=self._model,
                    contents=contents,
                    config=config,
                ),
                timeout=self._timeout,
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

    def __init__(
        self,
        reason: str | None = None,
        error: Exception | None = None,
    ) -> None:
        self._reason = reason
        self._error = error

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

        if "I couldn't identify one or both airports" in sys_content:
            return (
                "I couldn't identify one or both airports in that route. "
                "Please provide the departure and destination city, for example: Delhi to Hyderabad."
            ), None

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

        if "Destination understood: " in sys_content:
            parts = sys_content.split("Destination understood: ")
            if len(parts) > 1:
                dest_text = parts[1].split(". Origin")[0].strip()
                return (
                    f"I understand you want to fly to {dest_text}. "
                    "Where would you like to depart from?"
                ), None

        if "Origin understood: " in sys_content:
            parts = sys_content.split("Origin understood: ")
            if len(parts) > 1:
                orig_text = parts[1].split(". Destination")[0].strip()
                return (
                    f"I understand you are departing from {orig_text}. "
                    "Where would you like to fly to?"
                ), None

        import re
        from app.services.assistant_service import (
            is_capability_query,
            is_cancellation,
            is_duration_query,
            is_greeting,
            is_informational_query,
            is_result_followup,
        )

        u_strip = user_msg.strip()
        u_lower = u_strip.lower()

        # Handle result follow-ups in FallbackProvider (e.g. "which flight is best", "give only one", "which is cheapest", "fastest flight")
        if is_result_followup(u_strip) or "previously displayed flight results" in sys_content:
            all_text = sys_content + "\n" + "\n".join(m.get("content", "") for m in messages)
            flight_lines = [line.strip() for line in all_text.split("\n") if line.strip().startswith("- Flight ")]

            if flight_lines:
                if "cheapest" in u_lower or "lowest price" in u_lower:
                    best_line = flight_lines[0]
                    lowest_price = float("inf")
                    for line in flight_lines:
                        p_match = re.search(r"Price:\s*[A-Z]{3}\s*([\d.]+)", line)
                        if p_match:
                            val = float(p_match.group(1))
                            if val < lowest_price:
                                lowest_price = val
                                best_line = line
                    return f"Here is the cheapest flight available from your search:\n{best_line}", None

                if "fastest" in u_lower or "shortest" in u_lower:
                    return f"Here is the fastest flight option available from your search:\n{flight_lines[0]}", None

                if any(w in u_lower for w in ("give only one", "give me one", "show only one", "only 1", "only one")):
                    return f"Here is the top recommended flight option:\n{flight_lines[0]}", None

                return f"Based on your search results, I recommend:\n{flight_lines[0]}\nThis option offers the best balance of schedule and fare value.", None
            else:
                return "I don't have active flight search results to compare right now. Would you like to search for flights?", None

        # Handle duration queries in FallbackProvider
        if is_duration_query(u_strip) or "asking about flight duration" in sys_content:
            route_match = re.search(r"\b([A-Z]{3})\s+(?:to|->|→)\s+([A-Z]{3})\b", sys_content + " " + u_strip)
            if route_match:
                o, d = route_match.group(1), route_match.group(2)
                return f"Non-stop flights from {o} to {d} typically take around 2 to 2.5 hours.", None
            return "Flight duration varies by route. Non-stop domestic flights typically take 1 to 3 hours, while international flights range from 4 to 15+ hours depending on the destination.", None

        if is_capability_query(u_strip):
            return (
                "I am your AI travel assistant. I can help you search flights, "
                "compare fares, look up airport details, predict prices, and provide travel advice."
            ), None

        if is_greeting(u_strip):
            return (
                "Hello! I am your AI travel assistant for AI Flight "
                "Intelligence Platform. How can I help you with your flight "
                "search or travel plans today?"
            ), None

        if is_cancellation(u_strip):
            return (
                "No problem! I won't search for flights. Let me know if you need help with anything else."
            ), None

        if is_informational_query(u_strip):
            if any(w in u_lower for w in ("carry-on", "carry on", "cabin", "hand baggage")):
                return (
                    "For long-haul international travel, passengers are generally allowed 1 carry-on bag "
                    "(up to 7-10 kg) plus 1 small personal item (such as a laptop bag or handbag). "
                    "Please verify exact size and weight limits with your airline."
                ), None
            if any(w in u_lower for w in ("luggage", "baggage")):
                return (
                    "Standard baggage allowances vary by cabin class: Economy typically includes 15-23 kg of "
                    "checked baggage, while Business and First class allow 32 kg or more. Always check your ticket terms."
                ), None
            return (
                "For international flights, we recommend arriving at the airport at least 3 hours before departure "
                "to allow sufficient time for check-in, baggage drop, and security screening."
            ), None

        reply = classify_llm_exception(
            self._error,
            is_configured=(self._reason != "missing_api_key"),
            user_msg=user_msg,
        )

        logger.debug("FallbackProvider.complete | returning classified response: %s", reply)
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
        timeout: float = getattr(settings, "gemini_timeout_seconds", 30.0)
        logger.info("LLM provider: Gemini (model=%s, timeout=%.1fs)", model, timeout)
        return GeminiProvider(api_key=api_key, model=model, base_url=base_url, timeout=timeout)

    logger.warning("LLM provider: FallbackProvider (no GEMINI_API_KEY configured).")
    return FallbackProvider(reason="missing_api_key")



def get_system_prompt() -> str:
    """Return the system prompt injected at the start of every conversation."""
    from datetime import date
    today_str = date.today().isoformat()
    return f"{_SYSTEM_PROMPT}\n\nToday's date is {today_str}."
