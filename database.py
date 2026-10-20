"""
Joy Bot - SQLite Database Storage & Usage Tracker
"""

import sqlite3
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from config import DB_PATH, DAILY_FREE_VOICE_LIMIT, DAILY_FREE_TEXT_LIMIT, OWNER_ID

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes tables for users, daily usage, conversation context, and VIP subscriptions."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                mode TEXT DEFAULT 'companion',
                voice TEXT DEFAULT 'female',
                is_vip INTEGER DEFAULT 0,
                vip_expiry TEXT,
                created_at TEXT
            )
        """)
        
        # Daily usage table (tracks voice & text counts per day)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_usage (
                user_id INTEGER,
                usage_date TEXT,
                voice_count INTEGER DEFAULT 0,
                text_count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, usage_date)
            )
        """)
        
        # Conversation history table (keeps multi-turn context)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                role TEXT,
                content TEXT,
                created_at TEXT
            )
        """)

        # Subscriptions table (tracks paid plans, UPI ref, and expiry timestamps)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                plan_name TEXT DEFAULT 'Joy VIP Pass',
                amount_inr REAL DEFAULT 149.0,
                payment_method TEXT DEFAULT 'upi',
                reference_id TEXT,
                started_at TEXT,
                expires_at TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        # Migrations for users table (onboarding, imported memory, gender, active_contact)
        cursor.execute("PRAGMA table_info(users)")
        existing_cols = [c["name"] for c in cursor.fetchall()]
        if "onboarding_status" not in existing_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN onboarding_status TEXT DEFAULT 'completed'")
        if "old_ai_name" not in existing_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN old_ai_name TEXT DEFAULT ''")
        if "imported_memory" not in existing_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN imported_memory TEXT DEFAULT ''")
        if "gender" not in existing_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN gender TEXT DEFAULT 'male'")
        if "active_contact" not in existing_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN active_contact TEXT DEFAULT 'lover'")
        
        conn.commit()

def get_or_create_user(user_id: int, username: str = "", first_name: str = "") -> dict:
    """Retrieves user profile or registers new user."""
    today = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        if row is None:
            # Owner is automatically VIP and completed
            is_vip = 1 if user_id == OWNER_ID else 0
            initial_status = "completed" if user_id == OWNER_ID else "new"
            cursor.execute("""
                INSERT INTO users (user_id, username, first_name, mode, voice, is_vip, created_at, onboarding_status, gender, active_contact)
                VALUES (?, ?, ?, 'companion', 'female', ?, ?, ?, 'male', 'lover')
            """, (user_id, username, first_name, is_vip, today, initial_status))
            conn.commit()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
        
        return dict(row)

def set_user_onboarding_status(user_id: int, status: str):
    """Updates the onboarding status of a user ('new', 'waiting_memory', 'completed')."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET onboarding_status = ? WHERE user_id = ?", (status, user_id))
        conn.commit()

def save_imported_memory(user_id: int, old_ai_name: str, memory_text: str):
    """Saves the imported past memory from the user's previous AI companion."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users 
            SET old_ai_name = ?, imported_memory = ?, onboarding_status = 'completed'
            WHERE user_id = ?
        """, (old_ai_name, memory_text, user_id))
        conn.commit()

def get_user_imported_memory(user_id: int) -> Tuple[str, str]:
    """Returns (old_ai_name, imported_memory) for a user."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT old_ai_name, imported_memory FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return (row["old_ai_name"] or "", row["imported_memory"] or "")
        return ("", "")

def update_user_preference(user_id: int, key: str, value: str):
    """Updates mode, voice, gender ('male'/'female'), or active_contact."""
    if key not in ("mode", "voice", "gender", "active_contact"):
        return
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE users SET {key} = ? WHERE user_id = ?", (value, user_id))
        conn.commit()

def set_user_gender(user_id: int, gender: str):
    """Sets user gender ('male' or 'female')."""
    clean_gender = "female" if str(gender).lower() == "female" else "male"
    update_user_preference(user_id, "gender", clean_gender)

def set_user_active_contact(user_id: int, contact_id: str):
    """Sets the active contact for the user."""
    update_user_preference(user_id, "active_contact", contact_id)

def get_user_contact_settings(user_id: int) -> Tuple[str, str]:
    """Returns (gender, active_contact) for a user."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT gender, active_contact FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            g = row["gender"] or "male"
            c = row["active_contact"] or "lover"
            return (g, c)
        return ("male", "lover")

