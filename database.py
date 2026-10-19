"""
Joy Bot - SQLite Database Storage & Usage Tracker
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from config import DB_PATH, DAILY_FREE_VOICE_LIMIT, DAILY_FREE_TEXT_LIMIT, OWNER_ID

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes tables for users, daily usage, and conversation context."""
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
        
        conn.commit()

def get_or_create_user(user_id: int, username: str = "", first_name: str = "") -> dict:
    """Retrieves user profile or registers new user."""
    today = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        if row is None:
            # Owner is automatically VIP
            is_vip = 1 if user_id == OWNER_ID else 0
            cursor.execute("""
                INSERT INTO users (user_id, username, first_name, mode, voice, is_vip, created_at)
                VALUES (?, ?, ?, 'companion', 'female', ?, ?)
            """, (user_id, username, first_name, is_vip, today))
            conn.commit()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
        
        return dict(row)

def update_user_preference(user_id: int, key: str, value: str):
    """Updates mode ('companion'/'english') or voice ('female'/'male'/'hindi')."""
    if key not in ("mode", "voice"):
        return
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE users SET {key} = ? WHERE user_id = ?", (value, user_id))
        conn.commit()

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
        
        # Check if user is VIP
        cursor.execute("SELECT is_vip FROM users WHERE user_id = ?", (user_id,))
        user_row = cursor.fetchone()
        if user_row and user_row["is_vip"] == 1:
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
