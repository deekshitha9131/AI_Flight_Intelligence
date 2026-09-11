import json
import logging
from typing import Optional
from datetime import datetime
from app.core.config import settings
from app.schemas.assistant import FlightIntent
from app.ai.llm import generate_structured
from .prompts.flight_intent import get_flight_intent_prompt

logger = logging.getLogger(__name__)

class FlightUnderstandingService:
    """Service for extracting flight intent from natural language using LLM."""

    def __init__(self):
        pass

    async def extract_flight_intent(self, user_input: str, reference_date: Optional[datetime] = None) -> FlightIntent:
        """
        Extract flight intent from user input using LLM.

        Args:
            user_input: The user's natural language request.
            reference_date: The reference date for resolving relative dates.
                           If not provided, uses current date.

        Returns:
            FlightIntent object with extracted information.

        Raises:
            Exception: If there is an error in the extraction process.
        """
        if reference_date is None:
            reference_date = datetime.now()

        # Generate the prompt
        prompt = get_flight_intent_prompt(user_input, reference_date)

        try:
            # Get response from LLM
            llm_response = await generate_structured(prompt)
            logger.debug(f"LLM raw response: {llm_response}")

            # Parse the JSON response
            # The LLM might return extra text, so we try to extract JSON
            intent_data = self._extract_json_from_response(llm_response)

            # Validate and create FlightIntent object
            flight_intent = FlightIntent(**intent_data)
            return flight_intent

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {llm_response}")
            raise Exception(f"Failed to parse AI response: {str(e)}")
        except Exception as e:
            logger.error(f"Error extracting flight intent: {str(e)}")
            raise RuntimeError(f"AI understanding failed: {str(e)}") from e

    def _extract_json_from_response(self, response: str) -> dict:
        """
        Extract JSON from LLM response, handling potential extra text.

        Args:
            response: The raw response from the LLM.

        Returns:
            Dictionary parsed from the JSON in the response.

        Raises:
            json.JSONDecodeError: If no valid JSON is found.
        """
        # Try to parse the entire response as JSON first
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            pass

        # Look for JSON object in the response
        # Find the first '{' and last '}' to extract potential JSON
        start = response.find('{')
        end = response.rfind('}')

        if start != -1 and end != -1 and start < end:
            json_str = response[start:end+1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        # If we still didn't find valid JSON, raise an error
        raise json.JSONDecodeError("No valid JSON found in LLM response", response, 0)

# Create a singleton instance
flight_understanding_service = FlightUnderstandingService()

# Convenience function for external use
async def extract_flight_intent(user_input: str, reference_date: Optional[datetime] = None) -> FlightIntent:
    """
    Extract flight intent from user input using the configured AI service.

    Args:
        user_input: The user's natural language request.
        reference_date: The reference date for resolving relative dates.
                       If not provided, uses current date.

    Returns:
        FlightIntent object with extracted information.
    """
    return await flight_understanding_service.extract_flight_intent(user_input, reference_date)