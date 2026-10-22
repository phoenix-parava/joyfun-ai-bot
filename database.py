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
from typing import List, Dict, Tuple, Optional, Any
from config import (
    DB_PATH,
    DAILY_FREE_VOICE_LIMIT,
    DAILY_FREE_TEXT_LIMIT,
    DAILY_FREE_AI_CALL_LIMIT,
    DAILY_FREE_REAL_CALL_LIMIT,
    DAILY_FREE_REAL_CHAT_LIMIT,
    OWNER_ID,
)

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    return conn

def generate_deterministic_unique_id(user_id: int) -> str:
    """
    Generates a permanent, collision-resistant 5-character Joy Unique ID
    deterministically from the user's Telegram ID.
    Even if the bot is reset or reinstalled, the Telegram ID always matches the exact same unique ID.
    Uses unambiguous uppercase characters (no 0/O, 1/I).
    """
    if not user_id:
        return "Joy-00000"
    h = hashlib.sha256(f"joy_permanent_unique_id_{user_id}".encode()).digest()
    alphabet = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    num = int.from_bytes(h[:4], "big")
    code = ""
    for _ in range(5):
        code += alphabet[num % len(alphabet)]
        num //= len(alphabet)
    return f"Joy-{code}"

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
        
        # Daily usage table (tracks voice, text, AI calls, real calls, and real chats per day)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_usage (
                user_id INTEGER,
                usage_date TEXT,
                voice_count INTEGER DEFAULT 0,
                text_count INTEGER DEFAULT 0,
                ai_call_count INTEGER DEFAULT 0,
                real_call_count INTEGER DEFAULT 0,
                real_chat_count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, usage_date)
            )
        """)
        cursor.execute("PRAGMA table_info(daily_usage)")
        existing_du_cols = [c["name"] for c in cursor.fetchall()]
        if "ai_call_count" not in existing_du_cols:
            cursor.execute("ALTER TABLE daily_usage ADD COLUMN ai_call_count INTEGER DEFAULT 0")
        if "real_call_count" not in existing_du_cols:
            cursor.execute("ALTER TABLE daily_usage ADD COLUMN real_call_count INTEGER DEFAULT 0")
        if "real_chat_count" not in existing_du_cols:
            cursor.execute("ALTER TABLE daily_usage ADD COLUMN real_chat_count INTEGER DEFAULT 0")
        
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
        if "streak_count" not in existing_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN streak_count INTEGER DEFAULT 0")
        if "last_streak_date" not in existing_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN last_streak_date TEXT DEFAULT ''")
        if "relationship_level" not in existing_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN relationship_level INTEGER DEFAULT 1")
        if "last_proactive_date" not in existing_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN last_proactive_date TEXT DEFAULT ''")
        if "last_proactive_type" not in existing_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN last_proactive_type TEXT DEFAULT ''")
        if "proactive_enabled" not in existing_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN proactive_enabled INTEGER DEFAULT 1")
        if "contributor_discount_locked" not in existing_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN contributor_discount_locked INTEGER DEFAULT 0")
        if "unique_id" not in existing_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN unique_id TEXT DEFAULT ''")
        if "country_code" not in existing_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN country_code TEXT DEFAULT ''")

        # Backfill and guarantee permanent unique_id and mask mapping for all users
        cursor.execute("SELECT user_id, unique_id FROM users")
        for u in cursor.fetchall():
            uid = u["user_id"]
            if not u["unique_id"]:
                det_id = generate_deterministic_unique_id(uid)
                cursor.execute("UPDATE users SET unique_id = ? WHERE user_id = ?", (det_id, uid))
                cursor.execute("""
                    INSERT INTO mask_mappings (mask_id, user_id, updated_at) VALUES (?, ?, ?)
                    ON CONFLICT(mask_id) DO UPDATE SET user_id = excluded.user_id
                """, (det_id, uid, datetime.now(timezone.utc).isoformat()))

        # Table for permanent mask to user ID mapping (for missed call alerts & reconnects)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mask_mappings (
                mask_id TEXT PRIMARY KEY,
                user_id INTEGER,
                updated_at TEXT
            )
        """)

        # Table for blocked peers in Anonymous Voice Match
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blocked_peers (
                user_id INTEGER,
                blocked_mask TEXT,
                created_at TEXT,
                PRIMARY KEY (user_id, blocked_mask)
            )
        """)

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

        # Table for tamper-proof UPI payment requests & UTR tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payment_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL DEFAULT 149.0,
                utr TEXT UNIQUE,
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                verified_at TEXT
            )
        """)

        # Table for community requested languages and dialects
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS language_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                requested_language TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Table for previous chatted and called mutual partners
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS match_connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                peer_user_id INTEGER,
                peer_mask TEXT,
                connection_type TEXT DEFAULT 'chat',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, peer_user_id) ON CONFLICT REPLACE
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
            unique_id = generate_deterministic_unique_id(user_id)
            cursor.execute("""
                INSERT INTO users (user_id, username, first_name, mode, voice, is_vip, created_at, onboarding_status, gender, active_contact, language, unique_id)
                VALUES (?, ?, ?, 'companion', 'female', ?, ?, ?, 'male', 'lover', 'auto', ?)
            """, (user_id, username, first_name, is_vip, today, initial_status, unique_id))
            cursor.execute("""
                INSERT INTO mask_mappings (mask_id, user_id, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(mask_id) DO UPDATE SET user_id = excluded.user_id
            """, (unique_id, user_id, today))
            conn.commit()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
        elif "unique_id" in row.keys() and not row["unique_id"]:
            unique_id = generate_deterministic_unique_id(user_id)
            cursor.execute("UPDATE users SET unique_id = ? WHERE user_id = ?", (unique_id, user_id))
            cursor.execute("""
                INSERT INTO mask_mappings (mask_id, user_id, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(mask_id) DO UPDATE SET user_id = excluded.user_id
            """, (unique_id, user_id, today))
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
    """Sets the preferred language ('auto', 'english', 'hinglish', 'tanglish', 'telugu', 'malayalam', 'kannada', 'bengali', 'marathi', 'spanish')."""
    clean_lang = str(language).lower().strip()
    valid_langs = ("auto", "english", "hinglish", "tanglish", "telugu", "malayalam", "kannada", "bengali", "marathi", "spanish")
    if clean_lang not in valid_langs:
        clean_lang = "auto"
    update_user_preference(user_id, "language", clean_lang)

