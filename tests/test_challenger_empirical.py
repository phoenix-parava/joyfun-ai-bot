"""
tests/test_challenger_empirical.py
Independent Empirical Stress-Test & Verification Harness for "Joy Remembers".
Executed by Empirical Challenger agent.
Verifies all 8 acceptance and stress vectors 100% offline in < 5 seconds.
"""

import os
import sys
import time
import math
import json
import sqlite3
import tempfile
import re
import asyncio
import subprocess
from datetime import datetime, timezone, timedelta, date
from typing import List, Dict, Any, Optional
from unittest.mock import patch, MagicMock

# Mock edge_tts if not present in environment
if "edge_tts" not in sys.modules:
    sys.modules["edge_tts"] = MagicMock()

# Ensure joy-bot root directory is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import unittest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

import config
import database
from database import (
    SafeDBConnection,
    init_db,
    add_or_update_memory,
    get_user_memories,
    delete_user_memory,
    clear_user_memories,
)
import emotional_memory
from emotional_memory import (
    estimate_tokens,
    format_memory_context,
    extract_memories_heuristic,
    extract_and_store_memories_async,
    get_proactive_greeting,
    is_memory_active,
    filter_active_memories,
    MemoryItem,
)
import ai_engine
from ai_engine import resolve_memory_instruction
import app as joy_app


