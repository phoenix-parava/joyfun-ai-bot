#!/usr/bin/env python3
"""
Automated Test Suite for Campus Study Arena & Procedural Ambient Soundscapes.
Validates:
1. Scholar Tier XP progression and level calculations in database.
2. Placement & Exam Blitz decks structure, options count, and answer index integrity.
3. Study Hub menu generation with scholar stats banner.
4. Deck question picker and answer validation callback routing (+10 XP correct, +2 XP effort).
5. Web Audio API Procedural Ambient Soundscape markup, styles, and classes in static/call.html.
"""

import os
import sys
import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# Force test configuration
os.environ["OFFLINE_TEST"] = "1"
os.environ["ALLOW_TEST_USERS"] = "1"
os.environ["BOT_TOKEN"] = "123456:TEST_TOKEN_FOR_STUDY_ARENA"

# Include parent directory in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if "edge_tts" not in sys.modules:
    sys.modules["edge_tts"] = MagicMock()

import database
from database import (
    init_db,
    get_connection,
    record_study_quiz_attempt,
    get_user_study_stats,
    record_user_accepted_terms,
    set_user_onboarding_status,
    grant_beta_access,
)
from app import (
    CAMPUS_STUDY_DECKS,
    handle_study_menu,
    handle_callback_query
)
import tempfile