def save_user_language_request(user_id: int, requested_language: str) -> bool:
    """Saves a requested language/dialect for future model training and support."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS language_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, requested_language TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
            )
            cursor.execute(
                "INSERT INTO language_requests (user_id, requested_language) VALUES (?, ?)",
                (user_id, requested_language.strip())
            )
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error saving language request for user {user_id}: {e}")
        return False

def record_match_connection(user_id: int, peer_user_id: int, peer_mask: str, conn_type: str = "chat"):
    """Records or updates a match connection between two users."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now(timezone.utc).isoformat()
            cursor.execute("""
                INSERT INTO match_connections (user_id, peer_user_id, peer_mask, connection_type, created_at, last_interaction)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, peer_user_id) DO UPDATE SET
                    peer_mask = excluded.peer_mask,
                    connection_type = excluded.connection_type,
                    last_interaction = excluded.last_interaction
            """, (user_id, peer_user_id, peer_mask, conn_type, now, now))
            conn.commit()
    except Exception as e:
        logger.error(f"Error recording match connection: {e}")

def get_user_match_connections(user_id: int, limit: int = 30) -> list:
    """Returns list of past match connections for a user."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT peer_user_id, peer_mask, connection_type, last_interaction
                FROM match_connections
                WHERE user_id = ?
                ORDER BY last_interaction DESC
                LIMIT ?
            """, (user_id, limit))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                results.append({
                    "peer_uid": r["peer_user_id"],
                    "mask": r["peer_mask"],
                    "type": r["connection_type"],
                    "lastSeen": r["last_interaction"][:16].replace("T", " ") if r["last_interaction"] else "Recently"
                })
            return results
    except Exception as e:
        logger.error(f"Error fetching match connections: {e}")
        return []

