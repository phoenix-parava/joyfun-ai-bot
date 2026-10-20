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
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes tables for users, daily usage, conversation context, and VIP subscriptions."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Enable high-concurrency WAL mode and zero-lock busy timeout for 24/7 reliability
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=15000")
        
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
        
        # Migrations for users table (onboarding, imported memory, gender, active_contact, language)
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
        if "language" not in existing_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'auto'")
        if "allow_data_sharing" not in existing_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN allow_data_sharing INTEGER DEFAULT 0")
        if "custom_ai_name" not in existing_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN custom_ai_name TEXT DEFAULT ''")
        if "cloud_backup_enabled" not in existing_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN cloud_backup_enabled INTEGER DEFAULT 1")
        if "google_email" not in existing_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN google_email TEXT DEFAULT ''")
        if "google_refresh_token" not in existing_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN google_refresh_token TEXT DEFAULT ''")
        if "google_access_token" not in existing_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN google_access_token TEXT DEFAULT ''")
        if "google_name" not in existing_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN google_name TEXT DEFAULT ''")

        # Table for anonymized dev training samples (ONLY saved if user explicitly opts-in)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dev_shared_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                category TEXT,
                snippet TEXT,
                created_at TEXT
            )
        """)

        # Table for user feedback, feature requests & ideas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                feedback_type TEXT DEFAULT 'general',
                message TEXT,
                created_at TEXT
            )
        """)
        
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
                INSERT INTO users (user_id, username, first_name, mode, voice, is_vip, created_at, onboarding_status, gender, active_contact, language)
                VALUES (?, ?, ?, 'companion', 'female', ?, ?, ?, 'male', 'lover', 'auto')
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
    """Updates mode, voice, gender ('male'/'female'), active_contact, or language."""
    if key not in ("mode", "voice", "gender", "active_contact", "language"):
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

def set_user_language(user_id: int, language: str):
    """Sets the preferred language ('auto', 'tanglish', 'hinglish', 'english')."""
    clean_lang = str(language).lower().strip()
    if clean_lang not in ("auto", "tanglish", "hinglish", "english"):
        clean_lang = "auto"
    update_user_preference(user_id, "language", clean_lang)

def get_user_language(user_id: int) -> str:
    """Returns user's language setting ('auto', 'tanglish', 'hinglish', 'english')."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row and row["language"]:
            return row["language"]
        return "auto"

def set_user_data_sharing(user_id: int, allow: bool):
    """Sets whether the user opts-in to share anonymized conversation snippets for development."""
    val = 1 if allow else 0
    get_or_create_user(user_id)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET allow_data_sharing = ? WHERE user_id = ?", (val, user_id))
        conn.commit()

def get_user_data_sharing(user_id: int) -> bool:
    """Returns True if user has explicitly enabled data sharing for development (default False)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT allow_data_sharing FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row and row["allow_data_sharing"] is not None:
            return bool(row["allow_data_sharing"])
        return False

def save_dev_sample_if_allowed(user_id: int, category: str, snippet: str):
    """
    Saves an anonymized snippet for model evaluation ONLY if the user has explicitly opted in.
    Guarantees strict zero-telemetry and zero-storage when data sharing is disabled.
    """
    if not get_user_data_sharing(user_id) or not snippet:
        return
    now = datetime.now(timezone.utc).isoformat()
    # Strip any potential sensitive numbers or emails for extra safety
    clean_snippet = str(snippet)[:500].strip()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO dev_shared_samples (user_id, category, snippet, created_at) VALUES (?, ?, ?, ?)",
            (user_id, category, clean_snippet, now)
        )
        conn.commit()

def set_user_custom_ai_name(user_id: int, name: str):
    """Sets a personalized name for the user's AI companion (e.g. Aisha, Priya, Kabir, Sweetheart)."""
    clean_name = str(name).strip()[:40] if name else ""
    get_or_create_user(user_id)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET custom_ai_name = ? WHERE user_id = ?", (clean_name, user_id))
        conn.commit()

