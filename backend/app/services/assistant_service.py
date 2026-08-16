from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import date, timedelta
from typing import Any
from uuid import UUID

from app.ai.llm_provider import FallbackProvider, LLMProvider, get_system_prompt
from app.exceptions.base import NotFoundException
from app.repositories.chat_repository import ChatRepository
from app.schemas.assistant import (
    ChatMessageItem,
    ChatResponse,
    ChatResponseData,
    ConversationDetailResponse,
    ConversationItem,
    ConversationListResponse,
    ConversationWithMessages,
    DeleteConversationResponse,
)
from app.schemas.flight import FlightSearchParams, TravelClass
from app.services.flight_service import FlightService

logger = logging.getLogger(__name__)

# Maximum number of previous messages sent to the LLM for context
_CONTEXT_WINDOW = 10

AIRPORT_MAP: dict[str, str] = {
    "hyderabad": "HYD", "hyd": "HYD", "secunderabad": "HYD",
    "mumbai": "BOM", "bom": "BOM", "bombay": "BOM",
    "delhi": "DEL", "del": "DEL", "new delhi": "DEL",
    "dubai": "DXB", "dxb": "DXB",
    "bangalore": "BLR", "bengaluru": "BLR", "blr": "BLR",
    "chennai": "MAA", "maa": "MAA", "madras": "MAA",
    "singapore": "SIN", "sin": "SIN",
    "london": "LHR", "lhr": "LHR",
    "frankfurt": "FRA", "fra": "FRA",
    "san francisco": "SFO", "sfo": "SFO",
    "new york": "JFK", "jfk": "JFK",
    "bangkok": "BKK", "bkk": "BKK",
}


