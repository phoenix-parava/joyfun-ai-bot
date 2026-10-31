"""
tests/test_emotional_memory.py
100% Offline Automated Test Suite for Joy Remembers (Milestone 1).
Validates database.py schema/CRUD/pooling and emotional_memory.py extraction/decay/budgeting.
Executes in < 1.0 second using standard library unittest.
"""

import os
import sys
import re
import math
import tempfile
import sqlite3
import threading
import unittest
import asyncio
from datetime import datetime, timezone, timedelta, date
from typing import List, Dict, Any, Optional
from unittest.mock import patch, MagicMock

# Mock edge_tts if not present in environment so app can be imported cleanly
if "edge_tts" not in sys.modules:
    sys.modules["edge_tts"] = MagicMock()

# Ensure joy-bot root directory is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Target module imports
import config
import database
from database import (
    SafeDBConnection,
    init_db,
    add_or_update_memory,
    get_user_memories,
    delete_user_memory,
    clear_user_memories,
    _DB_SEMAPHORE,
)
import emotional_memory
from emotional_memory import (
    estimate_tokens,
    format_memory_context,
    extract_memories_offline,
    extract_memories_heuristic,
    extract_memories_async,
    get_proactive_greeting,
    is_memory_active,
    filter_active_memories,
    resolve_event_date,
    MemoryItem,
)


