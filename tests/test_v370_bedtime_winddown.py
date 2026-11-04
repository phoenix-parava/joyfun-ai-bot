"""
tests/test_v370_bedtime_winddown.py
Automated Regression Test Suite for Joy Bot v3.7.0:
1. Scheduled Evening Hostel Wind-Down & Bedtime Sleep Alert Engine (/sleep, /bedtime, /winddown)
2. 3-Breath Decompression Ritual, Gratitude Streak Tracking, and +15 Deep Rest Scholar XP
3. Soothing ASMR Whisper Voice Notes and 1-Tap Sleep Mode Demeanor Modulation
4. Full Database Lifecycle, Menu Rendering, and Version Constancy Checks
Runs 100% offline in < 1.0s.
"""

import os
import sys
import unittest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

# Force test configuration
os.environ["OFFLINE_TEST"] = "1"
os.environ["ALLOW_TEST_USERS"] = "1"
os.environ["BOT_TOKEN"] = "123456:TEST_TOKEN_FOR_BEDTIME_V370"

# Include parent directory in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if "edge_tts" not in sys.modules:
    sys.modules["edge_tts"] = MagicMock()

import config
import database
from config import BOT_VERSION, MINI_APP_VERSION, SECURITY_VERSION
from app import (
    BOT_COMMANDS,
    BETA_BOT_COMMANDS,
    USER_LAST_ACTION,
    dispatch_evening_winddown,
    handle_bedtime_menu,
    handle_callback_query,
    handle_bedtime_command
)


