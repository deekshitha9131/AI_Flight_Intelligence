from typing import Optional
from datetime import datetime


def get_flight_intent_prompt(user_input: str, reference_date: datetime) -> str:
    """
    Generate a prompt for extracting flight intent from user input.

    Args:
        user_input: The user's natural language request.
        reference_date: The current date to use for resolving relative dates.

    Returns:
        A prompt string that instructs the LLM to extract flight intent in a structured format.
    """
    # Format the reference date as a string (we'll use YYYY-MM-DD for simplicity)
    reference_date_str = reference_date.strftime("%Y-%m-%d")

    prompt = f"""
You are an AI assistant that identifies the user's flight-related intent and extracts structured details.
Your task is to convert the user's natural language request into a structured JSON object.
You must follow these rules:

1. Extract the following fields if present in the user input:
   - intent: Use one of GREETING, FLIGHT_SEARCH, FLIGHT_COMPARISON, PRICE_PREDICTION, RECOMMENDATION, GENERAL_FLIGHT_QUESTION, FOLLOW_UP, or UNKNOWN.
     Use FLIGHT_SEARCH only when the user is asking to find or search for flights.
     Use GREETING for greetings, GENERAL_FLIGHT_QUESTION for questions such as what "nonstop" means,
     and UNKNOWN when the request is not flight-related.
   - origin: The departure airport IATA code (e.g., "HYD" for Hyderabad). If not mentioned, set to null.
   - destination: The arrival airport IATA code (e.g., "DEL" for Delhi). If not mentioned, set to null.
   - departure_date: The departure date in YYYY-MM-DD format. If not mentioned, set to null.
   - return_date: The return date in YYYY-MM-DD format (for roundtrip). If not mentioned or one-way, set to null.
   - passengers: The number of passengers (integer between 1 and 9). If not mentioned, default to 1.
   - cabin: The cabin class (e.g., "ECONOMY", "BUSINESS", "FIRST", "PREMIUM_ECONOMY"). If not mentioned, default to "ECONOMY".
   - time_preference: Preferred time of day (e.g., "morning", "afternoon", "evening", "night"). If not mentioned, set to null.
   - price_preference: Price preference (e.g., "cheap", "budget", "expensive"). If not mentioned, set to null.

2. Do NOT invent or guess any information that is not explicitly present in the user input.
   If information is missing, use null (or the default for passengers and cabin as specified).

3. Use the provided reference date to resolve relative dates:
   Reference date: {reference_date_str}
   For example, if the reference date is 2026-08-29 and the user says "tomorrow",
   the departure_date should be 2026-08-30.

4. Normalize airport codes to their IATA codes when possible (e.g., "Hyderabad" -> "HYD").
   If you are unsure of the airport code, set the field to null.

5. Normalize cabin class to one of the standard values:
   ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST.

6. Normalize time preference to: morning, afternoon, evening, night (lowercase).

7. Normalize price preference to: cheap, budget, expensive (lowercase).

8. The output must be a valid JSON object and nothing else.
   Do not include any additional text, explanation, or formatting.

Example:
User input: "Find me a cheap morning flight from Hyderabad to Delhi for two people."
Reference date: 2026-08-29
Output:
{{
  "intent": "flight_search",
  "origin": "HYD",
  "destination": "DEL",
  "departure_date": "2026-08-30",
  "return_date": null,
  "passengers": 2,
  "cabin": "ECONOMY",
  "time_preference": "morning",
  "price_preference": "cheap"
}}

Now, extract the flight intent from the following user input:

User input: "{user_input}"
Reference date: {reference_date_str}
Output:
"""
    return prompt.strip()


def get_flight_intent_prompt_with_history(
    user_input: str,
    conversation_history: str,
    reference_date: datetime
) -> str:
    """
    Generate a prompt for extracting flight intent from user input considering conversation history.

    Args:
        user_input: The user's natural language request.
        conversation_history: A string containing the conversation history.
        reference_date: The current date to use for resolving relative dates.

    Returns:
        A prompt string that instructs the LLM to extract flight intent in a structured format.
    """
    # Format the reference date as a string (we'll use YYYY-MM-DD for simplicity)
    reference_date_str = reference_date.strftime("%Y-%m-%d")

    prompt = f"""
You are an AI assistant that extracts structured flight search intent from user input.
Consider the following conversation history:
{conversation_history}

Now, extract the flight intent from the current user input:
User input: "{user_input}"
Reference date: {reference_date_str}

Your task is to convert the user's natural language request into a structured JSON object, considering the conversation history for context.
You must follow these rules:

1. Extract the following fields if present in the user input or can be inferred from the conversation history:
   - intent: Should always be "flight_search" for flight-related requests.
   - origin: The departure airport IATA code (e.g., "HYD" for Hyderabad). If not mentioned, set to null.
   - destination: The arrival airport IATA code (e.g., "DEL" for Delhi). If not mentioned, set to null.
   - departure_date: The departure date in YYYY-MM-DD format. If not mentioned, set to null.
   - return_date: The return date in YYYY-MM-DD format (for roundtrip). If not mentioned or one-way, set to null.
   - passengers: The number of passengers (integer between 1 and 9). If not mentioned, default to 1.
   - cabin: The cabin class (e.g., "ECONOMY", "BUSINESS", "FIRST", "PREMIUM_ECONOMY"). If not mentioned, default to "ECONOMY".
   - time_preference: Preferred time of day (e.g., "morning", "afternoon", "evening", "night"). If not mentioned, set to null.
   - price_preference: Price preference (e.g., "cheap", "budget", "expensive"). If not mentioned, set to null.

2. Do NOT invent or guess any information that is not explicitly present in the user input or conversation history.
   If information is missing, use null (or the default for passengers and cabin as specified).

3. Use the provided reference date to resolve relative dates:
   Reference date: {reference_date_str}
   For example, if the reference date is 2026-08-29 and the user says "tomorrow",
   the departure_date should be 2026-08-30.

4. Normalize airport codes to their IATA codes when possible (e.g., "Hyderabad" -> "HYD").
   If you are unsure of the airport code, set the field to null.

5. Normalize cabin class to one of the standard values:
   ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST.

6. Normalize time preference to: morning, afternoon, evening, night (lowercase).

7. Normalize price preference to: cheap, budget, expensive (lowercase).

8. Current explicit information in the user input overrides any conflicting information from the conversation history.

9. The output must be a valid JSON object and nothing else.
   Do not include any additional text, explanation, or formatting.

Example:
Conversation history:
USER: Find flights from Hyderabad to Delhi tomorrow.
ASSISTANT: I found several flights from Hyderabad (HYD) to Delhi (DEL) for tomorrow, 2026-08-30.

User input: Which one is cheapest?
Reference date: 2026-08-29
Output:
{{
  "intent": "flight_search",
  "origin": "HYD",
  "destination": "DEL",
  "departure_date": "2026-08-30",
  "return_date": null,
  "passengers": 1,
  "cabin": "ECONOMY",
  "time_preference": null,
  "price_preference": "cheap"
}}

Now, extract the flight intent from the following user input:

User input: "{user_input}"
Reference date: {reference_date_str}
Output:
"""
    return prompt.strip()