def extract_flight_context(
    messages: list[dict[str, str]], today: date | None = None
) -> dict[str, Any]:
    """Extract flight search intent and parameters from conversation history."""
    if today is None:
        today = date.today()

    context: dict[str, Any] = {
        "origin": None,
        "destination": None,
        "departure_date": None,
        "time_preference": None,
        "target_hour": None,
    }

    user_texts = [m["content"] for m in messages if m.get("role") == "user"]
    if not user_texts:
        return context

    full_text = " ".join(user_texts).lower()
    last_user_text = user_texts[-1].strip().lower()

    # Do not trigger flight search for simple greetings or general inquiries
    greetings = {
        "hi", "hello", "hey", "hii", "good morning", "good afternoon",
        "good evening", "thanks", "thank you", "what can you do?", "help"
    }
    if last_user_text in greetings:
        return context

    # 1. Time preference and target hour extraction
    pm_rgx = r"\b([1-9]|1[0-2])\s*(?::\d{2})?\s*pm\b"
    if re.search(pm_rgx, full_text) or "7pm" in full_text:
        context["time_preference"] = "evening"
        pm_match = re.search(pm_rgx, full_text)
        if pm_match:
            hr = int(pm_match.group(1))
            context["target_hour"] = hr + 12 if hr < 12 else 12
        elif "7pm" in full_text:
            context["target_hour"] = 19
    elif re.search(r"\b(mrng|morning|am)\b", full_text):
        context["time_preference"] = "morning"
        am_match = re.search(r"\b([1-9]|1[0-2])\s*(?::\d{2})?\s*am\b", full_text)
        if am_match:
            context["target_hour"] = int(am_match.group(1)) % 12
    elif re.search(r"\b(aftn|afternoon)\b", full_text):
        context["time_preference"] = "afternoon"
    elif re.search(r"\b(eve|evening|night)\b", full_text):
        context["time_preference"] = "evening"

    # 2. Date extraction
    if re.search(r"\b(tommorow|tomorrow|tmrw|tomm)\b", full_text):
        context["departure_date"] = (today + timedelta(days=1)).isoformat()
    elif re.search(r"\b(today)\b", full_text):
        context["departure_date"] = today.isoformat()
    else:
        match_weekday = re.search(
            r"\bnext\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
            full_text,
        )
        if match_weekday:
            target_name = match_weekday.group(1)
            weekdays = [
                "monday", "tuesday", "wednesday", "thursday",
                "friday", "saturday", "sunday"
            ]
            target_idx = weekdays.index(target_name)
            current_idx = today.weekday()
            days_ahead = target_idx - current_idx
            if days_ahead <= 0:
                days_ahead += 7
            context["departure_date"] = (
                today + timedelta(days=days_ahead)
            ).isoformat()
        else:
            match_iso = re.search(r"\b\d{4}-\d{2}-\d{2}\b", full_text)
            if match_iso:
                context["departure_date"] = match_iso.group(0)

    # 3. Airport extraction
    # Check explicit multi-city patterns first
    for name1, code1 in AIRPORT_MAP.items():
        for name2, code2 in AIRPORT_MAP.items():
            if code1 == code2:
                continue
            n1_esc = re.escape(name1)
            n2_esc = re.escape(name2)
            pat_from_to = r"\bfrom\s+" + n1_esc + r"\s+to\s+" + n2_esc + r"\b"
            pat_dest_from = (
                r"\b(?:go\s+|fly\s+)?" + n1_esc + r"\s+from\s+" + n2_esc + r"\b"
            )
            pat_orig_to = r"\b" + n1_esc + r"\s+to\s+" + n2_esc + r"\b"

            if re.search(pat_from_to, full_text):
                context["origin"] = code1
                context["destination"] = code2
                break
            elif re.search(pat_dest_from, full_text):
                context["destination"] = code1
                context["origin"] = code2
                break
            elif re.search(pat_orig_to, full_text):
                context["origin"] = code1
                context["destination"] = code2
                break

    # Single-side pattern fallback
    if not context["origin"] or not context["destination"]:
        for name, code in AIRPORT_MAP.items():
            esc_n = re.escape(name)
            if (
                not context["origin"]
                and re.search(r"\bfrom\s+" + esc_n + r"\b", full_text)
            ):
                context["origin"] = code
            if (
                not context["destination"]
                and re.search(r"\bto\s+" + esc_n + r"\b", full_text)
            ):
                context["destination"] = code

    # Fallback to order of appearance for unassigned airport slots
    found_codes = []
    for word in re.findall(r"\b[a-z]{3,15}\b", full_text):
        if word in AIRPORT_MAP and AIRPORT_MAP[word] not in found_codes:
            found_codes.append(AIRPORT_MAP[word])

    if not context["origin"] and not context["destination"]:
        if len(found_codes) >= 2:
            context["origin"] = found_codes[0]
            context["destination"] = found_codes[1]
    elif context["origin"] and not context["destination"]:
        remaining = [c for c in found_codes if c != context["origin"]]
        if remaining:
            context["destination"] = remaining[0]
    elif context["destination"] and not context["origin"]:
        remaining = [c for c in found_codes if c != context["destination"]]
        if remaining:
            context["origin"] = remaining[0]

    if context["origin"] == context["destination"]:
        context["destination"] = None

    return context


