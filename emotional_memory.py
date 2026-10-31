"""
Joy Bot - AI Emotional Memory & Proactive Recall Engine ("Joy Remembers")

Provides:
1. 3-tier memory aging and decay (events: upcoming + 48h callback; emotions: 48h; preferences: permanent).
2. Deterministic offline token estimation (<150 tokens) and system prompt context formatting.
3. Proactive call greeting generator for upcoming or recent life events.
4. 100% offline heuristic extraction engine for dialogue turns (+ optional online LLM fallback).
5. Non-blocking asynchronous background worker for zero-latency storage.
"""

import os
import re
import math
import json
import logging
import asyncio
from datetime import datetime, date, timedelta, timezone
from datetime import datetime as _RealDateTime, date as _RealDate
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger("JoyEmotionalMemory")

# ============================================================================
# Data Model
# ============================================================================

@dataclass
class MemoryItem:
    """Structured representation of a Joy episodic or emotional memory."""
    id: Optional[int] = None
    user_id: int = 0
    category: str = "fact"        # 'event', 'emotion', 'preference', 'fact', 'milestone'
    memory_key: str = ""          # normalized semantic slug
    memory_val: str = ""          # human-readable content
    emotional_tag: str = ""       # 'stressed', 'anxious', 'excited', 'happy', etc.
    event_date: str = ""          # YYYY-MM-DD or empty
    created_at: str = ""          # ISO UTC timestamp

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryItem":
        return cls(
            id=data.get("id"),
            user_id=data.get("user_id", 0),
            category=data.get("category", "fact"),
            memory_key=data.get("memory_key", ""),
            memory_val=data.get("memory_val", ""),
            emotional_tag=data.get("emotional_tag", ""),
            event_date=data.get("event_date", ""),
            created_at=data.get("created_at", "")
        )


def _safe_parse_iso_datetime(dt_str: str) -> Optional[datetime]:
    """Parses an ISO datetime string reliably using unmocked datetime."""
    if not dt_str:
        return None
    try:
        clean_str = dt_str.replace("Z", "+00:00")
        dt = _RealDateTime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _safe_parse_iso_date(d_str: str) -> Optional[date]:
    """Parses an ISO date string reliably using unmocked date."""
    if not d_str:
        return None
    try:
        return _RealDate.fromisoformat(d_str[:10])
    except Exception:
        return None


# ============================================================================
# Memory Lifecycle, Aging & Decay (3-Tier Model)
# ============================================================================

def is_memory_active(memory: Dict[str, Any], reference_time: Optional[datetime] = None) -> bool:
    """
    Evaluates whether a memory record is currently active based on the 3-tier lifecycle:
    - Events: Active if upcoming or within 48h callback window (event_date >= today - 2 days).
    - Emotions: Active if created within the past 48 hours.
    - Preferences / Facts / Milestones: Enduring (always active).
    """
    if not memory or not isinstance(memory, dict):
        return False

    ref_dt = reference_time or datetime.now(timezone.utc)
    if hasattr(ref_dt, "tzinfo") and ref_dt.tzinfo is None:
        ref_dt = ref_dt.replace(tzinfo=timezone.utc)
    today = ref_dt.date() if hasattr(ref_dt, "date") else _RealDate.today()

    category = (memory.get("category") or "").strip().lower()
    event_date_str = (memory.get("event_date") or "").strip()
    created_at_str = (memory.get("created_at") or "").strip()

    # Tier 1: Events (upcoming + 48h callback window)
    if category == "event" or event_date_str:
        if event_date_str:
            ev_date = _safe_parse_iso_date(event_date_str)
            if ev_date is not None:
                cutoff = today - timedelta(days=2)
                return ev_date >= cutoff
        # Fallback if event_date was missing or unparseable: 48h shelf life from creation
        if created_at_str:
            c_dt = _safe_parse_iso_datetime(created_at_str)
            if c_dt is not None:
                return (ref_dt - c_dt) <= timedelta(hours=48)
        return False

    # Tier 2: Emotions (48h shelf life)
    if category in ("emotion", "mood"):
        if not created_at_str:
            return False
        c_dt = _safe_parse_iso_datetime(created_at_str)
        if c_dt is not None:
            return (ref_dt - c_dt) <= timedelta(hours=48)
        return False

    # Tier 3: Enduring Preferences & Facts (permanent)
    return True


