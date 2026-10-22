"""
Joy Bot - Notion Subscription Sync Engine
Syncs VIP Subscribers between Notion Cloud Database and Local SQLite cache.
Enables visual subscriber management from mobile Notion app with 0 downtime.
"""

import os
import json
import logging
import urllib.request
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

from config import NOTION_TOKEN, NOTION_SUBSCRIBERS_DB_ID
from database import get_connection

logger = logging.getLogger("JoySubscriptionSync")

NOTION_API_VERSION = "2022-06-28"

def _notion_request(endpoint: str, method: str = "GET", data: Optional[dict] = None) -> Optional[dict]:
    """Helper to perform requests to Notion API."""
    if not NOTION_TOKEN or not NOTION_SUBSCRIBERS_DB_ID:
        logger.warning("Notion token or subscriber DB ID not configured.")
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
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        logger.error(f"Notion API error on {endpoint}: {e}")
        return None

def sync_subscribers_from_notion() -> Dict[str, Any]:
    """
    Fetches all active subscribers from Notion and updates local SQLite cache.
    Marks expired subscribers locally if marked 'Expired' in Notion.
    """
    if not NOTION_TOKEN or not NOTION_SUBSCRIBERS_DB_ID:
        return {"ok": False, "reason": "Notion not configured", "synced": 0}

    # Query Notion database for all subscriber entries
    res = _notion_request(f"databases/{NOTION_SUBSCRIBERS_DB_ID}/query", method="POST", data={})
    if not res or "results" not in res:
        return {"ok": False, "reason": "Failed to query Notion DB", "synced": 0}

    synced_count = 0
    active_ids = []

    with get_connection() as conn:
        cursor = conn.cursor()
        for page in res.get("results", []):
            props = page.get("properties", {})
            
            # Extract User ID
            uid_list = props.get("User ID", {}).get("title", [])
            if not uid_list:
                continue
            raw_uid = uid_list[0].get("plain_text", "").strip()
            try:
                user_id = int(raw_uid)
            except ValueError:
                continue

            # Extract Status
            status_obj = props.get("Status", {}).get("select") or {}
            status = status_obj.get("name", "Active")

            # Extract Expiry Date
            expiry_obj = props.get("Expiry Date", {}).get("date") or {}
            expiry_str = expiry_obj.get("start", "")

            # Check if active
            is_active = status in ("Active", "Lifetime")
            if is_active and status == "Active" and expiry_str:
                try:
                    # Parse YYYY-MM-DD or ISO
                    if "T" in expiry_str:
                        exp_dt = datetime.fromisoformat(expiry_str)
                    else:
                        exp_dt = datetime.strptime(expiry_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    if exp_dt < datetime.now(timezone.utc):
                        is_active = False
                except Exception:
                    pass

            if is_active:
                active_ids.append(user_id)
                # Store ISO format expiry
                iso_exp = expiry_str if "T" in expiry_str else f"{expiry_str}T23:59:59+00:00" if expiry_str else "2099-12-31T23:59:59+00:00"
                cursor.execute("""
                    INSERT INTO users (user_id, username, first_name, is_vip, vip_expiry, created_at)
                    VALUES (?, '', 'Friend', 1, ?, datetime('now'))
                    ON CONFLICT(user_id) DO UPDATE SET is_vip = 1, vip_expiry = ?
                """, (user_id, iso_exp, iso_exp))
                synced_count += 1
            else:
                cursor.execute("UPDATE users SET is_vip = 0 WHERE user_id = ?", (user_id,))

        conn.commit()

    logger.info(f"Successfully synced {synced_count} active VIP subscribers from Notion!")
    return {"ok": True, "synced": synced_count, "active_user_ids": active_ids}

def add_or_update_notion_subscriber(
    user_id: int,
    username: str = "",
    first_name: str = "",
    plan: str = "Monthly VIP (₹99)",
    days: int = 30,
    amount: int = 149,
    utr: str = "",
    notes: str = ""
) -> bool:
    """
    Adds or updates a subscriber row in Notion and refreshes local SQLite cache.
    """
    if not NOTION_TOKEN or not NOTION_SUBSCRIBERS_DB_ID:
        return False

    expiry_dt = datetime.now(timezone.utc) + timedelta(days=days)
    expiry_date_str = expiry_dt.strftime("%Y-%m-%d")

    # 1. Search if page already exists for this User ID
    query_payload = {
        "filter": {
            "property": "User ID",
            "title": {"equals": str(user_id)}
        }
    }
    search_res = _notion_request(f"databases/{NOTION_SUBSCRIBERS_DB_ID}/query", method="POST", data=query_payload)

    properties: Dict[str, Any] = {
        "User ID": {"title": [{"text": {"content": str(user_id)}}]},
        "Name": {"rich_text": [{"text": {"content": first_name or "Friend"}}]},
        "Username": {"rich_text": [{"text": {"content": f"@{username}" if username and not username.startswith("@") else (username or "N/A")}}]},
        "Status": {"select": {"name": "Lifetime" if days > 10000 else "Active"}},
        "Plan": {"select": {"name": plan}},
        "Expiry Date": {"date": {"start": "2099-12-31" if days > 10000 else expiry_date_str}},
        "Amount (INR)": {"number": amount},
        "Payment Ref / UTR": {"rich_text": [{"text": {"content": utr or "DIRECT-UPI"}}]},
        "Notes": {"rich_text": [{"text": {"content": notes or f"Activated on {datetime.now().strftime('%Y-%m-%d %H:%M')}"}}]}
    }

    if search_res and search_res.get("results"):
        page_id = search_res["results"][0]["id"]
        res = _notion_request(f"pages/{page_id}", method="PATCH", data={"properties": properties})
    else:
        create_payload = {
            "parent": {"database_id": NOTION_SUBSCRIBERS_DB_ID},
            "properties": properties
        }
        res = _notion_request("pages", method="POST", data=create_payload)

    if res and res.get("id"):
        # Update local SQLite cache immediately
        iso_exp = "2099-12-31T23:59:59+00:00" if days > 10000 else f"{expiry_date_str}T23:59:59+00:00"
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (user_id, username, first_name, is_vip, vip_expiry, created_at)
                VALUES (?, ?, ?, 1, ?, datetime('now'))
                ON CONFLICT(user_id) DO UPDATE SET is_vip = 1, vip_expiry = ?
            """, (user_id, username, first_name, iso_exp, iso_exp))
            conn.commit()
        return True

    return False

def get_notion_subscribers_list() -> List[Dict[str, Any]]:
    """Returns a list of all subscriber records from Notion."""
    if not NOTION_TOKEN or not NOTION_SUBSCRIBERS_DB_ID:
        return []

    res = _notion_request(f"databases/{NOTION_SUBSCRIBERS_DB_ID}/query", method="POST", data={})
    if not res or "results" not in res:
        return []

    subscribers = []
    for page in res.get("results", []):
        props = page.get("properties", {})
        uid_title = props.get("User ID", {}).get("title", [])
        uid = uid_title[0].get("plain_text", "") if uid_title else ""
        name_rt = props.get("Name", {}).get("rich_text", [])
        name = name_rt[0].get("plain_text", "") if name_rt else ""
        uname_rt = props.get("Username", {}).get("rich_text", [])
        uname = uname_rt[0].get("plain_text", "") if uname_rt else ""
        status_sel = props.get("Status", {}).get("select") or {}
        status = status_sel.get("name", "Active")
        plan_sel = props.get("Plan", {}).get("select") or {}
        plan = plan_sel.get("name", "Monthly VIP")
        exp_date = props.get("Expiry Date", {}).get("date") or {}
        expiry = exp_date.get("start", "No Date")

        if uid:
            subscribers.append({
                "user_id": uid,
                "name": name,
                "username": uname,
                "status": status,
                "plan": plan,
                "expiry": expiry
            })
    return subscribers
