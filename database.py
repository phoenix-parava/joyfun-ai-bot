"""
Asynchronous Database Layer using aiosqlite in WAL Mode
Lightweight, thread-safe, and memory-capped for strict Render resource budgets.
"""

import aiosqlite
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from config import (
    DB_PATH,
    DAILY_P2P_VOICE_SECONDS,
    DAILY_AI_VOICE_SECONDS,
    DAILY_AI_TEXT_MESSAGES,
    DEFAULT_LANGUAGE
)

logger = logging.getLogger("AppDatabase")

@asynccontextmanager
async def get_db_connection():
    """Async context manager that yields a connection configured with WAL mode and row factory."""
    async with aiosqlite.connect(str(DB_PATH), timeout=10.0) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA synchronous=NORMAL")
        await conn.execute("PRAGMA busy_timeout=5000")
        yield conn

async def init_db():
    """Initializes normalized database tables and indexes."""
    async with get_db_connection() as conn:
        # Users Table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                pseudonym TEXT DEFAULT 'Anonymous',
                language TEXT DEFAULT 'tanglish',
                modality TEXT DEFAULT 'voice',
                partner_preference TEXT DEFAULT 'real_or_ai',
                onboarding_completed INTEGER DEFAULT 0,
                terms_accepted_at TEXT DEFAULT NULL,
                email_address TEXT DEFAULT '',
                email_enabled INTEGER DEFAULT 0,
                low_data_mode INTEGER DEFAULT 0,
                speech_rate REAL DEFAULT 1.0,
                created_at TEXT,
                updated_at TEXT
            )
        """)

        # Daily Quota Tracking Table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_quotas (
                user_id INTEGER,
                quota_date TEXT,
                p2p_voice_used_seconds INTEGER DEFAULT 0,
                ai_voice_used_seconds INTEGER DEFAULT 0,
                ai_text_used_count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, quota_date)
            )
        """)

        # User Feedback & Support Logs
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                pseudonym TEXT,
                email TEXT,
                language TEXT,
                message TEXT,
                admin_reply TEXT DEFAULT '',
                status TEXT DEFAULT 'pending',
                created_at TEXT
            )
        """)

        # P2P Completed Sessions
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS p2p_sessions (
                session_id TEXT PRIMARY KEY,
                user_a INTEGER,
                user_b INTEGER,
                language TEXT,
                modality TEXT,
                started_at TEXT,
                ended_at TEXT,
                duration_seconds INTEGER DEFAULT 0
            )
        """)

        # Indexes for speed
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_terms ON users(terms_accepted_at)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_quotas_lookup ON daily_quotas(user_id, quota_date)")
        await conn.commit()
        logger.info("Async SQLite database initialized in WAL mode.")

async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves user profile record or returns None."""
    async with get_db_connection() as conn:
        async with conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_or_create_user(user_id: int, default_name: str = "") -> Dict[str, Any]:
    """Ensures user exists in database and returns their profile record."""
    user = await get_user(user_id)
    if user:
        return user

    now_iso = datetime.now(timezone.utc).isoformat()
    # Generate clean initial pseudonym
    initial_name = default_name.strip()[:20] if default_name else f"Peer-{str(user_id)[-4:]}"
    if len(initial_name) < 3:
        initial_name = f"Peer-{str(user_id)[-4:]}"

    async with get_db_connection() as conn:
        await conn.execute("""
            INSERT INTO users (
                user_id, pseudonym, language, modality, partner_preference,
                onboarding_completed, terms_accepted_at, email_address,
                email_enabled, low_data_mode, speech_rate, created_at, updated_at
            ) VALUES (?, ?, ?, 'voice', 'real_or_ai', 0, NULL, '', 0, 0, 1.0, ?, ?)
            ON CONFLICT(user_id) DO NOTHING
        """, (user_id, initial_name, DEFAULT_LANGUAGE, now_iso, now_iso))
        await conn.commit()

    return await get_user(user_id) or {}

async def accept_terms(user_id: int) -> bool:
    """Records formal acceptance of Terms and Privacy Agreement."""
    now_iso = datetime.now(timezone.utc).isoformat()
    async with get_db_connection() as conn:
        await conn.execute("""
            UPDATE users 
            SET terms_accepted_at = ?, updated_at = ?
            WHERE user_id = ?
        """, (now_iso, now_iso, user_id))
        await conn.commit()
    logger.info(f"User {user_id} formally accepted terms at {now_iso}")
    return True

async def complete_onboarding(
    user_id: int,
    pseudonym: str,
    language: str,
    modality: str,
    partner_preference: str
) -> bool:
    """Saves user's pre-chat onboarding choices."""
    now_iso = datetime.now(timezone.utc).isoformat()
    clean_name = pseudonym.strip()[:20]
    if len(clean_name) < 3:
        clean_name = f"Peer-{str(user_id)[-4:]}"

    async with get_db_connection() as conn:
        await conn.execute("""
            UPDATE users 
            SET pseudonym = ?, language = ?, modality = ?, 
                partner_preference = ?, onboarding_completed = 1, updated_at = ?
            WHERE user_id = ?
        """, (clean_name, language.lower().strip(), modality.lower().strip(), partner_preference, now_iso, user_id))
        await conn.commit()
    return True