def check_and_increment_usage(user_id: int, msg_type: str = "voice") -> Tuple[bool, int, int]:
    """
    Checks if user is within daily free limits and increments count.
    Returns: (is_allowed: bool, current_used: int, limit: int)
    """
    if user_id == OWNER_ID:
        return True, 0, 999999
        
    today = datetime.now().strftime("%Y-%m-%d")
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Check if user is VIP with auto-expiration check
        vip_active, _, _ = is_user_vip(user_id)
        if vip_active:
            return True, 0, 999999
            
        # Get today's usage
        cursor.execute(
            "SELECT voice_count, text_count FROM daily_usage WHERE user_id = ? AND usage_date = ?",
            (user_id, today)
        )
        row = cursor.fetchone()
        
        voice_count = row["voice_count"] if row else 0
        text_count = row["text_count"] if row else 0
        
        limit = DAILY_FREE_VOICE_LIMIT if msg_type == "voice" else DAILY_FREE_TEXT_LIMIT
        current = voice_count if msg_type == "voice" else text_count
        
        if current >= limit:
            return False, current, limit
            
        # Increment usage
        if msg_type == "voice":
            cursor.execute("""
                INSERT INTO daily_usage (user_id, usage_date, voice_count, text_count)
                VALUES (?, ?, 1, 0)
                ON CONFLICT(user_id, usage_date) DO UPDATE SET voice_count = voice_count + 1
            """, (user_id, today))
        else:
            cursor.execute("""
                INSERT INTO daily_usage (user_id, usage_date, voice_count, text_count)
                VALUES (?, ?, 0, 1)
                ON CONFLICT(user_id, usage_date) DO UPDATE SET text_count = text_count + 1
            """, (user_id, today))
            
        conn.commit()
        return True, current + 1, limit

def add_conversation_turn(user_id: int, role: str, content: str):
    """Saves a conversation turn to persistent memory."""
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversations (user_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (user_id, role, content, now)
        )
        # Keep last 10 messages only to preserve lean storage
        cursor.execute("""
            DELETE FROM conversations WHERE id IN (
                SELECT id FROM conversations WHERE user_id = ? ORDER BY id DESC LIMIT -1 OFFSET 10
            )
        """, (user_id,))
        conn.commit()

def get_recent_history(user_id: int, limit: int = 6) -> List[Dict[str, str]]:
    """Fetches recent conversation turns for context injection."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content FROM conversations WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit)
        )
        rows = cursor.fetchall()
        # Return in chronological order
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

def set_vip_status(user_id: int, status: int = 1):
    """Grants or revokes VIP status for a user."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_vip = ? WHERE user_id = ?", (status, user_id))
        conn.commit()

def recharge_user_usage(user_id: int, bonus_voice: int = 5, bonus_text: int = 20) -> Tuple[int, int]:
    """
    Grants bonus voice notes and text messages by decrementing today's usage count.
    Enables free recharge via watching ads/sponsors.
    Returns: (new_voice_count, new_text_count)
    """
    today = datetime.now().strftime("%Y-%m-%d")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT voice_count, text_count FROM daily_usage WHERE user_id = ? AND usage_date = ?",
            (user_id, today)
        )
        row = cursor.fetchone()
        if row:
            new_voice = max(0, row["voice_count"] - bonus_voice)
            new_text = max(0, row["text_count"] - bonus_text)
            cursor.execute(
                "UPDATE daily_usage SET voice_count = ?, text_count = ? WHERE user_id = ? AND usage_date = ?",
                (new_voice, new_text, user_id, today)
            )
        else:
            new_voice, new_text = 0, 0
        conn.commit()
        return new_voice, new_text

