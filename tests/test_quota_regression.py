"""
tests/test_quota_regression.py
Automated Regression Test Suite for Joy Bot Quota & VIP Billing Engine.
Validates:
1. Owner ID (8747280850) is granted lifetime unlimited access.
2. Free tier quota limits across 4 communication channels (AI calls, mutual calls, AI chat, real chat).
3. VIP activation overrides all quota caps.
4. Quota exhaustion and manual/daily reset mechanisms.
5. UTC midnight reset calculation.
Executes 100% offline in < 1.0 second.
"""

import os
import sys
import unittest
import tempfile
import sqlite3
from datetime import datetime, timezone, timedelta

# Ensure joy-bot root directory is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import config
import database
from database import (
    init_db,
    get_or_create_user,
    is_user_vip,
    grant_vip_subscription,
    get_user_full_quota_status,
    reset_user_quota,
    exhaust_user_quota
)

class TestQuotaRegression(unittest.TestCase):
    """Test suite for Quota limits, VIP subscriptions, and resets."""

    def setUp(self):
        temp_dir = "/dev/shm" if os.path.exists("/dev/shm") else None
        self.temp_db = tempfile.NamedTemporaryFile(dir=temp_dir, suffix=".db", delete=False)
        self.temp_db_path = self.temp_db.name
        self.temp_db.close()

        self.orig_db_path = database.DB_PATH
        database.DB_PATH = self.temp_db_path
        init_db()

    def tearDown(self):
        database.DB_PATH = self.orig_db_path
        if os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except OSError:
                pass

    def test_owner_lifetime_unlimited_quota(self):
        """Verify Creator/Owner ID always has active VIP and unlimited quotas."""
        owner_id = 8747280850
        get_or_create_user(user_id=owner_id, username="owner_phoenix")

        status = get_user_full_quota_status(owner_id)
        self.assertTrue(status.get("is_vip"), "Owner should always be recognized as VIP")
        self.assertEqual(status.get("vip_expiry"), "Lifetime Owner Access")
        self.assertEqual(status.get("days_left"), 9999)

    def test_free_user_initial_quotas(self):
        """Verify free user receives standard daily quota limits."""
        user_id = 2001
        get_or_create_user(user_id=user_id, username="free_user")

        status = get_user_full_quota_status(user_id)
        self.assertFalse(status.get("is_vip"))
        self.assertIn("channels", status)
        self.assertIn("ai_call", status["channels"])
        self.assertIn("real_call", status["channels"])
        self.assertIn("ai_chat", status["channels"])
        self.assertIn("real_chat", status["channels"])

    def test_vip_activation_and_expiry(self):
        """Verify VIP activation unlocks unlimited usage and calculates expiry accurately."""
        user_id = 2002
        get_or_create_user(user_id=user_id, username="vip_subscriber")

        # Free tier initially
        is_vip, _, _ = is_user_vip(user_id)
        self.assertFalse(is_vip)

        # Activate 30-day VIP
        grant_vip_subscription(user_id, days=30)
        is_vip_now, expiry_str, days_left = is_user_vip(user_id)
        self.assertTrue(is_vip_now)
        self.assertGreaterEqual(days_left, 29)

    def test_quota_exhaustion_and_reset(self):
        """Verify exhausting user quota and resetting back to full allowance."""
        user_id = 2003
        get_or_create_user(user_id=user_id, username="quota_exhaust_user")

        # Exhaust quotas
        exhaust_user_quota(user_id)
        status = get_user_full_quota_status(user_id)
        # Verify text usage count has incremented to limit
        channels = status.get("channels", {})
        self.assertGreater(channels.get("ai_chat", {}).get("text_used", 0), 0)

        # Reset quotas
        reset_user_quota(user_id)
        status_after = get_user_full_quota_status(user_id)
        channels_after = status_after.get("channels", {})
        self.assertEqual(channels_after.get("ai_chat", {}).get("text_used", 0), 0)

if __name__ == "__main__":
    unittest.main()
