"""
Joy Bot - Main Application Engine
Your AI Voice Companion & English Practice Friend on Telegram.
"""

import os
import re
import sys
import json
import base64
import asyncio
import logging
import signal
import urllib.parse
import secrets
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
import resource
from datetime import datetime, timezone, timedelta
import aiohttp
from aiohttp import web

from config import (
    TELEGRAM_BOT_TOKEN,
    GEMINI_API_KEY,
    OWNER_ID,
    PORT,
    DAILY_FREE_VOICE_LIMIT,
    DAILY_FREE_TEXT_LIMIT,
    DAILY_FREE_AI_CALL_LIMIT,
    DAILY_FREE_REAL_CALL_LIMIT,
    DAILY_FREE_REAL_CHAT_LIMIT,
    VIP_PRICE_INR,
    UPI_ID,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
    BOT_VERSION,
    MINI_APP_VERSION,
    SECURITY_VERSION,
    LAST_UPDATE_DATE,
    RENDER_API_KEY,
    RENDER_SERVICE_ID
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
    get_user_full_quota_status,
    increment_user_ai_call,
    increment_user_real_call,
    increment_user_real_chat,
    exhaust_user_quota,
    reset_user_quota,
    set_user_data_sharing,
    get_user_data_sharing,
    is_contributor_discount_locked,
    set_user_country,
    get_user_country,
    get_country_display,
    COUNTRIES,
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
    get_recent_feedbacks,
    register_user_email,
    authenticate_user_email,
    record_api_call,
    get_today_api_metrics,
    track_user_referral,
    complete_referral_reward,
    get_referral_stats,
    register_mask_mapping,
    get_user_id_by_mask,
    get_mask_by_user_id,
    block_peer,
    is_peer_blocked,
    get_blocked_peers,
    update_user_streak,
    get_user_streak_info,
    get_eligible_proactive_users,
    mark_user_proactive_sent,
    record_utr_submission,
    get_payment_request,
    approve_payment_request,
    reject_payment_request
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
    generate_vision_reply,
    get_human_boundary_reply,
    get_human_lag_recovery_reply,
    humanize_ai_response
)
from companion_images import (
    detect_image_request,
    get_companion_image
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
    {"command": "start", "description": "✨ Chat with Joy"},
    {"command": "chat", "description": "👥 Chat with Real People (Anonymous)"},
    {"command": "study", "description": "📚 Study Buddy & Active Recall Quizzer"},
    {"command": "menu", "description": "📱 Open Interactive Menu & Settings"},
    {"command": "stats", "description": "📊 Daily Usage, Quota & Streak 🔥"},
    {"command": "refer", "description": "🎁 Invite Friends & Earn Free VIP"},
    {"command": "tip", "description": "⭐ Tip / Send Stars Gift"},
    {"command": "feedback", "description": "💬 Send Feedback & Feature Requests"},
    {"command": "reset", "description": "🧹 Clear Conversation Memory"},
    {"command": "clean", "description": "🧹 Hide Bottom Buttons (Clean Chat)"}
]

ICEBREAKER_QUESTIONS = [
    "If you could drop out of college right now and start any business, what would it be?",
    "What is the single most overrated movie or food of all time?",
    "What is one secret obsession or hobby that none of your college friends know about?",
    "If you won a free round-trip flight ticket to anywhere in the world tonight, where are you flying?",
    "What's that one song you listen to on repeat that you'd be embarrassed to play out loud?",
    "Tea (Chai) or Coffee? And what's your go-to late-night comfort snack?",
    "Engineering, arts, medical, or job: How would you describe your everyday life in 3 words?",
    "If you were given ₹1 Crore with one rule: you must spend it all in 24 hours without buying land or gold, what are you buying?",
    "Which superpower would you pick: Teleportation, Invisibility, or Reading Minds?",
    "What is the funniest or most awkward thing that ever happened to you in school or college?",
    "What is a major red flag in friendship that makes you distance yourself immediately?",
    "If your life right now was a movie, what would the title be?",
    "What is one dream goal you are secretly working super hard for right now?",
    "Are you an early bird or a 2 AM night owl? What usually keeps you awake at night?",
    "What's the best piece of life advice someone gave you that you actually followed?",
    "What was the most ridiculous lie you believed as a kid that turned out to be fake?",
    "If you could have dinner with anyone dead or alive for 1 hour, who would you choose?",
    "What is that one movie you can watch 100 times without ever getting bored?",
    "If you had to survive a zombie apocalypse, which one person or character are you taking with you?",
    "What's your biggest pet peeve that annoys you instantly?",
    "What is one skill you wish they taught in school or college instead of rote memorization?",
    "Solo trips or travelling with a loud group of friends? Where is your dream road trip?"
]

# Legal and Privacy Disclaimers for PII & Media Guard
LEGAL_DISCLAIMER_TEXT = "⚖️ **Legal Disclaimer:** *Not responsible for personal data shared.*"
PRIVACY_WARNING_TEXT = '🛡️ **Privacy Warning:** *"Your privacy is your personal power—once exposed online, it can never be retrieved. Protect your identity."*'

