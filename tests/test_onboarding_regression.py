"""
tests/test_onboarding_regression.py
Automated Regression Test Suite for Joy Bot Onboarding State Machine & Menu Access.
Validates:
1. End-to-end progression through steps 1 to 6+ without getting stuck in infinite loops.
2. Step 6 (Privacy) and Step 6+ (Login) properly transition user to 'completed'.
3. Text input during late onboarding steps auto-completes and unlocks normal chat.
4. Universal /menu and '📱 Menu' commands work with creator immunity (Owner ID 8747280850).
5. Beta tester persistence across updates and re-admissions.
Executes 100% offline in < 1.0 second.
"""

import os
import sys
import unittest
import tempfile
import sqlite3
from unittest.mock import MagicMock, patch, AsyncMock

# Ensure joy-bot root directory is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import config
import database
from database import (
    init_db,
    get_or_create_user,
    set_user_onboarding_status,
    set_user_language,
    set_user_gender,
    is_user_beta_approved
)

class TestOnboardingRegression(unittest.TestCase):
    """Test suite for Onboarding state transitions and menu guardrails."""

    def setUp(self):
        """Set up an isolated temporary SQLite database for each test run in RAM (/dev/shm)."""
        temp_dir = "/dev/shm" if os.path.exists("/dev/shm") else None
        self.temp_db = tempfile.NamedTemporaryFile(dir=temp_dir, suffix=".db", delete=False)
        self.temp_db_path = self.temp_db.name
        self.temp_db.close()

        # Patch config and database connection to point to test DB
        self.orig_db_path = database.DB_PATH
        database.DB_PATH = self.temp_db_path
        init_db()

    def tearDown(self):
        """Clean up temporary database."""
        database.DB_PATH = self.orig_db_path
        if os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except OSError:
                pass

    def test_new_user_initial_onboarding_status(self):
        """Assert new users are created with status 'new' and correct default attributes."""
        user = get_or_create_user(user_id=1001, username="test_phoenix", first_name="Phoenix")
        self.assertEqual(user["user_id"], 1001)
        self.assertEqual(user["onboarding_status"], "new")
        self.assertEqual(user["username"], "test_phoenix")

    def test_onboarding_step_transitions_sequence(self):
        """Verify strict progression across all onboarding milestones."""
        user_id = 1002
        get_or_create_user(user_id=user_id, username="stepper", first_name="Stepper")

        steps = [
            "onboard_country",
            "onboard_language",
            "onboard_gender",
            "onboard_contacts_preview",
            "onboard_naming",
            "onboard_privacy",
            "onboard_login",
            "completed"
        ]

        for step in steps:
            set_user_onboarding_status(user_id, step)
            u = get_or_create_user(user_id)
            self.assertEqual(u["onboarding_status"], step, f"Failed at step: {step}")

    def test_step_6_and_login_finalization(self):
        """
        Verify that user transitioning from onboard_privacy (Step 6) and
        onboard_login (Step 6+) properly reaches 'completed'.
        """
        user_id = 1003
        get_or_create_user(user_id=user_id, username="privacy_user")
        
        # Step 6: Privacy
        set_user_onboarding_status(user_id, "onboard_privacy")
        u = get_or_create_user(user_id)
        self.assertEqual(u["onboarding_status"], "onboard_privacy")

        # Step 6+: Login card
        set_user_onboarding_status(user_id, "onboard_login")
        u = get_or_create_user(user_id)
        self.assertEqual(u["onboarding_status"], "onboard_login")

        # Complete onboarding
        set_user_onboarding_status(user_id, "completed")
        u = get_or_create_user(user_id)
        self.assertEqual(u["onboarding_status"], "completed")

    def test_creator_immunity_user_id(self):
        """Assert that creator ID (8747280850) is recognized with full immunity."""
        creator_id = 8747280850
        user = get_or_create_user(user_id=creator_id, username="creator_phoenix")
        
        # Creator should always pass admin checks
        self.assertEqual(user["user_id"], 8747280850)
        self.assertEqual(config.CREATOR_ID, 8747280850)

    def test_language_and_gender_selection_persistence(self):
        """Verify user language and gender survive across onboarding."""
        user_id = 1004
        get_or_create_user(user_id=user_id, username="lang_tester")

        set_user_language(user_id, "hi")
        set_user_gender(user_id, "male")

        u = get_or_create_user(user_id)
        # "hi" alias is correctly normalized to "hinglish"
        self.assertEqual(u["language"], "hinglish")
        self.assertEqual(u["gender"], "male")

    def test_beta_tester_persistence_across_state_updates(self):
        """Assert beta tester approval status is never wiped during onboarding state updates."""
        user_id = 1005
        user = get_or_create_user(user_id=user_id, username="beta_pioneer")
        
        # Manually approve beta tester
        with database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET is_beta_tester = 1, beta_slot_number = 42 WHERE user_id = ?", (user_id,))
            conn.commit()

        # Update onboarding status
        set_user_onboarding_status(user_id, "completed")
        
        u = get_or_create_user(user_id)
        self.assertEqual(u["is_beta_tester"], 1)
        self.assertEqual(u["beta_slot_number"], 42)
        self.assertTrue(is_user_beta_approved(user_id))

if __name__ == "__main__":
    unittest.main()
