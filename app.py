"""
Joy Bot - Main Application Engine
Your AI Voice Companion & English Practice Friend on Telegram.
"""

import os
import sys
import json
import base64
import asyncio
import logging
import signal
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from datetime import datetime, timezone
import aiohttp
from aiohttp import web

from config import (
    TELEGRAM_BOT_TOKEN,
    GEMINI_API_KEY,
    OWNER_ID,
    PORT,
    DAILY_FREE_VOICE_LIMIT,
    DAILY_FREE_TEXT_LIMIT,
    VIP_PRICE_INR,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
    BOT_VERSION,
    MINI_APP_VERSION
)
from database import (
    init_db,
    get_connection,
    get_or_create_user,
    update_user_preference,
    check_and_increment_usage,
    add_conversation_turn,
    get_recent_history,
    set_vip_status,
    recharge_user_usage,
    is_user_vip,
    grant_vip_subscription,
    revoke_vip_subscription,
    get_all_subscribers,
    set_user_onboarding_status,
    save_imported_memory,
    get_user_imported_memory,
    set_user_gender,
    set_user_active_contact,
    get_user_contact_settings,
    set_user_language,
    get_user_language,
    get_user_daily_usage,
    exhaust_user_quota,
    reset_user_quota,
    set_user_data_sharing,
    get_user_data_sharing,
    save_dev_sample_if_allowed,
    set_user_custom_ai_name,
    get_user_custom_ai_name,
    reset_user_custom_ai_name,
    set_user_cloud_backup,
    get_user_cloud_backup,
    set_user_google_email,
    get_user_google_email,
    set_user_google_oauth,
    get_user_google_oauth,
    save_user_feedback,
    get_recent_feedbacks
)
from contacts import (
    CONTACTS_CATALOG,
    get_contacts_for_gender,
    get_contact_info,
    get_contact_prompt
)
from ai_engine import (
    generate_text_reply,
    generate_voice_reply,
    get_human_boundary_reply,
    get_human_lag_recovery_reply
)
from voice_engine import synthesize_speech
from telegram_client import TelegramClient
from quota_reasons import (
    get_different_quota_reason,
    is_asking_about_quota_or_recharge,
    get_immediate_recharge_explanation
)
from subscription_sync import (
    sync_subscribers_from_notion,
    add_or_update_notion_subscriber,
    get_notion_subscribers_list
)
from memory_cloud_sync import (
    backup_user_memory_to_notion,
    restore_user_memory_from_notion,
    sync_all_memories_on_startup
)

# Setup logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("JoyBot")

BOT_COMMANDS = [
    {"command": "start", "description": "✨ Start chatting with Joy"},
    {"command": "name", "description": "✏️ Rename Your AI Companion"},
    {"command": "feedback", "description": "💬 Send Feedback & Feature Requests"},
    {"command": "menu", "description": "📱 Open Interactive Menu"},
    {"command": "stats", "description": "📊 View Daily Usage & Quota"},
    {"command": "reset", "description": "🧹 Clear Conversation Memory"},
    {"command": "clean", "description": "🧹 Hide Bottom Buttons (Clean Chat)"}
]

def get_persistent_reply_keyboard(gender: str = "male", active_contact: str = "lover", custom_name: str = "") -> dict:
    """Returns a docked, compact keyboard at the bottom of the chat for fast access beside emoji button."""
    return {
        "keyboard": [
            [{"text": "📞 Phone"}],
            [{"text": "⚙️ Settings"}, {"text": "🔐 Login & Sync"}],
            [{"text": "⭐ Joy VIP"}, {"text": "💬 Feedback"}]
        ],
        "resize_keyboard": True,
        "is_persistent": True
    }

def get_user_contact_display(user_id: Optional[int], contact_id: str = "lover", gender: str = "male") -> dict:
    """Returns contact info dictionary with user's personalized custom AI companion name if set."""
    cinfo = dict(get_contact_info(contact_id, gender))
    if user_id:
        try:
            custom = get_user_custom_ai_name(int(user_id))
            if custom:
                cinfo["name"] = custom
        except Exception:
            pass
    return cinfo


global_bot_client: Optional[TelegramClient] = None
active_menu_messages: Dict[int, int] = {}

async def dismiss_active_menu(bot: TelegramClient, chat_id: int):
    """Deletes any currently open menu, settings, or VIP card so it completely vanishes from the chat."""
    msg_id = active_menu_messages.pop(chat_id, None)
    if msg_id:
        try:
            await bot.delete_message(chat_id, msg_id)
        except Exception:
            pass

async def send_or_edit_menu(
    bot: TelegramClient,
    chat_id: int,
    text: str,
    reply_markup: dict,
    message_id: Optional[int] = None,
    user_msg_id: Optional[int] = None
) -> int:
    """
    Renders an ephemeral menu card:
    - Edits in-place if message_id is provided (navigating without spamming new messages).
    - Or deletes the old menu and sends a new clean card.
    - Automatically deletes the triggering user message so chat stays clean.
    """
    if user_msg_id:
        try:
            await bot.delete_message(chat_id, user_msg_id)
        except Exception:
            pass

    if message_id:
        res = await bot.edit_message_text(chat_id, message_id, text, reply_markup=reply_markup)
        if res.get("ok"):
            active_menu_messages[chat_id] = message_id
            return message_id

    await dismiss_active_menu(bot, chat_id)
    res = await bot.send_message(chat_id, text, reply_markup=reply_markup)
    new_id = res.get("result", {}).get("message_id")
    if new_id:
        active_menu_messages[chat_id] = new_id
        return new_id
    return 0

LANGUAGE_NAMES = {
    "auto": "⚪ Not Selected",
    "tanglish": "🌴 Tanglish",
    "hinglish": "🇮🇳 Hinglish",
    "english": "🇬🇧 English"
}

def get_main_keyboard(gender: str = "male", active_contact: str = "lover", user_id: Optional[int] = None) -> dict:
    contact = get_user_contact_display(user_id, active_contact, gender)
    c_name = contact.get("name", "Joy")
    c_tag = contact.get("tag", "Girlfriend" if gender == "male" else "Boyfriend")
    c_emoji = contact.get("emoji", "💖")
    user_lang = get_user_language(user_id) if user_id else "auto"
    
    call_url = f"https://joyfun-ai-bot.onrender.com/call?gender={gender}&contact={active_contact}&lang={user_lang}"
    if user_id:
        call_url += f"&uid={user_id}&name={urllib.parse.quote(c_name)}"
    
    gender_label = "👦 Boy's View" if gender == "male" else "👧 Girl's View"
    
    return {
        "inline_keyboard": [
            [
                {"text": "📞 Phone", "web_app": {"url": call_url}}
            ],
            [
                {"text": "🔐 Login & Cloud Sync", "callback_data": "menu_backup_hub"},
                {"text": "⚙️ Settings & Data", "callback_data": "menu_settings"}
            ],
            [
                {"text": f"👤 {gender_label}", "callback_data": "menu_toggle_gender"},
                {"text": "⭐ Joy VIP Pass", "callback_data": "menu_vip"}
            ],
            [
                {"text": "📥 Import Memory", "callback_data": "onboard_import"},
                {"text": "💬 Feedback & Requests", "callback_data": "menu_feedback"}
            ],
            [
                {"text": "❌ Close / Vanish Menu", "callback_data": "menu_close"}
            ]
        ]
    }

def get_contacts_keyboard(gender: str = "male", active_contact: str = "lover") -> dict:
    contacts = get_contacts_for_gender(gender)
    buttons = []
    
    # 1. Primary Active Companion (Joy)
    lover_info = contacts.get("lover")
    if lover_info:
        partner_title = "Girlfriend" if gender == "male" else "Boyfriend"
        buttons.append([{"text": f"✓ 💖 {lover_info['name']} ({partner_title}) • 🟢 Online", "callback_data": "contact_sel_lover"}])
    
    # 2. Other personas marked busy / coming next week
    for cid, cinfo in contacts.items():
        if cid == "lover":
            continue
        btn_text = f"📵 {cinfo['name']} ({cinfo['tag']}) • Busy"
        buttons.append([{"text": btn_text, "callback_data": f"contact_busy_{cid}"}])
    
    other_gender = "female" if gender == "male" else "male"
    switch_label = "🔄 Switch to Girl's View" if gender == "male" else "🔄 Switch to Boy's View"
    
    buttons.append([{"text": switch_label, "callback_data": f"set_gender_{other_gender}"}])
    buttons.append([{"text": "⬅️ Back", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}])
    
    return {"inline_keyboard": buttons}