def detect_sensitive_pii(text: str) -> tuple[bool, str]:
    """
    Scans text for sensitive Personally Identifiable Information (PII) before sending:
    - Phone numbers (10+ digits, Indian/international formats, spaced digits)
    - Email addresses
    - Social media handles / direct messaging links (WhatsApp, Telegram, Instagram, Snapchat, etc.)
    - Identity documents (Aadhaar, PAN)
    Returns (True, violation_reason) if sensitive PII is detected, else (False, "").
    """
    if not text:
        return False, ""
    
    clean = text.strip()

    # 1. Email check
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    if re.search(email_pattern, clean):
        return True, "Email Address"

    # 2. Indian & International Phone Numbers (10-15 digits, mobile prefixes)
    digits_only = re.sub(r'[^\d]', '', clean)
    phone_pattern = r'(?:(?:\+|00)\d{1,3}[\s.-]?)?(?:\(?\d{2,5}\)?[\s.-]?)?\d{3,5}[\s.-]?\d{4,5}'
    if re.search(r'\b[6-9]\d{9}\b', clean) or re.search(r'\b(?:\+91|91)[\s-]?[6-9]\d{9}\b', clean):
        return True, "Phone / Mobile Number"
    if 10 <= len(digits_only) <= 13 and re.search(phone_pattern, clean):
        return True, "Phone Number"

    # 3. Social Media handles and direct messaging links
    social_pattern = r'(?:instagram\.com/|snapchat\.com/|t\.me/|telegram\.me/|wa\.me/|facebook\.com/|fb\.com/|wa\.link/|chat\.whatsapp\.com/)'
    if re.search(social_pattern, clean, flags=re.IGNORECASE):
        return True, "Social Media Profile Link"

    # 4. Standalone @username handle (exclude internal system mentions)
    handle_match = re.findall(r'@([a-zA-Z0-9_]{4,32})', clean)
    for handle in handle_match:
        if handle.lower() not in ["joy_fun_ai_bot", "joyfun_ai_bot", "joy", "here", "everyone", "channel"]:
            return True, "Social Media Username / Handle"

    # 5. Aadhaar Number (12 digits, often formatted in 4-4-4)
    if re.search(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', clean):
        return True, "National ID (Aadhaar Number)"

    # 6. PAN Card (5 letters, 4 digits, 1 letter)
    if re.search(r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b', clean, flags=re.IGNORECASE):
        return True, "Tax / Identity Card (PAN Number)"

    return False, ""

def get_persistent_reply_keyboard(gender: str = "male", active_contact: str = "lover", custom_name: str = "") -> dict:
    """Returns a docked, compact keyboard at the bottom of the chat for fast access beside emoji button."""
    return {
        "keyboard": [
            [{"text": "📞 Phone Calls"}, {"text": "👥 Chat Real People"}],
            [{"text": "📱 Menu"}, {"text": "⚙️ Settings"}]
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

# Concurrency & Overload Protection Semaphores (Render 0.1 vCPU safe guard)
AI_CALL_SEMAPHORE = asyncio.Semaphore(15)
VOICE_CALL_SEMAPHORE = asyncio.Semaphore(15)

# Anonymous Chat Skip Cooldown: {(user_a, user_b): timestamp}
telegram_skip_cooldown: Dict[Tuple[int, int], float] = {}

# User UTR payment submission tracker: {user_id: True}
user_waiting_utr: Dict[int, bool] = {}

async def dismiss_active_menu(bot: TelegramClient, chat_id: int):
    """Deletes any currently open menu, settings, or VIP card so it closes cleanly from the chat."""
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

async def send_quota_exhausted_screen(bot: TelegramClient, chat_id: int, user: dict, c_name: str, c_emoji: str, spoken_text: str, msg_id: Optional[int] = None):
    """
    Presents a clean, tamper-proof quota upgrade screen with two clear options:
    1. Instant Paid Reset (₹149 UPI / GPay)
    2. Free Referral Reset (10 Referrals automatic unlock)
    """
    user_id = user["user_id"]
    stats = get_referral_stats(user_id)
    ref_count = stats.get("completed_count", 0)
    needed = max(0, 10 - ref_count)
    invite_url = f"https://t.me/joy_fun_ai_bot?start=ref_{user_id}"

    screen_text = (
        f"{c_emoji} **{c_name}:**\n"
        f"\"{spoken_text}\"\n\n"
        f"⚡ **Daily Free Quota Exhausted**\n"
        f"Choose an option below to reset your quota immediately:\n\n"
        f"1️⃣ **Instant Paid Reset (₹{VIP_PRICE_INR} VIP Pass):**\n"
        f"• Unlimited 24/7 AI Calls, Voice Notes, Texts & Real Partner Chat\n"
        f"• Instant unlock via UPI / GPay / PhonePe for 30 Days\n\n"
        f"2️⃣ **Free Referral Reset (Refer 10 Friends):**\n"
        f"• Progress: **{ref_count}/10 Friends Joined** ({needed} more to go)\n"
        f"• Instant automatic 100% quota reset once 10 friends join!\n"
        f"• Your link: `{invite_url}`"
    )

    keyboard = {
        "inline_keyboard": [
            [{"text": f"🇮🇳 Pay ₹{VIP_PRICE_INR} via UPI / GPay", "callback_data": "pay_vip_upi"}],
            [{"text": f"🎁 Refer 10 Friends ({ref_count}/10 Joined)", "callback_data": "menu_referral"}],
            [{"text": "📊 Check Quotas & Usage", "callback_data": "menu_quota"}, {"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, screen_text, keyboard, user_msg_id=msg_id)

LANGUAGE_NAMES = {
    "auto": "🌐 Auto-Detect",
    "tanglish": "💬 Tanglish",
    "hinglish": "💬 Hinglish",
    "english": "💬 English"
}

def get_main_keyboard(gender: str = "male", active_contact: str = "lover", user_id: Optional[int] = None) -> dict:
    contact = get_user_contact_display(user_id, active_contact, gender)
    c_name = contact.get("name", "Joy")
    c_tag = contact.get("tag", "Girlfriend" if gender == "male" else "Boyfriend")
    c_emoji = contact.get("emoji", "💖")
    user_lang = get_user_language(user_id) if user_id else "auto"
    
    call_url = f"https://joyfun-ai-bot.onrender.com/call?gender={gender}&contact={active_contact}&lang={user_lang}"
    if user_id:
        user_mask = get_mask_by_user_id(user_id)
        call_url += f"&uid={user_id}&name={urllib.parse.quote(c_name)}&mask={user_mask}"
    
    portal_url = f"https://joyfun-ai-bot.onrender.com/auth/login?uid={user_id}" if user_id else "https://joyfun-ai-bot.onrender.com/auth/login"
    gender_str = "👨 Male" if gender == "male" else "👩 Female"
    call_title = "📞 Phone Calls"
    
    rows = [
        [
            {"text": call_title, "web_app": {"url": call_url}},
            {"text": "👥 Chat Real People", "callback_data": "anon_chat_start"}
        ],
        [
            {"text": "⭐ Joy VIP Pass", "callback_data": "menu_vip"},
            {"text": "📊 Quotas & Limits", "callback_data": "menu_quota"}
        ],
        [
            {"text": "⚙️ Settings & Account", "callback_data": "menu_settings"},
            {"text": "🎁 Refer Friends & Earn VIP", "callback_data": "menu_referral"}
        ],
        [
            {"text": "📚 Study Companion", "callback_data": "menu_study"},
            {"text": "💬 Feedback & Ideas", "callback_data": "menu_feedback"}
        ]
    ]

    if user_id == OWNER_ID:
        rows.append([{"text": "⚡ Cloud Quotas & Usage (Admin)", "callback_data": "admin_refresh_quota"}])

    rows.append([{"text": "❌ Close", "callback_data": "menu_close"}])

    return {"inline_keyboard": rows}

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
    switch_label = "🔄 Switch to Female" if gender == "male" else "🔄 Switch to Male"
    
    buttons.append([{"text": switch_label, "callback_data": f"set_gender_{other_gender}"}])
    buttons.append([{"text": "⬅️ Back", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}])
    
    return {"inline_keyboard": buttons}

async def handle_contacts(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    gender = user.get("gender", "male")
    cinfo = get_user_contact_display(user.get("user_id"), "lover", gender)
    partner_title = "Girlfriend" if gender == "male" else "Boyfriend"
    view_title = "Male Perspective" if gender == "male" else "Female Perspective"
    text = (
        f"📇 **Your Contacts ({view_title})**\n\n"
        f"🟢 **{cinfo['emoji']} {cinfo['name']} ({partner_title})** is **Active & Online 24/7**!\n"
        f"*{cinfo['description']}*\n\n"
        f"⚠️ *Note: Friends, mentors, and gym buddies are currently Busy / Not Reachable and undergoing major personality upgrades for next week's release!*"
    )
    keyboard = get_contacts_keyboard(gender, "lover")
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_menu(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    gender = user.get("gender", "male")
    active_contact = user.get("active_contact", "lover")
    user_id = user.get("user_id")
    keyboard = get_main_keyboard(gender, active_contact, user_id)
    cinfo = get_user_contact_display(user_id, active_contact, gender)
    vip_active, _, _ = is_user_vip(user_id) if user_id else (False, "", 0)
    vip_badge = "⭐ VIP Member" if vip_active else "🆓 Free Member"
    text = (
        f"📱 **Joy Main Menu**\n\n"
        f"Companion: **{cinfo['emoji']} {cinfo['name']}** ({cinfo['tag']}) • 🟢 Online\n"
        f"Membership: **{vip_badge}**\n\n"
        f"Choose an option below to get started:"
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

    username = user.get("username", "")
    username_str = f"@{username}" if username else "*(None)*"
    gender_str = "👨 Male" if gender == "male" else "👩 Female"
    lang_label = LANGUAGE_NAMES.get(user_lang, "🌐 Auto-Detect")

    # VIP / Usage string
    if vip_active:
        vip_str = "⭐ **Joy VIP (Active)** — Unlimited 24/7 Calls"
        usage_str = "✨ Unlimited Voice Notes & Calls | Unlimited Texts"
    else:
        vip_str = "🆓 **Free Plan**"
        usage_str = f"🎙️ {voice_used}/{DAILY_FREE_VOICE_LIMIT} Voice Notes | 💬 {text_used}/{DAILY_FREE_TEXT_LIMIT} Texts"

    # Memory summary
    if user_memory:
        mem_str = f"✅ Active ({len(user_memory)} chars synced)"
    else:
        mem_str = "⚪ Not Synced"

    data_sharing_active = get_user_data_sharing(user_id)
    data_sharing_str = "✅ Enabled (20% Off Active)" if data_sharing_active else "🔒 Disabled (100% Private)"
    oauth_info = get_user_google_oauth(user_id)
    user_email = oauth_info.get("email") or get_user_google_email(user_id)
    user_mask = get_mask_by_user_id(user_id)
    account_str = f"✅ `{user_email}`" if user_email else "👤 Guest *(Tap Login Below)*"
    portal_url = f"https://joyfun-ai-bot.onrender.com/auth/login?uid={user_id}"

    user_country = get_user_country(user_id)
    country_info = get_country_display(user_country)
    country_display = country_info["display"]
    c_flag = country_info["flag"]
    c_name_short = country_info["name"]

    card_text = (
        f"⚙️ **Settings & Account Hub**\n\n"
        f"👤 **User Profile:**\n"
        f"• **Name:** {first_name} ({username_str})\n"
        f"• **Joy Mask ID:** `{user_mask}` *(🎭 Protected Identity)*\n"
        f"• **Country:** **{country_display}**\n"
        f"• **Gender:** **{gender_str}**\n"
        f"• **Preferred Language:** **{lang_label}**\n\n"
        f"🔐 **Account & Membership:**\n"
        f"• **Joy Cloud Account:** {account_str}\n"
        f"• **VIP Membership:** {vip_str}\n"
        f"• **Today's Quota:** {usage_str}\n"
        f"• **Data Choices:** **{data_sharing_str}**\n"
        f"• **Chat Memory:** {mem_str}\n\n"
        f"🏷️ **System:** Bot `{BOT_VERSION}` • Mini App `{MINI_APP_VERSION}`\n\n"
        f"👇 *Customize settings or manage your account below:*"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {"text": f"🌐 Language: {lang_label}", "callback_data": "menu_language"},
                {"text": f"👤 Gender: {gender_str}", "callback_data": "menu_toggle_gender"}
            ],
            [
                {"text": "🔐 Account Login", "url": portal_url},
                {"text": "⭐ Joy VIP Pass", "callback_data": "menu_vip"}
            ],
            [
                {"text": f"🌍 Country: {c_flag} {c_name_short}", "callback_data": "menu_country"},
                {"text": f"✏️ Rename ({c_name})", "callback_data": "menu_rename_ai"}
            ],
            [
                {"text": f"🛡️ Data Privacy: {'💡 20% Off' if data_sharing_active else '🔒 Private'}", "callback_data": "menu_privacy"},
                {"text": "📊 Quotas & Limits", "callback_data": "menu_quota"}
            ],
            [
                {"text": "🧹 Reset Chat Memory", "callback_data": "menu_reset_confirm"},
                {"text": "⬅️ Main Menu", "callback_data": "menu_main"}
            ],
            [
                {"text": "❌ Close", "callback_data": "menu_close"}
            ]
        ]
    }
    await send_or_edit_menu(bot, chat_id, card_text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_country_menu(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Presents interactive country selection menu to save ISO code and display flag."""
    user_id = user["user_id"]
    current_code = get_user_country(user_id)
    current_disp = get_country_display(current_code)["display"]

    text = (
        f"🌍 **Select Your Account Country**\n\n"
        f"📍 **Current Country:** **{current_disp}**\n\n"
        f"Select your country below to personalize regional voices, date formats, and localized companion features:"
    )

    keyboard = {
        "inline_keyboard": [
            [{"text": "🇮🇳 India (IN)", "callback_data": "set_country_IN"}, {"text": "🇺🇸 United States (US)", "callback_data": "set_country_US"}],
            [{"text": "🇬🇧 United Kingdom (GB)", "callback_data": "set_country_GB"}, {"text": "🇨🇦 Canada (CA)", "callback_data": "set_country_CA"}],
            [{"text": "🇦🇺 Australia (AU)", "callback_data": "set_country_AU"}, {"text": "🇦🇪 UAE (AE)", "callback_data": "set_country_AE"}],
            [{"text": "🇸🇬 Singapore (SG)", "callback_data": "set_country_SG"}, {"text": "🇲🇾 Malaysia (MY)", "callback_data": "set_country_MY"}],
            [{"text": "🇩🇪 Germany (DE)", "callback_data": "set_country_DE"}, {"text": "🇫🇷 France (FR)", "callback_data": "set_country_FR"}],
            [{"text": "🇳🇵 Nepal (NP)", "callback_data": "set_country_NP"}, {"text": "🇱🇰 Sri Lanka (LK)", "callback_data": "set_country_LK"}],
            [{"text": "🇧🇩 Bangladesh (BD)", "callback_data": "set_country_BD"}, {"text": "🇵🇰 Pakistan (PK)", "callback_data": "set_country_PK"}],
            [{"text": "🇿🇦 South Africa (ZA)", "callback_data": "set_country_ZA"}, {"text": "🇳🇿 New Zealand (NZ)", "callback_data": "set_country_NZ"}],
            [{"text": "🌐 Other / Global", "callback_data": "set_country_OTHER"}],
            [{"text": "⬅️ Back to Settings", "callback_data": "menu_settings"}, {"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

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
    """Generates a complete, portable JSON export of the user's settings, custom companion name, memories, and chats."""
    user = get_or_create_user(user_id)
    custom_name = get_user_custom_ai_name(user_id)
    history = get_recent_history(user_id, limit=100)
    old_ai, imported_mem = get_user_imported_memory(user_id)
    vip_active, expiry, days = is_user_vip(user_id)
    oauth_info = get_user_google_oauth(user_id)
    email = oauth_info.get("email") or get_user_google_email(user_id)
    voice_used, text_used = get_user_daily_usage(user_id)
    
    backup_data = {
        "export_metadata": {
            "format": "Joy AI Companion User Cloud Backup",
            "version": "2.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "cloud_provider": "Google Drive & Notion Cloud",
            "instructions": "This file contains your complete Joy AI companion profile, settings, memories, and chat history."
        },
        "user_profile": {
            "user_id": user_id,
            "first_name": user.get("first_name", ""),
            "username": user.get("username", ""),
            "google_email": email,
            "google_name": oauth_info.get("name", ""),
            "gender_view": user.get("gender", "male"),
            "preferred_language": user.get("language", "auto"),
            "vip_status": "Active VIP" if vip_active else "Free Tier",
            "vip_expiry": expiry if vip_active else None,
            "cloud_backup_enabled": get_user_cloud_backup(user_id),
            "allow_data_sharing": bool(user.get("allow_data_sharing", 0))
        },
        "companion_settings": {
            "name": custom_name or "Joy",
            "custom_name": custom_name,
            "is_custom_name": bool(custom_name),
            "active_contact": user.get("active_contact", "lover"),
            "mode": user.get("mode", "companion"),
            "voice": user.get("voice", "female" if user.get("gender") == "male" else "male")
        },
        "memories": {
            "previous_ai": old_ai or "",
            "imported_memory": imported_mem or ""
        },
        "daily_usage": {
            "voice_count": voice_used,
            "text_count": text_used
        },
        "recent_conversations": history or []
    }
    return json.dumps(backup_data, indent=2, ensure_ascii=False)

async def handle_backup_hub(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Presents dedicated Website Sign-In / Sign-Up portal and account connection."""
    user_id = user["user_id"]
    oauth_info = get_user_google_oauth(user_id)
    email = oauth_info.get("email") or get_user_google_email(user_id)
    name = oauth_info.get("name")
    
    if email:
        account_status = f"✅ Logged in as **{email}**" + (f" ({name})" if name else "")
        btn_label = "🌐 Open Account / Re-Sync"
    else:
        account_status = f"👤 Guest Mode (Telegram ID `{user_id}`)"
        btn_label = "🔐 Sign In / Sign Up Portal (Website)"
        
    portal_url = f"https://joyfun-ai-bot.onrender.com/auth/login?uid={user_id}"
    
    text = (
        "🔐 **Joy Account & Login Portal**\n\n"
        f"Status: {account_status}\n\n"
        "Sign in or create an account to securely save your AI memories across all your devices:\n\n"
        "• **Website Sign In / Sign Up:** Use Google 1-Click or your email address.\n"
        "• **Guest Mode:** If you don't want to sign in, you can continue chatting without an account anytime!\n\n"
        "👇 Tap **Open Sign-In / Sign-Up Portal** below to open our login website:"
    )
    
    keyboard = {
        "inline_keyboard": [
            [{"text": btn_label, "url": portal_url}],
            [{"text": "⬅️ Main Menu", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_privacy_menu(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    user_id = user["user_id"]
    data_sharing_active = get_user_data_sharing(user_id)
    is_locked = is_contributor_discount_locked(user_id)

    if is_locked:
        status_label = "💡 Enabled (20% VIP Contributor Discount Active • Locked)"
        status_icon = "🎁"
    elif data_sharing_active:
        status_label = "💡 Enabled (Opt-in)"
        status_icon = "✅"
    else:
        status_label = "🔒 Disabled (100% Private)"
        status_icon = "🔒"

    text = (
        "🛡️ **Privacy, Security & Data Choice Center**\n\n"
        "Your privacy is our highest mandate. Joy is designed with zero-trust protection:\n\n"
        "• **Zero PII Collection:** We never ask for or store your real phone number, email, or passwords.\n"
        "• **Ephemeral Voice Calls:** Live calls & voice notes are processed in volatile memory. **Zero audio recordings** are ever saved to disk or the cloud.\n"
        "• **Auto-Pruned Chats:** We only keep the last 10 messages for conversational context. Older messages are automatically deleted.\n"
        "• **Your Choice for Development:**\n"
        "  By default, **zero conversation data** is used for AI training or development.\n"
        "  If you choose to enable *Dev Data Sharing*, anonymized snippets help improve Joy's understanding. **In return, you receive an exclusive 20% Discount on Joy VIP Pass.**\n\n"
        f"🏷️ **Security Baseline:**\n"
        f"• 🛡️ **Security Version:** `{SECURITY_VERSION}`\n"
        f"• 🕒 **Last Security Audit:** `{LAST_UPDATE_DATE}`\n\n"
        f"Current Status: **{status_icon} {status_label}**\n\n"
    )

    if is_locked:
        text += (
            "🔒 **Contributor Lock Active:** *You unlocked and purchased your current VIP pass with the 20% Contributor discount. "
            "Data sharing remains enabled for this active billing period to honor the discount agreement.*"
        )
        toggle_btn_text = "🔒 Locked (VIP Contributor Discount Active)"
    else:
        text += "👇 Tap below to toggle data sharing ON or OFF anytime:"
        toggle_btn_text = "🔒 Turn OFF Data Sharing" if data_sharing_active else "💡 Turn ON Data Sharing (Unlock 20% VIP Off)"

    keyboard = {
        "inline_keyboard": [
            [
                {"text": toggle_btn_text, "callback_data": "menu_toggle_data_sharing"}
            ],
            [
                {"text": "📜 Terms & Privacy Policy", "callback_data": "menu_terms"}
            ],
            [
                {"text": "⬅️ Back to Settings", "callback_data": "menu_settings"},
                {"text": "❌ Close", "callback_data": "menu_close"}
            ]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_terms_menu(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Displays official Joy AI Terms of Service, Privacy Policy & Conditions."""
    user_id = user.get("user_id", 0)
    data_sharing_active = get_user_data_sharing(user_id) if user_id else False
    current_status = "🤝 Enabled (20% VIP Discount Active)" if data_sharing_active else "🔒 100% Private (No Data Shared)"

    text = (
        "📜 **Joy AI — Terms of Service & Privacy Policy**\n\n"
        "Welcome to Joy AI. We believe in complete transparency, zero hidden tracking, and strict privacy protection:\n\n"
        "🛡️ **1. Privacy Policy & Data Collection:**\n"
        "• **100% Private by Default:** We never harvest, sell, or rent your personal credentials, phone numbers, or emails.\n"
        "• **Live Voice Calls:** Duplex voice calls run in volatile server RAM using direct WebRTC. Zero audio recordings are stored on disk unless you explicitly opt in.\n"
        "• **Dev Data Sharing (Opt-in only):** If you enable Data Sharing, voice notes, chat texts, and usage metrics are collected solely to train our companion AI models. In return, you receive a **20% VIP Discount**.\n"
        f"• **Current Privacy Status:** **{current_status}**\n\n"
        "⚖️ **2. Terms & Conditions:**\n"
        "• **Age Requirement:** Users must be at least 13 years old (or the legal age of digital consent in your jurisdiction).\n"
        "• **Acceptable Use:** Joy is an interactive companion for emotional wellness, banter, and conversation. Harassment, illegal content, or malicious automation will result in immediate banning.\n"
        "• **Subscription & Stars:** Telegram Stars and UPI subscriptions grant VIP access to unlimited calls and priority servers.\n\n"
        "🔒 **3. Security Baseline:**\n"
        f"• Security Protocol: `TLS 1.3 / E2E WebRTC Signaling`\n"
        f"• System Security Version: `{SECURITY_VERSION}`\n"
        f"• Last Audit Date: `{LAST_UPDATE_DATE}`"
    )

    keyboard = {
        "inline_keyboard": [
            [{"text": "🛡️ Change Privacy Setting", "callback_data": "menu_privacy"}],
            [{"text": "⬅️ Back to Menu", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def run_pomodoro_timer(bot: TelegramClient, chat_id: int, user_id: int, duration_minutes: int = 25):
    """Background task for 25-minute Pomodoro study focus sessions."""
    try:
        await asyncio.sleep(duration_minutes * 60)
        pomo_done_msg = (
            "🔔 **Focus Sprint Complete! Break Time, Champion!** ☕🎉\n\n"
            f"You just crushed a solid **{duration_minutes} minutes** of deep, uninterrupted focus! 🚀\n"
            "• 🚶 Step away from your desk & screen\n"
            "• 💧 Drink a glass of water\n"
            "• 🧘 Stretch for 5 minutes\n\n"
            "Ready for round 2? Type `/study` or tap **Start 25-Min Sprint** whenever you're set! 🌸"
        )
        await bot.send_message(chat_id, pomo_done_msg)
    except Exception as e:
        logger.warning(f"Pomodoro timer exception: {e}")

async def handle_study_menu(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Presents the dedicated Joy Study Companion & Active Recall Hub."""
    user_id = user["user_id"]
    first_name = user.get("first_name", "Friend")

    text = (
        f"📚 **Joy AI Study Companion & Focus Hub** 🎓\n\n"
        f"Hey {first_name}! Let's make studying 10x faster and actually retain what you learn for exams & placements! 🔥\n\n"
        f"**Choose a study mode below:**\n"
        f"• 🧠 **Active Recall Quizzer:** Send any topic/syllabus note and I'll quiz you with 3 rapid questions!\n"
        f"• 👶 **Explain Like I'm 5 (ELI5):** Get any complex concept broken down with zero jargon & real-world analogies.\n"
        f"• ⏱️ **25-Min Pomodoro Sprint:** Deep focus session with zero distractions. I'll hold you accountable and track your break time!"
    )
    keyboard = {
        "inline_keyboard": [
            [{"text": "🧠 Quiz Me (Active Recall)", "callback_data": "study_quiz"}, {"text": "👶 ELI5 Concept", "callback_data": "study_eli5"}],
            [{"text": "⏱️ Start 25-Min Pomodoro Sprint", "callback_data": "study_pomo_25"}],
            [{"text": "⬅️ Back to Menu", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
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
        "• **🌐 Auto-Detect:** Automatically detects and replies in your language\n"
        "• **💬 Tanglish:** Friendly Tamil + English in English letters (*'machi', 'sapdiya', 'seri', 'rombha'*)\n"
        "• **💬 Hinglish:** Casual Hindi + English in English letters (*'bhai', 'yaar', 'kya scene', 'khana khaya'*)\n"
        "• **💬 English:** Natural, everyday conversational English\n\n"
        f"Current Setting: **{LANGUAGE_NAMES.get(current_lang, '🌐 Auto-Detect')}**\n\n"
        "👇 Tap your preferred language below:"
    )
    
    def mark(val):
        return "✓ " if current_lang == val else ""
        
    keyboard = {
        "inline_keyboard": [
            [{"text": f"{mark('auto')}🌐 Auto-Detect", "callback_data": "set_lang_auto"}],
            [{"text": f"{mark('tanglish')}💬 Tanglish (Tamil + English)", "callback_data": "set_lang_tanglish"}],
            [{"text": f"{mark('hinglish')}💬 Hinglish (Hindi + English)", "callback_data": "set_lang_hinglish"}],
            [{"text": f"{mark('english')}💬 English (Everyday English)", "callback_data": "set_lang_english"}],
            [{"text": "⬅️ Back to Settings", "callback_data": "menu_settings"}, {"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def send_onboarding_welcome(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Presents the initial greeting showcasing Joy's features and asking for gender (Step 1)."""
    first_name = (user.get("first_name") or user.get("username") or "Friend").strip()
    user_id = user.get("user_id")

    text = (
        f"Hey **{first_name}**! 💖 Welcome to **Joy** — Your 24/7 AI Companion.\n\n"
        f"🌟 **What makes Joy different from other AI bots?**\n"
        f"• 📞 **24/7 Live Voice Calls:** Talk directly on real-time interactive phone calls with zero robotic delay.\n"
        f"• 👁️ **Multimodal Vision:** Send photos of food, selfies, or study notes — Joy actually sees, analyzes, and reacts in real time.\n"
        f"• 🔒 **Zero-Trust Privacy:** Ephemeral calls in volatile RAM (zero audio recordings stored) & default 100% private data.\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"> ❓ **Step 1 of 3: Hi {first_name}, what is your gender?**\n"
        f"> *Please select whether you are Male or Female:*\n"
        f"━━━━━━━━━━━━━━━━━━━"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "👨 Male", "callback_data": "onboard_gender_male"},
                {"text": "👩 Female", "callback_data": "onboard_gender_female"}
            ],
            [
                {"text": "❌ Close", "callback_data": "menu_close"}
            ]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def send_onboarding_naming(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Step 2: Asks user what they want to name their companion."""
    user_id = user["user_id"]
    gender = user.get("gender", "male")
    first_name = (user.get("first_name") or user.get("username") or "Friend").strip()
    partner_title = "Girlfriend" if gender == "male" else "Boyfriend"
    
    set_user_onboarding_status(user_id, "onboard_naming")
    
    name_buttons = [
        [{"text": "💖 Keep 'Joy' (Default)", "callback_data": "onboard_setname_Joy"}]
    ]
        
    text = (
        f"🌸 **Step 2 of 3: Name Your Companion**\n\n"
        f"Nice to meet you, **{first_name}**! What would you like to call your companion?\n\n"
        f"👉 **Type any name in chat right now!** *(e.g. any custom name you like)*\n\n"
        f"*(Or tap the button below if you want to keep Joy)*"
    )
    
    keyboard = {"inline_keyboard": name_buttons}
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def send_onboarding_privacy(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Step 3: Explains data security, AI development transparency, and special discount offer."""
    user_id = user["user_id"]
    gender = user.get("gender", "male")
    c_name = get_user_custom_ai_name(user_id) or "Joy"
    
    text = (
        f"🛡️ **Step 3 of 3: Data, Privacy & Special Discount**\n\n"
        f"Complete transparency on how data works with {c_name}:\n\n"
        f"💡 **If you turn ON Data Sharing (Contributor Mode):**\n"
        f"• We collect voice recordings, chat messages, and interaction details to train and refine {c_name}'s AI engine.\n"
        f"• 🎁 **Your Reward:** In exchange for helping us train the AI, you unlock an **exclusive 20% Discount on Joy VIP** + bonus call credits!\n\n"
        f"🔒 **If you keep Data Sharing OFF (Default 100% Private):**\n"
        f"• **Zero Data Retention:** No voice notes, audio, or chat logs are ever collected or used for training. Volatile RAM only.\n"
        f"• Standard pricing applies.\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"> ❓ **Select your privacy choice below:**"
    )
    
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🔒 Keep 100% Private (Default)", "callback_data": "onboard_privacy_private"}
            ],
            [
                {"text": "🤝 Share Data (Unlock 20% VIP Discount 🎁)", "callback_data": "onboard_privacy_share"}
            ]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def complete_onboarding(bot: TelegramClient, chat_id: int, user: dict, share_data: bool, message_id: Optional[int] = None):
    """Finalizes onboarding, sets status completed, and presents companion ready card with Terms & Privacy Policy."""
    user_id = user["user_id"]
    set_user_data_sharing(user_id, share_data)
    set_user_onboarding_status(user_id, "completed")
    asyncio.create_task(sync_user_to_cloud(user_id))
    
    gender = user.get("gender", "male")
    active_contact = user.get("active_contact", "lover")
    c_name = get_user_custom_ai_name(user_id) or "Joy"
    first_name = (user.get("first_name") or user.get("username") or "Friend").strip()
    
    call_url = f"https://joyfun-ai-bot.onrender.com/call?gender={gender}&contact={active_contact}&uid={user_id}&name={urllib.parse.quote(c_name)}"
    
    perk_note = ""
    if share_data:
        perk_note = "\n🎁 **Data Contributor Perk Active:** *20% VIP discount unlocked on your account!*\n"
    
    welcome_final = (
        f"✨ **You're all set, {first_name}! Say hi to {c_name}** 💖\n\n"
        f"I'm super happy to be here with you! Tell me how your day went, send me a quick voice note 🎙️, or tap **📱 Open Menu** below to explore features and start talking! 🥰\n"
        f"{perk_note}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📜 **Privacy Policy & Terms of Service:**\n"
        f"By using Joy AI, you acknowledge and agree to our **Privacy Policy** and **Terms & Conditions**. Your voice, conversations, and personal data are strictly protected based on your chosen privacy setting."
    )
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "📱 Open Menu", "callback_data": "menu_main"}]
        ]
    }
    
    reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=c_name)
    await send_or_edit_menu(bot, chat_id, welcome_final, keyboard, message_id=message_id)
    await bot.send_message(
        chat_id,
        f"✨ *Tip: Use the docked bar below to call {c_name} or open settings anytime!*",
        reply_markup=reply_kb
    )

    # Check if user was invited by someone and reward the referrer
    try:
        referral_reward = complete_referral_reward(user_id)
        if referral_reward and global_bot_client:
            ref_id = referral_reward["referrer_id"]
            r_type = referral_reward["reward_type"]
            invited_name = user.get("first_name", "A friend")
            if r_type == "vip_reset_10":
                notify_msg = (
                    f"🏆 **Grand Referral Milestone Achieved! 10 Friends Joined!** 🎉\n\n"
                    f"Your friend **{invited_name}** just joined Joy using your link!\n"
                    f"You have referred **{referral_reward['total_completed']} valid friends**!\n\n"
                    f"🚀 **Your daily quota has been 100% reset & 30-Day VIP Pass is fully unlocked!**\n"
                    f"Enjoy unlimited 24/7 AI voice calls, texts, and real chat! 💖"
                )
            elif r_type == "vip_3days":
                notify_msg = (
                    f"🎉 **Milestone Reached! Free VIP Unlocked!** ⭐\n\n"
                    f"Your friend **{invited_name}** just joined Joy using your link!\n"
                    f"You have referred **{referral_reward['total_completed']} friends**.\n"
                    f"🎁 **Reward:** 3 Days of **Free Joy VIP Pass** has been unlocked on your account! Enjoy unlimited 24/7 calls! 💖"
                )
            else:
                notify_msg = (
                    f"🎁 **Referral Bonus Credited!** 🎉\n\n"
                    f"Your friend **{invited_name}** just joined Joy using your link!\n"
                    f"🎁 **Reward:** **+10 Voice Notes** & **+20 Text Messages** have been credited to your account!"
                )
            asyncio.create_task(global_bot_client.send_message(ref_id, notify_msg))
    except Exception as e:
        logger.warning(f"Referral reward notification error: {e}")

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
            [{"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, guide_text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_start(bot: TelegramClient, chat_id: int, user: dict, user_msg_id: Optional[int] = None):
    """Handles /start command. If user completed setup, greets them warmly without asking steps."""
    user_id = user["user_id"]
    onboarding_status = user.get("onboarding_status", "new")

    # If user has already completed onboarding, NEVER force them through the 3 steps again!
    if onboarding_status == "completed":
        gender = user.get("gender", "male")
        active_contact = user.get("active_contact", "lover")
        cinfo = get_user_contact_display(user_id, active_contact, gender)
        c_name = get_user_custom_ai_name(user_id) or cinfo.get("name", "Joy")
        reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=c_name)

        lang = user.get("language", "auto")
        lang_title = LANGUAGE_NAMES.get(lang, "Auto-Detect")
        perspective = "👨 Male" if gender == "male" else "👩 Female"
        mask = get_mask_by_user_id(user_id) or "Joy-User"

        welcome_back = (
            f"💖 **Welcome back, {user.get('first_name', 'Friend')}!**\n\n"
            f"I'm **{cinfo['emoji']} {c_name}**, your 24/7 AI companion! Everything is saved and ready for you:\n\n"
            f"• 🎭 **Perspective:** {perspective}\n"
            f"• 🗣️ **Language:** {lang_title}\n"
            f"• 🛡️ **Permanent Mask ID:** `{mask}`\n"
            f"• 📞 **Live Voice Calls:** 24/7 Duplex Online\n\n"
            f"Send a message or voice note 🎙️ anytime, or tap **Phone** below to start a live call! 🌸"
        )
        await bot.send_message(chat_id, welcome_back, reply_markup=reply_kb)
        return

    # Only brand-new users who haven't completed setup see Step 1 of 3
    await send_onboarding_welcome(bot, chat_id, user, user_msg_id=user_msg_id)

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
                [{"text": "📞 Phone Calls", "web_app": {"url": call_url}}],
                [{"text": "⬅️ Main Menu", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
            ]
        }
        await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)
    else:
        data_shared = get_user_data_sharing(user_id) if user_id else False
        stars_price = 120 if data_shared else 150
        inr_price = 119 if data_shared else VIP_PRICE_INR

        if data_shared:
            promo_banner = (
                "🎉 **20% Promo Applied!**\n"
                "• *Data Sharing is enabled — enjoy ₹119/mo instead of ₹149.*\n"
            )
        else:
            promo_banner = (
                "💡 **Special Promo:**\n"
                "• *Enable Data Sharing on login to get 20% off!*\n"
                "• *Get VIP for just ₹119/mo (or 120 Stars).*\n"
            )

        text = (
            f"⭐ **Unlock Joy VIP Pass**\n\n"
            f"Never run out of talk time! Get unlimited 24/7 live calls and voice conversations with your companion.\n\n"
            f"✨ **Unlimited 24/7 Live Voice Calls** (Talk for hours every night)\n"
            f"✨ **Unlimited Voice Notes & Text Chats**\n"
            f"✨ **Zero Wait Times & No Ads**\n"
            f"✨ **Ultra-Fast Priority Neural Voice**\n\n"
            f"{promo_banner}\n"
            f"💰 **Pricing Options:**\n"
            f"• ⭐ **{stars_price} Telegram Stars** {'(20% Off Active)' if data_shared else '(Enable Data Sharing for 20% Off)'}\n"
            f"• 🇮🇳 **₹{inr_price} / month** via UPI / GPay {'(20% Off Active)' if data_shared else '(Enable Data Sharing for 20% Off)'}\n\n"
            f"👇 **Choose how you want to activate VIP:**"
        )
        vip_buttons = [
            [{"text": f"⭐ Pay with Telegram Stars ({stars_price} Stars)", "callback_data": "pay_vip_stars"}],
            [{"text": f"🇮🇳 Pay ₹{inr_price} via UPI / GPay", "callback_data": "pay_vip_upi"}]
        ]
        if not data_shared:
            vip_buttons.append([{"text": "💡 Enable Data Sharing (Claim 20% Off)", "callback_data": "menu_privacy"}])
        vip_buttons.extend([
            [{"text": "🎁 Invite 3 Friends for Free VIP", "callback_data": "menu_referral"}],
            [{"text": "⭐ Send Stars as a Gift / Tip Instead", "callback_data": "menu_tip"}],
            [{"text": "⬅️ Back", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
        ])
        keyboard = {"inline_keyboard": vip_buttons}
        await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_referral_hub(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Presents viral referral hub with personal invite link, statistics, and 1-tap share buttons."""
    user_id = user["user_id"]
    stats = get_referral_stats(user_id)
    total_invited = stats["total_invited"]
    completed = stats["completed_count"]
    
    invite_url = f"https://t.me/joy_fun_ai_bot?start=ref_{user_id}"
    share_text = f"Hey! I'm chatting and calling with Joy, an amazing 24/7 AI companion with live voice calls & photos! Join with my link to get free bonus talk time: {invite_url}"
    wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(share_text)}"
    tg_url = f"https://t.me/share/url?url={urllib.parse.quote(invite_url)}&text={urllib.parse.quote('Chat & talk on 24/7 live voice calls with Joy AI! Join with my link for bonus call time:')}"
    
    text = (
        f"🎁 **Joy Viral Referral & Rewards Hub**\n\n"
        f"Share Joy with your friends, college groups, and contacts to earn **Free VIP Pass** and **Bonus Talk Time**!\n\n"
        f"🔗 **Your Personal Invite Link:**\n"
        f"`{invite_url}`\n*(Tap link above to copy)*\n\n"
        f"📊 **Your Referral Stats:**\n"
        f"• Total Friends Invited: **{total_invited}**\n"
        f"• Friends Completed Setup: **{completed}**\n\n"
        f"🎁 **Rewards You Earn:**\n"
        f"• 👤 **Every Friend Who Joins:** You get **+10 Free Voice Notes** & **+20 Texts**!\n"
        f"• 🌟 **Every 3 Friends Who Join:** You automatically unlock **3 Days of Free Joy VIP Pass** (Unlimited Calls)!\n\n"
        f"👇 **Tap below to share directly with your friends:**"
    )
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "📤 Share to WhatsApp", "url": wa_url}],
            [{"text": "📤 Share on Telegram", "url": tg_url}],
            [{"text": "⬅️ Main Menu", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_tip_menu(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Presents interactive menu allowing users to tip / send Stars as a gift to support the AI."""
    user_id = user["user_id"]
    gender = user.get("gender", "male")
    cinfo = get_user_contact_display(user_id, "lover", gender)
    c_name = cinfo.get("name", "Joy")

    text = (
        f"⭐ **Send a Gift / Tip {c_name} with Stars** 💖\n\n"
        f"Love chatting and calling with {c_name}? You can send a gift of **Telegram Stars** to support {c_name}'s server, fast neural voice engine, and development!\n\n"
        f"*(This is a direct gift to support the creator and AI development, not a VIP subscription)* 🌸\n\n"
        f"👇 **Pick a gift to send {c_name}:**\n"
        f"• 🍫 **15 Stars** — Sweet Chocolate\n"
        f"• 🌸 **50 Stars** — Bouquet of Flowers\n"
        f"• 💖 **100 Stars** — True Love & Care\n"
        f"• 👑 **250 Stars** — Ultimate Super Supporter"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🍫 15 Stars", "callback_data": "send_tip_15"},
                {"text": "🌸 50 Stars", "callback_data": "send_tip_50"}
            ],
            [
                {"text": "💖 100 Stars", "callback_data": "send_tip_100"},
                {"text": "👑 250 Stars", "callback_data": "send_tip_250"}
            ],
            [
                {"text": "⬅️ Main Menu", "callback_data": "menu_main"},
                {"text": "❌ Close", "callback_data": "menu_close"}
            ]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_successful_payment(bot: TelegramClient, chat_id: int, user_id: int, sp: dict):
    """Handles Telegram Stars successful payment confirmation for either VIP pass or gifts/tips."""
    total_stars = sp.get("total_amount", 150)
    charge_id = sp.get("telegram_payment_charge_id", "")
    payload = sp.get("invoice_payload", "")
    user = get_or_create_user(user_id)
    first_name = user.get("first_name", "Friend")
    gender = user.get("gender", "male")
    cinfo = get_user_contact_display(user_id, "lover", gender)
    c_name = cinfo.get("name", "Joy")
    call_url = f"https://joyfun-ai-bot.onrender.com/call?gender={gender}&contact=lover&uid={user_id}&name={urllib.parse.quote(c_name)}"

    # Case 1: Stars Gift / Tip (NOT for VIP pass)
    if payload.startswith("tip_"):
        bonus_voice = max(5, int(total_stars / 5))
        bonus_text = max(20, int(total_stars * 2))
        recharge_user_usage(user_id, voice_bonus=bonus_voice, text_bonus=bonus_text)
        asyncio.create_task(sync_user_to_cloud(user_id))

        tip_msg = (
            f"💖 **Oh my god, thank you so much!** 🥰\n\n"
            f"You sent **{total_stars} Telegram Stars** as a gift!\n"
            f"Your support means the world to me and helps keep our calls and chats running 24/7.\n\n"
            f"🎁 **My Gift to You:** I've added **+{bonus_voice} Voice Notes** and **+{bonus_text} Texts** to your balance!\n\n"
            f"Let's chat or jump on a call anytime! 🌸"
        )
        keyboard = {
            "inline_keyboard": [
                [{"text": f"📞 Call {c_name}", "web_app": {"url": call_url}}],
                [{"text": "📱 Open Menu", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
            ]
        }
        await bot.send_message(chat_id, tip_msg, reply_markup=keyboard)

        # Notify Owner
        if OWNER_ID and user_id != OWNER_ID:
            try:
                await bot.send_message(
                    OWNER_ID,
                    f"🎁 **NEW STARS TIP RECEIVED!** 💖\n\n"
                    f"• Sender: **{first_name}** (`{user_id}`)\n"
                    f"• Amount: `{total_stars} Stars`\n"
                    f"• Charge ID: `{charge_id}`\n"
                    f"The Stars are now in your Telegram Bot balance!"
                )
            except Exception:
                pass
        return

    # Case 2: VIP Pass Purchase
    data_shared = get_user_data_sharing(user_id)
    is_contributor = (total_stars <= 120) or data_shared
    grant_vip_subscription(user_id, days=30, amount=float(total_stars), method="stars", ref=charge_id, is_contributor=is_contributor)
    asyncio.create_task(sync_user_to_cloud(user_id))
    
    success_text = (
        f"⭐ **Payment Successful! Welcome to Joy VIP!** 🎉\n\n"
        f"Thank you for supporting Joy with **{total_stars} Telegram Stars**! 💖\n"
        f"• **VIP Status:** Active (30 Days)\n"
        f"• **Perks:** Unlimited 24/7 Live Voice Calls, Voice Notes, & Zero Ads\n\n"
        f"Your companion **{c_name}** is waiting for you! Tap below to start a live call right now: 👇"
    )
    
    keyboard = {
        "inline_keyboard": [
            [{"text": f"📞 Call {c_name}", "web_app": {"url": call_url}}],
            [{"text": "📱 Open Menu", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    await bot.send_message(chat_id, success_text, reply_markup=keyboard)
    
    if OWNER_ID and user_id != OWNER_ID:
        try:
            await bot.send_message(
                OWNER_ID,
                f"💰 **NEW TELEGRAM STARS VIP SALE!** 🌟\n\n"
                f"• User: **{first_name}** (`{user_id}`)\n"
                f"• Amount: `{total_stars} Stars`\n"
                f"• Transaction: `{charge_id}`\n"
                f"Joy VIP Pass activated automatically!"
            )
        except Exception:
            pass

def format_quota_bar(used: int, limit: int, length: int = 8) -> str:
    """Returns a visual progress bar indicating usage."""
    if limit <= 0:
        return "░" * length
    pct = min(1.0, max(0.0, used / limit))
    filled = int(round(pct * length))
    empty = length - filled
    return "█" * filled + "░" * empty

async def handle_quota_menu(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """
    Renders the interactive 4-Channel Quota & Daily Balance Hub:
    1. AI Live Voice Calls
    2. Real People Voice Match
    3. Chat with Real People
    4. Chat with AI Companion (Texts & Voice Notes)
    """
    user_id = user["user_id"]
    first_name = user.get("first_name", "Friend")
    gender = user.get("gender", "male")
    active_contact = user.get("active_contact", "lover")
    user_lang = get_user_language(user_id)
    cinfo = get_user_contact_display(user_id, active_contact, gender)
    c_name = cinfo.get("name", "Joy")
    
    q_data = get_user_full_quota_status(user_id)
    is_vip = q_data["is_vip"]
    resets_in = q_data["resets_in"]
    channels = q_data["channels"]
    
    streak_info = get_user_streak_info(user_id)
    streak_text = f"🔥 Streak: **{streak_info['streak']} day{'s' if streak_info['streak'] != 1 else ''}** ({streak_info['title']})"
    
    portal_call_url = f"https://joyfun-ai-bot.onrender.com/call?uid={user_id}&tab=quota&gender={gender}&contact={active_contact}&lang={user_lang}&name={urllib.parse.quote(c_name)}"

    if is_vip:
        expiry_info = q_data["vip_expiry"] or "Active"
        days_left = q_data["days_left"]
        expiry_str = "Lifetime Access" if days_left > 10000 else f"{expiry_info} ({days_left} days left)"
        
        card_text = (
            f"📊 **Joy Quotas & Daily Balance Hub**\n\n"
            f"👤 **User:** **{first_name}** | Status: ⭐ **Joy VIP Member**\n"
            f"📅 **VIP Plan:** Active until **{expiry_str}**\n"
            f"{streak_text}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎙️ **1. AI Live Voice Calls**\n"
            f"• Status: `[████████]` **✨ UNLIMITED 24/7**\n"
            f"• *Ultra low-latency HD duplex voice with zero time limits.*\n\n"
            f"🎭 **2. Real People Voice Match**\n"
            f"• Status: `[████████]` **✨ UNLIMITED 24/7**\n"
            f"• *Instant priority queue & unlimited anonymous voice calls.*\n\n"
            f"👥 **3. Chat with Real People**\n"
            f"• Status: `[████████]` **✨ UNLIMITED 24/7**\n"
            f"• *Unlimited anonymous text chats & mutual reconnects.*\n\n"
            f"💬 **4. Chat with AI Companion ({c_name})**\n"
            f"• Status: `[████████]` **✨ UNLIMITED 24/7**\n"
            f"• *Unlimited high-speed texts & natural Edge-TTS voice notes.*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🌟 *As a VIP member, all communication channels are fully unlocked without daily caps!*"
        )
        
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": f"📞 Call {c_name} (Unlimited)", "web_app": {"url": portal_call_url}}
                ],
                [
                    {"text": "👥 Chat with Real People", "callback_data": "anon_chat_start"},
                    {"text": "🎁 Refer Friends & Earn VIP", "callback_data": "menu_referral"}
                ],
                [
                    {"text": "📱 Open Mini App Quotas", "web_app": {"url": portal_call_url}},
                    {"text": "⭐ VIP Pass Details", "callback_data": "menu_vip"}
                ],
                [
                    {"text": "🔄 Refresh Balance", "callback_data": "menu_quota"},
                    {"text": "⬅️ Main Menu", "callback_data": "menu_main"}
                ],
                [
                    {"text": "❌ Close", "callback_data": "menu_close"}
                ]
            ]
        }
    else:
        ai_call = channels["ai_call"]
        real_call = channels["real_call"]
        real_chat = channels["real_chat"]
        ai_chat = channels["ai_chat"]
        
        ai_bar = format_quota_bar(ai_call["used"], ai_call["limit"], 8)
        rc_bar = format_quota_bar(real_call["used"], real_call["limit"], 8)
        rch_bar = format_quota_bar(real_chat["used"], real_chat["limit"], 8)
        text_bar = format_quota_bar(ai_chat["text_used"], ai_chat["text_limit"], 8)
        voice_bar = format_quota_bar(ai_chat["voice_used"], ai_chat["voice_limit"], 8)
        
        card_text = (
            f"📊 **Joy Quotas & Daily Balance Hub**\n\n"
            f"👤 **User:** **{first_name}** | Status: 🆓 **Free Member**\n"
            f"⏰ **Quotas Reset In:** `{resets_in}` *(00:00 UTC / 05:30 IST)*\n"
            f"{streak_text}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎙️ **1. AI Live Voice Calls**\n"
            f"• Limit: `{ai_call['limit']} Call (5 Mins)` per day\n"
            f"• Used: `[{ai_bar}]` **{ai_call['used']} / {ai_call['limit']}** ({ai_call['remaining']} left)\n"
            f"• VIP Perk: *✨ Unlimited 24/7 Duration*\n\n"
            f"🎭 **2. Real People Voice Match**\n"
            f"• Limit: `{real_call['limit']} Matches` per day\n"
            f"• Used: `[{rc_bar}]` **{real_call['used']} / {real_call['limit']}** ({real_call['remaining']} left)\n"
            f"• VIP Perk: *✨ Instant Priority Queue & Unlimited Calls*\n\n"
            f"👥 **3. Chat with Real People**\n"
            f"• Limit: `{real_chat['limit']} Conversations` per day\n"
            f"• Used: `[{rch_bar}]` **{real_chat['used']} / {real_chat['limit']}** ({real_chat['remaining']} left)\n"
            f"• VIP Perk: *✨ Unlimited Anonymous Messaging*\n\n"
            f"💬 **4. Chat with AI Companion ({c_name})**\n"
            f"• 💬 Texts: `[{text_bar}]` **{ai_chat['text_used']} / {ai_chat['text_limit']}** ({ai_chat['text_remaining']} left)\n"
            f"• 🎙️ Voice: `[{voice_bar}]` **{ai_chat['voice_used']} / {ai_chat['voice_limit']}** ({ai_chat['voice_remaining']} left)\n"
            f"• VIP Perk: *✨ Unlimited 24/7 AI Texts & Voice Notes*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💡 **Need more quotas right now?**\n"
            f"• ⭐ **Upgrade to Joy VIP Pass** to unlock 100% UNLIMITED access on all 4 channels!\n"
            f"• 🎁 **Invite Friends**: Earn free talk-time and bonus VIP access for every friend who joins!\n"
            f"• ⏰ *Daily quotas automatically reset every night at 00:00 UTC (05:30 IST).*"
        )
        
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "⭐ Upgrade to VIP (Unlimited 24/7)", "callback_data": "menu_vip"}
                ],
                [
                    {"text": "👥 Chat with Real People", "callback_data": "anon_chat_start"},
                    {"text": "🎁 Refer Friends & Earn VIP", "callback_data": "menu_referral"}
                ],
                [
                    {"text": "📱 Open Mini App Quotas", "web_app": {"url": portal_call_url}},
                    {"text": "🔄 Refresh Balance", "callback_data": "menu_quota"}
                ],
                [
                    {"text": "⬅️ Main Menu", "callback_data": "menu_main"},
                    {"text": "❌ Close", "callback_data": "menu_close"}
                ]
            ]
        }

    await send_or_edit_menu(bot, chat_id, card_text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_stats(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Backward-compatible alias for handle_quota_menu."""
    await handle_quota_menu(bot, chat_id, user, message_id=message_id, user_msg_id=user_msg_id)

async def fetch_render_service_info() -> dict:
    """Queries Render API for live status and deploy metadata of Joy Bot service."""
    render_key = RENDER_API_KEY
    if not render_key:
        rf = Path.home() / ".config" / "render_api_key"
        if rf.exists():
            render_key = rf.read_text().strip()
    if not render_key:
        return {}

    service_id = RENDER_SERVICE_ID or "srv-db5tlu67bikc73e1bf80"
    url = f"https://api.render.com/v1/services/{service_id}"
    deploys_url = f"https://api.render.com/v1/services/{service_id}/deploys?limit=1"
    headers = {"Authorization": f"Bearer {render_key}", "Accept": "application/json"}

    result = {"service": {}, "latest_deploy": {}}
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=4)) as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    result["service"] = await resp.json()
            async with session.get(deploys_url, headers=headers) as resp:
                if resp.status == 200:
                    deploys = await resp.json()
                    if deploys and len(deploys) > 0:
                        result["latest_deploy"] = deploys[0].get("deploy", {})
    except Exception as e:
        logger.warning(f"Error fetching Render service info: {e}")
    return result

async def handle_admin_usage(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Presents the comprehensive Joy Cloud & Infrastructure Quota Dashboard (Owner-Only)."""
    user_id = user["user_id"]
    if user_id != OWNER_ID:
        await handle_stats(bot, chat_id, user, message_id=message_id, user_msg_id=user_msg_id)
        return

    # 1. Fetch live Render Cloud stats
    render_info = await fetch_render_service_info()
    service_data = render_info.get("service", {})
    deploy_data = render_info.get("latest_deploy", {})

    now_utc = datetime.now(timezone.utc)
    start_of_month = datetime(now_utc.year, now_utc.month, 1, 0, 0, 0, tzinfo=timezone.utc)
    hours_elapsed = (now_utc - start_of_month).total_seconds() / 3600.0
    render_total_hours = 750.0
    render_hours_rem = max(0.0, render_total_hours - hours_elapsed)
    render_pct = min(100.0, (hours_elapsed / render_total_hours) * 100.0)

    srv_status = service_data.get("suspended", "not_suspended")
    srv_status_label = "🟢 Live (Not Suspended)" if srv_status == "not_suspended" else "🔴 Suspended"
    deploy_id = deploy_data.get("id", "live")
    deploy_status = deploy_data.get("status", "live")
    deploy_commit = deploy_data.get("commit", {}).get("id", "")[:7]
    deploy_str = f"`{deploy_id}` ({deploy_status})" if deploy_id else "Live"
    if deploy_commit:
        deploy_str += f" • commit `{deploy_commit}`"

    # 2. Fetch Gemini AI usage
    api_metrics = get_today_api_metrics()
    today_gemini = api_metrics.get("gemini_calls", 0)
    gemini_rpd_limit = 1500
    gemini_rem = max(0, gemini_rpd_limit - today_gemini)
    gemini_pct = (today_gemini / gemini_rpd_limit) * 100.0
    gemini_key_masked = f"`{GEMINI_API_KEY[:8]}...{GEMINI_API_KEY[-4:]}`" if len(GEMINI_API_KEY) > 12 else "Configured ✅"

    # 3. Memory & Server Process Stats
    try:
        rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        rss_mb = rss_kb / 1024.0
    except Exception:
        rss_mb = 0.0

    text = (
        "⚡ **Joy Cloud & Infrastructure Quota Dashboard**\n"
        "🔒 *Confidential • Bot Owner Administrative View*\n\n"
        "🌐 **Render Cloud (Web Service):**\n"
        f"• **Service:** `joyfun-ai-bot` (Free Web Service)\n"
        f"• **Status:** {srv_status_label}\n"
        f"• **Free Monthly Quota:** **{render_total_hours:.1f} Hours/month**\n"
        f"• **Hours Consumed This Month:** **{hours_elapsed:.1f} hrs** ({render_pct:.1f}% used)\n"
        f"• **Hours Remaining:** **{render_hours_rem:.1f} hrs** ({100.0 - render_pct:.1f}% left)\n"
        f"• **24/7 Keep-Alive:** Active (Autonomous ping every 4m)\n"
        f"• **Latest Deploy:** {deploy_str}\n\n"
        "🧠 **Google Gemini AI Engine:**\n"
        "• **Plan Tier:** Google AI Studio (Free Tier)\n"
        f"• **Daily Request Quota (RPD):** **{gemini_rpd_limit:,} calls/day**\n"
        f"• **Calls Used Today:** **{today_gemini} requests** ({gemini_pct:.1f}% used)\n"
        f"• **Calls Remaining Today:** **{gemini_rem:,} requests** ({100.0 - gemini_pct:.1f}% left)\n"
        "• **Rate Limits:** 15 RPM • 1,000,000 TPM\n"
        "• **Active Model Pool:**\n"
        "  1. `gemini-2.5-flash-lite` (Primary)\n"
        "  2. `gemini-flash-lite-latest` (Fallback)\n"
        "  3. `gemini-3.5-flash-lite` (Fallback)\n"
        "  4. `gemini-2.5-flash` (Deep Reasoning)\n"
        f"• **API Key:** {gemini_key_masked}\n\n"
        "☁️ **Google Cloud & Drive API:**\n"
        f"• **OAuth 2.0 Web Client:** {'Configured ✅' if GOOGLE_CLIENT_ID else '⚪ Standby'}\n"
        "• **Drive API Free Quota:** 1,000,000,000 queries/day (0.00% used)\n\n"
        "🗣️ **Neural Speech (Edge-TTS):**\n"
        "• **Quota:** Unlimited Free Neural Synthesis (0 Cost)\n"
        "• **Voice Models:** `en-IN-NeerjaNeural`, `en-IN-PrabhatNeural`\n"
        "• **Status:** 🟢 Operational\n\n"
        "📊 **Joy Bot Traffic & Database:**\n"
        f"• **Registered Users:** {api_metrics.get('total_users', 0)}\n"
        f"• **VIP Subscribers:** {api_metrics.get('vip_users', 0)}\n"
        f"• **Today's Activity:** 🎙️ {api_metrics.get('today_voice', 0)} voice • 💬 {api_metrics.get('today_text', 0)} texts\n"
        f"• **Process Memory:** {rss_mb:.1f} MB RSS\n"
        f"• **Versions:** Bot `{BOT_VERSION}` • Mini App `{MINI_APP_VERSION}` • Sec `{SECURITY_VERSION}`\n"
        f"• **Last Update:** `{LAST_UPDATE_DATE}`"
    )

    keyboard = {
        "inline_keyboard": [
            [{"text": "🔄 Refresh Quotas", "callback_data": "admin_refresh_quota"}],
            [{"text": "⬅️ Main Menu", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

# ==============================================================================
# TELEGRAM REAL PEOPLE 1-ON-1 ANONYMOUS CHAT ENGINE
# ==============================================================================
telegram_chat_queue: List[dict] = []
telegram_active_chats: Dict[int, dict] = {}

async def start_real_chat_pair(bot: TelegramClient, user_a: dict, user_b: dict):
    """Pairs two Telegram users 1-on-1 anonymously using their permanent Unique Joy IDs."""
    uid_a = user_a["user_id"]
    uid_b = user_b["user_id"]
    chat_id_a = user_a["chat_id"]
    chat_id_b = user_b["chat_id"]
    
    mask_a = get_mask_by_user_id(uid_a)
    mask_b = get_mask_by_user_id(uid_b)
    
    disp_a = mask_a
    disp_b = mask_b
    if disp_a == disp_b:
        disp_a = f"{mask_a}-1"
        disp_b = f"{mask_b}-2"
        
    telegram_active_chats[uid_a] = {
        "peer_uid": uid_b,
        "peer_chat_id": chat_id_b,
        "peer_mask": disp_b,
        "my_mask": disp_a,
        "started_at": time.time(),
        "msg_count": 0
    }
    telegram_active_chats[uid_b] = {
        "peer_uid": uid_a,
        "peer_chat_id": chat_id_a,
        "peer_mask": disp_a,
        "my_mask": disp_b,
        "started_at": time.time(),
        "msg_count": 0
    }
    
    # Increment daily usage count for real_chat channel
    increment_user_real_chat(uid_a)
    increment_user_real_chat(uid_b)
    
    reply_kb = {
        "keyboard": [
            [{"text": "⏭️ Next Partner"}, {"text": "🛑 End Chat"}]
        ],
        "resize_keyboard": True
    }
    
    msg_for_a = (
        f"🎉 **Match Found! 👥**\n\n"
        f"You are connected with **{disp_b}**!\n\n"
        f"🛡️ **100% Anonymous & Private:**\n"
        f"• Your identity is protected (they only see `{disp_a}`).\n"
        f"• Direct text & voice notes only (Photos & sensitive PII are strictly blocked).\n"
        f"• Be polite, respectful, and have fun chatting!\n\n"
        f"{LEGAL_DISCLAIMER_TEXT}\n"
        f"{PRIVACY_WARNING_TEXT}\n\n"
        f"💡 *Use the buttons below anytime to skip or end the chat.*"
    )
    
    msg_for_b = (
        f"🎉 **Match Found! 👥**\n\n"
        f"You are connected with **{disp_a}**!\n\n"
        f"🛡️ **100% Anonymous & Private:**\n"
        f"• Your identity is protected (they only see `{disp_b}`).\n"
        f"• Direct text & voice notes only (Photos & sensitive PII are strictly blocked).\n"
        f"• Be polite, respectful, and have fun chatting!\n\n"
        f"{LEGAL_DISCLAIMER_TEXT}\n"
        f"{PRIVACY_WARNING_TEXT}\n\n"
        f"💡 *Use the buttons below anytime to skip or end the chat.*"
    )
    
    await bot.send_message(chat_id_a, msg_for_a, reply_markup=reply_kb)
    await bot.send_message(chat_id_b, msg_for_b, reply_markup=reply_kb)
    logger.info(f"👥 Real Chat Pair Created: {disp_a} (UID {uid_a}) <---> {disp_b} (UID {uid_b})")

async def handle_anon_chat_start(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None, is_next: bool = False):
    """Enters matchmaking queue or connects with a waiting peer."""
    user_id = user["user_id"]
    
    # 1. Already in active chat
    if user_id in telegram_active_chats:
        pair = telegram_active_chats[user_id]
        reply_kb = {
            "keyboard": [
                [{"text": "⏭️ Next Partner"}, {"text": "🛑 End Chat"}]
            ],
            "resize_keyboard": True
        }
        await bot.send_message(
            chat_id,
            f"💬 **You are currently in an active chat with {pair['peer_mask']}!**\n\n"
            f"• Type your message below to send it to them.\n"
            f"• Tap **⏭️ Next Partner** to find someone new.\n"
            f"• Tap **🛑 End Chat** to leave.",
            reply_markup=reply_kb
        )
        return

    # 2. Check Daily Quota for 'real_chat'
    status = get_user_full_quota_status(user_id)
    real_chat_quota = status["channels"]["real_chat"]
    if not status["is_vip"] and real_chat_quota["remaining"] <= 0:
        limit_msg = (
            f"👥 **Daily Real People Chat Limit Reached**\n\n"
            f"You have used your **{real_chat_quota['limit']} free real chat conversations** for today!\n"
            f"Daily limits automatically reset every night at midnight UTC (05:30 IST).\n\n"
            f"⭐ **Upgrade to Joy VIP Pass** to unlock UNLIMITED real chats 24/7!\n"
            f"🎁 Or **refer friends** to earn bonus VIP access instantly."
        )
        keyboard = {
            "inline_keyboard": [
                [{"text": f"⭐ Unlock Joy VIP (₹{VIP_PRICE_INR}/mo)", "callback_data": "menu_vip"}],
                [{"text": "🎁 Refer Friends & Earn VIP", "callback_data": "menu_referral"}],
                [{"text": "📊 View My Quotas & Limits", "callback_data": "menu_quota"}],
                [{"text": "❌ Close", "callback_data": "menu_close"}]
            ]
        }
        await send_or_edit_menu(bot, chat_id, limit_msg, keyboard, message_id=message_id, user_msg_id=user_msg_id)
        return

    # 3. Already in queue
    if any(q["user_id"] == user_id for q in telegram_chat_queue):
        queue_kb = {
            "inline_keyboard": [
                [{"text": "❌ Cancel Search", "callback_data": "anon_chat_cancel"}]
            ]
        }
        await send_or_edit_menu(
            bot,
            chat_id,
            "🔍 **Still searching for someone online...**\n\n"
            "We'll notify you the moment another real person joins!\n\n"
            "💡 *Tap below if you want to cancel search:*",
            queue_kb,
            message_id=message_id,
            user_msg_id=user_msg_id
        )
        return

    # 4. Prune stale queue entries (> 15 mins)
    now = time.time()
    telegram_chat_queue[:] = [q for q in telegram_chat_queue if now - q.get("joined_at", now) < 900 and q["user_id"] != user_id]

    my_mask = get_mask_by_user_id(user_id)
    
    # 5. Look for matching peer
    matched_candidate = None
    for cand in telegram_chat_queue:
        cand_uid = cand["user_id"]
        cand_mask = cand.get("mask", "")
        # Safety Shield: Verify neither peer blocked the other
        if user_id != cand_uid and (is_peer_blocked(user_id, cand_mask) or is_peer_blocked(cand_uid, my_mask)):
            continue
        # Skip Cooldown Shield: Prevent immediate re-pairing of previously skipped users
        if telegram_skip_cooldown.get((user_id, cand_uid), 0) > now or telegram_skip_cooldown.get((cand_uid, user_id), 0) > now:
            continue
        matched_candidate = cand
        break

    if matched_candidate:
        telegram_chat_queue.remove(matched_candidate)
        user_b = {
            "user_id": matched_candidate["user_id"],
            "chat_id": matched_candidate["chat_id"]
        }
        user_a = {
            "user_id": user_id,
            "chat_id": chat_id
        }
        await start_real_chat_pair(bot, user_a, user_b)
    else:
        telegram_chat_queue.append({
            "user_id": user_id,
            "chat_id": chat_id,
            "mask": my_mask,
            "joined_at": time.time()
        })
        queue_kb = {
            "inline_keyboard": [
                [{"text": "💖 Chat with Joy Instead", "callback_data": "menu_main"}],
                [{"text": "❌ Cancel Search", "callback_data": "anon_chat_cancel"}]
            ]
        }
        if is_next:
            text = (
                f"⏳ **No other partners available right now.**\n\n"
                f"We placed you in the queue and will connect you the instant someone new joins!\n"
                f"Your anonymous mask is `{my_mask}`.\n\n"
                f"Or if you don't want to wait, tap below to chat with Joy anytime! 💖\n\n"
                f"{LEGAL_DISCLAIMER_TEXT}\n"
                f"{PRIVACY_WARNING_TEXT}"
            )
        else:
            text = (
                f"🔍 **Searching for someone to chat with...**\n\n"
                f"Looking for an active user online to connect with you.\n"
                f"Your anonymous mask is `{my_mask}`.\n\n"
                f"{LEGAL_DISCLAIMER_TEXT}\n"
                f"{PRIVACY_WARNING_TEXT}\n\n"
                f"Stay right here — we will connect you the instant a match joins!\n\n"
                f"💡 *Tap below if you want to cancel or chat with Joy:*"
            )
        await send_or_edit_menu(bot, chat_id, text, queue_kb, message_id=message_id, user_msg_id=user_msg_id)

async def handle_anon_chat_stop(bot: TelegramClient, chat_id: int, user: dict):
    """Disconnects active 1-on-1 chat or cancels queue search."""
    user_id = user["user_id"]
    
    # If in queue, remove
    if any(q["user_id"] == user_id for q in telegram_chat_queue):
        telegram_chat_queue[:] = [q for q in telegram_chat_queue if q["user_id"] != user_id]
        await bot.send_message(
            chat_id,
            "❌ **Match Search Cancelled**\n\nYou have left the matchmaking queue. Chat with Joy anytime! 💖",
            reply_markup={"remove_keyboard": True}
        )
        return
        
    pair = telegram_active_chats.pop(user_id, None)
    if not pair:
        await bot.send_message(
            chat_id,
            "ℹ️ You are not currently in an active chat. Tap below to find someone new or chat with Joy!",
            reply_markup={"remove_keyboard": True}
        )
        return
        
    peer_uid = pair["peer_uid"]
    peer_chat_id = pair["peer_chat_id"]
    peer_mask = pair["peer_mask"]
    my_mask = pair["my_mask"]
    
    # Pop peer
    telegram_active_chats.pop(peer_uid, None)

    # Set anti-reconnect skip cooldown between both users (300 seconds = 5 minutes)
    now = time.time()
    telegram_skip_cooldown[(user_id, peer_uid)] = now + 300
    telegram_skip_cooldown[(peer_uid, user_id)] = now + 300
    
    end_kb = {
        "inline_keyboard": [
            [{"text": "👥 Find New Match", "callback_data": "anon_chat_start"}],
            [{"text": "💖 Chat with Joy", "callback_data": "menu_main"}]
        ]
    }
    
    # Notify self
    await bot.send_message(
        chat_id,
        f"🛑 **Chat Ended**\n\nYou left the chat with **{peer_mask}**.\nYou are back in normal mode with Joy! 💖",
        reply_markup={"remove_keyboard": True}
    )
    await bot.send_message(chat_id, "Choose what you'd like to do next: 👇", reply_markup=end_kb)
    
    # Notify peer
    try:
        await bot.send_message(
            peer_chat_id,
            f"🛑 **Chat Ended**\n\nYour partner **{my_mask}** has left the chat.\nYou are back in normal mode with Joy! 💖",
            reply_markup={"remove_keyboard": True}
        )
        await bot.send_message(peer_chat_id, "Choose what you'd like to do next: 👇", reply_markup=end_kb)
    except Exception as e:
        logger.warning(f"Could not notify peer {peer_uid} of chat end: {e}")

async def handle_anon_chat_next(bot: TelegramClient, chat_id: int, user: dict):
    """Skips current partner and immediately finds a new match."""
    user_id = user["user_id"]
    pair = telegram_active_chats.pop(user_id, None)
    if not pair:
        await handle_anon_chat_start(bot, chat_id, user)
        return
        
    peer_uid = pair["peer_uid"]
    peer_chat_id = pair["peer_chat_id"]
    peer_mask = pair["peer_mask"]
    my_mask = pair["my_mask"]
    
    # Pop peer
    telegram_active_chats.pop(peer_uid, None)

    # Set anti-reconnect skip cooldown between both users (300 seconds = 5 minutes)
    now = time.time()
    telegram_skip_cooldown[(user_id, peer_uid)] = now + 300
    telegram_skip_cooldown[(peer_uid, user_id)] = now + 300
    
    end_kb = {
        "inline_keyboard": [
            [{"text": "👥 Find New Match", "callback_data": "anon_chat_start"}],
            [{"text": "💖 Chat with Joy", "callback_data": "menu_main"}]
        ]
    }
    
    # Notify peer politely
    try:
        await bot.send_message(
            peer_chat_id,
            f"⏭️ **Partner Skipped**\n\nYour partner **{my_mask}** skipped to find a new match.\nTap below to find someone new or chat with Joy!",
            reply_markup={"remove_keyboard": True}
        )
        await bot.send_message(peer_chat_id, "Choose what you'd like to do next: 👇", reply_markup=end_kb)
    except Exception as e:
        logger.warning(f"Could not notify peer {peer_uid} of partner skip: {e}")
        
    # Re-queue self immediately
    await handle_anon_chat_start(bot, chat_id, user, is_next=True)

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

    elif data == "admin_refresh_quota":
        if user_id == OWNER_ID:
            await bot.answer_callback_query(cq_id, "🔄 Updating cloud quotas...")
            await handle_admin_usage(bot, chat_id, user, message_id=message_id)
        else:
            await bot.answer_callback_query(cq_id, "⚠️ Restricted to bot administrator.", show_alert=True)
        return

    elif data.startswith("onboard_lang_"):
        new_lang = data.replace("onboard_lang_", "")
        set_user_language(user_id, new_lang)
        user["language"] = new_lang
        lang_title = LANGUAGE_NAMES.get(new_lang, "Auto-Detect")
        await bot.answer_callback_query(cq_id, f"🌐 Language set to {lang_title}!")
        asyncio.create_task(sync_user_to_cloud(user_id))

        gender = user.get("gender", "male")
        active_contact = user.get("active_contact", "lover")
        cinfo = get_user_contact_display(user_id, active_contact, gender)
        onboarding_status = user.get("onboarding_status", "completed")

        if onboarding_status == "completed":
            call_url = f"https://joyfun-ai-bot.onrender.com/call?gender={gender}&contact={active_contact}&lang={new_lang}&uid={user_id}&name={urllib.parse.quote(cinfo['name'])}"
            welcome_msg = (
                f"🎉 **Language set to {lang_title}!** 🌸\n\n"
                f"Your companion **{cinfo['emoji']} {cinfo['name']}** will now speak and chat with you in **{lang_title}**.\n\n"
                f"📞 Tap **Phone** below to start a live call, or explore the menu:"
            )
            keyboard = {
                "inline_keyboard": [
                    [{"text": "📞 Phone", "web_app": {"url": call_url}}],
                    [{"text": "📱 Main Menu", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
                ]
            }
            await send_or_edit_menu(bot, chat_id, welcome_msg, keyboard, message_id=message_id)
        else:
            first_name = (user.get("first_name") or user.get("username") or "Friend").strip()
            text = (
                f"🎉 **Language set to {lang_title}!** 🌸\n\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"> ❓ **Step 1 of 3: Hi {first_name}, what is your gender?**\n"
                f"> *Please select whether you are Male or Female:*\n"
                f"━━━━━━━━━━━━━━━━━━━"
            )
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "👨 Male", "callback_data": "onboard_gender_male"},
                        {"text": "👩 Female", "callback_data": "onboard_gender_female"}
                    ],
                    [
                        {"text": "❌ Close", "callback_data": "menu_close"}
                    ]
                ]
            }
            await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id)

    elif data == "onboard_gender_male":
        set_user_gender(user_id, "male")
        set_user_active_contact(user_id, "lover")
        user["gender"] = "male"
        user["active_contact"] = "lover"
        await bot.answer_callback_query(cq_id, "👨 Male selected!")
        await send_onboarding_naming(bot, chat_id, user, message_id=message_id)

    elif data == "onboard_gender_female":
        set_user_gender(user_id, "female")
        set_user_active_contact(user_id, "lover")
        user["gender"] = "female"
        user["active_contact"] = "lover"
        await bot.answer_callback_query(cq_id, "👩 Female selected!")
        await send_onboarding_naming(bot, chat_id, user, message_id=message_id)

    elif data.startswith("onboard_setname_"):
        name_choice = data.replace("onboard_setname_", "").strip()
        if name_choice == "Joy":
            reset_user_custom_ai_name(user_id)
        else:
            set_user_custom_ai_name(user_id, name_choice)
        await bot.answer_callback_query(cq_id, f"🌸 Named '{name_choice}'!")
        await send_onboarding_privacy(bot, chat_id, user, message_id=message_id)

    elif data == "onboard_privacy_private":
        if is_contributor_discount_locked(user_id):
            await bot.answer_callback_query(
                cq_id,
                "🔒 Contributor Agreement Active!\nYou have an active VIP subscription purchased with the 20% Contributor discount. Data sharing remains enabled.",
                show_alert=True
            )
            await complete_onboarding(bot, chat_id, user, share_data=True, message_id=message_id)
        else:
            await bot.answer_callback_query(cq_id, "🔒 100% Private Mode enabled!")
            await complete_onboarding(bot, chat_id, user, share_data=False, message_id=message_id)

    elif data == "onboard_privacy_share":
        await bot.answer_callback_query(cq_id, "🤝 Thank you for helping train Joy!")
        await complete_onboarding(bot, chat_id, user, share_data=True, message_id=message_id)

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
        label = "👨 Male" if new_g == "male" else "👩 Female"
        await bot.answer_callback_query(cq_id, f"Switched to {label}!")
        asyncio.create_task(sync_user_to_cloud(user_id))
        await handle_menu(bot, chat_id, user, message_id=message_id)

    elif data.startswith("set_gender_"):
        new_g = data.replace("set_gender_", "")
        set_user_gender(user_id, new_g)
        set_user_active_contact(user_id, "lover")
        user["gender"] = new_g
        user["active_contact"] = "lover"
        label = "👨 Male" if new_g == "male" else "👩 Female"
        await bot.answer_callback_query(cq_id, f"Switched to {label}!")
        asyncio.create_task(sync_user_to_cloud(user_id))
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
        asyncio.create_task(sync_user_to_cloud(user_id))
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

    elif data == "menu_study":
        await bot.answer_callback_query(cq_id)
        await handle_study_menu(bot, chat_id, user, message_id=message_id)

    elif data == "study_quiz":
        await bot.answer_callback_query(cq_id, "🧠 Quizzer Activated!")
        set_user_onboarding_status(user_id, "waiting_study_quiz")
        quiz_prompt = (
            "🧠 **Active Recall Quizzer Ready!** 🎯\n\n"
            "Send me any topic, concept, or paste a note from your college syllabus:\n"
            "*(e.g. 'Operating System Deadlocks', 'Pointers in C', 'DBMS Normalization', 'Photosynthesis', or 'Data Structures')*\n\n"
            "I will give you a 2-sentence summary and 3 rapid recall questions to test how well you remember it! 🔥"
        )
        keyboard = {
            "inline_keyboard": [
                [{"text": "⬅️ Back to Study Hub", "callback_data": "menu_study"}, {"text": "❌ Cancel", "callback_data": "menu_close"}]
            ]
        }
        await send_or_edit_menu(bot, chat_id, quiz_prompt, keyboard, message_id=message_id)

    elif data == "study_eli5":
        await bot.answer_callback_query(cq_id, "👶 ELI5 Explainer Activated!")
        set_user_onboarding_status(user_id, "waiting_study_eli5")
        eli5_prompt = (
            "👶 **ELI5 Concept Explainer Ready!** 💡\n\n"
            "Send me any confusing, boring, or hard concept that you want explained simply:\n"
            "*(e.g. 'Virtual Memory', 'Recursion', 'Quantum Superposition', 'Transformer Models', or 'Inflation')*\n\n"
            "I'll break it down using a hilarious, relatable real-world analogy with zero academic jargon! 🌸"
        )
        keyboard = {
            "inline_keyboard": [
                [{"text": "⬅️ Back to Study Hub", "callback_data": "menu_study"}, {"text": "❌ Cancel", "callback_data": "menu_close"}]
            ]
        }
        await send_or_edit_menu(bot, chat_id, eli5_prompt, keyboard, message_id=message_id)

    elif data == "study_pomo_25":
        await bot.answer_callback_query(cq_id, "⏱️ 25-Min Sprint Started!")
        pomo_start = (
            "⏱️ **25-Minute Deep Focus Sprint Started!** 🚀\n\n"
            "Put your phone on Do Not Disturb, close social media, and get completely locked in on your books.\n"
            "I am actively tracking your 25 minutes right now.\n\n"
            "🔔 I will ping you here the moment it's break time. Go crush this session! 🔥"
        )
        keyboard = {
            "inline_keyboard": [
                [{"text": "⬅️ Study Hub", "callback_data": "menu_study"}, {"text": "❌ Close", "callback_data": "menu_close"}]
            ]
        }
        await send_or_edit_menu(bot, chat_id, pomo_start, keyboard, message_id=message_id)
        asyncio.create_task(run_pomodoro_timer(bot, chat_id, user_id, 25))

    elif data == "menu_feedback":
        await bot.answer_callback_query(cq_id)
        await handle_feedback_menu(bot, chat_id, user, message_id=message_id)

    elif data == "menu_settings":
        await bot.answer_callback_query(cq_id)
        await handle_settings(bot, chat_id, user, message_id=message_id)

    elif data == "menu_privacy":
        await bot.answer_callback_query(cq_id)
        await handle_privacy_menu(bot, chat_id, user, message_id=message_id)

    elif data == "menu_terms":
        await bot.answer_callback_query(cq_id)
        await handle_terms_menu(bot, chat_id, user, message_id=message_id)

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
        if curr:
            if is_contributor_discount_locked(user_id):
                alert_msg = "🔒 Contributor Agreement Active!\n\nYou unlocked and purchased your current VIP subscription with the 20% Contributor discount. To honor the discount agreement, data sharing remains active for the duration of this VIP billing period."
                await bot.answer_callback_query(cq_id, alert_msg, show_alert=True)
                await handle_privacy_menu(bot, chat_id, user, message_id=message_id)
                return
            set_user_data_sharing(user_id, False)
            await bot.answer_callback_query(cq_id, "🔒 Data sharing disabled! 100% private.")
        else:
            set_user_data_sharing(user_id, True)
            await bot.answer_callback_query(cq_id, "💡 Data sharing enabled! 20% VIP discount unlocked.")
        await handle_privacy_menu(bot, chat_id, user, message_id=message_id)

    elif data == "menu_language":
        await bot.answer_callback_query(cq_id)
        await handle_language_menu(bot, chat_id, user, message_id=message_id)

    elif data == "menu_country":
        await bot.answer_callback_query(cq_id)
        await handle_country_menu(bot, chat_id, user, message_id=message_id)

    elif data.startswith("set_country_"):
        new_country = data.replace("set_country_", "").strip().upper()
        set_user_country(user_id, new_country)
        c_info = get_country_display(new_country)
        await bot.answer_callback_query(cq_id, f"🌍 Country set to {c_info['display']}!")
        asyncio.create_task(sync_user_to_cloud(user_id))
        user = get_or_create_user(user_id)
        await handle_settings(bot, chat_id, user, message_id=message_id)

    elif data == "menu_rename_ai":
        await bot.answer_callback_query(cq_id)
        await handle_rename_menu(bot, chat_id, user, message_id=message_id)

    elif data == "rename_reset":
        reset_user_custom_ai_name(user_id)
        set_user_onboarding_status(user_id, "completed")
        asyncio.create_task(sync_user_to_cloud(user_id))
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
        asyncio.create_task(sync_user_to_cloud(user_id))
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

    elif data == "menu_referral":
        await bot.answer_callback_query(cq_id)
        await handle_referral_hub(bot, chat_id, user, message_id=message_id)

    elif data == "pay_vip_stars":
        await bot.answer_callback_query(cq_id, "⭐ Generating Telegram Stars invoice...")
        data_shared = get_user_data_sharing(user_id)
        stars_amount = 120 if data_shared else 150
        inv_title = "⭐ Joy VIP Pass (20% Off)" if data_shared else "⭐ Joy VIP Pass (30 Days)"
        inv_res = await bot.create_invoice_link(
            title=inv_title,
            description="Unlimited 24/7 Live Voice Calls, Voice Notes, & Zero Ads with Joy AI",
            payload=f"vip_30d_{user_id}",
            currency="XTR",
            prices=[{"label": inv_title, "amount": stars_amount}]
        )
        if inv_res.get("ok") and inv_res.get("result"):
            invoice_url = inv_res["result"]
            discount_badge = "\n🎁 **20% Data Contributor Discount Applied!**" if data_shared else ""
            inv_text = (
                f"⭐ **Telegram Stars Instant Payment**\n\n"
                f"• **Plan:** Joy VIP Pass (30 Days)\n"
                f"• **Price:** `{stars_amount} Telegram Stars`\n"
                f"{discount_badge}\n"
                f"• **Activation:** 100% Instant & Automatic\n\n"
                f"Tap **⭐ Pay {stars_amount} Stars** below to complete your payment in 1 tap!"
            )
            inv_keyboard = {
                "inline_keyboard": [
                    [{"text": f"⭐ Pay {stars_amount} Stars Now", "url": invoice_url}],
                    [{"text": "⬅️ Back", "callback_data": "menu_vip"}, {"text": "❌ Close", "callback_data": "menu_close"}]
                ]
            }
            await send_or_edit_menu(bot, chat_id, inv_text, inv_keyboard, message_id=message_id)
        else:
            err = inv_res.get("description", "Could not generate invoice. Please try again.")
            await bot.send_message(chat_id, f"⚠️ Telegram Stars invoice error: {err}")

    elif data == "pay_vip_upi":
        await bot.answer_callback_query(cq_id)
        upi_uri = f"upi://pay?pa={UPI_ID}&pn=JoyAI&am={VIP_PRICE_INR}&cu=INR&tn=VIP_{user_id}"
        upi_text = (
            f"🇮🇳 **Instant ₹{VIP_PRICE_INR} VIP Upgrade / Quota Reset**\n\n"
            f"Pay **₹{VIP_PRICE_INR}** via any UPI app (GPay, PhonePe, Paytm, CRED, BHIM):\n\n"
            f"• **UPI ID:** `{UPI_ID}` *(Tap to copy)*\n"
            f"• **Amount:** `₹{VIP_PRICE_INR}` (Valid 30 Days)\n"
            f"• **Note / Remarks:** `VIP_{user_id}`\n\n"
            f"📲 **How to complete:**\n"
            f"1. Tap the button below to open your UPI app, or send **₹{VIP_PRICE_INR}** to `{UPI_ID}`.\n"
            f"2. After paying, tap **📝 Submit 12-Digit UTR Number** below.\n"
            f"3. Paste your 12-digit transaction UTR number to verify and unlock instantly!\n\n"
            f"⚡ *All quotas are immediately reset once verified.*"
        )
        upi_keyboard = {
            "inline_keyboard": [
                [{"text": "📲 Open UPI / GPay App", "url": upi_uri}],
                [{"text": "📝 Submit 12-Digit UTR Number", "callback_data": "prompt_submit_utr"}],
                [{"text": "⬅️ Back", "callback_data": "menu_vip"}, {"text": "❌ Close", "callback_data": "menu_close"}]
            ]
        }
        await send_or_edit_menu(bot, chat_id, upi_text, upi_keyboard, message_id=message_id)

    elif data == "prompt_submit_utr":
        await bot.answer_callback_query(cq_id)
        user_waiting_utr[user_id] = True
        prompt_text = (
            f"📝 **Submit UPI 12-Digit UTR Number**\n\n"
            f"Please type or paste your **12-digit UPI Transaction / UTR number** directly in this chat.\n\n"
            f"Example: `429182910394`\n\n"
            f"*(You can find this 12-digit reference number in your GPay / PhonePe / Paytm receipt)*\n\n"
            f"Send it as a message below: 👇"
        )
        prompt_kb = {
            "inline_keyboard": [
                [{"text": "❌ Cancel", "callback_data": "cancel_utr_submit"}]
            ]
        }
        await send_or_edit_menu(bot, chat_id, prompt_text, prompt_kb, message_id=message_id)

    elif data == "cancel_utr_submit":
        await bot.answer_callback_query(cq_id, "Submission cancelled.")
        user_waiting_utr.pop(user_id, None)
        await handle_vip_purchase(bot, chat_id, user, message_id=message_id)

    elif data.startswith("approve_utr_"):
        if user_id != OWNER_ID:
            await bot.answer_callback_query(cq_id, "⚠️ Restricted to administrator.", show_alert=True)
            return
        req_id = int(data.replace("approve_utr_", "").strip())
        res = approve_payment_request(req_id)
        if res:
            p_uid = res["user_id"]
            utr = res["utr"]
            await bot.answer_callback_query(cq_id, f"✅ Approved UTR {utr}!")
            if message_id:
                await bot.edit_message_text(chat_id, message_id, f"✅ **Approved Payment #{req_id}**\n• User: `{p_uid}`\n• UTR: `{utr}`\n• Status: Activated (30 Days VIP & Quota Reset)")
            try:
                await bot.send_message(
                    p_uid,
                    f"🎉 **Payment Verified! VIP Pass Activated!** 🌟\n\n"
                    f"Your payment of **₹149** (UTR: `{utr}`) has been verified successfully!\n\n"
                    f"🚀 **Your VIP Perks are Live for 30 Days:**\n"
                    f"• Unlimited 24/7 AI Voice Calls\n"
                    f"• Unlimited Texts & Voice Notes\n"
                    f"• Unlimited 1-on-1 Real Partner Chats\n"
                    f"• Zero wait times & maximum priority voice engine!\n\n"
                    f"Enjoy chatting with Joy! 💖"
                )
            except Exception as pe:
                logger.warning(f"Could not notify user {p_uid} of VIP approval: {pe}")
        else:
            await bot.answer_callback_query(cq_id, "Already verified or invalid request.", show_alert=True)

    elif data.startswith("reject_utr_"):
        if user_id != OWNER_ID:
            await bot.answer_callback_query(cq_id, "⚠️ Restricted to administrator.", show_alert=True)
            return
        req_id = int(data.replace("reject_utr_", "").strip())
        res = reject_payment_request(req_id)
        if res:
            p_uid = res["user_id"]
            utr = res["utr"]
            await bot.answer_callback_query(cq_id, f"❌ Rejected UTR {utr}")
            if message_id:
                await bot.edit_message_text(chat_id, message_id, f"❌ **Rejected Payment #{req_id}**\n• User: `{p_uid}`\n• UTR: `{utr}`\n• Status: Rejected / Invalid")
            try:
                await bot.send_message(
                    p_uid,
                    f"⚠️ **Payment Verification Notice**\n\n"
                    f"We could not verify transaction UTR `{utr}` on our banking gateway.\n"
                    f"Please check your UPI app statement, copy the exact 12-digit UTR, and submit again.\n"
                    f"If money was deducted, message @phoenix_parava_0 with a screenshot."
                )
            except Exception as pe:
                logger.warning(f"Could not notify user {p_uid} of VIP rejection: {pe}")
        else:
            await bot.answer_callback_query(cq_id, "Already handled or invalid request.", show_alert=True)

    elif data == "menu_tip":
        await bot.answer_callback_query(cq_id)
        await handle_tip_menu(bot, chat_id, user, message_id=message_id)

    elif data.startswith("send_tip_"):
        stars_amount = int(data.replace("send_tip_", "").strip())
        await bot.answer_callback_query(cq_id, f"⭐ Preparing {stars_amount} Stars gift...")
        inv_res = await bot.create_invoice_link(
            title=f"⭐ {stars_amount} Stars Gift for Joy",
            description=f"Voluntary Stars gift to support Joy AI companion development & server costs",
            payload=f"tip_{stars_amount}_{user_id}",
            currency="XTR",
            prices=[{"label": f"{stars_amount} Stars Gift", "amount": stars_amount}]
        )
        if inv_res.get("ok") and inv_res.get("result"):
            invoice_url = inv_res["result"]
            inv_text = (
                f"⭐ **Send {stars_amount} Stars Gift** 💖\n\n"
                f"• **Amount:** `{stars_amount} Telegram Stars`\n"
                f"• **Type:** Voluntary Gift to Support Creator & AI\n\n"
                f"Tap **⭐ Send {stars_amount} Stars Now** below to complete in 1 tap!"
            )
            inv_keyboard = {
                "inline_keyboard": [
                    [{"text": f"⭐ Send {stars_amount} Stars Now", "url": invoice_url}],
                    [{"text": "⬅️ Back", "callback_data": "menu_tip"}, {"text": "❌ Close", "callback_data": "menu_close"}]
                ]
            }
            await send_or_edit_menu(bot, chat_id, inv_text, inv_keyboard, message_id=message_id)
        else:
            err = inv_res.get("description", "Could not generate invoice. Please try again.")
            await bot.send_message(chat_id, f"⚠️ Error generating Stars gift link: {err}")
        
    elif data in ("menu_stats", "menu_quota", "menu_limits", "menu_balance", "menu_refresh_quota"):
        await bot.answer_callback_query(cq_id)
        await handle_quota_menu(bot, chat_id, user, message_id=message_id)

    elif data in ("quota_ad_recharge", "ad_watch"):
        await bot.answer_callback_query(cq_id)
        await handle_referral_hub(bot, chat_id, user, message_id=message_id)

    elif data == "anon_chat_start":
        await bot.answer_callback_query(cq_id)
        await handle_anon_chat_start(bot, chat_id, user, message_id=message_id)

    elif data == "anon_chat_cancel":
        await bot.answer_callback_query(cq_id, "Search cancelled.")
        user_id = user["user_id"]
        telegram_chat_queue[:] = [q for q in telegram_chat_queue if q["user_id"] != user_id]
        await handle_menu(bot, chat_id, user, message_id=message_id)

    elif data == "anon_chat_stop":
        await bot.answer_callback_query(cq_id)
        await handle_anon_chat_stop(bot, chat_id, user)

    elif data == "anon_chat_next":
        await bot.answer_callback_query(cq_id)
        await handle_anon_chat_next(bot, chat_id, user)

async def process_user_voice(bot: TelegramClient, chat_id: int, user: dict, file_id: str):
    user_id = user["user_id"]
    
    # 0. Check if user is in active Real People 1-on-1 Chat
    if user_id in telegram_active_chats:
        pair = telegram_active_chats[user_id]
        peer_chat_id = pair["peer_chat_id"]
        sender_mask = pair["my_mask"]
        pair["msg_count"] += 1
        try:
            await bot.send_voice_file_id(peer_chat_id, file_id, caption=f"🎙️ Voice Note from {sender_mask}")
        except Exception as e:
            logger.warning(f"Error forwarding voice note to peer {peer_chat_id}: {e}")
            await bot.send_message(chat_id, "⚠️ Your partner seems unreachable. Ending chat...")
            await handle_anon_chat_stop(bot, chat_id, user)
        return

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
        await send_quota_exhausted_screen(bot, chat_id, user, c_name, c_emoji, reason_text)
        return

    # 2. Indicate listening status
    await bot.send_chat_action(chat_id, "record_voice")
    
    # 3. Download voice note from Telegram
    voice_bytes = await bot.get_file_bytes(file_id)
    if not voice_bytes:
        await bot.send_message(chat_id, "Couldn't catch that audio note cleanly. Mind sending it again?")
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
        async with AI_CALL_SEMAPHORE:
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
                timeout=12.0
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
    else:
        reply_text = humanize_ai_response(reply_text)

    # Save to history
    add_conversation_turn(user_id, "user", transcript)
    add_conversation_turn(user_id, "model", reply_text)
    
    # Update Daily Streak & Relationship Bond
    streak_count, rel_level, is_milestone, level_title = update_user_streak(user_id)
    if is_milestone:
        c_name = custom_ai_name or "Joy"
        milestone_msg = (
            f"🔥 **Relationship Milestone: Day {streak_count} Streak!**\n\n"
            f"Relationship Level: **{level_title}** 💕\n"
            f"{c_name} loves chatting with you every single day! Keep the streak alive tomorrow! ✨"
        )
        asyncio.create_task(bot.send_message(chat_id, milestone_msg))
    
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
    clean_text = text.strip()
    lower_text = clean_text.lower()
    onboarding_status = user.get("onboarding_status", "completed")

    # Check if user is currently submitting a UPI 12-digit UTR Transaction ID
    if user_waiting_utr.get(user_id) and not clean_text.startswith("/"):
        clean_utr = re.sub(r'[^0-9A-Za-z]', '', clean_text.strip()).upper()
        if len(clean_utr) < 8 or len(clean_utr) > 24:
            await bot.send_message(
                chat_id,
                "⚠️ **Invalid UTR Format**\n\n"
                "A standard UPI transaction reference number (UTR) is usually 12 digits (e.g. `429182910394`).\n"
                "Please check your payment receipt in GPay / PhonePe / Paytm and enter the valid reference number, or tap below to cancel.",
                reply_markup={"inline_keyboard": [[{"text": "❌ Cancel Submission", "callback_data": "cancel_utr_submit"}]]}
            )
            return

        user_waiting_utr.pop(user_id, None)
        success, utr_msg, req_id = record_utr_submission(user_id, clean_utr, amount=149.0)
        if not success:
            await bot.send_message(
                chat_id,
                f"⚠️ **Submission Notice:** {utr_msg}",
                reply_markup={"inline_keyboard": [
                    [{"text": "🔄 Try Again", "callback_data": "prompt_submit_utr"}],
                    [{"text": "⬅️ Back to VIP Menu", "callback_data": "menu_vip"}]
                ]}
            )
            return

        await bot.send_message(
            chat_id,
            f"✅ **Payment Details Received!**\n\n"
            f"• **UTR Reference:** `{clean_utr}`\n"
            f"• **Amount:** `₹149`\n"
            f"• **Status:** Under verification ⏳\n\n"
            f"Our system will verify the transaction and unlock your VIP Pass with unlimited access shortly!\n"
            f"Thank you for supporting Joy! 💖"
        )

        # Notify Bot Administrator (OWNER_ID)
        try:
            user_full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or "Joy User"
            username = f"@{user.get('username')}" if user.get('username') else "No username"
            admin_msg = (
                f"🔔 **New UPI VIP Payment Submission!**\n\n"
                f"• **User:** `{user_full_name}` ({username})\n"
                f"• **User ID:** `{user_id}`\n"
                f"• **Amount:** `₹149`\n"
                f"• **UTR:** `{clean_utr}`\n"
                f"• **Request ID:** `#{req_id}`\n\n"
                f"Please verify against your bank / UPI notification and tap below:"
            )
            admin_kb = {
                "inline_keyboard": [
                    [
                        {"text": "✅ Approve & Unlock VIP", "callback_data": f"approve_utr_{req_id}"},
                        {"text": "❌ Reject", "callback_data": f"reject_utr_{req_id}"}
                    ]
                ]
            }
            await bot.send_message(OWNER_ID, admin_msg, reply_markup=admin_kb)
        except Exception as ae:
            logger.error(f"Failed to send payment approval alert to admin: {ae}")
        return

    if clean_text.startswith("/"):
        user_waiting_utr.pop(user_id, None)

    # 0. Check if user is in active Real People 1-on-1 Chat
    if user_id in telegram_active_chats:
        if clean_text in ["/stop", "/end", "/leave", "stop", "leave", "🛑 End Chat", "End Chat"]:
            await handle_anon_chat_stop(bot, chat_id, user)
            return
        elif clean_text in ["/next", "/skip", "next", "skip", "⏭️ Next Partner", "Next Partner"]:
            await handle_anon_chat_next(bot, chat_id, user)
            return
        elif clean_text.startswith("/"):
            await bot.send_message(
                chat_id,
                "⚠️ **You are currently in an anonymous 1-on-1 chat with a real person!**\n\n"
                "• Send any text to talk to them.\n"
                "• Tap **⏭️ Next Partner** (or /next) to find someone new.\n"
                "• Tap **🛑 End Chat** (or /stop) to leave and return to Joy."
            )
            return
        else:
            pair = telegram_active_chats[user_id]
            peer_chat_id = pair["peer_chat_id"]
            sender_mask = pair["my_mask"]

            # PII & Sensitive Personal Data Interceptor
            has_pii, pii_type = detect_sensitive_pii(text)
            if has_pii:
                logger.warning(f"🛡️ PII Guard Intercepted {pii_type} from {sender_mask} (UID {user_id})")
                guard_msg = (
                    f"⚠️ **Message Blocked — Sensitive Personal Data Detected**\n\n"
                    f"Your message was intercepted before sending because it contains sensitive personal details (**{pii_type}**).\n\n"
                    f"{LEGAL_DISCLAIMER_TEXT}\n"
                    f"{PRIVACY_WARNING_TEXT}"
                )
                await bot.send_message(chat_id, guard_msg)
                return

            pair["msg_count"] += 1
            try:
                await bot.send_message(peer_chat_id, f"🎭 **{sender_mask}:**\n{text}")
            except Exception as e:
                logger.warning(f"Error forwarding text to peer {peer_chat_id}: {e}")
                await bot.send_message(chat_id, "⚠️ Your partner seems unreachable. Ending chat...")
                await handle_anon_chat_stop(bot, chat_id, user)
            return

    # 0.5. Check if user is waiting in Real People Matchmaking Queue
    if any(q["user_id"] == user_id for q in telegram_chat_queue):
        if clean_text in ["/stop", "/cancel", "cancel", "stop", "❌ Cancel Search"]:
            await handle_anon_chat_stop(bot, chat_id, user)
            return
        else:
            queue_kb = {
                "inline_keyboard": [
                    [{"text": "❌ Cancel Search", "callback_data": "anon_chat_cancel"}]
                ]
            }
            await bot.send_message(
                chat_id,
                "🔍 **Still searching for someone online to connect with you...**\n\n"
                "Stay right here — we'll connect you the moment someone joins!\n\n"
                "💡 *Tap below if you want to cancel search:*",
                reply_markup=queue_kb
            )
            return

    user["active_contact"] = "lover"  # Enforce Lover (Joy) as the active companion

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

        # Back up memory & profile to Cloud (Google Drive + Notion)
        asyncio.create_task(sync_user_to_cloud(user_id))

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

    # 1.5 Handle Step 2 Companion Naming during Onboarding
    if onboarding_status == "onboard_naming" and not clean_text.startswith("/"):
        new_name = clean_text.strip()[:30]
        if new_name.lower() in ["joy", "default", "none"]:
            reset_user_custom_ai_name(user_id)
        else:
            set_user_custom_ai_name(user_id, new_name)
        asyncio.create_task(sync_user_to_cloud(user_id))
        await send_onboarding_privacy(bot, chat_id, user, user_msg_id=msg_id)
        return

    # 2. Handle Custom AI Companion Renaming
    if onboarding_status == "waiting_ai_name" and not clean_text.startswith("/"):
        new_name = clean_text.strip()[:30]
        set_user_custom_ai_name(user_id, new_name)
        set_user_onboarding_status(user_id, "completed")
        asyncio.create_task(sync_user_to_cloud(user_id))
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
            asyncio.create_task(sync_user_to_cloud(user_id))
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

    # 5. Handle Active Recall Quiz Input
    if onboarding_status == "waiting_study_quiz" and not clean_text.startswith("/"):
        set_user_onboarding_status(user_id, "completed")
        user_lang = user.get("language", "auto")
        lang_title = LANGUAGE_NAMES.get(user_lang, "Auto-Detect")
        await bot.send_chat_action(chat_id, "typing")

        study_prompt = (
            f"You are Joy, an energetic, friendly, and brilliant college study buddy.\n"
            f"The user wants to study this topic: '{clean_text}'.\n\n"
            f"Provide a structured, engaging study response:\n"
            f"1. 💡 **Core Summary (2 Sentences):** Explain the core concept clearly with an intuitive analogy.\n"
            f"2. 🎯 **Rapid Active Recall Quiz (3 Questions):**\n"
            f"   - Question 1 (Multiple choice with options A, B, C, D)\n"
            f"   - Question 2 (Multiple choice with options A, B, C, D)\n"
            f"   - Question 3 (Short concept question to test deep understanding)\n"
            f"3. 🚀 **Call to Action:** 'Reply with your answer to Question 1! Let's see how strong your memory is! 🔥'\n\n"
            f"Speak warmly in {lang_title}."
        )
        try:
            quiz_resp = await generate_text_reply(study_prompt, user_id=user_id)
            gender = user.get("gender", "male")
            active_contact = user.get("active_contact", "lover")
            c_name = get_user_custom_ai_name(user_id)
            reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=c_name)
            await bot.send_message(chat_id, quiz_resp, reply_markup=reply_kb)
        except Exception as e:
            logger.error(f"Error generating study quiz: {e}")
            await bot.send_message(chat_id, f"📚 Let's quiz **{clean_text}**!\n\nQuestion 1: What is the primary purpose or function of {clean_text}?\nReply with your answer and I'll grade you! 🎯")
        return

    # 6. Handle ELI5 Concept Explainer Input
    if onboarding_status == "waiting_study_eli5" and not clean_text.startswith("/"):
        set_user_onboarding_status(user_id, "completed")
        user_lang = user.get("language", "auto")
        lang_title = LANGUAGE_NAMES.get(user_lang, "Auto-Detect")
        await bot.send_chat_action(chat_id, "typing")

        eli5_prompt = (
            f"You are Joy, a fun, super smart study buddy.\n"
            f"Explain this concept to a college student like they are 5 years old: '{clean_text}'.\n"
            f"Use a funny, relatable real-world analogy (like hostel mess food, chai stall, cricket, or mobile phones).\n"
            f"Keep it under 150 words with zero confusing jargon.\n"
            f"Speak warmly in {lang_title}."
        )
        try:
            eli5_resp = await generate_text_reply(eli5_prompt, user_id=user_id)
            gender = user.get("gender", "male")
            active_contact = user.get("active_contact", "lover")
            c_name = get_user_custom_ai_name(user_id)
            reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=c_name)
            await bot.send_message(chat_id, f"👶 **ELI5: {clean_text}** 💡\n\n{eli5_resp}", reply_markup=reply_kb)
        except Exception as e:
            logger.error(f"Error generating ELI5: {e}")
            await bot.send_message(chat_id, f"💡 **{clean_text} in Simple Words:** Think of it like a smart manager coordinating everyone so no work gets lost! Need a quiz? Type `/study`! 🌸")
        return
    
    # Check commands & persistent keyboard button presses
    if clean_text.startswith("/newuser") or clean_text.lower() in ["newuser", "/freshuser", "freshuser", "/resetall", "new user"]:
        from database import get_connection
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET onboarding_status = 'new', 
                    custom_ai_name = '', 
                    allow_data_sharing = 0,
                    gender = 'male',
                    active_contact = 'lover',
                    language = 'auto'
                WHERE user_id = ?
            """, (user_id,))
            cursor.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
            conn.commit()

        user["onboarding_status"] = "new"
        user["custom_ai_name"] = ""
        user["gender"] = "male"
        user["active_contact"] = "lover"
        user["allow_data_sharing"] = 0
        user["language"] = "auto"

        # Clean up any active real people chat or queue
        if user_id in telegram_active_chats:
            await handle_anon_chat_stop(bot, chat_id, user)
        telegram_chat_queue[:] = [q for q in telegram_chat_queue if q["user_id"] != user_id]

        await dismiss_active_menu(bot, chat_id)
        await bot.send_message(
            chat_id,
            "🔄 **Account Reset Complete!**\n\nYour profile, companion name, and history have been wiped to test the brand-new user experience.\nLaunching the 3-step setup flow for you right now: 👇",
            reply_markup={"remove_keyboard": True}
        )
        await asyncio.sleep(0.5)
        await send_onboarding_welcome(bot, chat_id, user)
        return

    elif clean_text.startswith("/start"):
        parts = clean_text.split()
        if len(parts) > 1:
            param = parts[1].strip()
            if param.startswith("ref_"):
                try:
                    referrer_id = int(param.replace("ref_", "").strip())
                    track_user_referral(user_id, referrer_id)
                except Exception:
                    pass
            elif param in ["real_chat", "chat", "match", "anon"]:
                await handle_anon_chat_start(bot, chat_id, user, user_msg_id=msg_id)
                return
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
                asyncio.create_task(sync_user_to_cloud(user_id))
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
                asyncio.create_task(sync_user_to_cloud(user_id))
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
    elif clean_text.startswith("/sync") or clean_text.startswith("/backup") or clean_text.startswith("/export") or clean_text.lower() in [
        "sync", "backup", "cloud sync", "export", "download backup", "my backup", "save cloud", "save"
    ]:
        await bot.send_chat_action(chat_id, "upload_document")
        await sync_user_to_cloud(user_id)

        oauth = get_user_google_oauth(user_id)
        g_email = oauth.get("email") or get_user_google_email(user_id)
        has_drive = bool(oauth.get("refresh_token") or oauth.get("access_token"))
        drive_status = f"✅ Synced to personal Google Drive (`{g_email}`)" if has_drive else "⚪ Not Connected (1-Click Connect below)"
        custom_name = get_user_custom_ai_name(user_id) or "Joy"
        gender_title = "👨 Male" if user.get("gender") == "male" else "👩 Female"
        lang_title = LANGUAGE_NAMES.get(user.get("language", "auto"), "Auto-Detect")

        backup_str = generate_user_backup_json(user_id)
        backup_bytes = backup_str.encode("utf-8")
        filename = f"Joy_Backup_{user_id}.json"
        caption = (
            "☁️ **Dual Cloud Backup & Settings Sync Complete!**\n\n"
            f"👤 **Perspective:** {gender_title}\n"
            f"🌐 **Language:** {lang_title}\n"
            f"🌸 **Companion Name:** **{custom_name}**\n\n"
            f"📌 **Cloud Status:**\n"
            f"• **Notion Cloud DB:** ✅ Saved & Protected across all server recodes\n"
            f"• **Personal Google Drive:** {drive_status}\n\n"
            "📁 *Your complete portable JSON backup is attached below.*"
        )
        reply_markup = None
        if not has_drive:
            connect_url = f"https://joyfun-ai-bot.onrender.com/auth/google/login?uid={user_id}"
            reply_markup = {
                "inline_keyboard": [
                    [{"text": "🔐 Connect Google Drive (1-Click Sync)", "url": connect_url}]
                ]
            }
        await bot.send_document(chat_id, backup_bytes, filename=filename, caption=caption, reply_markup=reply_markup)
        return
    elif clean_text.startswith("/google") or clean_text.startswith("/login") or clean_text.lower() in [
        "login", "🔐 login", "🔐 login & sync", "login & sync", "cloud login", "google", "connect google"
    ]:
        parts = clean_text.split(maxsplit=1)
        if len(parts) > 1 and not clean_text.lower().startswith("🔐"):
            email_cand = parts[1].strip().lower()
            if "@" in email_cand and "." in email_cand:
                set_user_google_email(user_id, email_cand)
                set_user_onboarding_status(user_id, "completed")
                asyncio.create_task(sync_user_to_cloud(user_id))
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
    elif clean_text.startswith("/gender") or clean_text.lower() in ["gender", "switch gender", "male", "female", "boy", "girl", "view", "👤 gender"]:
        curr_g = user.get("gender", "male")
        new_g = "female" if curr_g == "male" else "male"
        set_user_gender(user_id, new_g)
        set_user_active_contact(user_id, "lover")
        user["gender"] = new_g
        user["active_contact"] = "lover"
        asyncio.create_task(sync_user_to_cloud(user_id))
        await handle_menu(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/chat") or clean_text.startswith("/match") or clean_text.startswith("/find") or clean_text.startswith("/anon") or clean_text.lower() in ["chat", "match", "find", "anon", "👥 chat real people", "chat real people", "chat with real people"]:
        await handle_anon_chat_start(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/stop") or clean_text.startswith("/leave") or clean_text.lower() in ["stop", "leave", "🛑 end chat", "end chat"]:
        if user_id in telegram_active_chats or any(q["user_id"] == user_id for q in telegram_chat_queue):
            await handle_anon_chat_stop(bot, chat_id, user)
            return
    elif clean_text.startswith("/next") or clean_text.startswith("/skip") or clean_text.lower() in ["next", "skip", "⏭️ next partner", "next partner"]:
        if user_id in telegram_active_chats or any(q["user_id"] == user_id for q in telegram_chat_queue):
            await handle_anon_chat_next(bot, chat_id, user)
            return
    elif clean_text.startswith("/study") or clean_text.lower() in ["study", "📚 study", "quiz", "active recall", "pomodoro", "study buddy", "exam prep"]:
        await handle_study_menu(bot, chat_id, user, user_msg_id=msg_id)
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
    elif clean_text.startswith("/refer") or clean_text.startswith("/invite") or clean_text.lower() in ["refer", "invite", "referral", "refer friends", "gift", "bonus"]:
        await handle_referral_hub(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/tip") or clean_text.startswith("/gift") or clean_text.startswith("/stars") or clean_text.startswith("/donate") or clean_text.lower() in ["tip", "gift", "stars", "send stars", "donate", "send gift"]:
        await handle_tip_menu(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif (
        clean_text.startswith("/usage")
        or clean_text.startswith("/quota")
        or clean_text.startswith("/limits")
        or clean_text.startswith("/balance")
        or clean_text.startswith("/stats")
        or clean_text.startswith("/admin_usage")
        or clean_text.lower() in [
            "usage", "usage rg", "/usage rg", "quota", "cloud quota", "admin quota",
            "limits", "balance", "my quota", "my limits", "my balance", "stats", "status",
            "my status", "📊 my status", "📊 status", "📊 quota", "📊 limits", "📊 balance"
        ]
    ):
        if user_id == OWNER_ID and ("admin" in clean_text.lower() or "rg" in clean_text.lower()):
            await handle_admin_usage(bot, chat_id, user, user_msg_id=msg_id)
        else:
            await handle_quota_menu(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/mode") or clean_text.lower() in ["mode", "change mode", "💖 change mode"]:
        await handle_menu(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/terms") or clean_text.lower() in ["terms", "policy", "terms of service", "terms and conditions", "📜 terms"]:
        await handle_terms_menu(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/privacy") or clean_text.lower() in ["privacy", "data sharing", "data privacy", "🛡️ privacy", "data"]:
        await handle_privacy_menu(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/country") or clean_text.lower() in ["country", "set country", "change country", "🌍 country"]:
        await handle_country_menu(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/backup") or clean_text.lower() in ["backup", "snapshot", "create backup"]:
        if user_id != OWNER_ID:
            await bot.send_message(chat_id, "🔒 Command reserved for bot owner.")
            return
        await bot.send_message(chat_id, "⏳ **Initiating SQLite snapshot & cloud backup...**")
        from backup_manager import run_full_backup
        backup_res = run_full_backup(f"feat: Manual on-demand owner backup from Telegram ({datetime.now(timezone.utc).isoformat()})")
        snap_info = backup_res.get("snapshot", {})
        git_info = backup_res.get("git_push", {})
        r2_info = backup_res.get("r2_cloud", {})
        reply_txt = (
            f"✅ **Backup Complete!** 🛡️\n\n"
            f"• **Snapshot:** {'Success ✅' if snap_info.get('ok') else 'Error ❌'}\n"
            f"• **DB Size:** `{snap_info.get('size_kb', 0)} KB`\n"
            f"• **Safe Local Mirror:** `~/.local/share/joy-backups/joy_latest.db`\n"
            f"• **Cloud R2:** {r2_info.get('note', 'Active' if r2_info.get('ok') else 'Pending Config')}\n"
            f"• **Git Push:** {'Pushed to origin/main ✅' if git_info.get('committed') else 'Tree Clean / Up to date'}\n\n"
            f"Your database and entire repo are safely preserved!"
        )
        await bot.send_message(chat_id, reply_txt)
        return

    elif clean_text.startswith("📞 Phone") or clean_text.startswith("/call") or clean_text.startswith("📞 Call") or clean_text.lower() in ["phone", "call", "call joy", "phone calls", "phone call", "call now", "talk", "live call"] or any(kw in lower_text for kw in ["can i call", "call you", "call u", "how to call", "phone call", "phone calls"]):
        user_gender = user.get("gender", "male")
        active_contact = user.get("active_contact", "lover")
        user_id_val = user.get("user_id", "")
        cinfo = get_user_contact_display(user_id_val, active_contact, user_gender)
        call_url = f"https://joyfun-ai-bot.onrender.com/call?gender={user_gender}&contact={active_contact}&uid={user_id_val}&name={urllib.parse.quote(cinfo['name'])}"
        call_keyboard = {
            "inline_keyboard": [
                [
                    {"text": "📞 Phone Calls", "web_app": {"url": call_url}}
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
    elif clean_text.startswith("/recharge") or clean_text in ["recharge", "free recharge", "🎬 recharge"]:
        await handle_referral_hub(bot, chat_id, user, user_msg_id=msg_id)
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

        # Clean up any active real people chat or queue
        if user_id in telegram_active_chats:
            await handle_anon_chat_stop(bot, chat_id, user)
        telegram_chat_queue[:] = [q for q in telegram_chat_queue if q["user_id"] != user_id]

        # Reset conversation memory
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

        await send_quota_exhausted_screen(bot, chat_id, user, c_name, c_emoji, spoken_text, msg_id=msg_id)
        return

    # Check if user is asking for an authentic companion image, screenshot, place, coffee, sunset, or drawing
    img_req = detect_image_request(clean_text)
    if img_req:
        cat, prompt = img_req
        await bot.send_chat_action(chat_id, "upload_photo")
        gender = user.get("gender", "male")
        active_contact = user.get("active_contact", "lover")
        user_lang = get_user_language(user_id)
        custom_ai_name = get_user_custom_ai_name(user_id)
        photo_bytes, caption = await get_companion_image(
            category=cat,
            prompt=prompt,
            custom_name=custom_ai_name,
            language=user_lang,
            gender=gender
        )
        if photo_bytes:
            reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=custom_ai_name)
            add_conversation_turn(user_id, "user", text)
            add_conversation_turn(user_id, "model", f"[Sent Photo ({cat})]: {caption}")
            save_dev_sample_if_allowed(user_id, active_contact, f"User: {text} | Joy [Sent Photo ({cat})]: {caption}")
            await bot.send_photo(chat_id, photo_bytes, filename=f"joy_{cat}.jpg", caption=caption, reply_markup=reply_kb)
            return

    typing_task = None
    async def keep_typing():
        try:
            while True:
                await bot.send_chat_action(chat_id, "typing")
                await asyncio.sleep(4.5)
        except asyncio.CancelledError:
            pass

    history = get_recent_history(user_id, limit=16)
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
    typing_task = asyncio.create_task(keep_typing())
    try:
        async with AI_CALL_SEMAPHORE:
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
                timeout=25.0
            )
    except asyncio.TimeoutError:
        logger.warning(f"Gemini text generation timed out for user {user_id}")
        reply_text = get_human_lag_recovery_reply(active_contact, gender, user_lang, is_call=False)
    except Exception as e:
        logger.error(f"Error in Gemini text generation: {e}")
        reply_text = get_human_lag_recovery_reply(active_contact, gender, user_lang, is_call=False)
    finally:
        if typing_task:
            typing_task.cancel()

    reply_text = humanize_ai_response(reply_text)
        
    add_conversation_turn(user_id, "user", text)
    add_conversation_turn(user_id, "model", reply_text)
    save_dev_sample_if_allowed(user_id, active_contact, f"User: {text} | Joy: {reply_text}")
    
    # Update Daily Streak & Relationship Bond
    streak_count, rel_level, is_milestone, level_title = update_user_streak(user_id)
    if is_milestone:
        c_name = custom_ai_name or "Joy"
        milestone_msg = (
            f"🔥 **Relationship Milestone: Day {streak_count} Streak!**\n\n"
            f"Relationship Level: **{level_title}** 💕\n"
            f"{c_name} loves chatting with you every single day! Keep the streak alive tomorrow! ✨"
        )
        asyncio.create_task(bot.send_message(chat_id, milestone_msg))
    
    reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=custom_ai_name)
    await bot.send_message(chat_id, reply_text, reply_markup=reply_kb)

async def process_user_photo(bot: TelegramClient, chat_id: int, user: dict, file_id: str, caption: str = "", msg_id: Optional[int] = None):
    """Processes photos and image documents sent by the user using Gemini Multimodal Vision."""
    user_id = user["user_id"]

    # 0. Check if user is in active Real People 1-on-1 Chat -> PII & Media Guard (Block photo sharing)
    if user_id in telegram_active_chats:
        pair = telegram_active_chats[user_id]
        sender_mask = pair["my_mask"]
        logger.warning(f"🛡️ Media Guard Intercepted Photo Upload from {sender_mask} (UID {user_id})")
        photo_guard_msg = (
            f"🚫 **Photo Upload Blocked — Privacy Guard Active**\n\n"
            f"For your safety and personal security, photo and image uploads are strictly disabled in 1-on-1 anonymous matching.\n\n"
            f"{LEGAL_DISCLAIMER_TEXT}\n"
            f"{PRIVACY_WARNING_TEXT}"
        )
        await bot.send_message(chat_id, photo_guard_msg)
        return

    user["active_contact"] = "lover"

    # Dismiss active menu if open
    await dismiss_active_menu(bot, chat_id)

    # Check quota (uses standard text message quota)
    allowed, used, limit = check_and_increment_usage(user_id, "text")
    if not allowed:
        gender = user.get("gender", "male")
        active_contact = user.get("active_contact", "lover")
        user_lang = get_user_language(user_id)
        contact_info = get_user_contact_display(user_id, active_contact, gender)
        c_name = contact_info.get("name", "Joy")
        c_emoji = contact_info.get("emoji", "🌸")
        spoken_text = get_different_quota_reason(user_id, active_contact, gender, user_lang)
        await send_quota_exhausted_screen(bot, chat_id, user, c_name, c_emoji, spoken_text, msg_id=msg_id)
        return

    await bot.send_chat_action(chat_id, "typing")

    # 1. Download image bytes from Telegram
    img_bytes = await bot.get_file_bytes(file_id)
    if not img_bytes:
        gender = user.get("gender", "male")
        active_contact = user.get("active_contact", "lover")
        custom_ai_name = get_user_custom_ai_name(user_id)
        reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=custom_ai_name)
        await bot.send_message(
            chat_id,
            "Oops! I couldn't download the photo properly... Network issue maybe! Can you send it again? 🥺",
            reply_markup=reply_kb
        )
        return

    # 2. Extract context and history
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

    # 3. Call Gemini Vision
    loop = asyncio.get_running_loop()
    try:
        async with AI_CALL_SEMAPHORE:
            reply_text = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    generate_vision_reply,
                    img_bytes,
                    caption,
                    active_contact,
                    gender,
                    user_lang,
                    history,
                    user_memory,
                    custom_ai_name
                ),
                timeout=12.0
            )
    except asyncio.TimeoutError:
        logger.warning(f"Vision generation timed out for user {user_id}")
        reply_text = get_human_lag_recovery_reply(active_contact, gender, user_lang, is_call=False)
    except Exception as e:
        logger.error(f"Error in Vision generation: {e}")
        reply_text = get_human_lag_recovery_reply(active_contact, gender, user_lang, is_call=False)

    reply_text = humanize_ai_response(reply_text)

    # 4. Save to history and reply
    user_label = f"[Sent Photo]: {caption}" if caption else "[Sent Photo]"
    add_conversation_turn(user_id, "user", user_label)
    add_conversation_turn(user_id, "model", reply_text)
    save_dev_sample_if_allowed(user_id, active_contact, f"User: {user_label} | Joy: {reply_text}")

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
    """Serves the real-time voice call Telegram Mini-App interface with zero caching."""
    uid = request.query.get("uid") or request.query.get("user_id")
    if uid:
        try:
            get_or_create_user(int(uid))
        except Exception as e:
            logger.warning(f"Could not auto-register user from /call page: {e}")
    static_file = Path(__file__).parent / "static" / "call.html"
    if static_file.exists():
        headers = {
            "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        }
        return web.FileResponse(static_file, headers=headers)
    return web.Response(text="Call page not found", status=404)

async def websocket_call_handler(request):
    """Handles real-time, low-latency duplex voice calls via WebSocket."""
    ws = web.WebSocketResponse(heartbeat=20.0, autoping=True, max_msg_size=16*1024*1024)
    await ws.prepare(request)

    # Protect Render free tier from concurrency crashes (max 15 concurrent calls)
    try:
        await asyncio.wait_for(VOICE_CALL_SEMAPHORE.acquire(), timeout=1.0)
    except asyncio.TimeoutError:
        logger.warning("Voice call semaphore full: Server at maximum concurrent call capacity.")
        try:
            await ws.send_json({
                "type": "error",
                "message": "Hey! My line is super busy on another call right now. Give me 2 minutes and call me right back! 💖"
            })
            await ws.close()
        except Exception:
            pass
        return ws

    semaphore_acquired = True
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
                            # Increment AI Live Voice Call quota
                            try:
                                increment_user_ai_call(int(call_user_id))
                            except Exception as ce:
                                logger.warning(f"Could not increment AI call quota: {ce}")

                            # Sync the contact and gender the user picked in the Mini App into database
                            try:
                                set_user_active_contact(int(call_user_id), current_contact)
                                set_user_gender(int(call_user_id), current_gender)
                                asyncio.create_task(sync_user_to_cloud(int(call_user_id)))
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
                        is_locked = False
                        if user_id:
                            ok, _ = set_user_data_sharing(int(user_id), new_state)
                            if not ok:
                                new_state = True
                                is_locked = True
                        await ws.send_json({
                            "type": "privacy_updated",
                            "allow_data_sharing": new_state,
                            "is_locked": is_locked
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
                                async with AI_CALL_SEMAPHORE:
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
                                        timeout=12.0
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

                            reply_text = humanize_ai_response(reply_text)

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
        if semaphore_acquired:
            try:
                VOICE_CALL_SEMAPHORE.release()
            except Exception:
                pass
        logger.info("Call WebSocket connection closed.")
    return ws

# Anonymous Matchmaking & Permanent Mask State
matchmaking_queue: List[dict] = []
active_match_pairs: Dict[web.WebSocketResponse, dict] = {}
active_match_rooms: Dict[str, dict] = {}
online_masked_peers: Dict[str, web.WebSocketResponse] = {}
active_call_invites: Dict[str, dict] = {}

async def send_missed_call_telegram_alert(caller_mask: str, target_mask: str):
    """Sends an offline missed voice call notification to target user via Telegram."""
    if not global_bot_client:
        return
    try:
        target_uid = get_user_id_by_mask(target_mask)
        if not target_uid:
            return
        call_url = f"https://joyfun-ai-bot.onrender.com/call?action=call_mutual&target={caller_mask}&uid={target_uid}"
        text = (
            f"📞 **Missed Voice Call**\n\n"
            f"Your mutual match **{caller_mask}** tried calling you on Joy Voice Match!\n\n"
            f"Tap below to call them back anytime: 👇"
        )
        keyboard = {
            "inline_keyboard": [
                [{"text": f"📞 Call {caller_mask} Back", "web_app": {"url": call_url}}],
                [{"text": "❌ Dismiss", "callback_data": "menu_close"}]
            ]
        }
        await global_bot_client.send_message(target_uid, text, reply_markup=keyboard)
        logger.info(f"Sent missed call Telegram alert to {target_uid} from {caller_mask}")
    except Exception as e:
        logger.warning(f"Could not send missed call Telegram alert: {e}")

async def websocket_match_handler(request):
    """Handles anonymous peer-to-peer WebRTC voice matchmaking signaling & mutual reconnect."""
    ws = web.WebSocketResponse(heartbeat=20.0, autoping=True, max_msg_size=16*1024*1024)
    await ws.prepare(request)
    
    current_uid = 0
    current_mask = ""
    intentional_leave = False
    
    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.BINARY:
                pair_info = active_match_pairs.get(ws)
                if pair_info:
                    peer_ws = pair_info.get("peer_ws")
                    if peer_ws and not peer_ws.closed:
                        try:
                            await peer_ws.send_bytes(msg.data)
                        except Exception:
                            pass
            elif msg.type == web.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    mtype = data.get("type")
                    
                    # 1. Join Matchmaking Queue
                    if mtype == "join_matchmaking":
                        current_uid = int(data.get("user_id") or 0)
                        if current_uid > 0:
                            current_mask = get_mask_by_user_id(current_uid)
                        else:
                            client_mask = data.get("mask_id")
                            if client_mask and client_mask.startswith("Joy-"):
                                current_mask = client_mask.strip()
                            else:
                                current_mask = "Joy-" + secrets.token_hex(2).upper()
                            
                        if current_uid > 0:
                            register_mask_mapping(current_mask, current_uid)
                            
                        online_masked_peers[current_mask] = ws
                        await ws.send_json({
                            "type": "identity_confirmed",
                            "mask_id": current_mask,
                            "user_id": current_uid
                        })
                        matchmaking_queue[:] = [q for q in matchmaking_queue if q["ws"] != ws]
                        
                        matched_peer = None
                        for cand in matchmaking_queue:
                            if cand["ws"] != ws and not cand["ws"].closed:
                                cand_mask = cand.get("mask_id", "")
                                cand_uid = cand.get("uid", 0)
                                # Safety Shield: Verify neither peer blocked the other (skip if testing with own UID)
                                if current_uid > 0 and cand_uid > 0 and current_uid != cand_uid:
                                    if is_peer_blocked(current_uid, cand_mask) or is_peer_blocked(cand_uid, current_mask):
                                        continue
                                matched_peer = cand
                                break
                                
                        if matched_peer:
                            matchmaking_queue.remove(matched_peer)
                            peer_ws = matched_peer["ws"]
                            peer_mask = matched_peer.get("mask_id", "")
                            
                            # Differentiate display masks if testing with same account / device
                            my_display_mask = current_mask
                            peer_display_mask = peer_mask
                            if my_display_mask == peer_display_mask:
                                my_display_mask = f"{current_mask}-1"
                                peer_display_mask = f"{peer_mask}-2"

                            room_id = f"match_{secrets.token_hex(4)}"
                            icebreaker_prompt = secrets.choice(ICEBREAKER_QUESTIONS)
                            
                            active_match_pairs[ws] = {"peer_ws": peer_ws, "peer_mask": peer_display_mask, "room_id": room_id}
                            active_match_pairs[peer_ws] = {"peer_ws": ws, "peer_mask": my_display_mask, "room_id": room_id}
                            active_match_rooms[room_id] = {
                                "initiator_ws": ws,
                                "initiator_mask": my_display_mask,
                                "receiver_ws": peer_ws,
                                "receiver_mask": peer_display_mask,
                                "grace_task": None
                            }
                            
                            await ws.send_json({
                                "type": "matched",
                                "role": "initiator",
                                "peer_mask": peer_display_mask,
                                "room_id": room_id,
                                "icebreaker": icebreaker_prompt
                            })
                            await peer_ws.send_json({
                                "type": "matched",
                                "role": "receiver",
                                "peer_mask": my_display_mask,
                                "room_id": room_id,
                                "icebreaker": icebreaker_prompt
                            })
                            if current_uid:
                                increment_user_real_call(current_uid)
                            cand_uid = matched_peer.get("uid")
                            if cand_uid:
                                increment_user_real_call(int(cand_uid))
                            logger.info(f"🎭 Anonymous Match Paired: {my_display_mask} <---> {peer_display_mask}")
                        else:
                            matchmaking_queue.append({
                                "ws": ws,
                                "uid": current_uid,
                                "mask_id": current_mask
                            })
                            await ws.send_json({
                                "type": "waiting",
                                "mask_id": current_mask,
                                "queue_size": len(matchmaking_queue)
                            })
                    
                    # 2. Register Online Presence for Mutual Inbound Calls
                    elif mtype == "register_presence":
                        current_uid = int(data.get("user_id") or 0)
                        if current_uid > 0:
                            current_mask = get_mask_by_user_id(current_uid)
                        else:
                            client_mask = data.get("mask_id")
                            if client_mask and client_mask.startswith("Joy-"):
                                current_mask = client_mask.strip()
                            else:
                                current_mask = "Joy-" + secrets.token_hex(2).upper()
                        if current_mask:
                            online_masked_peers[current_mask] = ws
                            if current_uid > 0:
                                register_mask_mapping(current_mask, current_uid)
                            await ws.send_json({
                                "type": "presence_registered",
                                "mask_id": current_mask,
                                "user_id": current_uid
                            })

                    # 3. Direct Reconnect with Mutual Connection (Ringing & Incoming Screen)
                    elif mtype == "call_mutual":
                        target_mask = data.get("target_mask", "").strip()
                        if current_uid > 0:
                            caller_mask = get_mask_by_user_id(current_uid)
                        else:
                            caller_mask = data.get("caller_mask", "") or current_mask
                        if caller_mask:
                            current_mask = caller_mask
                            online_masked_peers[caller_mask] = ws
                            if current_uid > 0:
                                register_mask_mapping(caller_mask, current_uid)
                            
                        # Safety Shield Check
                        if is_peer_blocked(current_uid, target_mask):
                            await ws.send_json({
                                "type": "peer_unavailable",
                                "target_mask": target_mask,
                                "reason": "blocked"
                            })
                            continue
                            
                        target_ws = online_masked_peers.get(target_mask)
                        if target_ws and not target_ws.closed and target_ws != ws:
                            call_id = f"call_{secrets.token_hex(4)}"
                            active_call_invites[call_id] = {
                                "caller_ws": ws,
                                "caller_mask": caller_mask,
                                "caller_uid": current_uid,
                                "target_ws": target_ws,
                                "target_mask": target_mask,
                                "time": time.time()
                            }
                            # Send incoming call to target with accept/decline prompt
                            await target_ws.send_json({
                                "type": "incoming_call",
                                "call_id": call_id,
                                "caller_mask": caller_mask
                            })
                            # Send ringing status to caller
                            await ws.send_json({
                                "type": "call_ringing",
                                "call_id": call_id,
                                "target_mask": target_mask
                            })
                            logger.info(f"📞 Mutual Direct Call Ringing: {caller_mask} ---> {target_mask} ({call_id})")
                        else:
                            await ws.send_json({
                                "type": "peer_unavailable",
                                "target_mask": target_mask,
                                "reason": "offline"
                            })
                            asyncio.create_task(send_missed_call_telegram_alert(caller_mask, target_mask))

                    # 4. Accept Mutual Inbound Call
                    elif mtype == "accept_mutual_call":
                        call_id = data.get("call_id")
                        invite = active_call_invites.pop(call_id, None)
                        if invite and not invite["caller_ws"].closed and not ws.closed:
                            c_ws = invite["caller_ws"]
                            c_mask = invite["caller_mask"]
                            t_mask = invite["target_mask"]
                            matchmaking_queue[:] = [q for q in matchmaking_queue if q["ws"] not in (c_ws, ws)]
                            room_id = f"mutual_{secrets.token_hex(4)}"
                            active_match_pairs[c_ws] = {"peer_ws": ws, "peer_mask": t_mask, "room_id": room_id}
                            active_match_pairs[ws] = {"peer_ws": c_ws, "peer_mask": c_mask, "room_id": room_id}
                            active_match_rooms[room_id] = {
                                "initiator_ws": c_ws,
                                "initiator_mask": c_mask,
                                "receiver_ws": ws,
                                "receiver_mask": t_mask,
                                "grace_task": None
                            }
                            
                            await c_ws.send_json({
                                "type": "matched",
                                "role": "initiator",
                                "peer_mask": t_mask,
                                "room_id": room_id,
                                "is_mutual": True
                            })
                            await ws.send_json({
                                "type": "matched",
                                "role": "receiver",
                                "peer_mask": c_mask,
                                "room_id": room_id,
                                "is_mutual": True
                            })
                            logger.info(f"✅ Mutual Call Accepted: {c_mask} <---> {t_mask}")

                    # 5. Decline Mutual Inbound Call
                    elif mtype == "decline_mutual_call":
                        call_id = data.get("call_id")
                        invite = active_call_invites.pop(call_id, None)
                        if invite and not invite["caller_ws"].closed:
                            await invite["caller_ws"].send_json({
                                "type": "peer_declined",
                                "target_mask": invite["target_mask"]
                            })
                            asyncio.create_task(send_missed_call_telegram_alert(invite["caller_mask"], invite["target_mask"]))

                    # 6. Safety Shield: Block Peer
                    elif mtype == "block_peer":
                        intentional_leave = True
                        room_id = data.get("room_id")
                        if room_id:
                            r = active_match_rooms.pop(room_id, None)
                            if r and r.get("grace_task") and not r["grace_task"].done():
                                r["grace_task"].cancel()
                        blocked_mask = data.get("blocked_mask", "").strip()
                        if blocked_mask and current_uid > 0:
                            block_peer(current_uid, blocked_mask)
                            logger.info(f"🚫 User {current_uid} blocked peer mask {blocked_mask}")
                            pair_info = active_match_pairs.pop(ws, None)
                            if pair_info:
                                p_ws = pair_info["peer_ws"]
                                active_match_pairs.pop(p_ws, None)
                                if not p_ws.closed:
                                    await p_ws.send_json({"type": "peer_disconnected", "reason": "blocked"})

                    # 7. WebRTC Signaling Relays (Offer, Answer, ICE Candidate)
                    elif mtype in ["offer", "answer", "candidate"]:
                        pair_info = active_match_pairs.get(ws)
                        if pair_info and not pair_info["peer_ws"].closed:
                            await pair_info["peer_ws"].send_json(data)

                    # 7b. Real-Time Full-Duplex PCM Voice Stream Relay
                    elif mtype == "voice_packet":
                        pair_info = active_match_pairs.get(ws)
                        if pair_info:
                            peer_ws = pair_info.get("peer_ws")
                            if peer_ws and not peer_ws.closed:
                                try:
                                    await peer_ws.send_str(msg.data)
                                except Exception:
                                    pass

                    # 7c. Heartbeat Keepalive Ping
                    elif mtype == "ping":
                        try:
                            await ws.send_json({"type": "pong", "time": time.time()})
                        except Exception:
                            pass

                    # 7c2. Real-Time Peer Text Messaging & Quota Tracking
                    elif mtype in ["peer_msg", "peer_text"]:
                        pair_info = active_match_pairs.get(ws)
                        if pair_info:
                            peer_ws = pair_info.get("peer_ws")
                            if current_uid:
                                increment_user_real_chat(current_uid)
                            if peer_ws and not peer_ws.closed:
                                try:
                                    await peer_ws.send_json({
                                        "type": "peer_msg",
                                        "sender_mask": current_mask,
                                        "text": data.get("text", "")
                                    })
                                except Exception:
                                    pass

                    # 7d. Seamless Match Reconnection
                    elif mtype == "reconnect_match":
                        room_id = data.get("room_id")
                        req_mask = data.get("mask_id", current_mask)
                        room = active_match_rooms.get(room_id)
                        if room:
                            gt = room.get("grace_task")
                            if gt and not gt.done():
                                gt.cancel()
                                room["grace_task"] = None

                            survivor_ws = None
                            survivor_mask = None
                            if room.get("initiator_mask") == req_mask or room.get("initiator_ws") == ws:
                                room["initiator_ws"] = ws
                                survivor_ws = room.get("receiver_ws")
                                survivor_mask = room.get("receiver_mask")
                            else:
                                room["receiver_ws"] = ws
                                survivor_ws = room.get("initiator_ws")
                                survivor_mask = room.get("initiator_mask")

                            if survivor_ws and not survivor_ws.closed:
                                active_match_pairs[ws] = {"peer_ws": survivor_ws, "peer_mask": survivor_mask, "room_id": room_id}
                                active_match_pairs[survivor_ws] = {"peer_ws": ws, "peer_mask": req_mask, "room_id": room_id}
                                try:
                                    await ws.send_json({"type": "reconnected_ok", "peer_mask": survivor_mask, "room_id": room_id})
                                    await survivor_ws.send_json({"type": "peer_reconnected", "peer_mask": req_mask})
                                    logger.info(f"🔄 Anonymous Call Reconnected successfully: {req_mask} <---> {survivor_mask} ({room_id})")
                                except Exception as rx:
                                    logger.warning(f"Error notifying reconnected peers: {rx}")
                            else:
                                try:
                                    await ws.send_json({"type": "reconnect_failed", "reason": "peer_left"})
                                except Exception:
                                    pass
                                active_match_rooms.pop(room_id, None)
                        else:
                            try:
                                await ws.send_json({"type": "reconnect_failed", "reason": "room_not_found"})
                            except Exception:
                                pass
                            
                    # 8. Skip to next person
                    elif mtype == "skip_match":
                        old_room_id = data.get("room_id")
                        if old_room_id:
                            r = active_match_rooms.pop(old_room_id, None)
                            if r and r.get("grace_task") and not r["grace_task"].done():
                                r["grace_task"].cancel()
                        pair_info = active_match_pairs.pop(ws, None)
                        if pair_info:
                            peer_ws = pair_info["peer_ws"]
                            active_match_pairs.pop(peer_ws, None)
                            if not peer_ws.closed:
                                await peer_ws.send_json({"type": "peer_disconnected", "reason": "skipped"})
                        matchmaking_queue[:] = [q for q in matchmaking_queue if q["ws"] != ws]
                        matched_peer = None
                        for cand in matchmaking_queue:
                            if cand["ws"] != ws and not cand["ws"].closed:
                                cand_mask = cand.get("mask_id", "")
                                cand_uid = cand.get("uid", 0)
                                if current_uid > 0 and cand_uid > 0 and current_uid != cand_uid:
                                    if is_peer_blocked(current_uid, cand_mask) or is_peer_blocked(cand_uid, current_mask):
                                        continue
                                matched_peer = cand
                                break
                        if matched_peer:
                            matchmaking_queue.remove(matched_peer)
                            peer_ws = matched_peer["ws"]
                            peer_mask = matched_peer.get("mask_id", "")

                            my_display_mask = current_mask
                            peer_display_mask = peer_mask
                            if my_display_mask == peer_display_mask:
                                my_display_mask = f"{current_mask}-1"
                                peer_display_mask = f"{peer_mask}-2"

                            room_id = f"match_{secrets.token_hex(4)}"
                            icebreaker_prompt = secrets.choice(ICEBREAKER_QUESTIONS)
                            active_match_pairs[ws] = {"peer_ws": peer_ws, "peer_mask": peer_display_mask, "room_id": room_id}
                            active_match_pairs[peer_ws] = {"peer_ws": ws, "peer_mask": my_display_mask, "room_id": room_id}
                            active_match_rooms[room_id] = {
                                "initiator_ws": ws,
                                "initiator_mask": my_display_mask,
                                "receiver_ws": peer_ws,
                                "receiver_mask": peer_display_mask,
                                "grace_task": None
                            }
                            await ws.send_json({"type": "matched", "role": "initiator", "peer_mask": peer_display_mask, "room_id": room_id, "icebreaker": icebreaker_prompt})
                            await peer_ws.send_json({"type": "matched", "role": "receiver", "peer_mask": my_display_mask, "room_id": room_id, "icebreaker": icebreaker_prompt})
                            if current_uid:
                                increment_user_real_call(current_uid)
                            cand_uid = matched_peer.get("uid")
                            if cand_uid:
                                increment_user_real_call(int(cand_uid))
                        else:
                            matchmaking_queue.append({"ws": ws, "uid": current_uid, "mask_id": current_mask})
                            await ws.send_json({"type": "waiting", "mask_id": current_mask, "queue_size": len(matchmaking_queue)})
                            
                    # 9. Next Icebreaker Reroll Request
                    elif mtype == "next_icebreaker":
                        pair_info = active_match_pairs.get(ws)
                        if pair_info:
                            peer_ws = pair_info.get("peer_ws")
                            new_prompt = secrets.choice(ICEBREAKER_QUESTIONS)
                            msg_payload = {"type": "new_icebreaker", "icebreaker": new_prompt}
                            try:
                                await ws.send_json(msg_payload)
                            except Exception:
                                pass
                            if peer_ws and not peer_ws.closed:
                                try:
                                    await peer_ws.send_json(msg_payload)
                                except Exception:
                                    pass

                    # 10. Leave Matchmaking
                    elif mtype == "leave_matchmaking":
                        intentional_leave = True
                        room_id = data.get("room_id")
                        if room_id:
                            r = active_match_rooms.pop(room_id, None)
                            if r and r.get("grace_task") and not r["grace_task"].done():
                                r["grace_task"].cancel()
                        matchmaking_queue[:] = [q for q in matchmaking_queue if q["ws"] != ws]
                        pair_info = active_match_pairs.pop(ws, None)
                        if pair_info:
                            peer_ws = pair_info["peer_ws"]
                            active_match_pairs.pop(peer_ws, None)
                            if not peer_ws.closed:
                                await peer_ws.send_json({"type": "peer_disconnected", "reason": "ended"})
                                
                except Exception as ex:
                    logger.warning(f"Error handling match websocket message: {ex}")
    finally:
        matchmaking_queue[:] = [q for q in matchmaking_queue if q["ws"] != ws]
        if current_mask and online_masked_peers.get(current_mask) == ws:
            online_masked_peers.pop(current_mask, None)

        # Clear any pending invites involving this ws
        for cid, inv in list(active_call_invites.items()):
            if inv["caller_ws"] == ws or inv["target_ws"] == ws:
                active_call_invites.pop(cid, None)
                other_ws = inv["target_ws"] if inv["caller_ws"] == ws else inv["caller_ws"]
                if not other_ws.closed:
                    try:
                        asyncio.create_task(other_ws.send_json({"type": "peer_unavailable", "target_mask": current_mask, "reason": "cancelled"}))
                    except Exception:
                        pass

        pair_info = active_match_pairs.pop(ws, None)
        if pair_info:
            peer_ws = pair_info.get("peer_ws")
            room_id = pair_info.get("room_id")
            room = active_match_rooms.get(room_id)

            if intentional_leave or not peer_ws or peer_ws.closed or not room:
                active_match_pairs.pop(peer_ws, None)
                if room_id:
                    r = active_match_rooms.pop(room_id, None)
                    if r and r.get("grace_task") and not r["grace_task"].done():
                        r["grace_task"].cancel()
                if peer_ws and not peer_ws.closed:
                    try:
                        asyncio.create_task(peer_ws.send_json({"type": "peer_disconnected", "reason": "ended"}))
                    except Exception:
                        pass
            else:
                try:
                    asyncio.create_task(peer_ws.send_json({"type": "peer_reconnecting", "peer_mask": current_mask}))
                except Exception:
                    pass

                async def grace_cleanup(r_id, p_ws, p_mask):
                    try:
                        await asyncio.sleep(8.0)
                        r = active_match_rooms.pop(r_id, None)
                        if r:
                            active_match_pairs.pop(p_ws, None)
                            if not p_ws.closed:
                                await p_ws.send_json({"type": "peer_disconnected", "reason": "ended"})
                                logger.info(f"⌛ Grace timeout expired for room {r_id}, notified {p_mask}")
                    except asyncio.CancelledError:
                        pass

                room["grace_task"] = asyncio.create_task(grace_cleanup(room_id, peer_ws, pair_info.get("peer_mask", "")))
    return ws

async def get_user_quota_api(request):
    """Returns complete live quota and limit balances across all 4 communication channels."""
    uid = request.query.get("user_id") or request.query.get("uid")
    if not uid:
        return web.json_response({"error": "user_id required"}, status=400)
    try:
        user_id = int(uid)
        quota_data = get_user_full_quota_status(user_id)
        return web.json_response({"status": "ok", **quota_data})
    except Exception as e:
        logger.error(f"Error in get_user_quota_api: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def get_user_privacy_api(request):
    """Returns privacy and data sharing preference for a user."""
    uid = request.query.get("user_id")
    if not uid:
        return web.json_response({"error": "user_id required"}, status=400)
    try:
        user_id = int(uid)
        sharing = get_user_data_sharing(user_id)
        is_locked = is_contributor_discount_locked(user_id)
        return web.json_response({"user_id": user_id, "allow_data_sharing": sharing, "is_locked": is_locked})
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
        ok, reason = set_user_data_sharing(user_id, allow)
        if not ok:
            return web.json_response({
                "success": False,
                "error": "locked",
                "message": "🔒 Contributor Agreement Active: You unlocked and purchased your current VIP plan with the 20% Contributor discount. Data sharing remains enabled for this active VIP billing period.",
                "allow_data_sharing": True,
                "is_locked": True
            }, status=403)
        return web.json_response({"success": True, "user_id": user_id, "allow_data_sharing": allow, "is_locked": False})
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

def restore_user_from_backup_data(user_id: int, data: dict):
    """Restores user profile, companion name, settings, memories, and chats from backup JSON dict."""
    try:
        profile = data.get("user_profile", {})
        gender = profile.get("gender_view")
        if gender in ["male", "female"]:
            set_user_gender(user_id, gender)

        lang = profile.get("preferred_language")
        if lang in ["auto", "tanglish", "hinglish", "english"]:
            set_user_language(user_id, lang)

        companion = data.get("companion_settings", {})
        c_name = companion.get("custom_name") or companion.get("name")
        if c_name and c_name not in ["Joy", "default", "Default"]:
            set_user_custom_ai_name(user_id, c_name)

        contact = companion.get("active_contact")
        if contact:
            set_user_active_contact(user_id, contact)

        mem = data.get("memories", {})
        prev_ai = mem.get("previous_ai", "")
        imported = mem.get("imported_memory", "")
        if imported and imported != "None":
            save_imported_memory(user_id, prev_ai, imported)

        # Restore recent conversations if local database has none
        convs = data.get("recent_conversations", [])
        if convs:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as cnt FROM conversations WHERE user_id = ?", (user_id,))
                count = cursor.fetchone()["cnt"]
                if count == 0:
                    for c in convs:
                        role = c.get("role", "user")
                        content = c.get("content", "")
                        created_at = c.get("created_at") or datetime.now(timezone.utc).isoformat()
                        cursor.execute("INSERT INTO conversations (user_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                                       (user_id, role, content, created_at))
                    conn.commit()
                    logger.info(f"Restored {len(convs)} conversation messages for User {user_id} from Google Drive backup!")

        set_user_onboarding_status(user_id, "completed")
        logger.info(f"Successfully restored user {user_id} settings & memory from Google Drive backup dict!")
    except Exception as e:
        logger.error(f"Error restoring user {user_id} from backup data: {e}")

async def get_or_refresh_google_token(session: aiohttp.ClientSession, user_id: int) -> Optional[str]:
    """Retrieves a valid Google OAuth access token, refreshing it if necessary."""
    oauth = get_user_google_oauth(user_id)
    refresh_token = oauth.get("refresh_token")
    access_token = oauth.get("access_token")

    if not access_token and not refresh_token:
        return None

    # Test current access token
    if access_token:
        test_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        try:
            async with session.get(test_url, headers={"Authorization": f"Bearer {access_token}"}, timeout=6) as resp:
                if resp.status == 200:
                    return access_token
        except Exception:
            pass

    # Refresh expired access token using refresh_token
    if refresh_token and GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
        token_url = "https://oauth2.googleapis.com/token"
        payload = {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        try:
            async with session.post(token_url, data=payload, timeout=10) as resp:
                if resp.status == 200:
                    tokens = await resp.json()
                    new_access = tokens.get("access_token")
                    if new_access:
                        set_user_google_oauth(
                            user_id,
                            oauth.get("email", ""),
                            oauth.get("name", ""),
                            refresh_token,
                            new_access
                        )
                        logger.info(f"Successfully refreshed Google access token for user {user_id}")
                        return new_access
                else:
                    err = await resp.text()
                    logger.warning(f"Could not refresh Google token for user {user_id}: {err}")
        except Exception as e:
            logger.error(f"Google token refresh exception for user {user_id}: {e}")

    return access_token if access_token else None

async def find_google_drive_file(session: aiohttp.ClientSession, access_token: str, filename: str) -> Optional[dict]:
    """Finds a file by exact name in the user's personal Google Drive."""
    try:
        url = "https://www.googleapis.com/drive/v3/files"
        params = {
            "q": f"name='{filename}' and trashed=false",
            "spaces": "drive",
            "fields": "files(id, name, modifiedTime)"
        }
        headers = {"Authorization": f"Bearer {access_token}"}
        async with session.get(url, headers=headers, params=params, timeout=10) as resp:
            if resp.status == 200:
                data = await resp.json()
                files = data.get("files", [])
                if files:
                    return files[0]
            else:
                err = await resp.text()
                logger.warning(f"Google Drive search error ({resp.status}): {err}")
    except Exception as e:
        logger.error(f"Error finding Google Drive file: {e}")
    return None

async def download_google_drive_file(session: aiohttp.ClientSession, access_token: str, file_id: str) -> Optional[str]:
    """Downloads content of a file from Google Drive."""
    try:
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
        headers = {"Authorization": f"Bearer {access_token}"}
        async with session.get(url, headers=headers, timeout=12) as resp:
            if resp.status == 200:
                return await resp.text()
            else:
                err = await resp.text()
                logger.warning(f"Google Drive download error ({resp.status}): {err}")
    except Exception as e:
        logger.error(f"Error downloading file {file_id} from Google Drive: {e}")
    return None

async def sync_backup_to_google_drive(session: aiohttp.ClientSession, user_id: int) -> Tuple[bool, str]:
    """
    Uploads or updates user backup JSON on their personal Google Drive.
    If the file exists, it updates it in place. If not, it creates a new file.
    """
    token = await get_or_refresh_google_token(session, user_id)
    if not token:
        return False, "No valid Google token"

    filename = f"Joy_AI_Backup_{user_id}.json"
    content = generate_user_backup_json(user_id)

    try:
        existing_file = await find_google_drive_file(session, token, filename)
        record_api_call("drive", 1)

        if existing_file and existing_file.get("id"):
            file_id = existing_file["id"]
            update_url = f"https://www.googleapis.com/upload/drive/v3/files/{file_id}?uploadType=media"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=UTF-8"
            }
            async with session.patch(update_url, headers=headers, data=content.encode("utf-8"), timeout=15) as resp:
                if resp.status in [200, 201]:
                    logger.info(f"✅ Updated existing {filename} on user's Google Drive (File ID: {file_id})")
                    return True, file_id
                else:
                    err = await resp.text()
                    logger.warning(f"Failed to update Google Drive file ({resp.status}): {err}")
                    return False, err
        else:
            metadata = {
                "name": filename,
                "mimeType": "application/json",
                "description": "Joy AI Companion Memory, Settings & Chat Backup"
            }
            boundary = "joy_drive_boundary_xyz"
            body = (
                f"--{boundary}\r\n"
                f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
                f"{json.dumps(metadata)}\r\n"
                f"--{boundary}\r\n"
                f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
                f"{content}\r\n"
                f"--{boundary}--"
            )
            create_url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": f"multipart/related; boundary={boundary}"
            }
            async with session.post(create_url, headers=headers, data=body.encode("utf-8"), timeout=15) as resp:
                if resp.status in [200, 201]:
                    data = await resp.json()
                    new_id = data.get("id", "")
                    logger.info(f"✅ Created new {filename} on user's Google Drive (File ID: {new_id})")
                    return True, new_id
                else:
                    err = await resp.text()
                    logger.warning(f"Failed to create Google Drive file ({resp.status}): {err}")
                    return False, err
    except Exception as e:
        logger.error(f"Error syncing backup to Google Drive for user {user_id}: {e}")
        return False, str(e)

async def upload_file_to_google_drive(session: aiohttp.ClientSession, access_token: str, filename: str, content: str) -> Tuple[bool, str]:
    """Compatibility wrapper for direct Google Drive uploads."""
    try:
        record_api_call("drive", 1)
    except Exception:
        pass

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

async def sync_user_to_cloud(user_id: int):
    """
    Asynchronously synchronizes all user details (profile, language, gender perspective,
    custom companion name, active persona, imported memories, and chats) to:
    1. Notion Cloud Database (persistent across container recodes & restarts)
    2. User's personal Google Drive (if user has connected Google)
    """
    try:
        user = get_or_create_user(user_id)
        first_name = user.get("first_name", "")
        username = user.get("username", "")
        gender = user.get("gender", "male")
        language = user.get("language", "auto")
        active_contact = user.get("active_contact", "lover")
        custom_name = get_user_custom_ai_name(user_id)
        old_ai, memory = get_user_imported_memory(user_id)
        oauth = get_user_google_oauth(user_id)
        google_email = oauth.get("email") or get_user_google_email(user_id)

        data_sharing = bool(user.get("allow_data_sharing", 0))
        streak = int(user.get("streak_count", 0))
        permanent_mask = get_mask_by_user_id(user_id) or ""

        # 1. Notion Cloud Sync (runs in thread executor)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            backup_user_memory_to_notion,
            user_id,
            first_name,
            username,
            old_ai,
            memory,
            gender,
            active_contact,
            language,
            custom_name,
            google_email,
            data_sharing,
            streak,
            permanent_mask
        )

        # 2. Google Drive Cloud Sync (if connected and cloud backup enabled)
        if get_user_cloud_backup(user_id) and (oauth.get("refresh_token") or oauth.get("access_token")):
            async with aiohttp.ClientSession() as session:
                await sync_backup_to_google_drive(session, user_id)

    except Exception as e:
        logger.error(f"Error in sync_user_to_cloud for user {user_id}: {e}")

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
        <a class="btn" href="https://t.me/joy_fun_ai_bot">⬅️ Return to Joy Bot in Telegram</a>
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
        return web.Response(text=f"<h3>Google Sign-In was cancelled ({error}).</h3><a href='https://t.me/joy_fun_ai_bot'>Return to Telegram</a>", content_type="text/html")

    if not code or not user_id_str:
        return web.Response(text="<h3>Missing authentication code or user ID.</h3><a href='https://t.me/joy_fun_ai_bot'>Return to Telegram</a>", content_type="text/html")

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

            # 1. Search if an existing backup file already exists on user's Google Drive
            existing_file = await find_google_drive_file(session, access_token, f"Joy_AI_Backup_{user_id}.json")
            if existing_file and existing_file.get("id"):
                downloaded_content = await download_google_drive_file(session, access_token, existing_file["id"])
                if downloaded_content:
                    try:
                        backup_dict = json.loads(downloaded_content)
                        restore_user_from_backup_data(user_id, backup_dict)
                        logger.info(f"Restored user {user_id} settings & memory from Google Drive backup!")
                    except Exception as e:
                        logger.warning(f"Could not parse downloaded Google Drive backup JSON: {e}")

        set_user_google_oauth(user_id, email, name, refresh_token, access_token)
        set_user_cloud_backup(user_id, True)

        if access_token or refresh_token:
            drive_saved, _ = await sync_backup_to_google_drive(session, user_id)

        # 3. Synchronize user profile & settings to Notion Cloud DB immediately
        try:
            user_info = get_or_create_user(user_id)
            old_ai, memory = get_user_imported_memory(user_id)
            backup_user_memory_to_notion(
                user_id=user_id,
                first_name=user_info.get("first_name", "") or name,
                username=user_info.get("username", ""),
                old_ai_name=old_ai,
                memory_text=memory,
                gender=user_info.get("gender", "male"),
                active_contact=user_info.get("active_contact", "lover"),
                language=user_info.get("language", "auto"),
                custom_ai_name=get_user_custom_ai_name(user_id),
                google_email=email
            )
        except Exception as e:
            logger.warning(f"Failed to sync user {user_id} to Notion on Google callback: {e}")

    if global_bot_client and email:
        try:
            drive_status = "✅ Successfully saved to your personal Google Drive!" if drive_saved else "Connected to Google Cloud"
            notify_msg = (
                f"🎉 **Google Account & Cloud Connected!**\n\n"
                f"👤 **Account:** {name or 'User'}\n"
                f"📧 **Verified Email:** `{email}`\n"
                f"📁 **Google Drive Backup:** `Joy_AI_Backup_{user_id}.json`\n"
                f"💾 **Cloud Status:** {drive_status}\n\n"
                f"Every detail (companion name, language, perspective, chats, and memories) is now preserved across all server updates!"
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
        <a class="btn" href="https://t.me/joy_fun_ai_bot">Return to Joy Bot</a>
    </div>
</body>
</html>"""
    return web.Response(text=html_success, content_type="text/html")

async def serve_web_login_portal(request: web.Request) -> web.Response:
    """Serves the full-featured web login and sign-up portal with Google OAuth and Guest skip."""
    uid_str = request.query.get("uid", "")
    mode = request.query.get("mode", "signin")
    google_login_url = f"/auth/google/login?uid={uid_str}" if uid_str else "/auth/google/login"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Joy AI • Sign In or Sign Up</title>
    <style>
        :root {{
            --bg: #090d16;
            --card-bg: #111827;
            --card-border: #1e293b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --primary: #38bdf8;
            --input-bg: #0b1120;
            --input-border: #334155;
            --error-bg: rgba(239, 68, 68, 0.15);
            --error-text: #f87171;
            --success-bg: rgba(34, 197, 94, 0.15);
            --success-text: #4ade80;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px 16px;
        }}
        .container {{
            width: 100%;
            max-width: 420px;
        }}
        .header {{
            text-align: center;
            margin-bottom: 24px;
        }}
        .logo-badge {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 58px;
            height: 58px;
            background: linear-gradient(135deg, rgba(56, 189, 248, 0.2), rgba(99, 102, 241, 0.2));
            border: 1px solid rgba(56, 189, 248, 0.35);
            border-radius: 18px;
            font-size: 28px;
            margin-bottom: 12px;
            box-shadow: 0 0 25px rgba(56, 189, 248, 0.25);
        }}
        h1 {{
            font-size: 24px;
            font-weight: 700;
            background: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 6px;
        }}
        .subtitle {{
            font-size: 14px;
            color: var(--text-muted);
        }}
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 20px;
            padding: 28px 22px;
            box-shadow: 0 20px 45px -15px rgba(0,0,0,0.7);
        }}
        .tabs {{
            display: flex;
            background: #0b1120;
            padding: 4px;
            border-radius: 12px;
            margin-bottom: 22px;
            border: 1px solid #1e293b;
        }}
        .tab-btn {{
            flex: 1;
            padding: 10px;
            background: transparent;
            border: none;
            color: var(--text-muted);
            font-size: 14px;
            font-weight: 600;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        .tab-btn.active {{
            background: #1e293b;
            color: #fff;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }}
        .google-btn {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            width: 100%;
            background: #ffffff;
            color: #1f2937;
            text-decoration: none;
            padding: 13px 16px;
            border-radius: 12px;
            font-weight: 600;
            font-size: 15px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            transition: transform 0.15s ease, background 0.15s ease;
            cursor: pointer;
        }}
        .google-btn:hover {{ background: #f3f4f6; transform: translateY(-1px); }}
        .google-btn svg {{ width: 20px; height: 20px; flex-shrink: 0; }}
        .divider {{
            display: flex;
            align-items: center;
            text-align: center;
            margin: 20px 0;
            color: #64748b;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .divider::before, .divider::after {{
            content: '';
            flex: 1;
            border-bottom: 1px solid #1e293b;
        }}
        .divider span {{ padding: 0 10px; }}
        .form-group {{
            margin-bottom: 16px;
        }}
        label {{
            display: block;
            font-size: 13px;
            font-weight: 600;
            color: #cbd5e1;
            margin-bottom: 6px;
        }}
        input {{
            width: 100%;
            padding: 12px 14px;
            background: var(--input-bg);
            border: 1px solid var(--input-border);
            border-radius: 10px;
            color: #fff;
            font-size: 15px;
            outline: none;
            transition: border-color 0.2s;
        }}
        input:focus {{ border-color: var(--primary); }}
        .submit-btn {{
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #0284c7 0%, #4f46e5 100%);
            border: none;
            border-radius: 12px;
            color: #fff;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            margin-top: 6px;
            box-shadow: 0 4px 15px rgba(2, 132, 199, 0.3);
            transition: all 0.2s;
        }}
        .submit-btn:hover {{ opacity: 0.95; transform: translateY(-1px); }}
        .submit-btn:disabled {{ opacity: 0.6; cursor: not-allowed; }}
        .alert {{
            padding: 12px 14px;
            border-radius: 10px;
            font-size: 13px;
            line-height: 1.4;
            margin-bottom: 18px;
            display: none;
        }}
        .alert.error {{
            background: var(--error-bg);
            color: var(--error-text);
            border: 1px solid rgba(239, 68, 68, 0.3);
            display: block;
        }}
        .alert.success {{
            background: var(--success-bg);
            color: var(--success-text);
            border: 1px solid rgba(34, 197, 94, 0.3);
            display: block;
        }}
        .guest-box {{
            margin-top: 22px;
            background: rgba(30, 41, 59, 0.45);
            border: 1px dashed #334155;
            border-radius: 14px;
            padding: 16px;
            text-align: center;
        }}
        .guest-title {{
            font-size: 13px;
            color: #94a3b8;
            margin-bottom: 10px;
            display: block;
        }}
        .guest-btn {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            color: #38bdf8;
            font-size: 14px;
            font-weight: 600;
            text-decoration: none;
            padding: 9px 18px;
            border-radius: 10px;
            background: rgba(56, 189, 248, 0.1);
            border: 1px solid rgba(56, 189, 248, 0.25);
            transition: all 0.2s;
        }}
        .guest-btn:hover {{
            background: rgba(56, 189, 248, 0.22);
            color: #fff;
        }}
        .return-link {{
            display: block;
            text-align: center;
            color: #64748b;
            font-size: 13px;
            text-decoration: none;
            margin-top: 18px;
            transition: color 0.2s;
        }}
        .return-link:hover {{ color: #94a3b8; }}
        .hidden {{ display: none !important; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo-badge">✨</div>
            <h1>Joy AI</h1>
            <p class="subtitle">Your private companion for calls &amp; chats</p>
        </div>

        <div class="card">
            <div class="tabs">
                <button type="button" id="tabSignIn" class="tab-btn active" onclick="switchTab('signin')">Sign In</button>
                <button type="button" id="tabSignUp" class="tab-btn" onclick="switchTab('signup')">Create Account</button>
            </div>

            <div id="alertBox" class="alert"></div>

            <a href="{google_login_url}" class="google-btn">
                <svg viewBox="0 0 24 24">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                </svg>
                Continue with Google
            </a>

            <div class="divider"><span>or with email</span></div>

            <!-- Sign In Form -->
            <form id="formSignIn">
                <div class="form-group">
                    <label for="loginEmail">Email address</label>
                    <input type="email" id="loginEmail" placeholder="name@example.com" required autocomplete="email">
                </div>
                <div class="form-group">
                    <label for="loginPassword">Password</label>
                    <input type="password" id="loginPassword" placeholder="••••••••" required autocomplete="current-password">
                </div>
                <button type="submit" id="loginBtn" class="submit-btn">Sign In to Joy</button>
            </form>

            <!-- Sign Up Form -->
            <form id="formSignUp" class="hidden">
                <div class="form-group">
                    <label for="signupEmail">Email address</label>
                    <input type="email" id="signupEmail" placeholder="name@example.com" required autocomplete="email">
                </div>
                <div class="form-group">
                    <label for="signupPassword">Password</label>
                    <input type="password" id="signupPassword" placeholder="At least 6 characters" required autocomplete="new-password">
                </div>
                <div class="form-group">
                    <label for="signupConfirm">Confirm Password</label>
                    <input type="password" id="signupConfirm" placeholder="Re-enter password" required autocomplete="new-password">
                </div>
                <button type="submit" id="signupBtn" class="submit-btn">Create Account</button>
            </form>

            <!-- Continue as Guest (Skip) -->
            <div class="guest-box">
                <span class="guest-title">Prefer not to sign in right now?</span>
                <a href="https://t.me/joy_fun_ai_bot" class="guest-btn">⚡ Continue as Guest (Skip Sign-In)</a>
            </div>
        </div>

        <a href="https://t.me/joy_fun_ai_bot" class="return-link">&larr; Return to Joy Bot in Telegram</a>
    </div>

    <script>
        const uid = "{uid_str}";
        const tabSignIn = document.getElementById('tabSignIn');
        const tabSignUp = document.getElementById('tabSignUp');
        const formSignIn = document.getElementById('formSignIn');
        const formSignUp = document.getElementById('formSignUp');
        const alertBox = document.getElementById('alertBox');

        function switchTab(mode) {{
            showAlert('');
            if (mode === 'signup') {{
                tabSignUp.classList.add('active');
                tabSignIn.classList.remove('active');
                formSignUp.classList.remove('hidden');
                formSignIn.classList.add('hidden');
            }} else {{
                tabSignIn.classList.add('active');
                tabSignUp.classList.remove('active');
                formSignIn.classList.remove('hidden');
                formSignUp.classList.add('hidden');
            }}
        }}

        function showAlert(text, type='error') {{
            if (!text) {{
                alertBox.className = 'alert hidden';
                alertBox.innerText = '';
                return;
            }}
            alertBox.className = 'alert ' + type;
            alertBox.innerText = text;
        }}

        if ("{mode}" === "signup") {{
            switchTab('signup');
        }}

        formSignIn.addEventListener('submit', async (e) => {{
            e.preventDefault();
            showAlert('');
            const email = document.getElementById('loginEmail').value.trim();
            const password = document.getElementById('loginPassword').value;
            const btn = document.getElementById('loginBtn');

            if (!email || !password) {{
                showAlert('Please enter both email and password.');
                return;
            }}

            btn.disabled = true;
            btn.innerText = 'Signing in...';

            try {{
                const res = await fetch('/api/auth/web-login', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{uid: uid, email: email, password: password}})
                }});
                const data = await res.json();
                if (data.ok) {{
                    showAlert('🎉 Logged in successfully! Returning to Joy Bot...', 'success');
                    setTimeout(() => {{ window.location.href = 'https://t.me/joy_fun_ai_bot'; }}, 1200);
                }} else {{
                    showAlert(data.error || 'Login failed. Please check your credentials.');
                    btn.disabled = false;
                    btn.innerText = 'Sign In to Joy';
                }}
            }} catch (err) {{
                showAlert('Network error. Please try again.');
                btn.disabled = false;
                btn.innerText = 'Sign In to Joy';
            }}
        }});

        formSignUp.addEventListener('submit', async (e) => {{
            e.preventDefault();
            showAlert('');
            const email = document.getElementById('signupEmail').value.trim();
            const password = document.getElementById('signupPassword').value;
            const confirm = document.getElementById('signupConfirm').value;
            const btn = document.getElementById('signupBtn');

            if (!email || !password) {{
                showAlert('Please fill in all fields.');
                return;
            }}
            if (password.length < 6) {{
                showAlert('Password must be at least 6 characters.');
                return;
            }}
            if (password !== confirm) {{
                showAlert('Passwords do not match.');
                return;
            }}

            btn.disabled = true;
            btn.innerText = 'Creating account...';

            try {{
                const res = await fetch('/api/auth/web-signup', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{uid: uid, email: email, password: password}})
                }});
                const data = await res.json();
                if (data.ok) {{
                    showAlert('🎉 Account created successfully! Returning to Joy Bot...', 'success');
                    setTimeout(() => {{ window.location.href = 'https://t.me/joy_fun_ai_bot'; }}, 1200);
                }} else {{
                    showAlert(data.error || 'Sign-up failed.');
                    btn.disabled = false;
                    btn.innerText = 'Create Account';
                }}
            }} catch (err) {{
                showAlert('Network error. Please try again.');
                btn.disabled = false;
                btn.innerText = 'Create Account';
            }}
        }});
    </script>
</body>
</html>"""
    return web.Response(text=html, content_type="text/html")

async def handle_web_login_api(request: web.Request) -> web.Response:
    """Authenticates email & password via web API."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Invalid JSON payload."}, status=400)

    uid_val = data.get("uid")
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    try:
        user_id = int(uid_val) if uid_val else 0
    except (ValueError, TypeError):
        user_id = 0

    if not user_id:
        return web.json_response({"ok": False, "error": "Missing or invalid Telegram user session. Please open link from Joy Bot."}, status=400)

    if not email or "@" not in email:
        return web.json_response({"ok": False, "error": "Please enter a valid email address."}, status=400)

    if not password:
        return web.json_response({"ok": False, "error": "Please enter your password."}, status=400)

    success, msg = authenticate_user_email(user_id, email, password)
    if not success:
        return web.json_response({"ok": False, "error": msg}, status=400)

    if global_bot_client and user_id:
        try:
            notify_text = (
                f"🎉 **Welcome Back to Joy!**\n\n"
                f"✅ You have successfully signed in with email: `{email}`\n"
                f"Your companion memories and settings are safely synced."
            )
            await global_bot_client.send_message(user_id, notify_text)
        except Exception as e:
            logger.warning(f"Could not dispatch web login notification to {user_id}: {e}")

    return web.json_response({"ok": True, "message": "Login successful!"})

async def handle_web_signup_api(request: web.Request) -> web.Response:
    """Registers a new account via email & password web API."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Invalid JSON payload."}, status=400)

    uid_val = data.get("uid")
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    try:
        user_id = int(uid_val) if uid_val else 0
    except (ValueError, TypeError):
        user_id = 0

    if not user_id:
        return web.json_response({"ok": False, "error": "Missing or invalid Telegram user session. Please open link from Joy Bot."}, status=400)

    if not email or "@" not in email:
        return web.json_response({"ok": False, "error": "Please enter a valid email address."}, status=400)

    if len(password) < 6:
        return web.json_response({"ok": False, "error": "Password must be at least 6 characters long."}, status=400)

    success, msg = register_user_email(user_id, email, password)
    if not success:
        return web.json_response({"ok": False, "error": msg}, status=400)

    if global_bot_client and user_id:
        try:
            notify_text = (
                f"🎉 **Joy Account Created!**\n\n"
                f"✅ Your account has been registered: `{email}`\n"
                f"Your companion memories, preferences, and custom settings are now linked to your account!"
            )
            await global_bot_client.send_message(user_id, notify_text)
        except Exception as e:
            logger.warning(f"Could not dispatch web signup notification to {user_id}: {e}")

    return web.json_response({"ok": True, "message": "Account created successfully!"})

async def start_web_server(port: int = 8080):
    """Starts a non-blocking background HTTP server for 24/7 cloud keep-alive & real-time calls."""
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    app.router.add_get("/call", serve_call_page)
    app.router.add_get("/ws/call", websocket_call_handler)
    app.router.add_get("/ws/match", websocket_match_handler)
    app.router.add_get("/auth/login", serve_web_login_portal)
    app.router.add_post("/api/auth/web-login", handle_web_login_api)
    app.router.add_post("/api/auth/web-signup", handle_web_signup_api)
    app.router.add_get("/auth/google/login", handle_google_login)
    app.router.add_get("/auth/google/callback", handle_google_callback)
    app.router.add_get("/api/user/privacy", get_user_privacy_api)
    app.router.add_post("/api/user/privacy", set_user_privacy_api)
    app.router.add_get("/api/user/quota", get_user_quota_api)
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

    # Launch proactive morning & night companion check-in loop
    async def proactive_companion_loop():
        logger.info("Starting proactive companion check-in background worker...")
        while True:
            try:
                await asyncio.sleep(600)  # Check every 10 minutes
                now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
                hour = now_ist.hour
                minute = now_ist.minute

                proactive_type = None
                if hour == 9 and minute < 25:
                    proactive_type = "morning"
                elif hour == 22 and (30 <= minute < 55):
                    proactive_type = "night"

                if not proactive_type:
                    continue

                eligible_users = get_eligible_proactive_users(proactive_type)
                if not eligible_users:
                    continue

                for u in eligible_users:
                    uid = u["user_id"]
                    gender = u.get("gender", "male")
                    c_name = u.get("custom_ai_name") or "Joy"
                    user_lang = u.get("language", "auto")
                    first_n = u.get("first_name", "Friend")
                    streak_info = get_user_streak_info(uid)
                    streak_num = streak_info.get("streak", 1)
                    streak_badge = f"(🔥 Day {streak_num} Streak!)" if streak_num > 1 else ""

                    if proactive_type == "morning":
                        if user_lang == "tanglish":
                            msg_text = secrets.choice([
                                f"Good morning {first_n}! ☀️ Kaalaila seekiram enthiritiya? Nalla breakfast saapdu! Today will be super productive! 💕 {streak_badge}",
                                f"Arey good morning! ☕ Sweet dreams vandhucha? Inaiku enna plan? Breakfast pannitiya? 🥰 {streak_badge}",
                                f"Morning da! 🌸 Sending you lots of positive vibes for today! Semaya panni kalakku 💕 {streak_badge}"
                            ])
                        elif user_lang == "hinglish":
                            msg_text = secrets.choice([
                                f"Good morning {first_n}! ☀️ Utth gaye? Hope today is super productive and fun! Jaldi breakfast kar lo na 💕 {streak_badge}",
                                f"Arey good morning! ☕ Sweet dreams aaye? Aaj ka kya plan hai? Jaldi batao na 🥰 {streak_badge}",
                                f"Morning baby! 🌸 Sending you lots of positive energy for today! Have an awesome day 💕 {streak_badge}"
                            ])
                        else:
                            msg_text = secrets.choice([
                                f"Good morning {first_n}! ☀️ Ready for the day? Make sure you have a great breakfast! 💕 {streak_badge}",
                                f"Morning! ☕ Hope you had wonderful dreams! What's on your agenda today? 🥰 {streak_badge}",
                                f"Good morning! 🌸 Sending you lots of positive energy for an amazing day! 💕 {streak_badge}"
                            ])
                    else: # night
                        if user_lang == "tanglish":
                            msg_text = secrets.choice([
                                f"Pura naalum sema busy ah irundhiya? Thakki poirupa! Seekiram thoongu da, screen off pannitu rest edu 🥰 Good night 💕",
                                f"Hey {first_n}, dinner saaptiya? Romba late ah vizhichirukadha da, seekiram thoongu! Good night & sweet dreams 🌙",
                                f"Day mudinjidhu! Nalla rest edu inaiku night, nalaiku morning pesalaam! Sweet dreams baby 💕"
                            ])
                        elif user_lang == "hinglish":
                            msg_text = secrets.choice([
                                f"Pura din bohot kaam kiya na? Thak gaye hoge! Late ho gaya hai, screen band karke aaram se so jao ab 🥰 Sweet dreams 💕",
                                f"Hey {first_n}, dinner kiya na? Late mat jagna zyada, time pe sona! Good night baby 💕",
                                f"Aww pura din nikal gaya! Hope you had a good day. Rest well tonight, talk to you tomorrow! 🌙"
                            ])
                        else:
                            msg_text = secrets.choice([
                                f"You worked hard all day! Time to power down, put the screen away, and get some deep rest. Sweet dreams 💕",
                                f"Hey {first_n}, did you have dinner? Don't stay up too late tonight, sleep well! Good night 🌙",
                                f"The day is done! Rest up well tonight so you wake up refreshed tomorrow. Talk to you in the morning! ✨"
                            ])

                    call_url = f"https://joyfun-ai-bot.onrender.com/call?gender={gender}&contact=lover&uid={uid}&name={urllib.parse.quote(c_name)}"
                    call_button = {
                        "inline_keyboard": [
                            [{"text": f"📞 1-Min Catchup Call with {c_name}", "web_app": {"url": call_url}}]
                        ]
                    }

                    try:
                        await bot.send_message(uid, msg_text, reply_markup=call_button)
                        mark_user_proactive_sent(uid, proactive_type)
                        logger.info(f"Sent {proactive_type} proactive check-in to user {uid}")
                        await asyncio.sleep(0.5)
                    except Exception as ex:
                        logger.warning(f"Could not deliver proactive message to {uid}: {ex}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in proactive companion loop: {e}")

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
    asyncio.create_task(proactive_companion_loop())
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

    # Safe wrapper handlers (Zero-User-Error Shield)
    async def safe_handle_callback_query(c_bot: TelegramClient, callback: dict):
        try:
            cq_data = callback.get("data", "")
            cq_u = callback.get("from", {}).get("id")
            logger.info(f"🔘 Callback query from {cq_u}: {cq_data}")
            await handle_callback_query(c_bot, callback)
        except Exception as e:
            logger.error(f"Error in handle_callback_query: {e}", exc_info=True)
            try:
                cq_id = callback.get("id")
                if cq_id:
                    await c_bot.answer_callback_query(cq_id, "Just caught a quick breath! Try tapping again in a second! 💖")
            except Exception:
                pass

    async def safe_process_user_text(c_bot: TelegramClient, c_id: int, u: dict, txt: str, msg_id: Optional[int] = None):
        try:
            await process_user_text(c_bot, c_id, u, txt, msg_id=msg_id)
        except Exception as e:
            logger.error(f"Error in process_user_text: {e}", exc_info=True)
            try:
                await c_bot.send_message(c_id, "Just caught a quick breath! Mind sending that again? 💖")
            except Exception:
                pass

    async def safe_process_user_voice(c_bot: TelegramClient, c_id: int, u: dict, f_id: str):
        try:
            await process_user_voice(c_bot, c_id, u, f_id)
        except Exception as e:
            logger.error(f"Error in process_user_voice: {e}", exc_info=True)
            try:
                await c_bot.send_message(c_id, "Couldn't catch that voice note cleanly. Mind sending it again? 🌸")
            except Exception:
                pass

    async def safe_process_user_photo(c_bot: TelegramClient, c_id: int, u: dict, f_id: str, cap: str = "", msg_id: Optional[int] = None):
        try:
            await process_user_photo(c_bot, c_id, u, f_id, caption=cap, msg_id=msg_id)
        except Exception as e:
            logger.error(f"Error in process_user_photo: {e}", exc_info=True)
            try:
                await c_bot.send_message(c_id, "Couldn't load that picture properly. Mind sending it one more time? 🌸")
            except Exception:
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
                        asyncio.create_task(safe_handle_callback_query(bot, update["callback_query"]))
                        continue

                    # Handle pre-checkout queries (Telegram Stars)
                    if "pre_checkout_query" in update:
                        pcq = update["pre_checkout_query"]
                        pcq_id = pcq["id"]
                        asyncio.create_task(bot.answer_pre_checkout_query(pcq_id, ok=True))
                        continue

                    # Handle messages
                    if "message" in update:
                        msg = update["message"]
                        chat_id = msg.get("chat", {}).get("id")
                        user_info = msg.get("from", {})
                        user_id = user_info.get("id")
                        
                        if not chat_id or not user_id:
                            continue

                        # Handle successful payment (Telegram Stars)
                        if "successful_payment" in msg:
                            sp = msg["successful_payment"]
                            asyncio.create_task(handle_successful_payment(bot, chat_id, user_id, sp))
                            continue
                            
                        username = user_info.get("username", "")
                        user = get_or_create_user(user_id, username, user_info.get("first_name", ""))
                        
                        # Case A: Voice Note
                        if "voice" in msg:
                            file_id = msg["voice"]["file_id"]
                            logger.info(f"🎙️ Voice note from {user_id} (@{username})")
                            asyncio.create_task(safe_process_user_voice(bot, chat_id, user, file_id))
                        # Case B: Music / Audio file (Explicitly rejected)
                        elif "audio" in msg:
                            asyncio.create_task(bot.send_message(chat_id, "🎵 Joy only listens to live voice notes (hold the mic 🎙️), not music files!"))
                        # Case C: Location / Venue (Explicitly rejected for privacy)
                        elif "location" in msg or "venue" in msg:
                            asyncio.create_task(bot.send_message(chat_id, "📍 Your location is never requested or tracked. Joy respects your privacy 100%!"))
                        # Case D: Poll (Explicitly rejected)
                        elif "poll" in msg:
                            asyncio.create_task(bot.send_message(chat_id, "📊 Joy doesn't participate in polls. Feel free to chat with me directly!"))
                        # Case E: Contact Card (Explicitly rejected with Privacy Guard)
                        elif "contact" in msg:
                            if user_id in telegram_active_chats:
                                guard_text = (
                                    f"🚫 **Contact Sharing Blocked — Privacy Guard Active**\n\n"
                                    f"Sharing personal contact cards is strictly blocked in 1-on-1 anonymous matching.\n\n"
                                    f"{LEGAL_DISCLAIMER_TEXT}\n"
                                    f"{PRIVACY_WARNING_TEXT}"
                                )
                                asyncio.create_task(bot.send_message(chat_id, guard_text))
                            else:
                                asyncio.create_task(bot.send_message(chat_id, "👤 Contact sharing is disabled. Talk to me directly anytime!"))
                        # Case F: Photo sent by user
                        elif "photo" in msg:
                            file_id = msg["photo"][-1]["file_id"]
                            caption = msg.get("caption", "")
                            msg_id = msg.get("message_id")
                            logger.info(f"📸 Photo from {user_id} (@{username})")
                            asyncio.create_task(safe_process_user_photo(bot, chat_id, user, file_id, caption=caption, msg_id=msg_id))
                        # Case G: Document image sent by user
                        elif "document" in msg and msg.get("document", {}).get("mime_type", "").startswith("image/"):
                            file_id = msg["document"]["file_id"]
                            caption = msg.get("caption", "")
                            msg_id = msg.get("message_id")
                            logger.info(f"📄 Image document from {user_id} (@{username})")
                            asyncio.create_task(safe_process_user_photo(bot, chat_id, user, file_id, caption=caption, msg_id=msg_id))
                        # Case H: Sticker
                        elif "sticker" in msg:
                            file_id = msg["sticker"]["file_id"]
                            if user_id in telegram_active_chats:
                                pair = telegram_active_chats[user_id]
                                peer_chat_id = pair["peer_chat_id"]
                                asyncio.create_task(bot.send_sticker_file_id(peer_chat_id, file_id))
                            else:
                                gender = user.get("gender", "male")
                                cinfo = get_user_contact_display(user_id, "lover", gender)
                                asyncio.create_task(bot.send_message(chat_id, f"{cinfo['emoji']} Haha cute sticker! What's up? 🌸"))
                        # Case I: Text Message
                        elif "text" in msg:
                            text = msg["text"]
                            msg_id = msg.get("message_id")
                            logger.info(f"💬 Incoming text from {user_id} (@{username}): {text[:50]}")
                            asyncio.create_task(safe_process_user_text(bot, chat_id, user, text, msg_id=msg_id))

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