class AssistantService:
    """Business logic for the AI travel assistant.

    Responsibilities
    ----------------
    - Create / continue conversation threads.
    - Build the message history context window for the LLM.
    - Perform flight searches when parameters exist across multi-turn context.
    - Persist user and assistant messages.
    """

    def __init__(
        self,
        chat_repo: ChatRepository,
        llm_provider: LLMProvider,
        flight_service: FlightService | None = None,
    ) -> None:
        self._chat_repo = chat_repo
        self._llm = llm_provider
        self._flight_service = flight_service

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------

    async def chat(
        self,
        *,
        user_id: UUID,
        message: str,
        conversation_id: UUID | None,
    ) -> ChatResponse:
        """Process a user message and return the assistant reply."""
        # Resolve or create conversation
        t0 = time.monotonic()
        logger.info(
            "[STEP 2] RESOLVING CONVERSATION START | conv_id=%s", conversation_id
        )
        if conversation_id is not None:
            conversation = self._chat_repo.get_conversation(
                conversation_id=conversation_id, user_id=user_id
            )
            if conversation is None:
                raise NotFoundException(message="Conversation not found.")
        else:
            title = message[:60].strip() or "New Conversation"
            conversation = self._chat_repo.create_conversation(
                user_id=user_id, title=title
            )
        elapsed_res = (time.monotonic() - t0) * 1000
        logger.info(
            "[STEP 2] RESOLVING CONVERSATION COMPLETED | elapsed=%.2fms", elapsed_res
        )

        # Persist user message
        t1 = time.monotonic()
        logger.info("[STEP 3] PERSIST USER MESSAGE START")
        self._chat_repo.add_message(
            conversation_id=conversation.id,
            role="user",
            content=message,
        )
        elapsed_usr = (time.monotonic() - t1) * 1000
        logger.info(
            "[STEP 3] PERSIST USER MESSAGE COMPLETED | elapsed=%.2fms", elapsed_usr
        )

        # Build context window for LLM
        t2 = time.monotonic()
        logger.info("[STEP 4] BUILDING LLM CONTEXT START")
        history = self._chat_repo.get_messages(
            conversation_id=conversation.id, limit=_CONTEXT_WINDOW + 1
        )
        raw_messages = [{"role": msg.role, "content": msg.content} for msg in history]

        # Extract multi-turn flight search intent
        flight_ctx = extract_flight_context(raw_messages)
        system_prompt = get_system_prompt()

        search_executed = False
        flight_search_results: list[Any] = []
        reply_override: str | None = None

        if (
            self._flight_service is not None
            and flight_ctx["origin"]
            and flight_ctx["destination"]
            and flight_ctx["departure_date"]
        ):
            search_executed = True
            orig = flight_ctx["origin"]
            dest = flight_ctx["destination"]
            dep_dt = flight_ctx["departure_date"]
            try:
                dep_date = date.fromisoformat(dep_dt)
                search_params = FlightSearchParams(
                    origin=orig,
                    destination=dest,
                    departure_date=dep_date,
                    travel_class=TravelClass.ECONOMY,
                    adults=1,
                    children=0,
                    infants=0,
                    non_stop=False,
                    currency="USD",
                    max_results=5,
                )
                results, _ = await self._flight_service.search_flights(
                    params=search_params, user_id=user_id
                )
                flight_search_results = results

                if not results:
                    reply_override = (
                        f"No matching flights were found for {orig} → {dest} "
                        f"on {dep_dt}."
                    )
                else:
                    # Sort by target hour or time preference
                    target_hr = flight_ctx.get("target_hour")
                    time_pref = flight_ctx.get("time_preference")

                    if target_hr is not None:
                        results.sort(
                            key=lambda r: (
                                abs(r.departure_time.hour - target_hr),
                                r.departure_time,
                            )
                        )
                    elif time_pref == "morning":
                        results.sort(
                            key=lambda r: (
                                0 if 5 <= r.departure_time.hour < 12 else 1,
                                r.departure_time,
                            )
                        )
                    elif time_pref == "afternoon":
                        results.sort(
                            key=lambda r: (
                                0 if 12 <= r.departure_time.hour < 17 else 1,
                                r.departure_time,
                            )
                        )
                    elif time_pref == "evening":
                        results.sort(
                            key=lambda r: (
                                0 if r.departure_time.hour >= 17 else 1,
                                r.departure_time,
                            )
                        )

                    offer_lines = []
                    for offer in results[:3]:
                        dep_str = offer.departure_time.strftime("%H:%M")
                        arr_str = offer.arrival_time.strftime("%H:%M")
                        seg = offer.segments[0]
                        airline = seg.airline_name or seg.airline
                        flight_num = seg.flight_number
                        offer_lines.append(
                            f"- Flight {flight_num} ({airline}): Departs "
                            f"{dep_str}, Arrives {arr_str}, "
                            f"Price: {offer.currency} {offer.price:.2f}"
                        )

                    flight_summary = "\n".join(offer_lines)
                    pref_val = time_pref or (
                        f"{target_hr}:00" if target_hr is not None else None
                    )
                    time_note = (
                        f" (Filtered for {pref_val} departures)" if pref_val else ""
                    )
                    system_prompt += (
                        f"\n\nCRITICAL INSTRUCTION: Real flight search results "
                        f"from our database are provided below. You MUST present "
                        f"these exact flight results to the user clearly. Do NOT "
                        f"invent flight numbers, airlines, or prices. Do NOT give "
                        f"generic travel advice instead of presenting these "
                        f"real flight options.\n\n"
                        f"REAL FLIGHT SEARCH RESULTS for {orig} -> {dest} "
                        f"on {dep_dt}{time_note}:\n"
                        f"{flight_summary}\n\n"
                        "Present these real flight options clearly to the user."
                    )
            except Exception as exc:
                logger.warning("Assistant flight search execution failed: %s", exc)
                reply_override = (
                    f"I couldn't complete the flight search right now for "
                    f"{orig} → {dest} on {dep_dt}. Please try again."
                )
        elif (
            flight_ctx["origin"]
            and flight_ctx["destination"]
            and not flight_ctx["departure_date"]
        ):
            orig = flight_ctx["origin"]
            dest = flight_ctx["destination"]
            system_prompt += (
                f"\n\nRoute understood: {orig} to {dest}. Departure date is missing. "
                f"Acknowledge the route from {orig} to {dest} and ask the user what "
                "date or time they would like to depart."
            )

        llm_messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            llm_messages.append({"role": msg.role, "content": msg.content})

        elapsed_ctx = (time.monotonic() - t2) * 1000
        logger.info(
            "[STEP 4] BUILDING LLM CONTEXT COMPLETED | msg_count=%d elapsed=%.2fms",
            len(llm_messages),
            elapsed_ctx,
        )

        # Call LLM or use override
        t3 = time.monotonic()
        if reply_override:
            reply = reply_override
            tokens = None
            logger.info("[STEP 5] FLIGHT SEARCH OVERRIDE USED | reply=%s", reply)
        else:
            logger.info(
                "[STEP 5] CALLING LLM PROVIDER START | provider=%s",
                type(self._llm).__name__,
            )
            try:
                reply, tokens = await asyncio.wait_for(
                    self._llm.complete(messages=llm_messages),
                    timeout=3.0,
                )
                elapsed_llm = (time.monotonic() - t3) * 1000
                logger.info(
                    "[STEP 6] LLM CALL COMPLETED | tokens=%s elapsed=%.2fms",
                    tokens,
                    elapsed_llm,
                )
                if search_executed and flight_search_results:
                    bad_phrases = [
                        "google flights", "live booking feed", "live booking",
                        "don't have access to live", "don't have live",
                        "cannot search", "as an ai", "general travel tips"
                    ]
                    reply_lower = reply.lower()
                    contains_bad_phrase = any(p in reply_lower for p in bad_phrases)
                    has_flight_info = any(
                        offer.segments[0].flight_number.lower() in reply_lower
                        or offer.segments[0].airline.lower() in reply_lower
                        for offer in flight_search_results[:3]
                    )
                    if contains_bad_phrase or not has_flight_info:
                        pref_val = flight_ctx.get("time_preference") or (
                            f"{flight_ctx.get('target_hour')}:00"
                            if flight_ctx.get("target_hour") is not None
                            else None
                        )
                        time_note = (
                            f" (Filtered for {pref_val} departures)"
                            if pref_val else ""
                        )
                        offer_lines = []
                        for offer in flight_search_results[:3]:
                            seg = offer.segments[0]
                            al = seg.airline_name or seg.airline
                            fnum = seg.flight_number
                            dep = offer.departure_time.strftime("%H:%M")
                            arr = offer.arrival_time.strftime("%H:%M")
                            prc = f"{offer.currency} {offer.price:.2f}"
                            offer_lines.append(
                                f"- Flight {fnum} ({al}): Departs {dep}, "
                                f"Arrives {arr}, Price: {prc}"
                            )
                        orig_code = flight_ctx["origin"]
                        dest_code = flight_ctx["destination"]
                        dep_date_str = flight_ctx["departure_date"]
                        reply = (
                            f"Here are the available flights for {orig_code} → "
                            f"{dest_code} on {dep_date_str}{time_note}:\n"
                            + "\n".join(offer_lines)
                        )
            except Exception as exc:
                elapsed_err = (time.monotonic() - t3) * 1000
                logger.warning(
                    "[STEP 6 WARNING] LLM CALL FAILED/TIMED OUT after "
                    "%.2fms | error: %s",
                    elapsed_err,
                    exc,
                )
                tokens = None
                if search_executed and flight_search_results:
                    pref_val = flight_ctx.get("time_preference") or (
                        f"{flight_ctx.get('target_hour')}:00"
                        if flight_ctx.get("target_hour") is not None
                        else None
                    )
                    time_note = (
                        f" (Filtered for {pref_val} departures)"
                        if pref_val else ""
                    )
                    offer_lines = []
                    for offer in flight_search_results[:3]:
                        seg = offer.segments[0]
                        al = seg.airline_name or seg.airline
                        fnum = seg.flight_number
                        dep = offer.departure_time.strftime("%H:%M")
                        arr = offer.arrival_time.strftime("%H:%M")
                        prc = f"{offer.currency} {offer.price:.2f}"
                        offer_lines.append(
                            f"- Flight {fnum} ({al}): Departs {dep}, "
                            f"Arrives {arr}, Price: {prc}"
                        )
                    orig_code = flight_ctx["origin"]
                    dest_code = flight_ctx["destination"]
                    dep_date_str = flight_ctx["departure_date"]
                    reply = (
                        f"Here are the available flights for {orig_code} → "
                        f"{dest_code} on {dep_date_str}{time_note}:\n"
                        + "\n".join(offer_lines)
                    )
                else:
                    fallback = FallbackProvider()
                    reply, tokens = await fallback.complete(messages=llm_messages)

        # Persist assistant reply
        t4 = time.monotonic()
        logger.info("[STEP 8] DB PERSIST ASSISTANT REPLY START")
        self._chat_repo.add_message(
            conversation_id=conversation.id,
            role="assistant",
            content=reply,
            tokens_used=tokens,
        )
        self._chat_repo.touch_conversation(conversation_id=conversation.id)
        elapsed_ast = (time.monotonic() - t4) * 1000
        logger.info(
            "[STEP 8] DB PERSIST ASSISTANT REPLY COMPLETED | elapsed=%.2fms",
            elapsed_ast,
        )

        logger.info(
            "AssistantService.chat | user=%s conv=%s tokens=%s",
            user_id,
            conversation.id,
            tokens,
        )

        return ChatResponse(
            success=True,
            message="Reply generated successfully.",
            data=ChatResponseData(
                conversation_id=conversation.id,
                reply=reply,
                tokens_used=tokens,
            ),
        )

    # ------------------------------------------------------------------
    # Conversation management
    # ------------------------------------------------------------------

    def list_conversations(
        self,
        *,
        user_id: UUID,
        page: int,
        page_size: int,
    ) -> ConversationListResponse:
        """Return paginated conversation list for the user."""
        page = max(1, page)
        page_size = max(1, min(page_size, 50))
        offset = (page - 1) * page_size

        records, total = self._chat_repo.list_conversations(
            user_id=user_id, offset=offset, limit=page_size
        )

        items = [
            ConversationItem(
                id=c.id,
                title=c.title,
                is_active=c.is_active,
                created_at=c.created_at,
                updated_at=c.updated_at,
                message_count=self._chat_repo.count_messages(conversation_id=c.id),
            )
            for c in records
        ]

        return ConversationListResponse(
            success=True,
            message="Conversations retrieved successfully.",
            data=items,
            count=total,
        )

    def get_conversation(
        self,
        *,
        conversation_id: UUID,
        user_id: UUID,
    ) -> ConversationDetailResponse:
        """Return a conversation with its full message history."""
        conversation = self._chat_repo.get_conversation(
            conversation_id=conversation_id, user_id=user_id
        )
        if conversation is None:
            raise NotFoundException(message="Conversation not found.")

        messages = self._chat_repo.get_messages(
            conversation_id=conversation_id, limit=200
        )

        return ConversationDetailResponse(
            success=True,
            message="Conversation retrieved successfully.",
            data=ConversationWithMessages(
                id=conversation.id,
                title=conversation.title,
                is_active=conversation.is_active,
                created_at=conversation.created_at,
                messages=[
                    ChatMessageItem(
                        id=m.id,
                        role=m.role,
                        content=m.content,
                        created_at=m.created_at,
                    )
                    for m in messages
                ],
            ),
        )

    def delete_conversation(
        self,
        *,
        conversation_id: UUID,
        user_id: UUID,
    ) -> DeleteConversationResponse:
        """Delete a conversation and all its messages."""
        deleted = self._chat_repo.delete_conversation(
            conversation_id=conversation_id, user_id=user_id
        )
        if not deleted:
            raise NotFoundException(message="Conversation not found.")

        logger.info(
            "AssistantService.delete_conversation | user=%s conv=%s",
            user_id,
            conversation_id,
        )

        return DeleteConversationResponse(
            success=True,
            message="Conversation deleted successfully.",
        )
