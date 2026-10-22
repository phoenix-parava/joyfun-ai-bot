"""
Unified Production Configuration & Core Registries
Architected for high efficiency, zero-redundancy, and strict memory budgeting.
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, List

BASE_DIR = Path(__file__).resolve().parent

# --- Environment Variables ---
BOT_TOKEN = (os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID") or os.getenv("OWNER_ID") or "8747280850")
CREATOR_TELEGRAM_HANDLE = os.getenv("CREATOR_TELEGRAM_HANDLE", "phoenix_parava_0").strip().lstrip("@")
AI_API_KEY = (os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()
PORT = int(os.getenv("PORT") or "8080")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip().rstrip("/")
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://joyfun-ai-bot.onrender.com").strip().rstrip("/")
TURN_SERVER_URL = os.getenv("TURN_SERVER_URL", "stun:stun.l.google.com:19302").strip()

# Database Path
DB_PATH = BASE_DIR / "app_data.db"

# Server-Authoritative Daily Quota Caps
DAILY_P2P_VOICE_SECONDS = int(os.getenv("DAILY_P2P_VOICE_SECONDS", "1800"))  # 30 mins/day
DAILY_AI_VOICE_SECONDS = int(os.getenv("DAILY_AI_VOICE_SECONDS", "600"))     # 10 mins/day
DAILY_AI_TEXT_MESSAGES = int(os.getenv("DAILY_AI_TEXT_MESSAGES", "50"))      # 50 msgs/day

# WebRTC STUN/TURN Ice Servers
RTC_ICE_SERVERS = [
    {"urls": "stun:stun.l.google.com:19302"},
    {"urls": "stun:stun1.l.google.com:19302"},
]
if TURN_SERVER_URL and not TURN_SERVER_URL.startswith("stun:"):
    RTC_ICE_SERVERS.append({"urls": TURN_SERVER_URL})

# --- Three-Tier Language Matrix ---
class LanguageMatrix(dict):
    """Hybrid dictionary that supports both tier-level grouping and direct language lookups."""
    def get(self, key, default=None):
        if key in self:
            return super().get(key)
        for tier_data in self.values():
            if isinstance(tier_data, dict) and "languages" in tier_data:
                if key in tier_data["languages"]:
                    return tier_data["languages"][key]
        return default

    def __getitem__(self, key):
        if key in self:
            return super().__getitem__(key)
        for tier_data in self.values():
            if isinstance(tier_data, dict) and "languages" in tier_data:
                if key in tier_data["languages"]:
                    return tier_data["languages"][key]
        raise KeyError(key)

LANGUAGE_MATRIX = LanguageMatrix({
    "tier1_bilingual": {
        "label": "Tier 1: Code-Switched Bilingual Hybrids",
        "languages": {
            "tanglish": {"tier": 1, "name": "Tamil + English (Tanglish)", "native": "Tanglish", "code": "ta-EN"},
            "hinglish": {"tier": 1, "name": "Hindi + English (Hinglish)", "native": "Hinglish", "code": "hi-EN"},
            "telugish": {"tier": 1, "name": "Telugu + English (Telugish)", "native": "Telugish", "code": "te-EN"},
            "manglish": {"tier": 1, "name": "Malayalam + English (Manglish)", "native": "Manglish", "code": "ml-EN"},
            "kanglish": {"tier": 1, "name": "Kannada + English (Kanglish)", "native": "Kanglish", "code": "kn-EN"},
            "benglish": {"tier": 1, "name": "Bengali + English (Benglish)", "native": "Benglish", "code": "bn-EN"},
        }
    },
    "tier2_regional": {
        "label": "Tier 2: Pure Native Regional Languages",
        "languages": {
            "tamil": {"tier": 2, "name": "Tamil", "native": "தமிழ்", "code": "ta"},
            "hindi": {"tier": 2, "name": "Hindi", "native": "हिन्दी", "code": "hi"},
            "telugu": {"tier": 2, "name": "Telugu", "native": "తెలుగు", "code": "te"},
            "malayalam": {"tier": 2, "name": "Malayalam", "native": "മലയാളം", "code": "ml"},
            "kannada": {"tier": 2, "name": "Kannada", "native": "ಕನ್ನಡ", "code": "kn"},
            "marathi": {"tier": 2, "name": "Marathi", "native": "मराठी", "code": "mr"},
            "bengali": {"tier": 2, "name": "Bengali", "native": "বাংলা", "code": "bn"},
            "urdu": {"tier": 2, "name": "Urdu", "native": "اردو", "code": "ur"},
        }
    },
    "tier3_global": {
        "label": "Tier 3: Global Languages",
        "languages": {
            "english": {"tier": 3, "name": "English (Only English)", "native": "English", "code": "en"},
            "spanish": {"tier": 3, "name": "Spanish", "native": "Español", "code": "es"},
            "french": {"tier": 3, "name": "French", "native": "Français", "code": "fr"},
            "arabic": {"tier": 3, "name": "Arabic", "native": "العربية", "code": "ar"},
            "portuguese": {"tier": 3, "name": "Portuguese", "native": "Português", "code": "pt"},
            "russian": {"tier": 3, "name": "Russian", "native": "Русский", "code": "ru"},
            "indonesian": {"tier": 3, "name": "Indonesian", "native": "Bahasa Indonesia", "code": "id"},
        }
    }
})

DEFAULT_LANGUAGE = "tanglish"

# --- Compiled Server-Side PII Regular Expressions ---
# Scans for phone numbers (10-15 digits), emails, telegram usernames/links, and URLs
PII_PATTERNS = [
    # Phone numbers: 10 to 15 digit patterns with international prefixes or standard separators
    re.compile(r'(?:(?:\+|00)\d{1,3}[-.\s]?)?(?:\(?\d{2,5}\)?[-.\s]?)?\d{3,5}[-.\s]?\d{4,6}\b', re.ASCII),
    re.compile(r'\b(?:\d[-.\s]?){9,14}\d\b'),
    # Email addresses
    re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', re.IGNORECASE),
    # Telegram handles and deep links
    re.compile(r'(?:@|(?:https?:\/\/)?(?:t|telegram)\.me\/)[a-zA-Z0-9_]{4,32}\b', re.IGNORECASE),
    # External URLs & IP addresses
    re.compile(r'(?:https?:\/\/|www\.)[^\s/$.?#].[^\s]*', re.IGNORECASE),
    # Common Aadhaar / ID formats
    re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
]

# --- Bilingual Topic Icebreaker Deck ---
# Transmitted over RTCDataChannel in real-time during P2P sessions
ICEBREAKER_DECKS: Dict[str, List[str]] = {
    "tanglish": [
        "Unakku pudicha late-night comfort food enna? Maggie ah illa biryani ah?",
        "If you could travel anywhere right now without money constraints, enga pove?",
        "College or work la recently ungalukku nadandha funny incident enna?",
        "Tech vs Cinema: What's the one thing you can talk about for hours?",
        "What is your ultimate go-to song when you need to recharge your mood?",
    ],
    "hinglish": [
        "Late-night food craving me chai-maggi ya street food? What's your vibe?",
        "Aapki bucket list ki top 1 destination kaunsi hai abhi?",
        "Recently aisi kaunsi movie ya series dekhi jo dil ko chhu gayi?",
        "Agar kal se pura 1 mahina free mil jaye, kya karoge?",
        "Ek aisa song jo har mood ko instantly uplift kar deta hai?",
    ],
    "english": [
        "What's a project, passion, or hobby you can talk about effortlessly for hours?",
        "If you could teleport to any city in the world right now for 24 hours, where would you go?",
        "What's the best piece of advice you've received that actually worked for you?",
        "What's your ultimate comfort habit after a long, exhausting day?",
        "If you had the chance to master any skill instantly, what would it be?",
    ],
    "general": [
        "What is something exciting that happened in your week so far?",
        "If you had to pick one meal to eat for the rest of your life, what would it be?",
        "What's a movie or series you can re-watch endless times without getting bored?",
        "Morning person or night owl? How do your best productive hours look?",
        "What's the most memorable travel trip you've ever taken?",
    ]
}

def get_icebreaker_list(language: str) -> List[str]:
    """Returns curated topic cards for matched language or falls back to general deck."""
    clean_lang = language.lower().strip()
    return ICEBREAKER_DECKS.get(clean_lang) or ICEBREAKER_DECKS.get("general", [])
