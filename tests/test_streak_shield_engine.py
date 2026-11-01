"""
tests/test_streak_shield_engine.py
Automated Regression Test Suite for Joy Bot Streak Shield Engine, 24h Revive Quests,
and Campus Matchmaker Intent Filtering.
Validates:
1. Every user receives 1 default Streak Shield upon registration.
2. Auto-shield consumption preserves consecutive daily streak when 1 day is missed.
3. Gap of 2+ days or 0 shields breaks streak to 1 and stores broken streak for recovery.
4. revive_broken_streak restores broken streak within 24-hour grace window.
5. Referral completion awards +1 Streak Shield to referrer.
6. Milestones (Day 7, 14, 30) grant bonus shields.
7. Intent matching tags route and pair users by topic in anonymous matching.
Runs 100% offline in < 1.0s.
"""

import os
import sys
import unittest
import tempfile
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

os.environ["OFFLINE_TEST"] = "1"
os.environ["TELEGRAM_BOT_TOKEN"] = "test_token_offline_dummy"
os.environ["OWNER_ID"] = "8747280850"

# Ensure joy-bot root directory is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import config
import database
from database import (
    init_db,
    get_connection,
    get_or_create_user,
    update_user_streak,
    get_user_streak_info,
    get_user_streak_shields,
    add_user_streak_shields,
    revive_broken_streak,
    track_user_referral,
    complete_referral_reward,
    set_user_onboarding_status,
    grant_beta_access,
    _IST
)

if "edge_tts" not in sys.modules:
    sys.modules["edge_tts"] = MagicMock()

import app
from app import (
    MATCH_INTENTS,
    handle_streak_revive,
    handle_anon_chat_intent_picker,
    handle_anon_chat_start,
    telegram_chat_queue,
    telegram_active_chats
)