class TestCampusStudyArena(unittest.TestCase):
    def setUp(self):
        temp_dir = "/dev/shm" if os.path.exists("/dev/shm") else None
        self.temp_db = tempfile.NamedTemporaryFile(dir=temp_dir, suffix=".db", delete=False)
        self.temp_db_path = self.temp_db.name
        self.temp_db.close()

        self.orig_db_path = database.DB_PATH
        database.DB_PATH = self.temp_db_path
        init_db()

        # Clear throttle cache for clean test runs
        from app import USER_LAST_ACTION
        USER_LAST_ACTION.clear()

        self.test_user_id = 99887711
        record_user_accepted_terms(self.test_user_id)
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO users (user_id, username, first_name, onboarding_status, is_beta_tester, study_xp, study_questions_answered, terms_accepted_at)
                VALUES (?, 'test_scholar', 'ScholarTest', 'completed', 1, 0, 0, '2026-11-01T10:00:00Z')
            """, (self.test_user_id,))
            conn.commit()

    def tearDown(self):
        database.DB_PATH = self.orig_db_path
        if os.path.exists(self.temp_db_path):
            try:
                os.unlink(self.temp_db_path)
            except OSError:
                pass

    def test_01_study_xp_progression_and_level_up(self):
        """Verify XP increments correctly (+10 correct, +2 wrong) and triggers level-up every 100 XP."""
        # Initial stats
        stats = get_user_study_stats(self.test_user_id)
        self.assertEqual(stats["study_xp"], 0)
        self.assertEqual(stats["total_answered"], 0)
        self.assertEqual(stats["level"], 1)
        self.assertEqual(stats["xp_to_next"], 100)

        # 1 correct attempt -> +10 XP
        res1 = record_study_quiz_attempt(self.test_user_id, correct=True)
        self.assertEqual(res1["xp_gain"], 10)
        self.assertEqual(res1["total_xp"], 10)
        self.assertEqual(res1["total_answered"], 1)
        self.assertEqual(res1["level"], 1)
        self.assertFalse(res1["is_level_up"])

        # 1 incorrect attempt -> +2 effort XP
        res2 = record_study_quiz_attempt(self.test_user_id, correct=False)
        self.assertEqual(res2["xp_gain"], 2)
        self.assertEqual(res2["total_xp"], 12)
        self.assertEqual(res2["total_answered"], 2)
        self.assertEqual(res2["level"], 1)

        # Award 90 more XP to cross 100 XP threshold (Level 2)
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET study_xp = 95 WHERE user_id = ?", (self.test_user_id,))
            conn.commit()

        res3 = record_study_quiz_attempt(self.test_user_id, correct=True)
        self.assertEqual(res3["total_xp"], 105)
        self.assertEqual(res3["level"], 2)
        self.assertTrue(res3["is_level_up"])

    def test_02_deck_schema_integrity(self):
        """Verify all placement decks have valid titles, 4 options, and in-bounds answer index."""
        required_categories = ["dsa", "aptitude", "core"]
        for cat in required_categories:
            self.assertIn(cat, CAMPUS_STUDY_DECKS, f"Category {cat} missing from CAMPUS_STUDY_DECKS")
            deck = CAMPUS_STUDY_DECKS[cat]
            self.assertTrue(bool(deck.get("title")), f"Deck {cat} missing title")
            questions = deck.get("questions", [])
            self.assertGreaterEqual(len(questions), 4, f"Deck {cat} has fewer than 4 questions")
            for q in questions:
                self.assertIn("id", q)
                self.assertIn("q", q)
                self.assertIn("opts", q)
                self.assertIn("ans", q)
                self.assertIn("explain", q)
                self.assertEqual(len(q["opts"]), 4, f"Question {q['id']} must have exactly 4 choices")
                self.assertIn(q["ans"], [0, 1, 2, 3], f"Question {q['id']} answer index must be 0-3")
                self.assertGreater(len(q["explain"].strip()), 10, f"Question {q['id']} explanation is too short")

    def test_03_handle_study_menu_rendering(self):
        """Verify handle_study_menu renders Scholar Tier stats and interactive deck options."""
        bot = MagicMock()
        bot.edit_message_text = AsyncMock()
        bot.send_message = AsyncMock(return_value={"message_id": 1234})

        user = {
            "user_id": self.test_user_id,
            "first_name": "ScholarTest"
        }

        asyncio.run(handle_study_menu(bot, chat_id=self.test_user_id, user=user))

        bot.send_message.assert_called_once()
        args, kwargs = bot.send_message.call_args
        sent_text = args[1]
        reply_markup = kwargs.get("reply_markup", {})

        self.assertIn("Scholar Tier", sent_text)
        self.assertIn("Study XP", sent_text)

        # Check inline keyboard has DSA, Aptitude, Core buttons
        callbacks = [btn["callback_data"] for row in reply_markup.get("inline_keyboard", []) for btn in row]
        self.assertIn("study_deck_dsa", callbacks)
        self.assertIn("study_deck_aptitude", callbacks)
        self.assertIn("study_deck_core", callbacks)
        self.assertIn("study_quiz", callbacks)
        self.assertIn("study_pomo_25", callbacks)

    def test_04_study_deck_callback_displays_mcq(self):
        """Verify tapping a study deck callback returns a question with 4 answer buttons."""
        bot = MagicMock()
        bot.answer_callback_query = AsyncMock()
        bot.edit_message_text = AsyncMock(return_value={"ok": True})
        bot.send_message = AsyncMock(return_value={"message_id": 5566, "ok": True})

        cq = {
            "id": "cq_dsa_1",
            "from": {"id": self.test_user_id, "first_name": "ScholarTest"},
            "message": {"message_id": 5566, "chat": {"id": self.test_user_id}},
            "data": "study_deck_dsa"
        }

        asyncio.run(handle_callback_query(bot, cq))

        bot.answer_callback_query.assert_called_once()
        self.assertTrue(bot.edit_message_text.called or bot.send_message.called)
        if bot.edit_message_text.called:
            args, kwargs = bot.edit_message_text.call_args
            sent_text = args[2] if len(args) > 2 else kwargs.get("text", "")
            reply_markup = kwargs.get("reply_markup", {})
        else:
            args, kwargs = bot.send_message.call_args
            sent_text = args[1] if len(args) > 1 else kwargs.get("text", "")
            reply_markup = kwargs.get("reply_markup", {})

        self.assertIn("DSA & Coding Blitz", sent_text)
        callbacks = [btn["callback_data"] for row in reply_markup.get("inline_keyboard", []) for btn in row]
        ans_cbs = [cb for cb in callbacks if cb.startswith("study_ans:dsa:")]
        self.assertEqual(len(ans_cbs), 4)

    def test_05_study_answer_evaluation_correct_and_incorrect(self):
        """Verify submitting answer awards XP, reveals explanation, and provides next question button."""
        bot = MagicMock()
        bot.answer_callback_query = AsyncMock()
        bot.edit_message_text = AsyncMock(return_value={"ok": True})
        bot.send_message = AsyncMock(return_value={"message_id": 7788, "ok": True})

        # Test answering dsa_01 correctly (ans = 1)
        cq_correct = {
            "id": "cq_ans_correct",
            "from": {"id": self.test_user_id, "first_name": "ScholarTest"},
            "message": {"message_id": 7788, "chat": {"id": self.test_user_id}},
            "data": "study_ans:dsa:dsa_01:1"
        }
        asyncio.run(handle_callback_query(bot, cq_correct))

        stats = get_user_study_stats(self.test_user_id)
        self.assertEqual(stats["study_xp"], 10)
        self.assertEqual(stats["total_answered"], 1)

        # Clear throttle between consecutive test queries
        from app import USER_LAST_ACTION
        USER_LAST_ACTION.clear()

        # Test answering dsa_01 incorrectly (choice = 0)
        cq_wrong = {
            "id": "cq_ans_wrong",
            "from": {"id": self.test_user_id, "first_name": "ScholarTest"},
            "message": {"message_id": 7788, "chat": {"id": self.test_user_id}},
            "data": "study_ans:dsa:dsa_01:0"
        }
        asyncio.run(handle_callback_query(bot, cq_wrong))

        stats_after = get_user_study_stats(self.test_user_id)
        self.assertEqual(stats_after["study_xp"], 12)
        self.assertEqual(stats_after["total_answered"], 2)

    def test_06_procedural_soundscape_static_assets(self):
        """Verify static/call.html contains ProceduralSoundscapeEngine, ambient controls, and styles."""
        call_html_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "call.html"))
        self.assertTrue(os.path.isfile(call_html_path), "static/call.html missing")

        with open(call_html_path, "r", encoding="utf-8") as f:
            html = f.read()

        # Check DOM elements
        self.assertIn('id="ambientSoundscapeBtn"', html)
        self.assertIn('id="ambientDrawer"', html)
        self.assertIn('id="ambientVolSlider"', html)
        self.assertIn('id="ambientVolLabel"', html)
        self.assertIn('id="chip_rain"', html)
        self.assertIn('id="chip_cafe"', html)
        self.assertIn('id="chip_focus"', html)

        # Check JS Engine and Web Audio API Synthesis
        self.assertIn('class ProceduralSoundscapeEngine', html)
        self.assertIn('playRain()', html)
        self.assertIn('playCafe()', html)
        self.assertIn('playFocus()', html)
        self.assertIn('toggleAmbientDrawer()', html)
        self.assertIn('setAmbientMode(', html)
        self.assertIn('setAmbientVolume(', html)
        self.assertIn('window.ambientEngine', html)


if __name__ == "__main__":
    unittest.main()
