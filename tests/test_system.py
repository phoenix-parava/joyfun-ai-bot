import asyncio
import os
import sys

# Ensure joy-bot root is in Python module search path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import LANGUAGE_MATRIX, get_icebreaker_list
from security import sanitize_pii, validate_and_clean_pseudonym
from database import (
    init_db,
    get_or_create_user,
    get_user,
    accept_terms,
    complete_onboarding,
    update_user_settings,
    consume_quota,
    get_user_quota_summary,
    DB_PATH
)

async def run_tests():
    print("--- 1. Testing Config Language Matrix ---")
    assert "tier1_bilingual" in LANGUAGE_MATRIX
    assert "tier2_regional" in LANGUAGE_MATRIX
    assert "tier3_global" in LANGUAGE_MATRIX
    assert "tanglish" in LANGUAGE_MATRIX["tier1_bilingual"]["languages"]
    assert "tamil" in LANGUAGE_MATRIX["tier2_regional"]["languages"]
    assert "english" in LANGUAGE_MATRIX["tier3_global"]["languages"]

    icebreakers = get_icebreaker_list("tanglish")
    assert len(icebreakers) >= 5
    print("✅ Language matrix & icebreakers verified!")

    print("\n--- 2. Testing PII Sanitization Regex Filter ---")
    # Phone numbers
    blocked, _, reason = sanitize_pii("Call me at 9876543210 please")
    assert blocked and "phone" in reason.lower(), f"Failed: {reason}"
    blocked, _, reason = sanitize_pii("+91 91234 56789 is my number")
    assert blocked and "phone" in reason.lower()

    # Emails
    blocked, _, reason = sanitize_pii("Contact me at user.test@gmail.com")
    assert blocked and "email" in reason.lower()

    # Telegram @username & t.me
    blocked, _, reason = sanitize_pii("Ping me @awesome_peer")
    assert blocked and "telegram" in reason.lower()
    blocked, _, reason = sanitize_pii("Join t.me/mychannel")
    assert blocked and "telegram" in reason.lower()

    # External URL
    blocked, _, reason = sanitize_pii("Check this out https://example.com/login")
    assert blocked and "url" in reason.lower()

    # Clean text
    blocked, clean_text, reason = sanitize_pii("Hello, how is your day going?")
    assert not blocked
    assert clean_text == "Hello, how is your day going?"
    print("✅ PII sanitization verified across all patterns!")

    print("\n--- 3. Testing Pseudonym Validation ---")
    valid, name = validate_and_clean_pseudonym("ShadowWalker")
    assert valid and name == "ShadowWalker"

    # Too short
    valid, _ = validate_and_clean_pseudonym("ab")
    assert not valid

    # Too long
    valid, _ = validate_and_clean_pseudonym("a" * 25)
    assert not valid

    # PII in pseudonym
    valid, _ = validate_and_clean_pseudonym("Call9876543210")
    assert not valid
    print("✅ Pseudonym validation verified!")

    print("\n--- 4. Testing Async Database Operations ---")
    # Test DB in memory / temp
    await init_db()

    import time
    test_uid = int(time.time()) + 90000000
    user = await get_or_create_user(test_uid, "TestUser")
    assert user["user_id"] == test_uid
    assert user["terms_accepted_at"] is None
    assert user["onboarding_completed"] == 0

    # Accept Terms
    await accept_terms(test_uid)
    user_after_terms = await get_user(test_uid)
    assert user_after_terms["terms_accepted_at"] is not None
    print("✅ Terms acceptance verified!")

    # Complete Onboarding
    await complete_onboarding(
        test_uid,
        pseudonym="StellarKnight",
        language="tanglish",
        modality="voice",
        partner_preference="real_or_ai"
    )
    user_onboarded = await get_user(test_uid)
    assert user_onboarded["pseudonym"] == "StellarKnight"
    assert user_onboarded["language"] == "tanglish"
    assert user_onboarded["onboarding_completed"] == 1
    print("✅ Onboarding persistence verified!")

    # Quota operations
    quotas = await get_user_quota_summary(test_uid)
    assert quotas["p2p_voice"]["remaining"] == 1800
    assert quotas["ai_voice"]["remaining"] == 600
    assert quotas["ai_text"]["remaining"] == 50

    # Consume 60 seconds p2p voice
    allowed, rem, limit = await consume_quota(test_uid, "p2p_voice", 60)
    assert allowed
    assert rem == 1740

    # Consume 1 ai text msg
    allowed, rem, limit = await consume_quota(test_uid, "ai_text", 1)
    assert allowed
    assert rem == 49
    print("✅ Daily Quota system verified!")

    print("\n🎉 ALL ARCHITECTURAL TESTS PASSED CLEANLY!")

if __name__ == "__main__":
    asyncio.run(run_tests())