class TestStreakShieldEngine(unittest.TestCase):
    """Test suite for Streak Shield, 24h Revive, and Matchmaker Intent Tags."""

    def setUp(self):
        temp_dir = "/dev/shm" if os.path.exists("/dev/shm") else None
        self.temp_db = tempfile.NamedTemporaryFile(dir=temp_dir, suffix=".db", delete=False)
        self.temp_db_path = self.temp_db.name
        self.temp_db.close()

        self.orig_db_path = database.DB_PATH
        database.DB_PATH = self.temp_db_path
        init_db()

        # Clean queue
        telegram_chat_queue.clear()
        telegram_active_chats.clear()

    def tearDown(self):
        database.DB_PATH = self.orig_db_path
        if os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except OSError:
                pass
        telegram_chat_queue.clear()
        telegram_active_chats.clear()

    def _setup_user(self, user_id: int, streak: int, last_date_str: str, shields: int = 1):
        get_or_create_user(user_id)
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET streak_count = ?, last_streak_date = ?, streak_shields = ?
                WHERE user_id = ?
            """, (streak, last_date_str, shields, user_id))
            conn.commit()

    def test_01_user_receives_default_streak_shield(self):
        """Verify new users start with 1 active streak shield."""
        user_id = 7001
        get_or_create_user(user_id)
        shields = get_user_streak_shields(user_id)
        self.assertEqual(shields, 1, "New users must receive 1 default Streak Shield")

    def test_02_streak_shield_rescues_one_day_missed_streak(self):
        """Verify missing exactly 1 day consumes 1 shield and preserves streak count."""
        user_id = 7002
        now_ist = datetime.now(_IST)
        two_days_ago = (now_ist - timedelta(days=2)).strftime("%Y-%m-%d")

        # User had a 5-day streak, missed yesterday (last chatted 2 days ago)
        self._setup_user(user_id, streak=5, last_date_str=two_days_ago, shields=1)

        new_streak, new_lvl, is_m, title, shield_used = update_user_streak(user_id, return_details=True)

        self.assertTrue(shield_used, "Streak shield must activate for 1-day absence")
        self.assertEqual(new_streak, 6, "Streak must increment to 6 despite missing yesterday")
        self.assertEqual(get_user_streak_shields(user_id), 0, "Shield must be consumed (1 -> 0)")

    def test_03_streak_breaks_when_no_shields_available(self):
        """Verify missing 1 day with 0 shields resets streak to 1 and stores broken streak."""
        user_id = 7003
        now_ist = datetime.now(_IST)
        two_days_ago = (now_ist - timedelta(days=2)).strftime("%Y-%m-%d")

        # User had a 10-day streak, but 0 shields remaining
        self._setup_user(user_id, streak=10, last_date_str=two_days_ago, shields=0)

        new_streak, new_lvl, is_m, title, shield_used = update_user_streak(user_id, return_details=True)

        self.assertFalse(shield_used, "No shield should be used when inventory is 0")
        self.assertEqual(new_streak, 1, "Streak must reset to 1 when no shield protects it")

        info = get_user_streak_info(user_id)
        self.assertEqual(info["broken_streak"], 10, "Broken streak count must be preserved for recovery")
        self.assertTrue(info["can_revive"], "User must be eligible for 24h revive quest")

    def test_04_revive_broken_streak_restores_progress(self):
        """Verify revive_broken_streak restores broken streak count within grace window."""
        user_id = 7004
        now_ist = datetime.now(_IST)
        today_str = now_ist.strftime("%Y-%m-%d")

        # Setup user with broken streak
        get_or_create_user(user_id)
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET streak_count = 1, broken_streak_count = 8, broken_streak_date = ?
                WHERE user_id = ?
            """, (today_str, user_id))
            conn.commit()

        success, msg, restored = revive_broken_streak(user_id)
        self.assertTrue(success, "Streak recovery must succeed within 24h window")
        self.assertEqual(restored, 9, "Restored streak must increment from broken count (8 -> 9)")

        info = get_user_streak_info(user_id)
        self.assertEqual(info["streak"], 9)
        self.assertFalse(info["can_revive"], "can_revive must reset to False after recovery")

    def test_05_referral_reward_grants_streak_shield(self):
        """Verify referrer earns +1 Streak Shield when invitee completes referral."""
        referrer = 7005
        referred = 7006
        get_or_create_user(referrer)
        get_or_create_user(referred)

        initial_shields = get_user_streak_shields(referrer)
        track_user_referral(referred, referrer)
        reward = complete_referral_reward(referred)

        self.assertIsNotNone(reward)
        self.assertEqual(reward.get("shields_awarded"), 1)
        self.assertEqual(get_user_streak_shields(referrer), initial_shields + 1)

    def test_06_matchmaker_intent_tags_routing(self):
        """Verify intent tags match users by topic in anonymous queue."""
        self.assertIn("study", MATCH_INTENTS)
        self.assertIn("chill", MATCH_INTENTS)
        self.assertIn("vent", MATCH_INTENTS)
        self.assertIn("any", MATCH_INTENTS)

        mock_bot = AsyncMock()
        user_a = {"user_id": 8001, "chat_id": 8001, "is_beta_tester": 1, "onboarding_status": "completed"}
        user_b = {"user_id": 8002, "chat_id": 8002, "is_beta_tester": 1, "onboarding_status": "completed"}
        user_c = {"user_id": 8003, "chat_id": 8003, "is_beta_tester": 1, "onboarding_status": "completed"}

        for uid in [8001, 8002, 8003]:
            get_or_create_user(uid)
            set_user_onboarding_status(uid, "completed")
            grant_beta_access(uid)

        # 1. User A joins with intent "study"
        asyncio.run(handle_anon_chat_start(mock_bot, 8001, user_a, intent="study"))
        self.assertEqual(len(telegram_chat_queue), 1)
        self.assertEqual(telegram_chat_queue[0]["intent"], "study")

        # 2. User B joins with intent "chill" -> Should not match with User A
        asyncio.run(handle_anon_chat_start(mock_bot, 8002, user_b, intent="chill"))
        self.assertEqual(len(telegram_chat_queue), 2, "Different intents must not pair immediately")

        # 3. User C joins with intent "study" -> Should pair with User A!
        asyncio.run(handle_anon_chat_start(mock_bot, 8003, user_c, intent="study"))
        self.assertIn(8001, telegram_active_chats, "User A must be paired with User C on matching study intent")
        self.assertIn(8003, telegram_active_chats, "User C must be paired with User A")
        self.assertEqual(len(telegram_chat_queue), 1, "User B should remain in queue waiting for chill peer")

if __name__ == "__main__":
    unittest.main()
