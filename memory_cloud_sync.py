"""
Joy Bot - Notion Memory Cloud Sync Engine
Permanently backs up and restores user imported memories and profiles to Notion Cloud.
Ensures zero data loss even across Render ephemeral container restarts or redeployments.
"""

import os
import json
import logging
import urllib.request
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from config import NOTION_TOKEN, NOTION_MEMORIES_DB_ID
from database import get_connection, get_user_cloud_backup

logger = logging.getLogger("JoyMemoryCloudSync")

NOTION_API_VERSION = "2022-06-28"

def _notion_request(endpoint: str, method: str = "GET", data: Optional[dict] = None) -> Optional[dict]:
    """Helper to perform requests to Notion API."""
    if not NOTION_TOKEN or not NOTION_MEMORIES_DB_ID:
        logger.warning("Notion token or memory DB ID not configured.")
        return None

    url = f"https://api.notion.com/v1/{endpoint}"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json"
    }

    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        logger.error(f"Notion API error on {endpoint}: {e}")
        return None

def _split_text_chunks(text: str, chunk_size: int = 1900) -> List[Dict[str, Any]]:
    """Splits text into Notion rich_text blocks (each block max 2000 chars)."""
    if not text:
        return []
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunks.append({"text": {"content": text[i:i + chunk_size]}})
    return chunks

def backup_user_memory_to_notion(
    user_id: int,
    first_name: str = "",
    username: str = "",
    old_ai_name: str = "",
    memory_text: str = "",
    gender: str = "male",
    active_contact: str = "lover",
    language: str = "auto"
) -> bool:
    """
    Backs up user memory and profile settings to Notion Cloud Database.
    """
    if not NOTION_TOKEN or not NOTION_MEMORIES_DB_ID or not memory_text:
        return False

    if not get_user_cloud_backup(user_id):
        logger.info(f"User {user_id} has Cloud Backup disabled (Incognito). Skipping Notion sync.")
        return False

    lang_map = {
        "auto": "Auto-Match",
        "tanglish": "Tanglish",
        "hinglish": "Hinglish",
        "english": "English"
    }

    properties: Dict[str, Any] = {
        "User ID": {"title": [{"text": {"content": str(user_id)}}]},
        "Name": {"rich_text": [{"text": {"content": first_name or "Friend"}}]},
        "Username": {"rich_text": [{"text": {"content": f"@{username}" if username and not username.startswith("@") else (username or "N/A")}}]},
        "Previous AI": {"rich_text": [{"text": {"content": old_ai_name or "Previous AI"}}]},
        "Perspective": {"select": {"name": "Boy's View" if gender == "male" else "Girl's View"}},
        "Language": {"select": {"name": lang_map.get(language, "Auto-Match")}},
        "Active Contact": {"rich_text": [{"text": {"content": active_contact}}]},
        "Imported Memory": {"rich_text": _split_text_chunks(memory_text)},
        "Last Updated": {"date": {"start": datetime.now().strftime("%Y-%m-%d")}}
    }

    # Check if page already exists for this User ID
    query_payload = {
        "filter": {
            "property": "User ID",
            "title": {"equals": str(user_id)}
        }
    }
    search_res = _notion_request(f"databases/{NOTION_MEMORIES_DB_ID}/query", method="POST", data=query_payload)

    if search_res and search_res.get("results"):
        page_id = search_res["results"][0]["id"]
        res = _notion_request(f"pages/{page_id}", method="PATCH", data={"properties": properties})
    else:
        create_payload = {
            "parent": {"database_id": NOTION_MEMORIES_DB_ID},
            "properties": properties
        }
        res = _notion_request("pages", method="POST", data=create_payload)

    if res and res.get("id"):
        logger.info(f"Successfully backed up memory for User ID {user_id} to Notion Cloud!")
        return True

    return False

