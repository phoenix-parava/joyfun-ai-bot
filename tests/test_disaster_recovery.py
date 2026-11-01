import os
import sys
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

os.environ["OFFLINE_TEST"] = "1"

# Ensure joy-bot root directory is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import backup_manager
from backup_manager import (
    create_db_snapshot,
    auto_restore_latest_snapshot
)

class TestDisasterRecovery(unittest.TestCase):
    """Automated test suite for Joy Bot's zero-data-loss cloud snapshot & auto-restore engine."""

    def setUp(self):
        # Create isolated temp directory for test databases and snapshots
        self.test_dir = tempfile.mkdtemp(prefix="joy_test_backup_")
        self.test_dir_path = Path(self.test_dir)

        self.db_path = self.test_dir_path / "test_joy.db"
        self.backup_dir = self.test_dir_path / "backups"
        self.safe_dir = self.test_dir_path / "safe"

        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.safe_dir.mkdir(parents=True, exist_ok=True)

        # Point backup_manager to our isolated test paths
        self.orig_db_file = backup_manager.DB_FILE
        self.orig_backup_dir = backup_manager.BACKUP_DIR
        self.orig_safe_dir = backup_manager.LOCAL_SAFE_DIR

        backup_manager.DB_FILE = self.db_path
        backup_manager.BACKUP_DIR = self.backup_dir
        backup_manager.LOCAL_SAFE_DIR = self.safe_dir

        # Initialize mock database with users and streaks
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    streak_count INTEGER DEFAULT 1,
                    is_vip INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                INSERT INTO users (user_id, username, first_name, streak_count, is_vip)
                VALUES (1001, 'tester1', 'Phoenix', 14, 1),
                       (1002, 'tester2', 'Anish', 7, 0)
            """)
            conn.commit()

    def tearDown(self):
        backup_manager.DB_FILE = self.orig_db_file
        backup_manager.BACKUP_DIR = self.orig_backup_dir
        backup_manager.LOCAL_SAFE_DIR = self.orig_safe_dir
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_create_db_snapshot_integrity(self):
        """Verify atomic SQLite snapshot is created with valid schema and zero corruption."""
        res = create_db_snapshot()
        self.assertTrue(res.get("ok"), f"Snapshot creation failed: {res}")
        snap_path = Path(res["snapshot_path"])
        self.assertTrue(snap_path.exists())
        self.assertGreater(res["size_kb"], 0)

        # Verify PRAGMA integrity check on the snapshot
        with sqlite3.connect(str(snap_path)) as conn:
            chk = conn.execute("PRAGMA integrity_check").fetchone()[0]
            self.assertEqual(chk, "ok", "Snapshot must pass SQLite integrity check")

            # Check data preserved
            count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            self.assertEqual(count, 2)
            u1 = conn.execute("SELECT first_name, streak_count, is_vip FROM users WHERE user_id = 1001").fetchone()
            self.assertEqual(u1, ("Phoenix", 14, 1))

    def test_02_auto_restore_when_database_missing(self):
        """Verify auto_restore_latest_snapshot detects missing database and recovers it perfectly."""
        # Create a fresh snapshot first
        snap_res = create_db_snapshot()
        self.assertTrue(snap_res["ok"])

        # Simulate disaster: database file is deleted completely (container restart)
        self.db_path.unlink()
        self.assertFalse(self.db_path.exists())

        # Trigger auto-restore
        restored = auto_restore_latest_snapshot(target_db=self.db_path)
        self.assertTrue(restored, "Auto-restore must succeed when DB is missing")
        self.assertTrue(self.db_path.exists(), "DB file must be re-created")

        # Verify all users and streak data recovered
        with sqlite3.connect(str(self.db_path)) as conn:
            rows = conn.execute("SELECT user_id, streak_count FROM users ORDER BY user_id").fetchall()
            self.assertEqual(rows, [(1001, 14), (1002, 7)])

    def test_03_auto_restore_skipped_when_already_populated(self):
        """Verify auto-restore does nothing if the existing database already has valid users."""
        create_db_snapshot()
        # Database already exists with 2 users
        restored = auto_restore_latest_snapshot(target_db=self.db_path)
        self.assertFalse(restored, "Auto-restore must not overwrite active populated database")

if __name__ == "__main__":
    unittest.main()
