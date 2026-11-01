#!/usr/bin/env python3
"""
Automated Test Suite for Joy Bot Campus Daily Vibe & Leaderboard Engine.
Validates:
1. generate_daily_campus_vibe determinism, bounds (75-99% energy), and schema integrity.
2. handle_vibe_command UI formatting, streak integration, and viral share URL generation.
3. get_campus_leaderboard and get_user_rank query accuracy, sorting, and edge cases.
4. handle_leaderboard_menu privacy masking, medal icons, and toggle between study & streak boards.
5. Fast-path and standard callback routing for menu_vibe and menu_leaderboard.
"""

import os
import sys
import unittest
import tempfile
import asyncio
from unittest.mock import AsyncMock, MagicMock

# Force offline test environment
os.environ["OFFLINE_TEST"] = "1"
os.environ["ALLOW_TEST_USERS"] = "1"
os.environ["BOT_TOKEN"] = "123456:TEST_TOKEN_FOR_VIBE_LEADERBOARD"

# Include parent directory in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if "edge_tts" not in sys.modules:
    sys.modules["edge_tts"] = MagicMock()

import database
from database import (
    init_db,
    get_connection,
    record_user_accepted_terms,
    get_campus_leaderboard,
    get_user_rank,
    get_user_streak_info
)
import app
from app import (
    generate_daily_campus_vibe,
    handle_vibe_command,
    handle_leaderboard_menu,
    handle_callback_query,
    USER_LAST_ACTION
)


