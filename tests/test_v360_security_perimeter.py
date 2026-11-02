"""
Joy Bot v3.6.0 Master Security & Perimeter Test Harness
Empirically verifies:
1. Cryptographic HMAC-SHA256 initData generation, validation, expiration, and tampering rejection.
2. Zero-Trust perimeter authentication across REST endpoints (CWE-287 / CWE-306 / IDOR prevention).
3. WebSocket /ws/call handshake verification, session binding, and full-duplex spoken barge-in handling.
"""

import os
import sys
import time
import json
import unittest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

# Enforce test environment variables BEFORE module imports
TEST_TOKEN = "123456:TEST_BOT_TOKEN_FOR_PERIMETER_V360"
os.environ["OFFLINE_TEST"] = "1"
os.environ["ALLOW_TEST_USERS"] = "1"
os.environ["BOT_TOKEN"] = TEST_TOKEN
os.environ["TELEGRAM_BOT_TOKEN"] = TEST_TOKEN

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if "edge_tts" not in sys.modules:
    sys.modules["edge_tts"] = MagicMock()

import config
config.TELEGRAM_BOT_TOKEN = TEST_TOKEN

import database
from security import (
    verify_telegram_init_data,
    generate_telegram_init_data,
    extract_and_verify_telegram_auth
)
import app as joy_app