class TestV370BedtimeWinddown(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.test_user_id = 999370
        database.init_db()
        with database.get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE user_id = ?", (self.test_user_id,))
            c.execute("DELETE FROM user_bedtime_settings WHERE user_id = ?", (self.test_user_id,))
            c.execute("""
                INSERT INTO users (user_id, username, first_name, study_xp, study_questions_answered, onboarding_status, is_beta_tester, companion_tone)
                VALUES (?, 'test_nightowl', 'NightOwl', 80, 5, 'completed', 1, 'gentle')
            """, (self.test_user_id,))
            conn.commit()

    def tearDown(self):
        with database.get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE user_id = ?", (self.test_user_id,))
            c.execute("DELETE FROM user_bedtime_settings WHERE user_id = ?", (self.test_user_id,))
            conn.commit()

    def test_01_database_bedtime_lifecycle(self):
        """Verify bedtime creation, time updates, toggles, due query, and streak increment."""
        # 1. Default creation
        bedtime = database.get_user_bedtime(self.test_user_id)
        self.assertEqual(bedtime["bedtime_time"], "23:30")
        self.assertEqual(bedtime["is_enabled"], 1)
        self.assertEqual(bedtime["voice_note_enabled"], 1)
        self.assertEqual(bedtime["gratitude_streak"], 1)

        # 2. Update time to midnight
        updated = database.set_user_bedtime_time(self.test_user_id, "00:00")
        self.assertEqual(updated["bedtime_time"], "00:00")
        self.assertEqual(updated["is_enabled"], 1)

        # 3. Toggle bedtime active/pause
        is_on = database.toggle_user_bedtime(self.test_user_id)
        self.assertFalse(is_on)
        is_on = database.toggle_user_bedtime(self.test_user_id)
        self.assertTrue(is_on)

        # 4. Toggle voice note
        voice_on = database.toggle_user_bedtime_voice(self.test_user_id)
        self.assertFalse(voice_on)
        voice_on = database.toggle_user_bedtime_voice(self.test_user_id)
        self.assertTrue(voice_on)

        # 5. Query due bedtime alarms
        due = database.get_due_bedtime_alarms("00:00", "2026-11-02")
        matching = [d for d in due if d["user_id"] == self.test_user_id]
        self.assertEqual(len(matching), 1)

        # 6. Mark triggered and check streak increment
        database.mark_bedtime_triggered(self.test_user_id, "2026-11-02")
        due_after = database.get_due_bedtime_alarms("00:00", "2026-11-02")
        matching_after = [d for d in due_after if d["user_id"] == self.test_user_id]
        self.assertEqual(len(matching_after), 0)

        bedtime_after = database.get_user_bedtime(self.test_user_id)
        self.assertEqual(bedtime_after["last_triggered_date"], "2026-11-02")
        self.assertEqual(bedtime_after["gratitude_streak"], 2)

    def test_02_database_award_scholar_xp(self):
        """Verify award_scholar_xp correctly increments study_xp and calculates Scholar level."""
        res = database.award_scholar_xp(self.test_user_id, amount=15)
        self.assertEqual(res["xp_gained"], 15)
        self.assertEqual(res["new_xp"], 95)  # 80 initial + 15
        self.assertEqual(res["level"], 1)

        # Award another 15 to cross 100 XP threshold (Level 2)
        res2 = database.award_scholar_xp(self.test_user_id, amount=15)
        self.assertEqual(res2["new_xp"], 110)
        self.assertEqual(res2["level"], 2)

    async def test_03_handle_bedtime_menu_rendering(self):
        """Verify handle_bedtime_menu renders rich dashboard with time slots and toggles."""
        mock_bot = AsyncMock()
        mock_bot.send_message.return_value = {"ok": True, "result": {"message_id": 701}}
        mock_bot.edit_message_text.return_value = {"ok": True, "result": {"message_id": 701}}

        user_dict = {
            "user_id": self.test_user_id,
            "first_name": "NightOwl",
            "gender": "male"
        }

        await handle_bedtime_menu(mock_bot, self.test_user_id, user_dict)

        self.assertTrue(mock_bot.send_message.called or mock_bot.edit_message_text.called)
        sent_call = mock_bot.send_message.call_args or mock_bot.edit_message_text.call_args
        sent_text = sent_call[0][1] if len(sent_call[0]) > 1 else sent_call[1].get("text", "")
        reply_markup = sent_call[1].get("reply_markup") or (sent_call[0][2] if len(sent_call[0]) > 2 else {})

        self.assertIn("Joy Hostel Evening Wind-Down & Bedtime Engine", sent_text)
        self.assertIn("Current Bedtime Alert:", sent_text)
        self.assertIn("Rest Streak:", sent_text)

        # Inspect keyboard buttons
        inline_kb = reply_markup.get("inline_keyboard", [])
        all_cb = [btn.get("callback_data") for row in inline_kb for btn in row if "callback_data" in btn]
        self.assertIn("bedtime_toggle_active", all_cb)
        self.assertIn("bedtime_toggle_voice", all_cb)
        self.assertIn("bedtime_set_22:00", all_cb)
        self.assertIn("bedtime_set_23:30", all_cb)
        self.assertIn("bedtime_set_00:00", all_cb)
        self.assertIn("bedtime_test_trigger", all_cb)
        self.assertIn("beta_cmd_bedtime", all_cb)

    async def test_04_callback_query_routing_bedtime(self):
        """Verify callback queries for bedtime toggles, slot selection, and sleep mode."""
        mock_bot = AsyncMock()
        mock_bot.answer_callback_query.return_value = True
        mock_bot.edit_message_text.return_value = True

        # 1. Test bedtime_set_23:00
        USER_LAST_ACTION.clear()
        cb_update = {
            "id": "cq_set_time",
            "from": {"id": self.test_user_id},
            "message": {"message_id": 801, "chat": {"id": self.test_user_id}},
            "data": "bedtime_set_23:00"
        }
        await handle_callback_query(mock_bot, cb_update)
        bt = database.get_user_bedtime(self.test_user_id)
        self.assertEqual(bt["bedtime_time"], "23:00")

        # 2. Test bedtime_toggle_active
        USER_LAST_ACTION.clear()
        cb_toggle = {
            "id": "cq_toggle_act",
            "from": {"id": self.test_user_id},
            "message": {"message_id": 801, "chat": {"id": self.test_user_id}},
            "data": "bedtime_toggle_active"
        }
        await handle_callback_query(mock_bot, cb_toggle)
        bt_toggled = database.get_user_bedtime(self.test_user_id)
        self.assertEqual(bt_toggled["is_enabled"], 0)

        # 3. Test bedtime_sleep_mode activates whisper tone
        USER_LAST_ACTION.clear()
        cb_sleep = {
            "id": "cq_sleep_mode",
            "from": {"id": self.test_user_id},
            "message": {"message_id": 801, "chat": {"id": self.test_user_id}},
            "data": "bedtime_sleep_mode"
        }
        await handle_callback_query(mock_bot, cb_sleep)
        tone = database.get_user_companion_tone(self.test_user_id)
        self.assertEqual(tone, "whisper")

    async def test_05_dispatch_evening_winddown_execution(self):
        """Verify dispatch_evening_winddown sends 3-breath decompression card, awards +15 XP, and delivers whisper audio."""
        mock_bot = AsyncMock()
        mock_bot.send_message.return_value = {"ok": True, "result": {"message_id": 901}}
        mock_bot.send_voice.return_value = {"ok": True, "result": {"message_id": 902}}

        initial_xp = database.get_or_create_user(self.test_user_id).get("study_xp", 0)

        with patch("app.synthesize_speech", AsyncMock(return_value=b"soothing_whisper_voice_mp3_data_bytes_123456" * 50)):
            await dispatch_evening_winddown(mock_bot, self.test_user_id, with_voice=True)

        # Verify message content
        mock_bot.send_message.assert_called_once()
        sent_call = mock_bot.send_message.call_args
        sent_text = sent_call[0][1] if len(sent_call[0]) > 1 else sent_call[1].get("text", "")

        self.assertIn("Hostel Night Wind-Down", sent_text)
        self.assertIn("3-Breath Decompression Ritual", sent_text)
        self.assertIn("Night Gratitude Streak", sent_text)
        self.assertIn("+15 Deep Rest Scholar XP Awarded!", sent_text)

        # Verify XP awarded
        updated_xp = database.get_or_create_user(self.test_user_id).get("study_xp", 0)
        self.assertEqual(updated_xp, initial_xp + 15)

        # Verify voice note delivered
        mock_bot.send_voice.assert_called_once()

    def test_06_bot_commands_and_version_constants(self):
        """Verify BOT_COMMANDS, BETA_BOT_COMMANDS are decluttered of bedtime/sleep/winddown, and version strings are bumped."""
        bot_cmds = [c["command"] for c in BOT_COMMANDS]
        beta_cmds = [c["command"] for c in BETA_BOT_COMMANDS]

        self.assertNotIn("bedtime", bot_cmds)
        self.assertNotIn("sleep", bot_cmds)
        self.assertNotIn("winddown", bot_cmds)

        self.assertNotIn("bedtime", beta_cmds)
        self.assertNotIn("sleep", beta_cmds)
        self.assertNotIn("winddown", beta_cmds)

        self.assertEqual(BOT_VERSION, "v4.1.1")
        self.assertEqual(MINI_APP_VERSION, "v4.1.1")
        self.assertEqual(SECURITY_VERSION, "v4.1.1-ZeroTrust")


if __name__ == "__main__":
    unittest.main()