def get_user_language(user_id: int) -> str:
    """Returns user's language setting ('auto', 'tanglish', 'hinglish', 'english')."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row and row["language"]:
            return row["language"]
        return "auto"

# Standard ISO 3166-1 alpha-2 Country Directory with Flag Emojis
COUNTRIES = {
    "IN": {"name": "India", "flag": "🇮🇳", "code": "IN"},
    "US": {"name": "United States", "flag": "🇺🇸", "code": "US"},
    "GB": {"name": "United Kingdom", "flag": "🇬🇧", "code": "GB"},
    "CA": {"name": "Canada", "flag": "🇨🇦", "code": "CA"},
    "AU": {"name": "Australia", "flag": "🇦🇺", "code": "AU"},
    "AE": {"name": "United Arab Emirates", "flag": "🇦🇪", "code": "AE"},
    "SG": {"name": "Singapore", "flag": "🇸🇬", "code": "SG"},
    "MY": {"name": "Malaysia", "flag": "🇲🇾", "code": "MY"},
    "SA": {"name": "Saudi Arabia", "flag": "🇸🇦", "code": "SA"},
    "DE": {"name": "Germany", "flag": "🇩🇪", "code": "DE"},
    "FR": {"name": "France", "flag": "🇫🇷", "code": "FR"},
    "NP": {"name": "Nepal", "flag": "🇳🇵", "code": "NP"},
    "LK": {"name": "Sri Lanka", "flag": "🇱🇰", "code": "LK"},
    "BD": {"name": "Bangladesh", "flag": "🇧🇩", "code": "BD"},
    "PK": {"name": "Pakistan", "flag": "🇵🇰", "code": "PK"},
    "ZA": {"name": "South Africa", "flag": "🇿🇦", "code": "ZA"},
    "NZ": {"name": "New Zealand", "flag": "🇳🇿", "code": "NZ"},
    "OTHER": {"name": "Other / Global", "flag": "🌐", "code": "GLOBAL"},
}

def set_user_country(user_id: int, country_code: str) -> bool:
    """Saves user's ISO country code to database."""
    code = (country_code or "").strip().upper()
    if code not in COUNTRIES and code != "GLOBAL":
        code = "OTHER"
    get_or_create_user(user_id)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET country_code = ? WHERE user_id = ?", (code, user_id))
        conn.commit()
    return True

def get_user_country(user_id: int) -> str:
    """Returns user's ISO country code, or empty string if not set."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT country_code FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row and row["country_code"]:
            return row["country_code"]
    return ""

def get_country_display(country_code: str) -> dict:
    """Returns dictionary with name, flag, and formatted label for a country code."""
    code = (country_code or "").strip().upper()
    info = COUNTRIES.get(code)
    if info:
        return {
            "code": code,
            "name": info["name"],
            "flag": info["flag"],
            "display": f"{info['flag']} {info['name']} ({code})"
        }
    return {
        "code": "",
        "name": "Not Set",
        "flag": "🌍",
        "display": "⚪ Not Set (Select Country)"
    }

def is_contributor_discount_locked(user_id: int) -> bool:
    """
    Returns True if user currently has an active VIP subscription purchased with the 20% Contributor discount.
    Prevents gaming the system by unlocking 20% off and then turning off data sharing.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT is_vip, vip_expiry, contributor_discount_locked FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            return False
        is_vip = bool(row["is_vip"])
        locked = bool(row["contributor_discount_locked"]) if "contributor_discount_locked" in row.keys() else False
        if not is_vip or not locked:
            return False
        expiry_str = row["vip_expiry"]
        if not expiry_str:
            return False
        try:
            now = datetime.now(timezone.utc)
            expiry_dt = datetime.fromisoformat(expiry_str)
            if expiry_dt.tzinfo is None:
                expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
            if now > expiry_dt:
                cursor.execute("UPDATE users SET is_vip = 0, contributor_discount_locked = 0 WHERE user_id = ?", (user_id,))
                conn.commit()
                return False
            return True
        except Exception:
            return is_vip and locked

