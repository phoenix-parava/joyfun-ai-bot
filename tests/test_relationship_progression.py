import os
import sys
import unittest
import tempfile
from datetime import datetime, timezone, timedelta

os.environ["OFFLINE_TEST"] = "1"

# Ensure joy-bot root directory is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import database
from database import (
    init_db,
    get_connection,
    get_or_create_user,
    update_user_streak,
    get_user_streak_info,
    is_user_vip,
    _IST
)
from ai_engine import resolve_relationship_instruction

class TestRelationshipProgression(unittest.TestCase):
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

    def _setup_user_with_streak(self, user_id: int, streak: int, last_date_str: str):
        get_or_create_user(user_id)
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET streak_count = ?, last_streak_date = ?
                WHERE user_id = ?
            """, (streak, last_date_str, user_id))
            conn.commit()

    def test_01_relationship_instruction_calibration(self):
        """Verify dynamic prompt intimacy escalates across relationship tiers."""
        inst_day1 = resolve_relationship_instruction(1)
        self.assertIn("Level 1: New Acquaintance", inst_day1)
        self.assertIn("polite", inst_day1.lower())

        inst_day3 = resolve_relationship_instruction(3)
        self.assertIn("Level 2: Good Friends", inst_day3)
        self.assertIn("warm", inst_day3.lower())

        inst_day7 = resolve_relationship_instruction(7)
        self.assertIn("Level 3: Close Bestie & Confidant", inst_day7)
        self.assertIn("teasing", inst_day7.lower())

        inst_day14 = resolve_relationship_instruction(14)
        self.assertIn("Level 4: Special Soul Connection", inst_day14)
        self.assertIn("intimate confidantes", inst_day14.lower())

        inst_day30 = resolve_relationship_instruction(30)
        self.assertIn("Level 5: Soulmate / Eternal Bond", inst_day30)
        self.assertIn("unbreakable", inst_day30.lower())

    def test_02_streak_info_progress_bar_math(self):
        """Verify progress bar and percentage calculation to next milestone."""
        user_id = 9001
        self._setup_user_with_streak(user_id, streak=1, last_date_str="2026-10-31")

        info = get_user_streak_info(user_id)
        self.assertEqual(info["streak"], 1)
        self.assertEqual(info["next_target"], 3)
        self.assertEqual(info["days_needed"], 2)
        self.assertEqual(info["progress_pct"], 33)
        self.assertIn("░", info["progress_bar"])

        # Update to streak 3
        with get_connection() as conn:
            conn.cursor().execute("UPDATE users SET streak_count = 3 WHERE user_id = ?", (user_id,))
            conn.commit()

        info3 = get_user_streak_info(user_id)
        self.assertEqual(info3["streak"], 3)
        self.assertEqual(info3["next_target"], 7)
        self.assertEqual(info3["days_needed"], 4)
        self.assertEqual(info3["progress_pct"], 0)

        # Update to streak 30 (Max Level)
        with get_connection() as conn:
            conn.cursor().execute("UPDATE users SET streak_count = 30 WHERE user_id = ?", (user_id,))
            conn.commit()

        info30 = get_user_streak_info(user_id)
        self.assertEqual(info30["streak"], 30)
        self.assertIsNone(info30["next_target"])
        self.assertEqual(info30["days_needed"], 0)
        self.assertEqual(info30["progress_pct"], 100)
        self.assertEqual(info30["progress_bar"], "████████████████")

    def test_03_ist_streak_progression_consecutive_days(self):
        """Verify consecutive daily chats in IST increment streak and calculate properly."""
        user_id = 9002
        now_ist = datetime.now(_IST)
        yesterday_str = (now_ist - timedelta(days=1)).strftime("%Y-%m-%d")

        self._setup_user_with_streak(user_id, streak=2, last_date_str=yesterday_str)

        new_streak, new_level, is_milestone, level_title = update_user_streak(user_id)
        self.assertEqual(new_streak, 3)
        self.assertTrue(is_milestone)
        self.assertEqual(level_title, "🌸 Good Friends")

        # Same day interaction does not re-increment
        new_streak2, _, is_m2, _ = update_user_streak(user_id)
        self.assertEqual(new_streak2, 3)
        self.assertFalse(is_m2)

    def test_04_broken_streak_resets_to_one(self):
        """Verify gap of 2 or more days in IST resets streak to 1."""
        user_id = 9003
        now_ist = datetime.now(_IST)
        three_days_ago = (now_ist - timedelta(days=3)).strftime("%Y-%m-%d")

        self._setup_user_with_streak(user_id, streak=10, last_date_str=three_days_ago)

        new_streak, new_level, is_milestone, level_title = update_user_streak(user_id)
        self.assertEqual(new_streak, 1)
        self.assertFalse(is_milestone)
        self.assertEqual(level_title, "🌱 New Acquaintance")

    def test_05_milestone_rewards_auto_allocation(self):
        """Verify Day 3, 7, 14, 30 trigger milestone flags and Day 30 awards VIP pass."""
        now_ist = datetime.now(_IST)
        yesterday_str = (now_ist - timedelta(days=1)).strftime("%Y-%m-%d")

        # 1. Day 3 Milestone
        u3 = 9004
        self._setup_user_with_streak(u3, streak=2, last_date_str=yesterday_str)
        s3, _, m3, _ = update_user_streak(u3)
        self.assertEqual(s3, 3)
        self.assertTrue(m3)

        # 2. Day 7 Milestone
        u7 = 9005
        self._setup_user_with_streak(u7, streak=6, last_date_str=yesterday_str)
        s7, _, m7, _ = update_user_streak(u7)
        self.assertEqual(s7, 7)
        self.assertTrue(m7)

        # 3. Day 14 Milestone
        u14 = 9006
        self._setup_user_with_streak(u14, streak=13, last_date_str=yesterday_str)
        s14, _, m14, _ = update_user_streak(u14)
        self.assertEqual(s14, 14)
        self.assertTrue(m14)

        # 4. Day 30 Milestone (7 Days Free VIP Pass)
        u30 = 9007
        self._setup_user_with_streak(u30, streak=29, last_date_str=yesterday_str)
        self.assertFalse(is_user_vip(u30)[0])
        s30, _, m30, _ = update_user_streak(u30)
        self.assertEqual(s30, 30)
        self.assertTrue(m30)
        self.assertTrue(is_user_vip(u30)[0], "Day 30 milestone must grant VIP subscription")

if __name__ == "__main__":
    unittest.main()