def filter_active_memories(
    memories: List[Dict[str, Any]], 
    reference_time: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """Filters a list of memories, returning only those that are currently active."""
    return [m for m in memories if is_memory_active(m, reference_time=reference_time)]


# ============================================================================
# Token Estimation & Context Formatting (<150 Tokens)
# ============================================================================

def estimate_tokens(text: str) -> int:
    """
    Deterministic offline token estimator with zero external dependencies.
    Provides a conservative upper bound: max(ceil(len(text)/3.5), len(text.split())).
    """
    if not text:
        return 0
    chars_est = math.ceil(len(text) / 3.5)
    words_est = len(text.split())
    return max(chars_est, words_est)


def _memory_priority_key(mem: Dict[str, Any], today: date, ref_dt: datetime) -> Tuple[int, int, int]:
    """
    Generates a sorting key tuple (tier_rank, urgency_rank, secondary_rank) for memory prioritization:
    1. Active Events: Today (0) > Tomorrow (1) > Yesterday (-1) > Next 7 days > 2 days ago (-2) > Future
    2. Active Emotions: Most recent created_at first
    3. Enduring Preferences/Facts: Most recent created_at first
    """
    cat = (mem.get("category") or "").strip().lower()
    ev_str = (mem.get("event_date") or "").strip()

    if cat == "event" or ev_str:
        if ev_str:
            ev_date = _safe_parse_iso_date(ev_str)
            if ev_date is not None:
                diff = (ev_date - today).days
                if diff == 0:
                    return (1, 0, 0)          # Today
                elif diff == 1:
                    return (1, 1, 0)          # Tomorrow
                elif diff == -1:
                    return (1, 2, 0)          # Yesterday (callback)
                elif 2 <= diff <= 7:
                    return (1, 3, diff)       # Next 7 days
                elif diff == -2:
                    return (1, 4, 0)          # 2 days ago (callback)
                elif diff > 7:
                    return (1, 5, diff)       # Distant future
                else:
                    return (1, 9, abs(diff))  # Past
        return (1, 8, 0)

    if cat in ("emotion", "mood"):
        c_str = (mem.get("created_at") or "").strip()
        age_seconds = 0
        c_dt = _safe_parse_iso_datetime(c_str)
        if c_dt is not None:
            age_seconds = max(0, int((ref_dt - c_dt).total_seconds()))
        return (2, 0, age_seconds)

    # Preferences & Facts
    c_str = (mem.get("created_at") or "").strip()
    age_seconds = 0
    c_dt = _safe_parse_iso_datetime(c_str)
    if c_dt is not None:
        age_seconds = max(0, int((ref_dt - c_dt).total_seconds()))
    return (3, 0, age_seconds)


def format_memory_context(
    user_id: int, 
    max_tokens: int = 150, 
    reference_time: Optional[datetime] = None,
    memories_override: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Selects top 3-5 active memories for user_id, formats them into a compact prompt block,
    and strictly enforces an upper bound of max_tokens (default 150).
    
    Returns an empty string if no active memories exist.
    """
    if memories_override is not None:
        raw_mems = memories_override
    else:
        try:
            from database import get_user_memories
            raw_mems = get_user_memories(user_id, include_decayed=True)
        except Exception as e:
            logger.warning(f"Failed to fetch user memories for context formatting: {e}")
            raw_mems = []

    if not raw_mems:
        return ""

    ref_dt = reference_time or datetime.now(timezone.utc)
    if hasattr(ref_dt, "tzinfo") and ref_dt.tzinfo is None:
        ref_dt = ref_dt.replace(tzinfo=timezone.utc)
    today = ref_dt.date() if hasattr(ref_dt, "date") else _RealDate.today()

    # Filter strictly active memories
    active = [m for m in raw_mems if is_memory_active(m, reference_time=ref_dt)]
    if not active:
        return ""

    # Sort by priority key
    active.sort(key=lambda m: _memory_priority_key(m, today, ref_dt))

    header = "[Joy's Emotional Memories]:\n"
    footer = "\n(Naturally reflect this background. Never quote memories mechanically.)"

    formatted_lines: List[str] = []
    for m in active[:10]:
        cat = (m.get("category") or "").strip().lower()
        val = (m.get("memory_val") or "").strip()
        tag = (m.get("emotional_tag") or "").strip().lower()
        ev_date = (m.get("event_date") or "").strip()[:10]

        if cat == "event" or ev_date:
            timing_note = ""
            if ev_date:
                ev_d = _safe_parse_iso_date(ev_date)
                if ev_d is not None:
                    diff = (ev_d - today).days
                    if diff == 0:
                        timing_note = " (today)"
                    elif diff == 1:
                        timing_note = " (tomorrow)"
                    elif diff == -1:
                        timing_note = " (yesterday)"
                    elif diff == -2:
                        timing_note = " (2 days ago)"
                    elif diff > 1:
                        timing_note = f" (in {diff} days)"
                    else:
                        timing_note = f" on {ev_date}"
                else:
                    timing_note = f" on {ev_date}"
            tag_note = f" (User feels {tag})" if tag else ""
            line = f"• Event: {val}{timing_note}{tag_note}"

        elif cat in ("emotion", "mood"):
            line = f"• Recent Emotion: {val}"

        elif cat == "preference":
            line = f"• Preference: {val}"

        else:
            line = f"• Detail: {val}"

        formatted_lines.append(line)

    # Greedily include lines while strictly remaining under max_tokens
    selected_lines: List[str] = []
    base_overhead = estimate_tokens(header + footer)
    
    for line in formatted_lines:
        # Protect against individual oversized strings (> 2000 chars)
        max_line_chars = max(20, int((max_tokens - base_overhead - 5) * 3.5))
        if len(line) > max_line_chars:
            line = line[:max_line_chars].rstrip() + "..."

        candidate_lines = selected_lines + [line]
        candidate_block = header + "\n".join(candidate_lines) + footer
        if estimate_tokens(candidate_block) <= max_tokens:
            selected_lines.append(line)
        else:
            # If even the first line alone doesn't fit, truncate it aggressively to fit
            if not selected_lines:
                while len(line) > 10 and estimate_tokens(header + line + "..." + footer) > max_tokens:
                    line = line[:-10]
                if estimate_tokens(header + line + "..." + footer) <= max_tokens:
                    selected_lines.append(line + "...")
            break

    if not selected_lines:
        return ""

    final_block = header + "\n".join(selected_lines) + footer
    return final_block


# ============================================================================
# Proactive Callback & Greeting Engine
# ============================================================================

def get_proactive_greeting(
    user_id: int, 
    caller_name: str = "Joy",
    user_name: Optional[str] = None, 
    reference_time: Optional[datetime] = None,
    memories_override: Optional[List[Dict[str, Any]]] = None
) -> Optional[str]:
    """
    Inspects active memories for upcoming or recent events.
    If an event is today, tomorrow, yesterday, or 2 days ago, synthesizes a proactive spoken callback.
    Returns None if no qualifying event exists.
    """
    if memories_override is not None:
        raw_mems = memories_override
    else:
        try:
            from database import get_user_memories
            raw_mems = get_user_memories(user_id, include_decayed=True)
        except Exception as e:
            logger.warning(f"Failed to fetch memories for proactive greeting: {e}")
            raw_mems = []

    if not raw_mems:
        return None

    ref_dt = reference_time or datetime.now(timezone.utc)
    if hasattr(ref_dt, "tzinfo") and ref_dt.tzinfo is None:
        ref_dt = ref_dt.replace(tzinfo=timezone.utc)
    today = ref_dt.date() if hasattr(ref_dt, "date") else _RealDate.today()

    candidates: List[Tuple[int, Dict[str, Any], int]] = []
    for m in raw_mems:
        cat = (m.get("category") or "").strip().lower()
        ev_str = (m.get("event_date") or "").strip()[:10]
        if (cat == "event" or ev_str) and ev_str:
            ev_d = _safe_parse_iso_date(ev_str)
            if ev_d is not None:
                diff = (ev_d - today).days
                if diff in (-2, -1, 0, 1):
                    # Urgency priority: today (0) -> yesterday (-1) -> tomorrow (1) -> 2 days ago (-2)
                    order_map = {0: 1, -1: 2, 1: 3, -2: 4}
                    candidates.append((order_map[diff], m, diff))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0])
    chosen_item = candidates[0]
    chosen_mem = chosen_item[1]
    diff = chosen_item[2]

    val = (chosen_mem.get("memory_val") or "your event").strip()
    tag = (chosen_mem.get("emotional_tag") or "").strip().lower()

    # Clean leading possessives or determiners for spoken naturalness
    clean_val = val
    for prefix in ("my ", "the ", "our "):
        if clean_val.lower().startswith(prefix):
            clean_val = clean_val[len(prefix):].strip()

    name = user_name or "Phoenix"

    if diff == 0:
        if tag in ("anxious", "stressed", "nervous"):
            return f"Hey {name}! Thinking of you today for your {clean_val}. Take a deep breath—you've got this!"
        elif tag == "excited":
            return f"Hey {name}! Today is the big day for your {clean_val}! So excited for you!"
        else:
            return f"Hey {name}! Good luck with your {clean_val} today! How are you feeling?"

    elif diff == 1:
        if tag in ("anxious", "stressed", "nervous"):
            return f"Hey {name}! Big day tomorrow with your {clean_val}. Are you holding up okay?"
        elif tag == "excited":
            return f"Hey {name}! Big day tomorrow with your {clean_val}! All ready for it?"
        else:
            return f"Hey {name}! Big day tomorrow with your {clean_val}! How's preparation going?"

    elif diff in (-1, -2):
        when = "yesterday" if diff == -1 else "a couple days ago"
        if tag in ("anxious", "stressed", "nervous"):
            return f"Hey {name}! How did that {clean_val} go {when}? You were stressing about it!"
        elif tag == "excited":
            return f"Hey {name}! How was your {clean_val} {when}? Tell me everything!"
        else:
            return f"Hey {name}! How did that {clean_val} go {when}?"

    return None


# ============================================================================
# Offline Heuristic Extraction Engine & Date Resolution
# ============================================================================

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
}

_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6
}

EMOTION_KEYWORDS = {
    "stressed": [
        "stressed", "stressing", "overwhelmed", "burnt out", "swamped",
        "too much pressure", "drowning in work"
    ],
    "anxious": [
        "anxious", "nervous", "freaking out", "panicking", "scared",
        "worried", "dreading", "uneasy"
    ],
    "excited": [
        "excited", "hyped", "thrilled", "pumped", "cant wait", "can't wait",
        "looking forward", "buzzing"
    ],
    "sad": [
        "sad", "down", "depressed", "crying", "unhappy", "feeling low", "gloomy"
    ],
    "heartbroken": [
        "heartbroken", "breakup", "broke up", "dumped", "lost someone", "devastated"
    ],
    "happy": [
        "happy", "delighted", "glad", "joyful", "content", "celebrating"
    ],
    "exhausted": [
        "exhausted", "fatigued", "drained", "sleepless", "running on fumes"
    ]
}

EVENT_NOUNS = [
    "physics exam", "math exam", "semester exam", "finals exam", "exam",
    "finals", "midterm", "test", "quiz",
    "technical interview", "job interview", "interview",
    "flight", "trip", "vacation", "travel",
    "wedding", "birthday", "anniversary", "party",
    "meeting", "presentation", "deadline", "hackathon",
    "doctor appointment", "dentist appointment", "appointment"
]

GLITCH_PATTERNS = [
    r"\bcan you hear me\b",
    r"\bmic line\b",
    r"\bfluttered\b",
    r"\bvoice cracked\b",
    r"\bplease repeat\b",
    r"\bsay that again\b",
    r"\bline lagged\b",
    r"\bfirse bol\b",
    r"\bcan'?t hear you\b",
    r"\baudio cut(?:ting)? out\b",
    r"\byou(?:'re| are) breaking up\b",
]


def resolve_event_date(text: str, reference_date: Optional[date] = None) -> str:
    """
    Parses conversational relative dates, weekdays, and calendar dates into ISO YYYY-MM-DD.
    Handles:
    - 'today', 'tonight', 'tomorrow', 'day after tomorrow', 'yesterday'
    - 'in X days'
    - 'next Monday', 'this Friday', 'on Wednesday'
    - 'Oct 28', 'October 28th', '28th of Oct', 'Nov 15'
    """
    if not text:
        return ""

    ref = reference_date
    if ref is None:
        try:
            ref_dt = datetime.now(timezone.utc)
            ref = ref_dt.date() if hasattr(ref_dt, "date") else _RealDate.today()
        except Exception:
            ref = _RealDate.today()

    s = text.lower()

    if re.search(r"\bday after tomorrow\b", s):
        return (ref + timedelta(days=2)).isoformat()
    if re.search(r"\btomorrow\b", s):
        return (ref + timedelta(days=1)).isoformat()
    if re.search(r"\b(?:today|tonight)\b", s):
        return ref.isoformat()
    if re.search(r"\byesterday\b", s):
        return (ref - timedelta(days=1)).isoformat()

    # Relative offset: 'in 3 days'
    m_in = re.search(r"\bin\s+(\d+)\s+days?\b", s)
    if m_in:
        return (ref + timedelta(days=int(m_in.group(1)))).isoformat()

    # Weekday: 'next Monday', 'this Friday', 'on Thursday'
    m_w = re.search(r"\b(?:next|this|on)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", s)
    if m_w:
        target_wd = _WEEKDAYS[m_w.group(1)]
        cur_wd = ref.weekday()
        days_ahead = (target_wd - cur_wd) % 7
        if days_ahead == 0:
            days_ahead = 7
        return (ref + timedelta(days=days_ahead)).isoformat()

    # Month + Day: 'Oct 28', 'October 28th'
    m_m1 = re.search(
        r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?\b",
        s
    )
    if m_m1:
        mon_str = m_m1.group(1)[:3]
        mon = _MONTHS[mon_str]
        day = int(m_m1.group(2))
        try:
            d = _RealDate(ref.year, mon, day)
            if d < ref - timedelta(days=60):
                d = _RealDate(ref.year + 1, mon, day)
            return d.isoformat()
        except ValueError:
            pass

    # Day + Month: '28th of Oct', '28th October', '15 Nov'
    m_m2 = re.search(
        r"\b(\d{1,2})(?:st|nd|rd|th)?(?:\s+of)?\s+(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b",
        s
    )
    if m_m2:
        day = int(m_m2.group(1))
        mon_str = m_m2.group(2)[:3]
        mon = _MONTHS[mon_str]
        try:
            d = _RealDate(ref.year, mon, day)
            if d < ref - timedelta(days=60):
                d = _RealDate(ref.year + 1, mon, day)
            return d.isoformat()
        except ValueError:
            pass

    return ""


def _extract_event_phrase(text: str, ev: str) -> str:
    """Extracts and formats the clean phrase corresponding to an event noun."""
    m = re.search(rf"\b(?:about|for|having|have|got|my|our|the|a|an)\s+([A-Za-z0-9\s\-]+?\b{re.escape(ev)})\b", text, re.IGNORECASE)
    if m:
        raw = m.group(1).strip()
    else:
        m2 = re.search(rf"\b([A-Za-z0-9\s\-]{{0,30}}\b{re.escape(ev)})\b", text, re.IGNORECASE)
        raw = m2.group(1).strip() if m2 else ev
    cleaned = re.sub(r"^(?:(?:about|for|having|have|got|my|our|the|a|an|i have|i got|i'm having)\s+)+", "", raw, flags=re.IGNORECASE).strip()
    return cleaned.capitalize() if cleaned else ev.capitalize()


def extract_memories_heuristic(
    user_message: str, 
    assistant_reply: str = "",
    reference_date: Optional[date] = None
) -> List[Dict[str, Any]]:
    """
    High-precision regex and heuristic parser for 100% offline extraction.
    Identifies events, dates, emotions, personal preferences, and facts.
    Negative controls filter out mic glitches and transient transmission noise.
    """
    memories: List[Dict[str, Any]] = []
    if not user_message or not isinstance(user_message, str) or not user_message.strip():
        return memories

    t = user_message.strip()

    # Negative control: filter audio/network glitches and transient repetition requests
    for pat in GLITCH_PATTERNS:
        if re.search(pat, t, re.IGNORECASE):
            # Check if the text is primarily a line glitch request
            cleaned_noise = re.sub(pat, "", t, flags=re.IGNORECASE).strip(" .,?!")
            if len(cleaned_noise) < 15:
                return []

    ref_d = reference_date
    if ref_d is None:
        try:
            ref_dt = datetime.now(timezone.utc)
            ref_d = ref_dt.date() if hasattr(ref_dt, "date") else _RealDate.today()
        except Exception:
            ref_d = _RealDate.today()

    # 1. Detect emotion
    detected_emotion = ""
    for emo, kws in EMOTION_KEYWORDS.items():
        pattern = r"\b(?:" + "|".join(re.escape(k) for k in kws) + r")\b"
        if re.search(pattern, t, re.IGNORECASE):
            detected_emotion = emo
            break

    # 2. Extract Event & Date
    event_date = resolve_event_date(t, reference_date=ref_d)
    found_event_key = None

    for ev in EVENT_NOUNS:
        # Check if event noun is present
        if re.search(rf"\b{re.escape(ev)}(?:s)?\b", t, re.IGNORECASE):
            clean_phrase = _extract_event_phrase(t, ev)
            key_slug = ev.replace(" ", "_").lower()

            memories.append({
                "category": "event",
                "memory_key": key_slug,
                "memory_val": clean_phrase,
                "emotional_tag": detected_emotion,
                "event_date": event_date
            })
            found_event_key = ev
            break

    # 3. Standalone Emotion (if no event was linked)
    if detected_emotion and not found_event_key:
        m_about = re.search(rf"\b{detected_emotion}\b\s+(?:about|for|over|after)\s+([^,.?!;]+)", t, re.IGNORECASE)
        val = f"Feeling {detected_emotion} about {m_about.group(1).strip()}" if m_about else f"Feeling {detected_emotion}"
        memories.append({
            "category": "emotion",
            "memory_key": f"feeling_{detected_emotion}",
            "memory_val": val,
            "emotional_tag": detected_emotion,
            "event_date": ""
        })

    # 4. Preferences: Likes / Loves
    for m in re.finditer(
        r"\b(?:i\s+)?(?:really\s+|absolutely\s+)?(love|adore|enjoy)\s+([^,.?!;\n]+?)(?=(?:\s+(?:and|but|also|or|with|if)\b|[,.?!;]|$))",
        t,
        re.IGNORECASE
    ):
        target = m.group(2).strip()
        if target.lower() not in ("you", "it", "this", "that", "them") and len(target) > 2:
            slug = re.sub(r"[^\w]+", "_", target.lower())[:30].strip("_")
            memories.append({
                "category": "preference",
                "memory_key": slug or "likes",
                "memory_val": f"Loves {target}",
                "emotional_tag": "happy",
                "event_date": ""
            })

    # 5. Preferences: Dislikes / Hates
    for m in re.finditer(
        r"\b(?:i\s+)?(hate|dislike|can't stand|cant stand)\s+([^,.?!;\n]+?)(?=(?:\s+(?:and|but|also|or|with|if)\b|[,.?!;]|$))",
        t,
        re.IGNORECASE
    ):
        target = m.group(2).strip()
        if target.lower() not in ("you", "it", "this", "that", "them") and len(target) > 2:
            slug = re.sub(r"[^\w]+", "_", target.lower())[:30].strip("_")
            memories.append({
                "category": "preference",
                "memory_key": slug or "dislikes",
                "memory_val": f"Dislikes {target}",
                "emotional_tag": "",
                "event_date": ""
            })

    # 6. Preferences: Style / Banter
    for m in re.finditer(
        r"\b(?:i\s+)?(?:really\s+)?(prefer|rather have)\s+([^,.?!;\n]+?)(?=(?:\s+(?:and|but|also|or|with|if)\b|[,.?!;]|$))",
        t,
        re.IGNORECASE
    ):
        target = m.group(2).strip()
        if len(target) > 2:
            slug = re.sub(r"[^\w]+", "_", target.lower())[:30].strip("_")
            memories.append({
                "category": "preference",
                "memory_key": slug or "preference",
                "memory_val": f"Prefers {target}",
                "emotional_tag": "",
                "event_date": ""
            })

    # 7. Personal Facts: Preferred Name
    m_name = re.search(r"\b(?:call me|my name is)\s+([A-Z][a-zA-Z]{1,20})\b", t, re.IGNORECASE)
    if m_name:
        name_val = m_name.group(1).strip()
        memories.append({
            "category": "fact",
            "memory_key": "preferred_name",
            "memory_val": f"User's name is {name_val}",
            "emotional_tag": "",
            "event_date": ""
        })

    return memories


# Alias for backward and test compatibility
extract_memories_offline = extract_memories_heuristic


# ============================================================================
# Optional Online LLM Fallback & Unified Extractor
# ============================================================================

async def extract_memories_llm(text: str) -> Optional[List[Dict[str, Any]]]:
    """
    Attempts online extraction via LLM if Gemini API key and client are configured.
    Returns None immediately if offline or on timeout/exception.
    """
    try:
        from config import GEMINI_API_KEY
        if not GEMINI_API_KEY:
            return None
        from ai_engine import ai_client
        if not ai_client:
            return None

        prompt = (
            "Extract personal facts, upcoming events, emotional states, and user preferences "
            "from this user message. Return a strict JSON array of objects with keys: "
            "'category' (one of: 'event', 'emotion', 'preference', 'fact'), "
            "'memory_key' (short snake_case key), 'memory_val' (clean descriptive sentence), "
            "'emotional_tag' ('stressed', 'anxious', 'excited', 'sad', 'happy', or empty), "
            "'event_date' (YYYY-MM-DD or empty string).\n"
            f"Message: {text}\nJSON:"
        )

        response = await asyncio.wait_for(
            asyncio.to_thread(
                ai_client.models.generate_content,
                model="gemini-2.5-flash",
                contents=prompt
            ),
            timeout=3.0
        )
        if response and response.text:
            cleaned = response.text.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\n?|\n?```$", "", cleaned, flags=re.MULTILINE)
            data = json.loads(cleaned)
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return None


async def extract_memories(
    text: str, 
    use_llm_if_available: bool = False,
    reference_date: Optional[date] = None
) -> List[Dict[str, Any]]:
    """
    Unified extraction interface:
    - If use_llm_if_available is True, attempts online LLM extraction.
    - Seamlessly falls back to 100% offline heuristic parser.
    """
    if use_llm_if_available:
        llm_results = await extract_memories_llm(text)
        if llm_results:
            return llm_results
    return extract_memories_heuristic(text, reference_date=reference_date)


# ============================================================================
# Non-Blocking Background Storage Worker
# ============================================================================

async def extract_and_store_memories_async(
    user_id: int, 
    user_message: str, 
    assistant_reply: str = ""
) -> None:
    """
    Non-blocking background worker designed for asyncio.create_task().
    Extracts memories from user turns and atomically persists them via database.py.
    Runs asynchronously with zero latency impact on live calls or chat turns.
    Exceptions are safely handled and logged to prevent crashing background event loops.
    """
    if not user_id or not user_message or not isinstance(user_message, str):
        return

    try:
        extracted = await extract_memories(user_message, use_llm_if_available=False)
        if not extracted:
            return

        from database import add_or_update_memory
        for item in extracted:
            add_or_update_memory(
                user_id=user_id,
                category=item.get("category", "fact"),
                memory_key=item.get("memory_key", "general"),
                memory_val=item.get("memory_val", ""),
                emotional_tag=item.get("emotional_tag", ""),
                event_date=item.get("event_date", "")
            )
    except Exception as e:
        logger.warning(f"Background memory extraction failed for user {user_id}: {e}")


# Alias for backward and test compatibility
extract_memories_async = extract_and_store_memories_async
