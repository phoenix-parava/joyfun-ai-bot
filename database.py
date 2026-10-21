"""
Joy Bot - SQLite Database Storage & Usage Tracker
"""

import sqlite3
import re
import math
import hashlib
import secrets
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
        if "password_hash" not in existing_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT DEFAULT ''")
        if "referred_by" not in existing_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER DEFAULT 0")

        # Table for viral referral tracking and reward distribution
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER UNIQUE,
                status TEXT DEFAULT 'pending',
                reward_granted INTEGER DEFAULT 0,
                created_at TEXT
            )
        """)

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

        # Table for system & cloud API usage metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_usage_metrics (
                metric_date TEXT PRIMARY KEY,
                gemini_calls INTEGER DEFAULT 0,
                tts_calls INTEGER DEFAULT 0,
                drive_calls INTEGER DEFAULT 0
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
            # First, check Notion Cloud to see if this user has existing cloud settings
            try:
                from memory_cloud_sync import restore_user_memory_from_notion
                restore_user_memory_from_notion(user_id)
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
            except Exception:
                pass

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
    Enforces quality filtering, defensive PII redaction, and strict storage caps (max 200 items).
    """
    if not get_user_data_sharing(user_id) or not snippet:
        return

    raw_text = str(snippet).strip()
    
    # 1. Quality Filter: Ignore short dry noise, single-word replies, or empty prompts
    if len(raw_text) < 15 or len(raw_text.split()) < 3:
        return
    lowered = raw_text.lower()
    if lowered in ["hi", "hello", "k", "ok", "okay", "hmm", "hn", "haan", "what", "bye", "gm", "gn"]:
        return

    # 2. Defensive PII Redaction (Phone, Email, Handles)
    clean_snippet = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[EMAIL]', raw_text[:500])
    clean_snippet = re.sub(r'\+?\d{10,13}', '[PHONE]', clean_snippet)
    clean_snippet = re.sub(r'@\w{3,32}', '@[USER]', clean_snippet)

    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO dev_shared_samples (user_id, category, snippet, created_at) VALUES (?, ?, ?, ?)",
            (user_id, category, clean_snippet, now)
        )
        # 3. Storage Guard: Cap database table to latest 200 samples max to prevent any bloat
        cursor.execute("""
            DELETE FROM dev_shared_samples WHERE id IN (
                SELECT id FROM dev_shared_samples ORDER BY id DESC LIMIT -1 OFFSET 200
            )
        """)
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

def hash_password(password: str, salt: str = "") -> str:
    """Hashes a password with salt using SHA-256."""
    if not salt:
        salt = secrets.token_hex(8)
    h = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"{salt}:{h}"

def verify_password(stored_hash: str, password: str) -> bool:
    """Verifies a plaintext password against a salt:hash string."""
    if not stored_hash or ":" not in stored_hash:
        return False
    salt, expected = stored_hash.split(":", 1)
    computed = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return secrets.compare_digest(computed, expected)

def register_user_email(user_id: int, email: str, password: str) -> Tuple[bool, str]:
    """Registers or links an email/password account for user."""
    clean_email = email.strip().lower()
    if not clean_email or "@" not in clean_email or "." not in clean_email:
        return False, "Please enter a valid email address."
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."
        
    pwd_hash = hash_password(password)
    get_or_create_user(user_id)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE google_email = ? AND user_id != ?", (clean_email, user_id))
        existing = cursor.fetchone()
        if existing:
            return False, "This email is already registered with another account."
        cursor.execute("UPDATE users SET google_email = ?, password_hash = ? WHERE user_id = ?", (clean_email, pwd_hash, user_id))
        conn.commit()
    return True, "Account created successfully!"

def authenticate_user_email(user_id: int, email: str, password: str) -> Tuple[bool, str]:
    """Authenticates email & password, linking to current user session."""
    clean_email = email.strip().lower()
    get_or_create_user(user_id)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, password_hash, custom_ai_name, imported_memory FROM users WHERE google_email = ?", (clean_email,))
        row = cursor.fetchone()
        if not row:
            return False, "No account found with this email. Please click Sign Up."
        if not row["password_hash"]:
            return False, "This account was created via Google. Please click Continue with Google."
        if not verify_password(row["password_hash"], password):
            return False, "Incorrect password. Please try again."
        
        # Link current user session to this account
        cursor.execute("UPDATE users SET google_email = ?, password_hash = ? WHERE user_id = ?", (clean_email, row["password_hash"], user_id))
        
        # Merge settings if logging in on a new device/session
        old_uid = row["user_id"]
        if old_uid != user_id:
            if row["custom_ai_name"]:
                cursor.execute("UPDATE users SET custom_ai_name = ? WHERE user_id = ? AND (custom_ai_name = '' OR custom_ai_name IS NULL)", (row["custom_ai_name"], user_id))
            if row["imported_memory"]:
                cursor.execute("UPDATE users SET imported_memory = ? WHERE user_id = ? AND (imported_memory = '' OR imported_memory IS NULL)", (row["imported_memory"], user_id))
                
        conn.commit()
    return True, "Login successful!"