def is_user_vip(user_id: int) -> Tuple[bool, Optional[str], int]:
    """
    Checks if a user has an active VIP subscription and handles auto-expiration.
    Returns: (is_vip: bool, expiry_formatted: Optional[str], days_left: int)
    """
    if user_id == OWNER_ID:
        return True, "Lifetime (Owner)", 99999

    now = datetime.now(timezone.utc)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT is_vip, vip_expiry FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if not row or not row["is_vip"]:
            return False, None, 0

        expiry_iso = row["vip_expiry"]
        if not expiry_iso:
            return True, "Lifetime", 99999

        try:
            expiry_dt = datetime.fromisoformat(expiry_iso)
            if now > expiry_dt:
                # Subscription expired! Automatically revoke VIP
                cursor.execute("UPDATE users SET is_vip = 0, vip_expiry = NULL WHERE user_id = ?", (user_id,))
                cursor.execute("UPDATE subscriptions SET is_active = 0 WHERE user_id = ? AND is_active = 1", (user_id,))
                conn.commit()
                return False, None, 0

            seconds_left = (expiry_dt - now).total_seconds()
            days_left = max(0, int(math.ceil(seconds_left / 86400.0)))
            expiry_formatted = expiry_dt.strftime("%b %d, %Y")
            return True, expiry_formatted, days_left
        except Exception:
            return True, "Active", 30

def grant_vip_subscription(user_id: int, days: int = 30, amount: float = 149.0, method: str = "upi", ref: str = "") -> dict:
    """
    Activates or extends a user's VIP subscription and logs the transaction.
    Ensures user record exists even if they haven't sent a message yet.
    """
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(days=days)
    started_at = now.isoformat()
    expires_at = expiry.isoformat()

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, username, first_name, is_vip, vip_expiry, created_at)
            VALUES (?, '', 'Friend', 1, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET is_vip = 1, vip_expiry = ?
        """, (user_id, expires_at, started_at, expires_at))
        
        cursor.execute("""
            INSERT INTO subscriptions (user_id, plan_name, amount_inr, payment_method, reference_id, started_at, expires_at, is_active)
            VALUES (?, 'Joy VIP Pass', ?, ?, ?, ?, ?, 1)
        """, (user_id, amount, method, ref, started_at, expires_at))
        conn.commit()

    return {
        "user_id": user_id,
        "days": days,
        "amount": amount,
        "method": method,
        "ref": ref,
        "expires_at": expiry.strftime("%b %d, %Y")
    }

def revoke_vip_subscription(user_id: int) -> bool:
    """Revokes VIP subscription for a user."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_vip = 0, vip_expiry = NULL WHERE user_id = ?", (user_id,))
        cursor.execute("UPDATE subscriptions SET is_active = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
        return True

def get_all_subscribers() -> List[dict]:
    """Retrieves all active VIP subscribers with details."""
    now = datetime.now(timezone.utc)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.user_id, u.username, u.first_name, u.is_vip, u.vip_expiry,
                   MAX(s.amount_inr) as amount_inr, s.payment_method, s.started_at
            FROM users u
            LEFT JOIN subscriptions s ON u.user_id = s.user_id AND s.is_active = 1
            WHERE u.is_vip = 1
            GROUP BY u.user_id
            ORDER BY u.user_id ASC
        """)
        rows = cursor.fetchall()
        subscribers = []
        for r in rows:
            uid = r["user_id"]
            if uid == OWNER_ID:
                subscribers.append({
                    "user_id": uid,
                    "username": r["username"] or "phoenix_parava_0",
                    "first_name": r["first_name"] or "Anish",
                    "status": "Owner (Lifetime VIP)",
                    "days_left": 99999,
                    "expires_at": "Lifetime"
                })
                continue

            expiry_str = r["vip_expiry"]
            days_left = 30
            formatted_expiry = "Active"
            if expiry_str:
                try:
                    exp_dt = datetime.fromisoformat(expiry_str)
                    seconds_left = (exp_dt - now).total_seconds()
                    days_left = max(0, int(math.ceil(seconds_left / 86400.0)))
                    formatted_expiry = exp_dt.strftime("%b %d, %Y")
                except Exception:
                    pass

            subscribers.append({
                "user_id": uid,
                "username": r["username"] or "No username",
                "first_name": r["first_name"] or "Friend",
                "status": f"Active ({days_left}d left)",
                "days_left": days_left,
                "expires_at": formatted_expiry,
                "amount": r["amount_inr"] or 149.0
            })
        return subscribers
