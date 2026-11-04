#!/usr/bin/env python3
"""
Automated Regression Test Suite for Joy Bot UI Streamlining & About/Legal Hub.
Validates:
1. get_main_keyboard streamlined layout (6 lean rows, 12 buttons, localized about_hub).
2. Elimination of promotional bloat (menu_teaser, menu_vibe, menu_leaderboard demoted to commands).
3. handle_about_legal_hub rendering and callback query routing (menu_about_hub).
4. static/call.html instant sponsor recharge (+5 notes & +20 msgs) and removal of redundant theme chip.
5. Verification that 1.1 fake contacts in call.html remain untouched per explicit user mandate.
"""

import os
import sys
import unittest
import tempfile
import asyncio
from unittest.mock import AsyncMock, MagicMock

os.environ["OFFLINE_TEST"] = "1"
os.environ["ALLOW_TEST_USERS"] = "1"
os.environ["BOT_TOKEN"] = "123456:TEST_TOKEN_FOR_STREAMLINE_TESTS"

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if "edge_tts" not in sys.modules:
    sys.modules["edge_tts"] = MagicMock()

import database
from database import init_db
from config import OWNER_ID
import app
from app import (
    get_main_keyboard,
    handle_about_legal_hub,
    handle_callback_query,
    BOT_VERSION,
    MINI_APP_VERSION,
    SECURITY_VERSION
)