def set_user_data_sharing(user_id: int, allow: bool) -> tuple[bool, str]:
    """
    Sets whether the user opts-in to share anonymized conversation snippets for development.
    Returns (True, 'ok') if updated, or (False, 'contributor_locked') if user has an active discounted VIP pass.
    """
    if not allow and is_contributor_discount_locked(user_id):
        return False, "contributor_locked"
    val = 1 if allow else 0
    get_or_create_user(user_id)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET allow_data_sharing = ? WHERE user_id = ?", (val, user_id))
        conn.commit()
    return True, "ok"

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
    Supported msg_type values:
      - 'voice': AI Voice Notes
      - 'text': AI Text Messages
      - 'ai_call': AI Live Duplex Calls
      - 'real_call': Real People Anonymous Voice Match
      - 'real_chat': Real People Text Matches
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
            "SELECT voice_count, text_count, ai_call_count, real_call_count, real_chat_count FROM daily_usage WHERE user_id = ? AND usage_date = ?",
            (user_id, today)
        )
        row = cursor.fetchone()
        
        col_map = {
            "voice": ("voice_count", DAILY_FREE_VOICE_LIMIT),
            "text": ("text_count", DAILY_FREE_TEXT_LIMIT),
            "ai_call": ("ai_call_count", DAILY_FREE_AI_CALL_LIMIT),
            "real_call": ("real_call_count", DAILY_FREE_REAL_CALL_LIMIT),
            "real_chat": ("real_chat_count", DAILY_FREE_REAL_CHAT_LIMIT),
        }
        
        target_col, limit = col_map.get(msg_type, ("text_count", DAILY_FREE_TEXT_LIMIT))
        current = (row[target_col] or 0) if (row and target_col in row.keys()) else 0
        
        if current >= limit:
            return False, current, limit
            
        cursor.execute("""
            INSERT INTO daily_usage (user_id, usage_date, voice_count, text_count, ai_call_count, real_call_count, real_chat_count)
            VALUES (?, ?, 0, 0, 0, 0, 0)
            ON CONFLICT(user_id, usage_date) DO NOTHING
        """, (user_id, today))
        
        cursor.execute(f"""
            UPDATE daily_usage SET {target_col} = COALESCE({target_col}, 0) + 1
            WHERE user_id = ? AND usage_date = ?
        """, (user_id, today))
        
        conn.commit()
        return True, current + 1, limit

