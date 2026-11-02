"""
Tests for Joy Bot v3.4.0:
1. Automated Post-Call Voice Recap & Memory Ledger Engine (/recap) + Scholar Voice XP
2. Placement Code & Algorithm Scratchpad (/code) + Study Hub Integration
"""

import os
import sys
import unittest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

# Force test configuration
os.environ["OFFLINE_TEST"] = "1"
os.environ["ALLOW_TEST_USERS"] = "1"
os.environ["BOT_TOKEN"] = "123456:TEST_TOKEN_FOR_RECAP_CODE"

# Include parent directory in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if "edge_tts" not in sys.modules:
    sys.modules["edge_tts"] = MagicMock()

import database
from app import (
    dispatch_post_call_recap,
    handle_manual_recap_command,
    handle_code_command,
    handle_study_menu
)


class TestV340RecapAndCode(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.test_user_id = 999340
        database.init_db()
        with database.get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE user_id = ?", (self.test_user_id,))
            c.execute("DELETE FROM voice_call_logs WHERE user_id = ?", (self.test_user_id,))
            c.execute("""
                INSERT INTO users (user_id, username, first_name, study_xp, study_questions_answered, onboarding_status, is_beta_tester)
                VALUES (?, 'test_caller', 'Caller', 70, 4, 'completed', 1)
            """, (self.test_user_id,))
            conn.commit()

    def tearDown(self):
        with database.get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE user_id = ?", (self.test_user_id,))
            c.execute("DELETE FROM voice_call_logs WHERE user_id = ?", (self.test_user_id,))
            conn.commit()

    def test_01_database_voice_call_completion_xp(self):
        """Verify record_voice_call_completion calculates XP base + duration bonus and logs row."""
        # 120 seconds = 2 minutes -> base 15 + 2 = 17 XP
        res = database.record_voice_call_completion(
            user_id=self.test_user_id,
            duration_secs=120,
            recap_summary="Discussed dynamic programming and binary search."
        )
        self.assertEqual(res["xp_gain"], 17)
        self.assertEqual(res["total_xp"], 87)

        # Verify DB entry
        with database.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM voice_call_logs WHERE user_id = ?", (self.test_user_id,))
            row = c.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["duration_secs"], 120)
            self.assertEqual(row["xp_awarded"], 17)
            self.assertIn("dynamic programming", row["recap_summary"])

    async def test_02_dispatch_post_call_recap_threshold_gates(self):
        """Verify dispatch_post_call_recap rejects short (<25s) or trivial (<2 turns) calls without sending spam."""
        bot = AsyncMock()

        # Gate 1: Duration too short (10s)
        await dispatch_post_call_recap(bot, self.test_user_id, duration_secs=10, dialogue_turns=[{"speaker": "User", "text": "Hi"}])
        self.assertFalse(bot.send_message.called)

        # Gate 2: Not enough turns (1 turn)
        await dispatch_post_call_recap(bot, self.test_user_id, duration_secs=60, dialogue_turns=[{"speaker": "User", "text": "Hello"}])
        self.assertFalse(bot.send_message.called)

    async def test_03_dispatch_post_call_recap_success(self):
        """Verify qualified voice call generates recap and sends Telegram card with inline buttons."""
        bot = AsyncMock()
        dialogue = [
            {"speaker": "Joy", "text": "Hey! How is your DSA placement prep going?"},
            {"speaker": "User", "text": "I am revising Hash Tables and Sliding Window today."},
            {"speaker": "Joy", "text": "Great! Focus on the two-pointer technique for sliding window."},
            {"speaker": "User", "text": "Will do, thanks Joy!"}
        ]

        with patch("app.generate_text_reply", AsyncMock(return_value="💡 **Key Takeaways:**\n• Revising Hash Tables & Sliding Window\n• Focus on two-pointer pattern\n\n🫂 **Vibe Check:** Motivated and focused!\n\n🌸 **Joy's Note:** You've got this!")):
            await dispatch_post_call_recap(bot, self.test_user_id, duration_secs=180, dialogue_turns=dialogue)

        self.assertTrue(bot.send_message.called)
        call_args = bot.send_message.call_args
        sent_text = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("text", "")
        self.assertIn("Joy Voice Call Recap & Memory Ledger", sent_text)
        self.assertIn("3m 0s", sent_text)
        self.assertIn("Voice XP Earned", sent_text)

        # Verify DB updated
        stats = database.get_user_study_stats(self.test_user_id)
        self.assertGreater(stats["study_xp"], 70)

    async def test_04_manual_recap_command_rendering(self):
        """Verify handle_manual_recap_command shows logged recap or prompt."""
        bot = AsyncMock()
        user = database.get_or_create_user(self.test_user_id)

        # Before any call
        await handle_manual_recap_command(bot, 100, user)
        self.assertTrue(bot.send_message.called or bot.edit_message_text.called)

        # Log a call
        database.record_voice_call_completion(self.test_user_id, 95, recap_summary="Discussed system design and microservices.")

        # After call logged
        bot.reset_mock()
        await handle_manual_recap_command(bot, 100, user)
        call_args = bot.send_message.call_args or bot.edit_message_text.call_args
        rendered = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("text", "")
        self.assertIn("Latest Voice Call Recap & Ledger", rendered)
        self.assertIn("1m 35s", rendered)

    async def test_05_handle_code_command_menu_and_query(self):
        """Verify handle_code_command renders scratchpad menu on empty query and generates structured solution on query."""
        bot = AsyncMock()
        user = database.get_or_create_user(self.test_user_id)

        # Empty query -> presents menu
        await handle_code_command(bot, 100, user, query="")
        call_args = bot.send_message.call_args or bot.edit_message_text.call_args
        rendered_menu = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("text", "")
        self.assertIn("Joy Placement Code & Algorithm Scratchpad", rendered_menu)

        # Concrete query -> generates solution
        bot.reset_mock()
        mock_sol = (
            "💻 **Problem:** Find two indices in array that add to target.\n\n"
            "```python\ndef two_sum(nums, target):\n    lookup = {}\n    for i, num in enumerate(nums):\n        if target - num in lookup:\n            return [lookup[target - num], i]\n        lookup[num] = i\n```\n\n"
            "⏱️ **Time Complexity:** O(N) single pass\n"
            "💾 **Space Complexity:** O(N) hash map"
        )
        with patch("app.generate_text_reply", AsyncMock(return_value=mock_sol)):
            await handle_code_command(bot, 100, user, query="Two Sum")

        self.assertTrue(bot.send_message.called)
        call_args2 = bot.send_message.call_args
        rendered_sol = call_args2[0][1] if len(call_args2[0]) > 1 else call_args2[1].get("text", "")
        self.assertIn("two_sum", rendered_sol)
        self.assertIn("Time Complexity", rendered_sol)

    async def test_06_study_menu_includes_code_and_recap(self):
        """Verify handle_study_menu includes buttons for Code Scratchpad and Voice Call Recap."""
        bot = AsyncMock()
        user = database.get_or_create_user(self.test_user_id)

        await handle_study_menu(bot, 100, user)
        call_args = bot.send_message.call_args or bot.edit_message_text.call_args
        self.assertIsNotNone(call_args)
        rendered_text = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("text", "")
        self.assertIn("Code & DSA Scratchpad", rendered_text)
        self.assertIn("Voice Call Recap", rendered_text)


if __name__ == "__main__":
    unittest.main()
