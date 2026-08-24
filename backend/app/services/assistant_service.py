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


def is_affirmative(text: str) -> bool:
    t = text.strip().lower()
    affirmative_words = {
        "yes", "yeah", "yep", "sure", "ok", "okay", "please", "please search",
        "go ahead", "do it", "search", "confirm", "yes please", "yep please",
        "sounds good", "that works", "search flights", "find flights"
    }
    if t in affirmative_words or re.match(r"^(yes+|yeah+|yep+|sure|ok|okay|please)[.!?]*$", t):
        return True
    return False


def is_greeting(text: str) -> bool:
    t = text.strip().lower()
    greetings = {
        "hi", "hii", "hiii", "hello", "hey", "heyy", "good morning",
        "good afternoon", "good evening", "thanks", "thank you", "hello there", "hey there"
    }
    if t in greetings or re.match(r"^(hi+|hello|hey+|good\s+(morning|afternoon|evening))[.!?]*$", t):
        return True
    return False


def is_capability_query(text: str) -> bool:
    t = text.strip().lower()
    if t in {"what can you do?", "what can u do", "what can you do", "help", "help me"}:
        return True
    return bool(
        re.search(
            r"\b(what\s+can\s+(you|u)\s+(do|help|offer)|how\s+can\s+(you|u)\s+help|what\s+are\s+your\s+capabilities|what\s+do\s+you\s+do|what\s+features|help\s+me)\b",
            t,
        )
    )


def is_cancellation(text: str) -> bool:
    t = text.strip().lower()
    return bool(
        re.search(
            r"\b(don'?t\s+want\s+to\s+(travel|fly|book|go)|cancel|forget\s+it|never\s+mind|stop|don'?t\s+search|changed\s+my\s+mind|no\s+longer\s+interested|don'?t\s+need\s+flights?)\b",
            t,
        )
    )


def is_informational_query(text: str) -> bool:
    t = text.strip().lower()
    info_patterns = [
        r"\bhow\s+early\s+should\s+i\s+arrive",
        r"\bwhat\s+documents\s+do\s+i\s+need",
        r"\bhow\s+much\s+(luggage|baggage)",
        r"\bwhat\s+is\s+a\s+layover",
        r"\bdifference\s+between\s+(economy|business|first)",
        r"\bdo\s+i\s+need\s+a\s+visa",
        r"\bbaggage\s+allowance\b",
        r"\bluggage\s+allowance\b",
        r"\bcarry-?on\s+(rules|baggage|policy)",
        r"\bcabin\s+baggage\b",
        r"\bhand\s+baggage\b",
        r"\bchecked\s+baggage\b",
        r"\bwhat\s+luggage\s+can\s+i\s+take",
        r"\bwhat\s+can\s+i\s+take\s+in\s+cabin",
        r"\bairport\s+(rules|guidance|arrival)",
        r"\btravel\s+rules\b",
        r"\bboarding\s+guidance\b",
        r"\blong-?haul\s+(travel\s+)?rules\b",
    ]
    return any(re.search(pat, t) for pat in info_patterns)


def is_result_followup(text: str) -> bool:
    t = text.strip().lower()
    if re.search(r"\b(best|cheapest)\s+(day|time|month|date)\b", t):
        return False

    followup_patterns = [
        r"\bwhich\s+(flight|one|option)\s+is\s+(best|cheapest|fastest)\b",
        r"\bwhat\s+(flight|one|option)\s+is\s+(best|cheapest|fastest)\b",
        r"\bgive\s+(me\s+)?(only\s+)?(one|1)\b",
        r"\bshow\s+(only\s+)?(one|1)\b",
        r"\b(only|just)\s+one\s+(flight|offer|option)\b",
        r"\bwhich\s+is\s+(best|cheapest|fastest)\b",
        r"\b(cheapest|fastest)\s+flight\b",
        r"\btop\s+pick\b",
        r"\bbest\s+option\b",
        r"\bwhich\s+(one|option)\s+should\s+i\s+choose\b",
        # Broader patterns to catch natural phrasings
        r"\bwhich\s+is\s+(?:the\s+)?(best|cheapest|fastest)\b",
        r"\b(?:the\s+)?(cheapest|fastest|best)\s+(flight|airline|option)\b",
        r"\bgive\s+(?:me\s+)?(?:the\s+)?(cheapest|fastest|best)\s*(?:flight|option|one)?\b",
        r"\bshow\s+(?:me\s+)?(?:the\s+)?(cheapest|fastest|best)\b",
        r"\bi\s+want\s+(?:the\s+)?(cheapest|fastest|best)\b",
        r"\bsort\s+by\s+(price|cheapest|fastest|duration)\b",
    ]
    return any(re.search(pat, t) for pat in followup_patterns)