def increment_user_ai_call(user_id: int):
    """Increments today's AI live call count for user."""
    today = datetime.now().strftime("%Y-%m-%d")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO daily_usage (user_id, usage_date, voice_count, text_count, ai_call_count, real_call_count, real_chat_count)
            VALUES (?, ?, 0, 0, 1, 0, 0)
            ON CONFLICT(user_id, usage_date) DO UPDATE SET ai_call_count = COALESCE(ai_call_count, 0) + 1
        """, (user_id, today))
        conn.commit()

def increment_user_real_call(user_id: int):
    """Increments today's real voice match call count for user."""
    today = datetime.now().strftime("%Y-%m-%d")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO daily_usage (user_id, usage_date, voice_count, text_count, ai_call_count, real_call_count, real_chat_count)
            VALUES (?, ?, 0, 0, 0, 1, 0)
            ON CONFLICT(user_id, usage_date) DO UPDATE SET real_call_count = COALESCE(real_call_count, 0) + 1
        """, (user_id, today))
        conn.commit()

def increment_user_real_chat(user_id: int):
    """Increments today's real text chat count for user."""
    today = datetime.now().strftime("%Y-%m-%d")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO daily_usage (user_id, usage_date, voice_count, text_count, ai_call_count, real_call_count, real_chat_count)
            VALUES (?, ?, 0, 0, 0, 0, 1)
            ON CONFLICT(user_id, usage_date) DO UPDATE SET real_chat_count = COALESCE(real_chat_count, 0) + 1
        """, (user_id, today))
        conn.commit()

def get_user_full_quota_status(user_id: int) -> Dict[str, Any]:
    """
    Returns complete live quota and balance metrics across all 4 communication channels:
    1. AI Live Voice Calls
    2. Real People Voice Match
    3. Chat with Real People
    4. Chat with AI Companion (Texts & Voice Notes)
    """
    today = datetime.now().strftime("%Y-%m-%d")
    vip_active, expiry_formatted, days_left = is_user_vip(user_id)
    if user_id == OWNER_ID:
        vip_active = True
        expiry_formatted = "Lifetime Owner Access"
        days_left = 9999

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT voice_count, text_count, ai_call_count, real_call_count, real_chat_count FROM daily_usage WHERE user_id = ? AND usage_date = ?",
            (user_id, today)
        )
        row = cursor.fetchone()
        voice_cnt = (row["voice_count"] or 0) if row else 0
        text_cnt = (row["text_count"] or 0) if row else 0
        ai_call_cnt = (row["ai_call_count"] or 0) if (row and "ai_call_count" in row.keys()) else 0
        real_call_cnt = (row["real_call_count"] or 0) if (row and "real_call_count" in row.keys()) else 0
        real_chat_cnt = (row["real_chat_count"] or 0) if (row and "real_chat_count" in row.keys()) else 0

    # Calculate time until UTC midnight
    now_utc = datetime.now(timezone.utc)
    midnight_utc = (now_utc + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    diff_secs = max(0, int((midnight_utc - now_utc).total_seconds()))
    hours = diff_secs // 3600
    mins = (diff_secs % 3600) // 60
    resets_in = f"{hours}h {mins}m"

    return {
        "user_id": user_id,
        "unique_id": get_mask_by_user_id(user_id),
        "is_vip": vip_active,
        "vip_expiry": expiry_formatted,
        "days_left": days_left,
        "resets_in": resets_in,
        "channels": {
            "ai_call": {
                "title": "AI Live Voice Calls",
                "icon": "🎙️",
                "used": ai_call_cnt,
                "limit": DAILY_FREE_AI_CALL_LIMIT,
                "remaining": 999999 if vip_active else max(0, DAILY_FREE_AI_CALL_LIMIT - ai_call_cnt),
                "unit": "Call (5 min/call)",
                "unlimited": vip_active
            },
            "real_call": {
                "title": "Real People Voice Match",
                "icon": "🎭",
                "used": real_call_cnt,
                "limit": DAILY_FREE_REAL_CALL_LIMIT,
                "remaining": 999999 if vip_active else max(0, DAILY_FREE_REAL_CALL_LIMIT - real_call_cnt),
                "unit": "Voice Matches",
                "unlimited": vip_active
            },
            "real_chat": {
                "title": "Chat with Real People",
                "icon": "👥",
                "used": real_chat_cnt,
                "limit": DAILY_FREE_REAL_CHAT_LIMIT,
                "remaining": 999999 if vip_active else max(0, DAILY_FREE_REAL_CHAT_LIMIT - real_chat_cnt),
                "unit": "Conversations",
                "unlimited": vip_active
            },
            "ai_chat": {
                "title": "Chat with AI Companion",
                "icon": "💬",
                "text_used": text_cnt,
                "text_limit": DAILY_FREE_TEXT_LIMIT,
                "text_remaining": 999999 if vip_active else max(0, DAILY_FREE_TEXT_LIMIT - text_cnt),
                "voice_used": voice_cnt,
                "voice_limit": DAILY_FREE_VOICE_LIMIT,
                "voice_remaining": 999999 if vip_active else max(0, DAILY_FREE_VOICE_LIMIT - voice_cnt),
                "unit": "Texts & Notes",
                "unlimited": vip_active
            }
        }
    }

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

def recharge_user_usage(
    user_id: int,
    bonus_voice: int = 5,
    bonus_text: int = 20,
    bonus_ai_call: int = 1,
    bonus_real_call: int = 3,
    bonus_real_chat: int = 5
) -> Tuple[int, int]:
    """
    Grants bonus voice notes, text messages, AI calls, and real matches by decrementing today's usage count.
    Enables free recharge via watching ads/sponsors.
    Returns: (new_voice_count, new_text_count)
    """
    today = datetime.now().strftime("%Y-%m-%d")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT voice_count, text_count, ai_call_count, real_call_count, real_chat_count FROM daily_usage WHERE user_id = ? AND usage_date = ?",
            (user_id, today)
        )
        row = cursor.fetchone()
        if row:
            new_voice = max(0, (row["voice_count"] or 0) - bonus_voice)
            new_text = max(0, (row["text_count"] or 0) - bonus_text)
            new_ai_call = max(0, ((row["ai_call_count"] or 0) if "ai_call_count" in row.keys() else 0) - bonus_ai_call)
            new_real_call = max(0, ((row["real_call_count"] or 0) if "real_call_count" in row.keys() else 0) - bonus_real_call)
            new_real_chat = max(0, ((row["real_chat_count"] or 0) if "real_chat_count" in row.keys() else 0) - bonus_real_chat)
            cursor.execute(
                """UPDATE daily_usage SET
                    voice_count = ?,
                    text_count = ?,
                    ai_call_count = ?,
                    real_call_count = ?,
                    real_chat_count = ?
                WHERE user_id = ? AND usage_date = ?""",
                (new_voice, new_text, new_ai_call, new_real_call, new_real_chat, user_id, today)
            )
        else:
            new_voice, new_text = 0, 0
        conn.commit()
        return new_voice, new_text

def set_user_daily_quota(
    user_id: int,
    voice_count: int,
    text_count: int,
    ai_call_count: int = 0,
    real_call_count: int = 0,
    real_chat_count: int = 0
):
    """Admin function: sets exact usage counts across all channels for today's daily_usage."""
    today = datetime.now().strftime("%Y-%m-%d")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO daily_usage (user_id, usage_date, voice_count, text_count, ai_call_count, real_call_count, real_chat_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, usage_date) DO UPDATE SET
                voice_count = excluded.voice_count,
                text_count = excluded.text_count,
                ai_call_count = excluded.ai_call_count,
                real_call_count = excluded.real_call_count,
                real_chat_count = excluded.real_chat_count
        """, (user_id, today, voice_count, text_count, ai_call_count, real_call_count, real_chat_count))
        conn.commit()

def exhaust_user_quota(user_id: int) -> Tuple[int, int]:
    """Exhausts daily quota so user hits the paywall / ad prompt immediately."""
    set_user_daily_quota(
        user_id,
        DAILY_FREE_VOICE_LIMIT,
        DAILY_FREE_TEXT_LIMIT,
        DAILY_FREE_AI_CALL_LIMIT,
        DAILY_FREE_REAL_CALL_LIMIT,
        DAILY_FREE_REAL_CHAT_LIMIT
    )
    with get_connection() as conn:
        conn.cursor().execute("UPDATE users SET is_vip = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
    return (DAILY_FREE_VOICE_LIMIT, DAILY_FREE_TEXT_LIMIT)

def reset_user_quota(user_id: int) -> Tuple[int, int]:
    """Resets daily quota to 0 so user has full fresh access."""
    set_user_daily_quota(user_id, 0, 0, 0, 0, 0)
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

def grant_vip_subscription(user_id: int, days: int = 30, amount: float = 149.0, method: str = "upi", ref: str = "", is_contributor: bool = False) -> dict:
    """
    Activates or extends a user's VIP subscription and logs the transaction.
    Ensures user record exists even if they haven't sent a message yet.
    If purchased with contributor discount, locks data sharing to prevent gaming the system.
    """
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(days=days)
    started_at = now.isoformat()
    expires_at = expiry.isoformat()

    plan_title = "Joy VIP Pass (20% Contributor Discount)" if is_contributor else "Joy VIP Pass"
    lock_val = 1 if is_contributor else 0

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, username, first_name, is_vip, vip_expiry, contributor_discount_locked, allow_data_sharing, created_at)
            VALUES (?, '', 'Friend', 1, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET is_vip = 1, vip_expiry = ?,
                   contributor_discount_locked = CASE WHEN ? = 1 THEN 1 ELSE contributor_discount_locked END,
                   allow_data_sharing = CASE WHEN ? = 1 THEN 1 ELSE allow_data_sharing END
        """, (user_id, expires_at, lock_val, lock_val, started_at, expires_at, lock_val, lock_val))
        
        cursor.execute("""
            INSERT INTO subscriptions (user_id, plan_name, amount_inr, payment_method, reference_id, started_at, expires_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """, (user_id, plan_title, amount, method, ref, started_at, expires_at))
        conn.commit()

    return {
        "user_id": user_id,
        "days": days,
        "amount": amount,
        "method": method,
        "ref": ref,
        "is_contributor": is_contributor,
        "expires_at": expiry.strftime("%b %d, %Y")
    }