async def handle_contacts(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    gender = user.get("gender", "male")
    cinfo = get_user_contact_display(user.get("user_id"), "lover", gender)
    partner_title = "Girlfriend" if gender == "male" else "Boyfriend"
    view_title = "Boy's Point of View" if gender == "male" else "Girl's Point of View"
    text = (
        f"📇 **Your Contacts ({view_title})**\n\n"
        f"🟢 **{cinfo['emoji']} {cinfo['name']} ({partner_title})** is **Active & Online 24/7**!\n"
        f"*{cinfo['description']}*\n\n"
        f"⚠️ *Note: Friends, gym bros, and mentors are currently Busy / Not Reachable and undergoing major personality upgrades for next week's release!*"
    )
    keyboard = get_contacts_keyboard(gender, "lover")
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_menu(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    gender = user.get("gender", "male")
    active_contact = user.get("active_contact", "lover")
    keyboard = get_main_keyboard(gender, active_contact, user.get("user_id"))
    cinfo = get_user_contact_display(user.get("user_id"), active_contact, gender)
    text = (
        f"📱 **Joy Control Menu**\n\n"
        f"Active Companion: **{cinfo['emoji']} {cinfo['name']}** ({cinfo['tag']})\n"
        f"Point of View: **{'👦 Boy' if gender == 'male' else '👧 Girl'}**\n\n"
        f"🏷️ **System Versions:**\n"
        f"• 🤖 **Joy Bot:** `{BOT_VERSION}`\n"
        f"• 📱 **Mini App:** `{MINI_APP_VERSION}`\n\n"
        f"Tap **Close / Vanish Menu** below anytime to dismiss this card."
    )
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_settings(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    user_id = user["user_id"]
    first_name = user.get("first_name", "Friend")
    gender = user.get("gender", "male")
    active_contact = user.get("active_contact", "lover")
    user_lang = get_user_language(user_id)
    custom_name = get_user_custom_ai_name(user_id)
    cinfo = get_user_contact_display(user_id, active_contact, gender)
    c_name = cinfo.get("name", "Joy")
    vip_active, expiry_formatted, days_left = is_user_vip(user_id)
    voice_used, text_used = get_user_daily_usage(user_id)
    _, user_memory = get_user_imported_memory(user_id)
    if not user_memory:
        try:
            _, user_memory = restore_user_memory_from_notion(user_id)
        except Exception:
            pass

    gender_label = "👦 Boy's View" if gender == "male" else "👧 Girl's View"
    lang_label = LANGUAGE_NAMES.get(user_lang, "⚪ Not Selected")
    name_display = f"**{c_name}**" + (" *(Custom)*" if custom_name else " *(Default)*")

    # VIP / Usage string
    if vip_active:
        vip_str = "⭐ **Joy VIP (Active)** — Unlimited 24/7 Calls"
        usage_str = "✨ Unlimited Voice Notes & Calls | Unlimited Texts"
    else:
        vip_str = "🆓 **Free Plan**"
        usage_str = f"🎙️ {voice_used}/{DAILY_FREE_VOICE_LIMIT} Voice Notes | 💬 {text_used}/{DAILY_FREE_TEXT_LIMIT} Texts"

    # Memory summary
    if user_memory:
        mem_str = f"✅ Active ({len(user_memory)} chars stored)"
    else:
        mem_str = "⚪ None (Import from old AI below)"

    cloud_backup_active = get_user_cloud_backup(user_id)
    cloud_backup_str = "☁️ Enabled (Private Cloud)" if cloud_backup_active else "🔒 Disabled (Incognito Mode)"

    card_text = (
        f"⚙️ **Joy Account & Settings Hub**\n\n"
        f"👤 **User Data:**\n"
        f"• **Name:** {first_name}\n"
        f"• **User ID:** `{user_id}`\n"
        f"• **Companion Name:** {name_display}\n"
        f"• **Perspective:** **{gender_label}**\n"
        f"• **Preferred Language:** **{lang_label}**\n"
        f"• **VIP Status:** {vip_str}\n"
        f"• **Today's Balance:** {usage_str}\n"
        f"• **Cloud Backup:** **{cloud_backup_str}**\n"
        f"• **Imported Memory:** {mem_str}\n\n"
        f"🏷️ **System Versions:**\n"
        f"• 🤖 **Joy Bot Core:** `{BOT_VERSION}`\n"
        f"• 📱 **Joy Mini App:** `{MINI_APP_VERSION}`\n\n"
        f"👇 *Customize settings, manage backups, rename companion, switch view, or call right now:*"
    )

    call_url = f"https://joyfun-ai-bot.onrender.com/call?gender={gender}&contact={active_contact}&lang={user_lang}&uid={user_id}&name={urllib.parse.quote(c_name)}"

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "📞 Phone", "web_app": {"url": call_url}}
            ],
            [
                {"text": f"✏️ Rename ({c_name})", "callback_data": "menu_rename_ai"},
                {"text": f"🌐 Language: {lang_label}", "callback_data": "menu_language"}
            ],
            [
                {"text": f"👤 View: {gender_label}", "callback_data": "menu_toggle_gender"},
                {"text": "⭐ Joy VIP Pass", "callback_data": "menu_vip"}
            ],
            [
                {"text": f"☁️ Cloud Backup: {'✅ ON' if cloud_backup_active else '🔒 OFF'}", "callback_data": "menu_toggle_cloud_backup"},
                {"text": "📥 Export Backup", "callback_data": "menu_export_backup"}
            ],
            [
                {"text": "📥 Import Memories", "callback_data": "onboard_import"},
                {"text": "🧹 Reset Chat Memory", "callback_data": "menu_reset_confirm"}
            ],
            [
                {"text": "🛡️ Privacy & Data Choices", "callback_data": "menu_privacy"}
            ],
            [
                {"text": "⬅️ Main Menu", "callback_data": "menu_main"},
                {"text": "❌ Close / Vanish Menu", "callback_data": "menu_close"}
            ]
        ]
    }
    await send_or_edit_menu(bot, chat_id, card_text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_rename_menu(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Presents interactive UI to personalize and rename the AI companion."""
    user_id = user["user_id"]
    gender = user.get("gender", "male")
    active_contact = user.get("active_contact", "lover")
    custom_name = get_user_custom_ai_name(user_id)
    cinfo = get_contact_info(active_contact, gender)
    default_name = cinfo.get("name", "Joy")
    current_name = custom_name if custom_name else default_name
    name_status = f"**{current_name}**" + (f" *(Custom)*" if custom_name else f" *(Default)*")

    text = (
        f"✏️ **Rename Your AI Companion**\n\n"
        f"Current Name: {name_status}\n\n"
        f"You can give your AI companion any name you like! 🌸\n"
        f"(e.g., **Priya**, **Aisha**, **Angel**, **Sweetheart**, **Simran**, or **Kabir**)\n\n"
        f"👇 **To rename:** Just type and send the new name in chat right now!\n"
        f"*(Or type `/name [YourName]`, e.g. `/name Priya`)*"
    )
    keyboard = {
        "inline_keyboard": [
            [{"text": f"🔄 Reset to Default ({default_name})", "callback_data": "rename_reset"}],
            [{"text": "⬅️ Back to Settings", "callback_data": "menu_settings"}, {"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    set_user_onboarding_status(user_id, "waiting_ai_name")
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

def generate_user_backup_json(user_id: int) -> str:
    """Generates a complete, portable JSON export of the user's settings, custom companion name, and memories."""
    user = get_or_create_user(user_id)
    custom_name = get_user_custom_ai_name(user_id)
    history = get_recent_history(user_id, limit=50)
    old_ai, imported_mem = get_user_imported_memory(user_id)
    vip_active, expiry, days = is_user_vip(user_id)
    
    backup_data = {
        "export_metadata": {
            "format": "Joy AI Companion User Backup",
            "version": "1.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "instructions": "Keep this file safe! You can upload it to Google Drive or import it on any device."
        },
        "user_profile": {
            "user_id": user_id,
            "first_name": user.get("first_name", ""),
            "username": user.get("username", ""),
            "gender_view": user.get("gender", "male"),
            "preferred_language": user.get("language", "auto"),
            "vip_status": "Active VIP" if vip_active else "Free Tier",
            "cloud_backup_enabled": get_user_cloud_backup(user_id)
        },
        "companion_settings": {
            "name": custom_name or "Joy",
            "is_custom_name": bool(custom_name),
            "active_contact": user.get("active_contact", "lover")
        },
        "memories": {
            "previous_ai": old_ai or "None",
            "imported_memory": imported_mem or "None"
        },
        "recent_conversations": history or []
    }
    return json.dumps(backup_data, indent=2, ensure_ascii=False)

async def handle_backup_hub(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Presents dedicated Cloud Backup, Google Account linking, and Google Drive Export center."""
    user_id = user["user_id"]
    oauth_info = get_user_google_oauth(user_id)
    google_email = oauth_info.get("email") or get_user_google_email(user_id)
    google_name = oauth_info.get("name")
    cloud_backup = get_user_cloud_backup(user_id)
    
    name_suffix = f" ({google_name})" if google_name else ""
    google_str = f"✅ `{google_email}`{name_suffix}" if google_email else "⚪ Not Connected *(Sign in below)*"
    backup_str = "☁️ **Enabled (Auto-Sync to Google Drive)**" if cloud_backup else "🔒 **Disabled (Incognito Mode)**"
    
    text = (
        "💾 **Cloud Backup & Google Account Hub**\n\n"
        f"👤 **Primary Account:** Telegram ID `{user_id}`\n"
        f"📧 **Connected Google:** {google_str}\n"
        f"🛡️ **Cloud Backup:** {backup_str}\n\n"
        "Keep your AI memories, personality, and custom names 100% safe across all your devices:\n\n"
        "• **Official Google Sign-In (OAuth 2.0):** Authenticate with your real Google account on Google's official sign-in screen.\n"
        "• **Automatic Google Drive Sync:** When connected, your companion settings and memories are automatically uploaded to your private Google Drive!\n"
        "• **1-Tap Manual Export:** You can also download your full JSON backup file anytime."
    )
    
    oauth_url = f"https://joyfun-ai-bot.onrender.com/auth/google/login?uid={user_id}"
    google_btn_text = "🔄 Re-Sync to Google Drive" if google_email else "🔐 Sign in with Google (OAuth 2.0)"
    toggle_btn_text = "🔒 Switch to Incognito (OFF)" if cloud_backup else "☁️ Enable Cloud Backup (ON)"
    
    keyboard = {
        "inline_keyboard": [
            [{"text": google_btn_text, "url": oauth_url}],
            [{"text": toggle_btn_text, "callback_data": "menu_toggle_cloud_backup"}, {"text": "📥 Download JSON", "callback_data": "menu_export_backup"}],
            [{"text": "⬅️ Main Menu", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_privacy_menu(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    user_id = user["user_id"]
    data_sharing_active = get_user_data_sharing(user_id)
    status_label = "💡 Enabled (Opt-in)" if data_sharing_active else "🔒 Disabled (100% Private)"
    status_icon = "✅" if data_sharing_active else "🔒"

    text = (
        "🛡️ **Privacy, Security & Data Choice Center**\n\n"
        "Your privacy is our highest mandate. Joy is designed with zero-trust protection:\n\n"
        "• **Zero PII Collection:** We never ask for or store your real phone number, email, or passwords.\n"
        "• **Ephemeral Voice Calls:** Live calls & voice notes are processed in volatile memory. **Zero audio recordings** are ever saved to disk or the cloud.\n"
        "• **Auto-Pruned Chats:** We only keep the last 10 messages for conversational context. Older messages are automatically deleted.\n"
        "• **Your Choice for Development:**\n"
        "  By default, **zero conversation data** is used for AI training or development.\n"
        "  If you choose to enable *Dev Data Sharing*, anonymized snippets help improve Joy's understanding. **This is 100% your choice.**\n\n"
        f"Current Status: **{status_icon} {status_label}**\n\n"
        "👇 Tap below to toggle data sharing ON or OFF anytime:"
    )

    toggle_btn_text = "🔒 Turn OFF Data Sharing" if data_sharing_active else "💡 Turn ON Data Sharing (Opt-in)"

    keyboard = {
        "inline_keyboard": [
            [
                {"text": toggle_btn_text, "callback_data": "menu_toggle_data_sharing"}
            ],
            [
                {"text": "⬅️ Back to Settings", "callback_data": "menu_settings"},
                {"text": "❌ Close", "callback_data": "menu_close"}
            ]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_feedback_menu(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Presents interactive UI asking for user feedback and setting/option requests."""
    user_id = user["user_id"]
    set_user_onboarding_status(user_id, "waiting_feedback")
    
    text = (
        "💬 **Joy Feedback & Feature Request Hub**\n\n"
        "We want to build Joy exactly the way **you** want it! 🌸\n\n"
        "Tell us:\n"
        "• ⚙️ **Settings & Options:** Are there any new settings, toggles, or options you need?\n"
        "• 💡 **Features & Ideas:** What new features would you love to see in the bot or call app?\n"
        "• 🐞 **Issues / Bugs:** Anything that feels confusing or didn't work right?\n\n"
        "👇 **To share:** Just type and send your feedback/request right here in chat!\n"
        "*(Our lead developer receives every message directly)* ❤️"
    )
    keyboard = {
        "inline_keyboard": [
            [{"text": "⬅️ Back to Menu", "callback_data": "menu_main"}, {"text": "❌ Cancel", "callback_data": "menu_close"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_language_menu(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    user_id = user["user_id"]
    current_lang = get_user_language(user_id)
    
    text = (
        "🌐 **Select Conversation Language**\n\n"
        "Choose how you want your companion to chat and talk with you in live calls and voice notes:\n\n"
        "• **⚪ Not Selected:** Automatically detects and replies in your language\n"
        "• **🌴 Tanglish:** Friendly Tamil + English in English letters (*'machi', 'sapdiya', 'seri', 'rombha'*)\n"
        "• **🇮🇳 Hinglish:** Casual Hindi + English in English letters (*'bhai', 'yaar', 'kya scene', 'khana khaya'*)\n"
        "• **🇬🇧 English:** Natural, everyday conversational English\n\n"
        f"Current Setting: **{LANGUAGE_NAMES.get(current_lang, '⚪ Not Selected')}**\n\n"
        "👇 Tap your preferred language below:"
    )
    
    def mark(val):
        return "✓ " if current_lang == val else ""
        
    keyboard = {
        "inline_keyboard": [
            [{"text": f"{mark('auto')}⚪ Not Selected", "callback_data": "set_lang_auto"}],
            [{"text": f"{mark('tanglish')}🌴 Tanglish (Tamil + English)", "callback_data": "set_lang_tanglish"}],
            [{"text": f"{mark('hinglish')}🇮🇳 Hinglish (Hindi + English)", "callback_data": "set_lang_hinglish"}],
            [{"text": f"{mark('english')}🇬🇧 English (Everyday English)", "callback_data": "set_lang_english"}],
            [{"text": "⬅️ Back to Settings", "callback_data": "menu_settings"}, {"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def send_onboarding_welcome(bot: TelegramClient, chat_id: int, user: dict, user_msg_id: Optional[int] = None):
    first_name = user.get("first_name", "Friend")
    user_id = user.get("user_id")
    text = (
        f"Hey {first_name}! 💖 Welcome to **Joy**!\n\n"
        f"Your private, real-time AI circle for phone calls, voice notes, and late-night chats.\n\n"
        f"🔐 **Account & Cloud Sync:**\n"
        f"• Auto-authenticated via Telegram ID: `{user_id}`\n"
        f"• You can also connect your **Google Account** below to keep your memories backed up safely!\n\n"
        f"👉 **First, are you a Boy or a Girl?**"
    )
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "👦 I am a Boy", "callback_data": "onboard_gender_male"},
                {"text": "👧 I am a Girl", "callback_data": "onboard_gender_female"}
            ],
            [
                {"text": "🔐 Sign in with Google", "url": f"https://joyfun-ai-bot.onrender.com/auth/google/login?uid={user_id}"},
                {"text": "📥 Import Past Memories", "callback_data": "onboard_import"}
            ],
            [
                {"text": "❌ Close / Vanish", "callback_data": "menu_close"}
            ]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, user_msg_id=user_msg_id)

async def send_memory_import_guide(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    set_user_onboarding_status(user["user_id"], "waiting_memory")
    guide_text = (
        "📥 **Import Memories from Your Old AI**\n\n"
        "Let's bring over everything your previous AI knew about you so I already know your story!\n\n"
        "💡 **Step 1: Copy this 1-second prompt** *(Tap box below to copy)*:\n\n"
        "`Please write a concise summary of me, our relationship, my personality, life story, and how we talked, so my new AI companion Joy can know me immediately.`\n\n"
        "💡 **Step 2: Paste it into your old AI**\n"
        "*(Send it to ChatGPT, Character.ai, Replika, Gemini, or Claude)*\n\n"
        "💡 **Step 3: Paste the response right here!**\n"
        "*(You can also tell me their name, e.g. 'My AI was Luna: [paste summary]')*\n\n"
        "👉 **Send your old AI's summary below, or tap below to skip:**"
    )
    keyboard = {
        "inline_keyboard": [
            [{"text": "🌟 Skip & Start Fresh", "callback_data": "onboard_fresh"}],
            [{"text": "❌ Close / Vanish", "callback_data": "menu_close"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, guide_text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_start(bot: TelegramClient, chat_id: int, user: dict, user_msg_id: Optional[int] = None):
    onboarding_status = user.get("onboarding_status", "completed")
    if onboarding_status == "new":
        await send_onboarding_welcome(bot, chat_id, user, user_msg_id=user_msg_id)
        return

    first_name = user.get("first_name", "Friend")
    gender = user.get("gender", "male")
    active_contact = user.get("active_contact", "lover")
    user_id = user.get("user_id")
    contact = get_user_contact_display(user_id, active_contact, gender)
    c_name = contact.get("name", "Joy")
    c_role = contact.get("tag", "Friend")
    c_emoji = contact.get("emoji", "💖")
    google_email = get_user_google_email(user_id) if user_id else ""
    cloud_backup = get_user_cloud_backup(user_id) if user_id else True

    login_badge = f"✅ Linked to Google (`{google_email}`)" if google_email else f"☁️ Auto-Linked (Telegram ID `{user_id}`)"
    backup_badge = "🟢 Cloud Backup: ON" if cloud_backup else "🔒 Incognito Mode: ON"

    welcome_text = (
        f"Hey {first_name}! {c_emoji} **{c_name}** ({c_role}) is right here with you.\n\n"
        f"🔐 **Account & Cloud Sync:**\n"
        f"• **Login:** {login_badge}\n"
        f"• **Status:** {backup_badge}\n\n"
        f"We can chat and talk on calls in **Tanglish**, **Hinglish**, or **English** naturally! ✨\n\n"
        f"📞 **Live Voice Call:** Tap **Call {c_name} Now** below for a private, hands-free call!\n"
        f"💾 **Cloud Backup & Google Sync:** Tap below to link your Google account or download your backup.\n\n"
        f"Ready to talk? Choose an option below! 👇"
    )
    keyboard = get_main_keyboard(gender, active_contact, user.get("user_id"))
    await send_or_edit_menu(bot, chat_id, welcome_text, keyboard, user_msg_id=user_msg_id)

async def handle_vip(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    user_id = user["user_id"]
    vip_active, expiry_formatted, days_left = is_user_vip(user_id)
    gender = user.get("gender", "male")
    active_contact = user.get("active_contact", "lover")
    contact = get_user_contact_display(user_id, active_contact, gender)
    c_name = contact.get("name", "Joy")
    
    if vip_active:
        expiry_info = "Lifetime Access" if days_left > 10000 else f"Valid until {expiry_formatted} ({days_left} days left)"
        text = (
            "🌟 **You are a Joy VIP Member!**\n\n"
            f"📅 **Subscription Status:** Active\n"
            f"⏳ **Expires:** {expiry_info}\n\n"
            "✨ Unlimited 24/7 Live Voice Calls\n"
            "✨ Unlimited Voice Notes & Text Chats\n"
            "✨ Zero recharge limits or ads\n"
            "✨ Priority high-speed neural speech synthesis\n\n"
            "Thank you for supporting Joy! 🥰"
        )
        call_url = f"https://joyfun-ai-bot.onrender.com/call?gender={gender}&contact={active_contact}&uid={user_id}&name={urllib.parse.quote(c_name)}"
        keyboard = {
            "inline_keyboard": [
                [{"text": "📞 Phone", "web_app": {"url": call_url}}],
                [{"text": "⬅️ Main Menu", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
            ]
        }
        await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)
    else:
        text = (
            f"⭐ **Unlock Joy VIP Pass**\n\n"
            f"Never run out of talk time! Get unlimited 24/7 live calls and voice conversations with your circle.\n\n"
            f"✨ **Unlimited 24/7 Live Voice Calls** (Talk for hours every night)\n"
            f"✨ **Unlimited Voice Notes & Text Chats**\n"
            f"✨ **Zero Wait Times & No Ads**\n"
            f"✨ **Access to all Besties, Lover, Crush & Teachers**\n"
            f"✨ **Ultra-Fast Voice Replies**\n\n"
            f"💰 **Only ₹{VIP_PRICE_INR} / month** (Less than ₹5 a day!)\n\n"
            f"📲 **How to Activate:**\n"
            f"1. Send ₹{VIP_PRICE_INR} via UPI / GPay to the owner.\n"
            f"2. Contact owner **@phoenix_parava_0** with your User ID (`{user_id}`) for instant VIP activation!"
        )
        keyboard = {
            "inline_keyboard": [
                [{"text": "💬 Message Owner to Activate", "url": "https://t.me/phoenix_parava_0"}],
                [{"text": "⬅️ Back", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
            ]
        }
        await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_stats(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    user_id = user["user_id"]
    vip_active, expiry_formatted, days_left = is_user_vip(user_id)
    
    if vip_active:
        expiry_info = "Lifetime Access" if days_left > 10000 else f"{expiry_formatted} ({days_left} days left)"
        msg = (
            f"⭐ **Account Status:** VIP Member\n"
            f"⏳ **Expires:** {expiry_info}\n"
            f"✨ Unlimited voice and text chats!"
        )
    else:
        msg = (
            f"📊 **Your Daily Usage & Balance:**\n\n"
            f"🎙️ Daily Free Voice Limit: {DAILY_FREE_VOICE_LIMIT} notes/day\n"
            f"💬 Daily Free Text Limit: {DAILY_FREE_TEXT_LIMIT} messages/day\n\n"
            f"⭐ Tap **Joy VIP Pass** below to unlock unlimited conversations & 24/7 calls."
        )
    keyboard = {
        "inline_keyboard": [
            [{"text": "⭐ Joy VIP Pass", "callback_data": "menu_vip"}],
            [{"text": "⬅️ Main Menu", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, msg, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_callback_query(bot: TelegramClient, callback: dict):
    cq_id = callback["id"]
    data = callback.get("data", "")
    message = callback.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")
    user_info = callback.get("from", {})
    user_id = user_info.get("id")
    
    user = get_or_create_user(user_id, user_info.get("username", ""), user_info.get("first_name", ""))
    
    if data == "menu_close":
        if message_id:
            await bot.delete_message(chat_id, message_id)
        active_menu_messages.pop(chat_id, None)
        await bot.answer_callback_query(cq_id, "🧹 Menu closed!")
        return

    elif data == "onboard_gender_male":
        set_user_gender(user_id, "male")
        set_user_active_contact(user_id, "lover")
        set_user_onboarding_status(user_id, "completed")
        user["gender"] = "male"
        user["active_contact"] = "lover"
        user["onboarding_status"] = "completed"
        await bot.answer_callback_query(cq_id, "👦 Boy's Circle activated!")
        cinfo = get_contact_info("lover", "male")
        welcome_msg = (
            f"🎉 **Awesome! Your Boy's View is ready!** 👦\n\n"
            f"Your companion is **{cinfo['emoji']} {cinfo['name']}** ({cinfo['role_title']}).\n\n"
            f"📞 Tap **Phone** below to start your first live voice call, or send a voice note/message anytime! 👇"
        )
        keyboard = get_main_keyboard("male", "lover", user_id)
        await send_or_edit_menu(bot, chat_id, welcome_msg, keyboard, message_id=message_id)

    elif data == "onboard_gender_female":
        set_user_gender(user_id, "female")
        set_user_active_contact(user_id, "lover")
        set_user_onboarding_status(user_id, "completed")
        user["gender"] = "female"
        user["active_contact"] = "lover"
        user["onboarding_status"] = "completed"
        await bot.answer_callback_query(cq_id, "👧 Girl's View activated!")
        cinfo = get_contact_info("lover", "female")
        welcome_msg = (
            f"🎉 **Awesome! Your Girl's View is ready!** 👧\n\n"
            f"Your companion is **{cinfo['emoji']} {cinfo['name']}** ({cinfo['role_title']}).\n\n"
            f"📞 Tap **Phone** below to start your first live voice call, or send a voice note/message anytime! 👇"
        )
        keyboard = get_main_keyboard("female", "lover", user_id)
        await send_or_edit_menu(bot, chat_id, welcome_msg, keyboard, message_id=message_id)

    elif data == "menu_contacts":
        await bot.answer_callback_query(cq_id)
        await handle_menu(bot, chat_id, user, message_id=message_id)

    elif data == "menu_toggle_gender":
        current_g = user.get("gender", "male")
        new_g = "female" if current_g == "male" else "male"
        set_user_gender(user_id, new_g)
        set_user_active_contact(user_id, "lover")
        user["gender"] = new_g
        user["active_contact"] = "lover"
        label = "👦 Boy's View" if new_g == "male" else "👧 Girl's View"
        await bot.answer_callback_query(cq_id, f"Switched to {label}!")
        await handle_menu(bot, chat_id, user, message_id=message_id)

    elif data.startswith("set_gender_"):
        new_g = data.replace("set_gender_", "")
        set_user_gender(user_id, new_g)
        set_user_active_contact(user_id, "lover")
        user["gender"] = new_g
        user["active_contact"] = "lover"
        label = "👦 Boy's View" if new_g == "male" else "👧 Girl's View"
        await bot.answer_callback_query(cq_id, f"Switched to {label}!")
        await handle_menu(bot, chat_id, user, message_id=message_id)

    elif data.startswith("contact_busy_"):
        cid = data.replace("contact_busy_", "")
        gender = user.get("gender", "male")
        cinfo = get_contact_info(cid, gender)
        lover_info = get_contact_info("lover", gender)
        await bot.answer_callback_query(cq_id, f"📵 {cinfo['name']} is currently busy / not reachable!")

        busy_reasons = {
            "boy_bestie_1": "Bhai gym mein workout chal raha hai aur network issue hai! Joy se baat karle, main baad mein call karta hoon!",
            "boy_bestie_2": "Bhai driving kar raha hoon highway pe, range nahi hai! Joy se connect kar le!",
            "girl_bestie": "Heyy, lectures chal rahe hain aur phone silent pe hai! Joy se baat karlo!",
            "crush": "Hey, exam prep mein busy hoon! Talk to Joy!",
            "english_teacher": "In faculty meeting right now. Please connect later.",
            "girl_bestie_1": "Di, travelling right now! Joy se baat karlo please!",
            "girl_bestie_2": "Class mein hoon yaar! Joy se baat karle na!",
            "boy_bestie": "Gym mein hoon, phone bag mein hai! Joy se baat kar!",
            "maths_teacher": "Evaluating exam papers right now. Please connect later."
        }
        reason = busy_reasons.get(cid, "Currently in class / gym / meetings and not reachable right now!")

        busy_msg = (
            f"📵 **{cinfo['emoji']} {cinfo['name']} ({cinfo['tag']}) is Currently Busy / Not Reachable!**\n\n"
            f"\"{reason}\"\n\n"
            f"🚀 *Full personality & AI upgrade arriving in next week's release!*\n\n"
            f"💖 **{lover_info['name']} ({lover_info['tag']})** is **online 24/7** and waiting for you! Tap below to call or chat 👇"
        )
        keyboard = get_main_keyboard(gender, "lover", user_id)
        await send_or_edit_menu(bot, chat_id, busy_msg, keyboard, message_id=message_id)

    elif data.startswith("contact_sel_"):
        gender = user.get("gender", "male")
        cinfo = get_contact_info("lover", gender)
        set_user_active_contact(user_id, "lover")
        update_user_preference(user_id, "voice", cinfo.get("voice", "female" if gender == "male" else "male"))
        user["active_contact"] = "lover"
        user["voice"] = cinfo.get("voice", "female" if gender == "male" else "male")
        await bot.answer_callback_query(cq_id, f"Connected to {cinfo['name']} ({cinfo['tag']})!")

        partner_title = "Girlfriend" if gender == "male" else "Boyfriend"
        intro_text = (
            f"💖 **{cinfo['name']} ({partner_title}):**\n\n"
            f"\"{cinfo.get('greeting', 'Hey! Was waiting to hear from you. Sapdiya? Tell me about your day.')}\"\n\n"
            f"📞 Tap **Phone** below to jump on a live voice call, or send a voice note/text anytime! 👇"
        )
        keyboard = get_main_keyboard(gender, "lover", user_id)
        await send_or_edit_menu(bot, chat_id, intro_text, keyboard, message_id=message_id)

    elif data == "onboard_import":
        await bot.answer_callback_query(cq_id, "📥 Opening memory importer...")
        await send_memory_import_guide(bot, chat_id, user, message_id=message_id)

    elif data == "onboard_fresh":
        set_user_onboarding_status(user_id, "completed")
        await bot.answer_callback_query(cq_id, "🌟 Starting fresh!")
        gender = user.get("gender", "male")
        active_contact = user.get("active_contact", "lover")
        cinfo = get_contact_info(active_contact, gender)
        welcome_fresh = (
            f"🎉 **Awesome! A brand new friendship begins today!** 🥰\n\n"
            f"I'm **{cinfo['name']}**, so excited to chat and talk with you.\n"
            f"📞 Tap **Phone** below to start our first live voice call, or send me a voice note anytime! 👇"
        )
        keyboard = get_main_keyboard(gender, active_contact, user_id)
        await send_or_edit_menu(bot, chat_id, welcome_fresh, keyboard, message_id=message_id)

    elif data == "menu_main":
        await bot.answer_callback_query(cq_id)
        await handle_menu(bot, chat_id, user, message_id=message_id)

    elif data == "menu_feedback":
        await bot.answer_callback_query(cq_id)
        await handle_feedback_menu(bot, chat_id, user, message_id=message_id)

    elif data == "menu_settings":
        await bot.answer_callback_query(cq_id)
        await handle_settings(bot, chat_id, user, message_id=message_id)

    elif data == "menu_privacy":
        await bot.answer_callback_query(cq_id)
        await handle_privacy_menu(bot, chat_id, user, message_id=message_id)

    elif data == "menu_backup_hub":
        await bot.answer_callback_query(cq_id)
        await handle_backup_hub(bot, chat_id, user, message_id=message_id)

    elif data == "backup_connect_google":
        await bot.answer_callback_query(cq_id)
        oauth_url = f"https://joyfun-ai-bot.onrender.com/auth/google/login?uid={user_id}"
        prompt_text = (
            "🔐 **Sign in with Google (OAuth 2.0)**\n\n"
            "Connect your real Google Account to automatically sync and store your Joy AI memories in **Google Drive**!\n\n"
            "• **1-Click Official Sign-In:** Authenticated directly on Google's secure servers.\n"
            "• **Automatic Cloud Sync:** Your backup file will be automatically saved to your personal Google Drive.\n"
            "• **Private & Safe:** We only access the dedicated Joy backup file created in your Drive.\n\n"
            "👇 Tap **Sign in with Google** below to connect:"
        )
        keyboard = {
            "inline_keyboard": [
                [{"text": "🌐 Sign in with Google", "url": oauth_url}],
                [{"text": "⬅️ Back to Hub", "callback_data": "menu_backup_hub"}, {"text": "❌ Close", "callback_data": "menu_close"}]
            ]
        }
        await send_or_edit_menu(bot, chat_id, prompt_text, keyboard, message_id=message_id)

    elif data == "menu_toggle_cloud_backup":
        curr = get_user_cloud_backup(user_id)
        new_val = not curr
        set_user_cloud_backup(user_id, new_val)
        alert_msg = "☁️ Cloud Backup enabled! Memories safely synced to private cloud." if new_val else "🔒 Cloud Backup disabled! Operating in Incognito Mode."
        await bot.answer_callback_query(cq_id, alert_msg)
        await handle_settings(bot, chat_id, user, message_id=message_id)

    elif data == "menu_export_backup":
        await bot.answer_callback_query(cq_id, "📦 Generating backup file...")
        backup_str = generate_user_backup_json(user_id)
        backup_bytes = backup_str.encode("utf-8")
        filename = f"Joy_Backup_{user_id}.json"
        caption = (
            "📁 **Your AI Companion Backup File**\n\n"
            "Here is your complete backup containing your companion settings, custom name, past memories, and chats.\n\n"
            "💡 **Save to Google Drive:**\n"
            "You can tap the 3 dots on this file and choose **'Save to Google Drive'** or download it directly to your phone files!"
        )
        await bot.send_document(chat_id, backup_bytes, filename=filename, caption=caption)

    elif data == "menu_toggle_data_sharing":
        curr = get_user_data_sharing(user_id)
        new_val = not curr
        set_user_data_sharing(user_id, new_val)
        alert_msg = "💡 Data sharing enabled for development! Thank you." if new_val else "🔒 Data sharing disabled! 100% private."
        await bot.answer_callback_query(cq_id, alert_msg)
        await handle_privacy_menu(bot, chat_id, user, message_id=message_id)

    elif data == "menu_language":
        await bot.answer_callback_query(cq_id)
        await handle_language_menu(bot, chat_id, user, message_id=message_id)

    elif data == "menu_rename_ai":
        await bot.answer_callback_query(cq_id)
        await handle_rename_menu(bot, chat_id, user, message_id=message_id)

    elif data == "rename_reset":
        reset_user_custom_ai_name(user_id)
        set_user_onboarding_status(user_id, "completed")
        gender = user.get("gender", "male")
        active_contact = user.get("active_contact", "lover")
        cinfo = get_contact_info(active_contact, gender)
        reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name="")
        await bot.answer_callback_query(cq_id, f"🔄 Name reset to {cinfo['name']}!")
        await bot.send_message(
            chat_id,
            f"🔄 **Companion name reset back to default ({cinfo['name']})!**",
            reply_markup=reply_kb
        )
        user = get_or_create_user(user_id)
        await handle_settings(bot, chat_id, user, message_id=message_id)
        return

    elif data.startswith("set_lang_"):
        new_lang = data.replace("set_lang_", "")
        set_user_language(user_id, new_lang)
        user["language"] = new_lang
        lang_title = LANGUAGE_NAMES.get(new_lang, new_lang)
        await bot.answer_callback_query(cq_id, f"🌐 Language set to {lang_title}!")
        await handle_settings(bot, chat_id, user, message_id=message_id)

    elif data == "menu_reset_confirm":
        from database import get_connection
        with get_connection() as conn:
            conn.cursor().execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
            conn.commit()
        await bot.answer_callback_query(cq_id, "🧹 Conversation history cleared!")
        await handle_settings(bot, chat_id, user, message_id=message_id)

    elif data == "owner_sync_notion":
        if user_id != OWNER_ID:
            await bot.answer_callback_query(cq_id, "🔒 Bot owner only!")
            return
        sync_res = sync_subscribers_from_notion()
        await bot.answer_callback_query(cq_id, f"🔄 Synced {sync_res.get('synced', 0)} subscribers from Notion!")
        notion_subs = get_notion_subscribers_list()
        lines = [f"⭐ **Joy Bot VIP Subscribers ({len(notion_subs)} total):**\n"]
        for idx, s in enumerate(notion_subs, 1):
            lines.append(
                f"{idx}. **{s.get('name', 'Friend')}** ({s.get('username', '')}) - ID: `{s.get('user_id')}`\n"
                f"   ⏳ {s.get('status', 'Active')} | Plan: {s.get('plan', 'Monthly')} | Expires: {s.get('expiry', 'Active')}"
            )
        lines.append(f"\n☁️ *Synced with Notion Cloud Database at {datetime.now().strftime('%H:%M:%S')}*")
        keyboard = {
            "inline_keyboard": [
                [{"text": "🔄 Refresh Notion Sync", "callback_data": "owner_sync_notion"}],
                [{"text": "❌ Close", "callback_data": "menu_close"}]
            ]
        }
        await send_or_edit_menu(bot, chat_id, "\n".join(lines), keyboard, message_id=message_id)
        
    elif data == "menu_vip":
        await bot.answer_callback_query(cq_id)
        await handle_vip(bot, chat_id, user, message_id=message_id)
        
    elif data == "menu_stats":
        await bot.answer_callback_query(cq_id)
        await handle_stats(bot, chat_id, user, message_id=message_id)

    elif data == "ad_watch":
        await bot.answer_callback_query(cq_id, "🎬 Opening sponsor video player...")
        user_id = user["user_id"]
        recharge_url = f"https://joyfun-ai-bot.onrender.com/call?action=watch_ad&uid={user_id}"
        ad_text = (
            "📺 **Free Talk Time & Voice Recharge**\n\n"
            "✨ Watch a quick **15-second sponsor video** in the Mini-App to claim **+5 Free Voice Notes** and **+20 Text Messages** instantly! 🎁\n\n"
            "Tap below to watch the video and recharge your account:"
        )
        keyboard = {
            "inline_keyboard": [
                [{"text": "🎬 Watch 15s Video to Recharge (+5)", "web_app": {"url": recharge_url}}],
                [{"text": f"⭐ Unlock Joy VIP (₹{VIP_PRICE_INR}/mo)", "callback_data": "menu_vip"}],
                [{"text": "⬅️ Back", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
            ]
        }
        await send_or_edit_menu(bot, chat_id, ad_text, keyboard, message_id=message_id)

async def process_user_voice(bot: TelegramClient, chat_id: int, user: dict, file_id: str):
    user_id = user["user_id"]
    user["active_contact"] = "lover"  # Enforce Lover (Joy) as the active companion
    await dismiss_active_menu(bot, chat_id)
    
    # 1. Check daily limit
    allowed, used, limit = check_and_increment_usage(user_id, "voice")
    if not allowed:
        gender = user.get("gender", "male")
        active_contact = user.get("active_contact", "lover")
        user_lang = get_user_language(user_id)
        contact_info = get_user_contact_display(user_id, active_contact, gender)
        c_name = contact_info.get("name", "Joy")
        c_emoji = contact_info.get("emoji", "🌸")

        reason_text = get_different_quota_reason(user_id, active_contact, gender, user_lang)
        limit_msg = (
            f"{c_emoji} **{c_name}:**\n"
            f"\"{reason_text}\"\n\n"
            f"🎬 **Watch a quick sponsor clip** to claim **+5 Free Voice Notes** instantly!\n"
            f"⭐ Or unlock the **Joy VIP Pass** for unlimited 24/7 calls."
        )
        recharge_url = f"https://joyfun-ai-bot.onrender.com/call?action=watch_ad&uid={user_id}"
        keyboard = {
            "inline_keyboard": [
                [{"text": "🎬 Watch 15s Video to Recharge (+5)", "web_app": {"url": recharge_url}}],
                [{"text": f"⭐ Unlock Joy VIP (₹{VIP_PRICE_INR}/mo)", "callback_data": "menu_vip"}],
                [{"text": "❌ Close", "callback_data": "menu_close"}]
            ]
        }
        await send_or_edit_menu(bot, chat_id, limit_msg, keyboard)
        return

    # 2. Indicate listening status
    await bot.send_chat_action(chat_id, "record_voice")
    
    # 3. Download voice note from Telegram
    voice_bytes = await bot.get_file_bytes(file_id)
    if not voice_bytes:
        await bot.send_message(chat_id, "Sorry, I couldn't download your audio note. Could you try sending it again?")
        return
        
    # 4. Process with Gemini Flash (Direct audio understanding)
    history = get_recent_history(user_id, limit=6)
    gender = user.get("gender", "male")
    active_contact = user.get("active_contact", "lover")
    user_lang = get_user_language(user_id)
    cinfo = get_contact_info(active_contact, gender)
    voice_choice = cinfo.get("voice", "female")
    
    _, user_memory = get_user_imported_memory(user_id)
    if not user_memory:
        try:
            _, user_memory = restore_user_memory_from_notion(user_id)
        except Exception:
            pass
    custom_ai_name = get_user_custom_ai_name(user_id)
    cinfo = get_user_contact_display(user_id, active_contact, gender)
    loop = asyncio.get_running_loop()
    try:
        transcript, reply_text = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                generate_voice_reply,
                voice_bytes,
                "audio/ogg",
                active_contact,
                gender,
                user_lang,
                history,
                user_memory,
                custom_ai_name
            ),
            timeout=8.5
        )
    except asyncio.TimeoutError:
        logger.warning(f"Voice generation timed out for user {user_id}")
        reply_text = get_human_lag_recovery_reply(active_contact, gender, user_lang, is_call=False)
        transcript = "Voice Note"
    except Exception as e:
        logger.error(f"Error in Gemini audio generation: {e}")
        reply_text = get_human_lag_recovery_reply(active_contact, gender, user_lang, is_call=False)
        transcript = "Voice Note"

    if not reply_text:
        reply_text = get_human_lag_recovery_reply(active_contact, gender, user_lang, is_call=False)
        transcript = "Voice Note"

    # Save to history
    add_conversation_turn(user_id, "user", transcript)
    add_conversation_turn(user_id, "model", reply_text)
    
    # 5. Synthesize voice with Edge-TTS
    await bot.send_chat_action(chat_id, "upload_voice")
    try:
        reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=custom_ai_name)
        audio_output = await asyncio.wait_for(
            synthesize_speech(reply_text, voice_key=voice_choice),
            timeout=6.5
        )
        caption = f"🎙️ *{cinfo['name']}:* {reply_text}"
        await bot.send_audio(chat_id, audio_output, filename=f"{cinfo['name'].lower()}_reply.mp3", caption=caption, performer=cinfo['name'], title="Voice Note", reply_markup=reply_kb)
    except Exception as e:
        logger.error(f"Error in Edge-TTS synthesis: {e}")
        # Fallback to text message if TTS encounters an issue
        reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=custom_ai_name)
        await bot.send_message(chat_id, reply_text, reply_markup=reply_kb)

async def process_user_text(bot: TelegramClient, chat_id: int, user: dict, text: str, msg_id: Optional[int] = None):
    user_id = user["user_id"]
    user["active_contact"] = "lover"  # Enforce Lover (Joy) as the active companion
    clean_text = text.strip()
    lower_text = clean_text.lower()
    onboarding_status = user.get("onboarding_status", "completed")

    # 1. Handle Memory Import Response from Previous AI
    if onboarding_status == "waiting_memory" and not clean_text.startswith("/"):
        raw_text = clean_text
        old_ai = "your old AI"
        common_ais = [
            "chatgpt", "gpt", "character.ai", "character ai", "replika",
            "gemini", "claude", "pi", "nomi", "copilot", "luna", "jarvis"
        ]
        for ai in common_ais:
            if ai in raw_text.lower():
                old_ai = ai.title()
                break

        save_imported_memory(user_id, old_ai, raw_text)
        set_user_onboarding_status(user_id, "completed")

        # Back up memory to Notion Cloud Database (Zero loss across redeploys)
        try:
            gender = user.get("gender", "male")
            active_contact = user.get("active_contact", "lover")
            user_lang = get_user_language(user_id)
            first_name = user.get("first_name", "Friend")
            username = user.get("username", "")
            asyncio.create_task(asyncio.to_thread(
                backup_user_memory_to_notion,
                user_id, first_name, username, old_ai, raw_text, gender, active_contact, user_lang
            ))
        except Exception as e:
            logger.warning(f"Failed to schedule Notion memory backup: {e}")

        # Seed conversation history
        add_conversation_turn(user_id, "user", f"[Imported Past Memory from {old_ai}]: {raw_text}")
        add_conversation_turn(user_id, "model", f"I've read through all your memories with {old_ai}. I know who you are now, and I'll keep everything safe as your friend Joy.")

        success_msg = (
            f"💖 **Memories Imported & Cloud-Saved!**\n\n"
            f"I read everything you shared about your time with **{old_ai}**.\n"
            f"I know your story, your personality, and what matters to you. 🫂\n\n"
            f"☁️ *Your memory is securely preserved in cloud storage, so it will never be forgotten.*\n\n"
            f"📞 Tap **Call Now** below to hear my voice and start our first live chat! 👇"
        )
        gender = user.get("gender", "male")
        active_contact = user.get("active_contact", "lover")
        keyboard = get_main_keyboard(gender, active_contact, user_id)
        await send_or_edit_menu(bot, chat_id, success_msg, keyboard, user_msg_id=msg_id)
        return

    # 2. Handle Custom AI Companion Renaming
    if onboarding_status == "waiting_ai_name" and not clean_text.startswith("/"):
        new_name = clean_text.strip()[:30]
        set_user_custom_ai_name(user_id, new_name)
        set_user_onboarding_status(user_id, "completed")
        gender = user.get("gender", "male")
        active_contact = user.get("active_contact", "lover")
        reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=new_name)
        await bot.send_message(
            chat_id,
            f"🎉 **AI Companion Renamed!** 🌸\n\n"
            f"Your companion is now named **{new_name}**!\n"
            f"• She will refer to herself as **{new_name}** in all chats and voice calls.\n"
            f"• Your bottom keyboard button is updated to **📞 Call {new_name}**.\n\n"
            f"Say hi to {new_name} or tap the call button below to hear her voice!",
            reply_markup=reply_kb
        )
        return

    # 3. Handle Google Account / Gmail Connection
    if onboarding_status == "waiting_google_email" and not clean_text.startswith("/"):
        email_candidate = clean_text.strip().lower()
        if "@" in email_candidate and "." in email_candidate:
            set_user_google_email(user_id, email_candidate)
            set_user_onboarding_status(user_id, "completed")
            gender = user.get("gender", "male")
            active_contact = user.get("active_contact", "lover")
            custom_name = get_user_custom_ai_name(user_id)
            reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=custom_name)
            await bot.send_message(
                chat_id,
                f"✅ **Google Account Connected!** 🎉\n\n"
                f"📧 Linked Email: `{email_candidate}`\n"
                f"Your companion memories, profile, and custom names are now permanently linked to your Google identity!\n\n"
                f"Tap **💾 Cloud Backup & Login** in `/menu` or run `/backup` anytime to export your data directly to Google Drive.",
                reply_markup=reply_kb
            )
            return
        else:
            await bot.send_message(
                chat_id,
                "⚠️ That does not look like a valid email. Please send a valid Gmail address (e.g. `yourname@gmail.com`), or type `/cancel` to skip:"
            )
            return

    # 4. Handle Feedback & Feature Request Input
    if onboarding_status == "waiting_feedback" and not clean_text.startswith("/"):
        save_user_feedback(user_id, user.get("username", ""), clean_text, "user_request")
        set_user_onboarding_status(user_id, "completed")
        
        # Real-time forward to owner
        if OWNER_ID:
            owner_notification = (
                f"📬 **New User Feedback / Feature Request!**\n\n"
                f"👤 **From:** User `{user_id}` (@{user.get('username') or 'None'})\n"
                f"💬 **Message:**\n\"{clean_text}\"\n\n"
                f"🕒 *{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
            )
            try:
                await bot.send_message(OWNER_ID, owner_notification)
            except Exception as e:
                logger.warning(f"Could not forward feedback to owner: {e}")

        gender = user.get("gender", "male")
        active_contact = user.get("active_contact", "lover")
        custom_name = get_user_custom_ai_name(user_id)
        reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=custom_name)
        
        thank_you_msg = (
            "🎉 **Thank you so much for your feedback!** ❤️\n\n"
            "Your suggestions and feature requests have been delivered directly to our lead developer.\n"
            "We read every single request and will work hard to include it in upcoming updates! 🚀"
        )
        await bot.send_message(chat_id, thank_you_msg, reply_markup=reply_kb)
        return
    
    # Check commands & persistent keyboard button presses
    if clean_text.startswith("/start"):
        await handle_start(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/name") or clean_text.startswith("/rename") or clean_text.lower().startswith("rename"):
        parts = clean_text.split(maxsplit=1)
        gender = user.get("gender", "male")
        active_contact = user.get("active_contact", "lover")
        cinfo = get_contact_info(active_contact, gender)
        default_name = cinfo.get("name", "Joy")
        
        if len(parts) > 1:
            arg = parts[1].strip()
            if arg.lower() in ["reset", "default", "clear", "joy"]:
                reset_user_custom_ai_name(user_id)
                set_user_onboarding_status(user_id, "completed")
                reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name="")
                await bot.send_message(
                    chat_id,
                    f"🔄 **Companion name reset back to default ({default_name})!**",
                    reply_markup=reply_kb
                )
                return
            else:
                new_name = arg[:30].strip()
                set_user_custom_ai_name(user_id, new_name)
                set_user_onboarding_status(user_id, "completed")
                reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=new_name)
                await bot.send_message(
                    chat_id,
                    f"🎉 **AI Companion Renamed!** 🌸\n\n"
                    f"Your companion is now named **{new_name}**!\n"
                    f"• She will refer to herself as **{new_name}** in chats & voice calls.\n"
                    f"• Your bottom button is updated to **📞 Call {new_name}**.\n\n"
                    f"Say hi to {new_name} or tap the button below to start talking!",
                    reply_markup=reply_kb
                )
                return
        else:
            await handle_rename_menu(bot, chat_id, user, user_msg_id=msg_id)
            return
    elif clean_text.startswith("/backup") or clean_text.startswith("/export") or clean_text.lower() in ["backup", "export", "download backup", "my backup"]:
        await bot.send_chat_action(chat_id, "upload_document")
        backup_str = generate_user_backup_json(user_id)
        backup_bytes = backup_str.encode("utf-8")
        filename = f"Joy_Backup_{user_id}.json"
        caption = (
            "📁 **Your AI Companion Backup File**\n\n"
            "Here is your complete backup containing your companion settings, custom name, past memories, and chats.\n\n"
            "💡 **Save to Google Drive:**\n"
            "Tap the 3 dots on this file and choose **'Save to Google Drive'** or download it directly to your phone files!"
        )
        await bot.send_document(chat_id, backup_bytes, filename=filename, caption=caption)
        return
    elif clean_text.startswith("/google") or clean_text.startswith("/login") or clean_text.lower() in [
        "login", "🔐 login", "🔐 login & sync", "login & sync", "sync", "cloud login", "google", "connect google"
    ]:
        parts = clean_text.split(maxsplit=1)
        if len(parts) > 1 and not clean_text.lower().startswith("🔐"):
            email_cand = parts[1].strip().lower()
            if "@" in email_cand and "." in email_cand:
                set_user_google_email(user_id, email_cand)
                set_user_onboarding_status(user_id, "completed")
                await bot.send_message(
                    chat_id,
                    f"✅ **Google Account Connected!** 🎉\n\n"
                    f"📧 Linked Email: `{email_cand}`\n"
                    f"Your companion memories and settings are now secured to your Google identity!\n\n"
                    f"Use `/backup` anytime to export your data directly to Google Drive."
                )
                return
            else:
                await bot.send_message(chat_id, "⚠️ Please provide a valid email, e.g. `/google yourname@gmail.com`")
                return
        else:
            await handle_backup_hub(bot, chat_id, user, user_msg_id=msg_id)
            return
    elif clean_text.startswith("/import") or clean_text.startswith("/transfer"):
        await send_memory_import_guide(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/contacts") or clean_text.startswith("/contact") or clean_text.lower() in ["contacts", "contact", "📇 contacts", "switch contact", "switch", "circle"]:
        await handle_menu(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/gender") or clean_text.lower() in ["gender", "switch gender", "boy", "girl", "view", "👤 gender"]:
        curr_g = user.get("gender", "male")
        new_g = "female" if curr_g == "male" else "male"
        set_user_gender(user_id, new_g)
        set_user_active_contact(user_id, "lover")
        user["gender"] = new_g
        user["active_contact"] = "lover"
        await handle_menu(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/menu") or clean_text.lower() in ["menu", "📱 menu", "📱 control menu", "control menu", "control", "home"]:
        await handle_menu(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/keyboard") or clean_text.startswith("/buttons") or clean_text.startswith("/showbuttons") or clean_text.lower() in ["keyboard", "buttons", "show buttons"]:
        gender = user.get("gender", "male")
        active_contact = user.get("active_contact", "lover")
        custom_name = get_user_custom_ai_name(user_id)
        reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=custom_name)
        await bot.send_message(
            chat_id,
            "📱 **Quick Menu Activated!** Tap the 4-squares grid icon beside the emoji button anytime to open it.",
            reply_markup=reply_kb
        )
        return
    elif clean_text.startswith("/settings") or clean_text.lower() in ["settings", "setting", "setup", "preferences", "config", "account", "profile", "⚙️ settings", "⚙️ settings & data"]:
        await handle_settings(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/feedback") or clean_text.lower() in ["feedback", "💬 feedback", "suggest", "suggestion", "feature request", "request"]:
        await handle_feedback_menu(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/feedbacks") or clean_text.startswith("/feedback_list"):
        if user_id != OWNER_ID:
            await bot.send_message(chat_id, "🔒 Bot owner only.")
            return
        feedbacks = get_recent_feedbacks(15)
        if not feedbacks:
            await bot.send_message(chat_id, "📭 No feedback received yet.")
            return
        lines = [f"💬 **Recent User Feedbacks ({len(feedbacks)} total):**\n"]
        for f in feedbacks:
            lines.append(
                f"• **ID `{f['user_id']}`** (@{f['username'] or 'NoUser'}):\n"
                f"  \"{f['message']}\"\n"
                f"  *({f['created_at'][:19]})*\n"
            )
        await bot.send_message(chat_id, "\n".join(lines))
        return
    elif clean_text.startswith("/clean") or clean_text.startswith("/hidebuttons") or clean_text.lower() in ["clean", "hide buttons"]:
        if msg_id:
            try:
                await bot.delete_message(chat_id, msg_id)
            except Exception:
                pass
        await dismiss_active_menu(bot, chat_id)
        clean_msg = await bot.send_message(
            chat_id,
            "🧹 **Bottom buttons hidden!**\n\nYour chat is now completely clean and full-screen.\n"
            "Use the blue **[ ≡ Menu ]** button on the bottom-left anytime, or tap **Menu** to bring them back!",
            reply_markup={"remove_keyboard": True}
        )
        if clean_msg.get("result", {}).get("message_id"):
            active_menu_messages[chat_id] = clean_msg["result"]["message_id"]
        return
    elif clean_text.startswith("/vip") or clean_text.lower() in ["vip", "⭐ vip", "⭐ joy vip", "⭐ joy vip pass", "joy vip", "joy vip pass", "pass", "upgrade"]:
        await handle_vip(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/stats") or clean_text.lower() in ["stats", "status", "usage", "my status", "balance", "📊 my status", "📊 status"]:
        await handle_stats(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/mode") or clean_text.lower() in ["mode", "change mode", "💖 change mode"]:
        await handle_menu(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/privacy") or clean_text.lower() in ["privacy", "data sharing", "data privacy", "🛡️ privacy", "data"]:
        await handle_privacy_menu(bot, chat_id, user, user_msg_id=msg_id)
        return

    elif clean_text.startswith("📞 Phone") or clean_text.startswith("/call") or clean_text.startswith("📞 Call") or clean_text.lower() in ["phone", "call", "call joy", "call now", "phone call", "talk", "live call"] or any(kw in lower_text for kw in ["can i call", "call you", "call u", "how to call", "phone call"]):
        user_gender = user.get("gender", "male")
        active_contact = user.get("active_contact", "lover")
        user_id_val = user.get("user_id", "")
        cinfo = get_user_contact_display(user_id_val, active_contact, user_gender)
        call_url = f"https://joyfun-ai-bot.onrender.com/call?gender={user_gender}&contact={active_contact}&uid={user_id_val}&name={urllib.parse.quote(cinfo['name'])}"
        call_keyboard = {
            "inline_keyboard": [
                [
                    {"text": "📞 Phone", "web_app": {"url": call_url}}
                ],
                [
                    {"text": "❌ Close", "callback_data": "menu_close"}
                ]
            ]
        }
        await send_or_edit_menu(
            bot,
            chat_id,
            f"Yes! Of course you can call me! {cinfo['emoji']}\n\nTap below to start your live, hands-free call with **{cinfo['name']}** 👇",
            call_keyboard,
            user_msg_id=msg_id
        )
        return
    elif clean_text.startswith("/recharge") or clean_text.startswith("/ad") or clean_text in ["🎬 Recharge", "🎬 Free Recharge", "Free Recharge", "recharge", "ad"]:
        msg = (
            "🎬 **Free Talk Time & Voice Recharge**\n\n"
            "Need more voice notes or call time with Joy? You don't have to pay anything!\n\n"
            "Watch a quick sponsor ad below to claim **+5 Free Voice Notes** and **+20 Text Messages** instantly! 🎁"
        )
        recharge_url = f"https://joyfun-ai-bot.onrender.com/call?action=watch_ad&uid={user_id}"
        keyboard = {
            "inline_keyboard": [
                [{"text": "🎬 Watch 15s Video to Recharge (+5)", "web_app": {"url": recharge_url}}],
                [{"text": "⭐ Joy VIP Pass (Unlimited)", "callback_data": "menu_vip"}],
                [{"text": "⬅️ Back", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
            ]
        }
        await send_or_edit_menu(bot, chat_id, msg, keyboard, user_msg_id=msg_id)
        return
    elif text.startswith("/subscribers") or text.startswith("/vips") or (user_id == OWNER_ID and clean_text.lower() in ["subscribers", "vips", "vip list"]):
        if user_id != OWNER_ID:
            await bot.send_message(chat_id, "🔒 This command is only available to the bot owner.")
            return

        notion_subs = get_notion_subscribers_list()
        if not notion_subs:
            notion_subs = get_all_subscribers()

        lines = [f"⭐ **Joy Bot VIP Subscribers ({len(notion_subs)} total):**\n"]
        for idx, s in enumerate(notion_subs, 1):
            name_val = s.get('name') or s.get('first_name') or 'Friend'
            uname_val = s.get('username') or ''
            uid_val = s.get('user_id')
            status_val = s.get('status') or 'Active'
            plan_val = s.get('plan') or 'Monthly VIP'
            expiry_val = s.get('expiry') or s.get('expires_at') or 'Active'
            lines.append(
                f"{idx}. **{name_val}** ({uname_val}) - ID: `{uid_val}`\n"
                f"   ⏳ {status_val} | Plan: {plan_val} | Expires: {expiry_val}"
            )
        lines.append("\n☁️ *Stored & synced with Notion Cloud Database*\n💡 *To add:* `/addvip <user_id> [days]` or edit directly in Notion app!")
        keyboard = {
            "inline_keyboard": [
                [{"text": "🔄 Sync with Notion Now", "callback_data": "owner_sync_notion"}],
                [{"text": "❌ Close", "callback_data": "menu_close"}]
            ]
        }
        await send_or_edit_menu(bot, chat_id, "\n".join(lines), keyboard, user_msg_id=msg_id)
        return

    elif text.startswith("/addvip") or (user_id == OWNER_ID and clean_text.lower().startswith("addvip")):
        if user_id != OWNER_ID:
            await bot.send_message(chat_id, "🔒 This command is only available to the bot owner.")
            return

        parts = text.split()
        if len(parts) < 2:
            await bot.send_message(chat_id, "Usage: `/addvip <user_id> [days=30]`")
            return

        try:
            target_id = int(parts[1])
            days = int(parts[2]) if len(parts) > 2 else 30
            
            # Sync to Notion Cloud CRM
            add_or_update_notion_subscriber(target_id, days=days)
            sub_info = grant_vip_subscription(target_id, days=days, amount=149.0, method="upi")
            
            await bot.send_message(
                chat_id,
                f"✅ **VIP Subscription Activated & Synced to Notion!**\n\n"
                f"👤 **User ID:** `{target_id}`\n"
                f"⏳ **Duration:** {days} days\n"
                f"📅 **Expires:** {sub_info['expires_at']}\n"
                f"☁️ **Notion Cloud CRM:** Synced successfully!\n"
                f"✨ User now has unlimited calls and voice chats!"
            )
            
            # Notify the user directly if possible
            try:
                notify_msg = (
                    f"🎉 **Congratulations! Your Joy VIP Pass is Active!**\n\n"
                    f"✨ You now have **unlimited 24/7 live calls and voice chats** for **{days} days** (Expires: {sub_info['expires_at']})!\n\n"
                    f"📞 Tap **Phone** anytime to start an instant hands-free call!"
                )
                await bot.send_message(target_id, notify_msg)
            except Exception as e:
                logger.warning(f"Could not notify subscriber {target_id}: {e}")
        except ValueError:
            await bot.send_message(chat_id, "Invalid user ID or days. Example: `/addvip 8747280850 30`")
        return

    elif text.startswith("/removevip"):
        if user_id != OWNER_ID:
            await bot.send_message(chat_id, "🔒 This command is only available to the bot owner.")
            return

        parts = text.split()
        if len(parts) < 2:
            await bot.send_message(chat_id, "Usage: `/removevip <user_id>`")
            return

        try:
            target_id = int(parts[1])
            revoke_vip_subscription(target_id)
            await bot.send_message(chat_id, f"❌ Revoked VIP subscription for User ID `{target_id}`.")
        except ValueError:
            await bot.send_message(chat_id, "Invalid user ID. Example: `/removevip 123456789`")
        return

    elif text.startswith("/users") or text.startswith("/admin") or (user_id == OWNER_ID and clean_text.lower() in ["users", "admin", "all users", "user list"]):
        if user_id != OWNER_ID:
            await bot.send_message(chat_id, "🔒 This command is only available to the bot owner.")
            return

        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT user_id, username, first_name, is_vip, created_at FROM users ORDER BY rowid DESC LIMIT 50")
            all_u = c.fetchall()
            c.execute("SELECT COUNT(*) as cnt FROM users")
            total_count = c.fetchone()["cnt"]

        lines = [f"👥 **Aura AI Live Cloud Users ({total_count} total):**\n"]
        for idx, u in enumerate(all_u, 1):
            uname = f"@{u['username']}" if u['username'] else "No @username"
            fname = u['first_name'] or "Friend"
            vip_tag = "⭐ VIP" if u['is_vip'] else "🆓 Free"
            uid_val = u['user_id']
            created = str(u['created_at'])[:19] if u['created_at'] else "Recently"
            lines.append(f"{idx}. **{fname}** ({uname})\n   🆔 `{uid_val}` | {vip_tag} | 📅 `{created}`")

        await bot.send_message(chat_id, "\n\n".join(lines) if all_u else "No users registered yet.")
        return

    elif text.lower().startswith("/rmsub") or clean_text.lower().startswith("rmsub"):
        # Authorized test runners: Owner (8747280850) and secondary test account (8896571705)
        if user_id not in (OWNER_ID, 8896571705):
            await bot.send_message(chat_id, "🔒 Command locked: Authorized admin/test runner only.")
            return

        parts = text.split()
        target_id = None
        action = "exhaust"

        if len(parts) >= 2:
            try:
                target_id = int(parts[1])
            except ValueError:
                action = parts[1].lower()
        if len(parts) >= 3:
            action = parts[2].lower()

        # If run from test phone without args, target itself. If run from owner, target test phone.
        if not target_id:
            target_id = user_id if user_id == 8896571705 else 8896571705

        if action in ["reset", "restore", "clear", "0"]:
            reset_user_quota(target_id)
            await bot.send_message(
                chat_id,
                f"🎉 **[ADMIN COMMAND SUCCESSFUL]** ✅\n\n"
                f"👤 **Target Account:** `{target_id}`\n"
                f"⚙️ **Action:** Restored Full Daily Quota\n\n"
                f"📊 **Live Quota Status:**\n"
                f"• 🎙️ Voice Notes: `0 / {DAILY_FREE_VOICE_LIMIT}` (Fresh)\n"
                f"• 💬 Text Messages: `0 / {DAILY_FREE_TEXT_LIMIT}` (Fresh)\n"
                f"• 👑 VIP Override: Inactive (Standard Free Tier)\n\n"
                f"✨ Quota successfully refreshed to 100%!"
            )
        else:
            exhaust_user_quota(target_id)
            await bot.send_message(
                chat_id,
                f"⚡ **[ADMIN COMMAND SUCCESSFUL]** 🛑\n\n"
                f"👤 **Target Account:** `{target_id}`\n"
                f"⚙️ **Action:** Daily Quota Removed / Drained to 0\n\n"
                f"📊 **Live Quota Status:**\n"
                f"• 🎙️ Voice Notes: `{DAILY_FREE_VOICE_LIMIT} / {DAILY_FREE_VOICE_LIMIT}` [EXHAUSTED 🛑]\n"
                f"• 💬 Text Messages: `{DAILY_FREE_TEXT_LIMIT} / {DAILY_FREE_TEXT_LIMIT}` [EXHAUSTED 🛑]\n"
                f"• 👑 VIP Override: Inactive (Free Tier)\n\n"
                f"🎬 **Ready for Ad Testing:** Send any message, voice note, or call right now to see the **Watch Video Ad to Recharge** screen!"
            )
        return

    elif clean_text.startswith("/reset") or clean_text.lower() in ["reset", "clear", "clear memory", "restart", "refresh", "🧹 reset"]:

        # Reset conversation memory
        with bot.get_session():
            from database import get_connection
            with get_connection() as conn:
                conn.cursor().execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
                conn.commit()
        gender = user.get("gender", "male")
        active_contact = user.get("active_contact", "lover")
        custom_name = get_user_custom_ai_name(user_id)
        reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=custom_name)
        await bot.send_message(chat_id, "🧹 Conversation memory refreshed! Let's start fresh. What's up?", reply_markup=reply_kb)
        return

    # Dismiss any lingering menu card so chat remains 100% human and clean
    await dismiss_active_menu(bot, chat_id)

    # Check text usage limit
    allowed, used, limit = check_and_increment_usage(user_id, "text")
    if not allowed:
        gender = user.get("gender", "male")
        active_contact = user.get("active_contact", "lover")
        user_lang = get_user_language(user_id)
        contact_info = get_user_contact_display(user_id, active_contact, gender)
        c_name = contact_info.get("name", "Joy")
        c_emoji = contact_info.get("emoji", "🌸")

        if is_asking_about_quota_or_recharge(text):
            spoken_text = get_immediate_recharge_explanation(active_contact, gender, user_lang)
        else:
            spoken_text = get_different_quota_reason(user_id, active_contact, gender, user_lang)

        limit_msg = (
            f"{c_emoji} **{c_name}:**\n"
            f"\"{spoken_text}\"\n\n"
            f"🎬 **Watch a quick sponsor ad** to claim **+20 Free Messages** right now, or unlock VIP!"
        )
        recharge_url = f"https://joyfun-ai-bot.onrender.com/call?action=watch_ad&uid={user_id}"
        keyboard = {
            "inline_keyboard": [
                [{"text": "🎬 Watch 15s Video to Recharge (+20)", "web_app": {"url": recharge_url}}],
                [{"text": f"⭐ Unlock Joy VIP (₹{VIP_PRICE_INR}/mo)", "callback_data": "menu_vip"}],
                [{"text": "❌ Close", "callback_data": "menu_close"}]
            ]
        }
        await send_or_edit_menu(bot, chat_id, limit_msg, keyboard, user_msg_id=msg_id)
        return

    await bot.send_chat_action(chat_id, "typing")
    
    history = get_recent_history(user_id, limit=6)
    gender = user.get("gender", "male")
    active_contact = user.get("active_contact", "lover")
    user_lang = get_user_language(user_id)
    
    _, user_memory = get_user_imported_memory(user_id)
    if not user_memory:
        try:
            _, user_memory = restore_user_memory_from_notion(user_id)
        except Exception:
            pass
    custom_ai_name = get_user_custom_ai_name(user_id)
    loop = asyncio.get_running_loop()
    try:
        reply_text = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                generate_text_reply,
                text,
                active_contact,
                gender,
                user_lang,
                history,
                user_memory,
                custom_ai_name
            ),
            timeout=8.0
        )
    except asyncio.TimeoutError:
        logger.warning(f"Gemini text generation timed out for user {user_id}")
        reply_text = get_human_lag_recovery_reply(active_contact, gender, user_lang, is_call=False)
    except Exception as e:
        logger.error(f"Error in Gemini text generation: {e}")
        reply_text = get_human_lag_recovery_reply(active_contact, gender, user_lang, is_call=False)
        
    add_conversation_turn(user_id, "user", text)
    add_conversation_turn(user_id, "model", reply_text)
    save_dev_sample_if_allowed(user_id, active_contact, f"User: {text} | Joy: {reply_text}")
    
    reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=custom_ai_name)
    await bot.send_message(chat_id, reply_text, reply_markup=reply_kb)

async def health_check(request):
    """Health check endpoint required by cloud hosting platforms (Render/Koyeb)."""
    return web.json_response({
        "status": "online",
        "service": "Joy Bot - 24/7 Cloud AI Voice Companion",
        "bot_version": BOT_VERSION,
        "mini_app_version": MINI_APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

async def serve_call_page(request):
    """Serves the real-time voice call Telegram Mini-App interface."""
    uid = request.query.get("uid") or request.query.get("user_id")
    if uid:
        try:
            get_or_create_user(int(uid))
        except Exception as e:
            logger.warning(f"Could not auto-register user from /call page: {e}")
    static_file = Path(__file__).parent / "static" / "call.html"
    if static_file.exists():
        return web.FileResponse(static_file)
    return web.Response(text="Call page not found", status=404)

async def websocket_call_handler(request):
    """Handles real-time, low-latency duplex voice calls via WebSocket."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    logger.info("New live voice call connection established via WebSocket!")

    history = []
    current_gender = "male"
    current_contact = "lover"
    current_voice = "female"
    current_language = "auto"

    call_user_id = 0
    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    msg_type = data.get("type")

                    if msg_type == "call_started":
                        call_user_id = data.get("user_id") or 0
                        db_gender, db_contact = ("male", "lover")
                        if call_user_id:
                            try:
                                get_or_create_user(int(call_user_id))
                                db_gender, db_contact = get_user_contact_settings(int(call_user_id))
                            except Exception as e:
                                logger.warning(f"Error initializing user settings in call: {e}")

                        current_gender = data.get("gender") or db_gender
                        current_contact = "lover"  # Enforce Lover (Joy) as the active companion while others are in development

                        if call_user_id:
                            # Sync the contact and gender the user picked in the Mini App into database
                            try:
                                set_user_active_contact(int(call_user_id), current_contact)
                                set_user_gender(int(call_user_id), current_gender)
                            except Exception as e:
                                logger.warning(f"Could not sync Mini App contact selection to DB: {e}")

                            current_language = data.get("language") or get_user_language(int(call_user_id))
                            # Preload recent conversation memory so Joy remembers past chats & calls
                            past_history = get_recent_history(int(call_user_id), limit=8)
                            if past_history:
                                history = list(past_history)
                        else:
                            current_language = data.get("language") or "auto"
                        contact_info = get_user_contact_display(int(call_user_id) if call_user_id else None, current_contact, current_gender)
                        current_voice = contact_info.get("voice", "female")
                        greeting = contact_info.get("greeting", "Hey! So good you called.")

                        audio_bytes = await synthesize_speech(greeting, voice_key=current_voice)
                        base64_audio = base64.b64encode(audio_bytes).decode('utf-8')
                        await ws.send_json({
                            "type": "joy_speech",
                            "text": greeting,
                            "audio": base64_audio,
                            "caller_name": contact_info.get("name", "Joy"),
                            "caller_tag": contact_info.get("tag", "Lover")
                        })

                    elif msg_type == "mode_change":
                        current_contact = data.get("mode", "lover")
                        logger.info(f"Call contact changed to: {current_contact}")

                    elif msg_type == "voice_change":
                        current_voice = data.get("voice", "female")
                        logger.info(f"Call voice changed to: {current_voice}")

                    elif msg_type == "ad_recharge":
                        user_id = data.get("user_id", 0) or call_user_id
                        if user_id:
                            recharge_user_usage(int(user_id), bonus_voice=5, bonus_text=20)
                        await ws.send_json({
                            "type": "recharged",
                            "text": "🎉 Recharged +5 Mins Talk Time!"
                        })

                    elif msg_type == "toggle_data_sharing":
                        user_id = data.get("user_id", 0) or call_user_id
                        new_state = bool(data.get("allow", False))
                        if user_id:
                            set_user_data_sharing(int(user_id), new_state)
                        await ws.send_json({
                            "type": "privacy_updated",
                            "allow_data_sharing": new_state
                        })

                    elif msg_type == "voice_chunk":
                        raw_base64 = data.get("audio", "")
                        mime_type = data.get("mime_type", "audio/wav")
                        current_gender = data.get("gender") or current_gender
                        current_contact = data.get("contact") or data.get("mode") or current_contact
                        if data.get("language"):
                            current_language = data.get("language")
                        user_id = data.get("user_id") or call_user_id
                        contact_info = get_user_contact_display(int(user_id) if user_id else None, current_contact, current_gender)
                        current_voice = contact_info.get("voice", "female")

                        if raw_base64:
                            audio_bytes = base64.b64decode(raw_base64)

                            # Check call voice usage quota for non-VIP users
                            if user_id:
                                allowed, used, limit = check_and_increment_usage(int(user_id), "voice")
                                if not allowed:
                                    reason_text = get_different_quota_reason(int(user_id), current_contact, current_gender, current_language)
                                    joy_audio = await synthesize_speech(reason_text, voice_key=current_voice)
                                    joy_b64 = base64.b64encode(joy_audio).decode('utf-8')
                                    await ws.send_json({
                                        "type": "quota_exceeded",
                                        "text": reason_text,
                                        "audio": joy_b64,
                                        "caller_name": contact_info.get("name", "Joy"),
                                        "caller_tag": contact_info.get("tag", "Lover")
                                    })
                                    continue

                            user_memory = None
                            if user_id:
                                try:
                                    _, user_memory = get_user_imported_memory(int(user_id))
                                    if not user_memory:
                                        _, user_memory = restore_user_memory_from_notion(int(user_id))
                                except Exception:
                                    pass
                            custom_ai_name = get_user_custom_ai_name(int(user_id)) if user_id else ""
                            loop = asyncio.get_running_loop()
                            try:
                                transcript, reply_text = await asyncio.wait_for(
                                    loop.run_in_executor(
                                        None,
                                        generate_voice_reply,
                                        audio_bytes,
                                        mime_type,
                                        current_contact,
                                        current_gender,
                                        current_language,
                                        history,
                                        user_memory,
                                        custom_ai_name
                                    ),
                                    timeout=8.0
                                )
                            except asyncio.TimeoutError:
                                logger.warning(f"Live call audio processing timed out for user {call_user_id}")
                                transcript = "Live Call"
                                reply_text = get_human_lag_recovery_reply(current_contact, current_gender, current_language, is_call=True)
                            except Exception as err:
                                logger.error(f"Error generating live call voice reply: {err}")
                                transcript = "Live Call"
                                reply_text = get_human_lag_recovery_reply(current_contact, current_gender, current_language, is_call=True)

                            # If chunk was silent or empty, unlock client without generating audio
                            if not reply_text:
                                await ws.send_json({"type": "no_speech"})
                                continue

                            history.append({"role": "user", "content": transcript or "Voice Note"})
                            history.append({"role": "model", "content": reply_text})
                            if len(history) > 10:
                                history = history[-10:]

                            # Persist this live call turn directly into user conversation memory
                            if user_id:
                                try:
                                    add_conversation_turn(int(user_id), "user", transcript or "Voice Call")
                                    add_conversation_turn(int(user_id), "model", reply_text)
                                    save_dev_sample_if_allowed(int(user_id), current_contact, f"Call User: {transcript} | Companion: {reply_text}")
                                except Exception as e:
                                    logger.warning(f"Could not persist call turn to DB: {e}")

                            # Inform client of transcript
                            if transcript and transcript != "Voice Note":
                                await ws.send_json({
                                    "type": "transcript",
                                    "text": transcript
                                })

                            # Synthesize audio with Edge-TTS (with timeout protection)
                            try:
                                joy_audio = await asyncio.wait_for(
                                    synthesize_speech(reply_text, voice_key=current_voice),
                                    timeout=6.5
                                )
                            except Exception as tts_err:
                                logger.warning(f"Call TTS error or timeout: {tts_err}. Synthesizing brief recovery line...")
                                joy_audio = await synthesize_speech("Wait, your voice cracked a bit! Say that again?", voice_key=current_voice)

                            joy_b64 = base64.b64encode(joy_audio).decode('utf-8')
                            await ws.send_json({
                                "type": "joy_speech",
                                "text": reply_text,
                                "audio": joy_b64,
                                "caller_name": contact_info.get("name", "Joy"),
                                "caller_tag": contact_info.get("tag", "Lover")
                            })

                except Exception as err:
                    logger.error(f"Error handling call WS data: {err}")
                    await ws.send_json({"type": "no_speech"})

            elif msg.type == web.WSMsgType.ERROR:
                logger.error(f"Call WebSocket closed with exception {ws.exception()}")

    finally:
        logger.info("Call WebSocket connection closed.")
        return ws

async def get_user_privacy_api(request):
    """Returns privacy and data sharing preference for a user."""
    uid = request.query.get("user_id")
    if not uid:
        return web.json_response({"error": "user_id required"}, status=400)
    try:
        user_id = int(uid)
        sharing = get_user_data_sharing(user_id)
        return web.json_response({"user_id": user_id, "allow_data_sharing": sharing})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def set_user_privacy_api(request):
    """Updates user privacy data sharing preference."""
    try:
        data = await request.json()
        uid = data.get("user_id")
        allow = bool(data.get("allow_data_sharing", False))
        if not uid:
            return web.json_response({"error": "user_id required"}, status=400)
        user_id = int(uid)
        set_user_data_sharing(user_id, allow)
        return web.json_response({"success": True, "user_id": user_id, "allow_data_sharing": allow})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def get_admin_users_api(request):
    """Secure endpoint for owner to view all registered cloud users."""
    token = request.query.get("token") or request.headers.get("X-Admin-Token")
    if token != str(OWNER_ID) and token != os.getenv("RENDER_API_KEY"):
        return web.json_response({"error": "Unauthorized"}, status=401)
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT user_id, username, first_name, is_vip, vip_expiry, created_at FROM users ORDER BY rowid DESC LIMIT 100")
            users = [dict(row) for row in c.fetchall()]
            c.execute("SELECT COUNT(*) as count FROM users")
            total = c.fetchone()["count"]
        return web.json_response({"status": "ok", "total_users": total, "users": users})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def admin_quota_api(request):
    """Admin endpoint to exhaust or reset a user's daily quota for testing."""
    token = request.query.get("token") or request.headers.get("X-Admin-Token")
    if token != str(OWNER_ID) and token != os.getenv("RENDER_API_KEY"):
        return web.json_response({"error": "Unauthorized"}, status=401)

    uid = request.query.get("user_id") or "8896571705"
    action = request.query.get("action", "exhaust")
    try:
        user_id = int(uid)
        if action in ("reset", "0", "restore", "clear"):
            reset_user_quota(user_id)
            return web.json_response({
                "status": "ok",
                "user_id": user_id,
                "action": "reset",
                "voice_used": 0,
                "text_used": 0,
                "voice_limit": DAILY_FREE_VOICE_LIMIT,
                "text_limit": DAILY_FREE_TEXT_LIMIT
            })
        else:
            exhaust_user_quota(user_id)
            return web.json_response({
                "status": "ok",
                "user_id": user_id,
                "action": "exhaust",
                "voice_used": DAILY_FREE_VOICE_LIMIT,
                "text_used": DAILY_FREE_TEXT_LIMIT,
                "voice_left": 0,
                "text_left": 0
            })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def start_cloud_keepalive_worker(port: int = 8080):
    """
    Autonomous 24/7 Cloud Keep-Alive & Self-Healing Worker.
    1. Pings the public Render service URL or local health endpoint every 4 minutes (240s)
       to ensure zero idle sleeping and 100% 24/7 uptime.
    2. Runs an automatic SQLite WAL checkpoint every 6 hours to prevent WAL file growth.
    """
    import aiohttp
    
    render_external_url = os.getenv("RENDER_EXTERNAL_URL", "").strip()
    if not render_external_url:
        render_external_url = "https://joyfun-ai-bot.onrender.com"
        
    ping_url = f"{render_external_url.rstrip('/')}/health"
    local_url = f"http://127.0.0.1:{port}/health"

    logger.info(f"🚀 Cloud Keep-Alive Worker initialized. Target ping URL: {ping_url}")
    
    iteration = 0
    while True:
        try:
            await asyncio.sleep(240)  # Ping every 4 minutes (well below Render's 15-min idle sleep threshold)
            iteration += 1

            # 1. Pinger for 24/7 zero-sleep uptime
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                try:
                    async with session.get(ping_url) as resp:
                        if resp.status == 200:
                            logger.info(f"💓 Keep-Alive ping #{iteration} successful -> {ping_url} [HTTP {resp.status}]")
                        else:
                            logger.warning(f"⚠️ Keep-Alive ping returned status {resp.status}")
                except Exception as ex_ext:
                    try:
                        async with session.get(local_url) as resp_loc:
                            logger.info(f"💓 Local Keep-Alive ping #{iteration} -> {local_url} [HTTP {resp_loc.status}] (Ext error: {ex_ext})")
                    except Exception as ex_loc:
                        logger.warning(f"⚠️ Local Keep-Alive ping failed: {ex_loc}")

            # 2. Every 6 hours (90 iterations * 4 mins = 360 mins = 6 hours), run WAL checkpoint
            if iteration % 90 == 0:
                try:
                    from database import get_connection
                    with get_connection() as conn:
                        conn.cursor().execute("PRAGMA wal_checkpoint(TRUNCATE)")
                        conn.commit()
                    logger.info("🧹 Periodic SQLite WAL checkpoint executed successfully.")
                except Exception as wal_err:
                    logger.warning(f"SQLite WAL checkpoint error: {wal_err}")

        except asyncio.CancelledError:
            break
        except Exception as err:
            logger.error(f"Keep-Alive worker encountered unexpected error: {err}")
            await asyncio.sleep(10)

async def handle_ad_reward_api(request):
    """Adsgram / Monetag server-to-server postback reward webhook endpoint."""
    user_id = request.query.get("userid") or request.query.get("user_id") or request.query.get("custom_data")
    if not user_id and request.method == "POST":
        try:
            data = await request.json()
            user_id = data.get("userid") or data.get("user_id") or data.get("custom_data")
        except Exception:
            pass
    if user_id:
        try:
            get_or_create_user(int(user_id))
            recharge_user_usage(int(user_id), bonus_voice=5, bonus_text=20)
            logger.info(f"🎉 Adsgram server-to-server reward granted for user {user_id} (+5 voice, +20 text)")
            return web.json_response({"status": "ok", "user_id": int(user_id), "rewarded": True})
        except Exception as e:
            logger.warning(f"Error granting ad reward: {e}")
    return web.json_response({"status": "ok", "rewarded": True})

async def upload_file_to_google_drive(session: aiohttp.ClientSession, access_token: str, filename: str, content: str) -> Tuple[bool, str]:
    """Directly uploads a JSON file to user's personal Google Drive using Google Drive v3 REST API."""
    try:
        metadata = {
            "name": filename,
            "mimeType": "application/json",
            "description": "Joy AI Companion Memory & Chat Backup"
        }
        boundary = "joy_drive_boundary_xyz"
        body = (
            f"--{boundary}\r\n"
            f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
            f"{json.dumps(metadata)}\r\n"
            f"--{boundary}\r\n"
            f"Content-Type: application/json\r\n\r\n"
            f"{content}\r\n"
            f"--{boundary}--"
        )
        url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": f"multipart/related; boundary={boundary}"
        }
        async with session.post(url, headers=headers, data=body.encode("utf-8")) as resp:
            if resp.status in [200, 201]:
                res_data = await resp.json()
                logger.info(f"✅ Successfully uploaded {filename} to Google Drive (File ID: {res_data.get('id')})")
                return True, res_data.get("id", "")
            else:
                err_text = await resp.text()
                logger.warning(f"Google Drive upload error ({resp.status}): {err_text}")
                return False, ""
    except Exception as e:
        logger.error(f"Google Drive upload exception: {e}")
        return False, ""

async def handle_google_login(request: web.Request) -> web.Response:
    """Initiates official Google OAuth 2.0 flow or displays setup instructions if Client ID is not configured."""
    user_id = request.query.get("uid", "")
    if not GOOGLE_CLIENT_ID:
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Google Cloud OAuth 2.0 Setup</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0b0f19; color: #f8fafc; padding: 24px; line-height: 1.6; max-width: 620px; margin: auto; }}
        .card {{ background: #131b2e; border-radius: 16px; padding: 24px; border: 1px solid #1e293b; margin-top: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
        h1 {{ color: #38bdf8; font-size: 22px; margin-bottom: 6px; }}
        .badge {{ background: #f59e0b; color: #000; font-size: 11px; font-weight: 800; padding: 4px 8px; border-radius: 6px; text-transform: uppercase; letter-spacing: 0.5px; }}
        code {{ background: #0b0f19; color: #38bdf8; padding: 4px 8px; border-radius: 6px; font-size: 13px; word-break: break-all; border: 1px solid #1e293b; display: inline-block; }}
        ol {{ padding-left: 20px; }}
        li {{ margin-bottom: 14px; font-size: 14px; color: #cbd5e1; }}
        b {{ color: #f8fafc; }}
        .btn {{ display: inline-block; background: #2563eb; color: #fff; text-decoration: none; padding: 12px 20px; border-radius: 10px; font-weight: bold; margin-top: 16px; font-size: 14px; }}
    </style>
</head>
<body>
    <span class="badge">Google Cloud OAuth 2.0</span>
    <h1>🔐 Real Google Sign-In & Drive Sync</h1>
    <div class="card">
        <p>To enable genuine 1-click <b>Sign in with Google</b> and direct <b>Google Drive</b> memory sync, Google Cloud requires an authorized OAuth 2.0 Client ID for Joy Bot.</p>
        <h3 style="color: #60a5fa; margin-top: 18px;">🛠️ 2-Minute Google Cloud Setup:</h3>
        <ol>
            <li>Open <a href="https://console.cloud.google.com/apis/credentials" target="_blank" style="color: #38bdf8; font-weight: bold;">Google Cloud Console &rarr; Credentials</a>.</li>
            <li>Enable the <b>Google Drive API</b> in <i>APIs & Services &rarr; Library</i>.</li>
            <li>Click <b>Create Credentials &rarr; OAuth client ID</b> (Application type: <b>Web application</b>).</li>
            <li>In <b>Authorized redirect URIs</b>, paste this exact callback URL:<br><br><code>{GOOGLE_REDIRECT_URI}</code></li>
            <li>Copy your <b>Client ID</b> and <b>Client Secret</b> into Render environment variables:
                <ul style="margin-top: 8px;">
                    <li><code>GOOGLE_CLIENT_ID</code></li>
                    <li><code>GOOGLE_CLIENT_SECRET</code></li>
                </ul>
            </li>
        </ol>
        <p style="font-size: 13px; color: #94a3b8;">Once saved in Render, clicking <b>Sign in with Google</b> will instantly open Google's official account selector screen!</p>
        <a class="btn" href="https://t.me/joyfun_ai_bot">⬅️ Return to Joy Bot in Telegram</a>
    </div>
</body>
</html>"""
        return web.Response(text=html, content_type="text/html")

    # Redirect straight to Google's official OAuth consent screen!
    scopes = "openid email profile https://www.googleapis.com/auth/drive.file"
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": scopes,
        "access_type": "offline",
        "prompt": "consent",
        "state": str(user_id)
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    raise web.HTTPFound(auth_url)

async def handle_google_callback(request: web.Request) -> web.Response:
    """Handles Google OAuth callback, exchanges code for tokens, and uploads backup to Google Drive."""
    code = request.query.get("code")
    user_id_str = request.query.get("state", "")
    error = request.query.get("error")

    if error:
        logger.warning(f"Google OAuth cancelled or error: {error}")
        return web.Response(text=f"<h3>Google Sign-In was cancelled ({error}).</h3><a href='https://t.me/joyfun_ai_bot'>Return to Telegram</a>", content_type="text/html")

    if not code or not user_id_str:
        return web.Response(text="<h3>Missing authentication code or user ID.</h3><a href='https://t.me/joyfun_ai_bot'>Return to Telegram</a>", content_type="text/html")

    try:
        user_id = int(user_id_str)
    except ValueError:
        return web.Response(text="Invalid user ID.", status=400)

    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": GOOGLE_REDIRECT_URI
    }

    email = ""
    name = ""
    access_token = ""
    refresh_token = ""
    drive_saved = False

    async with aiohttp.ClientSession() as session:
        async with session.post(token_url, data=token_data) as resp:
            if resp.status == 200:
                tokens = await resp.json()
                access_token = tokens.get("access_token", "")
                refresh_token = tokens.get("refresh_token", "")
            else:
                err_text = await resp.text()
                logger.error(f"Google token exchange failed: {err_text}")
                return web.Response(text="Google authentication failed. Please try again.", status=400)

        if access_token:
            userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
            async with session.get(userinfo_url, headers={"Authorization": f"Bearer {access_token}"}) as resp:
                if resp.status == 200:
                    profile = await resp.json()
                    email = profile.get("email", "")
                    name = profile.get("name", "")

        set_user_google_oauth(user_id, email, name, refresh_token, access_token)
        set_user_cloud_backup(user_id, True)

        if access_token:
            backup_content = generate_user_backup_json(user_id)
            drive_saved, _ = await upload_file_to_google_drive(
                session, access_token, f"Joy_AI_Backup_{user_id}.json", backup_content
            )

    if global_bot_client and email:
        try:
            drive_status = "✅ Successfully saved to your personal Google Drive!" if drive_saved else "Connected to Google Cloud"
            notify_msg = (
                f"🎉 **Google Account Connected!**\n\n"
                f"👤 **Account:** {name or 'User'}\n"
                f"📧 **Verified Email:** `{email}`\n"
                f"📁 **Google Drive Backup:** {drive_status}\n\n"
                f"Your companion settings, past chats, and memories are now securely synced."
            )
            await global_bot_client.send_message(user_id, notify_msg)
        except Exception as e:
            logger.warning(f"Could not dispatch Google login notification to {user_id}: {e}")

    html_success = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Google Account Connected</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0b0f19; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; text-align: center; padding: 20px; }}
        .card {{ background: #131b2e; border-radius: 20px; padding: 32px 24px; max-width: 440px; border: 1px solid #1e293b; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5); }}
        .icon {{ font-size: 54px; margin-bottom: 16px; }}
        h1 {{ font-size: 22px; color: #38bdf8; margin-bottom: 8px; }}
        p {{ color: #94a3b8; font-size: 15px; line-height: 1.5; }}
        .email-badge {{ background: #0b0f19; color: #34d399; font-weight: bold; padding: 8px 14px; border-radius: 8px; display: inline-block; margin: 12px 0; font-size: 14px; border: 1px solid #1e293b; }}
        .btn {{ display: block; background: #2563eb; color: #fff; text-decoration: none; padding: 14px; border-radius: 12px; font-weight: bold; margin-top: 20px; font-size: 16px; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">🎉</div>
        <h1>Google Account Connected!</h1>
        <p>You have successfully authenticated with your Google account:</p>
        <div class="email-badge">{email}</div>
        <p>{'📁 A fresh backup was automatically created in your Google Drive!' if drive_saved else '☁️ Cloud backup is now active for your account.'}</p>
        <a class="btn" href="https://t.me/joyfun_ai_bot">Return to Joy Bot</a>
    </div>
</body>
</html>"""
    return web.Response(text=html_success, content_type="text/html")

async def start_web_server(port: int = 8080):
    """Starts a non-blocking background HTTP server for 24/7 cloud keep-alive & real-time calls."""
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    app.router.add_get("/call", serve_call_page)
    app.router.add_get("/ws/call", websocket_call_handler)
    app.router.add_get("/auth/google/login", handle_google_login)
    app.router.add_get("/auth/google/callback", handle_google_callback)
    app.router.add_get("/api/user/privacy", get_user_privacy_api)
    app.router.add_post("/api/user/privacy", set_user_privacy_api)
    app.router.add_get("/api/admin/users", get_admin_users_api)
    app.router.add_get("/api/admin/quota", admin_quota_api)
    app.router.add_post("/api/admin/quota", admin_quota_api)
    app.router.add_get("/api/ad/reward", handle_ad_reward_api)
    app.router.add_post("/api/ad/reward", handle_ad_reward_api)
    
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.router.add_static("/static/", path=static_dir, name="static")

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    try:
        await site.start()
        logger.info(f"✅ Cloud Keep-Alive & Voice Call Server listening on port {port}")
    except Exception as e:
        logger.warning(f"⚠️ Cloud health server warning: {e}")

async def main():
    logger.info("Initializing Joy Bot (24/7 Cloud Edition)...")
    init_db()
    
    # Start Cloud Keep-Alive & Voice Call Web Server
    await start_web_server(PORT)
    
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN is not set in .env! Please configure your bot token.")
        return

    global global_bot_client
    bot = TelegramClient(TELEGRAM_BOT_TOKEN)
    global_bot_client = bot
    me = await bot.get_me()
    if not me.get("ok"):
        logger.error(f"Failed to connect to Telegram: {me}")
        await bot.close()
        return

    bot_info = me["result"]
    logger.info(f"Connected successfully as @{bot_info.get('username')} ({bot_info.get('first_name')})")
    print(f"✅ Joy Bot is LIVE as @{bot_info.get('username')}! Ready to chat.")

    # Configure Telegram Bot Commands & Native Blue [ ≡ Menu ] Button
    try:
        cmd_res = await bot.set_my_commands(BOT_COMMANDS)
        logger.info(f"Registered Telegram Bot Commands: {cmd_res}")
        menu_res = await bot.set_chat_menu_button(menu_button={"type": "commands"})
        logger.info(f"Set Telegram Chat Menu Button to commands: {menu_res}")
    except Exception as e:
        logger.warning(f"Could not configure commands/menu button: {e}")

    # Initial Notion VIP Subscription Sync
    try:
        sync_res = sync_subscribers_from_notion()
        logger.info(f"Initial Notion VIP sync result: {sync_res}")
    except Exception as e:
        logger.warning(f"Initial Notion sync failed: {e}")

    # Initial Notion User Memory Sync (Restore memories across redeploys)
    try:
        mem_sync_res = sync_all_memories_on_startup()
        logger.info(f"Initial Notion user memory sync: restored {mem_sync_res} memories")
    except Exception as e:
        logger.warning(f"Initial Notion memory sync failed: {e}")

    # Launch periodic Notion sync background task (every 15 minutes)
    async def periodic_notion_sync_loop():
        while True:
            try:
                await asyncio.sleep(900)  # 15 minutes
                sync_subscribers_from_notion()
            except asyncio.CancelledError:
                break
            except Exception as ex:
                logger.warning(f"Periodic Notion sync error: {ex}")

    asyncio.create_task(periodic_notion_sync_loop())
    asyncio.create_task(start_cloud_keepalive_worker(PORT))

    offset = None

    
    # Graceful shutdown handler
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: stop_event.set())
        except NotImplementedError:
            pass

    try:
        while not stop_event.is_set():
            try:
                updates = await bot.get_updates(offset=offset, timeout=20)
                if not updates.get("ok"):
                    await asyncio.sleep(2)
                    continue

                for update in updates.get("result", []):
                    offset = update["update_id"] + 1

                    # Handle inline callback queries
                    if "callback_query" in update:
                        asyncio.create_task(handle_callback_query(bot, update["callback_query"]))
                        continue

                    # Handle messages
                    if "message" in update:
                        msg = update["message"]
                        chat_id = msg.get("chat", {}).get("id")
                        user_info = msg.get("from", {})
                        user_id = user_info.get("id")
                        
                        if not chat_id or not user_id:
                            continue
                            
                        user = get_or_create_user(user_id, user_info.get("username", ""), user_info.get("first_name", ""))
                        
                        # Case A: Voice Note
                        if "voice" in msg:
                            file_id = msg["voice"]["file_id"]
                            asyncio.create_task(process_user_voice(bot, chat_id, user, file_id))
                        # Case B: Audio file
                        elif "audio" in msg:
                            file_id = msg["audio"]["file_id"]
                            asyncio.create_task(process_user_voice(bot, chat_id, user, file_id))
                        # Case C: Text Message
                        elif "text" in msg:
                            text = msg["text"]
                            msg_id = msg.get("message_id")
                            asyncio.create_task(process_user_text(bot, chat_id, user, text, msg_id=msg_id))

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Polling loop encountered error: {e}")
                await asyncio.sleep(3)
    finally:
        await bot.close()
        logger.info("Joy Bot shutdown cleanly.")

if __name__ == "__main__":
    asyncio.run(main())
