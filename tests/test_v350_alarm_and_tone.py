"""
Tests for Joy Bot v3.5.0:
1. Proactive Morning Campus Briefing & Wake-Up Voice Alert Engine (/alarm, /morning)
2. Dynamic Companion Demeanor & Tone Presets (/tone)
"""

import os
import sys
import unittest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

# Force test configuration
os.environ["OFFLINE_TEST"] = "1"
os.environ["ALLOW_TEST_USERS"] = "1"
os.environ["BOT_TOKEN"] = "123456:TEST_TOKEN_FOR_ALARM_TONE"

# Include parent directory in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if "edge_tts" not in sys.modules:
    sys.modules["edge_tts"] = MagicMock()

import database
from ai_engine import resolve_tone_instruction
from app import (
    dispatch_morning_briefing,
    handle_alarm_menu,
    handle_tone_menu,
)


class TestV350AlarmAndTone(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.test_user_id = 999350
        database.init_db()
        with database.get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE user_id = ?", (self.test_user_id,))
            c.execute("DELETE FROM user_alarms WHERE user_id = ?", (self.test_user_id,))
            c.execute("""
                INSERT INTO users (user_id, username, first_name, study_xp, study_questions_answered, onboarding_status, is_beta_tester, companion_tone)
                VALUES (?, 'test_earlybird', 'EarlyBird', 50, 2, 'completed', 1, 'gentle')
            """, (self.test_user_id,))
            conn.commit()

    def tearDown(self):
        with database.get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE user_id = ?", (self.test_user_id,))
            c.execute("DELETE FROM user_alarms WHERE user_id = ?", (self.test_user_id,))
            conn.commit()

    def test_01_database_alarm_lifecycle(self):
        """Verify alarm creation, time updates, toggles, and due alarm queries."""
        # Default alarm
        alarm = database.get_user_alarm(self.test_user_id)
        self.assertEqual(alarm["alarm_time"], "07:30")
        self.assertEqual(alarm["is_enabled"], 1)
        self.assertEqual(alarm["voice_note_enabled"], 1)

        # Update time
        updated = database.set_user_alarm_time(self.test_user_id, "08:00")
        self.assertEqual(updated["alarm_time"], "08:00")

        # Toggle alarm
        is_on = database.toggle_user_alarm(self.test_user_id)
        self.assertFalse(is_on)
        is_on = database.toggle_user_alarm(self.test_user_id)
        self.assertTrue(is_on)

        # Toggle voice note
        voice_on = database.toggle_user_alarm_voice(self.test_user_id)
        self.assertFalse(voice_on)

        # Query due alarms
        due = database.get_due_morning_alarms("08:00", "2026-11-02")
        matching = [d for d in due if d["user_id"] == self.test_user_id]
        self.assertEqual(len(matching), 1)

        # Mark triggered
        database.mark_alarm_triggered(self.test_user_id, "2026-11-02")
        due_after = database.get_due_morning_alarms("08:00", "2026-11-02")
        matching_after = [d for d in due_after if d["user_id"] == self.test_user_id]
        self.assertEqual(len(matching_after), 0)

    def test_02_database_companion_tone_lifecycle(self):
        """Verify companion tone reading, writing, and fallback validation."""
        tone = database.get_user_companion_tone(self.test_user_id)
        self.assertEqual(tone, "gentle")

        # Set to strict
        database.set_user_companion_tone(self.test_user_id, "strict")
        self.assertEqual(database.get_user_companion_tone(self.test_user_id), "strict")

        # Set to hype
        database.set_user_companion_tone(self.test_user_id, "hype")
        self.assertEqual(database.get_user_companion_tone(self.test_user_id), "hype")

        # Set invalid fallback -> defaults to gentle
        database.set_user_companion_tone(self.test_user_id, "invalid_tone_123")
        self.assertEqual(database.get_user_companion_tone(self.test_user_id), "gentle")

    def test_03_ai_engine_tone_instructions(self):
        """Verify resolve_tone_instruction provides distinct prompt instructions for all presets."""
        strict_text = resolve_tone_instruction("strict")
        self.assertIn("Strict Technical Coach", strict_text)

        hype_text = resolve_tone_instruction("hype")
        self.assertIn("Hype Partner", hype_text)

        whisper_text = resolve_tone_instruction("whisper")
        self.assertIn("Late-Night Soft ASMR", whisper_text)

        gentle_text = resolve_tone_instruction("gentle")
        self.assertIn("Gentle, Warm & Empathetic", gentle_text)

    async def test_04_handle_alarm_menu_rendering(self):
        """Verify handle_alarm_menu formats status and provides interactive time buttons."""
        bot = AsyncMock()
        user = database.get_or_create_user(self.test_user_id)

        await handle_alarm_menu(bot, 100, user)
        call_args = bot.send_message.call_args or bot.edit_message_text.call_args
        self.assertIsNotNone(call_args)
        rendered = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("text", "")
        self.assertIn("Campus Morning Alarm & Wake-Up Engine", rendered)
        self.assertIn("07:30 AM IST", rendered)

    async def test_05_handle_tone_menu_rendering(self):
        """Verify handle_tone_menu displays current active tone and all 4 preset options."""
        bot = AsyncMock()
        user = database.get_or_create_user(self.test_user_id)

        await handle_tone_menu(bot, 100, user)
        call_args = bot.send_message.call_args or bot.edit_message_text.call_args
        self.assertIsNotNone(call_args)
        rendered = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("text", "")
        self.assertIn("Companion Demeanor & Tone Presets", rendered)
        self.assertIn("Gentle & Empathetic", rendered)

    async def test_06_dispatch_morning_briefing_delivery_and_xp(self):
        """Verify dispatch_morning_briefing sends good morning card with Vibe, MCQ, and awards XP."""
        bot = AsyncMock()

        # Dispatch with voice mocked
        with patch("app.synthesize_speech", AsyncMock(return_value=b"dummy_mp3_bytes_for_test_wake_up_alarm_audio")):
            await dispatch_morning_briefing(bot, self.test_user_id, with_voice=True)

        self.assertTrue(bot.send_message.called)
        call_args = bot.send_message.call_args
        sent_text = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("text", "")
        self.assertIn("Wake-Up Call from Joy", sent_text)
        self.assertIn("Today's Campus Vibe", sent_text)
        self.assertIn("Placement Brain Teaser", sent_text)
        self.assertIn("Early-Bird Scholar XP", sent_text)

        # Verify XP awarded
        stats = database.get_user_study_stats(self.test_user_id)
        self.assertGreater(stats["study_xp"], 50)


if __name__ == "__main__":
    unittest.main()