def revoke_vip_subscription(user_id: int) -> bool:
    """Revokes VIP subscription for a user."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_vip = 0, vip_expiry = NULL, contributor_discount_locked = 0 WHERE user_id = ?", (user_id,))
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

def record_utr_submission(user_id: int, utr: str, amount: float = 149.0) -> Tuple[bool, str, int]:
    """Records a user's UTR submission for ₹149 VIP payment. Guarantees uniqueness & prevents duplicate reuse."""
    clean_utr = utr.strip().upper()
    if len(clean_utr) < 8 or len(clean_utr) > 24:
        return False, "UTR must be a valid 8 to 22 character reference number.", 0
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, user_id, status FROM payment_requests WHERE utr = ?", (clean_utr,))
        existing = cursor.fetchone()
        if existing:
            if existing["status"] == "verified":
                return False, "This UTR has already been verified and activated!", existing["id"]
            return False, "This UTR has already been submitted and is currently being verified.", existing["id"]
        try:
            cursor.execute(
                "INSERT INTO payment_requests (user_id, amount, utr, status, created_at) VALUES (?, ?, ?, 'pending', ?)",
                (user_id, amount, clean_utr, now)
            )
            req_id = cursor.lastrowid
            conn.commit()
            return True, "Payment submitted successfully! Awaiting verification.", req_id
        except Exception as e:
            return False, f"Database error: {e}", 0