def record_api_call(service: str = "gemini", count: int = 1):
    """Records an API call count for the specified service (gemini, tts, drive)."""
    today = datetime.now().strftime("%Y-%m-%d")
    col = "gemini_calls" if service == "gemini" else ("tts_calls" if service == "tts" else "drive_calls")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            INSERT INTO api_usage_metrics (metric_date, {col})
            VALUES (?, ?)
            ON CONFLICT(metric_date) DO UPDATE SET {col} = {col} + ?
        """, (today, count, count))
        conn.commit()

def get_today_api_metrics() -> dict:
    """Returns today's aggregate API usage metrics across all services."""
    today = datetime.now().strftime("%Y-%m-%d")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM api_usage_metrics WHERE metric_date = ?", (today,))
        row = cursor.fetchone()
        if row:
            res = dict(row)
        else:
            res = {"metric_date": today, "gemini_calls": 0, "tts_calls": 0, "drive_calls": 0}
            
        # Also query daily_usage to ensure no calls were missed
        cursor.execute("SELECT COALESCE(SUM(voice_count), 0), COALESCE(SUM(text_count), 0) FROM daily_usage WHERE usage_date = ?", (today,))
        du = cursor.fetchone()
        voice_cnt = du[0] if du else 0
        text_cnt = du[1] if du else 0
        
        # Max of recorded calls vs daily_usage
        res["gemini_calls"] = max(res["gemini_calls"], voice_cnt + text_cnt)
        res["tts_calls"] = max(res["tts_calls"], voice_cnt)
        res["today_voice"] = voice_cnt
        res["today_text"] = text_cnt
        
        # Total users and VIP counts
        cursor.execute("SELECT COUNT(*) FROM users")
        res["total_users"] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_vip = 1")
        res["vip_users"] = cursor.fetchone()[0]
        
        return res

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

def track_user_referral(referred_id: int, referrer_id: int) -> bool:
    """Records that referred_id was invited by referrer_id (if not self and not already referred)."""
    if referred_id == referrer_id or referrer_id <= 0:
        return False
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT referred_by FROM users WHERE user_id = ?", (referred_id,))
        row = cursor.fetchone()
        if row and row["referred_by"]:
            return False  # Already referred
        cursor.execute("UPDATE users SET referred_by = ? WHERE user_id = ?", (referrer_id, referred_id))
        now = datetime.now(timezone.utc).isoformat()
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO referrals (referrer_id, referred_id, status, reward_granted, created_at) VALUES (?, ?, 'pending', 0, ?)",
                (referrer_id, referred_id, now)
            )
            conn.commit()
            return True
        except Exception:
            return False

def complete_referral_reward(referred_id: int) -> Optional[dict]:
    """
    Called when a user completes onboarding.
    If they were referred, grants the referrer:
    - +10 Voice Notes & +20 Texts bonus, OR +3 Days VIP if milestone hit.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT referrer_id, reward_granted FROM referrals WHERE referred_id = ?", (referred_id,))
        row = cursor.fetchone()
        if not row or row["reward_granted"]:
            return None
        referrer_id = row["referrer_id"]
        cursor.execute("UPDATE referrals SET status = 'completed', reward_granted = 1 WHERE referred_id = ?", (referred_id,))
        conn.commit()
    
    stats = get_referral_stats(referrer_id)
    total_completed = stats["completed_count"]
    
    if total_completed > 0 and total_completed % 3 == 0:
        grant_vip_subscription(referrer_id, days=3, amount=0.0, method="referral", ref=f"ref_milestone_{total_completed}")
        reward_type = "vip_3days"
    else:
        recharge_user_usage(referrer_id, voice_bonus=10, text_bonus=20)
        reward_type = "quota_bonus"
        
    return {
        "referrer_id": referrer_id,
        "total_completed": total_completed,
        "reward_type": reward_type
    }

def get_referral_stats(user_id: int) -> dict:
    """Returns referral counts and reward info for a given user."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM referrals WHERE referrer_id = ?", (user_id,))
        total = cursor.fetchone()["total"]
        cursor.execute("SELECT COUNT(*) as completed FROM referrals WHERE referrer_id = ? AND reward_granted = 1", (user_id,))
        completed = cursor.fetchone()["completed"]
        return {"total_invited": total, "completed_count": completed}

