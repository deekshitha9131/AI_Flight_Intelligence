from typing import Any

import anthropic
from anthropic import AsyncAnthropic
from pydantic import ValidationError

from app.ai.prompts.understanding_prompt import SYSTEM_PROMPT, build_user_prompt
from app.ai.schemas.ai_understanding import (
    AIUnderstandingResult,
    EmailCategory,
    EmailIntent,
    EmailSentiment,
    EmailUrgency,
)
from app.ai.schemas.preprocessing import PreprocessedEmail
from app.core.config import Settings
from app.domain.exceptions.ai import AIConfigurationError, AIProviderError, InvalidAIResponseError

_TOOL_NAME = "record_email_understanding"

_TOOL_DEFINITION: dict[str, Any] = {
    "name": _TOOL_NAME,
    "description": "Record the structured understanding of an email.",
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": [value.value for value in EmailCategory],
            },
            "intent": {
                "type": "string",
                "enum": [value.value for value in EmailIntent],
            },
            "urgency": {
                "type": "string",
                "enum": [value.value for value in EmailUrgency],
            },
            "sentiment": {
                "type": "string",
                "enum": [value.value for value in EmailSentiment],
            },
            "entities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "value": {"type": "string"},
                    },
                    "required": ["type", "value"],
                },
            },
            "summary": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        },
        "required": [
            "category",
            "intent",
            "urgency",
            "sentiment",
            "entities",
            "summary",
            "confidence",
        ],
    },
}

_MAX_RESPONSE_TOKENS = 1024
_MAX_DRAFT_RESPONSE_TOKENS = 1024


class LLMProvider:

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: AsyncAnthropic | None = None

    def _get_client(self) -> AsyncAnthropic:
        if self._client is None:
            if not self._settings.anthropic_api_key:
                raise AIConfigurationError(
                    "ANTHROPIC_API_KEY is not configured. Set it in the environment "
                    "before using AI email understanding."
                )
            self._client = AsyncAnthropic(api_key=self._settings.anthropic_api_key)
        return self._client

    async def understand_email(self, email: PreprocessedEmail) -> AIUnderstandingResult:
        client = self._get_client()
        user_prompt = build_user_prompt(email)

        try:
            response = await client.messages.create(
                model=self._settings.llm_classification_model,
                max_tokens=_MAX_RESPONSE_TOKENS,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
                tools=[_TOOL_DEFINITION],
                tool_choice={"type": "tool", "name": _TOOL_NAME},
            )
        except anthropic.APIError as exc:
            raise AIProviderError(f"LLM provider request failed: {exc}") from exc

        tool_use_block = next(
            (block for block in response.content if getattr(block, "type", None) == "tool_use"),
            None,
        )
        if tool_use_block is None:
            raise InvalidAIResponseError(
                "Model response did not include the expected structured tool call."
            )

        try:
            return AIUnderstandingResult(**tool_use_block.input)
        except ValidationError as exc:
            raise InvalidAIResponseError(f"Model output failed schema validation: {exc}") from exc

    async def generate_text(self, *, system_prompt: str, user_prompt: str, model: str) -> str:
        client = self._get_client()

        try:
            response = await client.messages.create(
                model=model,
                max_tokens=_MAX_DRAFT_RESPONSE_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except anthropic.APIError as exc:
            raise AIProviderError(f"LLM provider request failed: {exc}") from exc

        text_block = next(
            (block for block in response.content if getattr(block, "type", None) == "text"),
            None,
        )
        if text_block is None:
            raise InvalidAIResponseError("Model response did not include any text content.")

        return text_block.text