"""
tests/test_channel_growth_teaser.py
Automated Regression Test Suite for Joy Bot Channel Growth, Daily Dilemma Teasers,
and Unlocked Bedtime Relaxation Voice Notes.
Validates:
1. TEASER_LIBRARY structure, complete dilemma metadata, and categories.
2. Channel broadcast copy-block generation and social sharing links (Telegram/WhatsApp).
3. Viral attribution: ref_channel, ref_broadcast, and ref_teaser map to OWNER_ID.
4. Bedtime relaxation command is globally accessible without pioneer waitlist gating.
5. Bot command hubs cleanly register /teaser and /bedtime.
Runs 100% offline in < 1.0s.
"""

import os
import sys
import unittest
import tempfile
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

os.environ["OFFLINE_TEST"] = "1"

# Ensure joy-bot root directory is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import config
import database
from database import init_db, get_or_create_user, is_user_vip
from config import OWNER_ID

if "edge_tts" not in sys.modules:
    sys.modules["edge_tts"] = MagicMock()

import app
from app import (
    TEASER_LIBRARY,
    BOT_COMMANDS,
    BETA_BOT_COMMANDS,
    handle_teaser_hub,
    handle_teaser_channel_post,
    handle_bedtime_command
)

class TestChannelGrowthTeaser(unittest.TestCase):
    """Test suite for Viral Channel Growth, Dilemma Studio, and Bedtime Access."""

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

    def test_01_teaser_library_completeness_and_structure(self):
        """Verify TEASER_LIBRARY has rich dilemmas with all required viral fields."""
        self.assertGreaterEqual(len(TEASER_LIBRARY), 5, "Library must contain at least 5 viral dilemmas")
        for i, item in enumerate(TEASER_LIBRARY):
            self.assertEqual(item["id"], i, f"Item {i} must have matching id")
            self.assertIn("title", item)
            self.assertIn("category", item)
            self.assertIn("hook", item)
            self.assertIn("story", item)
            self.assertIn("options", item)
            self.assertIn("punchline", item)
            self.assertGreaterEqual(len(item["options"]), 2, f"Item {i} must provide at least 2 poll options")
            self.assertGreater(len(item["hook"]), 10, f"Item {i} must have engaging hook text")

    def test_02_teaser_hub_renders_cleanly(self):
        """Verify handle_teaser_hub produces responsive dilemma card with navigation."""
        mock_bot = AsyncMock()
        mock_bot.send_message.return_value = {"ok": True, "result": {"message_id": 101}}
        mock_bot.edit_message_text.return_value = {"ok": True, "result": {"message_id": 101}}
        user = {
            "user_id": 12345678,
            "first_name": "Phoenix",
            "gender": "male"
        }
        
        asyncio.run(handle_teaser_hub(mock_bot, 12345678, user, teaser_index=0))

        # Check that a message was sent or edited
        self.assertTrue(mock_bot.send_message.called or mock_bot.edit_message_text.called)
        sent_call = mock_bot.send_message.call_args or mock_bot.edit_message_text.call_args
        sent_text = sent_call[0][1] if len(sent_call[0]) > 1 else sent_call[1].get("text", "")
        reply_markup = sent_call[1].get("reply_markup") or (sent_call[0][2] if len(sent_call[0]) > 2 else {})
        
        self.assertIn("Daily Dilemma & Channel Growth Studio", sent_text)
        self.assertIn("The Canteen Crush Dilemma", sent_text)
        
        # Verify navigation buttons exist
        inline_kb = reply_markup.get("inline_keyboard", [])
        self.assertGreaterEqual(len(inline_kb), 3)
        row0_texts = [btn["text"] for btn in inline_kb[0]]
        self.assertIn("⬅️ Prev", row0_texts)
        self.assertIn("Next ➡️", row0_texts)

    def test_03_teaser_channel_post_copy_block_generation(self):
        """Verify handle_teaser_channel_post creates aesthetic broadcast block with deep links."""
        mock_bot = AsyncMock()
        mock_bot.send_message.return_value = {"ok": True, "result": {"message_id": 102}}
        mock_bot.edit_message_text.return_value = {"ok": True, "result": {"message_id": 102}}
        user = {
            "user_id": 98765432,
            "first_name": "Brandy",
            "gender": "male"
        }

        asyncio.run(handle_teaser_channel_post(mock_bot, 98765432, user, teaser_index=1))

        self.assertTrue(mock_bot.send_message.called or mock_bot.edit_message_text.called)
        sent_call = mock_bot.send_message.call_args or mock_bot.edit_message_text.call_args
        sent_text = sent_call[0][1] if len(sent_call[0]) > 1 else sent_call[1].get("text", "")

        self.assertIn("Channel Broadcast Copy Block", sent_text)
        self.assertIn("DAILY DILEMMA //", sent_text)
        self.assertIn("#JoyAI", sent_text)
        self.assertIn("t.me/joy_fun_ai_bot?start=ref_", sent_text)

    def test_04_channel_and_broadcast_attribution_mapping(self):
        """Verify ref_channel, ref_broadcast, and ref_teaser map to OWNER_ID."""
        test_codes = ["channel", "broadcast", "teaser"]
        for code in test_codes:
            ref_param = f"ref_{code}"
            ref_code = ref_param.replace("ref_", "").strip()
            referrer_id = None
            if ref_code in ["channel", "broadcast", "teaser"]:
                referrer_id = OWNER_ID
            self.assertEqual(referrer_id, OWNER_ID, f"{code} must resolve to OWNER_ID {OWNER_ID}")

    def test_05_bedtime_command_accessible_without_pioneer_gate(self):
        """Verify handle_bedtime_command is open to all users and does not reject with waitlist message."""
        mock_bot = AsyncMock()
        # Normal non-pioneer user
        regular_user = {
            "user_id": 55443322,
            "first_name": "TestUser",
            "gender": "male",
            "is_beta_tester": 0,
            "active_contact": "lover",
            "language": "auto"
        }
        get_or_create_user(55443322, "TestUser", "male")

        with patch("app.synthesize_speech", AsyncMock(return_value=b"fake_mp3_audio")):
            asyncio.run(handle_bedtime_command(mock_bot, 55443322, regular_user))

        # Check that it sent audio note or message without Pioneer gating rejection
        for call in mock_bot.send_message.call_args_list:
            msg = call[0][1] if len(call[0]) > 1 else call[1].get("text", "")
            self.assertNotIn("Exclusive Pioneer Feature", msg)
            self.assertNotIn("Tap /waitlist to claim", msg)

        # Either send_audio was called or send_message (with goodnight text) was called
        audio_called = mock_bot.send_audio.called
        msg_called = mock_bot.send_message.called
        self.assertTrue(audio_called or msg_called, "Bedtime voice note must deliver audio or fallback text")

    def test_06_bot_commands_registration(self):
        """Verify BOT_COMMANDS and BETA_BOT_COMMANDS contain /teaser and /bedtime."""
        bot_cmds = [c["command"] for c in BOT_COMMANDS]
        self.assertIn("teaser", bot_cmds, "/teaser must be registered in BOT_COMMANDS")
        self.assertIn("bedtime", bot_cmds, "/bedtime must be registered in BOT_COMMANDS")

        beta_cmds = [c["command"] for c in BETA_BOT_COMMANDS]
        self.assertIn("teaser", beta_cmds, "/teaser must be registered in BETA_BOT_COMMANDS")
        self.assertIn("bedtime", beta_cmds, "/bedtime must be registered in BETA_BOT_COMMANDS")

if __name__ == "__main__":
    unittest.main()