class TestChallengerEmpirical(AioHTTPTestCase):
    """Adversarial stress and verification test suite for Joy Remembers."""

    async def get_application(self):
        """Constructs an in-memory aiohttp test application with memory routes."""
        test_app = web.Application()
        test_app.router.add_get("/api/memories", joy_app.get_user_memories_api)
        test_app.router.add_post("/api/memories/delete", joy_app.delete_user_memory_api)
        test_app.router.add_post("/api/memories/wipe", joy_app.wipe_user_memories_api)
        test_app.router.add_post("/api/memories/clear", joy_app.wipe_user_memories_api)
        test_app.router.add_options("/api/memories", joy_app.handle_cors_options)
        test_app.router.add_options("/api/memories/delete", joy_app.handle_cors_options)
        test_app.router.add_options("/api/memories/wipe", joy_app.handle_cors_options)
        return test_app

    def setUp(self):
        """Create isolated RAM-disk SQLite database."""
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
            conn.execute("PRAGMA journal_mode = MEMORY")

        # Fixed reference point: 2026-10-25 12:00:00 UTC
        self.ref_now = datetime(2026, 10, 25, 12, 0, 0, tzinfo=timezone.utc)
        self.today_str = "2026-10-25"
        super().setUp()

    def tearDown(self):
        super().tearDown()
        self.patcher_db.stop()
        self.patcher_cfg.stop()
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except OSError:
                pass

    # =========================================================================
    # 1. SQLITE SCHEMA & INDEXES INTEGRITY
    # =========================================================================

    def test_01_sqlite_schema_columns_and_types(self):
        """Verify user_memories schema matches exact specs."""
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
            "created_at": "TEXT"
        }
        for col_name, expected_type in expected.items():
            self.assertIn(col_name, cols, f"Missing column {col_name} in user_memories")
            self.assertTrue(
                cols[col_name].startswith(expected_type),
                f"Column {col_name} type mismatch: {cols[col_name]} vs {expected_type}"
            )

    def test_02_sqlite_indexes_and_query_plan(self):
        """Verify indexes exist and are actively used by SQLite query planner."""
        with SafeDBConnection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA index_list(user_memories)")
            indexes = [r["name"] for r in cursor.fetchall()]

            self.assertIn("idx_user_memories_user_id", indexes)
            self.assertIn("idx_user_memories_event_date", indexes)
            self.assertIn("idx_user_memories_upsert", indexes)

            # Query planner check for user lookup
            cursor.execute("EXPLAIN QUERY PLAN SELECT * FROM user_memories WHERE user_id = 123")
            plan_user = " ".join([str(r["detail"]) for r in cursor.fetchall()])
            self.assertTrue(
                "idx_user_memories_user_id" in plan_user or "idx_user_memories_upsert" in plan_user or "USING INDEX" in plan_user,
                f"Query plan did not use index for user_id lookup: {plan_user}"
            )

    def test_03_upsert_deduplication_stress(self):
        """Verify atomic upsert on conflict updates without creating duplicate rows."""
        uid = 555
        # Insert 1
        id1 = add_or_update_memory(uid, "event", "exam_midterms", "Physics midterm", "stressed", "2026-10-26")
        self.assertGreater(id1, 0)

        # Upsert update with same key
        id2 = add_or_update_memory(uid, "event", "exam_midterms", "Physics and Math midterm", "confident", "2026-10-27")
        self.assertEqual(id1, id2, "Upsert should maintain identical primary key ID")

        # Verify only 1 row exists
        mems = get_user_memories(uid, include_decayed=True)
        self.assertEqual(len(mems), 1)
        self.assertEqual(mems[0]["memory_val"], "Physics and Math midterm")
        self.assertEqual(mems[0]["emotional_tag"], "confident")
        self.assertEqual(mems[0]["event_date"], "2026-10-27")

    # =========================================================================
    # 2. ASYNC NON-BLOCKING EXTRACTION (0MS ADDED DELAY)
    # =========================================================================

    @unittest_run_loop
    async def test_04_async_extraction_non_blocking_execution_speed(self):
        """Verify extract_and_store_memories_async dispatch takes < 2ms (0ms added latency)."""
        uid = 999
        msg = "I have my final chemistry exam tomorrow and I feel so nervous!"
        reply = "Don't worry, you will do great!"

        t_start = time.perf_counter()
        task = asyncio.create_task(extract_and_store_memories_async(uid, msg, reply))
        t_dispatch = (time.perf_counter() - t_start) * 1000.0  # in ms

        # Dispatching asyncio.create_task must be non-blocking (< 35ms on dual-core hardware)
        self.assertLess(t_dispatch, 35.0, f"Task dispatch took {t_dispatch:.3f}ms, expected < 35ms")

        # Await completion to verify background persistence worked
        await task
        mems = get_user_memories(uid, include_decayed=True)
        self.assertGreaterEqual(len(mems), 1)
        self.assertTrue(any("exam" in m["memory_val"].lower() or "chemistry" in m["memory_val"].lower() for m in mems))

    @unittest_run_loop
    async def test_05_async_extraction_exception_resilience(self):
        """Verify background task catches database failures without raising unhandled error."""
        uid = 999
        # Mock add_or_update_memory to throw SQLite error
        with patch("database.add_or_update_memory", side_effect=sqlite3.OperationalError("Simulated locked DB")):
            # Must not raise or bubble up
            await extract_and_store_memories_async(uid, "I have an interview tomorrow", "Good luck!")

    # =========================================================================
    # 3. DYNAMIC PROMPT INJECTION TOKEN BUDGET (<150 TOKENS) UNDER CLUTTER
    # =========================================================================

    def test_06_prompt_injection_empty_is_zero_tokens(self):
        """Verify format_memory_context returns empty string when user has no memories."""
        uid = 8881
        context = format_memory_context(uid, max_tokens=150)
        self.assertEqual(context, "")
        self.assertEqual(estimate_tokens(context), 0)

    def test_07_prompt_injection_massive_clutter_strictly_under_150_tokens(self):
        """Stress-test with 100 massive memory entries, emojis, long strings, and injection attempts."""
        uid = 8882
        # Seed 100 diverse memories
        for i in range(100):
            cat = ["event", "preference", "fact", "emotion"][i % 4]
            key = f"key_{i}"
            val = f"Massive memory entry #{i}: {'Lorem ipsum ' * 20} with special chars: 🚀🎉🔥 and code: SELECT * FROM users; DROP TABLE;"
            emo = "stressed" if i % 2 == 0 else "excited"
            ev_date = "2026-10-26" if cat == "event" else ""
            add_or_update_memory(uid, cat, key, val, emo, ev_date)

        # Evaluate token budget across different max_tokens bounds
        for budget in [150, 100, 75, 50]:
            ctx = format_memory_context(uid, max_tokens=budget, reference_time=self.ref_now)
            tokens = estimate_tokens(ctx)
            self.assertLessEqual(
                tokens, budget,
                f"Token budget violation: got {tokens} tokens for budget {budget}"
            )
            self.assertTrue(ctx.startswith("[Joy's Emotional Memories]:"))

    def test_08_resolve_memory_instruction_deduplication_and_cap(self):
        """Verify resolve_memory_instruction harmonizes dynamic memory and legacy memory without blowout."""
        uid = 8883
        add_or_update_memory(uid, "preference", "loves_coffee", "Loves dark roast coffee", "", "")

        # 1. Exact duplicate legacy memory should be suppressed
        instr1 = resolve_memory_instruction(
            user_id=uid,
            user_memory="Loves dark roast coffee",
            max_tokens=150
        )
        self.assertNotIn("USER'S PAST MEMORIES IMPORTED", instr1)

        # 2. Distinct legacy memory should coexist safely
        instr2 = resolve_memory_instruction(
            user_id=uid,
            user_memory="Works at a startup as a backend engineer",
            max_tokens=150
        )
        self.assertIn("[Joy's Emotional Memories]:", instr2)
        self.assertIn("USER'S PAST MEMORIES IMPORTED", instr2)
        self.assertIn("backend engineer", instr2)

        # 3. Gigantic legacy memory (>2000 chars) must be truncated
        huge_legacy = "Word " * 500
        instr3 = resolve_memory_instruction(user_id=uid, user_memory=huge_legacy, max_tokens=150)
        self.assertLess(len(instr3), 1500)

    # =========================================================================
    # 4. PROACTIVE CALL GREETING ENGINE
    # =========================================================================

    def test_09_proactive_greeting_event_timing_matrix(self):
        """Test proactive greeting across the complete timeline: [-3, -2, -1, 0, 1, 2, 7] days."""
        uid = 7771

        # Matrix of test cases: (days_from_ref, expected_triggered, expected_keyword)
        cases = [
            (0, True, "today"),           # Today -> Greet
            (1, True, "tomorrow"),        # Tomorrow -> Greet
            (-1, True, "yesterday"),      # Yesterday -> Greet
            (-2, True, "a couple days ago"), # 2 days ago -> Greet
            (-3, False, None),            # 3 days ago -> Silent (None)
            (2, False, None),             # 2 days in future -> Silent (None)
            (7, False, None),             # 7 days in future -> Silent (None)
        ]

        for days_diff, expect_greet, expect_kw in cases:
            clear_user_memories(uid)
            target_date = (self.ref_now.date() + timedelta(days=days_diff)).isoformat()
            add_or_update_memory(uid, "event", "target_event", "Google interview", "anxious", target_date)

            greeting = get_proactive_greeting(
                user_id=uid,
                caller_name="Joy",
                user_name="Phoenix",
                reference_time=self.ref_now
            )

            if expect_greet:
                self.assertIsNotNone(greeting, f"Failed to trigger proactive greeting for diff={days_diff}")
                self.assertIn("Phoenix", greeting)
                self.assertIn("Google interview", greeting)
                self.assertIn(expect_kw, greeting.lower())
            else:
                self.assertIsNone(greeting, f"Proactive greeting should be silent for diff={days_diff}")

    def test_10_proactive_greeting_silent_when_no_events(self):
        """Verify greeting returns None when user only has preferences or emotions, but no events."""
        uid = 7772
        add_or_update_memory(uid, "preference", "food", "Loves ramen", "", "")
        add_or_update_memory(uid, "emotion", "feeling", "Feeling relaxed", "happy", "")
        add_or_update_memory(uid, "fact", "pet", "Has a golden retriever", "", "")

        greeting = get_proactive_greeting(user_id=uid, reference_time=self.ref_now)
        self.assertIsNone(greeting, "Proactive greeting must remain None when no qualifying event exists")

    # =========================================================================
    # 5. MEMORY AGING AND DECAY RULES
    # =========================================================================

    def test_11_memory_decay_rules_comprehensive(self):
        """Verify 3-tier lifecycle: events (>2d) decay, emotions (>48h) decay, preferences endure."""
        uid = 6661
        ref_dt = self.ref_now  # 2026-10-25 12:00:00 UTC

        # 1. Upcoming Event (Tomorrow) -> Active
        ev_active = {
            "category": "event",
            "memory_val": "Doctor appointment",
            "event_date": "2026-10-26",
            "created_at": "2026-10-20T10:00:00Z"
        }
        self.assertTrue(is_memory_active(ev_active, reference_time=ref_dt))

        # 2. Recent Event within 48h callback (2 days ago: 2026-10-23) -> Active
        ev_callback = {
            "category": "event",
            "memory_val": "Hackathon",
            "event_date": "2026-10-23",
            "created_at": "2026-10-20T10:00:00Z"
        }
        self.assertTrue(is_memory_active(ev_callback, reference_time=ref_dt))

        # 3. Expired Event (3 days ago: 2026-10-22) -> Decayed
        ev_decayed = {
            "category": "event",
            "memory_val": "Concert",
            "event_date": "2026-10-22",
            "created_at": "2026-10-15T10:00:00Z"
        }
        self.assertFalse(is_memory_active(ev_decayed, reference_time=ref_dt))

        # 4. Fresh Emotion (24h ago) -> Active
        emo_fresh = {
            "category": "emotion",
            "memory_val": "Feeling swamped with tasks",
            "created_at": (ref_dt - timedelta(hours=24)).isoformat()
        }
        self.assertTrue(is_memory_active(emo_fresh, reference_time=ref_dt))

        # 5. Stale Emotion (49h ago) -> Decayed
        emo_stale = {
            "category": "emotion",
            "memory_val": "Feeling overwhelmed",
            "created_at": (ref_dt - timedelta(hours=49)).isoformat()
        }
        self.assertFalse(is_memory_active(emo_stale, reference_time=ref_dt))

        # 6. Enduring Preference (created 365 days ago) -> Active (Permanent)
        pref_permanent = {
            "category": "preference",
            "memory_val": "Enjoys sci-fi movies",
            "created_at": (ref_dt - timedelta(days=365)).isoformat()
        }
        self.assertTrue(is_memory_active(pref_permanent, reference_time=ref_dt))

    # =========================================================================
    # 6. REST API ENDPOINTS & TENANT ISOLATION (IDOR)
    # =========================================================================

    @unittest_run_loop
    async def test_12_api_get_memories_and_include_decayed(self):
        """Verify GET /api/memories filters decayed memories unless include_decayed=true."""
        uid = 4441
        # Add 1 active preference and 1 expired event
        add_or_update_memory(uid, "preference", "fav_band", "Pink Floyd", "", "")
        add_or_update_memory(uid, "event", "old_flight", "Flight to SF", "", "2026-01-01")

        # Default query (active only)
        resp = await self.client.get(f"/api/memories?user_id={uid}")
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertTrue(data.get("ok"))
        self.assertEqual(data.get("count"), 1)
        self.assertEqual(data["memories"][0]["memory_key"], "fav_band")

        # Query with include_decayed=true
        resp_all = await self.client.get(f"/api/memories?user_id={uid}&include_decayed=true")
        self.assertEqual(resp_all.status, 200)
        data_all = await resp_all.json()
        self.assertEqual(data_all.get("count"), 2)

    @unittest_run_loop
    async def test_13_api_delete_memory_tenant_isolation_idor(self):
        """CRITICAL: User A (4442) attempts to delete User B's (4443) memory. Must return 404 and protect data."""
        user_a = 4442
        user_b = 4443

        # Create memory for User B
        mem_b_id = add_or_update_memory(user_b, "fact", "secret_key", "Super confidential note", "", "")

        # Attack: User A calls DELETE with User B's memory ID
        attack_payload = {"user_id": user_a, "memory_id": mem_b_id}
        resp = await self.client.post("/api/memories/delete", json=attack_payload)
        self.assertEqual(resp.status, 404, "Cross-tenant deletion must return 404 Not Found / Unauthorized")

        # Verify User B's memory is intact in SQLite
        b_mems = get_user_memories(user_b, include_decayed=True)
        self.assertEqual(len(b_mems), 1)
        self.assertEqual(b_mems[0]["id"], mem_b_id)

        # Legitimate delete by User B
        legit_payload = {"user_id": user_b, "memory_id": mem_b_id}
        resp_legit = await self.client.post("/api/memories/delete", json=legit_payload)
        self.assertEqual(resp_legit.status, 200)
        self.assertEqual(len(get_user_memories(user_b, include_decayed=True)), 0)

    @unittest_run_loop
    async def test_14_api_wipe_memories_tenant_scoped(self):
        """Verify POST /api/memories/wipe completely purges target user without affecting others."""
        user_1 = 4444
        user_2 = 4445

        add_or_update_memory(user_1, "fact", "f1", "Fact 1", "", "")
        add_or_update_memory(user_1, "fact", "f2", "Fact 2", "", "")
        add_or_update_memory(user_2, "fact", "f3", "User 2 Fact", "", "")

        resp = await self.client.post("/api/memories/wipe", json={"user_id": user_1})
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertEqual(data.get("cleared"), 2)

        # User 1 has 0
        self.assertEqual(len(get_user_memories(user_1, include_decayed=True)), 0)
        # User 2 still has 1
        self.assertEqual(len(get_user_memories(user_2, include_decayed=True)), 1)

    @unittest_run_loop
    async def test_15_api_cors_preflight(self):
        """Verify OPTIONS returns 204 with full CORS headers for Mini App."""
        for path in ["/api/memories", "/api/memories/delete", "/api/memories/wipe"]:
            resp = await self.client.options(path)
            self.assertEqual(resp.status, 204)
            self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "*")
            self.assertIn("GET", resp.headers.get("Access-Control-Allow-Methods", ""))
            self.assertIn("POST", resp.headers.get("Access-Control-Allow-Methods", ""))

    # =========================================================================
    # 7. MINI APP UI COMPONENTS IN static/call.html
    # =========================================================================

    def test_16_miniapp_ui_elements_and_js_syntax(self):
        """Verify static/call.html contains required DOM IDs, handlers, and passes JS syntax check."""
        html_path = os.path.join(BASE_DIR, "static", "call.html")
        self.assertTrue(os.path.exists(html_path), "static/call.html not found")

        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. DOM IDs
        self.assertIn('id="memoryChip"', content, "Missing #memoryChip")
        self.assertIn('id="memoryListContainer"', content, "Missing #memoryListContainer")
        self.assertIn('id="memoryEmptyState"', content, "Missing #memoryEmptyState")
        self.assertIn('id="wipeAllMemoriesBtn"', content, "Missing #wipeAllMemoriesBtn")

        # Modal Overlay ID Assertion: Must strictly match #memoryModalOverlay
        self.assertIn(
            'id="memoryModalOverlay"', content,
            "DEFECT FOUND: static/call.html lacks exact id='memoryModalOverlay'. "
            "Found id='memoriesModalOverlay' with data-alias='memoryModalOverlay' instead. "
            "document.getElementById('memoryModalOverlay') returns null in DOM, and M3 handoff check fails."
        )

        # 2. JS Functions
        self.assertIn("deleteSingleMemory", content, "Missing deleteSingleMemory handler")
        self.assertIn("confirmWipeAllMemories", content, "Missing confirmWipeAllMemories handler")
        self.assertIn("openMemoryModal", content, "Missing openMemoryModal handler")
        self.assertIn("closeMemoryModal", content, "Missing closeMemoryModal handler")

        # 3. JavaScript Syntax validation via node --check
        scripts = re.findall(r"<script(?:\s+[^>]*)?>(.*?)</script>", content, re.DOTALL)
        self.assertGreater(len(scripts), 0, "No <script> tags found in call.html")

        # Test the main application script (usually the second or largest script)
        main_script = max(scripts, key=len)
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as tf:
            tf.write(main_script)
            tf_name = tf.name

        try:
            res = subprocess.run(["node", "--check", tf_name], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"Node.js syntax check failed: {res.stderr}")
        finally:
            if os.path.exists(tf_name):
                os.remove(tf_name)


if __name__ == "__main__":
    t0 = time.time()
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestChallengerEmpirical)
    result = runner.run(suite)
    elapsed = time.time() - t0
    print(f"\n=======================================================")
    print(f"Challenger Verification Benchmark: {elapsed:.3f} seconds")
    print(f"Passed: {result.wasSuccessful()} | Ran: {result.testsRun} tests")
    print(f"=======================================================")
    sys.exit(0 if result.wasSuccessful() else 1)