class TestEmotionalMemoryMilestone1(unittest.IsolatedAsyncioTestCase):
    """Zero-dependency, 100% offline test suite for Milestone 1."""

    def setUp(self):
        """Create isolated temporary SQLite database for each test in RAM disk if available."""
        temp_dir = "/dev/shm" if os.path.exists("/dev/shm") else None
        self.temp_db = tempfile.NamedTemporaryFile(dir=temp_dir, suffix=".db", delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

        # Patch DB_PATH in both config and database modules
        self.patcher_db = patch("database.DB_PATH", self.db_path)
        self.patcher_cfg = patch("config.DB_PATH", self.db_path)
        self.patcher_db.start()
        self.patcher_cfg.start()

        # Initialize schema
        init_db()
        with SafeDBConnection(self.db_path) as conn:
            conn.execute("PRAGMA synchronous = OFF")

        # Fixed reference time anchor: 2026-10-25 12:00:00 UTC (Sunday)
        self.ref_now = datetime(2026, 10, 25, 12, 0, 0, tzinfo=timezone.utc)
        self.today_str = "2026-10-25"

    def tearDown(self):
        """Clean up patches and temporary database file."""
        self.patcher_db.stop()
        self.patcher_cfg.stop()
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except OSError:
                pass

    # =========================================================================
    # PART 1: DATABASE STORAGE LAYER TESTS (database.py)
    # =========================================================================

    def test_01_init_db_creates_user_memories_table(self):
        """DB-01: Verify user_memories table schema, columns, and types."""
        with SafeDBConnection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(user_memories)")
            cols = {row["name"]: row["type"].upper() for row in cursor.fetchall()}

        expected = {
            "id": "INTEGER",
            "user_id": "INTEGER",
            "category": "TEXT",
            "memory_key": "TEXT",
            "memory_val": "TEXT",
            "emotional_tag": "TEXT",
            "event_date": "TEXT",
            "created_at": "TEXT",
        }
        for col, col_type in expected.items():
            self.assertIn(col, cols, f"Missing column {col} in user_memories")
            self.assertTrue(
                expected[col] in cols[col],
                f"Column {col} type mismatch: expected {expected[col]}, got {cols[col]}"
            )

    def test_02_init_db_idempotency(self):
        """DB-02: Repeated calls to init_db() must preserve existing data and structure."""
        mem_id = add_or_update_memory(
            user_id=1001,
            category="preference",
            memory_key="coding",
            memory_val="Loves Python",
            emotional_tag="happy",
            event_date=""
        )
        self.assertGreater(mem_id, 0)

        # Re-run init_db twice
        init_db()
        init_db()

        # Verify record still intact
        memories = get_user_memories(user_id=1001, include_decayed=True)
        self.assertEqual(len(memories), 1)
        self.assertEqual(memories[0]["memory_val"], "Loves Python")

    def test_03_indexes_creation_and_query_planner(self):
        """DB-03: Verify indexes exist and are utilized by the SQLite query planner."""
        with SafeDBConnection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA index_list(user_memories)")
            indexes = [row["name"] for row in cursor.fetchall()]

            self.assertIn("idx_user_memories_user_id", indexes)
            self.assertIn("idx_user_memories_event_date", indexes)

            # Query planner check
            cursor.execute("EXPLAIN QUERY PLAN SELECT * FROM user_memories WHERE user_id = ?", (1001,))
            plan = cursor.fetchone()[3]
            self.assertIn("idx_user_memories_user_id", plan)

    def test_04_safe_db_connection_pool_cap(self):
        """DB-04: Verify connection pool semaphore strictly caps concurrent connections at 5."""
        conns = []
        try:
            # Open 5 simultaneous connections (reaching limit)
            for _ in range(5):
                c = SafeDBConnection(self.db_path, timeout=0.1)
                conns.append(c)
                c.__enter__()

            # Verify semaphore is fully acquired
            acquired_6th = _DB_SEMAPHORE.acquire(blocking=False)
            self.assertFalse(acquired_6th, "Semaphore permitted more than 5 connections!")
        finally:
            # Release all opened connections
            for c in conns:
                c.__exit__(None, None, None)

        # After closing, semaphore must be available again
        self.assertTrue(_DB_SEMAPHORE.acquire(blocking=False))
        _DB_SEMAPHORE.release()

    def test_05_safe_db_connection_exception_rollback(self):
        """DB-05: Exception in context manager triggers rollback and releases semaphore permit."""
        user_id = 9999
        try:
            with SafeDBConnection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO user_memories (user_id, category, memory_key, memory_val, created_at) VALUES (?, ?, ?, ?, ?)",
                    (user_id, "preference", "test_roll", "should_rollback", "2026-10-25T12:00:00Z")
                )
                raise RuntimeError("Intentional error for rollback testing")
        except RuntimeError:
            pass

        # Verify rollback was performed and semaphore is not leaked
        with SafeDBConnection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as cnt FROM user_memories WHERE user_id = ?", (user_id,))
            self.assertEqual(cursor.fetchone()["cnt"], 0)

    def test_06_crud_add_and_upsert_memory(self):
        """DB-06 / DB-08: Add memory and verify atomic UPSERT prevents duplicate clutter."""
        user_id = 2001
        # Step 1: Insert initial memory
        id1 = add_or_update_memory(
            user_id=user_id,
            category="preference",
            memory_key="drink",
            memory_val="Loves green tea",
            emotional_tag="calm",
            event_date=""
        )
        self.assertGreater(id1, 0)

        # Verify count is 1
        mems = get_user_memories(user_id=user_id, include_decayed=True)
        self.assertEqual(len(mems), 1)
        self.assertEqual(mems[0]["memory_val"], "Loves green tea")

        # Step 2: Upsert with updated value for same key
        id2 = add_or_update_memory(
            user_id=user_id,
            category="preference",
            memory_key="drink",
            memory_val="Prefers cold coffee now",
            emotional_tag="energetic",
            event_date=""
        )

        # Verify count is still exactly 1, updated value persists, no duplicate clutter
        mems_after = get_user_memories(user_id=user_id, include_decayed=True)
        self.assertEqual(len(mems_after), 1)
        self.assertEqual(mems_after[0]["memory_val"], "Prefers cold coffee now")
        self.assertEqual(mems_after[0]["emotional_tag"], "energetic")

    def test_07_crud_tenant_isolation(self):
        """DB-09: Verify strict tenant isolation between users."""
        add_or_update_memory(1001, "preference", "lang", "Python", "", "")
        add_or_update_memory(1002, "preference", "lang", "Rust", "", "")

        u1_mems = get_user_memories(1001, include_decayed=True)
        u2_mems = get_user_memories(1002, include_decayed=True)

        self.assertEqual(len(u1_mems), 1)
        self.assertEqual(u1_mems[0]["memory_val"], "Python")

        self.assertEqual(len(u2_mems), 1)
        self.assertEqual(u2_mems[0]["memory_val"], "Rust")

    def test_08_crud_delete_and_idor_protection(self):
        """DB-10: Verify deletion and authorization guard against cross-tenant deletion."""
        id_user1 = add_or_update_memory(1001, "preference", "hobby", "Gaming", "", "")
        id_user2 = add_or_update_memory(1002, "preference", "hobby", "Reading", "", "")

        # IDOR Attempt: User 1 tries to delete User 2's memory
        result = delete_user_memory(user_id=1001, memory_id=id_user2)
        self.assertFalse(result, "IDOR Vulnerability: User 1 deleted User 2's memory!")

        # Verify User 2's memory still exists
        self.assertEqual(len(get_user_memories(1002, include_decayed=True)), 1)

        # Valid Delete: User 1 deletes own memory
        self.assertTrue(delete_user_memory(user_id=1001, memory_id=id_user1))
        self.assertEqual(len(get_user_memories(1001, include_decayed=True)), 0)

    def test_09_crud_clear_user_memories(self):
        """DB-11: Clear all memories for a user without affecting other users."""
        add_or_update_memory(1001, "event", "exam1", "Math", "", "2026-10-26")
        add_or_update_memory(1001, "event", "exam2", "Physics", "", "2026-10-28")
        add_or_update_memory(1002, "event", "interview", "Tech Lead", "", "2026-10-29")

        cleared_count = clear_user_memories(user_id=1001)
        self.assertEqual(cleared_count, 2)
        self.assertEqual(len(get_user_memories(1001, include_decayed=True)), 0)

        # User 1002 untouched
        self.assertEqual(len(get_user_memories(1002, include_decayed=True)), 1)

    # =========================================================================
    # PART 2: EMOTIONAL MEMORY ENGINE TESTS (emotional_memory.py)
    # =========================================================================

    def test_10_extraction_upcoming_relative_event(self):
        """EM-01: Extract upcoming event with relative date ('tomorrow') and emotion."""
        text = "Hey Joy, I'm really stressed about my semester physics exam tomorrow morning at 9 AM."
        with patch("emotional_memory.datetime") as mock_dt:
            mock_dt.now.return_value = self.ref_now
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            extracted = extract_memories_offline(text)

        self.assertGreaterEqual(len(extracted), 1)
        ev = [e for e in extracted if e["category"] == "event"][0]
        self.assertIn("exam", ev["memory_key"].lower())
        self.assertEqual(ev["emotional_tag"].lower(), "stressed")
        # Tomorrow relative to 2026-10-25 is 2026-10-26
        self.assertEqual(ev["event_date"], "2026-10-26")

    def test_11_extraction_explicit_date_event(self):
        """EM-02: Extract event with explicit date ('Oct 28')."""
        text = "Wish me luck, my Google technical interview is on Oct 28."
        extracted = extract_memories_offline(text)

        self.assertGreaterEqual(len(extracted), 1)
        ev = [e for e in extracted if e["category"] == "event"][0]
        self.assertIn("interview", ev["memory_key"].lower())
        self.assertIn("2026-10-28", ev["event_date"])

    def test_12_extraction_personal_preference_and_facts(self):
        """EM-03 & EM-04: Extract personal preference and banter style."""
        text = "By the way, I absolutely love coding in Python and I prefer teasing banter."
        extracted = extract_memories_offline(text)

        self.assertGreaterEqual(len(extracted), 1)
        prefs = [e for e in extracted if e["category"] == "preference"]
        pref_vals = " ".join([p["memory_val"].lower() for p in prefs])
        self.assertTrue("coding" in pref_vals or "python" in pref_vals or "banter" in pref_vals)

    def test_13_extraction_negative_control_ignore_glitches(self):
        """EM-06: Transient network noise and mic glitch messages must produce NO memories."""
        glitch_messages = [
            "Can you hear me? The mic line fluttered.",
            "voice cracked, please repeat that",
            "say that again line lagged",
            "firse bol can't hear you"
        ]
        for msg in glitch_messages:
            extracted = extract_memories_offline(msg)
            self.assertEqual(len(extracted), 0, f"False positive extracted from glitch: '{msg}'")

    def test_14_memory_aging_and_decay_rules(self):
        """EM-08 to EM-18: Rigorous test of event decay, emotion shelf life, and enduring facts."""
        user_id = 3001
        now = self.ref_now

        # 1. Upcoming Event (T + 2 days) -> ACTIVE
        add_or_update_memory(user_id, "event", "flight", "Flight to Delhi", "", (now + timedelta(days=2)).strftime("%Y-%m-%d"))

        # 2. Callback Window Event (T - 1 day, yesterday) -> ACTIVE
        add_or_update_memory(user_id, "event", "exam_yest", "Chemistry Exam", "relieved", (now - timedelta(days=1)).strftime("%Y-%m-%d"))

        # 3. Expired Event (T - 3 days) -> DECAYED
        add_or_update_memory(user_id, "event", "old_interview", "Mock Interview", "", (now - timedelta(days=3)).strftime("%Y-%m-%d"))

        # 4. Fresh Emotion (T - 12 hours) -> ACTIVE
        t_fresh = (now - timedelta(hours=12)).isoformat()
        with SafeDBConnection(self.db_path) as conn:
            conn.execute(
                "INSERT INTO user_memories (user_id, category, memory_key, memory_val, emotional_tag, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, "emotion", "mood_fresh", "feeling excited", "excited", t_fresh)
            )

        # 5. Stale Emotion (T - 50 hours, > 48h shelf life) -> DECAYED
        t_stale = (now - timedelta(hours=50)).isoformat()
        with SafeDBConnection(self.db_path) as conn:
            conn.execute(
                "INSERT INTO user_memories (user_id, category, memory_key, memory_val, emotional_tag, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, "emotion", "mood_old", "feeling anxious", "anxious", t_stale)
            )

        # 6. Enduring Preference (T - 60 days) -> PERMANENT / ACTIVE
        t_pref = (now - timedelta(days=60)).isoformat()
        with SafeDBConnection(self.db_path) as conn:
            conn.execute(
                "INSERT INTO user_memories (user_id, category, memory_key, memory_val, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, "preference", "food", "Loves spicy Biryani", t_pref)
            )

        # Query active memories only
        with patch("emotional_memory.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            active_mems = get_user_memories(user_id, include_decayed=False)
            all_mems = get_user_memories(user_id, include_decayed=True)

        active_keys = [m["memory_key"] for m in active_mems]

        # Active assertions
        self.assertIn("flight", active_keys, "Upcoming event must be active")
        self.assertIn("exam_yest", active_keys, "Yesterday's event must be active for callback")
        self.assertIn("mood_fresh", active_keys, "Emotion < 48h must be active")
        self.assertIn("food", active_keys, "Enduring preference must be permanent")

        # Decayed assertions
        self.assertNotIn("old_interview", active_keys, "Event older than 2 days must decay")
        self.assertNotIn("mood_old", active_keys, "Emotion older than 48 hours must decay")

        # Full audit assertion
        self.assertEqual(len(all_mems), 6, "include_decayed=True must return all 6 memories")

    def test_15_estimate_tokens(self):
        """EM-19: Token estimator calculation accuracy."""
        self.assertEqual(estimate_tokens(""), 0)
        self.assertGreater(estimate_tokens("Hello world"), 0)
        # ~3.5-4 chars per token
        short_tokens = estimate_tokens("Short sentence.")
        long_tokens = estimate_tokens("Short sentence. " * 20)
        self.assertGreater(long_tokens, short_tokens)

    def test_16_format_memory_context_strict_token_budget(self):
        """EM-21: Context formatter must strictly respect < 150 token budget even with 50 memories."""
        user_id = 4001
        # Insert 50 varied memories
        for i in range(50):
            add_or_update_memory(
                user_id=user_id,
                category="preference" if i % 2 == 0 else "personal_fact",
                memory_key=f"fact_{i}",
                memory_val=f"Fact number {i}: User enjoys learning technical concepts and building high scale systems in Python.",
                emotional_tag="focused",
                event_date=""
            )

        context_str = format_memory_context(user_id, max_tokens=150)
        self.assertIsInstance(context_str, str)
        self.assertTrue(len(context_str) > 0)

        token_count = estimate_tokens(context_str)
        self.assertLessEqual(token_count, 150, f"Token budget exceeded! Count: {token_count}")

    def test_17_format_memory_context_empty(self):
        """EM-20: Formatter returns empty string when user has no active memories."""
        context_str = format_memory_context(user_id=8888, max_tokens=150)
        self.assertEqual(context_str, "")
        self.assertEqual(estimate_tokens(context_str), 0)

    def test_18_proactive_greeting_callback(self):
        """EM-24 & EM-25: Proactive call greeting callback generation."""
        user_id = 5001
        now = self.ref_now

        # Case A: User had an exam yesterday with emotional tag 'stressed'
        yest_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        add_or_update_memory(
            user_id=user_id,
            category="event",
            memory_key="semester_exam",
            memory_val="semester exam",
            emotional_tag="stressed",
            event_date=yest_str
        )

        with patch("emotional_memory.datetime") as mock_dt:
            mock_dt.now.return_value = now
            greeting = get_proactive_greeting(user_id=user_id, caller_name="Joy")

        self.assertIsNotNone(greeting)
        self.assertTrue(
            "exam" in greeting.lower() or "stress" in greeting.lower() or "yesterday" in greeting.lower()
        )

        # Case B: User has no time-sensitive events
        clear_user_memories(user_id)
        add_or_update_memory(user_id, "preference", "color", "Blue", "", "")
        greeting_none = get_proactive_greeting(user_id=user_id, caller_name="Joy")
        self.assertIsNone(greeting_none)

    async def test_19_extract_memories_async_safe(self):
        """EM-26: Async extraction hook must be non-blocking and swallow errors cleanly."""
        user_id = 6001
        # Normal extraction
        await extract_memories_async(
            user_id=user_id,
            user_message="I have an interview tomorrow and I'm nervous",
            assistant_reply="You'll do great! Get plenty of rest."
        )

        # Verify memory was persisted
        mems = get_user_memories(user_id=user_id, include_decayed=True)
        self.assertGreaterEqual(len(mems), 1)

        # Error resilience: Pass None/invalid types, verify it handles gracefully
        try:
            await extract_memories_async(user_id=user_id, user_message=None, assistant_reply=None)
        except Exception as e:
            self.fail(f"extract_memories_async crashed on invalid input: {e}")

    def test_20_oversized_string_handling(self):
        """Verify that an individual oversized memory (2,000 chars) is truncated safely under 150 tokens."""
        user_id = 7001
        huge_val = "Very long personal memory detail " * 60  # ~2,000 chars
        add_or_update_memory(
            user_id=user_id,
            category="preference",
            memory_key="long_story",
            memory_val=huge_val,
            emotional_tag="",
            event_date=""
        )
        context_str = format_memory_context(user_id, max_tokens=150)
        self.assertTrue(len(context_str) > 0)
        self.assertLessEqual(estimate_tokens(context_str), 150)

    def test_21_memory_item_dataclass_serialization(self):
        """Verify MemoryItem serialization and deserialization."""
        item = MemoryItem(
            id=12,
            user_id=1001,
            category="event",
            memory_key="finals",
            memory_val="Math finals",
            emotional_tag="focused",
            event_date="2026-11-01",
            created_at="2026-10-25T12:00:00Z"
        )
        d = item.to_dict()
        self.assertEqual(d["id"], 12)
        self.assertEqual(d["category"], "event")
        restored = MemoryItem.from_dict(d)
        self.assertEqual(restored.memory_val, "Math finals")

    def test_22_resolve_event_date_various_formats(self):
        """Verify date resolution across relative words, in X days, weekdays, and calendar dates."""
        ref = date(2026, 10, 25)  # Sunday
        self.assertEqual(resolve_event_date("exam today", ref), "2026-10-25")
        self.assertEqual(resolve_event_date("exam tomorrow", ref), "2026-10-26")
        self.assertEqual(resolve_event_date("interview day after tomorrow", ref), "2026-10-27")
        self.assertEqual(resolve_event_date("trip yesterday", ref), "2026-10-24")
        self.assertEqual(resolve_event_date("flight in 5 days", ref), "2026-10-30")
        self.assertEqual(resolve_event_date("interview on next Monday", ref), "2026-10-26")
        self.assertEqual(resolve_event_date("Google interview on Oct 28", ref), "2026-10-28")
        self.assertEqual(resolve_event_date("wedding on 15 Nov", ref), "2026-11-15")


# =============================================================================
# PART 2: MILESTONE 2 INTEGRATION TESTS (REST API, PROMPT INJECTION, SCHEDULING)
# =============================================================================

class TestEmotionalMemoryMilestone2(unittest.IsolatedAsyncioTestCase):
    """
    100% Offline Integration Test Suite for Milestone 2:
    - REST Endpoints (GET /api/memories, POST /api/memories/delete, POST /api/memories/wipe, OPTIONS)
    - Dynamic Prompt Context Injection in ai_engine.py (<150 tokens)
    - Proactive Spoken Greeting Engine for Calls
    - Non-blocking Background Extraction Task Scheduling in app.py
    """

    async def asyncSetUp(self):
        """Create isolated temporary SQLite database and in-memory test aiohttp client."""
        temp_dir = "/dev/shm" if os.path.exists("/dev/shm") else None
        self.temp_db = tempfile.NamedTemporaryFile(dir=temp_dir, suffix=".db", delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

        self.patcher_db = patch("database.DB_PATH", self.db_path)
        self.patcher_cfg = patch("config.DB_PATH", self.db_path)
        self.patcher_db.start()
        self.patcher_cfg.start()

        init_db()
        with SafeDBConnection(self.db_path) as conn:
            conn.execute("PRAGMA synchronous = OFF")

        # Mock edge_tts if not present in environment
        if "edge_tts" not in sys.modules:
            sys.modules["edge_tts"] = MagicMock()

        import app
        from aiohttp import web, test_utils

        # Build test application with Milestone 2 endpoints
        test_app = web.Application()
        test_app.router.add_get("/api/memories", app.get_user_memories_api)
        test_app.router.add_post("/api/memories/delete", app.delete_user_memory_api)
        test_app.router.add_post("/api/memories/wipe", app.wipe_user_memories_api)
        test_app.router.add_options("/api/memories", app.handle_cors_options)
        test_app.router.add_options("/api/memories/delete", app.handle_cors_options)
        test_app.router.add_options("/api/memories/wipe", app.handle_cors_options)

        self.client = test_utils.TestClient(test_utils.TestServer(test_app))
        await self.client.start_server()

        self.test_user_id = 987654321
        self.peer_user_id = 123456789

    async def asyncTearDown(self):
        """Clean up test client, patches, and temporary database."""
        await self.client.close()
        self.patcher_db.stop()
        self.patcher_cfg.stop()
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except OSError:
                pass

    # -------------------------------------------------------------------------
    # REST API Integration Tests
    # -------------------------------------------------------------------------

    async def test_23_rest_get_memories_success(self):
        """REST-01: GET /api/memories returns active memories and CORS headers."""
        add_or_update_memory(
            user_id=self.test_user_id,
            category="preference",
            memory_key="coding",
            memory_val="Loves writing Python",
            emotional_tag="excited"
        )
        add_or_update_memory(
            user_id=self.test_user_id,
            category="fact",
            memory_key="pet",
            memory_val="Has a golden retriever named Max",
            emotional_tag="happy"
        )

        resp = await self.client.get(f"/api/memories?user_id={self.test_user_id}")
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "*")
        
        data = await resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["user_id"], self.test_user_id)
        self.assertEqual(data["count"], 2)
        self.assertEqual(len(data["memories"]), 2)
        self.assertEqual(data["memories"][0]["user_id"], self.test_user_id)

    async def test_24_rest_get_memories_missing_user_id(self):
        """REST-02: GET /api/memories without valid user_id returns 400 Bad Request."""
        resp1 = await self.client.get("/api/memories")
        self.assertEqual(resp1.status, 400)
        data1 = await resp1.json()
        self.assertEqual(data1["status"], "error")

        resp2 = await self.client.get("/api/memories?user_id=not_an_int")
        self.assertEqual(resp2.status, 400)
        data2 = await resp2.json()
        self.assertEqual(data2["status"], "error")

        resp3 = await self.client.get("/api/memories?user_id=-5")
        self.assertEqual(resp3.status, 400)

    async def test_25_rest_get_memories_include_decayed(self):
        """REST-03: GET /api/memories respects include_decayed flag."""
        # Active preference
        add_or_update_memory(
            user_id=self.test_user_id,
            category="preference",
            memory_key="drink",
            memory_val="Loves matcha latte"
        )
        # Expired event (10 days ago)
        add_or_update_memory(
            user_id=self.test_user_id,
            category="event",
            memory_key="past_concert",
            memory_val="Rock concert",
            event_date="2026-10-10"
        )

        # Default (include_decayed=False)
        resp_active = await self.client.get(f"/api/memories?user_id={self.test_user_id}")
        data_active = await resp_active.json()
        self.assertEqual(data_active["count"], 1)
        self.assertEqual(data_active["memories"][0]["memory_key"], "drink")

        # include_decayed=True
        resp_all = await self.client.get(f"/api/memories?user_id={self.test_user_id}&include_decayed=true")
        data_all = await resp_all.json()
        self.assertEqual(data_all["count"], 2)

    async def test_26_rest_delete_memory_success(self):
        """REST-04: POST /api/memories/delete purges memory from SQLite."""
        mid = add_or_update_memory(
            user_id=self.test_user_id,
            category="preference",
            memory_key="food",
            memory_val="Craves spicy ramen"
        )

        payload = {"user_id": self.test_user_id, "memory_id": mid}
        resp = await self.client.post("/api/memories/delete", json=payload)
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertTrue(data["deleted"])
        self.assertEqual(data["memory_id"], mid)

        # Confirm deleted in SQLite
        remaining = get_user_memories(self.test_user_id, include_decayed=True)
        self.assertEqual(len(remaining), 0)

    async def test_27_rest_delete_memory_tenant_isolation_idor(self):
        """REST-05: POST /api/memories/delete protects against IDOR tenant crossing."""
        mid_peer = add_or_update_memory(
            user_id=self.peer_user_id,
            category="preference",
            memory_key="secret",
            memory_val="Peer private fact"
        )

        # Unauthorized user attempts to delete peer's memory ID
        malicious_payload = {"user_id": self.test_user_id, "memory_id": mid_peer}
        resp = await self.client.post("/api/memories/delete", json=malicious_payload)
        self.assertEqual(resp.status, 404)
        data = await resp.json()
        self.assertFalse(data["deleted"])

        # Confirm peer's memory remains intact
        peer_mems = get_user_memories(self.peer_user_id, include_decayed=True)
        self.assertEqual(len(peer_mems), 1)

    async def test_28_rest_delete_memory_invalid_payload(self):
        """REST-06: POST /api/memories/delete rejects malformed or missing payloads."""
        resp1 = await self.client.post("/api/memories/delete", data="invalid_json", headers={"Content-Type": "application/json"})
        self.assertEqual(resp1.status, 400)

        resp2 = await self.client.post("/api/memories/delete", json={"user_id": self.test_user_id})
        self.assertEqual(resp2.status, 400)

        resp3 = await self.client.post("/api/memories/delete", json={"user_id": -1, "memory_id": 5})
        self.assertEqual(resp3.status, 400)

    async def test_29_rest_wipe_memories_success(self):
        """REST-07: POST /api/memories/wipe completely purges all user memories."""
        add_or_update_memory(self.test_user_id, "preference", "k1", "val1")
        add_or_update_memory(self.test_user_id, "fact", "k2", "val2")
        add_or_update_memory(self.test_user_id, "event", "k3", "val3")
        add_or_update_memory(self.peer_user_id, "preference", "peer_k", "peer_val")

        payload = {"user_id": self.test_user_id}
        resp = await self.client.post("/api/memories/wipe", json=payload)
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["cleared"], 3)
        self.assertEqual(data["user_id"], self.test_user_id)

        # Verify target user memories are 0, while peer user memories remain intact
        self.assertEqual(len(get_user_memories(self.test_user_id, include_decayed=True)), 0)
        self.assertEqual(len(get_user_memories(self.peer_user_id, include_decayed=True)), 1)

    async def test_30_rest_options_cors_preflight(self):
        """REST-08: OPTIONS preflight returns HTTP 204 with CORS headers."""
        for endpoint in ("/api/memories", "/api/memories/delete", "/api/memories/wipe"):
            resp = await self.client.options(endpoint)
            self.assertEqual(resp.status, 204)
            self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "*")
            self.assertIn("GET", resp.headers.get("Access-Control-Allow-Methods", ""))
            self.assertIn("POST", resp.headers.get("Access-Control-Allow-Methods", ""))

    # -------------------------------------------------------------------------
    # Dynamic Prompt Injection Tests (ai_engine.py)
    # -------------------------------------------------------------------------

    def test_31_prompt_injection_with_memories(self):
        """INJECT-01: generate_text_reply injects active memories into system_instruction."""
        today_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        add_or_update_memory(
            user_id=self.test_user_id,
            category="event",
            memory_key="exam",
            memory_val="Math finals",
            event_date=today_iso,
            emotional_tag="stressed"
        )
        add_or_update_memory(
            user_id=self.test_user_id,
            category="preference",
            memory_key="music",
            memory_val="Loves listening to lo-fi beats"
        )

        from ai_engine import generate_text_reply

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Good luck with your math finals! Put on some lo-fi beats and relax."
        mock_client.models.generate_content.return_value = mock_response
        mock_types = MagicMock()

        with patch("ai_engine.types", mock_types), \
             patch("ai_engine.get_gemini_client", return_value=mock_client):
            reply = generate_text_reply(
                user_text="Hey Joy, I need to focus today",
                user_id=self.test_user_id
            )

        self.assertIn("Good luck", reply)
        call_args = mock_types.GenerateContentConfig.call_args
        system_instruction = call_args[1]["system_instruction"]

        self.assertIn("[Joy's Emotional Memories]:", system_instruction)
        self.assertIn("Math finals", system_instruction)
        self.assertIn("lo-fi beats", system_instruction)

    def test_32_prompt_injection_empty_when_no_memories(self):
        """INJECT-02: When user has no memories, emotional memory block is not injected."""
        from ai_engine import generate_text_reply

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Hey there! How's your day going?"
        mock_client.models.generate_content.return_value = mock_response
        mock_types = MagicMock()

        with patch("ai_engine.types", mock_types), \
             patch("ai_engine.get_gemini_client", return_value=mock_client):
            generate_text_reply(
                user_text="Hey Joy",
                user_id=999999  # No memories for this user
            )

        call_args = mock_types.GenerateContentConfig.call_args
        system_instruction = call_args[1]["system_instruction"]
        self.assertNotIn("[Joy's Emotional Memories]:", system_instruction)

    def test_33_prompt_injection_token_budget_bound(self):
        """INJECT-03: System prompt injection overhead stays strictly under 150 tokens."""
        # Populate 30 memories to simulate potential context overflow
        for i in range(30):
            add_or_update_memory(
                user_id=self.test_user_id,
                category="fact",
                memory_key=f"fact_{i}",
                memory_val=f"Long detailed personal memory item number {i} discussing user life history"
            )

        context_block = format_memory_context(self.test_user_id, max_tokens=150)
        self.assertTrue(len(context_block) > 0)
        tokens_est = estimate_tokens(context_block)
        self.assertLessEqual(tokens_est, 150)

    def test_34_prompt_injection_coexistence_with_imported_memory(self):
        """INJECT-04: Dynamic emotional memories and legacy imported memories coexist cleanly."""
        add_or_update_memory(
            user_id=self.test_user_id,
            category="preference",
            memory_key="coding",
            memory_val="Loves Python"
        )
        legacy_memory = "User used to talk to Replika about astronomy."

        from ai_engine import generate_text_reply

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Hey!"
        mock_client.models.generate_content.return_value = mock_response
        mock_types = MagicMock()

        with patch("ai_engine.types", mock_types), \
             patch("ai_engine.get_gemini_client", return_value=mock_client):
            generate_text_reply(
                user_text="Hello",
                user_memory=legacy_memory,
                user_id=self.test_user_id
            )

        call_args = mock_types.GenerateContentConfig.call_args
        sys_inst = call_args[1]["system_instruction"]

        # Both memory sections must be present without clobbering each other
        self.assertIn("[USER'S PAST MEMORIES IMPORTED FROM PREVIOUS AI COMPANION]:", sys_inst)
        self.assertIn("astronomy", sys_inst)
        self.assertIn("[Joy's Emotional Memories]:", sys_inst)
        self.assertIn("Loves Python", sys_inst)

    def test_35_voice_prompt_injection(self):
        """INJECT-05: generate_voice_reply injects active memory block into live voice prompt."""
        today_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        add_or_update_memory(
            user_id=self.test_user_id,
            category="event",
            memory_key="interview",
            memory_val="Google interview",
            event_date=today_iso,
            emotional_tag="nervous"
        )

        from ai_engine import generate_voice_reply

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "TRANSCRIPT: I'm nervous\nREPLY: You're going to crush your Google interview!"
        mock_client.models.generate_content.return_value = mock_response

        # Generate fake non-silent WAV audio
        fake_wav = b"RIFF" + b"\x00" * 36 + b"data" + b"\x00" * 4 + (b"\x10\x20" * 500)
        mock_types = MagicMock()
        mock_types.Part.from_bytes.return_value = "audio_part"

        with patch("ai_engine.types", mock_types), \
             patch("ai_engine.get_gemini_client", return_value=mock_client), \
             patch("ai_engine.is_wav_audio_silent", return_value=False):
            transcript, reply = generate_voice_reply(
                audio_bytes=fake_wav,
                user_id=self.test_user_id
            )

        call_args = mock_types.GenerateContentConfig.call_args
        sys_inst = call_args[1]["system_instruction"]
        self.assertIn("[Joy's Emotional Memories]:", sys_inst)
        self.assertIn("Google interview", sys_inst)

    def test_36_resolve_memory_instruction_deduplication(self):
        """INJECT-06: resolve_memory_instruction suppresses legacy memory if identical or substring."""
        from ai_engine import resolve_memory_instruction

        add_or_update_memory(
            user_id=self.test_user_id,
            category="preference",
            memory_key="coding",
            memory_val="Loves Python"
        )

        # Exact duplicate
        inst_dup = resolve_memory_instruction(
            user_id=self.test_user_id,
            user_memory="Loves Python"
        )
        self.assertIn("[Joy's Emotional Memories]:", inst_dup)
        self.assertNotIn("[USER'S PAST MEMORIES IMPORTED", inst_dup)

        # Distinct legacy memory
        inst_distinct = resolve_memory_instruction(
            user_id=self.test_user_id,
            user_memory="Loves hiking in mountains"
        )
        self.assertIn("[Joy's Emotional Memories]:", inst_distinct)
        self.assertIn("[USER'S PAST MEMORIES IMPORTED", inst_distinct)

    # -------------------------------------------------------------------------
    # Non-Blocking Extraction Task Scheduling Tests
    # -------------------------------------------------------------------------

    async def test_37_async_extraction_scheduling_non_blocking(self):
        """EXTRACT-01: Background task scheduling persists memories asynchronously."""
        from emotional_memory import extract_and_store_memories_async

        # Launch extraction task as a background task
        task = asyncio.create_task(
            extract_and_store_memories_async(
                user_id=self.test_user_id,
                user_message="I have my final exams tomorrow and I'm stressed",
                assistant_reply="Take a deep breath! You've prepared hard."
            )
        )

        # Await task completion
        await task

        # Verify extracted entries in SQLite
        mems = get_user_memories(self.test_user_id, include_decayed=True)
        self.assertGreaterEqual(len(mems), 1)
        event_keys = [m["memory_key"] for m in mems]
        self.assertTrue(any("exam" in k for k in event_keys))

    async def test_38_async_extraction_exception_resilience(self):
        """EXTRACT-02: Extraction task safely catches exceptions without crashing event loop."""
        from emotional_memory import extract_and_store_memories_async

        # Simulate exception inside database persistence
        with patch("database.add_or_update_memory", side_effect=sqlite3.OperationalError("Database disk image is malformed")):
            try:
                task = asyncio.create_task(
                    extract_and_store_memories_async(
                        user_id=self.test_user_id,
                        user_message="I love coding in Python",
                        assistant_reply="Coding is awesome!"
                    )
                )
                await task
            except Exception as e:
                self.fail(f"Background task leaked an uncaught exception: {e}")

    # -------------------------------------------------------------------------
    # Proactive Spoken Greeting Tests
    # -------------------------------------------------------------------------

    def test_39_proactive_greeting_call_event_triggered(self):
        """GREET-01: Proactive greeting is triggered when an upcoming or recent event exists."""
        ref_dt = datetime(2026, 10, 25, 12, 0, 0, tzinfo=timezone.utc)

        # Event yesterday (Oct 24) with emotional tag 'stressed'
        add_or_update_memory(
            user_id=self.test_user_id,
            category="event",
            memory_key="semester_exam",
            memory_val="semester exam",
            event_date="2026-10-24",
            emotional_tag="stressed"
        )

        greeting = get_proactive_greeting(
            user_id=self.test_user_id,
            caller_name="Joy",
            user_name="Phoenix",
            reference_time=ref_dt
        )
        self.assertIsNotNone(greeting)
        self.assertIn("Phoenix", greeting)
        self.assertIn("semester exam", greeting)
        self.assertIn("yesterday", greeting)

    def test_40_proactive_greeting_silent_when_no_qualifying_event(self):
        """GREET-02: Proactive greeting returns None (silent phone line) when no active event exists."""
        ref_dt = datetime(2026, 10, 25, 12, 0, 0, tzinfo=timezone.utc)

        # Only permanent preferences, no time-sensitive events
        add_or_update_memory(
            user_id=self.test_user_id,
            category="preference",
            memory_key="food",
            memory_val="Loves sushi"
        )

        greeting = get_proactive_greeting(
            user_id=self.test_user_id,
            caller_name="Joy",
            user_name="Phoenix",
            reference_time=ref_dt
        )
        self.assertIsNone(greeting)


if __name__ == "__main__":
    unittest.main()
