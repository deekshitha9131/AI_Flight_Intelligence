import google.generativeai as genai
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class LLMProviderError(RuntimeError):
    """Raised when the configured Gemini provider cannot generate content."""


class LLMConfigurationError(LLMProviderError):
    """Raised when the Gemini provider is not configured correctly."""


class GeminiLLMProvider:
    """Google Gemini LLM provider."""

    def __init__(self):
        self.api_key = settings.LLM_API_KEY
        self.model_name = settings.LLM_MODEL
        self.timeout = settings.LLM_TIMEOUT
        self.model = None
        if not self.api_key or self.api_key.startswith("your-"):
            logger.error("Gemini API key not configured for model %s", self.model_name)
        else:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(self.model_name)
            except Exception as e:
                logger.error("Failed to initialize Gemini model %s: %s", self.model_name, str(e))
                self.model = None

    async def generate_structured(self, prompt: str) -> str:
        """
        Generate a structured response from the LLM.

        Args:
            prompt: The prompt to send to the LLM.

        Returns:
            The raw text response from the LLM.

        Raises:
            Exception: If there is an error communicating with the provider or if the provider is not configured.
        """
        if self.model is None:
            raise LLMConfigurationError(
                f"Gemini provider is not configured for model '{self.model_name}'"
            )
        try:
            # For simplicity, we are using the synchronous method in an async function.
            # In a production environment, we might want to use the async client or run in a threadpool.
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error("Error generating content from Gemini model %s: %s", self.model_name, str(e))
            raise LLMProviderError(
                f"Gemini model '{self.model_name}' failed to generate content: {str(e)}"
            ) from e

# Create a singleton instance
gemini_llm = GeminiLLMProvider()

# Convenience function for external use
async def generate_structured(prompt: str) -> str:
    """
    Generate a structured response using the configured LLM provider.

    Args:
        prompt: The prompt to send to the LLM.

    Returns:
        The raw text response from the LLM.
    """
    return await gemini_llm.generate_structured(prompt)