async def update_user_settings(user_id: int, **kwargs) -> Dict[str, Any]:
    """Dynamically updates user preferences in Settings tab."""
    allowed_fields = {
        "pseudonym", "language", "modality", "partner_preference",
        "email_address", "email_enabled", "low_data_mode", "speech_rate"
    }
    updates = []
    values = []

    for k, v in kwargs.items():
        if k in allowed_fields and v is not None:
            updates.append(f"{k} = ?")
            values.append(v)

    if not updates:
        return await get_user(user_id) or {}

    now_iso = datetime.now(timezone.utc).isoformat()
    updates.append("updated_at = ?")
    values.append(now_iso)
    values.append(user_id)

    async with get_db_connection() as conn:
        query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?"
        await conn.execute(query, tuple(values))
        await conn.commit()

    return await get_user(user_id) or {}

def _get_today_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

async def get_user_quota_summary(user_id: int) -> Dict[str, Any]:
    """Returns today's live server-authoritative quota balances."""
    today = _get_today_iso()
    async with get_db_connection() as conn:
        async with conn.execute(
            "SELECT * FROM daily_quotas WHERE user_id = ? AND quota_date = ?",
            (user_id, today)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return {
                    "quota_date": today,
                    "p2p_voice": {"used": 0, "limit": DAILY_P2P_VOICE_SECONDS, "remaining": DAILY_P2P_VOICE_SECONDS},
                    "ai_voice": {"used": 0, "limit": DAILY_AI_VOICE_SECONDS, "remaining": DAILY_AI_VOICE_SECONDS},
                    "ai_text": {"used": 0, "limit": DAILY_AI_TEXT_MESSAGES, "remaining": DAILY_AI_TEXT_MESSAGES},
                }

            p2p_used = row["p2p_voice_used_seconds"]
            ai_v_used = row["ai_voice_used_seconds"]
            ai_t_used = row["ai_text_used_count"]

            return {
                "quota_date": today,
                "p2p_voice": {
                    "used": p2p_used,
                    "limit": DAILY_P2P_VOICE_SECONDS,
                    "remaining": max(0, DAILY_P2P_VOICE_SECONDS - p2p_used)
                },
                "ai_voice": {
                    "used": ai_v_used,
                    "limit": DAILY_AI_VOICE_SECONDS,
                    "remaining": max(0, DAILY_AI_VOICE_SECONDS - ai_v_used)
                },
                "ai_text": {
                    "used": ai_t_used,
                    "limit": DAILY_AI_TEXT_MESSAGES,
                    "remaining": max(0, DAILY_AI_TEXT_MESSAGES - ai_t_used)
                },
            }

async def consume_quota(user_id: int, quota_type: str, amount: int = 1) -> Tuple[bool, int, int]:
    """
    Consumes quota server-authoritatively.
    quota_type: 'p2p_voice' (seconds), 'ai_voice' (seconds), or 'ai_text' (count)
    Returns: (is_allowed, remaining, limit)
    """
    today = _get_today_iso()
    col_map = {
        "p2p_voice": ("p2p_voice_used_seconds", DAILY_P2P_VOICE_SECONDS),
        "ai_voice": ("ai_voice_used_seconds", DAILY_AI_VOICE_SECONDS),
        "ai_text": ("ai_text_used_count", DAILY_AI_TEXT_MESSAGES),
    }

    if quota_type not in col_map:
        return (True, 9999, 9999)

    col, limit = col_map[quota_type]

    async with get_db_connection() as conn:
        # Ensure row exists
        await conn.execute("""
            INSERT INTO daily_quotas (user_id, quota_date, p2p_voice_used_seconds, ai_voice_used_seconds, ai_text_used_count)
            VALUES (?, ?, 0, 0, 0)
            ON CONFLICT(user_id, quota_date) DO NOTHING
        """, (user_id, today))

        async with conn.execute(f"SELECT {col} FROM daily_quotas WHERE user_id = ? AND quota_date = ?", (user_id, today)) as cur:
            row = await cur.fetchone()
            current_used = row[0] if row else 0

        if current_used >= limit:
            return (False, 0, limit)

        new_used = current_used + amount
        await conn.execute(
            f"UPDATE daily_quotas SET {col} = ? WHERE user_id = ? AND quota_date = ?",
            (new_used, user_id, today)
        )
        await conn.commit()

        remaining = max(0, limit - new_used)
        return (True, remaining, limit)

async def save_feedback(user_id: int, pseudonym: str, email: str, language: str, message: str) -> int:
    """Stores user feedback submission."""
    now_iso = datetime.now(timezone.utc).isoformat()
    async with get_db_connection() as conn:
        cursor = await conn.execute("""
            INSERT INTO feedback_logs (user_id, pseudonym, email, language, message, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
        """, (user_id, pseudonym, email, language, message, now_iso))
        await conn.commit()
        return cursor.lastrowid

async def record_feedback_reply(feedback_id: int, reply_text: str):
    """Updates feedback status with admin response."""
    async with get_db_connection() as conn:
        await conn.execute("""
            UPDATE feedback_logs 
            SET admin_reply = ?, status = 'replied'
            WHERE id = ?
        """, (reply_text, feedback_id))
        await conn.commit()
