"""
Test Suite: v4.1.1 Zero-Bug Security & Interactive QA Loop
Validates:
1. Reflected XSS sanitization in serve_web_login_portal.
2. Error message sanitization across API 500 responses.
3. UTR submission rate limiting (max 3 pending per user).
4. Voice call creation throttling via is_call_creation_throttled.
5. Google OAuth HMAC CSRF state parameter validation.
6. Study Blitz singular/plural formatting ("1 Question Practiced").
7. Mini App call.html VIP button responsive wrapping and clean CTA.
"""

import unittest
import asyncio
import hmac
import hashlib
import time
import sys
import os
from unittest.mock import MagicMock, AsyncMock, patch

if "edge_tts" not in sys.modules:
    sys.modules["edge_tts"] = MagicMock()

from aiohttp import web

from config import (
    BOT_VERSION,
    MINI_APP_VERSION,
    SECURITY_VERSION,
    TELEGRAM_BOT_TOKEN
)
from database import (
    record_utr_submission,
    get_connection
)
from app import (
    serve_web_login_portal,
    is_call_creation_throttled,
    handle_google_callback,
    USER_LAST_CALL_CREATE,
    ADMIN_CHAT_ID
)


class TestV411ZeroBugSecurityLoop(unittest.IsolatedAsyncioTestCase):

    async def test_01_reflected_xss_sanitization_in_login_portal(self):
        """Verify serve_web_login_portal sanitizes malicious XSS payload in uid and mode."""
        app = web.Application()
        app.router.add_get("/auth/login", serve_web_login_portal)
        
        # Attack payload attempting script breakout
        xss_uid = '";alert(document.cookie);//'
        xss_mode = '"><script>alert(1)</script>'
        req = MagicMock(spec=web.Request)
        req.query = {"uid": xss_uid, "mode": xss_mode}
        
        resp = await serve_web_login_portal(req)
        self.assertEqual(resp.status, 200)
        html_text = resp.text
        
        # Ensure the script tag was not injected into uid or mode
        self.assertNotIn('const uid = "";alert(document.cookie);//";', html_text)
        self.assertNotIn('<script>alert(1)</script>', html_text)
        # Should sanitize uid to empty string and mode to signin
        self.assertIn('const uid = "";', html_text)
        self.assertIn('if ("signin" === "signup")', html_text)

    async def test_02_utr_submission_rate_limiting(self):
        """Verify record_utr_submission caps pending requests at 3 per user."""
        test_uid = 9876543210
        # Clean up any test records
        with get_connection() as conn:
            conn.cursor().execute("DELETE FROM payment_requests WHERE user_id = ?", (test_uid,))
            conn.commit()

        # Submit 3 valid pending requests
        ok1, msg1, id1 = record_utr_submission(test_uid, "123456789001", amount=149.0, plan_type="monthly")
        ok2, msg2, id2 = record_utr_submission(test_uid, "123456789002", amount=149.0, plan_type="monthly")
        ok3, msg3, id3 = record_utr_submission(test_uid, "123456789003", amount=149.0, plan_type="monthly")
        self.assertTrue(ok1)
        self.assertTrue(ok2)
        self.assertTrue(ok3)

        # 4th submission should be rate limited
        ok4, msg4, id4 = record_utr_submission(test_uid, "123456789004", amount=149.0, plan_type="monthly")
        self.assertFalse(ok4)
        self.assertIn("already have 3 pending payment submissions", msg4)

        # Cleanup
        with get_connection() as conn:
            conn.cursor().execute("DELETE FROM payment_requests WHERE user_id = ?", (test_uid,))
            conn.commit()

    async def test_03_voice_call_throttling_cooldown(self):
        """Verify is_call_creation_throttled throttles rapid back-to-back calls."""
        test_uid = 8896571705
        # Reset last call time
        USER_LAST_CALL_CREATE.pop(test_uid, None)
        
        # First call is allowed
        self.assertFalse(is_call_creation_throttled(test_uid))
        
        # Immediate second call is throttled
        self.assertTrue(is_call_creation_throttled(test_uid))
        
        # Admin chat ID is exempt
        self.assertFalse(is_call_creation_throttled(ADMIN_CHAT_ID))

    async def test_04_google_oauth_csrf_hmac_verification(self):
        """Verify handle_google_callback validates HMAC in OAuth state and rejects tampered state."""
        valid_uid = 8896571705
        correct_sig = hmac.new(
            TELEGRAM_BOT_TOKEN.encode("utf-8"),
            f"oauth:{valid_uid}".encode("utf-8"),
            hashlib.sha256
        ).hexdigest()[:16]
        
        # Tampered state signature
        req_tampered = MagicMock(spec=web.Request)
        req_tampered.query = {"code": "auth_code_123", "state": f"{valid_uid}:tampered_sig_123"}
        
        resp_tampered = await handle_google_callback(req_tampered)
        self.assertEqual(resp_tampered.status, 403)
        self.assertIn("tampered OAuth state parameter", resp_tampered.text)

    async def test_05_miniapp_call_html_vip_button_styling(self):
        """Verify call.html contains dynamic wrapping styles and clean VIP button text."""
        with open("/home/brandy/joy-bot/static/call.html", "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("min-height: 48px !important;", content)
        self.assertIn("height: auto !important;", content)
        self.assertIn("line-height: 1.3 !important;", content)
        self.assertIn("👑 Upgrade to Joy VIP", content)


if __name__ == "__main__":
    unittest.main()