def get_payment_request(req_id: int) -> Optional[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM payment_requests WHERE id = ?", (req_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def approve_payment_request(req_id: int) -> Optional[dict]:
    """Approves a payment request, unlocks VIP for 30 days, and resets user quota to 0."""
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM payment_requests WHERE id = ?", (req_id,))
        req = cursor.fetchone()
        if not req or req["status"] == "verified":
            return None
        user_id = req["user_id"]
        amount = req["amount"]
        utr = req["utr"]
        cursor.execute("UPDATE payment_requests SET status = 'verified', verified_at = ? WHERE id = ?", (now, req_id))
        conn.commit()
    
    # Grant VIP and reset daily quota to 0
    vip_info = grant_vip_subscription(user_id, days=30, amount=amount, method="upi", ref=f"UTR_{utr}")
    reset_user_quota(user_id)
    return {"user_id": user_id, "amount": amount, "utr": utr, "vip_info": vip_info}

def reject_payment_request(req_id: int) -> Optional[dict]:
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM payment_requests WHERE id = ?", (req_id,))
        req = cursor.fetchone()
        if not req:
            return None
        cursor.execute("UPDATE payment_requests SET status = 'rejected', verified_at = ? WHERE id = ?", (now, req_id))
        conn.commit()
        return dict(req)

def track_user_referral(referred_id: int, referrer_id: int) -> bool:
    """Records that referred_id was invited by referrer_id (if not self, not existing user, and not already referred)."""
    if referred_id == referrer_id or referrer_id <= 0:
        return False
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT referred_by, onboarding_status, created_at FROM users WHERE user_id = ?", (referred_id,))
        row = cursor.fetchone()
        # Block existing users from counting as new referrals
        if row and (row["referred_by"] or row["onboarding_status"] == "completed"):
            return False

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
    - Automatically resets quota & grants 30-Day VIP if 5 referrals reached!
    - Or grants +3 Days VIP if milestone (every 3) hit, or bonus notes/texts.
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
    
    # Milestone: 5 referrals reached -> Automatic complete quota reset + 30-Day VIP Pass!
    if total_completed >= 5:
        reset_user_quota(referrer_id)
        grant_vip_subscription(referrer_id, days=30, amount=0.0, method="referral_5", ref=f"ref_milestone_5_{total_completed}")
        reward_type = "vip_reset_5"
    elif total_completed > 0 and total_completed % 3 == 0:
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

# ====================================================
# MASK MAPPINGS & VOICE MATCH RECONNECT LOGIC
# ====================================================
def register_mask_mapping(mask_id: str, user_id: int):
    """Associates permanent Joy-XXXX mask with user_id for mutual reconnects and offline call alerts."""
    if not mask_id or not user_id:
        return
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO mask_mappings (mask_id, user_id, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(mask_id) DO UPDATE SET user_id = excluded.user_id, updated_at = excluded.updated_at
        """, (mask_id.strip(), user_id, now))
        conn.commit()

def get_user_id_by_mask(mask_id: str) -> Optional[int]:
    """Retrieves user_id associated with a permanent Joy Unique ID."""
    if not mask_id:
        return None
    clean_mask = mask_id.strip()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM mask_mappings WHERE mask_id = ?", (clean_mask,))
        row = cursor.fetchone()
        if row and row["user_id"]:
            return int(row["user_id"])
        cursor.execute("SELECT user_id FROM users WHERE unique_id = ?", (clean_mask,))
        row = cursor.fetchone()
        if row and row["user_id"]:
            return int(row["user_id"])
    return None

def get_mask_by_user_id(user_id: int) -> str:
    """Retrieves or deterministically registers permanent Joy Unique ID associated with a user_id."""
    if not user_id:
        return "Joy-00000"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT unique_id FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row and row["unique_id"]:
            return str(row["unique_id"])
            
        cursor.execute("SELECT mask_id FROM mask_mappings WHERE user_id = ? ORDER BY updated_at DESC LIMIT 1", (user_id,))
        row = cursor.fetchone()
        if row and row["mask_id"]:
            return str(row["mask_id"])

    # Deterministic generation based on Telegram ID
    mask = generate_deterministic_unique_id(user_id)
    register_mask_mapping(mask, user_id)
    with get_connection() as conn:
        conn.cursor().execute("UPDATE users SET unique_id = ? WHERE user_id = ?", (mask, user_id))
        conn.commit()
    return mask

# ====================================================
# SAFETY SHIELD & BLOCKLIST MANAGEMENT
# ====================================================
def block_peer(user_id: int, blocked_mask: str):
    """Blocks a permanent mask from matchmaking and mutual calls."""
    if not user_id or not blocked_mask:
        return
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO blocked_peers (user_id, blocked_mask, created_at)
            VALUES (?, ?, ?)
        """, (user_id, blocked_mask.strip(), now))
        conn.commit()

def is_peer_blocked(user_id: int, blocked_mask: str) -> bool:
    """Checks if user has blocked this permanent mask."""
    if not user_id or not blocked_mask:
        return False
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM blocked_peers WHERE user_id = ? AND blocked_mask = ?",
            (user_id, blocked_mask.strip())
        )
        return cursor.fetchone() is not None

