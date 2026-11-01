import os
import unittest
from datetime import datetime, timezone, timedelta

os.environ["OFFLINE_TEST"] = "1"

from database import (
    init_db,
    get_connection,
    get_user_memories,
    delete_user_memory,
    clear_user_memories
)

class TestMemoryVaultChat(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_memories WHERE user_id >= 9950000")
            conn.commit()

    def test_01_empty_vault_state(self):
        """Verify empty vault returns zero memories."""
        user_id = 9950001
        mems = get_user_memories(user_id=user_id, include_decayed=False)
        self.assertEqual(len(mems), 0)

    def test_02_categorized_memories_storage_and_retrieval(self):
        """Verify memories are stored with category and retrieved cleanly."""
        user_id = 9950002
        now = datetime.now(timezone.utc).isoformat()
        future_date = (datetime.now(timezone.utc) + timedelta(days=3)).strftime("%Y-%m-%d")

        with get_connection() as conn:
            cursor = conn.cursor()
            # 1. Event
            cursor.execute("""
                INSERT INTO user_memories (user_id, category, memory_key, memory_val, event_date, created_at)
                VALUES (?, 'event', 'math_exam', 'Final Semester Mathematics Paper', ?, ?)
            """, (user_id, future_date, now))
            # 2. Preference
            cursor.execute("""
                INSERT INTO user_memories (user_id, category, memory_key, memory_val, created_at)
                VALUES (?, 'preference', 'coffee', 'Loves hot black coffee without sugar', ?)
            """, (user_id, now))
            # 3. Emotion
            cursor.execute("""
                INSERT INTO user_memories (user_id, category, memory_key, memory_val, created_at)
                VALUES (?, 'emotion', 'stressed', 'Felt overwhelmed studying late night', ?)
            """, (user_id, now))
            conn.commit()

        mems = get_user_memories(user_id=user_id, include_decayed=False)
        self.assertEqual(len(mems), 3)

        categories = [m["category"] for m in mems]
        self.assertIn("event", categories)
        self.assertIn("preference", categories)
        self.assertIn("emotion", categories)

    def test_03_selective_forget_by_keyword(self):
        """Verify granular keyword deletion removes only matching memories."""
        user_id = 9950003
        now = datetime.now(timezone.utc).isoformat()

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_memories (user_id, category, memory_key, memory_val, created_at)
                VALUES (?, 'preference', 'favorite_anime', 'One Piece with Zoro as favorite', ?)
            """, (user_id, now))
            cursor.execute("""
                INSERT INTO user_memories (user_id, category, memory_key, memory_val, created_at)
                VALUES (?, 'preference', 'comfort_drink', 'Caramel Macchiato', ?)
            """, (user_id, now))
            conn.commit()

        # Simulate /forget anime
        kw = "anime"
        all_mems = get_user_memories(user_id=user_id, include_decayed=True)
        matched = [m for m in all_mems if kw in (m["memory_key"] or "").lower() or kw in (m["memory_val"] or "").lower()]
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["memory_key"], "favorite_anime")

        # Delete matching memory
        deleted = delete_user_memory(user_id, matched[0]["id"])
        self.assertTrue(deleted)

        # Verify only the other memory remains
        remaining = get_user_memories(user_id=user_id, include_decayed=True)
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["memory_key"], "comfort_drink")

    def test_04_full_vault_wipe(self):
        """Verify 1-click wipe erases all memories for the user cleanly."""
        user_id = 9950004
        now = datetime.now(timezone.utc).isoformat()

        with get_connection() as conn:
            cursor = conn.cursor()
            for i in range(5):
                cursor.execute("""
                    INSERT INTO user_memories (user_id, category, memory_key, memory_val, created_at)
                    VALUES (?, 'preference', ?, 'Sample value', ?)
                """, (user_id, f"key_{i}", now))
            conn.commit()

        initial = get_user_memories(user_id=user_id, include_decayed=True)
        self.assertEqual(len(initial), 5)

        cleared_count = clear_user_memories(user_id=user_id)
        self.assertEqual(cleared_count, 5)

        after = get_user_memories(user_id=user_id, include_decayed=True)
        self.assertEqual(len(after), 0)

    def test_05_tenant_isolation_idor_prevention(self):
        """Verify user A cannot delete user B's memory."""
        user_a = 9950005
        user_b = 9950006
        now = datetime.now(timezone.utc).isoformat()

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_memories (user_id, category, memory_key, memory_val, created_at)
                VALUES (?, 'preference', 'secret', 'Private secret of user B', ?)
            """, (user_b, now))
            mem_b_id = cursor.lastrowid
            conn.commit()

        # User A tries to delete user B's memory
        deleted_by_a = delete_user_memory(user_id=user_a, memory_id=mem_b_id)
        self.assertFalse(deleted_by_a)

        # Verify User B's memory still exists intact
        mems_b = get_user_memories(user_id=user_b, include_decayed=True)
        self.assertEqual(len(mems_b), 1)

if __name__ == "__main__":
    unittest.main()
