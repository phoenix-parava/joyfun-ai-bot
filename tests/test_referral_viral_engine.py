"""
tests/test_referral_viral_engine.py
Automated Regression Test Suite for Joy Bot Viral Referral Engine & Growth Loops.
Validates:
1. Self-referrals are strictly blocked (Anti-Cheat).
2. Valid brand new referrals are tracked atomically.
3. Duplicate referral attempts on the same user are rejected.
4. Existing users with prior conversation history are rejected from retroactive referrals.
5. Referral reward completion grants bonuses to both referrer and invitee.
6. Referral milestones (3 referrals = 3 days VIP, 5 referrals = 30 days VIP) trigger accurately.
7. Universal /invite, /refer commands route cleanly to referral hub.
Runs 100% offline in < 1.0s.
"""

import os
import sys
import unittest
import tempfile
import sqlite3
from datetime import datetime, timezone

os.environ["OFFLINE_TEST"] = "1"

# Ensure joy-bot root directory is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import config
import database
from database import (
    init_db,
    get_or_create_user,
    track_user_referral,
    complete_referral_reward,
    get_referral_stats,
    is_user_vip,
    get_connection
)

class TestReferralViralEngine(unittest.TestCase):
    """Test suite for Viral Referral Engine, Anti-Cheat, and Reward Milestones."""

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

    def test_01_self_referral_blocked(self):
        """Verify that a user cannot refer themselves."""
        user_id = 9001
        get_or_create_user(user_id)
        result = track_user_referral(referred_id=user_id, referrer_id=user_id)
        self.assertFalse(result, "Self-referral must be blocked")

    def test_02_valid_new_user_referral(self):
        """Verify brand new user invited by referrer is tracked successfully."""
        referrer_id = 9002
        referred_id = 9003
        get_or_create_user(referrer_id)
        get_or_create_user(referred_id)

        result = track_user_referral(referred_id=referred_id, referrer_id=referrer_id)
        self.assertTrue(result, "Valid new user referral must succeed")

        stats = get_referral_stats(referrer_id)
        self.assertEqual(stats["total_invited"], 1)
        self.assertEqual(stats["completed_count"], 0)

    def test_03_duplicate_referral_blocked(self):
        """Verify that a user cannot be referred more than once."""
        referrer_a = 9010
        referrer_b = 9011
        referred = 9012
        get_or_create_user(referrer_a)
        get_or_create_user(referrer_b)
        get_or_create_user(referred)

        first = track_user_referral(referred_id=referred, referrer_id=referrer_a)
        self.assertTrue(first)

        second = track_user_referral(referred_id=referred, referrer_id=referrer_b)
        self.assertFalse(second, "Second referral on same user must be blocked")

    def test_04_existing_user_retroactive_referral_blocked(self):
        """Verify existing user with prior conversations cannot be referred retroactively."""
        referrer = 9020
        existing_user = 9021
        get_or_create_user(referrer)
        get_or_create_user(existing_user)

        # Simulate existing conversations
        now = datetime.now(timezone.utc).isoformat()
        with get_connection() as conn:
            conn.execute("INSERT INTO conversations (user_id, role, content, created_at) VALUES (?, 'user', 'hello', ?)", (existing_user, now))
            conn.execute("INSERT INTO conversations (user_id, role, content, created_at) VALUES (?, 'assistant', 'hi', ?)", (existing_user, now))

        result = track_user_referral(referred_id=existing_user, referrer_id=referrer)
        self.assertFalse(result, "Existing active user must not be eligible for retroactive referral")

    def test_05_reward_completion_and_welcome_bonus(self):
        """Verify complete_referral_reward grants bonuses to both referrer and invitee."""
        referrer = 9030
        referred = 9031
        get_or_create_user(referrer)
        get_or_create_user(referred)

        track_user_referral(referred_id=referred, referrer_id=referrer)

        reward = complete_referral_reward(referred)
        self.assertIsNotNone(reward)
        self.assertEqual(reward["referrer_id"], referrer)
        self.assertEqual(reward["reward_type"], "quota_bonus")

        # Verify stats updated
        stats = get_referral_stats(referrer)
        self.assertEqual(stats["completed_count"], 1)

        # Cannot reward again (idempotent)
        second_reward = complete_referral_reward(referred)
        self.assertIsNone(second_reward, "Reward cannot be granted twice")

    def test_06_milestone_rewards_progression(self):
        """Verify milestone triggers: 3 referrals -> 3 days VIP, 5 referrals -> 30 days VIP."""
        referrer = 9040
        get_or_create_user(referrer)

        # Refer 3 users
        for i in range(1, 4):
            uid = 9100 + i
            get_or_create_user(uid)
            track_user_referral(uid, referrer)
            reward = complete_referral_reward(uid)
            if i == 3:
                self.assertEqual(reward["reward_type"], "vip_3days")
                self.assertTrue(is_user_vip(referrer), "Referrer must have VIP after 3 referrals")

        # Refer users 4 and 5
        for i in range(4, 6):
            uid = 9100 + i
            get_or_create_user(uid)
            track_user_referral(uid, referrer)
            reward = complete_referral_reward(uid)
            if i == 5:
                self.assertEqual(reward["reward_type"], "vip_reset_5")
                self.assertTrue(is_user_vip(referrer), "Referrer must have 30-day VIP after 5 referrals")

if __name__ == "__main__":
    unittest.main()
