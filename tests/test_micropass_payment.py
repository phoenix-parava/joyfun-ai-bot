import os
import unittest
from datetime import datetime, timezone, timedelta
import urllib.parse

# Set offline test environment
os.environ["OFFLINE_TEST"] = "1"

from database import (
    init_db,
    get_connection,
    record_utr_submission,
    approve_payment_request,
    reject_payment_request,
    grant_vip_subscription,
    is_user_vip,
    reset_user_quota,
    get_payment_request
)
from config import VIP_TIERS, UPI_ID

class TestMicroPassPayment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        # Clean test tables
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM payment_requests WHERE user_id >= 9900000")
            cursor.execute("DELETE FROM subscriptions WHERE user_id >= 9900000")
            cursor.execute("DELETE FROM users WHERE user_id >= 9900000")
            cursor.execute("DELETE FROM daily_usage WHERE user_id >= 9900000")
            conn.commit()

    def test_01_tier_configuration_integrity(self):
        """Verify day, weekend, and monthly tiers have valid prices, days, and descriptions."""
        self.assertIn("day", VIP_TIERS)
        self.assertIn("weekend", VIP_TIERS)
        self.assertIn("monthly", VIP_TIERS)
        
        self.assertEqual(VIP_TIERS["day"]["price_inr"], 19)
        self.assertEqual(VIP_TIERS["day"]["days"], 1)
        self.assertEqual(VIP_TIERS["day"]["stars"], 25)

        self.assertEqual(VIP_TIERS["weekend"]["price_inr"], 29)
        self.assertEqual(VIP_TIERS["weekend"]["days"], 2)
        self.assertEqual(VIP_TIERS["weekend"]["stars"], 40)

        self.assertEqual(VIP_TIERS["monthly"]["price_inr"], 149)
        self.assertEqual(VIP_TIERS["monthly"]["days"], 30)

    def test_02_day_pass_utr_submission_and_approval(self):
        """Verify submitting and approving a ₹19 Day Pass grants 1 day VIP."""
        user_id = 9900001
        utr = "DAYPASS123456"
        
        success, msg, req_id = record_utr_submission(user_id, utr, amount=19.0, plan_type="day")
        self.assertTrue(success)
        self.assertGreater(req_id, 0)
        
        req = get_payment_request(req_id)
        self.assertEqual(req["plan_type"], "day")
        self.assertEqual(req["amount"], 19.0)
        self.assertEqual(req["status"], "pending")
        
        # Approve payment
        res = approve_payment_request(req_id)
        self.assertIsNotNone(res)
        self.assertEqual(res["plan_type"], "day")
        self.assertEqual(res["days"], 1)
        
        # Verify user is VIP
        is_vip, expiry, days_left = is_user_vip(user_id)
        self.assertTrue(is_vip)
        self.assertEqual(days_left, 1)

    def test_03_weekend_pass_utr_submission_and_approval(self):
        """Verify submitting and approving a ₹29 Weekend Pass grants 2 days VIP."""
        user_id = 9900002
        utr = "WKNDPASS654321"
        
        success, msg, req_id = record_utr_submission(user_id, utr, amount=29.0, plan_type="weekend")
        self.assertTrue(success)
        
        res = approve_payment_request(req_id)
        self.assertIsNotNone(res)
        self.assertEqual(res["plan_type"], "weekend")
        self.assertEqual(res["days"], 2)
        
        is_vip, expiry, days_left = is_user_vip(user_id)
        self.assertTrue(is_vip)
        self.assertEqual(days_left, 2)

    def test_04_duplicate_utr_rejection(self):
        """Verify duplicate UTRs cannot be submitted across users or tiers."""
        user1 = 9900003
        user2 = 9900004
        utr = "SHAREDUTR99999"
        
        ok1, _, _ = record_utr_submission(user1, utr, amount=19.0, plan_type="day")
        self.assertTrue(ok1)
        
        ok2, msg2, _ = record_utr_submission(user2, utr, amount=29.0, plan_type="weekend")
        self.assertFalse(ok2)
        self.assertIn("already", msg2.lower())

    def test_05_time_stacking_preserves_unexpired_vip(self):
        """Verify purchasing a 24h pass stacks onto existing VIP expiry."""
        user_id = 9900005
        # Grant initial 5 days
        grant_vip_subscription(user_id, days=5, amount=0.0)
        _, _, initial_days = is_user_vip(user_id)
        self.assertEqual(initial_days, 5)
        
        # Stack 2 days weekend pass
        grant_vip_subscription(user_id, days=2, amount=29.0)
        _, _, stacked_days = is_user_vip(user_id)
        self.assertGreaterEqual(stacked_days, 7)

    def test_06_dynamic_qr_url_generation(self):
        """Verify UPI URI encoding and QRServer URL formatting."""
        user_id = 9900006
        tier = "day"
        price = VIP_TIERS[tier]["price_inr"]
        note = f"PASS_{tier.upper()}_{user_id}"
        
        raw_uri = f"upi://pay?pa={UPI_ID}&pn=JoyAI&am={price}&cu=INR&tn={note}"
        encoded_uri = urllib.parse.quote(raw_uri)
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=350x350&data={encoded_uri}"
        
        self.assertIn("upi%3A//pay", qr_url)
        self.assertIn(f"am%3D{price}", qr_url)
        self.assertIn(f"tn%3D{note}", qr_url)

if __name__ == "__main__":
    unittest.main()