class TestVibeAndLeaderboard(unittest.TestCase):
    def setUp(self):
        temp_dir = "/dev/shm" if os.path.exists("/dev/shm") else None
        self.temp_db = tempfile.NamedTemporaryFile(dir=temp_dir, suffix=".db", delete=False)
        self.temp_db_path = self.temp_db.name
        self.temp_db.close()

        self.orig_db_path = database.DB_PATH
        database.DB_PATH = self.temp_db_path
        init_db()

        USER_LAST_ACTION.clear()

        # Seed mock campus students
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (user_id, username, first_name, onboarding_status, is_beta_tester, study_xp, study_questions_answered, streak_count, is_vip, terms_accepted_at)
                VALUES 
                (7001, 'alex_code', 'Alexander', 'completed', 1, 350, 35, 12, 1, '2026-11-01T10:00:00Z'),
                (7002, 'priya_dev', 'Priya', 'completed', 1, 280, 28, 8, 0, '2026-11-01T10:00:00Z'),
                (7003, 'rahul_tech', 'Rahul', 'completed', 1, 150, 15, 20, 1, '2026-11-01T10:00:00Z'),
                (7004, 'neha_ai', 'Neha', 'completed', 1, 90, 9, 3, 0, '2026-11-01T10:00:00Z'),
                (7005, 'novice_user', 'Novice', 'completed', 1, 0, 0, 0, 0, '2026-11-01T10:00:00Z')
            """)
            conn.commit()

        for uid in [7001, 7002, 7003, 7004, 7005]:
            record_user_accepted_terms(uid)

    def tearDown(self):
        database.DB_PATH = self.orig_db_path
        if os.path.exists(self.temp_db_path):
            try:
                os.unlink(self.temp_db_path)
            except OSError:
                pass

    def test_01_vibe_determinism_and_schema(self):
        """Verify daily vibe yields identical values for the same user today, with valid scores and cards."""
        vibe_1 = generate_daily_campus_vibe(7001)
        vibe_2 = generate_daily_campus_vibe(7001)

        # Strict idempotency
        self.assertEqual(vibe_1["energy"], vibe_2["energy"])
        self.assertEqual(vibe_1["card_name"], vibe_2["card_name"])
        self.assertEqual(vibe_1["color"], vibe_2["color"])
        self.assertEqual(vibe_1["prophecy"], vibe_2["prophecy"])

        # Energy score bounded within 75-99%
        self.assertGreaterEqual(vibe_1["energy"], 75)
        self.assertLessEqual(vibe_1["energy"], 99)
        self.assertEqual(len(vibe_1["energy_bar"]), 10)

        # Check required schema keys
        required_keys = ["date_str", "energy", "energy_bar", "color", "element", "card_name", "card_desc", "card_tag", "prophecy"]
        for k in required_keys:
            self.assertIn(k, vibe_1)
            self.assertTrue(bool(vibe_1[k]), f"Key {k} is empty")

    def test_02_handle_vibe_command_ui_and_share_url(self):
        """Verify handle_vibe_command formats card cleanly and includes viral telegram share URL."""
        bot = MagicMock()
        bot.send_message = AsyncMock(return_value={"message_id": 1122, "ok": True})
        bot.edit_message_text = AsyncMock(return_value={"ok": True})

        user = {"user_id": 7001, "first_name": "Alexander"}
        asyncio.run(handle_vibe_command(bot, chat_id=7001, user=user))

        bot.send_message.assert_called_once()
        args, kwargs = bot.send_message.call_args
        sent_text = args[1]
        reply_markup = kwargs.get("reply_markup", {})

        self.assertIn("Campus Vibe & Daily Tarot", sent_text)
        self.assertIn("Campus Energy Meter", sent_text)
        self.assertIn("Joy's Morning Prophecy", sent_text)

        # Verify share button URL
        inline_kb = reply_markup.get("inline_keyboard", [])
        share_btn = inline_kb[0][0]
        self.assertIn("Share Vibe", share_btn["text"])
        self.assertIn("https://t.me/share/url", share_btn["url"])
        self.assertIn("joyfun_ai_bot", share_btn["url"])

    def test_03_leaderboard_query_and_user_rank(self):
        """Verify get_campus_leaderboard returns correct ordering and get_user_rank accurately reflects positions."""
        # Study leaderboard: 7001 (350 XP) > 7002 (280 XP) > 7003 (150 XP) > 7004 (90 XP)
        study_board = get_campus_leaderboard(category="study")
        self.assertEqual(len(study_board), 4)
        self.assertEqual(study_board[0]["user_id"], 7001)
        self.assertEqual(study_board[1]["user_id"], 7002)
        self.assertEqual(study_board[2]["user_id"], 7003)
        self.assertEqual(study_board[3]["user_id"], 7004)

        # User ranks
        rank_1 = get_user_rank(7001, category="study")
        self.assertEqual(rank_1["rank"], 1)
        self.assertEqual(rank_1["score"], 350)

        rank_3 = get_user_rank(7003, category="study")
        self.assertEqual(rank_3["rank"], 3)
        self.assertEqual(rank_3["score"], 150)

        # Unranked user (0 XP)
        rank_unranked = get_user_rank(7005, category="study")
        self.assertIsNone(rank_unranked["rank"])
        self.assertEqual(rank_unranked["score"], 0)

        # Streak leaderboard: 7003 (20 days) > 7001 (12 days) > 7002 (8 days) > 7004 (3 days)
        streak_board = get_campus_leaderboard(category="streak")
        self.assertEqual(len(streak_board), 4)
        self.assertEqual(streak_board[0]["user_id"], 7003)
        self.assertEqual(streak_board[1]["user_id"], 7001)

        streak_rank_1 = get_user_rank(7003, category="streak")
        self.assertEqual(streak_rank_1["rank"], 1)
        self.assertEqual(streak_rank_1["score"], 20)

    def test_04_handle_leaderboard_menu_privacy_and_medals(self):
        """Verify handle_leaderboard_menu displays privacy masking, medals, and caller highlight."""
        bot = MagicMock()
        bot.send_message = AsyncMock(return_value={"message_id": 3344, "ok": True})
        bot.edit_message_text = AsyncMock(return_value={"ok": True})

        user = {"user_id": 7002, "first_name": "Priya"}
        asyncio.run(handle_leaderboard_menu(bot, chat_id=7002, user=user, category="study"))

        bot.send_message.assert_called_once()
        args, kwargs = bot.send_message.call_args
        sent_text = args[1]
        reply_markup = kwargs.get("reply_markup", {})

        # Should contain medals
        self.assertIn("🥇", sent_text)
        self.assertIn("🥈", sent_text)

        # 7001 Alexander should be masked as Ale***
        self.assertIn("Ale***", sent_text)

        # 7002 Priya is the caller and should be highlighted
        self.assertIn("Priya (You)", sent_text)

        # Toggle button should switch to streak
        toggle_btn = reply_markup["inline_keyboard"][0][0]
        self.assertEqual(toggle_btn["callback_data"], "lead_streak")

    def test_05_callback_routing_menu_vibe_and_leaderboard(self):
        """Verify callback query routing for menu_vibe and menu_leaderboard dispatches cleanly."""
        bot = MagicMock()
        bot.answer_callback_query = AsyncMock()
        bot.send_message = AsyncMock(return_value={"message_id": 5566, "ok": True})
        bot.edit_message_text = AsyncMock(return_value={"ok": True})

        # Test menu_vibe
        USER_LAST_ACTION.clear()
        cq_vibe = {
            "id": "cq_vibe_1",
            "from": {"id": 7001, "first_name": "Alexander"},
            "message": {"message_id": 5566, "chat": {"id": 7001}},
            "data": "menu_vibe"
        }
        asyncio.run(handle_callback_query(bot, cq_vibe))
        bot.answer_callback_query.assert_called_once()

        # Test menu_leaderboard
        USER_LAST_ACTION.clear()
        bot.answer_callback_query.reset_mock()
        cq_lead = {
            "id": "cq_lead_1",
            "from": {"id": 7001, "first_name": "Alexander"},
            "message": {"message_id": 5566, "chat": {"id": 7001}},
            "data": "menu_leaderboard"
        }
        asyncio.run(handle_callback_query(bot, cq_lead))
        bot.answer_callback_query.assert_called_once()


if __name__ == "__main__":
    unittest.main()