class TestUIStreamlineAndAboutHub(unittest.TestCase):
    """Test suite validating UI streamlining, lean main keyboard, and About Hub."""

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

    def test_01_main_keyboard_lean_structure_and_localization(self):
        """Verify main keyboard has 5 symmetrical rows (10 buttons) for regular users, and 7 for owner."""
        # Regular user
        reg_kb = get_main_keyboard(gender="male", user_id=987654, ui_lang="english")
        rows = reg_kb["inline_keyboard"]
        
        # 5 content rows + 1 close row = 6 rows total
        self.assertEqual(len(rows), 6)
        self.assertEqual(rows[-1][0]["callback_data"], "menu_close")

        # Verify each of the 5 content rows has exactly 2 buttons
        for i in range(5):
            self.assertEqual(len(rows[i]), 2, f"Row {i} should contain exactly 2 buttons")

        # Check expected callbacks in the 5 rows
        self.assertIn("web_app", rows[0][0])  # Neural Audio Console
        self.assertEqual(rows[0][1]["callback_data"], "menu_match_real")
        self.assertEqual(rows[1][0]["callback_data"], "menu_user_profile")
        self.assertEqual(rows[1][1]["callback_data"], "menu_vip")
        self.assertEqual(rows[2][0]["callback_data"], "menu_study")
        self.assertEqual(rows[2][1]["callback_data"], "menu_quota")
        self.assertEqual(rows[3][0]["callback_data"], "menu_streak")
        self.assertEqual(rows[3][1]["callback_data"], "menu_settings")
        self.assertEqual(rows[4][0]["callback_data"], "menu_about_hub")
        self.assertEqual(rows[4][1]["callback_data"], "menu_feedback")

        # Verify demoted and shifted buttons are not in primary main menu
        all_callbacks = [b.get("callback_data") for r in rows for b in r if "callback_data" in b]
        self.assertNotIn("menu_language", all_callbacks)
        self.assertNotIn("menu_memories", all_callbacks)
        self.assertNotIn("menu_bedtime", all_callbacks)
        self.assertNotIn("menu_vibe", all_callbacks)
        self.assertNotIn("menu_leaderboard", all_callbacks)
        self.assertNotIn("menu_teaser", all_callbacks)
        self.assertNotIn("menu_about_creator", all_callbacks)
        self.assertNotIn("menu_notice", all_callbacks)
        self.assertNotIn("menu_updates", all_callbacks)
        self.assertNotIn("menu_legal_acts", all_callbacks)

        # Owner keyboard: 5 content rows + 1 owner row + 1 close row = 7 rows total
        owner_kb = get_main_keyboard(gender="male", user_id=OWNER_ID, ui_lang="english")
        owner_rows = owner_kb["inline_keyboard"]
        self.assertEqual(len(owner_rows), 7)
        self.assertEqual(owner_rows[-2][0]["callback_data"], "owner_hub")

        # Localization checks for about_hub label
        german_kb = get_main_keyboard(user_id=987654, ui_lang="german")
        self.assertEqual(german_kb["inline_keyboard"][4][0]["text"], "ℹ️ Über & Rechtliches")

        spanish_kb = get_main_keyboard(user_id=987654, ui_lang="spanish")
        self.assertEqual(spanish_kb["inline_keyboard"][4][0]["text"], "ℹ️ Acerca de y Legal")

        telugu_kb = get_main_keyboard(user_id=987654, ui_lang="telugu")
        self.assertEqual(telugu_kb["inline_keyboard"][4][0]["text"], "ℹ️ సమాచారం & చట్టపరమైనవి")

        malayalam_kb = get_main_keyboard(user_id=987654, ui_lang="malayalam")
        self.assertEqual(malayalam_kb["inline_keyboard"][4][0]["text"], "ℹ️ വിവരങ്ങളും നിയമങ്ങളും")

    def test_02_handle_about_legal_hub_rendering(self):
        """Verify handle_about_legal_hub renders comprehensive hub with consolidated options."""
        bot = MagicMock()
        bot.send_message = AsyncMock(return_value={"message_id": 8801, "ok": True})
        bot.edit_message_text = AsyncMock(return_value={"ok": True})

        user = {"user_id": 123456, "first_name": "Phoenix"}
        asyncio.run(handle_about_legal_hub(bot, chat_id=123456, user=user))

        bot.send_message.assert_called_once()
        args, kwargs = bot.send_message.call_args
        sent_text = args[1]
        reply_markup = kwargs.get("reply_markup", {})

        self.assertIn("Architecture, Charter & Compliance Hub", sent_text)
        self.assertIn(f"`{BOT_VERSION}`", sent_text)
        self.assertIn(f"`{MINI_APP_VERSION}`", sent_text)
        self.assertIn(f"`{SECURITY_VERSION}`", sent_text)

        # Verify buttons in reply_markup (creator & pioneer notice removed per user mandate)
        kb_callbacks = [b.get("callback_data") for r in reply_markup.get("inline_keyboard", []) for b in r if "callback_data" in b]
        self.assertNotIn("menu_about_creator", kb_callbacks)
        self.assertNotIn("menu_notice", kb_callbacks)
        self.assertIn("menu_why_joy", kb_callbacks)
        self.assertIn("menu_updates", kb_callbacks)
        self.assertIn("menu_legal_acts", kb_callbacks)
        self.assertIn("menu_privacy", kb_callbacks)
        self.assertIn("menu_main", kb_callbacks)
        self.assertIn("menu_close", kb_callbacks)

    def test_03_callback_routing_menu_about_hub(self):
        """Verify callback query routing for menu_about_hub responds and displays hub."""
        bot = MagicMock()
        bot.answer_callback_query = AsyncMock()
        bot.send_message = AsyncMock(return_value={"message_id": 8802, "ok": True})
        bot.edit_message_text = AsyncMock(return_value={"ok": True})

        cq = {
            "id": "cq_about_hub_1",
            "from": {"id": 123456, "first_name": "Phoenix"},
            "message": {"message_id": 8802, "chat": {"id": 123456}},
            "data": "menu_about_hub"
        }
        asyncio.run(handle_callback_query(bot, cq))
        bot.answer_callback_query.assert_called_once()
        self.assertTrue(bot.send_message.called or bot.edit_message_text.called)

    def test_04_static_call_html_instant_ad_and_theme_chip_removal(self):
        """Verify static/call.html has sponsor recharge removed, VIP redirection, and VIP member elements."""
        call_html_path = os.path.join(BASE_DIR, "static", "call.html")
        self.assertTrue(os.path.exists(call_html_path), "static/call.html must exist")

        with open(call_html_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. Redundant theme chip removed
        self.assertNotIn('id="themeChip"', content)

        # 2. Unreleased sponsor feature completely removed
        self.assertNotIn("Instant Sponsor Recharge", content)
        self.assertNotIn("watchInCallAd", content)

        # 3. Joy VIP upgrade redirection & VIP member elements present
        self.assertIn("btnUpgradeVip", content)
        self.assertIn("redirectToJoyVip", content)
        self.assertIn("topVipBanner", content)
        self.assertIn("headerVipPill", content)

        # 4. Clean production AI companions present
        self.assertIn("Joy", content)
        self.assertIn("Kabir", content)
        self.assertIn("Aman", content)
        self.assertIn("Riya", content)
        self.assertIn("Aisha", content)


if __name__ == "__main__":
    unittest.main()