def restore_user_memory_from_notion(user_id: int) -> Tuple[str, str]:
    """
    Checks Notion Cloud Database for user's past memories.
    If found, restores them into local SQLite database cache.
    Returns: (old_ai_name, imported_memory)
    """
    if not NOTION_TOKEN or not NOTION_MEMORIES_DB_ID:
        return ("", "")

    query_payload = {
        "filter": {
            "property": "User ID",
            "title": {"equals": str(user_id)}
        }
    }
    search_res = _notion_request(f"databases/{NOTION_MEMORIES_DB_ID}/query", method="POST", data=query_payload)
    if not search_res or not search_res.get("results"):
        return ("", "")

    props = search_res["results"][0].get("properties", {})

    old_ai_blocks = props.get("Previous AI", {}).get("rich_text", [])
    old_ai = old_ai_blocks[0].get("plain_text", "") if old_ai_blocks else ""

    mem_blocks = props.get("Imported Memory", {}).get("rich_text", [])
    memory = "".join(b.get("plain_text", "") for b in mem_blocks).strip()

    persp_sel = props.get("Perspective", {}).get("select") or {}
    gender = "female" if "Girl" in persp_sel.get("name", "") else "male"

    lang_sel = props.get("Language", {}).get("select") or {}
    lang_name = lang_sel.get("name", "Auto-Match").lower()
    clean_lang = "auto"
    if "tanglish" in lang_name:
        clean_lang = "tanglish"
    elif "hinglish" in lang_name:
        clean_lang = "hinglish"
    elif "english" in lang_name:
        clean_lang = "english"

    contact_blocks = props.get("Active Contact", {}).get("rich_text", [])
    active_contact = contact_blocks[0].get("plain_text", "lover") if contact_blocks else "lover"

    # Restore into local SQLite database
    if memory:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (user_id, old_ai_name, imported_memory, gender, active_contact, language, onboarding_status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'completed', datetime('now'))
                ON CONFLICT(user_id) DO UPDATE SET
                    old_ai_name = excluded.old_ai_name,
                    imported_memory = excluded.imported_memory,
                    gender = excluded.gender,
                    active_contact = excluded.active_contact,
                    language = excluded.language,
                    onboarding_status = 'completed'
            """, (user_id, old_ai, memory, gender, active_contact, clean_lang))
            conn.commit()
            logger.info(f"Restored memory and profile for User ID {user_id} from Notion Cloud into SQLite!")

    return (old_ai, memory)

def sync_all_memories_on_startup() -> int:
    """
    On bot startup, scans Notion Memories Database and populates local SQLite if missing.
    Returns: count of restored user memories.
    """
    if not NOTION_TOKEN or not NOTION_MEMORIES_DB_ID:
        return 0

    res = _notion_request(f"databases/{NOTION_MEMORIES_DB_ID}/query", method="POST", data={})
    if not res or "results" not in res:
        return 0

    restored_count = 0
    with get_connection() as conn:
        cursor = conn.cursor()
        for page in res.get("results", []):
            props = page.get("properties", {})
            uid_list = props.get("User ID", {}).get("title", [])
            if not uid_list:
                continue
            raw_uid = uid_list[0].get("plain_text", "").strip()
            try:
                user_id = int(raw_uid)
            except ValueError:
                continue

            old_ai_blocks = props.get("Previous AI", {}).get("rich_text", [])
            old_ai = old_ai_blocks[0].get("plain_text", "") if old_ai_blocks else ""

            mem_blocks = props.get("Imported Memory", {}).get("rich_text", [])
            memory = "".join(b.get("plain_text", "") for b in mem_blocks).strip()

            persp_sel = props.get("Perspective", {}).get("select") or {}
            gender = "female" if "Girl" in persp_sel.get("name", "") else "male"

            lang_sel = props.get("Language", {}).get("select") or {}
            lang_name = lang_sel.get("name", "Auto-Match").lower()
            clean_lang = "auto"
            if "tanglish" in lang_name:
                clean_lang = "tanglish"
            elif "hinglish" in lang_name:
                clean_lang = "hinglish"
            elif "english" in lang_name:
                clean_lang = "english"

            contact_blocks = props.get("Active Contact", {}).get("rich_text", [])
            active_contact = contact_blocks[0].get("plain_text", "lover") if contact_blocks else "lover"

            if memory:
                cursor.execute("""
                    INSERT INTO users (user_id, old_ai_name, imported_memory, gender, active_contact, language, onboarding_status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'completed', datetime('now'))
                    ON CONFLICT(user_id) DO UPDATE SET
                        old_ai_name = excluded.old_ai_name,
                        imported_memory = excluded.imported_memory,
                        gender = excluded.gender,
                        active_contact = excluded.active_contact,
                        language = excluded.language,
                        onboarding_status = 'completed'
                """, (user_id, old_ai, memory, gender, active_contact, clean_lang))
                restored_count += 1

        conn.commit()

    logger.info(f"Startup memory sync: Restored {restored_count} user memories from Notion Cloud!")
    return restored_count