def get_user_custom_ai_name(user_id: int) -> str:
    """Returns the custom companion name for the user, or empty string if using default."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT custom_ai_name FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row and row["custom_ai_name"]:
            return row["custom_ai_name"].strip()
        return ""

def reset_user_custom_ai_name(user_id: int):
    """Resets the custom AI companion name back to the default contact name."""
    set_user_custom_ai_name(user_id, "")

def set_user_cloud_backup(user_id: int, enabled: bool):
    """Sets whether cloud backup is enabled for the user's memories (1 = Enabled, 0 = Incognito)."""
    val = 1 if enabled else 0
    get_or_create_user(user_id)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET cloud_backup_enabled = ? WHERE user_id = ?", (val, user_id))
        conn.commit()

def get_user_cloud_backup(user_id: int) -> bool:
    """Returns True if cloud backup is enabled for user memories (default True)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT cloud_backup_enabled FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row and row["cloud_backup_enabled"] is not None:
            return bool(row["cloud_backup_enabled"])
        return True

def set_user_google_email(user_id: int, email: str):
    """Saves user's connected Google account / Gmail address."""
    clean_email = str(email).strip().lower()[:100]
    get_or_create_user(user_id)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET google_email = ? WHERE user_id = ?", (clean_email, user_id))
        conn.commit()

def get_user_google_email(user_id: int) -> str:
    """Returns user's connected Google email or empty string if not linked."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT google_email FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row and row["google_email"]:
            return row["google_email"].strip()
        return ""

def set_user_google_oauth(user_id: int, email: str, name: str = "", refresh_token: str = "", access_token: str = ""):
    """Saves user's authenticated Google OAuth account details and tokens."""
    clean_email = str(email).strip().lower()[:100]
    get_or_create_user(user_id)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE users 
               SET google_email = ?, google_name = ?, google_refresh_token = ?, google_access_token = ? 
               WHERE user_id = ?""",
            (clean_email, name, refresh_token, access_token, user_id)
        )
        conn.commit()

def get_user_google_oauth(user_id: int) -> dict:
    """Returns dict with google_email, google_name, google_refresh_token, google_access_token."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT google_email, google_name, google_refresh_token, google_access_token FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return {
                "email": row["google_email"] or "",
                "name": row["google_name"] or "",
                "refresh_token": row["google_refresh_token"] or "",
                "access_token": row["google_access_token"] or ""
            }
        return {"email": "", "name": "", "refresh_token": "", "access_token": ""}

def save_user_feedback(user_id: int, username: str, message: str, feedback_type: str = "general") -> int:
    """Stores user feedback, bug report, or feature request in database."""
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO feedback (user_id, username, feedback_type, message, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, username, feedback_type, message.strip(), now)
        )
        conn.commit()
        return cursor.lastrowid

def get_recent_feedbacks(limit: int = 20) -> List[dict]:
    """Retrieves recent user feedback and suggestions for admin review."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, user_id, username, feedback_type, message, created_at FROM feedback ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]

def get_user_daily_usage(user_id: int) -> Tuple[int, int]:
    """Returns today's (voice_count, text_count) for the user."""
    today = datetime.now().strftime("%Y-%m-%d")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT voice_count, text_count FROM daily_usage WHERE user_id = ? AND usage_date = ?",
            (user_id, today)
        )
        row = cursor.fetchone()
        if row:
            return (row["voice_count"] or 0, row["text_count"] or 0)
        return (0, 0)

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

def set_user_daily_quota(user_id: int, voice_count: int, text_count: int):
    """Admin function: sets exact voice_count and text_count for today's daily_usage."""
    today = datetime.now().strftime("%Y-%m-%d")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO daily_usage (user_id, usage_date, voice_count, text_count)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, usage_date) DO UPDATE SET
                voice_count = excluded.voice_count,
                text_count = excluded.text_count
        """, (user_id, today, voice_count, text_count))
        conn.commit()

def exhaust_user_quota(user_id: int) -> Tuple[int, int]:
    """Exhausts daily quota so user hits the paywall / ad prompt immediately."""
    set_user_daily_quota(user_id, DAILY_FREE_VOICE_LIMIT, DAILY_FREE_TEXT_LIMIT)
    with get_connection() as conn:
        conn.cursor().execute("UPDATE users SET is_vip = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
    return (DAILY_FREE_VOICE_LIMIT, DAILY_FREE_TEXT_LIMIT)

def reset_user_quota(user_id: int) -> Tuple[int, int]:
    """Resets daily quota to 0 so user has full fresh access."""
    set_user_daily_quota(user_id, 0, 0)
    return (0, 0)

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
