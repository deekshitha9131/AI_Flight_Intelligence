import logging
import re
import json
from typing import Optional, List, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from app.schemas.assistant import FlightIntent, AssistantChatRequest, AssistantResponse
from app.schemas.flight import FlightSearchRequest, FlightResponse
from app.core.config import settings
from app.models.conversation import Conversation
from app.models.message import Message
from app.services.flight import search_flights
from app.services.conversation import ConversationService
from app.services.preference import get_preference

logger = logging.getLogger(__name__)


class AssistantService:
    """Orchestrates the AI flight assistant workflow."""

    def __init__(self, db: Session):
        self.conversation_service = ConversationService(db)

    # ------------------------------------------------------------------ #
    #  Main entry point                                                   #
    # ------------------------------------------------------------------ #

    async def process_message(
        self,
        user_input: str,
        conversation_id: Optional[str],
        user_id: str,
        db: Session,
        reference_date: Optional[datetime] = None
    ) -> dict:
        """
        Process a user message through the assistant workflow:

        1. Load or create conversation; persist the user message.
        2. Retrieve conversation history for context.
        3. Send message + history to the LLM for unified understanding.
        4. Route based on intent: direct response, flight search, or followup.
        5. Persist the assistant response and return.
        """
        if reference_date is None:
            reference_date = datetime.now()

        logger.info(f"Processing message: {user_input}")

        # --- conversation management (unchanged) ---
        if conversation_id:
            conversation = self.conversation_service.get_conversation(conversation_id, user_id)
            if not conversation:
                conversation = self.conversation_service.create_conversation(user_id)
        else:
            conversation = self.conversation_service.create_conversation(user_id)

        self.conversation_service.add_user_message(conversation.id, user_input)

        # Retrieve expanded history for better context
        conversation_history = self.conversation_service.get_conversation_messages(
            conversation.id, limit=20
        )

        # --- special case: user preferences (requires DB, not LLM) ---
        normalized_lower = user_input.lower().strip()
        if re.search(r"\b(my|our) flight preferences\b|\bwhat are my preferences\b", normalized_lower):
            preference = get_preference(db, user_id)
            if not preference:
                return self._save_response(
                    conversation.id,
                    "You don't have saved flight preferences yet. "
                    "You can set them from your preferences page."
                )
            return self._save_response(
                conversation.id,
                f"Your saved preferences are cabin {preference.preferred_cabin or 'not set'}, "
                f"currency {preference.preferred_currency or 'not set'}, "
                f"airport {preference.preferred_airport or 'not set'}, "
                f"and travel time {preference.preferred_time or 'not set'}."
            )

        # --- LLM-based understanding ---
        try:
            understanding = await self._understand_message(
                user_input, conversation_history, reference_date
            )
        except Exception as e:
            logger.error(f"LLM understanding failed: {e}")
            return self._save_response(
                conversation.id,
                "I'm having trouble processing that right now. "
                "Could you try rephrasing your question?"
            )

        intent = understanding.get("intent", "general")
        response_text = understanding.get("response", "")
        needs_search = understanding.get("needs_flight_search", False)
        flight_params = understanding.get("flight_params") or {}

        # --- route based on understanding ---

        # 1. Non-flight intents → return the LLM's contextual response
        if intent in ("greeting", "capabilities", "general", "general_flight_info") and not needs_search:
            if response_text:
                return self._save_response(conversation.id, response_text)
            return self._save_response(
                conversation.id,
                "I'm here to help! Ask me about flights, travel planning, or anything else."
            )

        # 2. Flight followup (cheapest? compare? recommend?)
        if intent == "flight_followup":
            return await self._handle_flight_followup(
                conversation.id, user_input, flight_params,
                conversation_history, user_id, db, response_text
            )

        # 3. Flight search
        if intent == "flight_search" or needs_search:
            return await self._handle_flight_search(
                conversation.id, user_input, flight_params,
                conversation_history, user_id, db, reference_date
            )

        # 4. Fallback — use the LLM response if available
        if response_text:
            return self._save_response(conversation.id, response_text)
        return self._save_response(
            conversation.id,
            "I'm here to help with flights, travel planning, and general questions. "
            "What would you like to know?"
        )

    # ------------------------------------------------------------------ #
    #  LLM-based unified understanding                                    #
    # ------------------------------------------------------------------ #

    async def _understand_message(
        self, user_input: str, conversation_history: List[Message],
        reference_date: datetime
    ) -> dict:
        """Call the LLM with a unified prompt to understand the user's
        current message in the context of conversation history."""
        prompt = self._build_unified_prompt(user_input, conversation_history, reference_date)
        from app.ai.llm import generate_structured
        raw = await generate_structured(prompt)

        # Attempt JSON parse
        try:
            return json.loads(raw.strip())
        except json.JSONDecodeError:
            pass
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and start < end:
            try:
                return json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                pass
        # Complete parse failure — treat raw text as a general response
        return {
            "intent": "general",
            "response": raw.strip() if raw.strip() else "",
            "needs_flight_search": False,
            "flight_params": {},
        }

    def _build_unified_prompt(
        self, user_input: str, conversation_history: List[Message],
        reference_date: datetime
    ) -> str:
        """Build the comprehensive prompt that the LLM uses to understand
        intent, extract flight params, and generate a response."""
        # Exclude the current user message from history (it's already in user_input)
        history_str = self._format_conversation_history(conversation_history[:-1])
        ref_date = reference_date.strftime("%Y-%m-%d")

        return (
            "You are an AI Flight Assistant for the AI Flight Intelligence application.\n\n"
            "YOUR CAPABILITIES:\n"
            "- Search for flights between airports (when the user explicitly asks)\n"
            "- Compare flight options (cheapest, fastest, best value) from search results\n"
            "- Answer general travel and aviation questions\n"
            "- Answer general knowledge questions on any topic\n"
            "- Explain flight terminology (nonstop, layover, cabin class, etc.)\n"
            "- Help users plan trips\n"
            "- Remember and recall conversation context\n\n"
            "CONVERSATION HISTORY:\n"
            f"{history_str}\n\n"
            f'CURRENT USER MESSAGE: "{user_input}"\n'
            f"TODAY'S DATE: {ref_date}\n\n"
            "TASK: Understand the user's current message in the context of the conversation "
            "history and provide an appropriate response.\n\n"
            "Return a JSON object with exactly these fields:\n"
            "{\n"
            '  "intent": "<one of: greeting, capabilities, flight_search, flight_followup, general_flight_info, general>",\n'
            '  "response": "<your natural language response to the user>",\n'
            '  "needs_flight_search": <true or false>,\n'
            '  "flight_params": {\n'
            '    "origin": "<IATA code or null>",\n'
            '    "destination": "<IATA code or null>",\n'
            '    "departure_date": "<YYYY-MM-DD or null>"\n'
            "  }\n"
            "}\n\n"
            "INTENT DEFINITIONS:\n"
            '- "greeting": The user is greeting you (hi, hello, hey, good morning, etc.)\n'
            '- "capabilities": The user is asking what you can do or how you can help\n'
            '- "flight_search": The user is explicitly requesting to find, search, or show flights '
            "for a route, OR is continuing a flight booking flow by providing missing information "
            "(e.g. giving a date after being asked for one)\n"
            '- "flight_followup": The user is asking about previously discussed flights — which is '
            "cheapest, compare options, recommend, which airline is best for that route, etc. "
            "Set needs_flight_search=true and include the flight_params from conversation context.\n"
            '- "general_flight_info": The user is asking a general travel/aviation question (best time '
            "to travel, which airlines fly a route, what does nonstop mean, etc.) — NOT a flight search\n"
            '- "general": Any other question — general knowledge, unrelated topics, conversation recall, etc.\n\n'
            "CRITICAL RULES:\n"
            "1. ALWAYS PRIORITIZE THE CURRENT MESSAGE over conversation history. "
            "History is context, not a command.\n"
            "2. If the user asks a general question (\"What is Python?\", \"What is the capital of France?\", "
            "\"Explain REST APIs\"), answer it directly. Set intent=\"general\". "
            "Do NOT ask for flight details.\n"
            "3. If the user asks about your capabilities, explain them. Set intent=\"capabilities\".\n"
            "4. If the user greets you, respond warmly and briefly mention you can help with flights "
            "and general questions. Set intent=\"greeting\".\n"
            '5. "What is the best time to travel to Paris?" is "general_flight_info", NOT "flight_search". '
            "Answer with general travel advice.\n"
            '6. "Which airlines fly from X to Y?" is "general_flight_info", NOT "flight_search".\n'
            '7. Set intent="flight_search" ONLY when the user explicitly wants to find/search/show '
            "available flights, OR is providing missing information (like a date) to complete a "
            "flight search that was started earlier in the conversation.\n"
            "8. For flight_search, extract flight_params from the CURRENT message AND relevant "
            "conversation history. Use IATA airport codes (HYD=Hyderabad, DEL=Delhi, BLR=Bangalore/Bengaluru, "
            "BOM=Mumbai, MAA=Chennai, LHR=London Heathrow, CDG=Paris, JFK=New York JFK, SFO=San Francisco, "
            "DXB=Dubai, SIN=Singapore, NRT=Tokyo Narita, etc.).\n"
            "9. If the user provides a date after being asked for one in a flight context, "
            'set intent="flight_search" and carry forward origin/destination from history into flight_params.\n'
            "10. If the user changes topics (asks about something unrelated after discussing flights), "
            'follow the new topic. Set intent="general". Do NOT force flight context.\n'
            "11. If the user returns to a previous flight topic (\"back to my Delhi flight\", "
            "\"my HYD to DEL trip\"), restore that context from the conversation history. "
            'Set intent="flight_followup" and include the flight_params from the earlier discussion.\n'
            "12. For flight_followup questions like \"which is cheapest?\", \"compare the options\", "
            "\"which airline is best\", \"which flight was cheapest\": set needs_flight_search=true "
            "and include the relevant flight_params from conversation history.\n"
            "13. For questions about conversation context (\"what was my route?\", \"what date did I "
            "give you?\", \"summarize my flight request\"), answer directly from the conversation "
            'history. Set intent="general".\n'
            "14. NEVER ask for origin/destination/date when the user is asking a non-flight question.\n"
            "15. If the user says something like \"I want to travel from HYD to DEL\" without "
            "explicitly asking to search, treat it as the start of a flight search — acknowledge "
            'the plan and ask for missing info. Set intent="flight_search".\n'
            f"16. Resolve relative dates using today's date ({ref_date}). "
            "\"tomorrow\" = the day after today. \"next month\" = the following calendar month. "
            "Parse dates like \"29-09-2026\" as September 29, 2026 (DD-MM-YYYY format).\n"
            "17. Keep responses concise, conversational, and directly relevant to the question.\n"
            "18. Do NOT dump flight listings. Only set needs_flight_search=true when a search "
            "is genuinely needed to answer the user's question.\n"
            "19. For jokes, stories, explanations, or any non-flight question, just answer naturally.\n\n"
            "IMPORTANT: Output ONLY the JSON object. No markdown, no code fences, no extra text."
        )

    # ------------------------------------------------------------------ #
    #  Flight search handler                                              #
    # ------------------------------------------------------------------ #

    async def _handle_flight_search(
        self, conversation_id: str, user_input: str, flight_params: dict,
        conversation_history: List[Message], user_id: str, db: Session,
        reference_date: datetime
    ) -> dict:
        """Execute a flight search after extracting / merging parameters."""
        # Parameters from LLM understanding
        origin = flight_params.get("origin")
        destination = flight_params.get("destination")
        dep_date_str = flight_params.get("departure_date")
        dep_date = self._parse_iso_date(dep_date_str)

        # Fallback: regex extraction from current message
        regex_origin, regex_dest, regex_date = self._parse_search_details(user_input)

        # Fallback: accumulated context from conversation history
        previous = self._latest_search_context(conversation_history[:-1])

        # Merge priority: LLM > regex > history
        final_origin = origin or regex_origin or (previous.origin if previous else None)
        final_dest = destination or regex_dest or (previous.destination if previous else None)
        final_date = dep_date or regex_date or (previous.departure_date if previous else None)

        flight_intent = FlightIntent(
            intent="FLIGHT_SEARCH",
            origin=final_origin,
            destination=final_dest,
            departure_date=final_date,
        )

        # Check for missing required fields
        missing = self._get_missing_required_fields(flight_intent)
        if missing:
            clarification_text, clarification_questions = self._generate_clarification(
                flight_intent, missing
            )
            self.conversation_service.add_assistant_message(conversation_id, clarification_text)
            self._update_conversation_timestamp(conversation_id)
            return {
                "message": clarification_text,
                "conversation_id": conversation_id,
                "flight_results": None,
                "requires_clarification": True,
                "clarification_questions": clarification_questions,
            }

        # All required parameters present — search
        try:
            search_request = self._convert_to_search_request(flight_intent, user_id, db)
            flight_results = await search_flights(search_request)
            response_text = await self._generate_response(
                user_input, flight_intent, flight_results
            )
            self.conversation_service.add_assistant_message(conversation_id, response_text)
            self._update_conversation_timestamp(conversation_id)
            return {
                "message": response_text,
                "conversation_id": conversation_id,
                "flight_results": flight_results,
                "requires_clarification": False,
                "clarification_questions": None,
            }
        except Exception as e:
            logger.error(f"Flight search failed: {e}")
            return self._save_response(
                conversation_id,
                "I'm unable to retrieve live flight information right now. "
                "Please try again later."
            )

    # ------------------------------------------------------------------ #
    #  Flight followup handler                                            #
    # ------------------------------------------------------------------ #

    async def _handle_flight_followup(
        self, conversation_id: str, user_input: str, flight_params: dict,
        conversation_history: List[Message], user_id: str, db: Session,
        fallback_response: str
    ) -> dict:
        """Handle followup questions about previously discussed flights
        (e.g. which is cheapest, compare, recommend)."""
        origin = flight_params.get("origin")
        destination = flight_params.get("destination")
        dep_date_str = flight_params.get("departure_date")
        dep_date = self._parse_iso_date(dep_date_str)

        # Supplement from conversation history if the LLM missed anything
        if not origin or not destination:
            previous = self._latest_search_context(conversation_history[:-1])
            if previous:
                origin = origin or previous.origin
                destination = destination or previous.destination
                if not dep_date and previous.departure_date:
                    dep_date = previous.departure_date

        if not (origin and destination and dep_date):
            # Cannot determine search context
            if fallback_response:
                return self._save_response(conversation_id, fallback_response)
            return self._save_response(
                conversation_id,
                "I'd need the flight details to answer that. "
                "Could you tell me the route and date you're interested in?"
            )

        search_intent = FlightIntent(
            intent="FLIGHT_SEARCH",
            origin=origin,
            destination=destination,
            departure_date=dep_date,
        )

        try:
            results = await search_flights(
                self._convert_to_search_request(search_intent, user_id, db)
            )
            if not results:
                return self._save_response(
                    conversation_id,
                    f"I couldn't find flights from {origin} to {destination} for that date."
                )

            # Build a concise summary for the LLM to reason over
            flights_lines = []
            for f in results[:7]:
                flights_lines.append(
                    f"- {f.airline} {f.flight_number}: {f.price:g} {f.currency}, "
                    f"{f.duration} min, {f.stops} stop(s)"
                )
            flights_text = "\n".join(flights_lines)
            date_label = dep_date.strftime("%B %d, %Y") if dep_date else "the requested date"

            followup_prompt = (
                "You are an AI Flight Assistant. The user previously searched flights "
                f"from {origin} to {destination} on {date_label}.\n\n"
                f"Available flights:\n{flights_text}\n\n"
                f'User\'s question: "{user_input}"\n\n'
                "Answer the user's specific question concisely based on these flight options. "
                "Do not list all flights unless specifically asked to. "
                "Focus on answering the exact question. Be conversational and helpful. "
                "Only use data from the flight options shown above — never invent airlines, "
                "prices, or flight numbers."
            )

            from app.ai.llm import generate_structured
            llm_answer = await generate_structured(followup_prompt)
            return self._save_response(conversation_id, llm_answer.strip())

        except Exception as e:
            logger.error(f"Flight followup failed: {e}")
            if fallback_response:
                return self._save_response(conversation_id, fallback_response)
            return self._save_response(
                conversation_id,
                "I couldn't access the flight options to answer that right now."
            )

    # ------------------------------------------------------------------ #
    #  Response helpers                                                   #
    # ------------------------------------------------------------------ #

    def _save_response(self, conversation_id: str, response_text: str) -> dict:
        self.conversation_service.add_assistant_message(conversation_id, response_text)
        self._update_conversation_timestamp(conversation_id)
        return {
            "message": response_text,
            "conversation_id": conversation_id,
            "flight_results": None,
            "requires_clarification": False,
            "clarification_questions": None,
        }

    def _format_conversation_history(self, messages: List[Message]) -> str:
        """Format a list of messages into a string for the prompt."""
        if not messages:
            return "No previous conversation."
        history_lines = []
        for msg in messages:
            role = msg.role.upper()
            content = msg.content
            history_lines.append(f"{role}: {content}")
        return "\n".join(history_lines)

    # ------------------------------------------------------------------ #
    #  Flight context extraction from history (fallback)                  #
    # ------------------------------------------------------------------ #

    def _latest_search_context(self, messages: List[Message]) -> Optional[FlightIntent]:
        """Accumulate the most recent flight search context by scanning
        user messages in reverse order.  Picks up origin, destination, and
        date from separate messages if necessary."""
        origin = None
        destination = None
        departure_date = None

        for message in reversed(messages):
            if message.role != "user":
                continue
            o, d, dt = self._parse_search_details(message.content)
            if o and not origin:
                origin = o
            if d and not destination:
                destination = d
            if dt and not departure_date:
                departure_date = dt
            if origin and destination and departure_date:
                break

        if origin or destination or departure_date:
            return FlightIntent(
                intent="FLIGHT_SEARCH",
                origin=origin,
                destination=destination,
                departure_date=departure_date,
            )
        return None

    # ------------------------------------------------------------------ #
    #  Text parsing utilities                                             #
    # ------------------------------------------------------------------ #

    def _parse_search_details(self, text: str) -> Tuple[Optional[str], Optional[str], Optional[datetime]]:
        normalized = text.lower()
        airports = {
            "hyderabad": "HYD", "hyd": "HYD",
            "bangalore": "BLR", "bengaluru": "BLR", "blr": "BLR",
            "delhi": "DEL", "del": "DEL",
            "mumbai": "BOM", "bom": "BOM",
            "chennai": "MAA", "maa": "MAA",
            "london": "LHR", "lhr": "LHR",
        }
        origin = destination = None
        route = re.search(
            r"\bfrom\s+([a-z][a-z .-]*?)(?:\s+to\s+|\s+on\s+|\s+for\s+|$)", normalized
        )
        if route:
            origin = self._airport_code(route.group(1), airports)
            destination_match = re.search(
                r"\bto\s+([a-z][a-z .-]*?)(?:\s+on\s+|\s+for\s+|\s+at\s+|$)", normalized
            )
            if destination_match:
                destination = self._airport_code(destination_match.group(1), airports)
        if not origin:
            code_match = re.search(r"\b([a-z]{3})\s*(?:-|to)\s*([a-z]{3})\b", normalized)
            if code_match:
                origin, destination = code_match.group(1).upper(), code_match.group(2).upper()
        return origin, destination, self._parse_date(normalized)

    @staticmethod
    def _airport_code(value: str, airports: dict) -> Optional[str]:
        words = value.strip().split()
        for size in range(min(2, len(words)), 0, -1):
            candidate = " ".join(words[:size]).strip(" ,.")
            if candidate in airports:
                return airports[candidate]
        return None

    @staticmethod
    def _parse_date(text: str) -> Optional[datetime]:
        reference = datetime.now()
        if "tomorrow" in text:
            return reference.replace(hour=0, minute=0, second=0, microsecond=0) + __import__("datetime").timedelta(days=1)
        patterns = [
            (r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b", "%d-%m-%Y"),
            (r"\b([a-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?\b", None),
        ]
        match = re.search(patterns[0][0], text)
        if match:
            try:
                return datetime.strptime("-".join(match.groups()), patterns[0][1])
            except ValueError:
                return None
        match = re.search(patterns[1][0], text)
        if match:
            month, day, year = match.groups()
            try:
                return datetime.strptime(f"{month} {day} {year or reference.year}", "%B %d %Y")
            except ValueError:
                try:
                    return datetime.strptime(f"{month} {day} {year or reference.year}", "%b %d %Y")
                except ValueError:
                    return None
        return None

    @staticmethod
    def _parse_iso_date(date_str: Optional[str]) -> Optional[datetime]:
        """Parse a YYYY-MM-DD string returned by the LLM."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return None

    # ------------------------------------------------------------------ #
    #  Missing-field handling                                              #
    # ------------------------------------------------------------------ #

    def _get_missing_required_fields(self, flight_intent: FlightIntent) -> List[str]:
        """Check which required fields are missing for flight search."""
        missing = []
        if not flight_intent.origin:
            missing.append("origin")
        if not flight_intent.destination:
            missing.append("destination")
        if not flight_intent.departure_date:
            missing.append("departure_date")
        return missing

    def _generate_clarification(
        self, flight_intent: FlightIntent, missing_fields: List[str]
    ) -> tuple[str, List[str]]:
        """Generate clarification questions for missing fields."""
        questions = []
        if "origin" in missing_fields:
            questions.append("What city or airport are you flying from?")
        if "destination" in missing_fields:
            questions.append("Where would you like to fly to?")
        if "departure_date" in missing_fields:
            questions.append("When would you like to travel?")

        route = f" from {flight_intent.origin}" if flight_intent.origin else ""
        route += f" to {flight_intent.destination}" if flight_intent.destination else ""
        if missing_fields == ["departure_date"]:
            clarification_text = f"Sure — I can help you find flights{route}. What date would you like to travel?"
        elif len(questions) == 1:
            clarification_text = questions[0]
        elif len(questions) == 2:
            clarification_text = f"{questions[0]} And {questions[1].lower()}"
        else:
            clarification_text = " ".join(questions[:-1]) + f", and {questions[-1].lower()}"

        return clarification_text, questions

    # ------------------------------------------------------------------ #
    #  Flight search request conversion                                   #
    # ------------------------------------------------------------------ #

    def _convert_to_search_request(
        self, flight_intent: FlightIntent, user_id: str, db: Session
    ) -> FlightSearchRequest:
        """Convert FlightIntent to FlightSearchRequest."""
        passengers = flight_intent.passengers if flight_intent.passengers else 1
        cabin_class = flight_intent.cabin if flight_intent.cabin else "ECONOMY"
        user_preference = get_preference(db, user_id)
        currency = (
            user_preference.preferred_currency
            if user_preference and user_preference.preferred_currency
            else "USD"
        )
        return FlightSearchRequest(
            origin=flight_intent.origin.upper(),
            destination=flight_intent.destination.upper(),
            departure_date=flight_intent.departure_date,
            return_date=flight_intent.return_date,
            passengers=passengers,
            cabin_class=cabin_class,
            currency=currency,
        )

    # ------------------------------------------------------------------ #
    #  Flight result response generation                                  #
    # ------------------------------------------------------------------ #

    async def _generate_response(
        self,
        user_input: str,
        flight_intent: FlightIntent,
        flight_results: List[FlightResponse]
    ) -> str:
        """Generate natural language response from flight results."""
        try:
            if flight_results:
                cheapest = min(flight_results, key=lambda flight: flight.price)
                fastest = min(flight_results, key=lambda flight: flight.duration)
                nonstop_count = sum(1 for flight in flight_results if flight.stops == 0)
                date_text = (
                    f"{flight_intent.departure_date.strftime('%B')} {flight_intent.departure_date.day}, "
                    f"{flight_intent.departure_date.year}"
                    if flight_intent.departure_date else "that date"
                )
                return (
                    f"I found {len(flight_results)} flight options from {flight_intent.origin} to {flight_intent.destination} "
                    f"for {date_text}. The cheapest is {cheapest.airline} {cheapest.flight_number} at "
                    f"{cheapest.price:g} {cheapest.currency}; the fastest takes {fastest.duration} minutes. "
                    f"{nonstop_count} option(s) are nonstop. The full results are available on the Flights page, "
                    "and I can help you compare or choose one."
                )
            # No results — use LLM to generate a helpful no-results message
            search_info = {
                "origin": flight_intent.origin,
                "destination": flight_intent.destination,
                "departure_date": flight_intent.departure_date.isoformat() if flight_intent.departure_date else None,
                "passengers": flight_intent.passengers,
                "cabin": flight_intent.cabin,
            }
            flights_data: List[dict] = []
            prompt = self._create_response_prompt(
                user_input, search_info, flights_data, len(flight_results)
            )
            from app.ai.llm import generate_structured
            llm_response = await generate_structured(prompt)
            response_text = llm_response.strip()
            if not response_text:
                raise Exception("Empty response from LLM")
            return response_text
        except Exception as e:
            logger.error(f"Response generation failed: {str(e)}")
            if len(flight_results) == 0:
                origin = flight_intent.origin or "unknown"
                destination = flight_intent.destination or "unknown"
                date_str = ""
                if flight_intent.departure_date:
                    date_str = flight_intent.departure_date.strftime("%B %d, %Y")
                return f"I couldn't find any flights from {origin} to {destination}{' on ' + date_str if date_str else ''}."
            else:
                origin = flight_intent.origin or "unknown"
                destination = flight_intent.destination or "unknown"
                return f"I found {len(flight_results)} flight options from {origin} to {destination}."

    def _create_response_prompt(
        self,
        user_input: str,
        search_info: dict,
        flights_data: List[dict],
        total_results: int
    ) -> str:
        """Create prompt for response generation LLM."""
        prompt = f"""
You are an AI flight assistant. Generate a helpful, conversational response based on the verified flight search results provided below.

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
- Only use information provided in the flight results above
- Never invent airline names, flight numbers, prices, or times
- Do not mention baggage, cancellation policies, or other details not in the data
- Keep the response conversational and helpful
- If no flights were found, suggest trying different dates or nearby airports
- If flights were found, summarize the options naturally

Response:"""
        return prompt.strip()

    # ------------------------------------------------------------------ #
    #  Timestamp management                                               #
    # ------------------------------------------------------------------ #

    def _update_conversation_timestamp(self, conversation_id: str) -> None:
        """Update the conversation's updated_at timestamp."""
        self.conversation_service.update_conversation_timestamp(conversation_id)