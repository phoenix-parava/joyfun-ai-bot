"""
Tests for Joy Bot v3.3.0:
1. Full-Duplex Spoken Barge-In in Mini Phone Web Audio Engine & WebSocket Relay
2. Campus Placement Mock Interviewer & Viva Simulator (/interview, /viva)
"""

import os
import sys
import unittest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

# Force test configuration
os.environ["OFFLINE_TEST"] = "1"
os.environ["ALLOW_TEST_USERS"] = "1"
os.environ["BOT_TOKEN"] = "123456:TEST_TOKEN_FOR_STUDY_ARENA"

# Include parent directory in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if "edge_tts" not in sys.modules:
    sys.modules["edge_tts"] = MagicMock()

import database
from app import (
    INTERVIEW_TRACKS,
    active_interviews,
    count_filler_words,
    handle_interview_menu,
    start_interview_session,
    handle_interview_answer,
    handle_interview_skip,
    handle_interview_exit,
    handle_study_menu
)


class TestV330BargeInAndInterview(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.test_user_id = 999123
        database.init_db()
        with database.get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE user_id = ?", (self.test_user_id,))
            c.execute("DELETE FROM mock_interviews WHERE user_id = ?", (self.test_user_id,))
            c.execute("""
                INSERT INTO users (user_id, username, first_name, study_xp, study_questions_answered, onboarding_status, is_beta_tester)
                VALUES (?, 'test_scholar', 'Scholar', 80, 5, 'completed', 1)
            """, (self.test_user_id,))
            conn.commit()
        active_interviews.pop(self.test_user_id, None)

    def tearDown(self):
        active_interviews.pop(self.test_user_id, None)
        with database.get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE user_id = ?", (self.test_user_id,))
            c.execute("DELETE FROM mock_interviews WHERE user_id = ?", (self.test_user_id,))
            conn.commit()

    def test_01_filler_words_counting(self):
        """Verify count_filler_words accurately detects common speech fillers."""
        clean_text = "Hash tables compute key indices using deterministic hash functions with O(1) lookups."
        self.assertEqual(count_filler_words(clean_text), 0)

        filler_text = "Um, like, basically hash table chaining uses linked lists, actually, you know, for collisions."
        self.assertGreaterEqual(count_filler_words(filler_text), 5)

    def test_02_database_mock_interview_completion(self):
        """Verify record_mock_interview_completion updates XP, answered counter, and logs to mock_interviews table."""
        res = database.record_mock_interview_completion(
            user_id=self.test_user_id,
            score=9,
            track="sde",
            filler_count=2,
            feedback="Great explanation of hash table collision resolution."
        )
        self.assertIn("xp_gain", res)
        self.assertGreaterEqual(res["xp_gain"], 50)  # +50 XP baseline + bonus
        self.assertEqual(res["total_answered"], 8)  # 5 + 3 questions

        # Verify DB records
        with database.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM mock_interviews WHERE user_id = ?", (self.test_user_id,))
            row = c.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["track"], "sde")
            self.assertEqual(row["overall_score"], 9)
            self.assertEqual(row["filler_words_count"], 2)

    def test_03_interview_tracks_schema(self):
        """Verify all interview tracks contain title, badge, description, and exactly 3 curated viva questions."""
        required_tracks = ["sde", "data", "hr"]
        for t_key in required_tracks:
            self.assertIn(t_key, INTERVIEW_TRACKS)
            track = INTERVIEW_TRACKS[t_key]
            self.assertIn("title", track)
            self.assertIn("badge", track)
            self.assertIn("questions", track)
            self.assertEqual(len(track["questions"]), 3)

    async def test_04_handle_interview_menu_and_study_hub_integration(self):
        """Verify handle_interview_menu renders options and handle_study_menu includes mock interview option."""
        bot = AsyncMock()
        user = database.get_or_create_user(self.test_user_id)

        # Test study menu has mock interview option
        await handle_study_menu(bot, 100, user)
        self.assertTrue(bot.send_message.called or bot.edit_message_text.called)

        # Test interview menu
        bot.reset_mock()
        await handle_interview_menu(bot, 100, user)
        call_args = bot.send_message.call_args or bot.edit_message_text.call_args
        self.assertIsNotNone(call_args)
        rendered_text = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("text", "")
        self.assertIn("Mock Interview & Viva Simulator", rendered_text)

    async def test_05_mock_interview_round_progression_and_completion(self):
        """Verify candidate advances through 3 viva rounds and receives final score card and XP."""
        bot = AsyncMock()
        user = database.get_or_create_user(self.test_user_id)

        # Round 1 Start
        await start_interview_session(bot, 100, user, "sde")
        self.assertIn(self.test_user_id, active_interviews)
        self.assertEqual(active_interviews[self.test_user_id]["round"], 0)

        # Answer Round 1
        with patch("app.generate_text_reply", AsyncMock(return_value="Score: 9/10\nStrong explanation of chaining vs open addressing.")):
            await handle_interview_answer(bot, 100, user, "Chaining uses linked list nodes while open addressing probes next slots.", is_voice=False)
        self.assertEqual(active_interviews[self.test_user_id]["round"], 1)

        # Answer Round 2
        with patch("app.generate_text_reply", AsyncMock(return_value="Score: 8/10\nGood differentiation between memory space and thread execution.")):
            await handle_interview_answer(bot, 100, user, "Processes have separate memory spaces whereas threads share heap memory.", is_voice=True)
        self.assertEqual(active_interviews[self.test_user_id]["round"], 2)

        # Answer Round 3 (Completion!)
        with patch("app.generate_text_reply", AsyncMock(return_value="Score: 9/10\nExcellent choice of token bucket for burst tolerance.")):
            await handle_interview_answer(bot, 100, user, "Token bucket algorithm allows bursts while enforcing average rate limits.", is_voice=False)

        # Session should be cleared after round 3
        self.assertNotIn(self.test_user_id, active_interviews)

        # Verify DB updated
        stats = database.get_user_study_stats(self.test_user_id)
        self.assertGreater(stats["study_xp"], 80)

    async def test_06_mock_interview_skip_and_exit(self):
        """Verify interview skip and exit handlers clean up sessions safely."""
        bot = AsyncMock()
        user = database.get_or_create_user(self.test_user_id)

        # Start session
        await start_interview_session(bot, 100, user, "hr")
        self.assertIn(self.test_user_id, active_interviews)

        # Skip round
        await handle_interview_skip(bot, 100, user, cq_id="cq_skip")
        self.assertEqual(active_interviews[self.test_user_id]["round"], 1)

        # Exit session
        await handle_interview_exit(bot, 100, user, cq_id="cq_exit")
        self.assertNotIn(self.test_user_id, active_interviews)

    def test_07_call_html_barge_in_and_ducking_presence(self):
        """Verify static/call.html contains spoken barge-in detector with smooth audio ducking."""
        call_html_path = os.path.join(os.path.dirname(__file__), "..", "static", "call.html")
        with open(call_html_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("user_interrupted", content)
        self.assertIn("exponentialRampToValueAtTime", content)
        self.assertIn("isJoySpeaking && !isMuted", content)


if __name__ == "__main__":
    unittest.main()
