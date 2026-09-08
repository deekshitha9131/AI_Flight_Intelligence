from app.ai.context.draft_context import DraftContext
from app.ai.prompts.draft_prompt import SYSTEM_PROMPT, build_draft_prompt
from app.ai.providers.llm_provider import LLMProvider
from app.core.config import Settings
from app.domain.exceptions.ai import InvalidAIResponseError


class DraftGenerator:

    def __init__(self, *, llm_provider: LLMProvider, settings: Settings) -> None:
        self._llm_provider = llm_provider
        self._settings = settings

    async def generate(self, context: DraftContext) -> str:
        user_prompt = build_draft_prompt(
            email=context.email,
            understanding=context.understanding,
            context=context.retrieved_context,
        )

        generated_text = await self._llm_provider.generate_text(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            model=self._settings.llm_drafting_model,
        )

        if generated_text is None or not generated_text.strip():
            raise InvalidAIResponseError(
                "Model returned an empty or whitespace-only draft response."
            )

        return generated_text