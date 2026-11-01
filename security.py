"""
Joy Bot Security & Cryptographic Handshake Engine
Production-grade HMAC-SHA256 Telegram WebApp validation, PII scrubbing, and session isolation.
"""

import hmac
import hashlib
import json
import logging
import re
import time
from urllib.parse import parse_qsl
from typing import Optional, Dict, Any, Tuple

from config import TELEGRAM_BOT_TOKEN

logger = logging.getLogger("JoySecurity")

# Pre-compiled high-performance regex patterns for Real-Time PII & Sensitive Data Scrubber
EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', re.IGNORECASE)
PHONE_REGEX_1 = re.compile(r'\b(?:(?:\+|00)\d{1,3}[\s.-]?)?(?:\(?\d{2,5}\)?[\s.-]?)?\d{3,5}[\s.-]?\d{4,5}\b')
PHONE_REGEX_2 = re.compile(r'\b[6-9]\d{9}\b')
PHONE_REGEX_3 = re.compile(r'\b(?:\+91|91)[\s-]?[6-9]\d{9}\b')
URL_REGEX = re.compile(r'(?:https?://|www\.)[^\s]+', re.IGNORECASE)
SOCIAL_LINKS_REGEX = re.compile(r'(?:t\.me/|telegram\.me/|wa\.me/|instagram\.com/|snapchat\.com/|facebook\.com/|fb\.com/|wa\.link/|chat\.whatsapp\.com/)[^\s]+', re.IGNORECASE)
TELEGRAM_USERNAME_REGEX = re.compile(r'@([a-zA-Z0-9_]{4,32})')
AADHAAR_REGEX = re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b')
PAN_REGEX = re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b', re.IGNORECASE)
EXCLUDED_SYSTEM_USERNAMES = {"joy_fun_ai_bot", "joyfun_ai_bot", "joy", "here", "everyone", "channel"}

def detect_sensitive_pii(text: str) -> Tuple[bool, str]:
    """
    Scans text for sensitive Personally Identifiable Information (PII) before sending:
    - Phone numbers (10+ digits, Indian/international formats, spaced digits)
    - Email addresses
    - Social media handles / direct messaging links (WhatsApp, Telegram, Instagram, Snapchat, etc.)
    - External URLs and t.me links
    - Identity documents (Aadhaar, PAN)
    Returns (True, violation_reason) if sensitive PII is detected, else (False, "").
    """
    if not text:
        return False, ""
    
    clean = text.strip()

    if EMAIL_REGEX.search(clean):
        return True, "Email Address"

    if URL_REGEX.search(clean) or SOCIAL_LINKS_REGEX.search(clean):
        return True, "External Link / URL"

    for handle in TELEGRAM_USERNAME_REGEX.findall(clean):
        if handle.lower() not in EXCLUDED_SYSTEM_USERNAMES:
            return True, f"Telegram Username (@{handle})"

    if AADHAAR_REGEX.search(clean):
        return True, "National ID (Aadhaar Number)"

    if PAN_REGEX.search(clean):
        return True, "Tax / Identity Card (PAN Number)"

    digits_only = re.sub(r'[^\d]', '', clean)
    if PHONE_REGEX_2.search(clean) or PHONE_REGEX_3.search(clean) or (10 <= len(digits_only) <= 15 and PHONE_REGEX_1.search(clean)):
        return True, "Phone / Mobile Number"

    return False, ""

def sanitize_pii_in_text(text: str) -> str:
    """Replaces detected PII patterns with redacted placeholders."""
    if not text:
        return ""
    clean = EMAIL_REGEX.sub("[email protected]", text)
    clean = URL_REGEX.sub("[link redacted]", clean)
    clean = SOCIAL_LINKS_REGEX.sub("[social link redacted]", clean)
    clean = AADHAAR_REGEX.sub("[id redacted]", clean)
    clean = PAN_REGEX.sub("[pan redacted]", clean)
    clean = PHONE_REGEX_3.sub("[phone redacted]", clean)
    clean = PHONE_REGEX_2.sub("[phone redacted]", clean)
    clean = PHONE_REGEX_1.sub("[phone redacted]", clean)
    return clean

def verify_telegram_init_data(init_data: str, bot_token: Optional[str] = None, max_age_seconds: int = 86400) -> Optional[int]:
    """
    Cryptographically validates window.Telegram.WebApp.initData according to Telegram Core specs.
    Uses HMAC-SHA256 with key derived from b"WebAppData" and bot token.
    
    Returns:
        int: authenticated Telegram user_id if valid
        None: if signature is invalid, missing, or expired
    """
    token = bot_token or TELEGRAM_BOT_TOKEN
    if not init_data or not token:
        return None

    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            return None

        # Verify auth_date freshness
        auth_date = int(parsed.get("auth_date", 0))
        if auth_date > 0 and (time.time() - auth_date > max_age_seconds):
            logger.warning(f"Telegram initData expired (auth_date: {auth_date})")
            return None

        # Build data check string sorted alphabetically
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))

        # Telegram spec: secret_key = HMAC_SHA256(b"WebAppData", token)
        secret_key = hmac.new(b"WebAppData", token.encode("utf-8"), hashlib.sha256).digest()
        computed_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(computed_hash.lower(), received_hash.lower()):
            logger.warning("Telegram initData HMAC-SHA256 signature mismatch.")
            return None

        # Extract user ID
        user_raw = parsed.get("user")
        if user_raw:
            user_obj = json.loads(user_raw)
            uid = int(user_obj.get("id", 0))
            if uid > 0:
                return uid

        user_id_param = int(parsed.get("user_id", 0))
        if user_id_param > 0:
            return user_id_param

        return None
    except Exception as e:
        logger.warning(f"Error verifying Telegram initData: {e}")
        return None
