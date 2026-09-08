from app.ai.preprocessing.email_preprocessor import EmailPreprocessor
from app.ai.providers.llm_provider import LLMProvider
from app.ai.schemas.ai_understanding import AIUnderstandingResult
from app.domain.entities.email import Email


class AIUnderstandingService:
    def __init__(self, *, preprocessor: EmailPreprocessor, llm_provider: LLMProvider) -> None:
        self._preprocessor = preprocessor
        self._llm_provider = llm_provider

    async def analyze_email(self, email: Email) -> AIUnderstandingResult:
        preprocessed = self._preprocessor.preprocess(email)
        return await self._llm_provider.understand_email(preprocessed)