def is_duration_query(text: str) -> bool:
    t = text.strip().lower()
    duration_patterns = [
        r"\bhow\s+many\s+hours\b",
        r"\bhow\s+long\s+is\s+the\s+flight\b",
        r"\bhow\s+long\s+does\s+the\s+flight\s+take\b",
        r"\btravel\s+time\b",
        r"\bflight\s+duration\b",
        r"\bjourney\s+duration\b",
        r"\bhow\s+much\s+time\s+does\s+it\s+take\b",
        r"\bflight\s+time\b",
    ]
    return any(re.search(pat, t) for pat in duration_patterns)



_MONTH_NAMES: dict[str, int] = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}
_MONTH_REGEX_PAT: str = "|".join(_MONTH_NAMES.keys())


def _safe_date(day: int, month: int, year: int, today: date) -> str | None:
    """Build an ISO date string if the values form a valid, non-past date."""
    try:
        d = date(year, month, day)
    except ValueError:
        return None
    if d < today:
        return None
    return d.isoformat()


def _parse_date(text: str, today: date) -> str | None:
    if re.search(r"\b(tommorow|tomorrow|tmrw|tomm)\b", text):
        return (today + timedelta(days=1)).isoformat()
    if re.search(r"\b(today)\b", text):
        return today.isoformat()

    if re.search(r"\b(?:in|within|anytime\s+in|any\s+day\s+in)?\s*(?:the\s+)?next\s+(\d+)\s+days?\b", text):
        return (today + timedelta(days=1)).isoformat()

    in_days_m = re.search(r"\bin\s+(\d+)\s+days?\b", text)
    if in_days_m:
        days_num = int(in_days_m.group(1))
        return (today + timedelta(days=days_num)).isoformat()

    if re.search(r"\bnext\s+week\b", text):
        return (today + timedelta(days=7)).isoformat()

    if re.search(r"\b(?:this\s+)?weekend\b", text):
        days_ahead = (5 - today.weekday()) % 7 or 7
        return (today + timedelta(days=days_ahead)).isoformat()

    match_weekday = re.search(
        r"\bnext\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        text,
    )
    if match_weekday:
        target_name = match_weekday.group(1)
        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        target_idx = weekdays.index(target_name)
        current_idx = today.weekday()
        days_ahead = target_idx - current_idx
        if days_ahead <= 0:
            days_ahead += 7
        return (today + timedelta(days=days_ahead)).isoformat()

    # ISO format: YYYY-MM-DD (must stay before DD-MM-YYYY to avoid ambiguity)
    match_iso = re.search(r"\b\d{4}-\d{2}-\d{2}\b", text)
    if match_iso:
        return match_iso.group(0)

    # DD-MM-YYYY or DD/MM/YYYY (default assumption: day first, Indian format)
    match_dmy = re.search(r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b", text)
    if match_dmy:
        day_val = int(match_dmy.group(1))
        month_val = int(match_dmy.group(2))
        year_val = int(match_dmy.group(3))
        result = _safe_date(day_val, month_val, year_val, today)
        if result:
            return result
        # Fallback: try MM-DD-YYYY interpretation
        result = _safe_date(month_val, day_val, year_val, today)
        if result:
            return result

    # "21 August 2026", "21 aug 2026", "21st August 2026"
    match_dmy_natural = re.search(
        r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(" + _MONTH_REGEX_PAT + r")\s+(\d{4})\b", text
    )
    if match_dmy_natural:
        day_val = int(match_dmy_natural.group(1))
        month_val = _MONTH_NAMES[match_dmy_natural.group(2)]
        year_val = int(match_dmy_natural.group(3))
        result = _safe_date(day_val, month_val, year_val, today)
        if result:
            return result

    # "August 21, 2026", "Aug 21 2026"
    match_mdy_natural = re.search(
        r"\b(" + _MONTH_REGEX_PAT + r")\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b", text
    )
    if match_mdy_natural:
        month_val = _MONTH_NAMES[match_mdy_natural.group(1)]
        day_val = int(match_mdy_natural.group(2))
        year_val = int(match_mdy_natural.group(3))
        result = _safe_date(day_val, month_val, year_val, today)
        if result:
            return result

    return None


def parse_date_intent(text: str, today: date) -> tuple[str | None, str | None, int | None]:
    t = text.lower()
    time_pref = None
    target_hr = None

    pm_rgx = r"\b([1-9]|1[0-2])\s*(?::\d{2})?\s*pm\b"
    if re.search(pm_rgx, t) or "7pm" in t:
        time_pref = "evening"
        pm_match = re.search(pm_rgx, t)
        if pm_match:
            hr = int(pm_match.group(1))
            target_hr = hr + 12 if hr < 12 else 12
        elif "7pm" in t:
            target_hr = 19
    elif re.search(r"\b(mrng|morning|am)\b", t):
        time_pref = "morning"
        am_match = re.search(r"\b([1-9]|1[0-2])\s*(?::\d{2})?\s*am\b", t)
        if am_match:
            target_hr = int(am_match.group(1)) % 12
    elif re.search(r"\b(aftn|afternoon)\b", t):
        time_pref = "afternoon"
    elif re.search(r"\b(eve|evening|night)\b", t):
        time_pref = "evening"

    dep_date = _parse_date(t, today)
    return dep_date, time_pref, target_hr


def _extract_airports_with_intent(
    text: str, pending_question: str | None = None
) -> tuple[str | None, str | None, bool, bool, bool]:
    """
    Extract (origin, destination, is_explicit_orig, is_explicit_dest, is_correction) from a single text turn.
    Respects pending question context for bare airport/city answers.
    """
    t = text.strip().lower()

    # 0a. Negative origin correction phrasing ("not from hyderabad from delhi", "instead of hyderabad, delhi", "not hyderabad, delhi")
    neg_orig_match = re.search(
        r"\b(?:not\s+from|instead\s+of|rather\s+than|don'?t\s+want\s+to\s+(?:leave|depart)\s+from|change\s+origin\s+from|not)\s+([a-z\s]{3,20}?)\s*(?:,|\s+from|\s+leave\s+from|\s+depart\s+from|\s+to)?\s+([a-z\s]{3,20})\b",
        t,
    )
    if neg_orig_match:
        neg_city = neg_orig_match.group(1).strip()
        pos_city = neg_orig_match.group(2).strip()
        neg_code = None
        pos_code = None
        for name, code in AIRPORT_MAP.items():
            if name == neg_city or name in neg_city:
                neg_code = code
            if name == pos_city or name in pos_city:
                pos_code = code
        if pos_code and neg_code and pos_code != neg_code:
            return pos_code, None, True, False, True

    # 0b. Negative destination correction phrasing ("I don't want Dubai, I want London", "not Dubai, London", "change destination to London")
    neg_dest_match = re.search(
        r"\b(?:don'?t\s+want|not|instead\s+of|rather\s+than|change\s+destination\s+from)\s+([a-z\s]{3,20}?)\s*(?:,|\s+want|\s+fly\s+to|\s+go\s+to|\s+to)?\s+(?:i\s+want\s+|want\s+|to\s+)?([a-z\s]{3,20})\b",
        t,
    )
    if neg_dest_match:
        neg_city = neg_dest_match.group(1).strip()
        pos_city = neg_dest_match.group(2).strip()
        neg_code = None
        pos_code = None
        for name, code in AIRPORT_MAP.items():
            if name == neg_city or name in neg_city:
                neg_code = code
            if name == pos_city or name in pos_city:
                pos_code = code
        if pos_code and neg_code and pos_code != neg_code:
            return None, pos_code, False, True, True

    # 1. Both origin and destination explicit patterns
    iata_match = re.search(
        r"\b(?:from\s+)?([a-zA-Z]{3})\s+to\s+([a-zA-Z]{3})\b", t
    )
    stop_words = {"the", "and", "for", "you", "can", "out", "set", "now", "fly", "get", "day", "any"}
    if iata_match:
        c1 = iata_match.group(1).lower()
        c2 = iata_match.group(2).lower()
        code1 = AIRPORT_MAP.get(c1, c1.upper() if c1 not in stop_words else None)
        code2 = AIRPORT_MAP.get(c2, c2.upper() if c2 not in stop_words else None)
        if code1 and code2 and code1 != code2:
            return code1, code2, True, True, False

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

            if re.search(pat_from_to, t):
                return code1, code2, True, True, False
            elif re.search(pat_dest_from, t):
                return code2, code1, True, True, False
            elif re.search(pat_orig_to, t):
                return code1, code2, True, True, False

    # 2. Explicit origin phrases ("from mumbai", "leaving from delhi", "departing from bangalore", "start from delhi", "leave from delhi")
    orig_match = re.search(
        r"\b(?:from|leaving\s+from|departing\s+from|depart\s+from|leaving|start\s+from|leave\s+from|departure\s+to)\s+([a-z\s]{3,20})\b",
        t,
    )
    if orig_match:
        target_str = orig_match.group(1).strip()
        for name, code in AIRPORT_MAP.items():
            if target_str == name or re.search(r"\b" + re.escape(name) + r"\b", target_str):
                return code, None, True, False, False

    # 3. Explicit destination phrases ("i want to go delhi", "no i want to fly london", "take me to delhi", "change destination to delhi", "actually london", "to delhi", "i want london")
    dest_match = re.search(
        r"\b(?:to|go\s+to|go|going\s+to|fly\s+to|head\s+to|heading\s+to|destination\s+to|take\s+me\s+to|what\s+about|actually|rather\s+go\s+to|want\s+to\s+fly|want\s+to\s+go|i\s+want|want)\s+([a-z\s]{3,20})\b",
        t,
    )
    if dest_match:
        target_str = dest_match.group(1).strip()
        for name, code in AIRPORT_MAP.items():
            if target_str == name or re.search(r"\b" + re.escape(name) + r"\b", target_str):
                return None, code, False, True, False

    # 4. Check if text contains airport/city mentions sorted by position in string
    matches = []
    for name, code in AIRPORT_MAP.items():
        m = re.search(r"\b" + re.escape(name) + r"\b", t)
        if m:
            matches.append((m.start(), code))
    if matches:
        matches.sort(key=lambda x: x[0])
        found_city_code = matches[-1][1]
        if pending_question == "ASKED_FOR_ORIGIN":
            return found_city_code, None, True, False, False
        elif pending_question == "ASKED_FOR_DESTINATION":
            return None, found_city_code, False, True, False
        else:
            return None, found_city_code, False, True, False

    return None, None, False, False, False


def extract_flight_context(
    messages: list[dict[str, str]], today: date | None = None
) -> dict[str, Any]:
    """
    Extract flight search intent and parameters from conversation history.
    Uses turn-aware intent/state precedence:
    PENDING QUESTION + LATEST TURN + EXISTING VALID CONTEXT -> CURRENT INTERPRETATION
    """
    if today is None:
        today = date.today()

    context: dict[str, Any] = {
        "origin": None,
        "destination": None,
        "departure_date": None,
        "time_preference": None,
        "target_hour": None,
        "is_greeting": False,
        "is_capability_query": False,
        "is_cancellation": False,
        "is_informational_query": False,
        "is_result_followup": False,
        "is_duration_query": False,
        "is_search_intent": False,
        "is_unresolved_route": False,
    }

    user_messages = [m for m in messages if m.get("role") == "user"]
    if not user_messages:
        return context

    last_user_text = user_messages[-1]["content"].strip()

    if is_cancellation(last_user_text):
        context["is_cancellation"] = True
        return context

    if is_greeting(last_user_text):
        context["is_greeting"] = True
        return context

    if is_capability_query(last_user_text):
        context["is_capability_query"] = True
        return context

    # NOTE: is_result_followup is set but we do NOT early-return.
    # We must continue processing to accumulate origin/dest/date from history
    # so follow-up queries can access stored Duffel results or re-search.
    is_followup = is_result_followup(last_user_text)

    if is_duration_query(last_user_text):
        context["is_duration_query"] = True
        turn_orig, turn_dest, _, _, _ = _extract_airports_with_intent(last_user_text)
        if turn_orig and turn_dest:
            context["origin"] = turn_orig
            context["destination"] = turn_dest
        return context

    if is_informational_query(last_user_text):
        context["is_informational_query"] = True
        return context

    curr_origin = None
    curr_dest = None
    curr_date = None
    curr_time_pref = None
    curr_target_hr = None
    is_search_intent = False
    is_unresolved_route = False

    assistant_messages = [m["content"] for m in messages if m.get("role") == "assistant"]

    for i, u_msg in enumerate(user_messages):
        t = u_msg["content"].strip()
        is_last_turn = (i == len(user_messages) - 1)

        if is_cancellation(t):
            curr_origin = None
            curr_dest = None
            curr_date = None
            continue
        if is_greeting(t) or is_capability_query(t) or is_informational_query(t) or is_result_followup(t) or is_duration_query(t):
            continue

        turn_pending = None
        if i > 0 and (i - 1) < len(assistant_messages):
            prev_asst = assistant_messages[i - 1].lower()
            sentences = [s.strip() for s in re.split(r"[.!?]", prev_asst) if s.strip()]
            question_clause = sentences[-1] if sentences else prev_asst

            orig_q_pat = r"\b(depart(ing)?\s+from|leave\s+from|leaving\s+from|starting\s+from|start\s+your\s+journey|origin|departure\s+(city|location|airport)|flying\s+from|where\s+.*depart)\b"
            dest_q_pat = r"\b(fly\s+to|travel\s+to|going\s+to|destination|arrival\s+(city|location|airport)|flying\s+to|where\s+.*(?:fly|go))\b"
            date_q_pat = r"\b(what\s+date|when\s+would\s+you\s+like|departure\s+date|when\s+are\s+you\s+trave?lling|what\s+day|when\s+do\s+you\s+want\s+to\s+leave|date\s+or\s+time)\b"

            if re.search(orig_q_pat, question_clause):
                turn_pending = "ASKED_FOR_ORIGIN"
            elif re.search(dest_q_pat, question_clause):
                turn_pending = "ASKED_FOR_DESTINATION"
            elif re.search(date_q_pat, question_clause):
                turn_pending = "ASKED_FOR_DATE"
            elif re.search(orig_q_pat, prev_asst) and not re.search(r"fly\s+to|going\s+to", question_clause):
                turn_pending = "ASKED_FOR_ORIGIN"
            elif re.search(dest_q_pat, prev_asst) and not re.search(r"depart|leaving\s+from", question_clause):
                turn_pending = "ASKED_FOR_DESTINATION"

        turn_orig, turn_dest, is_exp_orig, is_exp_dest, is_correction = _extract_airports_with_intent(t, turn_pending)
        turn_date, turn_pref, turn_hr = parse_date_intent(t, today)

        # Check if turn is an explicit route attempt that failed airport resolution (e.g. "deli to hderbad")
        is_route_attempt = bool(
            re.search(r"\b(?:from\s+[a-z]{3,20}\s+to\s+[a-z]{3,20}|[a-z]{3,20}\s+to\s+[a-z]{3,20}|travel\s+from|fly\s+from|go\s+from|tavel\s+from)\b", t.lower())
        )
        if is_route_attempt and not turn_orig and not turn_dest and not is_cancellation(t) and not is_greeting(t) and not is_capability_query(t):
            curr_origin = None
            curr_dest = None
            curr_date = None
            is_unresolved_route = True
            is_search_intent = False
            continue

        if is_affirmative(t):
            if is_last_turn and curr_origin and curr_dest and curr_date:
                is_search_intent = True
            continue

        if is_exp_orig and is_exp_dest:
            curr_origin = turn_orig
            curr_dest = turn_dest
            curr_date = turn_date
            if is_last_turn:
                if curr_origin and curr_dest and curr_date:
                    is_search_intent = True
                else:
                    is_search_intent = False

        elif is_exp_orig and not is_exp_dest:
            curr_origin = turn_orig
            if turn_dest:
                curr_dest = turn_dest
            if turn_date:
                curr_date = turn_date
            elif not is_correction:
                curr_date = None
            if is_last_turn:
                if curr_origin and curr_dest and curr_date:
                    is_search_intent = True
                else:
                    is_search_intent = False

        elif is_exp_dest and not is_exp_orig:
            curr_dest = turn_dest
            if turn_orig:
                curr_origin = turn_orig
            if turn_date:
                curr_date = turn_date
            elif not is_correction:
                curr_date = None
            if is_last_turn:
                if curr_origin and curr_dest and curr_date:
                    is_search_intent = True
                else:
                    is_search_intent = False

        elif turn_orig and not turn_dest:
            curr_origin = turn_orig
            if is_last_turn:
                if curr_origin and curr_dest and curr_date:
                    is_search_intent = True
                else:
                    is_search_intent = False

        elif turn_dest and not turn_orig:
            curr_dest = turn_dest
            if is_last_turn:
                if curr_origin and curr_dest and curr_date:
                    is_search_intent = True
                else:
                    is_search_intent = False

        if turn_date:
            curr_date = turn_date
            if curr_origin and curr_dest and is_last_turn:
                is_search_intent = True
        if turn_pref:
            curr_time_pref = turn_pref
        if turn_hr:
            curr_target_hr = turn_hr

        if is_last_turn and any(k in t.lower() for k in ("search flights", "find flights", "show me flights", "show flights")):
            if curr_origin and curr_dest and curr_date:
                is_search_intent = True

    context["origin"] = curr_origin
    context["destination"] = curr_dest
    context["departure_date"] = curr_date
    context["time_preference"] = curr_time_pref
    context["target_hour"] = curr_target_hr
    context["is_search_intent"] = is_search_intent
    context["is_unresolved_route"] = is_unresolved_route
    context["is_result_followup"] = is_followup

    return context




class AssistantService:
    """Business logic for the AI travel assistant."""

    def __init__(
        self,
        chat_repo: ChatRepository,
        llm_provider: LLMProvider,
        flight_service: FlightService | None = None,
    ) -> None:
        self._chat_repo = chat_repo
        self._llm = llm_provider
        self._flight_service = flight_service

    async def chat(
        self,
        *,
        user_id: UUID,
        message: str,
        conversation_id: UUID | None,
    ) -> ChatResponse:
        """Process a user message and return the assistant reply."""
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

        self._chat_repo.add_message(
            conversation_id=conversation.id,
            role="user",
            content=message,
        )

        t2 = time.monotonic()
        history = self._chat_repo.get_messages(
            conversation_id=conversation.id, limit=_CONTEXT_WINDOW + 1
        )
        raw_messages = [{"role": msg.role, "content": msg.content} for msg in history]


        flight_ctx = extract_flight_context(raw_messages)
        system_prompt = get_system_prompt()

        search_executed = False
        flight_search_results: list[Any] = []
        reply_override: str | None = None

        should_execute_search = (
            self._flight_service is not None
            and flight_ctx.get("is_search_intent") is True
            and bool(flight_ctx.get("origin"))
            and bool(flight_ctx.get("destination"))
            and bool(flight_ctx.get("departure_date"))
        )

        if flight_ctx.get("is_cancellation"):
            reply_override = (
                "No problem! I won't search for flights. Let me know if you need help with anything else."
            )
        elif flight_ctx.get("is_unresolved_route"):
            reply_override = (
                "I couldn't identify one or both airports in that route. Please provide the departure and destination city, for example: Delhi to Hyderabad."
            )
        elif should_execute_search:
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

                    # Persist search results for follow-up queries
                    try:
                        self._chat_repo.update_conversation_context(
                            conversation_id=conversation.id,
                            context={
                                "origin": orig,
                                "destination": dest,
                                "departure_date": dep_dt,
                                "last_search_results": [
                                    {
                                        "flight_number": o.segments[0].flight_number if o.segments else "N/A",
                                        "airline": (o.segments[0].airline_name or o.segments[0].airline) if o.segments else "N/A",
                                        "departure_time": o.departure_time.strftime("%H:%M") if o.departure_time else "N/A",
                                        "arrival_time": o.arrival_time.strftime("%H:%M") if o.arrival_time else "N/A",
                                        "price": o.price,
                                        "currency": o.currency,
                                        "duration": o.duration or "N/A",
                                    }
                                    for o in results[:5]
                                ],
                            },
                        )
                    except Exception as ctx_exc:
                        logger.warning("Failed to persist search context: %s", ctx_exc)
            except Exception as exc:
                logger.warning("Assistant flight search execution failed: %s", exc)
                reply_override = (
                    f"I couldn't complete the flight search right now for "
                    f"{orig} → {dest} on {dep_dt}. Please try again."
                )
        elif flight_ctx.get("is_result_followup"):
            # Attempt deterministic follow-up from stored results
            stored_ctx = self._chat_repo.get_conversation_context(
                conversation_id=conversation.id
            )
            stored_results = (stored_ctx or {}).get("last_search_results", []) if stored_ctx else []
            last_text_lower = message.strip().lower()

            if stored_results:
                # Deterministic filtering — no LLM needed for simple queries
                if "cheapest" in last_text_lower or "lowest price" in last_text_lower:
                    sorted_offers = sorted(stored_results, key=lambda r: float(r.get("price", 999999)))
                    winner = sorted_offers[0]
                    reply_override = (
                        f"Here is the cheapest flight from your search:\n"
                        f"- Flight {winner.get('flight_number', 'N/A')} ({winner.get('airline', 'N/A')}): "
                        f"Departs {winner.get('departure_time', 'N/A')}, "
                        f"Arrives {winner.get('arrival_time', 'N/A')}, "
                        f"Price: {winner.get('currency', 'USD')} {float(winner.get('price', 0)):.2f}"
                    )
                elif "fastest" in last_text_lower or "shortest" in last_text_lower:
                    sorted_offers = sorted(stored_results, key=lambda r: r.get("duration", "PT99H"))
                    winner = sorted_offers[0]
                    reply_override = (
                        f"Here is the fastest flight from your search:\n"
                        f"- Flight {winner.get('flight_number', 'N/A')} ({winner.get('airline', 'N/A')}): "
                        f"Departs {winner.get('departure_time', 'N/A')}, "
                        f"Arrives {winner.get('arrival_time', 'N/A')}, "
                        f"Price: {winner.get('currency', 'USD')} {float(winner.get('price', 0)):.2f}"
                    )
                elif any(w in last_text_lower for w in ("best", "recommend", "top", "which one")):
                    winner = stored_results[0]
                    reply_override = (
                        f"Based on your search, I recommend:\n"
                        f"- Flight {winner.get('flight_number', 'N/A')} ({winner.get('airline', 'N/A')}): "
                        f"Departs {winner.get('departure_time', 'N/A')}, "
                        f"Arrives {winner.get('arrival_time', 'N/A')}, "
                        f"Price: {winner.get('currency', 'USD')} {float(winner.get('price', 0)):.2f}\n"
                        f"This offers the best balance of schedule and fare."
                    )
                else:
                    # General follow-up — re-display all stored results
                    lines = []
                    for r in stored_results[:3]:
                        lines.append(
                            f"- Flight {r.get('flight_number', 'N/A')} ({r.get('airline', 'N/A')}): "
                            f"Departs {r.get('departure_time', 'N/A')}, "
                            f"Arrives {r.get('arrival_time', 'N/A')}, "
                            f"Price: {r.get('currency', 'USD')} {float(r.get('price', 0)):.2f}"
                        )
                    reply_override = (
                        f"Here are your search results:\n" + "\n".join(lines)
                    )
            elif (
                flight_ctx.get("origin")
                and flight_ctx.get("destination")
                and flight_ctx.get("departure_date")
                and self._flight_service is not None
            ):
                # No stored results but route is known — re-execute search inline
                re_orig = flight_ctx["origin"]
                re_dest = flight_ctx["destination"]
                re_dep_dt = flight_ctx["departure_date"]
                try:
                    re_dep_date = date.fromisoformat(re_dep_dt)
                    re_params = FlightSearchParams(
                        origin=re_orig,
                        destination=re_dest,
                        departure_date=re_dep_date,
                        travel_class=TravelClass.ECONOMY,
                        adults=1, children=0, infants=0,
                        non_stop=False, currency="USD", max_results=5,
                    )
                    re_results, _ = await self._flight_service.search_flights(
                        params=re_params, user_id=user_id
                    )
                    if re_results:
                        search_executed = True
                        flight_search_results = re_results
                        # Apply the follow-up filter
                        if "cheapest" in last_text_lower or "lowest price" in last_text_lower:
                            re_results.sort(key=lambda r: r.price)
                        elif "fastest" in last_text_lower or "shortest" in last_text_lower:
                            re_results.sort(key=lambda r: r.duration or "PT99H")
                        winner = re_results[0]
                        seg = winner.segments[0] if winner.segments else None
                        airline = (seg.airline_name or seg.airline) if seg else "N/A"
                        flight_num = seg.flight_number if seg else "N/A"
                        reply_override = (
                            f"Here is the {'cheapest' if 'cheapest' in last_text_lower else 'best'} flight for "
                            f"{re_orig} → {re_dest} on {re_dep_dt}:\n"
                            f"- Flight {flight_num} ({airline}): Departs "
                            f"{winner.departure_time.strftime('%H:%M')}, "
                            f"Arrives {winner.arrival_time.strftime('%H:%M')}, "
                            f"Price: {winner.currency} {winner.price:.2f}"
                        )
                        # Persist for future follow-ups
                        try:
                            self._chat_repo.update_conversation_context(
                                conversation_id=conversation.id,
                                context={
                                    "origin": re_orig,
                                    "destination": re_dest,
                                    "departure_date": re_dep_dt,
                                    "last_search_results": [
                                        {
                                            "flight_number": (o.segments[0].flight_number if o.segments else "N/A"),
                                            "airline": ((o.segments[0].airline_name or o.segments[0].airline) if o.segments else "N/A"),
                                            "departure_time": o.departure_time.strftime("%H:%M") if o.departure_time else "N/A",
                                            "arrival_time": o.arrival_time.strftime("%H:%M") if o.arrival_time else "N/A",
                                            "price": o.price,
                                            "currency": o.currency,
                                            "duration": o.duration or "N/A",
                                        }
                                        for o in re_results[:5]
                                    ],
                                },
                            )
                        except Exception as ctx_exc:
                            logger.warning("Failed to persist re-search context: %s", ctx_exc)
                    else:
                        reply_override = (
                            f"No matching flights were found for {re_orig} → {re_dest} "
                            f"on {re_dep_dt}."
                        )
                except Exception as re_exc:
                    logger.warning("Follow-up re-search failed: %s", re_exc)
                    reply_override = (
                        f"I couldn't complete the flight search right now for "
                        f"{re_orig} → {re_dest} on {re_dep_dt}. Please try again."
                    )
            else:
                reply_override = (
                    "I don't have active flight search results to compare. "
                    "Would you like to search for flights? Please provide a route and date."
                )
        elif flight_ctx.get("is_duration_query"):
            orig = flight_ctx.get("origin")
            dest = flight_ctx.get("destination")
            if orig and dest:
                system_prompt += (
                    f"\n\nUser is asking about flight duration for route {orig} to {dest}. "
                    "Provide a helpful answer about general flight duration for this route."
                )
            else:
                system_prompt += (
                    "\n\nUser is asking about flight duration. "
                    "Provide a helpful answer about general travel times."
                )
        elif (
            flight_ctx["origin"]
            and flight_ctx["destination"]
            and not flight_ctx["departure_date"]
            and not flight_ctx.get("is_greeting")
            and not flight_ctx.get("is_capability_query")
            and not flight_ctx.get("is_informational_query")
        ):
            orig = flight_ctx["origin"]
            dest = flight_ctx["destination"]
            system_prompt += (
                f"\n\nRoute understood: {orig} to {dest}. Departure date is missing. "
                f"Acknowledge the route from {orig} to {dest} and ask the user what "
                "date or time they would like to depart."
            )
        elif (
            flight_ctx["destination"]
            and not flight_ctx["origin"]
            and not flight_ctx.get("is_greeting")
            and not flight_ctx.get("is_capability_query")
            and not flight_ctx.get("is_informational_query")
        ):
            dest = flight_ctx["destination"]
            system_prompt += (
                f"\n\nDestination understood: {dest}. Origin (departure location) is missing. "
                f"Acknowledge destination {dest} and ask the user where they would like to depart from."
            )
        elif (
            flight_ctx["origin"]
            and not flight_ctx["destination"]
            and not flight_ctx.get("is_greeting")
            and not flight_ctx.get("is_capability_query")
            and not flight_ctx.get("is_informational_query")
        ):
            orig = flight_ctx["origin"]
            system_prompt += (
                f"\n\nOrigin understood: {orig}. Destination is missing. "
                f"Acknowledge origin {orig} and ask the user where they would like to fly to."
            )
        elif flight_ctx.get("is_capability_query"):
            system_prompt += (
                "\n\nUser is asking about your capabilities. Provide a clear, helpful summary of "
                "what you can do: flight search, price prediction, airport lookup, and travel information."
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
                    timeout=getattr(self, "_llm_timeout", 30.0),
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
                    fallback = FallbackProvider(error=exc)
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