def get_blocked_peers(user_id: int) -> List[str]:
    """Returns list of blocked mask IDs for user."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT blocked_mask FROM blocked_peers WHERE user_id = ?", (user_id,))
        return [r["blocked_mask"] for r in cursor.fetchall()]

# ====================================================
# DAILY CHAT STREAKS & RELATIONSHIP LEVELS
# ====================================================
RELATIONSHIP_LEVELS = [
    (1, "🌱 New Acquaintance", "We're getting to know each other!"),
    (3, "🌸 Good Friends", "We chat every day and have fun!"),
    (7, "💖 Close Bestie & Confidant", "You can share anything with me."),
    (14, "✨ Special Soul Connection", "We have an incredible, unbreakable bond."),
    (30, "💍 Soulmate / Eternal Bond", "Unstoppable connection — Joy is forever by your side.")
]

def update_user_streak(user_id: int) -> Tuple[int, int, bool, str]:
    """
    Updates the daily chat streak for user.
    Returns: (new_streak_count, relationship_level, is_milestone, level_title)
    """
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT streak_count, last_streak_date, relationship_level FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            return 1, 1, False, "🌱 New Acquaintance"
            
        current_streak = row["streak_count"] or 0
        last_date = row["last_streak_date"] or ""
        rel_level = row["relationship_level"] or 1
        
        # Determine title
        def get_title(streak):
            for days, title, _ in reversed(RELATIONSHIP_LEVELS):
                if streak >= days:
                    return title
            return "🌱 New Acquaintance"

        if last_date == today_str:
            return current_streak, rel_level, False, get_title(current_streak)
            
        if last_date == yesterday_str:
            new_streak = current_streak + 1
        else:
            new_streak = 1
            
        new_level = 1
        for min_days, _, _ in RELATIONSHIP_LEVELS:
            if new_streak >= min_days:
                new_level = min_days
                
        is_milestone = (new_streak in [3, 7, 14, 30]) and (last_date != today_str)
        level_title = get_title(new_streak)
        
        cursor.execute("""
            UPDATE users SET streak_count = ?, last_streak_date = ?, relationship_level = ?
            WHERE user_id = ?
        """, (new_streak, today_str, new_level, user_id))
        conn.commit()
        return new_streak, new_level, is_milestone, level_title

def get_user_streak_info(user_id: int) -> dict:
    """Returns streak and relationship info for user."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT streak_count, last_streak_date, relationship_level FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        streak = row["streak_count"] if row and row["streak_count"] else 0
        level_days = row["relationship_level"] if row and row["relationship_level"] else 1
        
        level_title = "🌱 New Acquaintance"
        level_desc = "Start chatting daily to build your streak!"
        for days, title, desc in reversed(RELATIONSHIP_LEVELS):
            if streak >= days:
                level_title = title
                level_desc = desc
                break
                
        return {
            "streak": streak,
            "level": level_days,
            "title": level_title,
            "description": level_desc
        }

# ====================================================
# PROACTIVE MORNING & NIGHT MESSAGES
# ====================================================
def get_eligible_proactive_users(proactive_type: str) -> List[dict]:
    """
    Returns users eligible to receive a proactive morning/night message.
    """
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, username, first_name, gender, active_contact, custom_ai_name, language
            FROM users
            WHERE onboarding_status = 'completed'
              AND (proactive_enabled IS NULL OR proactive_enabled = 1)
              AND (last_proactive_date IS NULL OR last_proactive_date != ? OR last_proactive_type != ?)
            LIMIT 50
        """, (today_str, proactive_type))
        return [dict(r) for r in cursor.fetchall()]

def mark_user_proactive_sent(user_id: int, proactive_type: str):
    """Records that a proactive message of this type was sent today."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET last_proactive_date = ?, last_proactive_type = ?
            WHERE user_id = ?
        """, (today_str, proactive_type, user_id))
        conn.commit()

