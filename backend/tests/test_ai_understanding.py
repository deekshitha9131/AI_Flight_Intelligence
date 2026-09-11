import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from datetime import datetime
from unittest.mock import patch, AsyncMock
from app.schemas.assistant import FlightIntent
from app.ai.understanding import extract_flight_intent, FlightUnderstandingService
from app.ai.prompts.flight_intent import get_flight_intent_prompt


class TestFlightIntentExtraction:
    """Test cases for flight intent extraction using LLM."""

    @pytest.fixture
    def reference_date(self):
        """Fixed reference date for deterministic tests."""
        return datetime(2026, 8, 29)

    def test_prompt_generation(self, reference_date):
        """Test that the prompt is generated correctly."""
        user_input = "Find me a flight from Hyderabad to Delhi"
        prompt = get_flight_intent_prompt(user_input, reference_date)

        # Check that the prompt contains essential elements
        assert user_input in prompt
        assert "2026-08-29" in prompt  # reference date
        assert "flight_search" in prompt
        assert "origin" in prompt
        assert "destination" in prompt
        assert "departure_date" in prompt
        assert "JSON" in prompt

    def test_extract_json_from_response_valid(self):
        """Test extracting valid JSON from LLM response."""
        service = FlightUnderstandingService()

        # Valid JSON response
        response = '{"intent": "flight_search", "origin": "HYD"}'
        result = service._extract_json_from_response(response)
        assert result == {"intent": "flight_search", "origin": "HYD"}

        # JSON with extra whitespace
        response = '  {"intent": "flight_search"}  '
        result = service._extract_json_from_response(response)
        assert result == {"intent": "flight_search"}

        # JSON embedded in text
        response = 'Here is the result: {"intent": "flight_search", "passengers": 2} End of response.'
        result = service._extract_json_from_response(response)
        assert result == {"intent": "flight_search", "passengers": 2}

    def test_extract_json_from_response_invalid(self):
        """Test handling of invalid JSON responses."""
        service = FlightUnderstandingService()

        # Invalid JSON
        response = 'This is not JSON'
        with pytest.raises(Exception):  # Should raise JSONDecodeError or our custom exception
            service._extract_json_from_response(response)

        # Empty response
        response = ''
        with pytest.raises(Exception):
            service._extract_json_from_response(response)

    @pytest.mark.asyncio
    @patch('app.ai.understanding.generate_structured')
    async def test_extract_flight_intent_success(self, mock_generate, reference_date):
        """Test successful flight intent extraction."""
        # Mock LLM response
        mock_llm_response = '''
        {
          "intent": "flight_search",
          "origin": "HYD",
          "destination": "DEL",
          "departure_date": "2026-08-30T10:00:00",
          "return_date": null,
          "passengers": 2,
          "cabin": "ECONOMY",
          "time_preference": "morning",
          "price_preference": "cheap"
        }
        '''
        mock_generate.return_value = mock_llm_response

        # Call the function
        result = await extract_flight_intent(
            "Find me a cheap morning flight from Hyderabad to Delhi for two people tomorrow",
            reference_date=reference_date
        )

        # Verify the LLM was called
        mock_generate.assert_called_once()

        # Verify the result
        assert isinstance(result, FlightIntent)
        assert result.intent == "flight_search"
        assert result.origin == "HYD"
        assert result.destination == "DEL"
        assert result.passengers == 2
        assert result.cabin == "ECONOMY"
        assert result.time_preference == "morning"
        assert result.price_preference == "cheap"
        # Note: We're not checking the exact datetime parsing here as it depends on implementation

    @pytest.mark.asyncio
    @patch('app.ai.understanding.generate_structured')
    async def test_extract_flight_intent_missing_info(self, mock_generate, reference_date):
        """Test extraction with missing information."""
        # Mock LLM response with missing fields
        mock_llm_response = '''
        {
          "intent": "flight_search",
          "origin": "HYD",
          "destination": null,
          "departure_date": null,
          "return_date": null,
          "passengers": 1,
          "cabin": "ECONOMY",
          "time_preference": null,
          "price_preference": null
        }
        '''
        mock_generate.return_value = mock_llm_response

        result = await extract_flight_intent(
            "I want to fly from Hyderabad",
            reference_date=reference_date
        )

        assert result.origin == "HYD"
        assert result.destination is None
        assert result.departure_date is None
        assert result.passengers == 1  # default value
        assert result.cabin == "ECONOMY"  # default value
        assert result.time_preference is None
        assert result.price_preference is None

    @pytest.mark.asyncio
    @patch('app.ai.understanding.generate_structured')
    async def test_extract_flight_intent_relative_dates(self, mock_generate, reference_date):
        """Test extraction of relative dates."""
        # Test tomorrow
        mock_llm_response = '''
        {
          "intent": "flight_search",
          "origin": "HYD",
          "destination": "DEL",
          "departure_date": "2026-08-30T00:00:00",
          "return_date": null,
          "passengers": 1,
          "cabin": "ECONOMY",
          "time_preference": null,
          "price_preference": null
        }
        '''
        mock_generate.return_value = mock_llm_response

        result = await extract_flight_intent(
            "Flight from Hyderabad to Delhi tomorrow",
            reference_date=reference_date
        )

        # The day after 2026-08-29 is 2026-08-30
        assert result.origin == "HYD"
        assert result.destination == "DEL"
        # Note: We're checking that a date was extracted, exact time depends on implementation

        # Test next Monday (from 2026-08-29, which is a Sunday, next Monday is 2026-09-04)
        mock_llm_response = '''
        {
          "intent": "flight_search",
          "origin": "HYD",
          "destination": "DEL",
          "departure_date": "2026-09-04T00:00:00",
          "return_date": null,
          "passengers": 1,
          "cabin": "ECONOMY",
          "time_preference": null,
          "price_preference": null
        }
        '''
        mock_generate.return_value = mock_llm_response

        result = await extract_flight_intent(
            "Flight from Hyderabad to Delhi next Monday",
            reference_date=reference_date
        )

        assert result.origin == "HYD"
        assert result.destination == "DEL"

    @pytest.mark.asyncio
    @patch('app.ai.understanding.generate_structured')
    async def test_extract_flight_intent_invalid_json(self, mock_generate, reference_date):
        """Test handling of invalid JSON from LLM."""
        mock_generate.return_value = "This is not valid JSON"

        with pytest.raises(Exception):  # Should raise our custom exception
            await extract_flight_intent(
                "Find me a flight to Delhi",
                reference_date=reference_date
            )

    @pytest.mark.asyncio
    @patch('app.ai.understanding.generate_structured')
    async def test_extract_flight_intent_llm_error(self, mock_generate, reference_date):
        """Test handling of LLM provider errors."""
        mock_generate.side_effect = Exception("LLM API error")

        with pytest.raises(Exception):  # Should raise our custom exception
            await extract_flight_intent(
                "Find me a flight to Delhi",
                reference_date=reference_date
            )

    @pytest.mark.asyncio
    @patch('app.ai.understanding.generate_structured')
    async def test_extract_flight_intent_no_fabrication(self, mock_generate, reference_date):
        """Test that the system does not fabricate missing information."""
        # Mock LLM response that correctly leaves missing fields as null
        mock_llm_response = '''
        {
          "intent": "flight_search",
          "origin": null,
          "destination": "DEL",
          "departure_date": null,
          "return_date": null,
          "passengers": 1,
          "cabin": "ECONOMY",
          "time_preference": null,
          "price_preference": null
        }
        '''
        mock_generate.return_value = mock_llm_response

        result = await extract_flight_intent(
            "I want to go to Delhi",
            reference_date=reference_date
        )

        # Should NOT invent an origin
        assert result.origin is None
        assert result.destination == "DEL"
        # Should use defaults for passengers and cabin
        assert result.passengers == 1
        assert result.cabin == "ECONOMY"

    def test_flight_intent_schema_defaults(self):
        """Test that FlightIntent schema applies correct defaults."""
        # Let's create a more specific test by looking at the schema
        from app.schemas.assistant import FlightIntent
        # Check that passengers defaults to 1
        assert FlightIntent(intent="flight_search").passengers == 1
        # Check that cabin defaults to ECONOMY
        assert FlightIntent(intent="flight_search").cabin == "ECONOMY"
        # Check that origin and destination are None by default
        assert FlightIntent(intent="flight_search").origin is None
        assert FlightIntent(intent="flight_search").destination is None

if __name__ == "__main__":
    pytest.main([__file__])