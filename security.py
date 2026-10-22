"""
Cryptographic Authentication & Zero-Trust Security Middleware
Enforces HMAC-SHA256 Telegram WebApp signature verification and server-side PII filtering.
"""

import hmac
import hashlib
import json
import logging
from urllib.parse import parse_qsl, unquote
from typing import Optional, Dict, Any, Tuple
from config import BOT_TOKEN, PII_PATTERNS

logger = logging.getLogger("AppSecurity")

def validate_telegram_init_data(init_data: str, bot_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Cryptographically validates window.Telegram.WebApp.initData according to Telegram Core specifications.
    Uses HMAC-SHA256 with key derived from b"WebAppData" and bot token.
    Returns: parsed user profile dictionary if signature matches; None if invalid or tampered.
    """
    token = bot_token or BOT_TOKEN
    if not init_data or not token:
        logger.warning("Empty initData or bot token provided for validation.")
        return None

    try:
        parsed_qsl = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed_qsl.pop("hash", None)
        if not received_hash:
            logger.warning("Telegram initData missing 'hash' signature parameter.")
            return None

        # Build data check string sorted alphabetically
        sorted_pairs = [f"{k}={v}" for k, v in sorted(parsed_qsl.items())]
        data_check_string = "\n".join(sorted_pairs)

        # Telegram algorithm: secret_key = HMAC_SHA256(b"WebAppData", token)
        secret_key = hmac.new(b"WebAppData", token.encode("utf-8"), hashlib.sha256).digest()
        computed_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(computed_hash.lower(), received_hash.lower()):
            logger.warning("Telegram initData HMAC-SHA256 verification failed (signature mismatch).")
            return None

        # Parse user JSON payload
        user_raw = parsed_qsl.get("user")
        if user_raw:
            user_data = json.loads(user_raw)
            # Include auth_date and query_id if present
            user_data["auth_date"] = parsed_qsl.get("auth_date")
            user_data["query_id"] = parsed_qsl.get("query_id")
            return user_data

        return {"user_id": int(parsed_qsl.get("user_id", 0))}
    except Exception as e:
        logger.error(f"Error validating Telegram initData: {e}", exc_info=False)
        return None

def sanitize_pii(text: str) -> Tuple[bool, str, Optional[str]]:
    """
    Pre-compiled server-side regex screening against phone numbers, emails,
    Telegram @handles / t.me links, external URLs, and national identity numbers.
    Returns: (is_blocked, filtered_or_original_text, violation_reason)
    """
    if not text:
        return (False, "", None)

    clean_text = text.strip()

    # Scan through compiled patterns
    for pattern in PII_PATTERNS:
        match = pattern.search(clean_text)
        if match:
            matched_val = match.group(0)
            # Differentiate violation type for sanitized logging
            if "@" in matched_val and "." in matched_val:
                reason = "Email Address"
            elif matched_val.startswith("@") or "t.me" in matched_val or "telegram.me" in matched_val:
                reason = "Telegram Handle / Deep Link"
            elif any(proto in matched_val.lower() for proto in ["http", "www."]):
                reason = "External Website Link / URL"
            else:
                reason = "Phone Number / National ID"

            return (
                True,
                "🚫 [Message Blocked — Sharing personal contacts, links, or phone numbers is strictly prohibited.]",
                reason
            )

    return (False, clean_text, None)

def validate_and_clean_pseudonym(name: str) -> Tuple[bool, str]:
    """
    Validates user-defined display name:
    - Must be between 3 and 20 characters
    - Must not contain PII or links
    - Removes HTML tags or script injection
    Returns: (is_valid, cleaned_name)
    """
    if not name:
        return (False, "Anonymous")

    # Strip HTML and control characters
    cleaned = "".join(ch for ch in name if ch.isalnum() or ch in " _-.").strip()
    if len(cleaned) < 3 or len(cleaned) > 20:
        return (False, cleaned[:20] if len(cleaned) >= 3 else "Anonymous")

    is_pii, _, _ = sanitize_pii(cleaned)
    if is_pii:
        return (False, "Anonymous")

    return (True, cleaned)