class TestV360SecurityPerimeter(AioHTTPTestCase):

    async def get_application(self):
        """Constructs test aiohttp application with protected endpoints."""
        app = web.Application()
        app.router.add_get("/api/user/quota", joy_app.get_user_quota_api)
        app.router.add_get("/api/user/privacy", joy_app.get_user_privacy_api)
        app.router.add_post("/api/user/privacy", joy_app.set_user_privacy_api)
        app.router.add_post("/api/user/preference", joy_app.handle_user_preference_api)
        app.router.add_get("/api/memories", joy_app.get_user_memories_api)
        app.router.add_post("/api/memories/delete", joy_app.delete_user_memory_api)
        app.router.add_post("/api/memories/wipe", joy_app.wipe_user_memories_api)
        app.router.add_post("/api/feedback", joy_app.handle_api_feedback)
        app.router.add_get("/ws/call", joy_app.websocket_call_handler)
        return app

    def setUp(self):
        super().setUp()
        database.init_db()
        self.user_alice = 9993601
        self.user_bob = 9993602
        self.test_token = TEST_TOKEN

        with database.get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE user_id IN (?, ?)", (self.user_alice, self.user_bob))
            c.execute("""
                INSERT INTO users (user_id, username, first_name, onboarding_status, is_beta_tester, is_vip)
                VALUES (?, 'alice_test', 'Alice', 'completed', 1, 0),
                       (? , 'bob_test', 'Bob', 'completed', 1, 0)
            """, (self.user_alice, self.user_bob))
            conn.commit()

    def tearDown(self):
        with database.get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE user_id IN (?, ?)", (self.user_alice, self.user_bob))
            c.execute("DELETE FROM user_memories WHERE user_id IN (?, ?)", (self.user_alice, self.user_bob))
            conn.commit()
        super().tearDown()

    def test_01_cryptographic_init_data_lifecycle_and_tampering(self):
        """Verify HMAC-SHA256 generation, validation, expired timestamp rejection, and tamper rejection."""
        # 1. Valid signature
        valid_init = generate_telegram_init_data(self.user_alice, bot_token=self.test_token)
        verified_uid = verify_telegram_init_data(valid_init, bot_token=self.test_token)
        self.assertEqual(verified_uid, self.user_alice)

        # 2. Tampered user_id in payload with original hash -> Rejection
        tampered_init = valid_init.replace(str(self.user_alice), str(self.user_bob))
        tampered_result = verify_telegram_init_data(tampered_init, bot_token=self.test_token)
        self.assertIsNone(tampered_result)

        # 3. Expired timestamp (>24h ago) -> Rejection
        expired_time = int(time.time()) - 100000
        expired_init = generate_telegram_init_data(self.user_alice, bot_token=self.test_token, auth_date=expired_time)
        expired_result = verify_telegram_init_data(expired_init, bot_token=self.test_token)
        self.assertIsNone(expired_result)

        # 4. Tampered hash value -> Rejection
        bogus_hash_init = valid_init[:-4] + "dead"
        bogus_result = verify_telegram_init_data(bogus_hash_init, bot_token=self.test_token)
        self.assertIsNone(bogus_result)

    def test_02_extract_and_verify_telegram_auth_multiple_channels(self):
        """Verify extract_and_verify_telegram_auth extracts from headers, query params, and body."""
        valid_alice = generate_telegram_init_data(self.user_alice, bot_token=self.test_token)

        # 1. Header X-Telegram-Init-Data
        req_mock = MagicMock()
        req_mock.headers = {"X-Telegram-Init-Data": valid_alice}
        req_mock.query = {}
        uid, err = extract_and_verify_telegram_auth(req_mock)
        self.assertEqual(uid, self.user_alice)
        self.assertIsNone(err)

        # 2. Header Authorization: tma <initData>
        req_mock.headers = {"Authorization": f"tma {valid_alice}"}
        req_mock.query = {}
        uid, err = extract_and_verify_telegram_auth(req_mock)
        self.assertEqual(uid, self.user_alice)

        # 3. Query param ?initData=...
        req_mock.headers = {}
        req_mock.query = {"initData": valid_alice}
        uid, err = extract_and_verify_telegram_auth(req_mock)
        self.assertEqual(uid, self.user_alice)

        # 4. Payload body {"initData": ...}
        req_mock.headers = {}
        req_mock.query = {}
        uid, err = extract_and_verify_telegram_auth(req_mock, payload_dict={"initData": valid_alice})
        self.assertEqual(uid, self.user_alice)

    @unittest_run_loop
    async def test_03_idor_attack_prevention_on_rest_endpoints(self):
        """Verify an attacker authenticated as Alice cannot query or modify Bob's privacy or memories."""
        auth_alice = generate_telegram_init_data(self.user_alice, bot_token=self.test_token)
        headers = {"X-Telegram-Init-Data": auth_alice, "Content-Type": "application/json"}

        # Attack 1: Alice requests Bob's quota -> 403 Forbidden
        resp1 = await self.client.get(f"/api/user/quota?user_id={self.user_bob}", headers=headers)
        self.assertEqual(resp1.status, 403)
        body1 = await resp1.json()
        self.assertIn("Forbidden", body1.get("error", ""))

        # Attack 2: Alice requests Bob's privacy -> 403 Forbidden
        resp2 = await self.client.get(f"/api/user/privacy?user_id={self.user_bob}", headers=headers)
        self.assertEqual(resp2.status, 403)

        # Attack 3: Alice attempts to wipe Bob's memories -> 403 Forbidden
        resp3 = await self.client.post("/api/memories/wipe", json={"user_id": self.user_bob}, headers=headers)
        self.assertEqual(resp3.status, 403)

        # Attack 4: Forged signature -> 401 Unauthorized
        corrupt_headers = {"X-Telegram-Init-Data": "bad_hash_data_12345", "Content-Type": "application/json"}
        resp4 = await self.client.get(f"/api/user/quota?user_id={self.user_alice}", headers=corrupt_headers)
        self.assertEqual(resp4.status, 401)

        # Attack 5: Alice attempts to submit feedback as Bob -> 403 Forbidden (IDOR blocked)
        resp5 = await self.client.post("/api/feedback", json={"user_id": self.user_bob, "category": "bug", "message": "Test bug"}, headers=headers)
        self.assertEqual(resp5.status, 403)

    @unittest_run_loop
    async def test_04_authorized_rest_endpoints_success(self):
        """Verify legitimate user with matching signed initData accesses their endpoints cleanly."""
        auth_alice = generate_telegram_init_data(self.user_alice, bot_token=self.test_token)
        headers = {"X-Telegram-Init-Data": auth_alice, "Content-Type": "application/json"}

        # 1. Quota
        resp = await self.client.get(f"/api/user/quota?user_id={self.user_alice}", headers=headers)
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertEqual(data.get("status"), "ok")

        # 2. Privacy GET
        resp_p = await self.client.get(f"/api/user/privacy?user_id={self.user_alice}", headers=headers)
        self.assertEqual(resp_p.status, 200)

        # 3. Privacy POST
        resp_set = await self.client.post(
            "/api/user/privacy",
            json={"user_id": self.user_alice, "allow_data_sharing": True},
            headers=headers
        )
        self.assertEqual(resp_set.status, 200)

        # 4. Memories GET
        resp_m = await self.client.get(f"/api/memories?user_id={self.user_alice}", headers=headers)
        self.assertEqual(resp_m.status, 200)

        # 5. Feedback POST
        resp_fb = await self.client.post(
            "/api/feedback",
            json={"user_id": self.user_alice, "category": "bug", "message": "Microphone volume low on Firefox"},
            headers=headers
        )
        self.assertEqual(resp_fb.status, 200)
        fb_data = await resp_fb.json()
        self.assertTrue(fb_data.get("ok"))

    @unittest_run_loop
    async def test_05_websocket_call_handler_authentication_and_barge_in(self):
        """Verify /ws/call enforces authentication and gracefully acknowledges spoken barge-in frames."""
        auth_alice = generate_telegram_init_data(self.user_alice, bot_token=self.test_token)

        # 1. Connect with valid initData in query string
        ws = await self.client.ws_connect(f"/ws/call?initData={auth_alice}")

        # Send call_started
        await ws.send_json({
            "type": "call_started",
            "initData": auth_alice,
            "user_id": self.user_alice
        })

        # Expect call_connected
        msg = await ws.receive_json()
        self.assertEqual(msg.get("type"), "call_connected")
        self.assertEqual(msg.get("status"), "listening")

        # 2. Send barge_in frame (spoken interruption)
        await ws.send_json({"type": "barge_in"})
        barge_ack = await ws.receive_json()
        self.assertEqual(barge_ack.get("type"), "interrupted_ack")
        self.assertEqual(barge_ack.get("status"), "listening")

        await ws.close()

    @unittest_run_loop
    async def test_06_websocket_call_rejects_unauthenticated_connection(self):
        """Verify /ws/call closes connection when signature is forged or invalid."""
        ws = await self.client.ws_connect("/ws/call")
        await ws.send_json({
            "type": "call_started",
            "initData": "query_id=fake&hash=invalid_signature_hash_0000",
            "user_id": self.user_bob
        })

        msg = await ws.receive_json()
        self.assertEqual(msg.get("type"), "error")
        self.assertIn("Unauthorized session", msg.get("message", ""))
        close_frame = await ws.receive()
        self.assertEqual(close_frame.type, web.WSMsgType.CLOSE)
        self.assertTrue(ws.closed)


if __name__ == "__main__":
    unittest.main()
