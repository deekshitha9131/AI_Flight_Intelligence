from typing import Optional, List
from datetime import datetime

def get_assistant_response_prompt(
    user_input: str,
    search_info: dict,
    flights_data: List[dict],
    total_results: int
) -> str:
    """
    Generate a prompt for the assistant to create a conversational response
    based on verified flight search results.

    Args:
        user_input: The user's original natural language request
        search_info: Dictionary with search parameters (origin, destination, etc.)
        flights_data: List of flight dictionaries (limited to top 5 for response)
        total_results: Total number of flights found

    Returns:
        Prompt string for the LLM to generate response
    """
    # Format the reference date as a string (we'll use YYYY-MM-DD for simplicity)
    reference_date_str = datetime.now().strftime("%Y-%m-%d")

    prompt = f"""
You are an AI flight assistant generating a response using verified flight data supplied by the backend.

USER REQUEST: "{user_input}"

SEARCH PARAMETERS:
- Origin: {search_info.get('origin')}
- Destination: {search_info.get('destination')}
- Departure Date: {search_info.get('departure_date')}
- Passengers: {search_info.get('passengers')}
- Cabin Class: {search_info.get('cabin')}

FLIGHT RESULTS (showing up to 5 of {total_results} total flights):
"""

    if flights_data:
        for i, flight in enumerate(flights_data, 1):
            prompt += f"""
{i}. Airline: {flight['airline']}
   Flight: {flight['flight_number']}
   Route: {flight['origin']} → {flight['destination']}
   Departure: {flight['departure_time']}
   Arrival: {flight['arrival_time']}
   Duration: {flight['duration']} minutes
   Stops: {flight['stops']}
   Price: {flight['price']} {flight['currency']}
"""
    else:
        prompt += "No flights found matching the search criteria.\n"

    prompt += """
IMPORTANT RULES:
- You are generating a response using verified flight data supplied by the backend.
- Never invent:
  * airlines
  * flight numbers
  * prices
  * times
  * durations
  * baggage information
  * cancellation policies
  * availability
- Use only information contained in the supplied flight results.
- If no results are supplied, do not claim flights were found.
- Keep the response conversational, helpful, and natural-sounding.
- If flights were found, summarize the options naturally.
- If no flights were found, suggest trying different dates or nearby airports.
- Do not expose internal provider errors or technical details.

Response:
"""
    return prompt.strip()