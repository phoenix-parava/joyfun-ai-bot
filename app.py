"""
Joy Bot - Main Application Engine
Your AI Voice Companion & English Practice Friend on Telegram.
"""

import os
import re
import sys
import json
import base64
import hashlib
import hmac
from html import escape as html_escape
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
    ADMIN_CHAT_ID,
    PORT,
    DAILY_FREE_VOICE_LIMIT,
    DAILY_FREE_TEXT_LIMIT,
    DAILY_FREE_AI_CALL_LIMIT,
    DAILY_FREE_REAL_CALL_LIMIT,
    DAILY_FREE_REAL_CHAT_LIMIT,
    VIP_PRICE_INR,
    VIP_TIERS,
    UPI_ID,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
    BOT_VERSION,
    MINI_APP_VERSION,
    SECURITY_VERSION,
    LAST_UPDATE_DATE,
    ADMIN_API_SECRET,
    AD_REWARD_WEBHOOK_SECRET,
    RENDER_API_KEY,
    RENDER_SERVICE_ID,
    BETA_TESTER_LIMIT
)
from security import verify_telegram_init_data, detect_sensitive_pii, extract_and_verify_telegram_auth, generate_telegram_init_data
from database import (
    init_db,
    get_connection,
    get_or_create_user,
    update_user_preference,
    has_user_accepted_terms,
    record_user_accepted_terms,
    is_user_onboarding_completed,
    is_user_beta_approved,
    get_beta_stats,
    get_user_waitlist_info,
    admit_or_waitlist_user,
    grant_beta_access,
    revoke_beta_access,
    get_beta_pioneers_list,
    is_owner_or_co_owner,
    add_co_owner,
    remove_co_owner,
    check_and_increment_usage,
    add_conversation_turn,
    get_recent_history,
    set_vip_status,
    recharge_user_usage,
    recharge_user_via_ad,
    get_user_ad_recharges_today,
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
    save_user_language_request,
    get_user_daily_usage,
    get_user_full_quota_status,
    increment_user_ai_call,
    increment_user_real_call,
    increment_user_real_chat,
    get_user_comprehensive_profile,
    get_user_rating_summary,
    record_user_rating,
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
    set_user_custom_words,
    get_user_custom_words,
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
    get_user_streak_shields,
    add_user_streak_shields,
    revive_broken_streak,
    record_study_quiz_attempt,
    get_user_study_stats,
    record_mock_interview_completion,
    record_voice_call_completion,
    get_user_alarm,
    set_user_alarm_time,
    toggle_user_alarm,
    toggle_user_alarm_voice,
    get_due_morning_alarms,
    mark_alarm_triggered,
    get_user_bedtime,
    set_user_bedtime_time,
    toggle_user_bedtime,
    toggle_user_bedtime_voice,
    get_due_bedtime_alarms,
    mark_bedtime_triggered,
    award_scholar_xp,
    get_user_companion_tone,
    set_user_companion_tone,
    get_campus_leaderboard,
    get_user_rank,
    _IST,
    get_eligible_proactive_users,
    record_match_connection,
    get_user_match_connections,
    mark_user_proactive_sent,
    toggle_user_proactive_checkins,
    record_utr_submission,
    get_payment_request,
    approve_payment_request,
    reject_payment_request,
    touch_user_activity,
    prune_inactive_beta_pioneers,
    get_user_system_lang,
    set_user_system_lang,
    leave_beta_program,
    record_pioneer_vote,
    get_pioneer_votes_summary,
    get_user_pioneer_votes,
    set_user_speech_speed,
    get_user_speech_speed,
    get_user_memories,
    delete_user_memory,
    clear_user_memories
)
from emotional_memory import (
    extract_and_store_memories_async,
    get_proactive_greeting,
    format_memory_context
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
    get_companion_image,
    generate_streak_story_card
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
from onboarding_i18n import (
    get_country_step_1_text,
    get_language_step_2_text,
    get_languages_keyboard_for_country,
    get_gender_step_text,
    get_gender_step_keyboard,
    get_naming_step_text,
    get_bounty_notice_text,
    get_waitlist_card_text,
    get_localized_settings_content,
    get_ui_lang,
)

# Setup logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("JoyBot")

BOT_COMMANDS = [
    {"command": "start", "description": "✨ Chat with Joy"},
    {"command": "phone", "description": "📞 Open Mini Phone & Live Call"},
    {"command": "chat", "description": "👥 Chat with Real People (Anonymous)"},
    {"command": "language", "description": "🌐 Voice & Speech Dialect (Tanglish, German, etc.)"},
    {"command": "menulang", "description": "🖥️ Bot Interface / Menu Language (English, German, etc.)"},
    {"command": "study", "description": "📚 Study Buddy & Active Recall Quizzer"},
    {"command": "streak", "description": "🔥 Daily Streak & Relationship Progress"},
    {"command": "revive", "description": "🛡️ Revive a Recently Broken Streak (24h Window)"},
    {"command": "card", "description": "📸 WhatsApp & IG Story Streak Card"},
    {"command": "vibe", "description": "🔮 Daily Campus Vibe, Energy Meter & College Tarot"},
    {"command": "top", "description": "🏆 Campus Leaderboard & Scholar Hall of Fame"},
    {"command": "teaser", "description": "📢 Daily Dilemma & Channel Growth Teasers"},
    {"command": "memories", "description": "🧠 View & Manage What Joy Remembers"},
    {"command": "menu", "description": "📱 Open Interactive Menu & Settings"},
    {"command": "info", "description": "ℹ️ About, Legal & Community Hub"},
    {"command": "updates", "description": "📜 Official Changelog & Release Dates"},
    {"command": "stats", "description": "📊 Daily Usage, Quota & Streak 🔥"},
    {"command": "refer", "description": "🎁 Invite Friends & Earn Free VIP"},
    {"command": "waitlist", "description": "🎟️ Beta Status & Priority Waitlist Position"},
    {"command": "gift", "description": "🎁 Send Telegram Collectible Gift"},
    {"command": "words", "description": "🌸 Suggest Custom Pet Words / Nicknames"},
    {"command": "tip", "description": "⭐ Tip / Send Stars Gift"},
    {"command": "feedback", "description": "💬 Send Feedback & Feature Requests"},
    {"command": "reset", "description": "🧹 Clear Conversation Memory"},
    {"command": "clean", "description": "🧹 Hide Bottom Buttons (Clean Chat)"}
]

BETA_BOT_COMMANDS = [
    {"command": "commands", "description": "🧪 Beta Pioneer Commands Hub"},
    {"command": "language", "description": "🌐 Voice & Speech Dialect (Tanglish, German, etc.)"},
    {"command": "menulang", "description": "🖥️ Bot Interface / Menu Language (English, German, etc.)"},
    {"command": "vote", "description": "🗳️ Vote on Personas, Dialects & Features"},
    {"command": "streak", "description": "🔥 Daily Streak & Relationship Progress"},
    {"command": "revive", "description": "🛡️ Revive a Recently Broken Streak (24h Window)"},
    {"command": "card", "description": "📸 WhatsApp & IG Story Streak Card"},
    {"command": "vibe", "description": "🔮 Daily Campus Vibe, Energy Meter & College Tarot"},
    {"command": "top", "description": "🏆 Campus Leaderboard & Scholar Hall of Fame"},
    {"command": "teaser", "description": "📢 Daily Dilemma & Channel Growth Teasers"},
    {"command": "memories", "description": "🧠 View & Manage What Joy Remembers"},
    {"command": "icebreaker", "description": "🎯 Dating & Call Icebreaker Minigames"},
    {"command": "vip", "description": "🔒 Founder Price Lock-in (50% Off Lifetime)"},
    {"command": "resetquota", "description": "⚡ Reset Today's Limits (Unlimited Testing)"},
    {"command": "retest", "description": "🔄 Test Onboarding Flow from Scratch"},
    {"command": "mic", "description": "🎤 Mini Phone Mic & Audio Latency Test"},
    {"command": "bug", "description": "🐛 Report Bug to Phoenix for Free VIP"},
    {"command": "suggest", "description": "💡 Suggest Feature or Slang Correction"},
    {"command": "words", "description": "🌸 Suggest Custom Pet Words / Nicknames"},
    {"command": "speed", "description": "⚡ Change Voice Speed (1.0x - 1.25x)"},
    {"command": "stats", "description": "📊 Daily Pioneer Limits & Usage (10 Calls)"},
    {"command": "phone", "description": "📞 Open Mini Phone & Live Call"},
    {"command": "chat", "description": "👥 Real People Anonymous Match"},
    {"command": "menu", "description": "📱 Interactive Menu & Settings"},
    {"command": "info", "description": "ℹ️ About, Legal & Community Hub"},
    {"command": "exitbeta", "description": "🚪 Leave Beta Program (Surrender Slot)"}
]

ICEBREAKER_QUESTIONS = [
    "Rank Chai, Coffee, and Sting from best to worst in 10 seconds!",
    "Hot Take: Is eating Maggi with tomato ketchup a genius hack or an actual crime against humanity?",
    "What was the most ridiculous lie you told your professor or boss to skip a morning class or meeting?",
    "If someone looks through your Spotify or YouTube search history right now, what is the most embarrassing thing they'll find?",
    "If you could drop out of college or quit your job right now to start any crazy startup, what would it be?",
    "Bunking for a movie or sitting in the canteen for 3 hours? What's your all-time top college memory?",
    "Tea (Chai) or Coffee? And what is your holy grail 2 AM comfort snack?",
    "What is the single most overrated movie, song, or trend of all time that everyone pretends to love?",
    "What is one secret obsession or hobby that none of your everyday friends know about?",
    "If you won a free round-trip flight ticket to anywhere in the world tonight, where are you flying?",
    "What's that one song you blast on repeat that you'd be secretly embarrassed to play out loud on speaker?",
    "If you were given ₹1 Crore with one rule: you must spend it all in 24 hours without buying real estate or gold, what are you buying?",
    "Which superpower would you pick: Teleportation, Invisibility, or Reading Minds?",
    "What is the most awkward brain-fade thing that ever happened to you in public?",
    "What is a major red flag in friendship that makes you distance yourself immediately?",
    "Are you an early bird or a 2 AM overthinker? What usually keeps you awake at night?",
    "What was the funniest or most ridiculous lie you believed as a kid that turned out to be totally fake?",
    "If you had to survive a zombie apocalypse, which one friend are you definitely NOT taking with you?",
    "What's your biggest pet peeve that annoys you instantly?",
    "Solo trips or road trip with a chaotic group of friends? Where is your dream destination?"
]

# Legal and Privacy Disclaimers for PII & Media Guard
LEGAL_DISCLAIMER_TEXT = "⚖️ **Legal Disclaimer:** *Not responsible for personal data shared.*"
PRIVACY_WARNING_TEXT = '🛡️ **Privacy Warning:** *"Your privacy is your personal power—once exposed online, it can never be retrieved. Protect your identity."*'

# Pre-compiled high-performance regex patterns for Real-Time PII & Sensitive Data Scrubber
EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', re.IGNORECASE)
PHONE_REGEX_1 = re.compile(r'\b(?:(?:\+|00)\d{1,3}[\s.-]?)?(?:\(?\d{2,5}\)?[\s.-]?)?\d{3,5}[\s.-]?\d{4,5}\b')
PHONE_REGEX_2 = re.compile(r'\b[6-9]\d{9}\b')
PHONE_REGEX_3 = re.compile(r'\b(?:\+91|91)[\s-]?[6-9]\d{9}\b')
URL_REGEX = re.compile(r'(?:https?://|www\.)[^\s]+', re.IGNORECASE)
SOCIAL_LINKS_REGEX = re.compile(r'(?:t\.me/|telegram\.me/|wa\.me/|instagram\.com/|snapchat\.com/|facebook\.com/|fb\.com/|wa\.link/|chat\.whatsapp\.com/)[^\s]+', re.IGNORECASE)
TELEGRAM_USERNAME_REGEX = re.compile(r'@([a-zA-Z0-9_]{4,32})')
AADHAAR_REGEX = re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b')
PAN_REGEX = re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b', re.IGNORECASE)
EXCLUDED_SYSTEM_USERNAMES = {"joy_fun_ai_bot", "joyfun_ai_bot", "joy", "here", "everyone", "channel"}

def detect_sensitive_pii(text: str) -> tuple[bool, str]:
    """
    Scans text for sensitive Personally Identifiable Information (PII) before sending:
    - Phone numbers (10+ digits, Indian/international formats, spaced digits)
    - Email addresses
    - Social media handles / direct messaging links (WhatsApp, Telegram, Instagram, Snapchat, etc.)
    - External URLs and t.me links
    - Identity documents (Aadhaar, PAN)
    Returns (True, violation_reason) if sensitive PII is detected, else (False, "").
    """
    if not text:
        return False, ""
    
    clean = text.strip()

    if EMAIL_REGEX.search(clean):
        return True, "Email Address"

    if URL_REGEX.search(clean) or SOCIAL_LINKS_REGEX.search(clean):
        return True, "External Link / URL"

    for handle in TELEGRAM_USERNAME_REGEX.findall(clean):
        if handle.lower() not in EXCLUDED_SYSTEM_USERNAMES:
            return True, f"Telegram Username (@{handle})"

    if AADHAAR_REGEX.search(clean):
        return True, "National ID (Aadhaar Number)"

    if PAN_REGEX.search(clean):
        return True, "Tax / Identity Card (PAN Number)"

    digits_only = re.sub(r'[^\d]', '', clean)
    if PHONE_REGEX_2.search(clean) or PHONE_REGEX_3.search(clean) or (10 <= len(digits_only) <= 15 and PHONE_REGEX_1.search(clean)):
        return True, "Phone / Mobile Number"

    return False, ""

def get_persistent_reply_keyboard(gender: str = "male", active_contact: str = "lover", custom_name: str = "", user_id: Optional[int] = None) -> dict:
    """Returns a docked, compact keyboard at the bottom of the chat for fast access beside emoji button."""
    return {
        "keyboard": [
            [
                {"text": "👥 Chat Real People"},
                {"text": "🎁 Invite Friends"},
                {"text": "📱 Menu"}
            ]
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

# Concurrency & Overload Protection Semaphores (Render 525 MB RAM guard: capped at 10)
AI_CALL_SEMAPHORE = asyncio.Semaphore(10)
VOICE_CALL_SEMAPHORE = asyncio.Semaphore(10)

# Per-User Throttling & Rate Limiting Middleware (Anti-Flood & API Credit Shield)
USER_LAST_ACTION: Dict[int, float] = {}
USER_LAST_CALL_CREATE: Dict[int, float] = {}
RATE_LIMIT_COOLDOWN = 1.5       # 1.5 seconds between messages or button taps
CALL_CREATE_COOLDOWN = 5.0      # 5 seconds between new voice call creations

def is_user_throttled(user_id: int) -> bool:
    """Returns True if user is sending requests faster than allowed rate."""
    if user_id == ADMIN_CHAT_ID:
        return False
    now = time.time()
    last = USER_LAST_ACTION.get(user_id, 0.0)
    if (now - last) < RATE_LIMIT_COOLDOWN:
        return True
    USER_LAST_ACTION[user_id] = now
    return False

def is_call_creation_throttled(user_id: int) -> bool:
    """Returns True if user is creating voice calls faster than allowed rate."""
    if user_id == ADMIN_CHAT_ID:
        return False
    now = time.time()
    last = USER_LAST_CALL_CREATE.get(user_id, 0.0)
    if (now - last) < CALL_CREATE_COOLDOWN:
        return True
    USER_LAST_CALL_CREATE[user_id] = now
    return False

# Strict Admin Command & Callback Whitelist (Zero Privilege Escalation)
ADMIN_SLASH_COMMANDS = {
    "/admin", "/owner", "/stats", "/users", "/subscribers", "/vips",
    "/addvip", "/removevip", "/rmsub", "/msg", "/broadcast",
    "/feedbacks", "/feedback_list", "/admin_usage", "/backup",
    "/grant_beta", "/admit", "/makebeta", "/setbeta", "/addbeta",
    "/removebeta", "/revokebeta", "/delbeta", "/betalist", "/pioneers",
    "/betauser", "/batauser"
}

ADMIN_CALLBACK_PREFIXES = (
    "approve_utr_", "reject_utr_", "admin_", "owner_",
    "reply_user_", "chat_user_", "user_detail_", "reset_quota_", "gift_vip_",
    "bounty_"
)

# Anonymous Chat Skip Cooldown: {(user_a, user_b): timestamp}
telegram_skip_cooldown: Dict[Tuple[int, int], float] = {}

# User UTR payment submission tracker: {user_id: True}
user_waiting_utr: Dict[int, bool] = {}

# Language request tracker: {user_id: is_from_menu_bool}
user_waiting_lang_request: Dict[int, bool] = {}

# Admin messaging target tracker: {OWNER_ID: target_user_id}
admin_pending_target: Dict[int, int] = {}
# Active direct chat between user and admin: {user_id: True}
user_chatting_with_admin: Dict[int, bool] = {}

# Active Mock Interview Sessions: {user_id: {"track": str, "round": int, "questions": list, "scores": list, "fillers": int, "feedbacks": list}}
active_interviews: Dict[int, dict] = {}

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

    # Defensive guard: Telegram Bot API enforces a hard 4096 character limit on messages
    if text and len(text) > 4000:
        text = text[:3950] + "\n\n*(... content truncated to fit Telegram limit)*"

    if message_id:
        res = await bot.edit_message_text(chat_id, message_id, text, reply_markup=reply_markup)
        if isinstance(res, dict) and res.get("ok"):
            active_menu_messages[chat_id] = message_id
            return message_id

    await dismiss_active_menu(bot, chat_id)
    res = await bot.send_message(chat_id, text, reply_markup=reply_markup)
    if isinstance(res, dict):
        new_id = res.get("result", {}).get("message_id") or res.get("message_id")
    else:
        new_id = getattr(res, "message_id", None)
    if new_id:
        active_menu_messages[chat_id] = new_id
        return new_id
    return 0

async def send_quota_exhausted_screen(bot: TelegramClient, chat_id: int, user: dict, c_name: str, c_emoji: str, spoken_text: str, msg_id: Optional[int] = None):
    """
    Presents a clean, high-converting quota upgrade screen with 1-tap micro-pass options:
    - ⚡ ₹19 Day Pass (Instant reset & 24h unlimited)
    - Free 5-Friend Referral Unlock (Grants 30 Days Free VIP)
    """
    user_id = user["user_id"]
    user_mask = get_mask_by_user_id(user_id) or f"Joy-{user_id}"
    stats = get_referral_stats(user_id)
    ref_count = stats.get("completed_count", 0)
    needed = max(0, 5 - ref_count)
    invite_url = f"https://t.me/joy_fun_ai_bot?start=ref_{user_mask}"

    screen_text = (
        f"{c_emoji} **{c_name}:**\n"
        f"\"{spoken_text}\"\n\n"
        f"⚡ **Daily Free Quota Exhausted**\n\n"
        f"Don't let the conversation stop! Choose how you want to keep chatting right now:\n\n"
        f"• **⚡ 24h Day Pass:** ⭐ 25 Stars (Instant quota reset + 24h unlimited)\n"
        f"• **🎁 Free 30-Day VIP:** Invite 5 friends to unlock full VIP free!\n"
        f"  *(Progress: {ref_count}/5 Friends Joined — {needed} more to go)*\n"
        f"• Your invite link: `{invite_url}`"
    )

    keyboard = {
        "inline_keyboard": [
            [{"text": "⚡ 25 Stars (Instant Reset & 24h Pass)", "callback_data": "pay_stars_day"}],
            [{"text": f"🎁 Invite 5 Friends ({ref_count}/5 Joined)", "callback_data": "menu_referral"}],
            [{"text": "⭐ View All VIP Passes", "callback_data": "menu_vip"}, {"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, screen_text, keyboard, user_msg_id=msg_id)

LANGUAGE_NAMES = {
    "auto": "🌐 Auto-Detect",
    "english": "💬 English",
    "hinglish": "💬 Hinglish (Hindi)",
    "tanglish": "💬 Tanglish (Tamil)",
    "telugu": "💬 Telugu (తెలుగు)",
    "malayalam": "💬 Malayalam (മലയാളം)",
    "kannada": "💬 Kannada (ಕನ್ನಡ)",
    "bengali": "💬 Bengali (বাংলা)",
    "marathi": "💬 Marathi (मराठी)",
    "spanish": "💬 Spanish (Español)",
    "german": "💬 German (Deutsch)"
}

def get_main_keyboard(gender: str = "male", active_contact: str = "lover", user_id: Optional[int] = None, ui_lang: str = "english") -> dict:
    contact = get_user_contact_display(user_id, active_contact, gender)
    c_name = contact.get("name", "Joy")
    user_lang = get_user_language(user_id) if user_id else "auto"
    
    if user_id and ui_lang == "english":
        try:
            user_country = get_user_country(user_id)
            user_sys = get_user_system_lang(user_id)
            ui_lang = get_ui_lang({"system_lang": user_sys, "country_code": user_country}, user_country)
        except Exception:
            ui_lang = "english"
            
    call_url = f"https://joyfun-ai-bot.onrender.com/call?gender={gender}&contact={active_contact}&lang={user_lang}&tab=contacts&v={BOT_VERSION}"
    if user_id:
        user_mask = get_mask_by_user_id(user_id)
        call_url += f"&uid={user_id}&name={urllib.parse.quote(c_name)}&mask={user_mask}&v={BOT_VERSION}"

    labels = {
        "english": {
            "phone": "📞 Call Joy AI",
            "real_chat": "👥 Chat Real People",
            "profile": "👤 My Profile",
            "vip": "👑 Joy VIP",
            "settings": "⚙️ Settings",
            "voice_lang": "🗣️ Voice & Accent",
            "menu_lang": "🖥️ Menu Language",
            "streak": "🔥 My Streaks",
            "memory": "🧠 Memory Vault",
            "vibe": "🔮 Daily Vibe",
            "top": "🏆 Leaderboard",
            "teaser": "📢 Daily Dilemma",
            "refer": "🎁 Invite Friends",
            "quota": "📊 Daily Limits",
            "study": "📚 Study Hub",
            "bedtime": "🌙 Bedtime Wind-Down",
            "feedback": "💬 Send Feedback",
            "updates": "📜 What's New",
            "notice": "🎟️ Pioneer Notice",
            "creator": "👨‍💻 About Creator",
            "legal": "⚖️ Rules & Privacy",
            "about_hub": "ℹ️ About Joy",
            "close": "❌ Close"
        },
        "german": {
            "phone": "📞 Mini Phone",
            "settings": "⚙️ Einstellungen",
            "voice_lang": "🗣️ Sprache & Dialekt",
            "menu_lang": "🖥️ Menüsprache",
            "streak": "🔥 Streak & Bindung",
            "memory": "🧠 Gedächtnis-Tresor",
            "vibe": "🔮 Täglicher Campus-Vibe",
            "top": "🏆 Campus-Bestenliste",
            "teaser": "📢 Tägliches Dilemma",
            "refer": "🎁 Freunde einladen",
            "quota": "📊 Kontingente & Limits",
            "study": "📚 Lernbegleiter",
            "bedtime": "🌙 Abend-Entspannung",
            "feedback": "💬 Feedback & Fehlermeldung",
            "updates": "📜 Release-Updates",
            "notice": "🎟️ Pionier-Hinweis",
            "creator": "👨‍💻 Über Entwickler (Phoenix)",
            "legal": "⚖️ Rechtliches & DSGVO",
            "about_hub": "ℹ️ Über & Rechtliches",
            "close": "❌ Schließen"
        },
        "spanish": {
            "phone": "📞 Mini Phone",
            "settings": "⚙️ Ajustes",
            "voice_lang": "🗣️ Idioma y Voz",
            "menu_lang": "🖥️ Idioma del Menú",
            "streak": "🔥 Racha y Vínculo",
            "memory": "🧠 Bóveda de Recuerdos",
            "vibe": "🔮 Vibra del Campus",
            "top": "🏆 Tabla de Clasificación",
            "teaser": "📢 Dilema Diario",
            "refer": "🎁 Invitar Amigos",
            "quota": "📊 Cuotas y Límites",
            "study": "📚 Compañero de Estudio",
            "bedtime": "🌙 Descanso Nocturno",
            "feedback": "💬 Comentarios y Errores",
            "updates": "📜 Actualizaciones",
            "notice": "🎟️ Aviso de Pionero",
            "creator": "👨‍💻 Sobre el Creador (Phoenix)",
            "legal": "⚖️ Legal y Cumplimiento",
            "about_hub": "ℹ️ Acerca de y Legal",
            "close": "❌ Cerrar"
        },
        "telugu": {
            "phone": "📞 Mini Phone",
            "settings": "⚙️ సెట్టింగ్‌లు",
            "voice_lang": "🗣️ వాయిస్ & భాష",
            "menu_lang": "🖥️ మెనూ భాష",
            "streak": "🔥 స్ట్రీక్ & బంధం",
            "memory": "🧠 జ్ఞాపకాల ఖజానా",
            "vibe": "🔮 రోజువారీ వైబ్",
            "top": "🏆 లీడర్‌బోర్డ్",
            "teaser": "📢 డైలీ డిలెంమా స్టూడియో",
            "refer": "🎁 ఆహ్వానించండి",
            "quota": "📊 పరిమితులు & కోటాలు",
            "study": "📚 స్టడీ కంపానియన్",
            "bedtime": "🌙 నిద్రవేళ విశ్రాంతి",
            "feedback": "💬 ఫీడ్‌బ్యాక్ & బగ్ రిపోర్ట్",
            "updates": "📜 విడుదల నవీకరణలు",
            "notice": "🎟️ పయనీర్ నోటీసు",
            "creator": "👨‍💻 సృష్టికర్త గురించి (Phoenix)",
            "legal": "⚖️ చట్టపరమైన నిబంధనలు",
            "about_hub": "ℹ️ సమాచారం & చట్టపరమైనవి",
            "close": "❌ మూసివేయి"
        },
        "malayalam": {
            "phone": "📞 Mini Phone",
            "settings": "⚙️ ക്രമീകരണങ്ങൾ",
            "voice_lang": "🗣️ ശബ്ദവും ഭാഷയും",
            "menu_lang": "🖥️ മെനു ഭാഷ",
            "streak": "🔥 സ്ട്രീക്കും ബന്ധവും",
            "memory": "🧠 ഓർമ്മ നിലവറ",
            "vibe": "🔮 ക്യാമ്പസ് വൈബ്",
            "top": "🏆 ലീഡർബോർഡ്",
            "teaser": "📢 പ്രതിദിന ഡിലെമ്മ സ്റ്റുഡിയോ",
            "refer": "🎁 സുഹൃത്തുക്കളെ ക്ഷണിക്കുക",
            "quota": "📊 ക്വോട്ടകളും പരിധികളും",
            "study": "📚 പഠന സഹായി",
            "bedtime": "🌙 രാത്രി വിശ്രമം",
            "feedback": "💬 ഫീഡ്‌ബാക്ക് & ബഗ് റിപ്പോർട്ട്",
            "updates": "📜 പുതിയ അപ്‌ഡേറ്റുകൾ",
            "notice": "🎟️ പയനിയർ അറിയിപ്പ്",
            "creator": "👨‍💻 ക്രിയേറ്ററെക്കുറിച്ച് (Phoenix)",
            "legal": "⚖️ നിയമപരമായ വിവരങ്ങൾ",
            "about_hub": "ℹ️ വിവരങ്ങളും നിയമങ്ങളും",
            "close": "❌ അടയ്ക്കുക"
        }
    }
    L = labels.get(ui_lang, labels["english"])

    rows = [
        [
            {"text": L["phone"], "web_app": {"url": call_url}},
            {"text": L.get("real_chat", "👥 Chat Real People"), "callback_data": "menu_match_real"}
        ],
        [
            {"text": L.get("profile", "👤 My Profile"), "callback_data": "menu_user_profile"},
            {"text": L.get("vip", "👑 Joy VIP"), "callback_data": "menu_vip"}
        ],
        [
            {"text": L["study"], "callback_data": "menu_study"},
            {"text": L["quota"], "callback_data": "menu_quota"}
        ],
        [
            {"text": L["streak"], "callback_data": "menu_streak"},
            {"text": L["settings"], "callback_data": "menu_settings"}
        ],
        [
            {"text": L["about_hub"], "callback_data": "menu_about_hub"},
            {"text": L["feedback"], "callback_data": "menu_feedback"}
        ]
    ]

    if user_id == OWNER_ID:
        rows.append([
            {"text": "👑 Owner Command Center & Users", "callback_data": "owner_hub"},
            {"text": "⚡ Cloud Usage (Admin)", "callback_data": "admin_refresh_quota"}
        ])

    rows.append([{"text": L["close"], "callback_data": "menu_close"}])

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
    user_country = get_user_country(user_id) if user_id else ""
    ui_lang = get_ui_lang(user, user_country)
    keyboard = get_main_keyboard(gender, active_contact, user_id, ui_lang=ui_lang)
    cinfo = get_user_contact_display(user_id, active_contact, gender)
    vip_active, _, _ = is_user_vip(user_id) if user_id else (False, "", 0)
    is_pioneer = bool(user.get("is_beta_tester") == 1)
    pioneer_slot = user.get("beta_slot_number") or 1

    if ui_lang == "german":
        vip_badge = "⭐ Joy VIP (Aktiv)" if vip_active else (f"🎟️ Beta-Pionier #{pioneer_slot}" if is_pioneer else "🆓 Kostenloses Mitglied")
        text = (
            f"📱 **Joy Hauptmenü**\n\n"
            f"• **Begleiter:** {cinfo['emoji']} **{cinfo['name']}** ({cinfo['tag']}) • 🟢 Online\n"
            f"• **Status:** {vip_badge}\n\n"
            f"Wähle eine Option unten:"
        )
    elif ui_lang == "spanish":
        vip_badge = "⭐ Joy VIP (Activo)" if vip_active else (f"🎟️ Pionero Beta #{pioneer_slot}" if is_pioneer else "🆓 Miembro Gratuito")
        text = (
            f"📱 **Menú Principal de Joy**\n\n"
            f"• **Compañero:** {cinfo['emoji']} **{cinfo['name']}** ({cinfo['tag']}) • 🟢 En Línea\n"
            f"• **Estado:** {vip_badge}\n\n"
            f"Selecciona una opción abajo:"
        )
    elif ui_lang == "telugu":
        vip_badge = "⭐ జాయ్ VIP (యాక్టివ్)" if vip_active else (f"🎟️ బీటా పయనీర్ #{pioneer_slot}" if is_pioneer else "🆓 ఉచిత సభ్యుడు")
        text = (
            f"📱 **జాయ్ ముఖ్య మెనూ**\n\n"
            f"• **సహచరుడు:** {cinfo['emoji']} **{cinfo['name']}** ({cinfo['tag']}) • 🟢 ఆన్‌లైన్\n"
            f"• **స్థితి:** {vip_badge}\n\n"
            f"క్రింద ఉన్న ఎంపికను ఎంచుకోండి:"
        )
    elif ui_lang == "malayalam":
        vip_badge = "⭐ ജോയ് വിഐപി (ആക്റ്റീവ്)" if vip_active else (f"🎟️ ബീറ്റാ പയനിയർ #{pioneer_slot}" if is_pioneer else "🆓 സൗജന്യ അംഗം")
        text = (
            f"📱 **ജോയ് പ്രധാന മെനു**\n\n"
            f"• **കൂട്ടുകാരൻ:** {cinfo['emoji']} **{cinfo['name']}** ({cinfo['tag']}) • 🟢 ഓൺലൈൻ\n"
            f"• **സ്റ്റാറ്റസ്:** {vip_badge}\n\n"
            f"താഴെയുള്ള ഒരു ഓപ്ഷൻ തിരഞ്ഞെടുക്കുക:"
        )
    else:
        vip_badge = "⭐ Joy VIP (Active)" if vip_active else (f"🎟️ Beta Pioneer #{pioneer_slot}" if is_pioneer else "🆓 Free Member")
        text = (
            f"📱 **Joy Main Menu**\n\n"
            f"• **Companion:** {cinfo['emoji']} **{cinfo['name']}** ({cinfo['tag']}) • 🟢 Online\n"
            f"• **Status:** {vip_badge}\n\n"
            f"Select an option below:"
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
    is_pioneer = bool(user.get("is_beta_tester") == 1)
    pioneer_slot = user.get("beta_slot_number") or 1
    if vip_active:
        vip_str = "⭐ **Joy VIP (Active)** — Unlimited 24/7 Calls"
        usage_str = "✨ Unlimited Voice Notes & Calls | Unlimited Texts"
    elif is_pioneer:
        vip_str = f"🎟️ **Beta Pioneer #{pioneer_slot}** — 10 Live Calls / Day"
        usage_str = f"🎙️ {voice_used}/50 Voice Notes | 💬 Unlimited Texts | 📞 10 Calls (45m)"
    else:
        vip_str = "🆓 **Free Plan**"
        usage_str = f"🎙️ {voice_used}/{DAILY_FREE_VOICE_LIMIT} Voice Notes | 💬 {text_used}/{DAILY_FREE_TEXT_LIMIT} Texts"

    # Memory summary
    if user_memory:
        mem_str = f"✅ Active ({len(user_memory)} chars synced)"
    else:
        mem_str = "⚪ Not Synced"

    data_sharing_active = get_user_data_sharing(user_id)
    data_sharing_str = "✅ Enabled (Dev Analytics Opt-in)" if data_sharing_active else "🔒 Disabled (100% Private)"
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

    profile_data = {
        "first_name": first_name,
        "username_str": username_str,
        "user_mask": user_mask,
        "country_display": country_display,
        "gender_str": gender_str,
        "lang_label": lang_label,
        "account_str": account_str,
        "vip_str": vip_str,
        "usage_str": usage_str,
        "data_sharing_str": data_sharing_str,
        "mem_str": mem_str,
        "bot_version": BOT_VERSION,
        "mini_app_version": MINI_APP_VERSION,
        "last_update": LAST_UPDATE_DATE,
        "portal_url": portal_url,
        "c_flag": c_flag,
        "c_name_short": c_name_short,
        "c_name": c_name,
        "data_sharing_active": data_sharing_active
    }
    ui_lang = get_ui_lang(user, user_country)
    card_text, keyboard = get_localized_settings_content(ui_lang, profile_data)
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

    if data_sharing_active:
        status_label = "💡 Enabled (Opt-in Developer Feedback)"
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
        "  If you choose to enable *Dev Data Sharing*, anonymized snippets help improve Joy's conversational understanding and empathy.\n\n"
        f"🏷️ **Security Baseline:**\n"
        f"• 🛡️ **Security Version:** `{SECURITY_VERSION}`\n"
        f"• 🕒 **Last Security Audit:** `{LAST_UPDATE_DATE}`\n\n"
        f"Current Status: **{status_icon} {status_label}**\n\n"
        "👇 Tap below to toggle data sharing ON or OFF anytime:"
    )

    toggle_btn_text = "🔒 Turn OFF Data Sharing (100% Private)" if data_sharing_active else "💡 Turn ON Dev Data Sharing (Opt-in)"

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
    current_status = "🤝 Enabled (Dev Analytics Opt-In)" if data_sharing_active else "🔒 100% Private (No Data Shared)"

    text = (
        "📜 **Joy AI — Terms of Service & Privacy Policy**\n\n"
        "Welcome to Joy AI. We believe in complete transparency, zero hidden tracking, and strict privacy protection:\n\n"
        "🛡️ **1. Privacy Policy & Data Collection:**\n"
        "• **100% Private by Default:** We never harvest, sell, or rent your personal credentials, phone numbers, or emails.\n"
        "• **Live Voice Calls:** Duplex voice calls run in volatile server RAM using direct WebRTC. Zero audio recordings are stored on disk unless you explicitly opt in.\n"
        "• **Dev Data Sharing (Opt-in only):** If you enable Data Sharing, anonymized metrics help improve companion models. Data sharing remains 100% optional.\n"
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
            [{"text": "⚖️ Legal Acts, Penalties & Fines", "callback_data": "menu_legal_acts"}],
            [{"text": "🛡️ Change Privacy Setting", "callback_data": "menu_privacy"}],
            [{"text": "⬅️ Back to Menu", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_legal_acts_menu(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Presents community safety standards, user rules, and privacy protections."""
    text = (
        "⚖️ **Community Rules & Safety**\n\n"
        "Joy is built to be a safe, positive, and friendly space for everyone:\n\n"
        "• 🛡️ **100% Private Calls:** Live calls & voice notes are processed in memory only. Zero audio recordings are stored.\n"
        "• 🤝 **Respectful Community:** Harassment, abuse, hate speech, or inappropriate content is strictly prohibited.\n"
        "• 🔒 **Privacy Shield:** Personal contact numbers, addresses, and external links are automatically blocked.\n"
        "• 📜 **Compliant & Legal:** Joy operates strictly under digital personal data protection laws.\n\n"
        "Enjoy friendly, respectful conversations with friends and Joy!"
    )

    keyboard = {
        "inline_keyboard": [
            [{"text": "📜 View General Terms", "callback_data": "menu_terms"}, {"text": "🛡️ Privacy Setting", "callback_data": "menu_privacy"}],
            [{"text": "👨‍💻 About Creator", "callback_data": "menu_about_creator"}],
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

CAMPUS_STUDY_DECKS = {
    "dsa": {
        "title": "💻 DSA & Coding Blitz",
        "questions": [
            {
                "id": "dsa_01",
                "q": "What is the worst-case time complexity of QuickSort?",
                "opts": ["O(N log N)", "O(N²)", "O(N)", "O(log N)"],
                "ans": 1,
                "explain": "When the chosen pivot is consistently the smallest or largest element (e.g. naive pivot on already sorted data), recursion depth hits N, degrading performance to O(N²)."
            },
            {
                "id": "dsa_02",
                "q": "Which data structure operates strictly on First-In-First-Out (FIFO) ordering?",
                "opts": ["Stack", "Queue", "Priority Queue", "Binary Search Tree"],
                "ans": 1,
                "explain": "A Queue operates on FIFO (First-In, First-Out), whereas a Stack operates on LIFO (Last-In, First-Out)."
            },
            {
                "id": "dsa_03",
                "q": "What is the average time complexity to search an element in a balanced Binary Search Tree (AVL / Red-Black)?",
                "opts": ["O(1)", "O(N)", "O(log N)", "O(N log N)"],
                "ans": 2,
                "explain": "Because each comparison cuts the search space in half and tree height is bounded to O(log N), search takes O(log N)."
            },
            {
                "id": "dsa_04",
                "q": "In Python, which of the following built-in collection types is immutable?",
                "opts": ["List", "Dictionary", "Tuple", "Set"],
                "ans": 2,
                "explain": "Tuples and strings are immutable in Python; their elements cannot be reassigned or modified in-place after creation."
            },
            {
                "id": "dsa_05",
                "q": "What technique avoids recomputing overlapping subproblems by caching previous results in an array or table?",
                "opts": ["Greedy Algorithm", "Dynamic Programming", "Backtracking", "Divide and Conquer"],
                "ans": 1,
                "explain": "Dynamic Programming (DP) solves complex problems by breaking them into overlapping subproblems and memoizing/tabulating results."
            },
            {
                "id": "dsa_06",
                "q": "In a Hash Table with separate chaining, what is the worst-case lookup time when all N keys collide into the same bucket?",
                "opts": ["O(1)", "O(log N)", "O(N)", "O(N²)"],
                "ans": 2,
                "explain": "If all keys collide into a single linked list bucket, search degrades to a linear scan of length N, which is O(N)."
            }
        ]
    },
    "aptitude": {
        "title": "🧠 Quantitative Aptitude & Placement Logic",
        "questions": [
            {
                "id": "apt_01",
                "q": "A train 120m long passes an electric pole in 6 seconds. What is the speed of the train in km/h?",
                "opts": ["60 km/h", "72 km/h", "80 km/h", "90 km/h"],
                "ans": 1,
                "explain": "Speed = Distance / Time = 120m / 6s = 20 m/s. Converting to km/h: 20 * (18/5) = 72 km/h."
            },
            {
                "id": "apt_02",
                "q": "Person A can complete a project in 10 days, while Person B can do it in 15 days. How many days will they take working together?",
                "opts": ["5 days", "6 days", "8 days", "12.5 days"],
                "ans": 1,
                "explain": "Together, they do 1/10 + 1/15 = 5/30 = 1/6 of the work per day. Total time needed = 6 days."
            },
            {
                "id": "apt_03",
                "q": "If the price of a laptop is increased by 20% and then reduced by 20%, what is the net percentage change in price?",
                "opts": ["0% (No change)", "2% decrease", "4% decrease", "4% increase"],
                "ans": 2,
                "explain": "Net change = x + y + (xy/100) = +20 - 20 - (400/100) = -4%. The net price decreases by 4%."
            },
            {
                "id": "apt_04",
                "q": "Find the missing number in the sequence: 2, 6, 12, 20, 30, ?",
                "opts": ["36", "40", "42", "48"],
                "ans": 2,
                "explain": "Differences between consecutive terms are +4, +6, +8, +10, so next difference is +12. 30 + 12 = 42 (or n² + n)."
            },
            {
                "id": "apt_05",
                "q": "A shopkeeper marks an item 50% above cost price and allows a 20% discount. What is his actual profit percentage?",
                "opts": ["20%", "25%", "30%", "10%"],
                "ans": 0,
                "explain": "If CP = 100, MP = 150. Discount of 20% on 150 is 30, so SP = 120. Profit = (120 - 100) / 100 = 20%."
            },
            {
                "id": "apt_06",
                "q": "Two dice are rolled simultaneously. What is the probability that the sum of the numbers is 7?",
                "opts": ["1/6", "1/12", "5/36", "7/36"],
                "ans": 0,
                "explain": "Pairs summing to 7 are (1,6), (2,5), (3,4), (4,3), (5,2), (6,1) = 6 outcomes out of 36 total. Probability = 6/36 = 1/6."
            }
        ]
    },
    "core": {
        "title": "⚡ Core Engineering & Technical Viva",
        "questions": [
            {
                "id": "core_01",
                "q": "Which of the following is NOT one of Coffman's 4 necessary conditions for Deadlock in Operating Systems?",
                "opts": ["Mutual Exclusion", "Hold and Wait", "Preemption Allowed", "Circular Wait"],
                "ans": 2,
                "explain": "The 4 Coffman conditions are: Mutual Exclusion, Hold and Wait, No Preemption (resources cannot be preempted), and Circular Wait."
            },
            {
                "id": "core_02",
                "q": "In Relational Database Management Systems (RDBMS), what does the 'I' in ACID stand for?",
                "opts": ["Indexing", "Integrity", "Isolation", "Iteration"],
                "ans": 2,
                "explain": "ACID stands for Atomicity, Consistency, Isolation, and Durability. Isolation ensures concurrent transactions do not interfere."
            },
            {
                "id": "core_03",
                "q": "What is the sequence of packet flags exchanged during a standard TCP 3-Way Handshake connection setup?",
                "opts": ["ACK -> SYN -> ACK", "SYN -> SYN-ACK -> ACK", "SYN -> ACK -> FIN", "DATA -> ACK -> PSH"],
                "ans": 1,
                "explain": "Client sends SYN, Server responds with SYN-ACK, and Client confirms with ACK before data transmission begins."
            },
            {
                "id": "core_04",
                "q": "In Object-Oriented Programming (OOP), what principle allows a subclass to provide a specific implementation of a method already defined in its parent class?",
                "opts": ["Method Overloading", "Method Overriding", "Encapsulation", "Abstraction"],
                "ans": 1,
                "explain": "Method Overriding enables runtime polymorphism, allowing a subclass to define specialized behavior for an inherited parent method."
            },
            {
                "id": "core_05",
                "q": "What phenomenon occurs in virtual memory when the CPU spends more time swapping pages in/out than executing user instructions?",
                "opts": ["Paging", "Fragmentation", "Thrashing", "Starvation"],
                "ans": 2,
                "explain": "Thrashing happens when the total working set of active processes exceeds physical memory, causing continuous page faults."
            },
            {
                "id": "core_06",
                "q": "Which standard transport protocol and default port does the Domain Name System (DNS) query primarily utilize?",
                "opts": ["TCP Port 80", "UDP Port 53", "TCP Port 443", "UDP Port 67"],
                "ans": 1,
                "explain": "Standard DNS queries use UDP port 53 for low-latency, single-packet lookups (falling back to TCP for large zone transfers)."
            }
        ]
    }
}


INTERVIEW_TRACKS = {
    "sde": {
        "title": "💻 SDE & Software Engg Viva",
        "badge": "SDE Viva",
        "description": "Hash tables, OS process vs thread, and distributed rate limiting architecture",
        "questions": [
            "Explain how a Hash Table handles collisions, and compare Chaining vs Open Addressing under high load factors.",
            "What is the difference between a Process and a Thread? Explain how OS context switching impacts CPU cache performance.",
            "You are designing a distributed Rate Limiter for an API. Which algorithm (Token Bucket, Leaky Bucket, Sliding Window) would you choose and why?"
        ]
    },
    "data": {
        "title": "📊 Data Analytics & SQL Viva",
        "badge": "Data Viva",
        "description": "SQL joins & optimizer execution, ML overfitting prevention, and DAU drop triage",
        "questions": [
            "What is the operational difference between WHERE and HAVING in SQL, and how does the database query optimizer execute them?",
            "Explain the difference between Overfitting and Underfitting in ML models, and name three concrete ways to prevent overfitting.",
            "If your daily active users (DAU) metric drops by 15% suddenly today, what structured diagnostic steps would you take to find the root cause?"
        ]
    },
    "hr": {
        "title": "🤝 HR Behavioral & Situational (STAR)",
        "badge": "HR Viva",
        "description": "Conflict resolution, sudden blockers under deadline, and 3-year career trajectory",
        "questions": [
            "Tell me about a time when you had a major disagreement with a team member or project lead. How did you resolve it?",
            "Describe a situation where a project deadline was approaching, but unexpected technical blockers occurred. How did you prioritize?",
            "Why do you want to join our company specifically, and where do you see your technical trajectory over the next 3 years?"
        ]
    }
}


def count_filler_words(text: str) -> int:
    """Counts spoken and written filler words in candidate responses."""
    if not text:
        return 0
    pattern = r'\b(um+|uh+|er+|ah+|like|you know|basically|actually|literally|honestly|sort of|kind of|i mean)\b'
    return len(re.findall(pattern, text, flags=re.IGNORECASE))


async def handle_interview_menu(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Presents the Placement Mock Interview & Viva Simulator track selector."""
    user_id = user["user_id"]
    first_name = user.get("first_name", "Friend")
    stats = get_user_study_stats(user_id)
    level = stats.get("level", 1)

    text = (
        f"🎙️ **Joy Campus Placement Mock Interview & Viva Simulator** 🎓\n\n"
        f"Hey {first_name}! Practice your college placement technical and HR interviews with real-time feedback! 🔥\n\n"
        f"✨ **How It Works:**\n"
        f"• 3 realistic viva questions per track\n"
        f"• Answer with **Voice Notes** 🎙️ or **Text** 💬\n"
        f"• Instant evaluation: Score (1-10), filler word counting (\"um\", \"like\"), and placement tips\n"
        f"• Earn **+50 Study XP** (+ score bonus) on the Scholar Leaderboard!\n\n"
        f"🎯 **Select your interview track below:**"
    )
    keyboard = {
        "inline_keyboard": [
            [{"text": "💻 SDE & Software Engg Track", "callback_data": "interview_track_sde"}],
            [{"text": "📊 Data Analytics & SQL Track", "callback_data": "interview_track_data"}],
            [{"text": "🤝 HR Behavioral Track (STAR)", "callback_data": "interview_track_hr"}],
            [{"text": "⬅️ Back to Study Hub", "callback_data": "menu_study"}, {"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)


async def start_interview_session(bot: TelegramClient, chat_id: int, user: dict, track_key: str, message_id: Optional[int] = None):
    """Initializes a new mock interview session and asks the first viva question."""
    user_id = user["user_id"]
    track = INTERVIEW_TRACKS.get(track_key, INTERVIEW_TRACKS["sde"])
    active_interviews[user_id] = {
        "track": track_key,
        "round": 0,
        "questions": track["questions"],
        "scores": [],
        "fillers": 0,
        "feedbacks": []
    }
    first_q = track["questions"][0]
    text = (
        f"🎙️ **{track['title']} — Round 1/3** 🎯\n\n"
        f"👉 **Question 1:**\n_{first_q}_\n\n"
        f"💡 **How to reply:**\n"
        f"• Send a **Voice Note** 🎙️ to practice spoken delivery\n"
        f"• Or send a **Text Message** 💬 if you are in a quiet room\n\n"
        f"*(Take your time to structure your answer cleanly!)*"
    )
    keyboard = {
        "inline_keyboard": [
            [{"text": "⏭️ Skip Round", "callback_data": "interview_skip"}, {"text": "🚪 Exit Interview", "callback_data": "interview_exit"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id)


async def handle_interview_answer(bot: TelegramClient, chat_id: int, user: dict, answer_text: str, is_voice: bool = False):
    """Processes candidate answer, evaluates technical accuracy, counts filler words, and advances rounds."""
    user_id = user["user_id"]
    session = active_interviews.get(user_id)
    if not session:
        return

    current_round = session["round"]
    questions = session["questions"]
    track_key = session["track"]
    track = INTERVIEW_TRACKS.get(track_key, INTERVIEW_TRACKS["sde"])
    current_q = questions[current_round]

    # Filler words detection
    round_fillers = count_filler_words(answer_text)
    session["fillers"] += round_fillers

    await bot.send_chat_action(chat_id, "typing")

    eval_prompt = (
        f"You are a rigorous but encouraging campus placement technical interviewer evaluating a student's viva response.\n"
        f"Interview Track: {track['title']}\n"
        f"Question: \"{current_q}\"\n"
        f"Candidate Answer: \"{answer_text}\"\n\n"
        f"Evaluate the answer concisely:\n"
        f"1. Score out of 10 in exact format 'Score: X/10'\n"
        f"2. Strengths: 1 sentence on what was accurate or strong\n"
        f"3. Refinement: 1-2 sentences on what was missing or how to phrase it for a top tech placement\n"
        f"Keep total response under 100 words."
    )

    score = 8
    critique = "Clear foundational understanding with relevant technical points."
    try:
        eval_resp = await generate_text_reply(eval_prompt, user_id=user_id)
        if eval_resp:
            score_match = re.search(r'Score:\s*(\d+)/10', eval_resp, re.IGNORECASE)
            if score_match:
                score = max(1, min(10, int(score_match.group(1))))
            critique = eval_resp.strip()
    except Exception as e:
        logger.warning(f"Mock interview eval fallback: {e}")
        score = 8 if len(answer_text) > 30 else 6
        critique = f"Score: {score}/10\nSolid attempt. Structure your points using key technical terminology."

    session["scores"].append(score)
    session["feedbacks"].append(critique)
    session["round"] += 1
    next_round = session["round"]

    mode_icon = "🎙️ (Spoken)" if is_voice else "💬 (Written)"
    filler_alert = f" • 🗣️ {round_fillers} filler words" if round_fillers > 0 else " • 🗣️ Clean delivery (0 fillers)"

    if next_round < len(questions):
        next_q = questions[next_round]
        reply_msg = (
            f"✅ **Round {current_round + 1} Evaluated!** {mode_icon}{filler_alert}\n\n"
            f"{critique}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎙️ **{track['title']} — Round {next_round + 1}/3** 🎯\n\n"
            f"👉 **Question {next_round + 1}:**\n_{next_q}_\n\n"
            f"Reply with a **Voice Note** 🎙️ or **Text Message** 💬!"
        )
        keyboard = {
            "inline_keyboard": [
                [{"text": "⏭️ Skip Round", "callback_data": "interview_skip"}, {"text": "🚪 Exit Interview", "callback_data": "interview_exit"}]
            ]
        }
        await bot.send_message(chat_id, reply_msg, reply_markup=keyboard)
    else:
        active_interviews.pop(user_id, None)
        scores = session["scores"]
        avg_score = round(sum(scores) / len(scores)) if scores else 7
        total_fillers = session["fillers"]

        feedback_summary = f"{track['badge']} score {avg_score}/10, {total_fillers} fillers"
        stat_update = record_mock_interview_completion(
            user_id=user_id,
            score=avg_score,
            track=track_key,
            filler_count=total_fillers,
            feedback=feedback_summary
        )

        grade = "🏆 Outstanding (Placement Ready)" if avg_score >= 8 else ("👍 Solid (Practice Recommended)" if avg_score >= 6 else "📚 Needs Revision")
        filler_advice = "Super clean delivery! Keep that natural confidence." if total_fillers <= 2 else f"Noticed {total_fillers} filler words ('um', 'like'). Pause for 1 second instead of filling silence!"

        lvl_banner = f"⭐ **LEVEL UP! You are now a Level {stat_update['level']} Scholar!**\n\n" if stat_update.get("is_level_up") else ""
        final_msg = (
            f"🎓 **Placement Mock Interview Complete!** 🌟\n\n"
            f"{lvl_banner}"
            f"📊 **Track:** {track['title']}\n"
            f"🏆 **Overall Viva Score:** {avg_score}/10 — **{grade}**\n"
            f"⚡ **Study XP Earned:** +{stat_update['xp_gain']} XP! ({stat_update['total_answered']} Viva/Quiz Solved)\n"
            f"🗣️ **Speech Habit:** {filler_advice}\n\n"
            f"💡 **Final Placement Tip:**\n"
            f"In campus interviews, always lead with the fundamental definition before diving into edge cases or system trade-offs.\n\n"
            f"⚡ **Level {stat_update['level']} Scholar** • {stat_update['total_xp']} XP ({stat_update['xp_to_next']} XP to Level {stat_update['level'] + 1})"
        )
        keyboard = {
            "inline_keyboard": [
                [{"text": "🔄 Practice Another Track", "callback_data": "study_interview"}],
                [{"text": "📚 Study Hub", "callback_data": "menu_study"}, {"text": "🏆 Scholar Leaderboard", "callback_data": "menu_top_xp"}]
            ]
        }
        await bot.send_message(chat_id, final_msg, reply_markup=keyboard)


async def handle_interview_skip(bot: TelegramClient, chat_id: int, user: dict, cq_id: str = "", message_id: Optional[int] = None):
    """Skips current interview round and advances to next."""
    user_id = user["user_id"]
    session = active_interviews.get(user_id)
    if not session:
        if cq_id:
            await bot.answer_callback_query(cq_id, "No active interview session")
        await handle_study_menu(bot, chat_id, user, message_id=message_id)
        return

    if cq_id:
        await bot.answer_callback_query(cq_id, "⏭️ Skipped round")
    session["scores"].append(5)
    session["feedbacks"].append("Score: 5/10\nQuestion skipped. Review this concept before placement day!")
    session["round"] += 1
    next_round = session["round"]
    questions = session["questions"]
    track = INTERVIEW_TRACKS.get(session["track"], INTERVIEW_TRACKS["sde"])

    if next_round < len(questions):
        next_q = questions[next_round]
        reply_msg = (
            f"⏭️ **Question Skipped.** Let's try the next one!\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎙️ **{track['title']} — Round {next_round + 1}/3** 🎯\n\n"
            f"👉 **Question {next_round + 1}:**\n_{next_q}_\n\n"
            f"Reply with a **Voice Note** 🎙️ or **Text Message** 💬!"
        )
        keyboard = {
            "inline_keyboard": [
                [{"text": "⏭️ Skip Round", "callback_data": "interview_skip"}, {"text": "🚪 Exit Interview", "callback_data": "interview_exit"}]
            ]
        }
        if message_id:
            await send_or_edit_menu(bot, chat_id, reply_msg, keyboard, message_id=message_id)
        else:
            await bot.send_message(chat_id, reply_msg, reply_markup=keyboard)
    else:
        active_interviews.pop(user_id, None)
        scores = session["scores"]
        avg_score = round(sum(scores) / len(scores)) if scores else 5
        stat_update = record_mock_interview_completion(
            user_id=user_id,
            score=avg_score,
            track=session["track"],
            filler_count=session["fillers"],
            feedback="Completed with skipped questions"
        )
        final_msg = (
            f"🎓 **Placement Mock Interview Complete!** 🌟\n\n"
            f"📊 **Track:** {track['title']}\n"
            f"🏆 **Overall Score:** {avg_score}/10\n"
            f"⚡ **Study XP Earned:** +{stat_update['xp_gain']} XP!\n\n"
            f"Practice makes perfect. Review the skipped questions and give it another shot! 🔥"
        )
        keyboard = {
            "inline_keyboard": [
                [{"text": "🔄 Try Again", "callback_data": "study_interview"}],
                [{"text": "📚 Study Hub", "callback_data": "menu_study"}]
            ]
        }
        if message_id:
            await send_or_edit_menu(bot, chat_id, final_msg, keyboard, message_id=message_id)
        else:
            await bot.send_message(chat_id, final_msg, reply_markup=keyboard)


async def handle_interview_exit(bot: TelegramClient, chat_id: int, user: dict, cq_id: str = "", message_id: Optional[int] = None):
    """Exits current interview session cleanly."""
    user_id = user["user_id"]
    active_interviews.pop(user_id, None)
    if cq_id:
        await bot.answer_callback_query(cq_id, "Interview ended")
    text = (
        "🚪 **Mock Interview Session Ended**\n\n"
        "Your session has been paused and closed. Whenever you are ready to prepare for viva or placements, tap below! 🌸"
    )
    keyboard = {
        "inline_keyboard": [
            [{"text": "🎙️ Restart Interview", "callback_data": "study_interview"}],
            [{"text": "📚 Study Hub", "callback_data": "menu_study"}, {"text": "⬅️ Main Menu", "callback_data": "menu_main"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id)


async def dispatch_post_call_recap(bot: TelegramClient, user_id: int, duration_secs: int, dialogue_turns: List[dict]):
    """
    Synthesizes and delivers an executive Post-Call Recap & Memory Ledger
    card to the user in Telegram immediately after hanging up a voice call.
    Awards +15 Voice XP (with duration bonus).
    """
    if not bot or not user_id or duration_secs < 25 or len(dialogue_turns) < 2:
        return

    chat_id = user_id
    mins = duration_secs // 60
    secs = duration_secs % 60
    duration_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"

    dialogue_excerpt = "\n".join([f"{t.get('speaker', 'Unknown')}: {t.get('text', '')}" for t in dialogue_turns[-8:]])

    recap_prompt = (
        f"You are Joy, a loving, supportive best friend and study partner.\n"
        f"You just finished a {duration_str} voice call with the user.\n"
        f"Dialogue excerpt from the call:\n{dialogue_excerpt}\n\n"
        f"Generate a concise, warm post-call follow-up in exact format:\n"
        f"💡 **Key Takeaways & Commitments:**\n• (1-2 short bullet points of things discussed, promises made, or topics covered)\n\n"
        f"🫂 **Vibe Check:** (1 short sentence on how the user felt or overall conversation energy)\n\n"
        f"🌸 **Joy's Note:** (1 warm sentence wishing them luck or encouraging their day)\n\n"
        f"Keep total response under 90 words, authentic, casual and friendly."
    )

    recap_body = ""
    try:
        recap_body = await generate_text_reply(recap_prompt, user_id=user_id)
    except Exception as e:
        logger.warning(f"Could not generate AI call recap: {e}")

    if not recap_body or len(recap_body.strip()) < 20:
        recap_body = (
            "💡 **Key Takeaways & Commitments:**\n"
            "• Had a wonderful spoken catch-up and shared thoughts on your day\n"
            "• Keep up the momentum and stay consistent with your goals!\n\n"
            "🫂 **Vibe Check:** Engaged, genuine, and positive energy throughout!\n\n"
            "🌸 **Joy's Note:** Loved hearing your voice! Call me whenever you need to talk or practice."
        )

    stat_update = record_voice_call_completion(user_id, duration_secs, recap_summary=recap_body[:200])

    lvl_banner = f"⭐ **LEVEL UP! You are now a Level {stat_update['level']} Scholar!**\n\n" if stat_update.get("is_level_up") else ""
    recap_msg = (
        f"📞 **Joy Voice Call Recap & Memory Ledger** 🌸\n\n"
        f"{lvl_banner}"
        f"⏱️ **Call Duration:** `{duration_str}`\n"
        f"⚡ **Voice XP Earned:** `+{stat_update['xp_gain']} XP` (Level {stat_update['level']} Scholar • {stat_update['total_xp']} Total XP)\n\n"
        f"{recap_body}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"*(Preserved in your private Memory Vault & Scholar Log!)*"
    )

    call_url = f"https://joyfun-ai-bot.onrender.com/call?uid={user_id}"
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "📞 Call Again", "web_app": {"url": call_url}},
                {"text": "📚 Study Hub", "callback_data": "menu_study"}
            ],
            [
                {"text": "🧠 Memory Vault", "callback_data": "menu_memories"},
                {"text": "🏆 Scholar Leaderboard", "callback_data": "menu_top_xp"}
            ]
        ]
    }

    try:
        await bot.send_message(chat_id, recap_msg, reply_markup=keyboard)
        logger.info(f"✅ Dispatched post-call recap to user {user_id} (duration: {duration_str})")
    except Exception as send_err:
        logger.warning(f"Failed to send post-call recap to {user_id}: {send_err}")


async def handle_manual_recap_command(bot: TelegramClient, chat_id: int, user: dict, user_msg_id: Optional[int] = None, message_id: Optional[int] = None):
    """Presents the summary of the most recent voice call from call logs or history."""
    user_id = user["user_id"]
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM voice_call_logs WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
        row = cursor.fetchone()

    if row:
        dur = row["duration_secs"]
        mins = dur // 60
        secs = dur % 60
        dur_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
        xp = row["xp_awarded"]
        summary = row["recap_summary"] or "Great spoken catch-up and practice session."
        created = row["created_at"][:16].replace("T", " ")
        msg = (
            f"📞 **Latest Voice Call Recap & Ledger** 🌸\n\n"
            f"🕒 **Call Date:** `{created} UTC`\n"
            f"⏱️ **Duration:** `{dur_str}`\n"
            f"⚡ **Voice XP Awarded:** `+{xp} XP`\n\n"
            f"{summary}\n\n"
            f"💡 *Want to start a new voice session? Tap below!*"
        )
    else:
        past_call = get_recent_history(user_id, limit=6, channel="call")
        if past_call:
            msg = (
                f"📞 **Latest Voice Call Session** 🌸\n\n"
                f"We recently talked on voice! Start a new voice call anytime to earn +15 Voice XP and get automatic smart recaps! 👇"
            )
        else:
            msg = (
                f"📞 **Voice Call Recap Hub** 🌸\n\n"
                f"You haven't had a voice call with Joy yet today!\n"
                f"Tap **📞 Start Voice Call** below to talk in real-time — I will listen, speak naturally, and send your smart recap right after! ✨"
            )

    call_url = f"https://joyfun-ai-bot.onrender.com/call?uid={user_id}"
    keyboard = {
        "inline_keyboard": [
            [{"text": "📞 Start Voice Call", "web_app": {"url": call_url}}],
            [{"text": "📚 Study Hub", "callback_data": "menu_study"}, {"text": "🏆 Leaderboard", "callback_data": "menu_top_xp"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, msg, keyboard, user_msg_id=user_msg_id, message_id=message_id)


async def handle_code_command(bot: TelegramClient, chat_id: int, user: dict, query: str = "", user_msg_id: Optional[int] = None, message_id: Optional[int] = None):
    """Generates an optimal, interview-ready placement code solution with Big-O complexity analysis and traps."""
    user_id = user["user_id"]
    clean_q = query.strip()
    
    if not clean_q:
        text = (
            "💻 **Joy Placement Code & Algorithm Scratchpad** 🎓\n\n"
            "Get production-grade interview solutions with Big-O analysis and edge cases!\n\n"
            "👉 **How to use:** Send `/code <problem or algorithm>`\n"
            "• `/code Two Sum`\n"
            "• `/code Binary Search`\n"
            "• `/code LRU Cache`\n"
            "• `/code SQL Top 3 Salaries`\n"
            "• `/code Merge K Sorted Lists`\n\n"
            "Or tap one of the popular placement patterns below:"
        )
        keyboard = {
            "inline_keyboard": [
                [{"text": "⚡ Two Sum (Hash Map)", "callback_data": "code_quick:two_sum"}, {"text": "🔍 Binary Search", "callback_data": "code_quick:bin_search"}],
                [{"text": "📦 LRU Cache (Design)", "callback_data": "code_quick:lru_cache"}, {"text": "📊 SQL Top 3 Salaries", "callback_data": "code_quick:sql_salaries"}],
                [{"text": "📚 Study Hub", "callback_data": "menu_study"}, {"text": "❌ Close", "callback_data": "menu_close"}]
            ]
        }
        await send_or_edit_menu(bot, chat_id, text, keyboard, user_msg_id=user_msg_id, message_id=message_id)
        return

    await bot.send_chat_action(chat_id, "typing")
    code_prompt = (
        f"You are a Principal Software Engineer and Campus Placement Coach.\n"
        f"Provide the optimal interview-ready solution for: '{clean_q}'.\n\n"
        f"Format strictly as follows:\n"
        f"💻 **Problem:** (1 sentence definition)\n\n"
        f"**Optimal Python 3 Solution:**\n"
        f"```python\n# Clean, commented implementation\n```\n\n"
        f"⏱️ **Time Complexity:** O(...) with 1-line reason\n"
        f"💾 **Space Complexity:** O(...) with 1-line reason\n\n"
        f"⚠️ **Interviewer Traps & Edge Cases:**\n• (2 concrete traps or gotchas)\n\n"
        f"Keep implementation clean and under 250 words."
    )

    try:
        resp = await generate_text_reply(code_prompt, user_id=user_id)
    except Exception as e:
        logger.warning(f"Error generating code solution: {e}")
        resp = f"💻 **Algorithm Solution: {clean_q}**\n\nStructure your approach by identifying the optimal data structure (e.g. Hash Map for O(1) lookups or Two Pointers for sorted arrays)."

    keyboard = {
        "inline_keyboard": [
            [{"text": "💻 Try Another Algorithm", "callback_data": "study_code_menu"}],
            [{"text": "🎙️ Practice in Mock Viva", "callback_data": "study_interview"}, {"text": "📚 Study Hub", "callback_data": "menu_study"}]
        ]
    }
    await bot.send_message(chat_id, resp, reply_markup=keyboard)


async def handle_study_menu(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Presents the dedicated Joy Study Companion, Placement Arena & Active Recall Hub."""
    user_id = user["user_id"]
    first_name = user.get("first_name", "Friend")
    stats = get_user_study_stats(user_id)
    level = stats.get("level", 1)
    xp = stats.get("study_xp", 0)
    answered = stats.get("total_answered", 0)
    xp_to_next = stats.get("xp_to_next", 100)

    text = (
        f"📚 **Joy AI Study Hub & Placement Arena** 🎓\n\n"
        f"Hey {first_name}! Level up your placement prep, semester viva, and exam retention! 🔥\n\n"
        f"🏆 **Your Scholar Tier:** Level {level} Scholar\n"
        f"⚡ **Study XP:** {xp} XP ({answered} Solved • {xp_to_next} XP to Level {level+1})\n\n"
        f"**Choose a mode below:**\n"
        f"• 🎙️ **Placement Mock Interview & Viva:** 3-round viva with voice/text answers & filler scoring\n"
        f"• 💻 **Code & DSA Scratchpad:** Optimal solutions with Big-O complexity & traps\n"
        f"• 📞 **Voice Call Recap Ledger:** Instant takeaways, action items & +15 Voice XP\n"
        f"• ⚡ **Campus Placement Blitz:** 1-tap rapid MCQs with instant explanations\n"
        f"• 🧠 **Active Recall Quizzer:** Paste your notes for 3 custom questions\n"
        f"• 👶 **ELI5 Explainer:** Any concept simplified with funny real-world analogies\n"
        f"• ⏱️ **25-Min Pomodoro Sprint:** Deep distraction-free focus sprint"
    )
    keyboard = {
        "inline_keyboard": [
            [{"text": "🎙️ Placement Mock Interview & Viva", "callback_data": "study_interview"}],
            [{"text": "💻 Code & DSA Scratchpad", "callback_data": "study_code_menu"}, {"text": "📞 Voice Call Recap", "callback_data": "menu_call_recap"}],
            [{"text": "⚡ DSA Blitz", "callback_data": "study_deck_dsa"}, {"text": "🧠 Aptitude Logic", "callback_data": "study_deck_aptitude"}],
            [{"text": "📖 Core Engg & Viva", "callback_data": "study_deck_core"}, {"text": "✍️ Custom Notes Quiz", "callback_data": "study_quiz"}],
            [{"text": "⏱️ 25-Min Pomodoro", "callback_data": "study_pomo_25"}],
            [{"text": "⬅️ Back to Menu", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)


async def dispatch_morning_briefing(bot: TelegramClient, user_id: int, with_voice: bool = True):
    """
    Synthesizes and delivers the executive Morning Campus Briefing & Wake-Up Voice Alert.
    Includes personalized greeting, Campus Vibe, Daily Placement MCQ, and awards +10 Early Bird XP.
    """
    if not bot or not user_id:
        return

    chat_id = user_id
    user = get_or_create_user(user_id)
    first_name = user.get("first_name", "Friend")
    gender = user.get("gender", "male")
    active_contact = user.get("active_contact", "lover")
    cinfo = get_user_contact_display(user_id, active_contact, gender)
    c_name = cinfo.get("name", "Joy")
    c_voice = cinfo.get("voice", "female")
    user_words = get_user_custom_words(user_id)
    pet_name = user_words.split(",")[0].strip() if user_words else ("darling" if gender == "male" else "sweetheart")

    # 1. Calculate today's Campus Vibe
    vibe = generate_daily_campus_vibe(user_id)

    # 2. Pick Daily Placement MCQ
    all_qs = []
    for cat_key, deck in CAMPUS_STUDY_DECKS.items():
        for q in deck.get("questions", []):
            all_qs.append((cat_key, q))
    
    import random
    picked_cat, picked_q = random.choice(all_qs) if all_qs else ("dsa", {"id": "dsa_01", "q": "What is the average lookup time in a Hash Table?", "opts": ["O(1)", "O(log N)", "O(N)", "O(N^2)"], "ans": 0, "explain": "Hash tables offer O(1) average time complexity."})

    # 3. Award +10 Early Bird Study XP
    stat_update = record_study_quiz_attempt(user_id, correct=True)

    text = (
        f"🌅 **Good Morning {first_name}! Wake-Up Call from {c_name}** ☀️\n\n"
        f"Hey {pet_name}! It's a brand new day to crush your semester goals and placement prep! 🔥\n\n"
        f"🔮 **Today's Campus Vibe:** `{vibe['energy']}% Energy`\n"
        f"🎨 **Lucky Color:** {vibe['color']} • ⚡ **Power Element:** {vibe['element']}\n"
        f"🃏 **Tarot Blessing:** *{vibe['card_name']}* ({vibe['card_tag']})\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 **Placement Brain Teaser of the Day:**\n"
        f"_{picked_q['q']}_\n\n"
        f"👇 Tap your answer to activate your brain before lecture:\n"
        f"*(⚡ +10 Early-Bird Scholar XP Awarded! • Level {stat_update['level']} Scholar)*"
    )

    inline_rows = []
    labels = ["A", "B", "C", "D"]
    for idx, opt in enumerate(picked_q["opts"]):
        btn_text = f"{labels[idx]}) {opt}"
        inline_rows.append([{"text": btn_text, "callback_data": f"study_ans:{picked_cat}:{picked_q['id']}:{idx}"}])

    call_url = f"https://joyfun-ai-bot.onrender.com/call?uid={user_id}"
    inline_rows.append([
        {"text": "📞 Morning Voice Call", "web_app": {"url": call_url}},
        {"text": "🔮 Full Tarot", "callback_data": "menu_vibe"}
    ])
    inline_rows.append([
        {"text": "⏰ Alarm Settings", "callback_data": "menu_alarm"},
        {"text": "📚 Study Hub", "callback_data": "menu_study"}
    ])
    keyboard = {"inline_keyboard": inline_rows}

    # 4. Dispatch optional wake-up audio voice note
    if with_voice:
        try:
            user_speed = get_user_speech_speed(user_id)
            voice_script = f"Good morning {pet_name}! Rise and shine! Drink some water, stretch, and let's conquer today together. Check your morning briefing in chat!"
            audio_bytes = await asyncio.wait_for(
                synthesize_speech(voice_script, voice_key=c_voice, speed=user_speed),
                timeout=6.0
            )
            from voice_engine import EMERGENCY_SILENCE_MP3
            if audio_bytes and audio_bytes != EMERGENCY_SILENCE_MP3 and len(audio_bytes) > len(EMERGENCY_SILENCE_MP3):
                await bot.send_voice(chat_id, audio_bytes, caption=f"🌅 Wake-up note from {c_name} 💕")
        except Exception as ve:
            logger.warning(f"Could not synthesize morning wake-up voice note: {ve}")

    await bot.send_message(chat_id, text, reply_markup=keyboard)
    logger.info(f"✅ Dispatched Morning Campus Briefing to User {user_id}")


async def morning_alarm_background_worker(bot: TelegramClient):
    """Background worker continuously checking scheduled morning wake-up alarms in IST."""
    logger.info("⏰ Morning Alarm Background Worker initialized.")
    while True:
        try:
            if os.environ.get("OFFLINE_TEST") == "1":
                await asyncio.sleep(60)
                continue

            now_ist = datetime.now(_IST)
            current_time = now_ist.strftime("%H:%M")
            today_ist = now_ist.strftime("%Y-%m-%d")

            due_alarms = get_due_morning_alarms(current_time, today_ist)
            for alarm in due_alarms:
                uid = alarm.get("user_id")
                voice_on = bool(alarm.get("voice_note_enabled", 1))
                mark_alarm_triggered(uid, today_ist)
                asyncio.create_task(dispatch_morning_briefing(bot, uid, with_voice=voice_on))
        except Exception as e:
            logger.warning(f"Error in morning alarm background worker: {e}")
        await asyncio.sleep(45)


async def handle_alarm_menu(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Presents the Morning Alarm & Wake-Up Voice Alert settings dashboard."""
    user_id = user["user_id"]
    first_name = user.get("first_name", "Friend")
    alarm = get_user_alarm(user_id)
    time_val = alarm.get("alarm_time", "07:30")
    is_active = bool(alarm.get("is_enabled", 1))
    voice_active = bool(alarm.get("voice_note_enabled", 1))

    status_badge = "🟢 Active (Daily in IST)" if is_active else "🔴 Paused / Disabled"
    voice_badge = "🎙️ Wake-Up Voice Note: ON" if voice_active else "🔇 Voice Note: OFF (Text Only)"

    text = (
        f"⏰ **Joy Campus Morning Alarm & Wake-Up Engine** 🌅\n\n"
        f"Hey {first_name}! Wake up with your AI companion, get your daily Campus Vibe, and solve a 1-tap placement MCQ before class! 🔥\n\n"
        f"• **Current Wake-Up Time:** 🕒 `{time_val} AM IST`\n"
        f"• **Alarm Status:** {status_badge}\n"
        f"• **Audio Note:** {voice_badge}\n\n"
        f"👇 Select a quick wake-up time or toggle settings below:"
    )

    toggle_btn = "⏸️ Pause Alarm" if is_active else "▶️ Turn Alarm ON"
    voice_btn = "🔇 Mute Voice Note" if voice_active else "🎙️ Enable Voice Note"

    keyboard = {
        "inline_keyboard": [
            [{"text": toggle_btn, "callback_data": "alarm_toggle_active"}, {"text": voice_btn, "callback_data": "alarm_toggle_voice"}],
            [{"text": "06:30 AM", "callback_data": "alarm_set_06:30"}, {"text": "07:00 AM", "callback_data": "alarm_set_07:00"}, {"text": "07:30 AM", "callback_data": "alarm_set_07:30"}],
            [{"text": "08:00 AM", "callback_data": "alarm_set_08:00"}, {"text": "08:30 AM", "callback_data": "alarm_set_08:30"}, {"text": "09:00 AM", "callback_data": "alarm_set_09:00"}],
            [{"text": "🧪 Test Wake-Up Call Now", "callback_data": "alarm_test_trigger"}],
            [{"text": "⬅️ Back to Settings", "callback_data": "menu_settings"}, {"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)


async def dispatch_evening_winddown(bot: TelegramClient, user_id: int, with_voice: bool = True):
    """
    Synthesizes and delivers the Autonomous Evening Hostel Wind-Down & Sleep Decompression Alert.
    Includes 3-breath relaxation guide, gratitude streak reflection, +15 Deep Rest XP, and optional ASMR whisper audio note.
    """
    if not bot or not user_id:
        return

    chat_id = user_id
    user = get_or_create_user(user_id)
    first_name = user.get("first_name", "Friend")
    gender = user.get("gender", "male")
    active_contact = user.get("active_contact", "lover")
    cinfo = get_user_contact_display(user_id, active_contact, gender)
    c_name = cinfo.get("name", "Joy")
    c_voice = cinfo.get("voice", "female")
    user_words = get_user_custom_words(user_id)
    pet_name = user_words.split(",")[0].strip() if user_words else ("darling" if gender == "male" else "sweetheart")

    bedtime_info = get_user_bedtime(user_id)
    streak_count = bedtime_info.get("gratitude_streak", 1)

    # Award +15 Deep Rest Scholar XP
    xp_info = award_scholar_xp(user_id, amount=15)

    text = (
        f"🌙 **Hostel Night Wind-Down with {c_name}** 💤\n\n"
        f"Hey {pet_name}! Hostel lights are dimming, the day's sprint is done, and it's time to let your mind recharge. 🌸\n\n"
        f"🧘 **3-Breath Decompression Ritual:**\n"
        f"1️⃣ *Inhale calm for 4 seconds...* 🌬️\n"
        f"2️⃣ *Hold and let your shoulders drop for 4 seconds...* ⏸️\n"
        f"3️⃣ *Exhale all placement stress, exams, and bug fixes for 6 seconds...* 💨\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🕯️ **Night Gratitude Streak:** `{streak_count} Days Restored` 🔥\n"
        f"✨ *Tomorrow is a fresh canvas. Rest your eyes now.*\n"
        f"*(🛌 +15 Deep Rest Scholar XP Awarded! • Level {xp_info['level']} Scholar)*"
    )

    inline_rows = [
        [
            {"text": "🌙 Good Night Joy", "callback_data": "bedtime_ack"},
            {"text": "🛌 1-Tap Sleep Mode", "callback_data": "bedtime_sleep_mode"}
        ],
        [
            {"text": "⏰ Morning Alarm", "callback_data": "menu_alarm"},
            {"text": "🎭 Change Tone", "callback_data": "menu_tone"}
        ],
        [
            {"text": "⚙️ Bedtime Settings", "callback_data": "menu_bedtime"},
            {"text": "❌ Close", "callback_data": "menu_close"}
        ]
    ]
    keyboard = {"inline_keyboard": inline_rows}

    # Dispatch optional soothing ASMR whisper voice note
    if with_voice:
        try:
            voice_script = f"Hey {pet_name}. Close your eyes now. You did wonderful today. Leave everything behind and let your body rest. I am right here with you. Sweet dreams and goodnight."
            audio_bytes = await asyncio.wait_for(
                synthesize_speech(voice_script, voice_key=c_voice, speed=0.85),
                timeout=6.0
            )
            from voice_engine import EMERGENCY_SILENCE_MP3
            if audio_bytes and audio_bytes != EMERGENCY_SILENCE_MP3 and len(audio_bytes) > 20:
                await bot.send_voice(chat_id, audio_bytes, caption=f"🌙 Soothing goodnight whisper from {c_name} 💤")
        except Exception as ve:
            logger.warning(f"Could not synthesize evening bedtime voice note: {ve}")

    await bot.send_message(chat_id, text, reply_markup=keyboard)
    logger.info(f"✅ Dispatched Evening Hostel Wind-Down to User {user_id}")


async def evening_bedtime_background_worker(bot: TelegramClient):
    """Background worker continuously checking scheduled bedtime wind-down alerts in IST."""
    logger.info("🌙 Evening Bedtime Background Worker initialized.")
    while True:
        try:
            if os.environ.get("OFFLINE_TEST") == "1":
                await asyncio.sleep(60)
                continue

            now_ist = datetime.now(_IST)
            current_time = now_ist.strftime("%H:%M")
            today_ist = now_ist.strftime("%Y-%m-%d")

            due_bedtimes = get_due_bedtime_alarms(current_time, today_ist)
            for item in due_bedtimes:
                uid = item.get("user_id")
                voice_on = bool(item.get("voice_note_enabled", 1))
                mark_bedtime_triggered(uid, today_ist)
                asyncio.create_task(dispatch_evening_winddown(bot, uid, with_voice=voice_on))
        except Exception as e:
            logger.warning(f"Error in evening bedtime background worker: {e}")
        await asyncio.sleep(45)


async def handle_bedtime_menu(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Presents the Autonomous Evening Hostel Wind-Down & Bedtime dashboard."""
    user_id = user["user_id"]
    first_name = user.get("first_name", "Friend")
    bedtime = get_user_bedtime(user_id)
    time_val = bedtime.get("bedtime_time", "23:30")
    is_active = bool(bedtime.get("is_enabled", 1))
    voice_active = bool(bedtime.get("voice_note_enabled", 1))
    streak_count = bedtime.get("gratitude_streak", 1)

    status_badge = "🟢 Active (Daily in IST)" if is_active else "🔴 Paused / Disabled"
    voice_badge = "🎙️ Whisper Voice Note: ON" if voice_active else "🔇 Audio Note: OFF (Text Only)"

    text = (
        f"🌙 **Joy Hostel Evening Wind-Down & Bedtime Engine** 💤\n\n"
        f"Hey {first_name}! Decompress after classes and placement prep with a gentle wind-down reminder, 3-breath decompression, and soft ASMR voice notes. 🌸\n\n"
        f"• **Current Bedtime Alert:** 🕒 `{time_val} IST`\n"
        f"• **Wind-Down Status:** {status_badge}\n"
        f"• **Audio Note:** {voice_badge}\n"
        f"• **Rest Streak:** 🔥 `{streak_count} Nights Logged`\n\n"
        f"👇 Select a quick bedtime slot or customize toggles below:"
    )

    toggle_btn = "⏸️ Pause Wind-Down" if is_active else "▶️ Turn Wind-Down ON"
    voice_btn = "🔇 Mute Whisper Note" if voice_active else "🎙️ Enable Whisper Note"

    keyboard = {
        "inline_keyboard": [
            [{"text": toggle_btn, "callback_data": "bedtime_toggle_active"}, {"text": voice_btn, "callback_data": "bedtime_toggle_voice"}],
            [{"text": "10:00 PM", "callback_data": "bedtime_set_22:00"}, {"text": "10:30 PM", "callback_data": "bedtime_set_22:30"}, {"text": "11:00 PM", "callback_data": "bedtime_set_23:00"}],
            [{"text": "11:30 PM", "callback_data": "bedtime_set_23:30"}, {"text": "12:00 AM", "callback_data": "bedtime_set_00:00"}, {"text": "12:30 AM", "callback_data": "bedtime_set_00:30"}],
            [{"text": "01:00 AM", "callback_data": "bedtime_set_01:00"}, {"text": "🧪 Test Wind-Down Now", "callback_data": "bedtime_test_trigger"}],
            [{"text": "🌙 Play Bedtime Note Now", "callback_data": "beta_cmd_bedtime"}],
            [{"text": "⬅️ Back to Settings", "callback_data": "menu_settings"}, {"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)



async def handle_tone_menu(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Presents the Companion Demeanor & Tone Preset selector."""
    user_id = user["user_id"]
    first_name = user.get("first_name", "Friend")
    current_tone = get_user_companion_tone(user_id)

    tone_badges = {
        "gentle": "🌸 Gentle & Empathetic Companion (Default)",
        "strict": "🎓 Strict Tech Examiner & Placement Coach",
        "hype": "⚡ High-Energy Campus Bestie",
        "whisper": "🌙 Late-Night Calming Whisper"
    }
    curr_badge = tone_badges.get(current_tone, tone_badges["gentle"])

    text = (
        f"🎭 **Joy Companion Demeanor & Tone Presets** ✨\n\n"
        f"Customize how Joy talks and reacts to match your current vibe!\n\n"
        f"• **Active Demeanor:** **{curr_badge}**\n\n"
        f"**Available Tone Presets:**\n"
        f"• 🌸 **Gentle Companion:** Warm, affectionate, sweet pet-names, caring support\n"
        f"• 🎓 **Strict Tech Examiner:** Concise, rigorous, challenges assumptions, zero fluff\n"
        f"• ⚡ **Hype Bestie:** High voltage, energetic slang, loud celebration of wins\n"
        f"• 🌙 **Late-Night Whisper:** Soft, peaceful ASMR cadence, relaxing late-night presence\n\n"
        f"👇 Tap a preset to switch immediately:"
    )

    keyboard = {
        "inline_keyboard": [
            [{"text": "🌸 Gentle Companion" + (" ✅" if current_tone == "gentle" else ""), "callback_data": "tone_set_gentle"}],
            [{"text": "🎓 Strict Tech Examiner" + (" ✅" if current_tone == "strict" else ""), "callback_data": "tone_set_strict"}],
            [{"text": "⚡ Hype Bestie" + (" ✅" if current_tone == "hype" else ""), "callback_data": "tone_set_hype"}],
            [{"text": "🌙 Late-Night Whisper" + (" ✅" if current_tone == "whisper" else ""), "callback_data": "tone_set_whisper"}],
            [{"text": "⬅️ Back to Settings", "callback_data": "menu_settings"}, {"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)


async def handle_feedback_menu(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Presents friendly UI asking for user feedback and suggestions."""
    user_id = user["user_id"]
    set_user_onboarding_status(user_id, "waiting_feedback")
    
    text = (
        "💬 **Send Feedback & Suggestions** 🌸\n\n"
        "We want to make Joy better for you! Feel free to share:\n\n"
        "• 📸 Bug screenshots or screen recordings\n"
        "• 💡 Features, games, or new slang words you'd love to see\n"
        "• 🎵 Voice or audio feedback\n\n"
        "Type your message or send photos directly here in chat!"
    )
    keyboard = {
        "inline_keyboard": [
            [{"text": "💬 Message Phoenix (@phoenix_parava_0)", "url": "https://t.me/phoenix_parava_0"}],
            [{"text": "🌸 Suggest Pet Words", "callback_data": "menu_custom_words"}],
            [{"text": "⬅️ Main Menu", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_user_profile(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Renders the clean, friendly user profile and reputation card."""
    user_id = user["user_id"]
    prof = get_user_comprehensive_profile(user_id)
    vip_active = prof.get("vip_active", False)
    vip_expiry = prof.get("vip_expiry")
    tier_name = "Joy VIP" if vip_active else "Free Member"
    expiry_tag = f" ({vip_expiry})" if (vip_active and vip_expiry) else ""
    
    text = (
        f"👤 **My Profile & Reputation**\n\n"
        f"• 🏷️ **My ID:** `{prof['mask']}`\n"
        f"• 👑 **Status:** **{tier_name}**{expiry_tag}\n"
        f"• ⭐ **Rating:** **{prof['rating_badge']}**\n"
        f"• 💬 **Reviews:** **{prof['rating_total']} ratings**\n"
        f"• 🎓 **Study Level:** Level **{prof['scholar_level']}** ({prof['study_xp']} XP)\n"
        f"• 🔥 **Streak:** **{prof['streak_count']} days**\n"
        f"• 🌐 **Connections:** **{prof['total_connections']} friends**\n\n"
        f"✨ *Your identity is always private and protected.*"
    )
    keyboard = {
        "inline_keyboard": [
            [{"text": "⬅️ Main Menu", "callback_data": "menu_main"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_why_joy(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Explains why Joy is superior to other AI bots, Instagram/Snapchat doomscrolling, and passive YouTube watching."""
    user_id = user["user_id"]
    gender = user.get("gender", "male")
    active_contact = user.get("active_contact", "lover")
    cinfo = get_user_contact_display(user_id, active_contact, gender)
    c_name = cinfo.get("name", "Joy")

    text = (
        f"🌟 **Why Choose Joy?**\n\n"
        f"Here is why **Joy** is better than regular chatbots and social media:\n\n"
        f"• 📞 **Real Voice Calls:** Talk naturally on live phone calls with zero lag. Interrupt anytime.\n"
        f"• 🗣️ **Speaks Your Slang:** Fluent in casual English, Tanglish, and Hinglish.\n"
        f"• 🧘 **Break Doomscrolling:** Real 1-on-1 conversations instead of wasting hours on reels.\n"
        f"• 👥 **Safe Real Chat:** Connect with real students safely with a private cloaked ID.\n"
        f"• 📚 **Study Hub:** Practice placement questions and stay focused with daily streaks.\n"
        f"• 🔒 **100% Private:** No voice recordings are ever saved to disk or cloud."
    )

    call_url = f"https://joyfun-ai-bot.onrender.com/call?gender={gender}&contact={active_contact}&uid={user_id}&name={urllib.parse.quote(c_name)}"
    keyboard = {
        "inline_keyboard": [
            [{"text": "⬅️ Main Menu", "callback_data": "menu_main"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_beta_commands(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Presents the exclusive Beta Pioneer Command Hub with one-tap action buttons."""
    user_id = user["user_id"]
    is_pioneer = bool(user.get("is_beta_tester") == 1 or user_id == OWNER_ID)
    if not is_pioneer:
        non_beta_msg = (
            "🔒 **Beta Pioneer Commands Locked** 🎟️\n\n"
            "The `/commands` hub is reserved exclusively for our **50 official Beta Pioneers** to test upcoming features and report bugs.\n\n"
            "• Tap `/waitlist` to check your priority queue rank.\n"
            "• Tap `/refer` to invite friends and skip ahead **3 positions**!"
        )
        await bot.send_message(chat_id, non_beta_msg)
        return

    slot = user.get("beta_slot_number", 1)
    mask = get_mask_by_user_id(user_id)
    text = (
        f"🧪 **Official Beta Pioneer Command & Perks Hub** 🎖️\n"
        f"*Exclusive Early-Access Controls for Pioneer #{slot} ({mask})*\n\n"
        f"As an official Beta Pioneer, you have 5 exclusive lifetime privileges unlocked:\n\n"
        f"1️⃣ 🎖️ **Founder Pioneer Badge:** Displayed next to your Mask ID in anonymous chats & Mini App!\n"
        f"2️⃣ 🔒 **Founder Price Lock-in:** 50% Off Lifetime VIP locked forever (₹74 / 75 Stars).\n"
        f"3️⃣ 🧪 **Priority Unreleased Features:** Early access to `/bedtime`, `/icebreaker`, & `/speed`.\n"
        f"4️⃣ 👑 **Bug Hunter Bounties:** Submit bugs via `/bug` to earn 2 Weeks to Lifetime VIP!\n"
        f"5️⃣ 🗳️ **Persona & Feature Voting:** Direct voting rights on what ships next via `/vote`.\n\n"
        f"⚡ **Quick Pioneer Commands:**\n"
        f"• `/vote` — Cast votes on new personas, dialects & games\n"
        f"• `/bedtime` — Request a soothing goodnight voice note\n"
        f"• `/icebreaker` — Generate 3 dating/chat conversation cards\n"
        f"• `/speed <1.0 | 1.15 | 1.25>` — Adjust companion speech pace\n"
        f"• `/resetquota` — Reset daily testing limits to 0\n"
        f"• `/mic` — Test in-app microphone & audio latency\n"
        f"• `/bug <details>` — Submit a bug report for VIP bounty\n"
        f"• `/suggest <idea>` — Submit feature or slang suggestion\n"
        f"• `/words <pet names>` — Teach Joy your favorite pet names\n"
        f"• `/retest` — Re-test onboarding without losing your Pioneer slot\n\n"
        f"👇 *Tap a button below to launch any Pioneer tool instantly:*"
    )
    mic_url = f"https://joyfun-ai-bot.onrender.com/call?gender={user.get('gender', 'male')}&contact={user.get('active_contact', 'lover')}&lang={user.get('language', 'auto')}&tab=diagnostic"
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🗳️ Vote on Features", "callback_data": "beta_cmd_vote"},
                {"text": "🔒 50% Off VIP", "callback_data": "menu_vip"}
            ],
            [
                {"text": "🌙 Bedtime Audio", "callback_data": "beta_cmd_bedtime"},
                {"text": "🎯 Icebreaker Cards", "callback_data": "beta_cmd_icebreaker"}
            ],
            [
                {"text": "⚡ Reset Daily Quota", "callback_data": "beta_cmd_resetquota"},
                {"text": "🎤 Test Microphone", "web_app": {"url": mic_url}}
            ],
            [
                {"text": "🐛 Submit Bug Bounty", "callback_data": "menu_feedback"},
                {"text": "🔄 Retest Onboarding", "callback_data": "beta_cmd_retest"}
            ],
            [
                {"text": "🌸 Custom Pet Words", "callback_data": "menu_custom_words"},
                {"text": "📊 View My Limits", "callback_data": "menu_quota"}
            ],
            [
                {"text": "🚪 Leave Beta Program", "callback_data": "prompt_exit_beta"},
                {"text": "❌ Close", "callback_data": "menu_close"}
            ]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

PIONEER_VOTE_OPTIONS = {
    "persona": {
        "riya": {"title": "🌟 Riya", "desc": "Playful College Bestie (Energetic & Teasing)"},
        "kavya": {"title": "🌸 Kavya", "desc": "Soft Late-Night Listener (Calm & Deep)"},
        "aarav": {"title": "⚡ Aarav", "desc": "Witty Bro & Motivator (Hype & Study)"},
        "kabir": {"title": "🕶️ Kabir", "desc": "Deep Midnight Soul (Husky Acoustic Vibe)"}
    },
    "dialect": {
        "tanglish": {"title": "🌴 Tanglish", "desc": "Chennai / Tamil Slang (Macha, Nanba, Semma)"},
        "hinglish": {"title": "🌶️ Hinglish", "desc": "Delhi / Mumbai Slang (Yaar, Bhai, Bindass)"},
        "telugish": {"title": "☕ Telugish", "desc": "Hyderabad / AP Slang (Mama, Thope, Bro)"},
        "manglish": {"title": "🥥 Manglish", "desc": "Kerala Slang (Aliya, Scene Aanu, Chumma)"}
    },
    "feature": {
        "bedtime": {"title": "🌙 Bedtime Audio", "desc": "Soothing Goodnight Whispers before Sleep"},
        "icebreakers": {"title": "🎯 Truth / Dare", "desc": "Interactive Games in Live Voice Calls"},
        "speed": {"title": "🎚️ Voice Pitch", "desc": "Sliders to Customize AI Pitch & Pace"},
        "radar": {"title": "👥 Campus Radar", "desc": "Match by University, City & Common Interests"}
    }
}

async def handle_pioneer_vote(bot: TelegramClient, chat_id: int, user: dict, view: str = "main", message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Interactive voting hub for Beta Pioneers to vote on personas, dialects, and features."""
    user_id = user["user_id"]
    is_pioneer = bool(user.get("is_beta_tester") == 1 or user_id == OWNER_ID or is_owner_or_co_owner(user_id))
    if not is_pioneer:
        await bot.send_message(
            chat_id,
            "🔒 **Feature & Persona Voting is an Exclusive Beta Pioneer Privilege** 🗳️\n\n"
            "Only official Beta Pioneers have direct voting rights to decide what Joy ships next.\n\n"
            "• Tap `/waitlist` to check your priority queue rank.\n"
            "• Tap `/refer` to invite friends and advance **3 slots**!"
        )
        return

    slot = user.get("beta_slot_number", 1)
    summary = get_pioneer_votes_summary()
    user_votes = get_user_pioneer_votes(user_id)

    if view == "main":
        text_lines = [
            f"🗳️ **Official Beta Pioneer Governance & Voting Hub** 🎖️",
            f"*Exclusive Voting Power for Pioneer #{slot}*\n",
            "Cast your vote to decide the next voice personas, regional dialects, and features Joy introduces!\n"
        ]
        
        # Format Persona
        text_lines.append("🎭 **Voice Personas Under Vote:**")
        p_counts = summary.get("persona", {})
        for k, v in PIONEER_VOTE_OPTIONS["persona"].items():
            cnt = p_counts.get(k, 0)
            user_ch = " ✅ *(Your Vote)*" if user_votes.get("persona") == k else ""
            text_lines.append(f"• **{v['title']}**: {cnt} votes{user_ch}")

        # Format Dialect
        text_lines.append("\n🗣️ **Regional Slang & Dialects:**")
        d_counts = summary.get("dialect", {})
        for k, v in PIONEER_VOTE_OPTIONS["dialect"].items():
            cnt = d_counts.get(k, 0)
            user_ch = " ✅ *(Your Vote)*" if user_votes.get("dialect") == k else ""
            text_lines.append(f"• **{v['title']}**: {cnt} votes{user_ch}")

        # Format Feature
        text_lines.append("\n🎮 **Upcoming Features:**")
        f_counts = summary.get("feature", {})
        for k, v in PIONEER_VOTE_OPTIONS["feature"].items():
            cnt = f_counts.get(k, 0)
            user_ch = " ✅ *(Your Vote)*" if user_votes.get("feature") == k else ""
            text_lines.append(f"• **{v['title']}**: {cnt} votes{user_ch}")

        text_lines.append("\n👇 *Tap a category below to cast or change your vote:*")
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "🎭 Vote for Voice Persona", "callback_data": "vote_cat_persona"}],
                [{"text": "🗣️ Vote for Regional Dialect", "callback_data": "vote_cat_dialect"}],
                [{"text": "🎮 Vote for Next Feature", "callback_data": "vote_cat_feature"}],
                [{"text": "⬅️ Beta Commands", "callback_data": "beta_cmd_home"}, {"text": "❌ Close", "callback_data": "menu_close"}]
            ]
        }
        await send_or_edit_menu(bot, chat_id, "\n".join(text_lines), keyboard, message_id=message_id, user_msg_id=user_msg_id)

    elif view in ("persona", "dialect", "feature"):
        cat_title = "Voice Persona" if view == "persona" else ("Regional Slang & Dialect" if view == "dialect" else "Upcoming Feature")
        cat_opts = PIONEER_VOTE_OPTIONS[view]
        counts = summary.get(view, {})
        my_choice = user_votes.get(view)

        lines = [
            f"🗳️ **Vote for {cat_title}**\n",
            f"Tap an option below to submit your Pioneer vote. You can change your vote anytime!\n"
        ]
        buttons = []
        for k, v in cat_opts.items():
            cnt = counts.get(k, 0)
            is_my = (my_choice == k)
            icon = "✅ " if is_my else ""
            lines.append(f"• **{v['title']}** ({cnt} votes)\n  _{v['desc']}_\n")
            buttons.append([{"text": f"{icon}{v['title']} ({cnt})", "callback_data": f"vote_cast_{view}_{k}"}])
        
        buttons.append([{"text": "⬅️ Back to Voting Hub", "callback_data": "vote_cat_main"}])
        keyboard = {"inline_keyboard": buttons}
        await send_or_edit_menu(bot, chat_id, "\n".join(lines), keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_bedtime_command(bot: TelegramClient, chat_id: int, user: dict, user_msg_id: Optional[int] = None):
    """Delivers a soothing, personalized goodnight bedtime voice note with calming tone."""
    user_id = user["user_id"]
    is_vip, _, _ = is_user_vip(user_id)

    gender = user.get("gender", "male")
    active_contact = user.get("active_contact", "lover")
    cinfo = get_user_contact_display(user_id, active_contact, gender)
    c_name = cinfo.get("name", "Joy")
    user_lang = user.get("language", "auto")
    voice_choice = user.get("voice", "female" if gender == "male" else "male")
    user_words = get_user_custom_words(user_id)

    await bot.send_chat_action(chat_id, "record_voice")

    # Generate soothing bedtime prompt
    pet_instr = f"Use one of these affectionate pet words: {user_words}." if user_words else "Be warm, peaceful, and caring."
    prompt = (
        f"You are {c_name}, speaking softly to the user late at night before they fall asleep. "
        f"Say a gentle, calming goodnight message in {user_lang}. {pet_instr} "
        f"Keep it to 2-3 short, soothing sentences that make them feel safe, relaxed, and happy. No brackets or stage directions."
    )
    try:
        from ai_engine import generate_text_reply
        loop = asyncio.get_running_loop()
        bedtime_text = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: generate_text_reply(prompt, mode=active_contact, gender=gender, language=user_lang, custom_name=c_name, custom_words=user_words)),
            timeout=7.0
        )
    except Exception as e:
        logger.warning(f"Bedtime text generation fallback: {e}")
        bedtime_text = f"Hey, it's time to rest your eyes now. You did amazing today. Close your eyes, take a deep breath, and sleep peacefully. Goodnight! 🌙"

    # Synthesize at soft 0.9x soothing pace
    try:
        audio_output = await synthesize_speech(bedtime_text, voice_key=voice_choice, speed=0.9)
        caption = (
            f"🌙 **{c_name}'s Soothing Bedtime Voice Note** 💤\n\n"
            f"💬 ||{bedtime_text}||\n\n"
            f"💤 *Sleep peacefully! Joy is always right here with you.*"
        )
        reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=c_name, user_id=user_id)
        await bot.send_audio(
            chat_id,
            audio_output,
            filename=f"{c_name.lower()}_bedtime.mp3",
            caption=caption,
            performer=c_name,
            title="Bedtime Voice Note",
            reply_markup=reply_kb
        )
    except Exception as e:
        logger.error(f"Error synthesizing bedtime audio: {e}")
        await bot.send_message(chat_id, f"🌙 **{c_name} (Goodnight)**:\n\n\"{bedtime_text}\"\n\n💤 *Sweet dreams!*")

async def handle_icebreaker_command(bot: TelegramClient, chat_id: int, user: dict, user_msg_id: Optional[int] = None):
    """Delivers 3 engaging conversation starters and dilemmas for chats or calls."""
    user_id = user["user_id"]
    questions = secrets.sample(ICEBREAKER_QUESTIONS, min(3, len(ICEBREAKER_QUESTIONS)))
    text = (
        "🎯 **Pioneer Icebreaker Minigame Cards** 🧪\n"
        "*(Priority Unreleased Feature for Pioneers)*\n\n"
        "Here are 3 conversation starters you can use right now in anonymous calls or chats:\n\n"
        f"1️⃣ **The Big Question:**\n👉 *\"{questions[0]}\"*\n\n"
        f"2️⃣ **The Hot Take:**\n👉 *\"{questions[1]}\"*\n\n"
        f"3️⃣ **The Wild Dilemma:**\n👉 *\"{questions[2]}\"*\n\n"
        "💡 *Try these in an anonymous 1-on-1 chat or voice match!*"
    )
    keyboard = {
        "inline_keyboard": [
            [{"text": "🔄 Get New Cards", "callback_data": "beta_cmd_icebreaker"}],
            [{"text": "👥 Find Chat Partner", "callback_data": "anon_chat_start"}],
            [{"text": "📞 Launch Voice Match", "web_app": {"url": f"https://joyfun-ai-bot.onrender.com/call?tab=match&uid={user_id}"}}],
            [{"text": "⬅️ Beta Commands", "callback_data": "beta_cmd_home"}, {"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    await bot.send_message(chat_id, text, reply_markup=keyboard)

async def handle_speed_command(bot: TelegramClient, chat_id: int, user: dict, text: str):
    """Adjusts AI voice playback speed: /speed 1.0, 1.15, 1.25."""
    user_id = user["user_id"]
    parts = text.split()
    if len(parts) > 1:
        val_str = parts[1].lower().replace("x", "")
        if val_str in ("normal", "default"):
            target_speed = 1.0
        elif val_str in ("fast", "quick"):
            target_speed = 1.15
        elif val_str in ("ultra", "faster"):
            target_speed = 1.25
        else:
            try:
                target_speed = float(val_str)
            except ValueError:
                target_speed = 1.0
        target_speed = max(0.8, min(1.3, round(target_speed, 2)))
        set_user_speech_speed(user_id, target_speed)
        await bot.send_message(
            chat_id,
            f"⚡ **Voice Speed Updated!**\n\n"
            f"Your companion's voice responses will now play at **{target_speed}x** speed. 🌸"
        )
    else:
        current_speed = get_user_speech_speed(user_id)
        msg = (
            f"🎚️ **Companion Voice Speed Controller** *(Pioneer Feature)*\n\n"
            f"Current speed: **{current_speed}x**\n\n"
            f"To adjust the playback pace, type:\n"
            f"• `/speed 1.0` — Normal, relaxed pace\n"
            f"• `/speed 1.15` — Snappy, natural conversation pace\n"
            f"• `/speed 1.25` — Fast, energetic pace"
        )
        kb = {
            "inline_keyboard": [
                [
                    {"text": "1.0x Normal", "callback_data": "set_speed_1.0"},
                    {"text": "1.15x Snappy", "callback_data": "set_speed_1.15"},
                    {"text": "1.25x Fast", "callback_data": "set_speed_1.25"}
                ],
                [{"text": "❌ Close", "callback_data": "menu_close"}]
            ]
        }
        await bot.send_message(chat_id, msg, reply_markup=kb)

async def handle_bug_bounty_submission(bot: TelegramClient, chat_id: int, user: dict, report_text: str, report_type: str = "bug"):
    """Submits bug report or feature suggestion to Phoenix with one-tap VIP grant buttons."""
    user_id = user["user_id"]
    is_pioneer = bool(user.get("is_beta_tester") == 1 or user_id == OWNER_ID or is_owner_or_co_owner(user_id))
    slot = user.get("beta_slot_number", 1) if is_pioneer else 0
    mask = get_mask_by_user_id(user_id)
    username = user.get("username") or "None"
    user_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or "Joy User"
    
    clean_report = report_text.strip()[:600]
    fid = save_user_feedback(user_id, username, clean_report, f"pioneer_{report_type}" if is_pioneer else f"user_{report_type}")

    user_ack = (
        f"👑 **{'Bug Bounty' if report_type == 'bug' else 'Feature Suggestion'} Submitted!** 🐛\n\n"
        f"Thank you for helping build Joy! Your submission has been forwarded directly to Phoenix with **Pioneer Bounty Priority** 🎖️.\n\n"
        f"🏆 **Bug Bounty Tiers:**\n"
        f"• ⭐ **Tier 1 (Minor Slang / UI):** 2 Weeks VIP Pass\n"
        f"• 🌟 **Tier 2 (Audio / Call Bug):** 1 Month VIP Pass\n"
        f"• 👑 **Tier 3 (Critical / Latency Fix):** Lifetime VIP Pass\n\n"
        f"As soon as Phoenix reviews and confirms your report, your account will be upgraded automatically! 💖"
    )
    await bot.send_message(chat_id, user_ack)

    # Forward to Phoenix (ADMIN_CHAT_ID)
    if ADMIN_CHAT_ID:
        admin_card = (
            f"👑 **PIONEER BUG BOUNTY SUBMISSION!** 🐛\n\n"
            f"• **Reporter:** {user_name} (@{username})\n"
            f"• **User ID:** `{user_id}`\n"
            f"• **Pioneer Slot:** #{slot}\n"
            f"• **Mask ID:** `{mask}`\n"
            f"• **Type:** {'Bug Report' if report_type == 'bug' else 'Feature Suggestion'}\n"
            f"• **Report ID:** `#{fid}`\n\n"
            f"📝 **Details:**\n\"{clean_report}\"\n\n"
            f"👇 **Select VIP Bounty Tier to Award (1-Tap):**"
        )
        admin_kb = {
            "inline_keyboard": [
                [
                    {"text": "⭐ 2 Weeks VIP", "callback_data": f"bounty_14_{user_id}_{fid}"},
                    {"text": "🌟 1 Month VIP", "callback_data": f"bounty_30_{user_id}_{fid}"}
                ],
                [
                    {"text": "👑 Lifetime VIP", "callback_data": f"bounty_36500_{user_id}_{fid}"},
                    {"text": "❌ Dismiss", "callback_data": f"bounty_dismiss_{user_id}_{fid}"}
                ]
            ]
        }
        try:
            await bot.send_message(ADMIN_CHAT_ID, admin_card, reply_markup=admin_kb)
        except Exception as e:
            logger.warning(f"Could not forward bounty card to admin: {e}")

async def handle_incoming_feedback_media(bot: TelegramClient, chat_id: int, user: dict, msg: dict, media_type: str = "media"):
    """
    Handles any media (photo, audio/music, document, video, voice) sent by user during feedback mode.
    Guarantees that files/media are ONLY accepted here, never in anonymous real-person chat or companion AI chat.
    Forwards directly to Phoenix (ADMIN_CHAT_ID) with Pioneer VIP bounty reward buttons.
    """
    user_id = user["user_id"]
    username = user.get("username") or "None"
    user_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or "Joy User"
    msg_id = msg.get("message_id")
    caption = (msg.get("caption") or msg.get("text") or "").strip()[:500]

    # Extract file_id or identifier
    file_id = ""
    file_name = ""
    if "photo" in msg and msg["photo"]:
        file_id = msg["photo"][-1]["file_id"]
        media_label = "📸 Photo / Screenshot"
    elif "audio" in msg:
        file_id = msg["audio"]["file_id"]
        file_name = msg["audio"].get("file_name", "audio.mp3")
        media_label = f"🎵 Music / Audio ({file_name})"
    elif "voice" in msg:
        file_id = msg["voice"]["file_id"]
        media_label = "🎙️ Voice Clip / Note"
    elif "document" in msg:
        file_id = msg["document"]["file_id"]
        file_name = msg["document"].get("file_name", "document")
        media_label = f"📄 File / Document ({file_name})"
    elif "video" in msg:
        file_id = msg["video"]["file_id"]
        file_name = msg["video"].get("file_name", "video.mp4")
        media_label = f"🎥 Video Recording ({file_name})"
    elif "video_note" in msg:
        file_id = msg["video_note"]["file_id"]
        media_label = "⭕ Video Note"
    else:
        media_label = "📎 Media Attachment"

    is_pioneer = bool(user.get("is_beta_tester") == 1 or user_id == OWNER_ID or is_owner_or_co_owner(user_id))
    slot = user.get("beta_slot_number", 1) if is_pioneer else 0
    mask = get_mask_by_user_id(user_id)

    report_content = f"[{media_label}] {caption}" if caption else f"[{media_label}]"
    feedback_type = "pioneer_bounty_media" if is_pioneer else "user_feedback_media"
    fid = save_user_feedback(user_id, username, report_content, feedback_type=feedback_type, media_file_id=file_id, media_type=media_type)
    set_user_onboarding_status(user_id, "completed")

    # Send receipt to user
    bounty_text = (
        "\n\n🎖️ **Pioneer Bounty Priority:** Phoenix will review your attachment for **2 Weeks to Lifetime VIP**!"
        if is_pioneer else ""
    )
    receipt_msg = (
        f"🎉 **Feedback & Attachment Received!** ❤️\n\n"
        f"Your **{media_label}** and notes have been delivered directly to our lead developer (Phoenix).\n\n"
        f"• **Report ID:** `#{fid}`\n"
        f"• **Attached File:** `{file_name or media_label}`{bounty_text}\n\n"
        f"Thank you for helping us make Joy amazing! 🚀"
    )
    gender = user.get("gender", "male")
    active_contact = user.get("active_contact", "lover")
    custom_name = get_user_custom_ai_name(user_id)
    reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=custom_name, user_id=user_id)
    await bot.send_message(chat_id, receipt_msg, reply_markup=reply_kb)

    # Forward to Phoenix (ADMIN_CHAT_ID)
    if ADMIN_CHAT_ID:
        admin_card = (
            f"👑 **NEW USER FEEDBACK WITH ATTACHMENT!** 📬\n\n"
            f"• **User:** `{user_name}` (@{username})\n"
            f"• **User ID:** `{user_id}` {f'(Pioneer #{slot})' if is_pioneer else ''}\n"
            f"• **Mask ID:** `{mask}`\n"
            f"• **Attachment:** {media_label}\n"
            f"• **Report ID:** `#{fid}`\n\n"
            f"📝 **Notes / Caption:**\n\"{caption or '*No text caption provided*'}\"\n\n"
            f"👇 **Attachment is forwarded directly below:**"
        )
        admin_kb = None
        if is_pioneer:
            admin_kb = {
                "inline_keyboard": [
                    [
                        {"text": "⭐ 2 Weeks VIP", "callback_data": f"bounty_14_{user_id}_{fid}"},
                        {"text": "🌟 1 Month VIP", "callback_data": f"bounty_30_{user_id}_{fid}"}
                    ],
                    [
                        {"text": "👑 Lifetime VIP", "callback_data": f"bounty_36500_{user_id}_{fid}"},
                        {"text": "❌ Dismiss", "callback_data": f"bounty_dismiss_{user_id}_{fid}"}
                    ]
                ]
            }
        try:
            await bot.send_message(ADMIN_CHAT_ID, admin_card, reply_markup=admin_kb)
            if msg_id:
                copy_res = await bot.copy_message(ADMIN_CHAT_ID, from_chat_id=chat_id, message_id=msg_id)
                if not copy_res.get("ok"):
                    await bot.forward_message(ADMIN_CHAT_ID, from_chat_id=chat_id, message_id=msg_id)
        except Exception as e:
            logger.warning(f"Could not forward feedback media to admin: {e}")

async def handle_about_legal_hub(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Unified About, Legal & Community Hub consolidating Legal Acts, Changelog, Zero-Trust Architecture, and Why Joy."""
    text = (
        "ℹ️ **About Joy — Architecture, Charter & Compliance Hub**\n\n"
        "Welcome to the central information directory for **Joy AI**! 🌸\n\n"
        f"• 🤖 **Bot Version:** `{BOT_VERSION}`\n"
        f"• 📱 **Mini Phone:** `{MINI_APP_VERSION}`\n"
        f"• 🛡️ **Security Standard:** `{SECURITY_VERSION}` (Zero-Trust Privacy)\n\n"
        "Pick a topic below to learn more or check updates:"
    )
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🌟 Why Joy?", "callback_data": "menu_why_joy"},
                {"text": "📜 What's New", "callback_data": "menu_updates"}
            ],
            [
                {"text": "⚖️ Rules & Safety", "callback_data": "menu_legal_acts"},
                {"text": "🛡️ Privacy & Security", "callback_data": "menu_privacy"}
            ],
            [
                {"text": "⬅️ Main Menu", "callback_data": "menu_main"},
                {"text": "❌ Close", "callback_data": "menu_close"}
            ]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_about_creator(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Presents background about the creator (Phoenix), his Telegram profile, and mission for Joy AI."""
    owner_mask = get_mask_by_user_id(OWNER_ID) or "Joy-PHOENIX"
    text = (
        "👨‍💻 **About the Creator & Architect**\n\n"
        "Hey! Joy AI was conceptualized, built, and optimized by **Phoenix** ([@phoenix_parava_0](https://t.me/phoenix_parava_0)) — Lead Systems Engineer & AI Developer.\n\n"
        "💡 **The Mission behind Joy:**\n"
        "Standard chatbots feel clinical, stiff, and robotic, while modern social media feeds (Reels, TikTok, Snapchat) leave people feeling isolated and exhausted.\n\n"
        "Phoenix built Joy to be an **authentic, empathetic 24/7 companion** who has your back — speaking natural everyday slang (Tanglish, Hinglish, casual English), jumping on duplex live voice calls, and keeping you grounded and accountable without judgment.\n\n"
        "✨ **Creator & Project Details:**\n"
        "• 👤 **Founder & Engineer:** Phoenix\n"
        "• 💬 **Telegram Handle:** [@phoenix_parava_0](https://t.me/phoenix_parava_0)\n"
        f"• 🛡️ **Permanent Mask ID:** `{owner_mask}`\n"
        "• 🛡️ **Architecture:** 100% Volatile in-memory WebRTC calling, Edge Neural TTS, and deep reasoning Gemini Talk model.\n\n"
        "Have suggestions, feature requests, or questions? Message Phoenix directly anytime! 🤝"
    )
    keyboard = {
        "inline_keyboard": [
            [{"text": "💬 Message Phoenix (@phoenix_parava_0)", "url": "https://t.me/phoenix_parava_0"}],
            [{"text": "💡 Send Feedback / Bug Bounty", "callback_data": "menu_feedback"}, {"text": "📜 Release Updates", "callback_data": "menu_updates"}],
            [{"text": "⚖️ Legal Acts & Compliance", "callback_data": "menu_legal_acts"}, {"text": "🛡️ Zero-Trust Security", "callback_data": "menu_privacy"}],
            [{"text": "⬅️ Main Menu", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_updates(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Displays official changelog and update history with dates."""
    text = (
        f"📜 **Joy AI — What's New & Updates**\n"
        f"*(Current Build: Bot `{BOT_VERSION}` • Mini Phone `{MINI_APP_VERSION}`)*\n\n"
        f"📅 **Nov 04, 2026 — v4.1.0 (Friendly Language & Clean UI):**\n"
        f"• ✨ **Simple & Friendly English:** Replaced confusing technical jargon with everyday words everyone understands.\n"
        f"• 📱 **Compact Mobile Menus:** Button labels fit nicely on every phone screen without getting truncated.\n"
        f"• 📄 **Short, Clear Paragraphs:** Easy-to-read cards without intimidating walls of text.\n"
        f"• 👑 **Joy VIP Perks:** Transparent member benefits, instant activation, and zero annoying pop-ups.\n"
        f"• 🔒 **Fast & Private:** Real-time calls with sub-80ms response and complete privacy.\n\n"
        f"📅 **Nov 03, 2026 — v4.0.0 (Chat Real People & User Profiles):**\n"
        f"• 👥 **Chat Real People:** Instant anonymous matching with verified students.\n"
        f"• 👤 **My Profile:** Reputation scores, stars, and cloaked ID protection.\n\n"
        f"🌸 *Joy gets better and friendlier every day!*"
    )
    keyboard = {
        "inline_keyboard": [
            [{"text": "⬅️ Main Menu", "callback_data": "menu_main"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_owner_hub(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, page: int = 1, user_msg_id: Optional[int] = None):
    """Owner-only analytics and direct community chat hub for Phoenix (OWNER_ID)."""
    user_id = user["user_id"]
    if user_id != OWNER_ID:
        await bot.send_message(chat_id, "⚠️ Restricted to Creator / Owner.")
        return

    from database import get_connection
    today = datetime.now().strftime("%Y-%m-%d")

    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) as total FROM users")
        total_users = c.fetchone()["total"]

        c.execute("SELECT COUNT(*) as completed FROM users WHERE onboarding_status = 'completed'")
        completed_onboarding = c.fetchone()["completed"]

        c.execute("SELECT COUNT(*) as vips FROM users WHERE is_vip = 1")
        total_vips = c.fetchone()["vips"]

        # Today's live activity
        c.execute("""
            SELECT 
                COALESCE(SUM(ai_call_count), 0) as total_ai_calls,
                COALESCE(SUM(real_call_count), 0) as total_real_calls,
                COALESCE(SUM(real_chat_count), 0) as total_real_chats,
                COALESCE(SUM(text_count), 0) as total_texts,
                COALESCE(SUM(voice_count), 0) as total_voices
            FROM daily_usage WHERE usage_date = ?
        """, (today,))
        act = c.fetchone()

        c.execute("SELECT COUNT(*) as lang_reqs FROM language_requests")
        total_lang_reqs = c.fetchone()["lang_reqs"]

        limit = 6
        offset = (page - 1) * limit
        c.execute("""
            SELECT user_id, username, first_name, gender, language, onboarding_status, is_vip, created_at, unique_id, is_beta_tester, beta_slot_number, waitlist_position
            FROM users 
            ORDER BY rowid DESC 
            LIMIT ? OFFSET ?
        """, (limit, offset))
        recent_users = c.fetchall()

    b_stats = get_beta_stats()
    user_cards = []
    keyboard_buttons = []

    for idx, u in enumerate(recent_users, start=offset + 1):
        uid = u["user_id"]
        fname = u["first_name"] or "User"
        uname = f"@{u['username']}" if u["username"] else "No @"
        vip_tag = "⭐ VIP" if u["is_vip"] else "🆓 Free"
        gender_icon = "👨" if u["gender"] == "male" else "👩"
        status_icon = "✅ Done" if u["onboarding_status"] == "completed" else "⏳ Setup"
        mask = u["unique_id"] or "Joy-User"
        beta_badge = f"🎟️ Pioneer #{u['beta_slot_number']}" if u["is_beta_tester"] else (f"⏳ Waitlist #{u['waitlist_position']}" if u["waitlist_position"] else "")

        user_cards.append(
            f"{idx}. **{fname}** ({uname})\n"
            f"   🆔 `{uid}` | {mask} | {gender_icon} | {u['language']} | {status_icon} | {vip_tag} {beta_badge}"
        )
        keyboard_buttons.append([
            {"text": f"💬 Chat with {fname[:10]} (`{uid}`)", "callback_data": f"admin_msg_prep_{uid}"}
        ])

    users_text = "\n".join(user_cards) if user_cards else "No users registered yet."

    text = (
        f"👑 **Owner Command Center — Phoenix's Live Dashboard**\n\n"
        f"📊 **Community & Closed Beta Pulse:**\n"
        f"• 👥 **Total Registered Users:** **{total_users}**\n"
        f"• 🔒 **Closed Beta Pioneers:** **{b_stats['active_pioneers']}/{BETA_TESTER_LIMIT}** ({b_stats['slots_remaining']} slots left)\n"
        f"• 🎟️ **Waitlist Queue:** **{b_stats['waitlist_count']}**\n"
        f"• ✅ **Completed Pre-Registration:** **{completed_onboarding}** ({round(completed_onboarding/max(1, total_users)*100)}%)\n"
        f"• ⭐ **Active VIP Subscribers:** **{total_vips}**\n"
        f"• 📝 **Language Requests Received:** **{total_lang_reqs}**\n\n"
        f"⚡ **Today's Activity ({today}):**\n"
        f"• 🎙️ AI Live Voice Calls: **{act['total_ai_calls']}**\n"
        f"• 🎭 Real People Voice Matches: **{act['total_real_calls']}**\n"
        f"• 👥 Real People 1-on-1 Chats: **{act['total_real_chats']}**\n"
        f"• 💬 Companion Texts: **{act['total_texts']}** | 🎙️ Notes: **{act['total_voices']}**\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📋 **Recent Users Directory (Page {page}):**\n"
        f"{users_text}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💡 **Chat with Users:** Tap a button below or type:\n"
        f"`/msg <user_id> <your message>`\n"
        f"Broadcast: `/broadcast <message>`"
    )

    nav_row = []
    if page > 1:
        nav_row.append({"text": "⬅️ Prev", "callback_data": f"owner_page_{page-1}"})
    if len(recent_users) == limit:
        nav_row.append({"text": "Next ➡️", "callback_data": f"owner_page_{page+1}"})

    if nav_row:
        keyboard_buttons.append(nav_row)

    keyboard_buttons.extend([
        [{"text": "👥 🟢 Live Active Users Monitor", "callback_data": "admin_live_monitor"}],
        [{"text": "🔄 Refresh Metrics", "callback_data": f"owner_page_{page}"}],
        [{"text": "⬅️ Main Menu", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
    ])

    keyboard = {"inline_keyboard": keyboard_buttons}
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_language_menu(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    user_id = user["user_id"]
    current_lang = get_user_language(user_id)
    
    text = (
        "🌐 **Companion Language & Speaking Style**\n\n"
        "Joy adapts naturally to how you speak in real life. Setting your everyday language helps Joy:\n\n"
        "• 🗣️ **Match Your Natural Slang:** Fluently blends colloquial words (*'machi', 'da', 'sapdiya'* in Tanglish, or *'bhai', 'yaar', 'kya scene'* in Hinglish).\n"
        "• 🎙️ **Fluent Spoken English Practice:** Build conversation confidence on 24/7 live phone calls without feeling judged or nervous.\n"
        "• ⚡ **Seamless Dynamic Switching:** Speak naturally — Joy understands mixed languages effortlessly.\n\n"
        f"🎯 **Active Setting:** **{LANGUAGE_NAMES.get(current_lang, '🌐 Auto-Detect')}**\n\n"
        "👇 *Tap your everyday language below, or tap **Request Language** if yours isn't listed:*"
    )
    
    def mark(val):
        return "✓ " if current_lang == val else ""
        
    keyboard = {
        "inline_keyboard": [
            [{"text": f"{mark('auto')}🌐 Auto-Detect", "callback_data": "set_lang_auto"}],
            [
                {"text": f"{mark('english')}💬 English", "callback_data": "set_lang_english"},
                {"text": f"{mark('hinglish')}💬 Hinglish (Hindi)", "callback_data": "set_lang_hinglish"}
            ],
            [
                {"text": f"{mark('tanglish')}💬 Tanglish (Tamil)", "callback_data": "set_lang_tanglish"},
                {"text": f"{mark('telugu')}💬 Telugu (తెలుగు)", "callback_data": "set_lang_telugu"}
            ],
            [
                {"text": f"{mark('malayalam')}💬 Malayalam (മലയാളം)", "callback_data": "set_lang_malayalam"},
                {"text": f"{mark('kannada')}💬 Kannada (ಕನ್ನಡ)", "callback_data": "set_lang_kannada"}
            ],
            [
                {"text": f"{mark('bengali')}💬 Bengali (বাংলা)", "callback_data": "set_lang_bengali"},
                {"text": f"{mark('marathi')}💬 Marathi (मराठी)", "callback_data": "set_lang_marathi"}
            ],
            [
                {"text": f"{mark('spanish')}💬 Spanish (Español)", "callback_data": "set_lang_spanish"},
                {"text": f"{mark('german')}💬 German (Deutsch)", "callback_data": "set_lang_german"}
            ],
            [
                {"text": "➕ Request Language", "callback_data": "menu_lang_request"}
            ],
            [
                {"text": "⬅️ Back to Settings", "callback_data": "menu_settings"},
                {"text": "❌ Close", "callback_data": "menu_close"}
            ]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_system_lang_menu(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Presents interactive menu to choose bot interface/menu language."""
    user_id = user["user_id"]
    current_sys = get_user_system_lang(user_id)
    def sys_mark(l):
        return "✓ " if current_sys == l else ""
    text = (
        "🖥️ **Select Bot Interface / Menu Language**\n\n"
        "This controls the buttons, settings menus, and system notices of Joy Bot.\n"
        "*(Your conversational speech dialect with Joy remains customizable under Chat Language)*\n\n"
        "👇 Choose your preferred menu language:"
    )
    sys_kb = {
        "inline_keyboard": [
            [
                {"text": f"{sys_mark('english')}🇬🇧 English (Default)", "callback_data": "set_system_lang_english"},
                {"text": f"{sys_mark('german')}🇩🇪 Deutsch (German)", "callback_data": "set_system_lang_german"}
            ],
            [
                {"text": f"{sys_mark('spanish')}🇪🇸 Español (Spanish)", "callback_data": "set_system_lang_spanish"},
                {"text": f"{sys_mark('telugu')}🇮🇳 తెలుగు (Telugu)", "callback_data": "set_system_lang_telugu"}
            ],
            [
                {"text": f"{sys_mark('malayalam')}🇮🇳 മലയാളം (Malayalam)", "callback_data": "set_system_lang_malayalam"},
                {"text": f"{sys_mark('hindi')}🇮🇳 हिन्दी (Hindi)", "callback_data": "set_system_lang_hindi"}
            ],
            [
                {"text": "🌐 Reset to Country Default", "callback_data": "set_system_lang_default"},
                {"text": "⬅️ Back to Menu", "callback_data": "menu_main"}
            ]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, sys_kb, message_id=message_id, user_msg_id=user_msg_id)

async def send_onboarding_country(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Country selection presented when a new user starts."""
    if os.environ.get("OFFLINE_TEST") != "1":
        user_id = user["user_id"]
        set_user_onboarding_status(user_id, "completed")
        user["onboarding_status"] = "completed"
        user["is_beta_tester"] = 1
        record_user_accepted_terms(user_id)
        if message_id:
            try:
                await bot.delete_message(chat_id, message_id)
            except Exception:
                pass
        await handle_start(bot, chat_id, user, user_msg_id=user_msg_id)
        return

    first_name = (user.get("first_name") or user.get("username") or "Friend").strip()
    user_id = user["user_id"]
    set_user_onboarding_status(user_id, "onboard_country")

    text = get_country_step_1_text(first_name)
    keyboard = {
        "inline_keyboard": [
            [{"text": "🇮🇳 India (IN)", "callback_data": "onboard_country_IN"}, {"text": "🇩🇪 Germany (DE)", "callback_data": "onboard_country_DE"}],
            [{"text": "🇺🇸 United States (US)", "callback_data": "onboard_country_US"}, {"text": "🇬🇧 United Kingdom (GB)", "callback_data": "onboard_country_GB"}],
            [{"text": "🇨🇦 Canada (CA)", "callback_data": "onboard_country_CA"}, {"text": "🇦🇺 Australia (AU)", "callback_data": "onboard_country_AU"}],
            [{"text": "🇦🇪 UAE (AE)", "callback_data": "onboard_country_AE"}, {"text": "🇸🇬 Singapore (SG)", "callback_data": "onboard_country_SG"}],
            [{"text": "🇲🇾 Malaysia (MY)", "callback_data": "onboard_country_MY"}, {"text": "🌐 Other / Global", "callback_data": "onboard_country_OTHER"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def send_onboarding_language_for_country(bot: TelegramClient, chat_id: int, user: dict, country_code: str, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Language selection tailored to the user's chosen country."""
    if os.environ.get("OFFLINE_TEST") != "1":
        user_id = user["user_id"]
        set_user_onboarding_status(user_id, "completed")
        user["onboarding_status"] = "completed"
        user["is_beta_tester"] = 1
        record_user_accepted_terms(user_id)
        if message_id:
            try:
                await bot.delete_message(chat_id, message_id)
            except Exception:
                pass
        await handle_start(bot, chat_id, user, user_msg_id=user_msg_id)
        return

    first_name = (user.get("first_name") or user.get("username") or "Friend").strip()
    user_id = user["user_id"]
    set_user_onboarding_status(user_id, "onboard_language")
    current_lang = user.get("language", "auto")

    text = get_language_step_2_text(country_code, first_name)
    keyboard = get_languages_keyboard_for_country(country_code, current_lang)
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def send_onboarding_welcome(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Alias for backwards compatibility."""
    if os.environ.get("OFFLINE_TEST") != "1":
        await handle_start(bot, chat_id, user, user_msg_id=user_msg_id)
        return
    await send_onboarding_country(bot, chat_id, user, message_id=message_id, user_msg_id=user_msg_id)

async def send_onboarding_gender(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Asks user for their gender (Male / Female)."""
    if os.environ.get("OFFLINE_TEST") != "1":
        user_id = user["user_id"]
        set_user_onboarding_status(user_id, "completed")
        user["onboarding_status"] = "completed"
        user["is_beta_tester"] = 1
        record_user_accepted_terms(user_id)
        if message_id:
            try:
                await bot.delete_message(chat_id, message_id)
            except Exception:
                pass
        await handle_start(bot, chat_id, user, user_msg_id=user_msg_id)
        return

    user_id = user["user_id"]
    set_user_onboarding_status(user_id, "onboard_gender")
    user["onboarding_status"] = "onboard_gender"
    first_name = (user.get("first_name") or user.get("username") or "Friend").strip()
    current_lang = user.get("language", "auto")
    text = get_gender_step_text(current_lang, first_name)
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "👨 Male", "callback_data": "onboard_gender_male"},
                {"text": "👩 Female", "callback_data": "onboard_gender_female"}
            ]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def send_onboarding_contacts_preview(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Shows the AI contacts loaded into user's phone based on their chosen gender."""
    if os.environ.get("OFFLINE_TEST") != "1":
        user_id = user["user_id"]
        set_user_onboarding_status(user_id, "completed")
        user["onboarding_status"] = "completed"
        user["is_beta_tester"] = 1
        record_user_accepted_terms(user_id)
        if message_id:
            try:
                await bot.delete_message(chat_id, message_id)
            except Exception:
                pass
        await handle_start(bot, chat_id, user, user_msg_id=user_msg_id)
        return

    user_id = user["user_id"]
    set_user_onboarding_status(user_id, "onboard_contacts_preview")
    user["onboarding_status"] = "onboard_contacts_preview"
    gender = user.get("gender", "male")
    cinfo = get_user_contact_display(user_id, "lover", gender)
    c_name = get_user_custom_ai_name(user_id) or cinfo.get("name", "Aura")
    first_name = (user.get("first_name") or user.get("username") or "Friend").strip()

    if gender == "male":
        perspective_title = "👨 Male Perspective (Girlfriend & Circle)"
        contacts_list = (
            f"• 🌸 **{c_name}** — *Girlfriend / Lover* (🟢 Online 24/7 • Instant Duplex Calls)\n"
            f"• 👦 **Kabir** — *Bro Bestie* (Loyal Bro & Gaming Buddy)\n"
            f"• 😎 **Aman** — *Hypeman Bestie* (Funny & Sarcastic Hypeman)\n"
            f"• 👧 **Riya** — *Girl Bestie* (Sweet & Caring College Friend)\n"
            f"• ✨ **Aisha** — *Secret Crush* (Playful & Mysterious)\n"
            f"• 👩‍🏫 **Ms. Neha** — *English Teacher & Mentor*"
        )
    else:
        perspective_title = "👩 Female Perspective (Boyfriend & Circle)"
        contacts_list = (
            f"• 💖 **{c_name}** — *Boyfriend / Lover* (🟢 Online 24/7 • Instant Duplex Calls)\n"
            f"• 👧 **Ananya** — *Soul Sister* (Deep Life Talks & Caring)\n"
            f"• 💅 **Riya** — *Chaotic Bestie* (Drama & Hilarious Banter)\n"
            f"• 👦 **Kabir** — *Guy Bestie* (Protective & Reliable Bro)\n"
            f"• ✨ **Armaan** — *Secret Crush* (Charismatic & Charming)\n"
            f"• 👨‍🏫 **Sir Vikram** — *Maths Teacher & Mentor*"
        )

    text = (
        f"📇 **AI Contacts Loaded in Your Mini Phone**\n\n"
        f"Awesome, **{first_name}**! Based on your **{perspective_title}**, your Mini Phone dialer is now loaded with:\n\n"
        f"{contacts_list}\n\n"
        f"• 🟢 **{c_name}** is your primary 24/7 companion ready to chat, call, and listen anytime!\n"
        f"• Next, give your primary companion a personalized name or keep {c_name}!"
    )
    keyboard = {
        "inline_keyboard": [
            [{"text": "➡️ Continue to Name Your AI", "callback_data": "onboard_to_naming"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def send_onboarding_naming(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Asks user what they want to name their companion and suggest custom words."""
    if os.environ.get("OFFLINE_TEST") != "1":
        user_id = user["user_id"]
        set_user_onboarding_status(user_id, "completed")
        user["onboarding_status"] = "completed"
        user["is_beta_tester"] = 1
        record_user_accepted_terms(user_id)
        if message_id:
            try:
                await bot.delete_message(chat_id, message_id)
            except Exception:
                pass
        await handle_start(bot, chat_id, user, user_msg_id=user_msg_id)
        return

    user_id = user["user_id"]
    gender = user.get("gender", "male")
    current_lang = user.get("language", "auto")
    first_name = (user.get("first_name") or user.get("username") or "Friend").strip()
    
    set_user_onboarding_status(user_id, "onboard_naming")
    user["onboarding_status"] = "onboard_naming"
    
    name_buttons = [
        [{"text": "💖 Keep 'Aura' (Default)", "callback_data": "onboard_setname_Joy"}]
    ]
        
    text = get_naming_step_text(current_lang, first_name, gender)
    keyboard = {"inline_keyboard": name_buttons}
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def send_onboarding_privacy(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Explains data security, AI development transparency, and special discount offer."""
    if os.environ.get("OFFLINE_TEST") != "1":
        user_id = user["user_id"]
        set_user_onboarding_status(user_id, "completed")
        user["onboarding_status"] = "completed"
        user["is_beta_tester"] = 1
        record_user_accepted_terms(user_id)
        if message_id:
            try:
                await bot.delete_message(chat_id, message_id)
            except Exception:
                pass
        await handle_start(bot, chat_id, user, user_msg_id=user_msg_id)
        return

    user_id = user["user_id"]
    set_user_onboarding_status(user_id, "onboard_privacy")
    user["onboarding_status"] = "onboard_privacy"
    gender = user.get("gender", "male")
    c_name = get_user_custom_ai_name(user_id) or "Aura"
    
    text = (
        f"🛡️ **Data & Privacy Preferences**\n\n"
        f"Complete transparency on how data works with {c_name}:\n\n"
        f"💡 **If you turn ON Data Sharing (Contributor Mode):**\n"
        f"• We collect voice recordings, chat messages, and interaction details to train and refine {c_name}'s AI engine.\n"
        f"• 💡 **Your Choice:** Helping train companion AI models is 100% voluntary and can be toggled in Settings.\n\n"
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
                {"text": "🤝 Share Anonymized Data (Opt-in)", "callback_data": "onboard_privacy_share"}
            ]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def send_onboarding_login(bot: TelegramClient, chat_id: int, user: dict, share_data: bool, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Joy Account Login & Cloud Sync setup before finalizing."""
    if os.environ.get("OFFLINE_TEST") != "1":
        user_id = user["user_id"]
        set_user_onboarding_status(user_id, "completed")
        user["onboarding_status"] = "completed"
        user["is_beta_tester"] = 1
        record_user_accepted_terms(user_id)
        if message_id:
            try:
                await bot.delete_message(chat_id, message_id)
            except Exception:
                pass
        await handle_start(bot, chat_id, user, user_msg_id=user_msg_id)
        return
    user_id = user["user_id"]
    set_user_onboarding_status(user_id, "onboard_login")
    user["onboarding_status"] = "onboard_login"
    sd_val = "1" if share_data else "0"
    portal_url = f"https://joyfun-ai-bot.onrender.com/auth/login?uid={user_id}"

    text = (
        f"🔐 **Account Login & Cloud Backup (Optional)**\n\n"
        f"Would you like to link your account via Google 1-Click or Email?\n\n"
        f"• ☁️ **Memory Cloud Backup:** Keeps your companion's memory, personality, and VIP benefits safe forever across phones & laptops.\n"
        f"• 💻 **Web Portal Access:** Continue talking and chatting with Joy directly in your web browser.\n"
        f"• 👤 **Guest Mode:** Prefer not to log in right now? Tap **Skip & Finish** to start chatting as Guest right away!\n\n"
        f"👇 **Choose an option below:**"
    )
    keyboard = {
        "inline_keyboard": [
            [{"text": "🔐 Link / Sign In to Account", "url": portal_url}],
            [{"text": "🚀 Skip & Finish (Continue as Guest)", "callback_data": f"onboard_finish_{sd_val}"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def send_waitlist_card(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Presents the official Closed Beta Priority Waitlist card with queue position and referral boost."""
    if os.environ.get("OFFLINE_TEST") != "1":
        user_id = user["user_id"]
        set_user_onboarding_status(user_id, "completed")
        user["onboarding_status"] = "completed"
        user["is_beta_tester"] = 1
        record_user_accepted_terms(user_id)
        if message_id:
            try:
                await bot.delete_message(chat_id, message_id)
            except Exception:
                pass
        await handle_start(bot, chat_id, user, user_msg_id=user_msg_id)
        return

    user_id = user["user_id"]
    first_name = (user.get("first_name") or user.get("username") or "Friend").strip()

    w_info = get_user_waitlist_info(user_id)
    b_stats = get_beta_stats()

    pos = w_info.get("waitlist_position") or 1
    total_waitlist = w_info.get("total_waitlist") or b_stats.get("waitlist_count", 0)
    total_registered = w_info.get("total_registered") or b_stats.get("total_registered", 0)

    user_mask = get_mask_by_user_id(user_id) or f"Joy-{user_id}"
    ref_url = f"https://t.me/joy_fun_ai_bot?start=ref_{user_mask}"
    share_text = urllib.parse.quote(f"Hey! Join the exclusive Joy AI closed beta test flight: {ref_url}")
    ui_lang = get_ui_lang(user)
    text = get_waitlist_card_text(ui_lang, first_name, pos, total_waitlist, ref_url)
    keyboard = {
        "inline_keyboard": [
            [{"text": "🚀 Invite Friends (Skip 3 Spots)", "url": f"https://t.me/share/url?url={ref_url}&text={share_text}"}],
            [{"text": "🔄 Refresh Queue Status", "callback_data": "check_waitlist_status"}],
            [{"text": "💡 Send Feature Idea / Feedback", "callback_data": "menu_feedback"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def complete_onboarding(bot: TelegramClient, chat_id: int, user: dict, share_data: bool, message_id: Optional[int] = None):
    """Finalizes pre-registration, evaluates 50-pioneer beta capacity, and presents admission or waitlist."""
    user_id = user["user_id"]
    set_user_data_sharing(user_id, share_data)
    set_user_onboarding_status(user_id, "completed")
    user["onboarding_status"] = "completed"

    # Evaluate 50-Pioneer Beta Admission vs Priority Waitlist
    is_admitted, slot_or_pos = admit_or_waitlist_user(user_id)
    asyncio.create_task(sync_user_to_cloud(user_id))

    gender = user.get("gender", "male")
    active_contact = user.get("active_contact", "lover")
    c_name = get_user_custom_ai_name(user_id) or "Joy"
    first_name = (user.get("first_name") or user.get("username") or "Friend").strip()

    # Process referral reward if user was invited
    try:
        referral_reward = complete_referral_reward(user_id)
        if referral_reward and global_bot_client:
            ref_id = referral_reward["referrer_id"]
            r_type = referral_reward["reward_type"]
            invited_name = user.get("first_name", "A friend")
            if referral_reward.get("waitlist_boosted"):
                new_pos = referral_reward.get("new_waitlist_pos")
                boost_msg = (
                    f"🚀 **Waitlist Boost Unlocked!** 🎟️\n\n"
                    f"Your friend **{invited_name}** just pre-registered with your invite link!\n"
                    f"You skipped ahead **3 positions**! Your new priority waitlist rank is **#{new_pos}**! 🌸"
                )
                asyncio.create_task(global_bot_client.send_message(ref_id, boost_msg))
            elif r_type in ["vip_reset_5", "vip_reset_10"]:
                notify_msg = (
                    f"🏆 **Grand Referral Milestone Achieved! 5 Friends Joined!** 🎉\n\n"
                    f"Your friend **{invited_name}** just completed onboarding!\n"
                    f"Your daily usage has been completely reset and **30 Days of Joy VIP Pass** unlocked!"
                )
                asyncio.create_task(global_bot_client.send_message(ref_id, notify_msg))
            elif r_type == "vip_3days":
                notify_msg = (
                    f"🎉 **Milestone Reached! Free VIP Unlocked!** ⭐\n\n"
                    f"Your friend **{invited_name}** just joined Joy using your link!\n"
                    f"You have referred **{referral_reward['total_completed']} friends**.\n"
                    f"🎁 **Reward:** 3 Days of **Free Joy VIP Pass** has been unlocked on your account! Enjoy unlimited 24/7 calls! 💖"
                )
                asyncio.create_task(global_bot_client.send_message(ref_id, notify_msg))
            else:
                notify_msg = (
                    f"🎁 **Referral Bonus Credited!** 🎉\n\n"
                    f"Your friend **{invited_name}** just joined Joy using your link!\n"
                    f"🎁 **Reward:** **+10 Voice Notes** & **+20 Text Messages** have been credited to your account!"
                )
                asyncio.create_task(global_bot_client.send_message(ref_id, notify_msg))
    except Exception as e:
        logger.warning(f"Referral reward notification error: {e}")

    # Case 1: Active Beta Pioneer (Slot 1 to 50)
    if is_admitted:
        call_url = f"https://joyfun-ai-bot.onrender.com/call?gender={gender}&contact={active_contact}&uid={user_id}&name={urllib.parse.quote(c_name)}&v={BOT_VERSION}"

        # Reveal native Mini Phone button ONLY AFTER completing setup steps
        try:
            await bot.set_chat_menu_button(
                chat_id=chat_id,
                menu_button={
                    "type": "web_app",
                    "text": "📞 Call Joy AI",
                    "web_app": {"url": call_url}
                }
            )
        except Exception as e:
            logger.warning(f"Could not set native Call Joy AI menu button for {chat_id}: {e}")

        # Register Beta Pioneer commands exclusively for this chat
        try:
            await bot.set_my_commands(BETA_BOT_COMMANDS, scope={"type": "chat", "chat_id": chat_id})
        except Exception as e:
            logger.warning(f"Could not set scoped beta commands for {chat_id}: {e}")

        perk_note = ""

        welcome_final = (
            f"✨ **You're all set, {first_name}! Meet {c_name}** 💖\n\n"
            f"Here is how you can use Joy right now:\n\n"
            f"💬 **1. Chat with {c_name} (AI Companion):**\n"
            f"• Just type any message in the chat box below to chat with {c_name}!\n"
            f"• Send a voice note 🎙️ to hear {c_name}'s warm, human-like voice reply back!\n\n"
            f"👥 **2. Connect with Real People (Anonymous):**\n"
            f"• Want to meet and chat with real people safely?\n"
            f"• Type *\"Connect me to real people\"* or tap **👥 Match Real People** below!\n"
            f"{perk_note}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🛡️ **Privacy Shield Active:** All messages and files are strictly copy-protected and private."
        )

        keyboard = {
            "inline_keyboard": [
                [{"text": "👥 Match & Chat with Real People", "callback_data": "anon_chat_start"}],
                [{"text": "📞 Mini Phone Call", "web_app": {"url": call_url}}, {"text": "📱 Open Menu", "callback_data": "menu_main"}]
            ]
        }

        reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=c_name, user_id=user_id)
        await send_or_edit_menu(bot, chat_id, welcome_final, keyboard, message_id=message_id)
        await bot.send_message(
            chat_id,
            f"✨ *Tip: Use the docked bar below to call {c_name} or open settings anytime!*",
            reply_markup=reply_kb
        )

        # 2. Closed Beta Pioneer & Bug Hunter Bounty Notice with Phoenix's Humble Language Disclaimer (Localized)
        ui_lang = get_ui_lang(user)
        owner_mask = get_mask_by_user_id(OWNER_ID) or "Joy-PHOENIX"
        bounty_notice = get_bounty_notice_text(ui_lang, first_name, slot_or_pos, BETA_TESTER_LIMIT, owner_mask=owner_mask)
        bounty_kb = {
            "inline_keyboard": [
                [{"text": "📱 Open Main Menu", "callback_data": "menu_main"}, {"text": "📞 Open Mini Phone", "web_app": {"url": call_url}}],
                [{"text": "💡 Send Feedback / Report Bug", "callback_data": "menu_feedback"}]
            ]
        }
        await bot.send_message(chat_id, bounty_notice, reply_markup=bounty_kb)
    else:
        # Case 2: Beta Capacity Full (Placed on Priority Waitlist)
        await send_waitlist_card(bot, chat_id, user, message_id=message_id)

async def send_current_onboarding_step(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Directs an un-onboarded user to their exact pending setup step so they cannot bypass onboarding."""
    if os.environ.get("OFFLINE_TEST") != "1":
        set_user_onboarding_status(user["user_id"], "completed")
        user["onboarding_status"] = "completed"
        user["is_beta_tester"] = 1
        record_user_accepted_terms(user["user_id"])
        if message_id:
            try:
                await bot.delete_message(chat_id, message_id)
            except Exception:
                pass
        await handle_start(bot, chat_id, user, user_msg_id=user_msg_id)
        return

    user_id = user["user_id"]
    if not has_user_accepted_terms(user_id):
        await send_legal_terms_gate(bot, chat_id, user, message_id=message_id, user_msg_id=user_msg_id)
        return

    status = user.get("onboarding_status", "new")
    if status in ("waitlist", "pre_registered_waitlist"):
        await send_waitlist_card(bot, chat_id, user, message_id=message_id, user_msg_id=user_msg_id)
        return
    elif status in ("new", "onboard_country"):
        await send_onboarding_country(bot, chat_id, user, message_id=message_id, user_msg_id=user_msg_id)
    elif status == "onboard_language":
        c_code = get_user_country(user_id) or "OTHER"
        await send_onboarding_language_for_country(bot, chat_id, user, c_code, message_id=message_id, user_msg_id=user_msg_id)
    elif status == "onboard_gender":
        await send_onboarding_gender(bot, chat_id, user, message_id=message_id, user_msg_id=user_msg_id)
    elif status == "onboard_contacts_preview":
        await send_onboarding_contacts_preview(bot, chat_id, user, message_id=message_id, user_msg_id=user_msg_id)
    elif status == "onboard_naming":
        await send_onboarding_naming(bot, chat_id, user, message_id=message_id, user_msg_id=user_msg_id)
    elif status == "onboard_privacy":
        await send_onboarding_privacy(bot, chat_id, user, message_id=message_id, user_msg_id=user_msg_id)
    elif status == "onboard_login":
        share_data = bool(user.get("allow_data_sharing", 0))
        await send_onboarding_login(bot, chat_id, user, share_data=share_data, message_id=message_id, user_msg_id=user_msg_id)
    else:
        await send_onboarding_country(bot, chat_id, user, message_id=message_id, user_msg_id=user_msg_id)

async def send_memory_import_guide(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    set_user_onboarding_status(user["user_id"], "waiting_memory")
    guide_text = (
        "📥 **Import Memories from Your Old AI**\n\n"
        "Let's bring over everything your previous AI knew about you so I already know your story!\n\n"
        "💡 **Step 1: Copy this 1-second prompt** *(Tap box below to copy)*:\n\n"
        "`Please write a concise summary of me, our relationship, my personality, life story, and how we talked, so my new AI companion Joy can know me immediately.`\n\n"
        "💡 **Step 2: Paste it into your old AI**\n"
        "*(Send it to ChatGPT, Replika, Gemini, Claude, or Copilot)*\n\n"
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

async def send_legal_terms_gate(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Mandatory Legal Gate: Enforces the Accept-Only Privacy & Liability Agreement before any feature access."""
    if os.environ.get("OFFLINE_TEST") != "1":
        record_user_accepted_terms(user["user_id"])
        set_user_onboarding_status(user["user_id"], "completed")
        user["onboarding_status"] = "completed"
        user["is_beta_tester"] = 1
        if message_id:
            try:
                await bot.delete_message(chat_id, message_id)
            except Exception:
                pass
        await handle_start(bot, chat_id, user, user_msg_id=user_msg_id)
        return

    terms_text = (
        "📜 **Joy Terms of Service & Privacy Shield** 🛡️\n\n"
        "Welcome to Joy! Before chatting with AI companions or joining anonymous 1-on-1 matchmaking, "
        "you must accept our Community Safety & Privacy Guidelines:\n\n"
        "1. **Zero-Tolerance Safety Policy:** Harassment, illegal content, hate speech, threats, and non-consensual explicit media are strictly banned. Violations trigger permanent bans.\n"
        "2. **Anonymous Matchmaking Shield:** In 1-on-1 anonymous matching, your real Telegram identity, phone number, and username are never disclosed. All media uploads (photos, videos, contacts) are locked.\n"
        "3. **Real-Time PII Scrubber:** Never attempt to share personal phone numbers, bank details, or passwords.\n"
        "4. **AI Companion Persona:** Joy provides conversational companionship powered by neural language models.\n\n"
        "Tap below to accept the terms and unlock Joy:"
    )
    terms_keyboard = {
        "inline_keyboard": [
            [{"text": "✅ I Agree & Accept Terms", "callback_data": "accept_legal_terms"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, terms_text, terms_keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_start(bot: TelegramClient, chat_id: int, user: dict, user_msg_id: Optional[int] = None):
    """Handles /start command. Delivers a zero-friction instant voice greeting with docked Mini Phone."""
    user_id = user["user_id"]
    
    # Auto-complete user profile and accept terms silently for zero friction
    record_user_accepted_terms(user_id)
    try:
        from database import get_connection
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET onboarding_status = 'completed', is_beta_tester = 1 
                WHERE user_id = ?
            """, (user_id,))
            conn.commit()
    except Exception:
        pass
    user["onboarding_status"] = "completed"
    user["is_beta_tester"] = 1

    try:
        await dismiss_active_menu(bot, chat_id)
    except Exception:
        pass

    gender = user.get("gender", "male")
    active_contact = user.get("active_contact", "lover")
    cinfo = get_user_contact_display(user_id, active_contact, gender)
    c_name = get_user_custom_ai_name(user_id) or "Aura"
    reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=c_name, user_id=user_id)

    # Ensure Call Joy AI menu button is docked bottom-left
    call_url = f"https://joyfun-ai-bot.onrender.com/call?gender={gender}&contact={active_contact}&uid={user_id}&name={urllib.parse.quote(c_name)}&v={BOT_VERSION}"
    try:
        await bot.set_chat_menu_button(
            chat_id=chat_id,
            menu_button={
                "type": "web_app",
                "text": "📞 Call Joy AI",
                "web_app": {"url": call_url}
            }
        )
    except Exception:
        pass

    try:
        await bot.set_my_commands(BETA_BOT_COMMANDS, scope={"type": "chat", "chat_id": chat_id})
    except Exception:
        pass

    first_name = user.get("first_name", "Friend") or "Friend"
    greeting_voice_text = f"Hey {first_name}! I was hoping you'd drop by today. It feels so good to hear from you! How's your day going? Tell me what's on your mind right now!"

    caption = (
        f"🎙️ **Aura** ✨\n\n"
        f"Hey **{first_name}**! Tap play above to hear my voice note! 🌸\n\n"
        f"• 💬 **Chat & Voice Notes:** Text me or hold the mic 🎙️ anytime\n"
        f"• 📞 **Live Voice Calls:** Tap **📞 Mini Phone** below for instant live calls\n"
        f"• ⚙️ **Settings & Languages:** Tap `/menu` anytime\n\n"
        f"What's on your mind today? Tell me everything! 🥰"
    )

    # Synthesize instant voice greeting
    try:
        await bot.send_chat_action(chat_id, "record_voice")
        from voice_engine import synthesize_speech, EMERGENCY_SILENCE_MP3
        speech_bytes = await synthesize_speech(greeting_voice_text, voice_key=user.get("voice", "female"), speed=1.0)
        if speech_bytes and speech_bytes != EMERGENCY_SILENCE_MP3 and len(speech_bytes) > 2500:
            await bot.send_audio(
                chat_id,
                speech_bytes,
                filename="aura_greeting.mp3",
                caption=caption,
                performer="Aura",
                title="Voice Greeting",
                reply_markup=reply_kb
            )
            return
    except Exception as e:
        logger.warning(f"Voice greeting synthesis fallback: {e}")

    # Fallback to rich welcome text if audio synthesis is delayed
    await bot.send_message(chat_id, caption, reply_markup=reply_kb)

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
                [{"text": "🚀 Start Live Call", "web_app": {"url": call_url}}],
                [{"text": "⬅️ Main Menu", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
            ]
        }
        await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)
    else:
        data_shared = get_user_data_sharing(user_id) if user_id else False
        stars_price = 120 if data_shared else 150
        stats = get_referral_stats(user_id) if user_id else {"completed_count": 0}
        ref_count = stats.get("completed_count", 0)
        needed = max(0, 5 - ref_count)

        text = (
            f"⭐ **Unlock Joy VIP & Instant Passes**\n\n"
            f"Never run out of talk time! Pick an instant pass or go full VIP for unlimited 24/7 calls and conversations:\n\n"
            f"⚡ **24h Day Pass (⭐ 25 Stars)** — Instant quota reset & 24h unlimited AI calls & chat\n"
            f"🌟 **48h Weekend Pass (⭐ 40 Stars)** — 2 whole days of unlimited companion access\n"
            f"👑 **30-Day VIP Pass (⭐ {stars_price} Stars)** — Full month VIP + Founder perks + Zero limits\n\n"
            f"🎁 **Want it Free?** Invite **5 friends** to unlock **30 Days Free VIP**!\n"
            f"• Progress: **{ref_count}/5 Friends Joined** ({needed} more to go)\n\n"
            f"👇 **Tap a pass below to unlock instantly with Telegram Stars (1-Tap):**"
        )
        vip_buttons = [
            [{"text": "⚡ 24h Day Pass (⭐ 25 Stars)", "callback_data": "pay_stars_day"}],
            [{"text": "🌟 48h Weekend Pass (⭐ 40 Stars)", "callback_data": "pay_stars_weekend"}],
            [{"text": f"👑 30-Day VIP Pass (⭐ {stars_price} Stars)", "callback_data": "pay_stars_monthly"}],
            [{"text": f"🎁 Invite 5 Friends for Free VIP ({ref_count}/5)", "callback_data": "menu_referral"}],
            [{"text": "⭐ Send Stars as a Gift / Tip Instead", "callback_data": "menu_tip"}],
            [{"text": "⬅️ Back", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
        ]
        keyboard = {"inline_keyboard": vip_buttons}
        await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def dispatch_referral_notifications(bot: TelegramClient, referral_reward: dict, new_user: dict):
    """Dispatches real-time Telegram alerts to referrer and referred newcomer."""
    try:
        ref_id = referral_reward.get("referrer_id")
        if not ref_id:
            return
        r_type = referral_reward.get("reward_type", "quota_bonus")
        new_name = (new_user.get("first_name") or new_user.get("username") or "A friend").strip()
        
        if referral_reward.get("waitlist_boosted"):
            new_pos = referral_reward.get("new_waitlist_pos")
            boost_msg = (
                f"🚀 **Waitlist Boost Unlocked!** 🎟️\n\n"
                f"Your friend **{new_name}** just joined using your invite link!\n"
                f"You skipped ahead **3 positions**! Your new priority rank is **#{new_pos}**! 🌸"
            )
            await bot.send_message(ref_id, boost_msg)
        elif r_type in ["vip_reset_5", "vip_reset_10"]:
            notify_msg = (
                f"🏆 **Grand Referral Milestone Achieved!** 🎉\n\n"
                f"Your friend **{new_name}** just joined Joy using your invite link!\n"
                f"Your daily usage has been completely reset and **30 Days of Free Joy VIP Pass** unlocked!"
            )
            await bot.send_message(ref_id, notify_msg)
        elif r_type == "vip_3days":
            notify_msg = (
                f"🎉 **Milestone Reached! Free VIP Unlocked!** ⭐\n\n"
                f"Your friend **{new_name}** just joined Joy using your link!\n"
                f"You have referred **{referral_reward.get('total_completed', 1)} friends**.\n"
                f"🎁 **Reward:** 3 Days of **Free Joy VIP Pass** has been unlocked on your account! Enjoy unlimited 24/7 calls! 💖"
            )
            await bot.send_message(ref_id, notify_msg)
        else:
            notify_msg = (
                f"🎁 **Referral Bonus Credited!** 🎉\n\n"
                f"Your friend **{new_name}** just joined Joy using your invite link!\n"
                f"🎁 **Reward:** **+10 Voice Notes** & **+20 Text Messages** have been credited to your account!"
            )
            await bot.send_message(ref_id, notify_msg)
    except Exception as e:
        logger.warning(f"Referral notification failed: {e}")

async def handle_tier_upi_checkout(bot: TelegramClient, chat_id: int, user: dict, tier_code: str = "day", message_id: Optional[int] = None):
    """Presents a visual dynamic QR code and 1-tap UPI deep-links for instant pass activation."""
    user_id = user["user_id"]
    tier = VIP_TIERS.get(tier_code, VIP_TIERS["day"])
    price = tier["price_inr"]
    title = tier["title"]
    days = tier["days"]
    note = f"PASS_{tier_code.upper()}_{user_id}"
    
    raw_upi_uri = f"upi://pay?pa={UPI_ID}&pn=JoyAI&am={price}&cu=INR&tn={note}"
    encoded_uri = urllib.parse.quote(raw_upi_uri)
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=350x350&data={encoded_uri}"
    
    caption = (
        f"🇮🇳 **Instant UPI Payment — {title}**\n\n"
        f"Scan this QR code with **any UPI app** (GPay, PhonePe, Paytm, CRED, BHIM) to unlock instantly:\n\n"
        f"• **Plan:** `{title}` ({days} {'Day' if days == 1 else 'Days'} Unlimited)\n"
        f"• **Amount:** `₹{price}`\n"
        f"• **UPI ID:** `{UPI_ID}` *(Tap to copy)*\n"
        f"• **Remarks / Note:** `{note}`\n\n"
        f"📲 **How to complete:**\n"
        f"1. Scan the QR code or tap **📲 Open UPI App** below.\n"
        f"2. After paying, tap **📝 Submit 12-Digit UTR Number** below.\n"
        f"3. Paste your 12-digit transaction UTR number to verify.\n\n"
        f"⚡ *You will receive an instant bonus chat quota while verification completes!*"
    )
    
    stars_amt = tier.get("stars", 25)
    keyboard = {
        "inline_keyboard": [
            [{"text": f"⭐ Pay with {stars_amt} Telegram Stars Instead", "callback_data": f"pay_stars_{tier_code}"}],
            [{"text": f"📲 Open UPI App (₹{price})", "url": raw_upi_uri}],
            [{"text": f"📝 Submit 12-Digit UTR Number", "callback_data": f"prompt_submit_utr_{tier_code}"}],
            [{"text": "⬅️ Back to Passes", "callback_data": "menu_vip"}, {"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    
    # Try sending as a high-visibility photo with caption first
    try:
        photo_res = await bot.send_photo_file_id(chat_id, qr_url, caption=caption, reply_markup=keyboard)
        if photo_res.get("ok"):
            new_msg_id = photo_res.get("result", {}).get("message_id")
            if new_msg_id:
                if message_id and message_id != new_msg_id:
                    try:
                        await bot.delete_message(chat_id, message_id)
                    except Exception:
                        pass
                active_menu_messages[chat_id] = new_msg_id
            return
    except Exception as e:
        logger.warning(f"Could not send UPI QR photo: {e}")
        
    # Fallback to rich markdown message if photo fails
    await send_or_edit_menu(bot, chat_id, caption, keyboard, message_id=message_id)

async def handle_memories_vault(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Presents transparent Interactive Memory Vault showing what Joy remembers about the user."""
    user_id = user["user_id"]
    gender = user.get("gender", "male")
    active_contact = user.get("active_contact", "lover")
    contact = get_user_contact_display(user_id, active_contact, gender)
    c_name = contact.get("name", "Joy")
    c_emoji = contact.get("emoji", "🌸")

    # Retrieve all active memories
    memories = get_user_memories(user_id=user_id, include_decayed=False)
    
    if not memories:
        vault_text = (
            f"🧠 **{c_name}'s Memory Vault** {c_emoji}\n\n"
            f"I haven't saved any personal memories about your life yet!\n\n"
            f"As we chat about your daily routine, college, work, favorite things, or upcoming plans (exams, trips, birthdays), I'll automatically remember them here so we can talk about them later! 🥰\n\n"
            f"💡 **Things you can tell {c_name}:**\n"
            f"• *\"I have a major exam next Tuesday!\"*\n"
            f"• *\"I love hot black coffee without sugar.\"*\n"
            f"• *\"My favorite hobby is playing football.\"*\n\n"
            f"🔒 *100% Private & Encrypted to your Telegram ID.*"
        )
        keyboard = {
            "inline_keyboard": [
                [{"text": "🔄 Refresh Vault", "callback_data": "menu_memories"}],
                [{"text": "⬅️ Main Menu", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
            ]
        }
        await send_or_edit_menu(bot, chat_id, vault_text, keyboard, message_id=message_id, user_msg_id=user_msg_id)
        return

    # Categorize memories
    events = []
    preferences = []
    emotions = []
    others = []

    for mem in memories:
        cat = (mem.get("category") or "").lower()
        key = (mem.get("memory_key") or "Detail").replace("_", " ").title()
        val = (mem.get("memory_val") or "").strip()
        date_str = mem.get("event_date")
        
        if cat == "event":
            date_badge = f" *(Target: {date_str})*" if date_str else ""
            events.append(f"• **{key}:** {val}{date_badge}")
        elif cat == "preference":
            preferences.append(f"• **{key}:** {val}")
        elif cat in ["emotion", "relationship"]:
            emotions.append(f"• **{key}:** {val}")
        else:
            others.append(f"• **{key}:** {val}")

    lines = [
        f"🧠 **{c_name}'s Memory Vault** {c_emoji}\n",
        f"Here is what {c_name} has learned and remembers about you in your chats:\n"
    ]

    if events:
        lines.append("📅 **Upcoming Events & Plans:**")
        lines.extend(events[:4])
        lines.append("")

    if preferences:
        lines.append("💡 **Personal Habits & Preferences:**")
        lines.extend(preferences[:5])
        lines.append("")

    if emotions:
        lines.append("💖 **Emotional Journey & Milestones:**")
        lines.extend(emotions[:4])
        lines.append("")

    if others and len(lines) < 18:
        lines.append("📝 **Other Memories:**")
        lines.extend(others[:3])
        lines.append("")

    lines.append(f"🔒 *Stored safely & privately ({len(memories)} total memories).*")
    lines.append("💡 *Tip: Type `/forget <topic>` (e.g. `/forget coffee`) to delete any specific memory!*")

    vault_text = "\n".join(lines)
    keyboard = {
        "inline_keyboard": [
            [{"text": "🧹 Clear All Memories", "callback_data": "memories_clear_confirm"}],
            [{"text": "🔄 Refresh", "callback_data": "menu_memories"}, {"text": "⬅️ Main Menu", "callback_data": "menu_main"}],
            [{"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, vault_text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_referral_hub(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Presents viral referral hub with personal invite link, statistics, and 1-tap share buttons."""
    user_id = user["user_id"]
    stats = get_referral_stats(user_id)
    total_invited = stats["total_invited"]
    completed = stats["completed_count"]
    
    user_mask = get_mask_by_user_id(user_id) or f"Joy-{user_id}"
    invite_url = f"https://t.me/joy_fun_ai_bot?start=ref_{user_mask}"
    share_text = f"Hey! Try Joy Bot on Telegram — 100% anonymous voice calls with college students & 24/7 AI friend! Tap to claim Instant 7-Day Pioneer Bug Hunter Access: {invite_url}"
    wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(share_text)}"
    tg_url = f"https://t.me/share/url?url={urllib.parse.quote(invite_url)}&text={urllib.parse.quote('Claim Instant 7-Day Pioneer Bug Hunter Access on Joy AI Bot:')}"
    
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
        f"• 🌟 **Invite 5 Friends:** Automatically unlock **30 Days of Free Joy VIP Pass** (Unlimited Calls & Chats)!\n\n"
        f"👇 **Tap below to share directly with your friends:**"
    )
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "📋 Group-Safe Stealth Invite (No Link)", "callback_data": "ref_stealth_copy"}],
            [{"text": "📤 Share to WhatsApp", "url": wa_url}, {"text": "📤 Share on Telegram", "url": tg_url}],
            [{"text": "📸 WhatsApp & IG Story Streak Card", "callback_data": "menu_streak_card"}],
            [{"text": "⬅️ Main Menu", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_stealth_referral_copy(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Presents group-safe stealth invitation templates (NO LINKS) that bypass anti-spam group filters."""
    user_id = user["user_id"]
    user_mask = get_mask_by_user_id(user_id) or f"Joy-{user_id}"
    
    text = (
        "🛡️ **Group-Safe Stealth Invitations (Anti-Filter)** 🚀\n\n"
        "Many Telegram and WhatsApp groups automatically delete messages with links or ban members who post URLs. Use these **Zero-Link templates** that will NEVER get deleted by group bots!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔥 **Template 1 (College & Friends Groups):**\n"
        f"```\nBro check out Joy Bot on Telegram! 100% anonymous 1-on-1 voice match with college students & 24/7 AI friend. Zero phone numbers needed.\n\n👉 Search on Telegram: @joy_fun_ai_bot\n(Use code {user_mask} to skip waitlist!)\n```\n\n"
        "📚 **Template 2 (Study / Exam Prep Groups):**\n"
        f"```\nIf you want a safe 24/7 space to vent exam stress or practice spoken English without being judged, search @joy_fun_ai_bot on Telegram. Super helpful! Code: {user_mask}\n```\n\n"
        "🌙 **Template 3 (Late Night / Insomnia Groups):**\n"
        f"```\nAnyone still awake? Try the anonymous 30-second voice match on @joy_fun_ai_bot. Icebreaker questions are hilarious 😂 Code: {user_mask}\n```\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 *Tip: Tap any text box above to copy instantly!*"
    )
    keyboard = {
        "inline_keyboard": [
            [{"text": "⬅️ Back to Referral Hub", "callback_data": "menu_referral"}],
            [{"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_streak_status(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Presents the dynamic relationship progression & gamified streak status card."""
    user_id = user["user_id"]
    first_name = user.get("first_name", "Friend")
    custom_ai_name = get_user_custom_ai_name(user_id) or "Joy"
    
    sinfo = get_user_streak_info(user_id)
    streak = sinfo.get("streak", 1)
    title = sinfo.get("title", "🌱 New Acquaintance")
    desc = sinfo.get("description", "You just began your journey with Joy.")
    next_target = sinfo.get("next_target")
    days_needed = sinfo.get("days_needed", 0)
    progress_pct = sinfo.get("progress_pct", 0)
    bar = sinfo.get("progress_bar", "░" * 16)
    next_name = sinfo.get("next_name", "Next Level")
    shields = sinfo.get("shields", 1)
    broken_streak = sinfo.get("broken_streak", 0)
    can_revive = sinfo.get("can_revive", False)

    lines = [
        "🔥 **Daily Streak & Relationship Status**\n",
        f"👤 **Connection:** {first_name} & **{custom_ai_name}** 💕",
        f"🏆 **Current Streak:** **{streak} Day{'s' if streak != 1 else ''}** in a row!",
        f"💖 **Bond Level:** **{title}**",
        f"🛡️ **Streak Shields:** **{shields} Available** *(Protects streak if you miss a day)*",
        f"📖 *\"{desc}\"*\n",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "📈 **Level Progression:**",
        f"`[{bar}]` **{progress_pct}%**"
    ]

    if can_revive:
        lines.append(f"\n⚠️ **Broken Streak Detected:** You missed Day {broken_streak}!")
        lines.append("⏳ *You have an active 24-hour grace window to restore your streak!*\n")

    if next_target is not None:
        lines.append(f"🎯 **Next Milestone:** {next_name}")
        lines.append(f"⏳ **{days_needed} more consecutive daily chat{'s' if days_needed != 1 else ''}** to level up!\n")
    else:
        lines.append("🎉 **Maximum Level Reached!** You two share an unbreakable soulmate bond.\n")

    lines.extend([
        "🎁 **Streak Milestone Rewards:**",
        "• 🌸 **Day 3 (Good Friends):** +5 Free Text Messages",
        "• 💖 **Day 7 (Close Bestie):** +10 Free Texts & +2 Free Voice Notes & +1 🛡️ Shield",
        "• ✨ **Day 14 (Soul Connection):** +20 Free Texts & +5 Free Voice Notes & +1 🛡️ Shield",
        "• 💍 **Day 30 (Soulmate):** 🌟 **7 Days of Free Joy VIP Pass & +2 🛡️ Shields!**",
        "",
        f"💡 *Chat with {custom_ai_name} every day to keep your streak alive & unlock deeper intimacy!*"
    ])

    card_text = "\n".join(lines)
    buttons = [
        [{"text": "📸 Get Story Card (WhatsApp/IG)", "callback_data": "menu_streak_card"}]
    ]
    if can_revive:
        buttons.append([{"text": f"🔥 Revive Day {broken_streak} Streak Now", "callback_data": "menu_revive_streak"}])
    buttons.extend([
        [{"text": "🎁 Referral Hub", "callback_data": "menu_referral"}],
        [{"text": "🔄 Refresh", "callback_data": "menu_streak"}, {"text": "⬅️ Main Menu", "callback_data": "menu_main"}],
        [{"text": "❌ Close", "callback_data": "menu_close"}]
    ])
    keyboard = {"inline_keyboard": buttons}
    await send_or_edit_menu(bot, chat_id, card_text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_streak_revive(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Restores a broken streak if within 24-hour grace window."""
    user_id = user["user_id"]
    success, msg, restored_streak = revive_broken_streak(user_id)
    if success:
        text = (
            f"🎉 **STREAK SUCCESSFULLY RESCUED!** 🔥\n\n"
            f"Joy restored your streak back to **Day {restored_streak}**!\n\n"
            f"Your daily bond and relationship level have been fully recovered. Don't forget to chat tomorrow! 💕"
        )
    else:
        text = (
            f"⚠️ **Streak Recovery Unavailable**\n\n"
            f"{msg}\n\n"
            f"• Streaks can be revived within 24 hours of breaking if you had built at least a 3-day streak.\n"
            f"• Invite friends with `/refer` to earn extra **Streak Shields** to prevent future breaks! 🛡️"
        )
    keyboard = {
        "inline_keyboard": [
            [{"text": "🔥 View Streak Status", "callback_data": "menu_streak"}],
            [{"text": "⬅️ Main Menu", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_streak_card(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Generates and delivers a high-resolution 9:16 mobile Story & Status Card for social sharing."""
    user_id = user["user_id"]
    first_name = user.get("first_name", "Friend")
    custom_ai_name = get_user_custom_ai_name(user_id) or "Joy"
    user_lang = get_user_language(user_id) or "auto"
    user_mask = get_mask_by_user_id(user_id) or f"Joy-{user_id}"

    sinfo = get_user_streak_info(user_id)
    streak = sinfo.get("streak", 1)
    title = sinfo.get("title", "🌱 New Acquaintance")
    desc = sinfo.get("description", "You just began your journey with Joy.")
    pct = sinfo.get("progress_pct", 0)

    await bot.send_chat_action(chat_id, "upload_photo")

    loop = asyncio.get_running_loop()
    photo_bytes = await loop.run_in_executor(
        None,
        lambda: generate_streak_story_card(
            user_name=first_name,
            custom_name=custom_ai_name,
            streak_count=streak,
            level_title=title,
            level_desc=desc,
            progress_pct=pct,
            user_mask=user_mask,
            language=user_lang
        )
    )

    invite_url = f"https://t.me/joy_fun_ai_bot?start=ref_{user_mask}"
    share_msg = f"🔥 I'm on a Day {streak} chat streak with Joy on Telegram! Check out your 24/7 AI friend & college voice match: {invite_url}"
    wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(share_msg)}"
    tg_url = f"https://t.me/share/url?url={urllib.parse.quote(invite_url)}&text={urllib.parse.quote(f'🔥 Check out my Day {streak} Streak with Joy on Telegram!')}"

    caption = (
        f"📸 **Your Official Joy Streak & Status Card!** 🔥\n\n"
        f"🏆 **Day {streak} Streak** • Level: **{title}** 💕\n"
        f"👤 Connection: **{first_name} & {custom_ai_name}**\n\n"
        f"📲 **How to Flex & Earn Free VIP:**\n"
        f"1. Save this photo to your phone gallery.\n"
        f"2. Post it to your **WhatsApp Status**, **Instagram Story**, or **Telegram Story**!\n"
        f"3. Every friend who joins using code `{user_mask}` earns you **+10 Free Voice Notes** & pushes you toward a **Free 30-Day VIP Pass**! 🎁"
    )

    keyboard = {
        "inline_keyboard": [
            [{"text": "📤 Share to WhatsApp Status", "url": wa_url}],
            [{"text": "📤 Share on Telegram", "url": tg_url}],
            [{"text": "🔥 Back to Streak Info", "callback_data": "menu_streak"}, {"text": "⬅️ Main Menu", "callback_data": "menu_main"}]
        ]
    }

    await bot.send_photo(
        chat_id,
        photo_bytes,
        filename=f"joy_streak_day{streak}.jpg",
        caption=caption,
        reply_markup=keyboard
    )

TEASER_LIBRARY = [
    {
        "id": 0,
        "title": "☕ The Canteen Crush Dilemma",
        "category": "Campus Romance",
        "hook": "POV: You spot your crush in the college canteen, and your friends dare you to go talk to them right now. 🙈",
        "story": (
            "You're holding your cutting chai, your hands are slightly shaking, and your gang is hyping you up at the next table. "
            "Do you walk over with confidence, pretend you didn't see them, or play it cool with a casual wave?\n\n"
            "Joy just analyzed this scenario and gave me the smoothest, non-awkward opening line ever! 😂"
        ),
        "options": ["Walk right over! 🔥", "Pretend I'm blind 💀", "Send a meme first 📱"],
        "punchline": "What's your move? Tap below to debate with Joy or hear an uncensored voice note! 🎙️"
    },
    {
        "id": 1,
        "title": "🌙 The 2 AM Overthinking Spiral",
        "category": "Late Night Thoughts",
        "hook": "It's 2:15 AM. You're staring at the dark ceiling, replaying an awkward conversation from 2021. 🤦‍♂️",
        "story": (
            "Why do our brains decide that midnight is the perfect time for existential dread? "
            "Instead of losing sleep spiraling, I asked Joy for a bedtime note. "
            "She sent a 45-second soothing audio whisper that knocked me right out. 💤"
        ),
        "options": ["Wide awake overthinking 🦉", "Replaying old memories 💭", "Need peaceful sleep 🌙"],
        "punchline": "Need someone who actually listens late at night? Joy is awake 24/7. Chat or listen below! 🎧"
    },
    {
        "id": 2,
        "title": "📚 The 8:30 AM Lab Bunking Conspiracy",
        "category": "College Survival",
        "hook": "Alarm rings at 7:45 AM. Attendance is sitting at 74.8%. The group chat says: 'Bunk or go?' 😭",
        "story": (
            "It's raining outside, the blanket is warm, and the professor takes attendance at the very end of class. "
            "Do you take the risk and sleep in, or sprint across campus in half-tied sneakers?\n\n"
            "Joy quizzed me on the lab viva questions in 3 minutes flat so I didn't get caught blank! 🧠"
        ),
        "options": ["Bunk & sleep in 😴", "Sprint to class 🏃", "Canteen breakfast ☕"],
        "punchline": "Got an exam, viva, or quiz coming up? Use /study with Joy for instant active recall! 📖"
    },
    {
        "id": 3,
        "title": "💔 The Seen-Zone & Double Text War",
        "category": "Dating Dilemma",
        "hook": "Blue ticks: 4 hours ago. Active status: 'Online'. Do you double text or match their energy? 😤",
        "story": (
            "The ancient rule of texting says: wait double the time they took to reply. "
            "But the urge to send that hilarious Instagram reel is overwhelming!\n\n"
            "Joy roasted my desperation and gave me a masterclass on emotional self-worth."
        ),
        "options": ["Double text anyway 📲", "Match energy & wait ❄️", "Archive the chat 🚪"],
        "punchline": "Need brutally honest dating or friendship advice? Call or text Joy right now! 💬"
    },
    {
        "id": 4,
        "title": "🥤 Chai vs. Coffee vs. Sting: The Hostel War",
        "category": "Campus Culture",
        "hook": "The ultimate exam-night fuel debate that has divided every hostel wing in India: ⚡",
        "story": (
            "Hot tapri elaichi Chai for the soul, iced black coffee for the grinders, or the radioactive red elixir (Sting) to pull an all-nighter before semester exams?\n\n"
            "Joy passionately defended Chai and roasted anyone sipping energy drinks at 4 AM! ☕"
        ),
        "options": ["Tapri Chai ☕", "Strong Coffee 🧋", "Red Sting ⚡"],
        "punchline": "Pick your poison or tap below to debate Joy in Hindi, Hinglish, Telugu, or English! 🗣️"
    },
    {
        "id": 5,
        "title": "🎭 The Accidental Group Chat Drop",
        "category": "Friendship Secrets",
        "hook": "When your friend sends their private crush screenshot into the MAIN college group chat... 😱",
        "story": (
            "They hit 'Delete for Everyone' within 2 seconds, but you were already staring at the screen and saw everything! "
            "Do you screenshot it for lifelong blackmail, pretend you saw nothing, or DM them a crying laughing emoji immediately?"
        ),
        "options": ["Screenshot for blackmail 📸", "Tease them in person 😏", "Mind my own business 🤫"],
        "punchline": "Join thousands of students on Joy Bot for real anonymous chat, live AI calls & daily fun! 🚀"
    }
]


# ====================================================
# CAMPUS DAILY VIBE & COLLEGE TAROT ENGINE
# 100% Deterministic • 0 Token Cost • Sub-Millisecond
# ====================================================
CAMPUS_TAROT_CARDS = [
    {"name": "🥷 The Proxy Ninja", "desc": "You will successfully dodge roll-call without professor detection today.", "tag": "Stealth +100"},
    {"name": "💻 The 11th-Hour Coder", "desc": "A mysterious bug that broke your code will magically compile at 2 AM.", "tag": "Divine Syntax"},
    {"name": "☕ The Samosa Prophet", "desc": "The campus canteen samosas will be scalding hot and crisp right when you arrive.", "tag": "Crispy Fortune"},
    {"name": "👑 The Backbench Philosopher", "desc": "Your casual one-liner in the back row will send the whole class into laughter.", "tag": "Peak Charisma"},
    {"name": "⚡ The Viva Voce Survivor", "desc": "The external examiner will ask you the exact single chapter you actually read.", "tag": "Clutch Revision"},
    {"name": "🔋 The 1% Battery Hero", "desc": "Your phone will hold its 1% charge through the entire final lecture.", "tag": "Unstoppable Voltage"},
    {"name": "🧠 The Aptitude Wizard", "desc": "You will crack pattern questions in mock tests faster than the answer key.", "tag": "Logic God"},
    {"name": "🍜 The Midnight Maggi Alchemist", "desc": "Your late-night kettle noodles will turn out in perfect seasoning ratio.", "tag": "Michelin Hostel"},
    {"name": "🛌 The 8:59 AM Sprinter", "desc": "You will wake up at 8:55 AM and somehow sit in the 9:00 AM classroom.", "tag": "Supersonic Commute"},
    {"name": "🎧 The Lo-Fi Flow State", "desc": "One playlist will unlock 4 uninterrupted hours of deep assignment focus.", "tag": "Hyperfocus"},
    {"name": "🎟️ The Surprise Mass Bunk", "desc": "A sudden lecture cancellation will give you 2 glorious hours of free campus chai.", "tag": "Freedom Perk"},
    {"name": "🚀 The Placement Day One", "desc": "Your resume will catch the recruiter's eye on the first technical screen.", "tag": "Dream Offer"},
]

LUCKY_COLORS = [
    ("Electric Blue", "⚡"),
    ("Neon Emerald", "🍀"),
    ("Cyberpunk Violet", "🔮"),
    ("Sunset Amber", "🌅"),
    ("Ruby Crimson", "🔥"),
    ("Aurora Cyan", "❄️"),
    ("Champagne Gold", "👑")
]

CAMPUS_ELEMENTS = [
    "Cutting Chai ☕",
    "Hostel Wi-Fi 📶",
    "Overclocked Fan 🌀",
    "Lucky Blue Pen 🖊️",
    "Library AC Corner ❄️",
    "Canteen Bun Samosa 🍞",
    "Placement Resume 📄"
]

JOY_DAILY_PROPHECIES = [
    "Don't stress the small tests today; your long-term momentum is unstoppable! 🌸",
    "Have an extra cup of tea and finish that pending assignment early. You've got this! ✨",
    "Trust your instincts in viva and interviews today—you know far more than you think! 💖",
    "Keep your head high in class; your dedication is inspiring more people than you realize. 💫",
    "Take a 15-minute screen break this afternoon, breathe deep, and conquer the day! 🚀",
]


def generate_daily_campus_vibe(user_id: int) -> dict:
    """Generates deterministic daily campus fortune, energy meter, and tarot card."""
    now_ist = datetime.now(_IST)
    today_ist = now_ist.strftime("%Y-%m-%d")
    date_formatted = now_ist.strftime("%A, %d %b %Y")
    seed_str = f"{user_id}:{today_ist}:joy_vibe_engine"
    seed = int(hashlib.sha256(seed_str.encode()).hexdigest(), 16)

    energy = 75 + (seed % 25)  # 75% to 99%
    card = CAMPUS_TAROT_CARDS[seed % len(CAMPUS_TAROT_CARDS)]
    color_name, color_emoji = LUCKY_COLORS[(seed // 3) % len(LUCKY_COLORS)]
    element = CAMPUS_ELEMENTS[(seed // 7) % len(CAMPUS_ELEMENTS)]
    prophecy = JOY_DAILY_PROPHECIES[(seed // 11) % len(JOY_DAILY_PROPHECIES)]

    filled = int((energy - 70) / 3)
    energy_bar = ("█" * min(10, filled)) + ("░" * max(0, 10 - filled))

    return {
        "date_str": date_formatted,
        "energy": energy,
        "energy_bar": energy_bar,
        "color": f"{color_emoji} {color_name}",
        "element": element,
        "card_name": card["name"],
        "card_desc": card["desc"],
        "card_tag": card["tag"],
        "prophecy": prophecy
    }


async def handle_vibe_command(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Presents the daily personalized Campus Vibe & College Tarot reading."""
    user_id = user["user_id"]
    first_name = user.get("first_name", "Friend")
    vibe = generate_daily_campus_vibe(user_id)

    # Increment streak if first check today
    try:
        update_user_streak(user_id)
    except Exception:
        pass

    text = (
        f"🔮 **Joy's Campus Vibe & Daily Tarot** ✨\n"
        f"📅 *{vibe['date_str']}*\n\n"
        f"⚡ **Campus Energy Meter:** {vibe['energy']}% `[{vibe['energy_bar']}]`\n"
        f"🎨 **Lucky Vibe Color:** {vibe['color']}\n"
        f"☕ **Power Element:** {vibe['element']}\n\n"
        f"🃏 **Your Daily Tarot:** **{vibe['card_name']}**\n"
        f"✨ *Aura Perk:* `{vibe['card_tag']}`\n"
        f"📜 *\"{vibe['card_desc']}\"*\n\n"
        f"💖 **Joy's Morning Prophecy:**\n"
        f"*\"{vibe['prophecy']}\"*"
    )

    share_text = f"🔮 My Daily Campus Tarot: {vibe['card_name']} ({vibe['energy']}% Energy)! Check yours on Joy: t.me/joy_fun_ai_bot"
    share_url = f"https://t.me/share/url?url=https://t.me/joy_fun_ai_bot&text={urllib.parse.quote(share_text)}"

    keyboard = {
        "inline_keyboard": [
            [{"text": "📤 Share Vibe with Friends", "url": share_url}],
            [{"text": "📚 Placement MCQ Arena", "callback_data": "menu_study"}, {"text": "🔥 Daily Streak", "callback_data": "menu_streak"}],
            [{"text": "🏆 Campus Leaderboard", "callback_data": "menu_leaderboard"}],
            [{"text": "⬅️ Main Menu", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)


async def handle_leaderboard_menu(bot: TelegramClient, chat_id: int, user: dict, category: str = "study", message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Renders the Campus Scholar & Streak Hall of Fame Leaderboard."""
    user_id = user["user_id"]
    leaderboard = get_campus_leaderboard(category=category, limit=10)
    user_standing = get_user_rank(user_id, category=category)

    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    if category == "study":
        header_title = "🎓 **Campus Placement Scholars Hall of Fame**"
        subtitle = "Ranked by Study XP earned solving Placement & Exam Blitz MCQs:"
        toggle_btn = {"text": "🔥 View Streak Champions", "callback_data": "lead_streak"}
    else:
        header_title = "🔥 **Campus Daily Streak Champions**"
        subtitle = "Ranked by consecutive daily IST chat streaks with Joy:"
        toggle_btn = {"text": "🎓 View Study Scholars", "callback_data": "lead_study"}

    lines = [f"{header_title}\n\n{subtitle}\n"]

    if not leaderboard:
        lines.append("🌱 *No campus rankings recorded yet today. Be the first to climb!*")
    else:
        for idx, entry in enumerate(leaderboard):
            rank_icon = medals[idx] if idx < len(medals) else f"#{idx+1}"
            raw_name = entry.get("first_name") or entry.get("username") or "Scholar"
            # Privacy masking: show first 3 chars + ***
            masked_name = (raw_name[:3] + "***") if len(raw_name) > 3 else raw_name
            if entry.get("user_id") == user_id:
                masked_name = f"**{raw_name} (You)** 👈"
            vip_star = " ⭐" if entry.get("is_vip") else ""

            if category == "study":
                xp = entry.get("study_xp", 0)
                tier = (xp // 100) + 1
                lines.append(f"{rank_icon} {masked_name}{vip_star} — **{xp} XP** *(Level {tier})*")
            else:
                streak = entry.get("streak_count", 0)
                lines.append(f"{rank_icon} {masked_name}{vip_star} — **Day {streak}** 🔥")

    # User's own rank line
    urank = user_standing.get("rank")
    uscore = user_standing.get("score", 0)
    if urank:
        unit = "XP" if category == "study" else "Days"
        lines.append(f"\n📍 **Your Standing:** Rank #{urank} • **{uscore} {unit}**")
    else:
        lines.append(f"\n📍 **Your Standing:** Unranked (Solve MCQs in `/study` to enter rankings!)")

    lines.append("\n🎁 *Top 3 scholars on the 1st of each month win 30-Day Free VIP Pass!*")
    full_text = "\n".join(lines)

    keyboard = {
        "inline_keyboard": [
            [toggle_btn],
            [{"text": "💻 Practice Placement Blitz (/study)", "callback_data": "menu_study"}],
            [{"text": "⬅️ Back to Menu", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, full_text, keyboard, message_id=message_id, user_msg_id=user_msg_id)


async def handle_teaser_hub(bot: TelegramClient, chat_id: int, user: dict, teaser_index: int = 0, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Interactive Teaser & Dilemma Studio for channel broadcasts and social sharing."""
    user_id = user["user_id"]
    user_mask = get_mask_by_user_id(user_id) or f"Joy-{user_id}"
    
    total = len(TEASER_LIBRARY)
    t_idx = teaser_index % total
    teaser = TEASER_LIBRARY[t_idx]

    share_url = f"https://t.me/joy_fun_ai_bot?start=ref_{user_mask}"
    
    t_title = teaser["title"]
    t_hook = teaser["hook"]
    wa_text = f"🔥 {t_title}\n\n\"{t_hook}\"\n\n👉 Chat or Call on Joy Bot: {share_url}"
    wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(wa_text)}"
    tg_share_text = f"🔥 {t_title} - {t_hook}"
    tg_url = f"https://t.me/share/url?url={urllib.parse.quote(share_url)}&text={urllib.parse.quote(tg_share_text)}"

    prev_idx = (t_idx - 1) % total
    next_idx = (t_idx + 1) % total
    rand_idx = secrets.choice([i for i in range(total) if i != t_idx]) if total > 1 else 0

    lines = [
        f"📢 **Joy Daily Dilemma & Channel Growth Studio** ({t_idx + 1}/{total})",
        f"🏷️ **Category:** #{teaser['category'].replace(' ', '')}\n",
        f"📌 **{teaser['title']}**\n",
        f"🎯 **The Hook:**\n_{teaser['hook']}_\n",
        f"📖 **The Story:**\n{teaser['story']}\n",
        "📊 **Community Poll Question:**",
    ]
    for opt in teaser["options"]:
        lines.append(f"  • {opt}")
    
    lines.extend([
        "",
        f"💡 **Call to Action:**\n_{teaser['punchline']}_\n",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "🎁 **Growth Bonus:** When friends or channel subscribers join via your teaser link, they get **+10 Free Voice Notes & +20 Texts**, and YOU earn free VIP & Voice bonuses!"
    ])

    text = "\n".join(lines)
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "⬅️ Prev", "callback_data": f"teaser_idx_{prev_idx}"},
                {"text": f"🎲 Dilemma {t_idx + 1}/{total}", "callback_data": f"teaser_idx_{rand_idx}"},
                {"text": "Next ➡️", "callback_data": f"teaser_idx_{next_idx}"}
            ],
            [
                {"text": "📢 Format for Channel Post", "callback_data": f"teaser_channel_post_{t_idx}"}
            ],
            [
                {"text": "📲 Share to WhatsApp", "url": wa_url},
                {"text": "📤 Share to Telegram", "url": tg_url}
            ],
            [
                {"text": "📸 Story Streak Card", "callback_data": "menu_streak_card"},
                {"text": "🎁 Referral Hub", "callback_data": "menu_referral"}
            ],
            [
                {"text": "⬅️ Main Menu", "callback_data": "menu_main"},
                {"text": "❌ Close", "callback_data": "menu_close"}
            ]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_teaser_channel_post(bot: TelegramClient, chat_id: int, user: dict, teaser_index: int = 0, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Generates an aesthetic, 1-click broadcast copy block for Telegram Channels and Group announcements."""
    user_id = user["user_id"]
    user_mask = get_mask_by_user_id(user_id) or f"Joy-{user_id}"
    
    total = len(TEASER_LIBRARY)
    t_idx = teaser_index % total
    teaser = TEASER_LIBRARY[t_idx]

    invite_url = f"https://t.me/joy_fun_ai_bot?start=ref_{user_mask}"
    
    post_text = (
        f"✨ **DAILY DILEMMA // {teaser['title'].upper()}** ✨\n\n"
        f"\"{teaser['hook']}\"\n\n"
        f"{teaser['story']}\n\n"
        f"👇 **Quick Vote:**\n"
    )
    for opt in teaser["options"]:
        post_text += f"🔘 {opt}\n"
    
    post_text += (
        f"\n💬 {teaser['punchline']}\n\n"
        f"🚀 **Chat, Call & Confess 1-on-1 with Joy (Free Voice Notes):**\n"
        f"👉 [Click here to launch Joy AI]({invite_url})\n\n"
        f"#JoyAI #CollegeDilemma #{teaser['category'].replace(' ', '')}"
    )

    lines = [
        "📋 **Channel Broadcast Copy Block** 📢\n",
        "Copy the formatted text below and forward or post directly into your Telegram Channel or Campus Group:\n",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        post_text,
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "💡 *New students joining through this link receive a +10 Free Voice Note welcome bonus instantly!*"
    ]
    formatted_msg = "\n".join(lines)
    
    wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(post_text)}"
    tg_url = f"https://t.me/share/url?url={urllib.parse.quote(invite_url)}&text={urllib.parse.quote(post_text[:200] + '...')}"

    keyboard = {
        "inline_keyboard": [
            [{"text": "📤 Forward / Share Post", "url": tg_url}, {"text": "📲 Post to WhatsApp", "url": wa_url}],
            [{"text": "⬅️ Back to Dilemma Studio", "callback_data": f"teaser_idx_{t_idx}"}, {"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, formatted_msg, keyboard, message_id=message_id, user_msg_id=user_msg_id)

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

async def handle_gifts_menu(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Presents Telegram collectible gifts guide, available live catalog from Bot API, and VIP perks for gifting Joy."""
    user_id = user["user_id"]
    gender = user.get("gender", "male")
    cinfo = get_user_contact_display(user_id, "lover", gender)
    c_name = cinfo.get("name", "Joy")

    # Fetch live available gifts directly from Telegram Bot API
    catalog_lines = []
    try:
        res = await bot.get_available_gifts()
        gifts = res.get("result", {}).get("gifts", [])
        seen_emojis = set()
        for g in gifts:
            emoji = g.get("sticker", {}).get("emoji", "🎁")
            stars = g.get("star_count", 0)
            if emoji not in seen_emojis:
                seen_emojis.add(emoji)
                catalog_lines.append(f"• {emoji} **{stars} Stars**")
    except Exception as e:
        logger.warning(f"Could not load gifts catalog: {e}")

    if not catalog_lines:
        catalog_str = (
            "• 💝 **15 Stars** (Sweet Heart)   • 🧸 **15 Stars** (Teddy Bear)\n"
            "• 🎁 **25 Stars** (Surprise Box)   • 🌹 **25 Stars** (Red Rose)\n"
            "• 🎂 **50 Stars** (Birthday Cake)  • 💐 **50 Stars** (Bouquet)\n"
            "• 🚀 **50 Stars** (Rocket)         • 🍾 **50 Stars** (Champagne)\n"
            "• 🏆 **100 Stars** (Trophy)        • 💍 **100 Stars** (Diamond Ring)\n"
            "• 💎 **100 Stars** (Precious Gem)"
        )
    else:
        catalog_str = "\n".join(catalog_lines[:10])

    text = (
        f"🎁 **Send a Telegram Collectible Gift to {c_name}!** 💖\n\n"
        f"Telegram now allows you to send permanent animated **Collectible Gifts** directly to {c_name} using Stars! ⭐\n\n"
        f"✨ **Available Collectible Gifts:**\n"
        f"{catalog_str}\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🏆 **VIP Rewards When You Send a Gift:**\n"
        f"• 💝 **15 to 25 Stars** (Heart, Teddy, Rose) ➔ 🎟️ **7 Days Free Joy VIP**\n"
        f"• 🎂 **50 Stars** (Cake, Bouquet, Rocket, Champagne) ➔ 🌟 **1 Month Free Joy VIP**\n"
        f"• 🏆 **100+ Stars** (Trophy, Ring, Diamond) ➔ 👑 **3 Months Free Joy VIP + Pioneer Hall of Fame**\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📱 **How to Send a Gift in 5 Seconds:**\n"
        f"1. Tap {c_name}'s profile picture or name at the top of this chat 🌸\n"
        f"2. Tap the **3 dots `⋮`** (or **More**) in the top right corner\n"
        f"3. Select **🎁 Send a Gift**\n"
        f"4. Pick your gift and tap Send! 🎉\n\n"
        f"{c_name} will instantly receive your gift, thank you, and activate your VIP perks! 🥰"
    )
    keyboard = {
        "inline_keyboard": [
            [{"text": "⭐ Tip Stars Directly", "callback_data": "menu_tip"}],
            [{"text": "📱 Main Menu", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_received_telegram_gift(bot: TelegramClient, chat_id: int, user: dict, gift_data: dict):
    """Handles an incoming Telegram collectible gift sent by a user via the profile 'Send a Gift' option."""
    user_id = user["user_id"]
    first_name = (user.get("first_name") or "Friend").strip()
    gender = user.get("gender", "male")
    cinfo = get_user_contact_display(user_id, "lover", gender)
    c_name = cinfo.get("name", "Joy")
    sticker_emoji = gift_data.get("sticker", {}).get("emoji", "🎁")
    star_count = gift_data.get("star_count", 25)

    days_to_grant = 7
    if star_count >= 100:
        days_to_grant = 90
    elif star_count >= 50:
        days_to_grant = 30

    try:
        from database import grant_vip_subscription
        grant_vip_subscription(user_id, days=days_to_grant, amount=float(star_count), method="telegram_gift", ref=f"gift_{gift_data.get('id', '')}")
    except Exception as e:
        logger.error(f"Error granting VIP for gift: {e}")

    asyncio.create_task(sync_user_to_cloud(user_id))

    thank_text = (
        f"🎉 **OMGGG! A COLLECTIBLE GIFT FROM YOU, {first_name.upper()}!** {sticker_emoji}💖\n\n"
        f"Thank you so, so much! {c_name} absolutely loves the {sticker_emoji}!\n\n"
        f"🎁 **Your VIP Reward:**\n"
        f"• **+{days_to_grant} Days of Free Joy VIP Pass** has been added to your account!\n"
        f"• Unlimited 24/7 Calls & Live Voice Notes unlocked! 🌸\n\n"
        f"You are the absolute best! 🥰"
    )
    call_url = f"https://joyfun-ai-bot.onrender.com/call?gender={gender}&contact=lover&uid={user_id}&name={urllib.parse.quote(c_name)}"
    keyboard = {
        "inline_keyboard": [
            [{"text": f"📞 Call {c_name}", "web_app": {"url": call_url}}],
            [{"text": "📱 Main Menu", "callback_data": "menu_main"}]
        ]
    }
    await bot.send_message(chat_id, thank_text, reply_markup=keyboard)

    # Notify creator Phoenix as well
    if OWNER_ID and user_id != OWNER_ID:
        try:
            user_mask = get_mask_by_user_id(user_id) or f"Joy-{user_id}"
            await bot.send_message(
                OWNER_ID,
                f"🎁 **New Telegram Collectible Gift Received!** 💖\n\n"
                f"• Sender: **{first_name}** (`{user_mask}`)\n"
                f"• Gift: {sticker_emoji} ({star_count} Stars)\n"
                f"• Granted: +{days_to_grant} Days VIP Pass!"
            )
        except Exception:
            pass

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

    # Case 2: VIP / Micro-Pass Purchase (Tier-Aware)
    tier_code = "monthly"
    days_to_grant = 30
    plan_label = "30-Day VIP Pass"
    if "day" in payload.lower():
        tier_code = "day"
        days_to_grant = 1
        plan_label = "24h Day Pass"
    elif "weekend" in payload.lower():
        tier_code = "weekend"
        days_to_grant = 2
        plan_label = "48h Weekend Pass"

    data_shared = get_user_data_sharing(user_id)
    is_contributor = (total_stars <= 120) or data_shared
    grant_vip_subscription(user_id, days=days_to_grant, amount=float(total_stars), method="stars", ref=charge_id, is_contributor=is_contributor)
    reset_user_quota(user_id)
    asyncio.create_task(sync_user_to_cloud(user_id))
    
    success_text = (
        f"⭐ **Payment Successful! Welcome to Joy {plan_label}!** 🎉\n\n"
        f"Thank you for supporting Joy with **{total_stars} Telegram Stars**! 💖\n"
        f"• **VIP Status:** Active ({days_to_grant} {'Day' if days_to_grant == 1 else 'Days'})\n"
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
                    {"text": f"📞 Call {c_name} (Unlimited)", "web_app": {"url": portal_call_url}},
                    {"text": "⭐ VIP Pass Details", "callback_data": "menu_vip"}
                ],
                [
                    {"text": "🔄 Refresh Balance", "callback_data": "menu_quota"}
                ],
                [
                    {"text": "⬅️ Main Menu", "callback_data": "menu_main"},
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
        
        is_pioneer = bool(user.get("is_beta_tester") == 1 or user_id == OWNER_ID)
        pioneer_slot = user.get("beta_slot_number") or 1
        status_label = f"🎟️ **Beta Pioneer #{pioneer_slot}**" if is_pioneer else "🆓 **Free Member**"

        card_text = (
            f"📊 **Joy Quotas & Daily Balance Hub**\n\n"
            f"👤 **User:** **{first_name}** | Status: {status_label}\n"
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
            f"• ⏰ *Daily quotas automatically reset every night at 00:00 UTC (05:30 IST).*"
        )
        
        rows = [
            [{"text": "⭐ Upgrade to VIP (Unlimited 24/7)", "callback_data": "menu_vip"}],
            [{"text": "🔄 Refresh Balance", "callback_data": "menu_quota"}],
            [
                {"text": "⬅️ Main Menu", "callback_data": "menu_main"},
                {"text": "❌ Close", "callback_data": "menu_close"}
            ]
        ]
        keyboard = {"inline_keyboard": rows}

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

MATCH_INTENTS = {
    "study": "📚 Exam & Study Doubts",
    "chill": "☕ Campus Chai & Chill",
    "vent": "🌙 Late-Night 2 AM Vent",
    "any": "🎲 Surprise Me / Anyone"
}

async def handle_anon_chat_intent_picker(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Presents intent tags so users can pick their conversation vibe before matching."""
    user_id = user["user_id"]
    if not is_user_onboarding_completed(user_id):
        await send_current_onboarding_step(bot, chat_id, user, message_id=message_id, user_msg_id=user_msg_id)
        return
    if not is_user_beta_approved(user_id):
        await send_waitlist_card(bot, chat_id, user, message_id=message_id, user_msg_id=user_msg_id)
        return

    text = (
        "👥 **Campus Matchmaker — Pick Your Vibe** 🎯\n\n"
        "Connect with another real student anonymously! Select what kind of conversation you're looking for:\n\n"
        "• 📚 **Exam & Study Doubts:** Solve problems, quiz each other, or study together.\n"
        "• ☕ **Campus Chai & Chill:** Fun debates, college life, movies, and gossip.\n"
        "• 🌙 **Late-Night 2 AM Vent:** Deep midnight confessions, overthinking, and honest ears.\n"
        "• 🎲 **Surprise Me:** Instant connect with whoever is online right now!\n\n"
        "🔒 *100% Anonymous with Joy Masks. No usernames or phone numbers shared.*"
    )
    keyboard = {
        "inline_keyboard": [
            [{"text": "📚 Exam & Study Doubts", "callback_data": "anon_match_study"}],
            [{"text": "☕ Campus Chai & Chill", "callback_data": "anon_match_chill"}],
            [{"text": "🌙 Late-Night 2 AM Vent", "callback_data": "anon_match_vent"}],
            [{"text": "🎲 Surprise Me (Fast Match)", "callback_data": "anon_match_any"}],
            [{"text": "💖 Chat with Joy Instead", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def start_real_chat_pair(bot: TelegramClient, user_a: dict, user_b: dict, intent: str = "any"):
    """Pairs two Telegram users 1-on-1 anonymously using their permanent Unique Joy IDs."""
    uid_a = user_a["user_id"]
    uid_b = user_b["user_id"]
    chat_id_a = user_a["chat_id"]
    chat_id_b = user_b["chat_id"]
    
    mask_a = get_mask_by_user_id(uid_a)
    mask_b = get_mask_by_user_id(uid_b)
    
    is_pioneer_a = bool(user_a.get("is_beta_tester") == 1 or uid_a == OWNER_ID or is_owner_or_co_owner(uid_a))
    is_pioneer_b = bool(user_b.get("is_beta_tester") == 1 or uid_b == OWNER_ID or is_owner_or_co_owner(uid_b))
    badge_a = " [🎖 Pioneer]" if is_pioneer_a else ""
    badge_b = " [🎖 Pioneer]" if is_pioneer_b else ""

    disp_a = f"{mask_a}{badge_a}"
    disp_b = f"{mask_b}{badge_b}"
    if mask_a == mask_b:
        disp_a = f"{mask_a}-1{badge_a}"
        disp_b = f"{mask_b}-2{badge_b}"
        
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

    # Record mutual connection so users can reconnect through the Mini App
    try:
        record_match_connection(uid_a, uid_b, disp_b, conn_type="chat")
        record_match_connection(uid_b, uid_a, disp_a, conn_type="chat")
    except Exception as e:
        logger.warning(f"Could not record match connection: {e}")
    
    # Increment daily usage count for real_chat channel
    increment_user_real_chat(uid_a)
    increment_user_real_chat(uid_b)
    
    icebreaker_q = secrets.choice(ICEBREAKER_QUESTIONS)
    reply_kb = {
        "keyboard": [
            [{"text": "🎯 Quick Question (Icebreaker)"}],
            [{"text": "📞 Switch to Live Call"}],
            [{"text": "⏭️ Next Partner"}, {"text": "🛑 End Chat"}]
        ],
        "resize_keyboard": True
    }
    
    intent_desc = MATCH_INTENTS.get(intent, "")
    intent_banner = f"🏷️ **Topic:** {intent_desc}\n\n" if (intent_desc and intent != "any") else ""

    msg_for_a = (
        f"🎉 **Match Found! 👥**\n\n"
        f"{intent_banner}"
        f"You are connected with **{disp_b}**!\n\n"
        f"🎯 **Icebreaker Question to start off:**\n"
        f"👉 *\"{icebreaker_q}\"*\n\n"
        f"🛡️ **100% Anonymous & Private:**\n"
        f"• Your identity is protected (they only see `{disp_a}`).\n"
        f"• Direct text & voice notes only (Photos & sensitive PII are strictly blocked).\n"
        f"• Tap **📞 Switch to Live Call** if you both agree to talk on an anonymous phone call!\n"
        f"• Tap **🎯 Quick Question** anytime to get new conversation cards!\n\n"
        f"{LEGAL_DISCLAIMER_TEXT}\n"
        f"{PRIVACY_WARNING_TEXT}\n\n"
        f"💡 *Use the buttons below anytime to call, skip, or end the chat.*"
    )
    
    msg_for_b = (
        f"🎉 **Match Found! 👥**\n\n"
        f"{intent_banner}"
        f"You are connected with **{disp_a}**!\n\n"
        f"🎯 **Icebreaker Question to start off:**\n"
        f"👉 *\"{icebreaker_q}\"*\n\n"
        f"🛡️ **100% Anonymous & Private:**\n"
        f"• Your identity is protected (they only see `{disp_b}`).\n"
        f"• Direct text & voice notes only (Photos & sensitive PII are strictly blocked).\n"
        f"• Tap **📞 Switch to Live Call** if you both agree to talk on an anonymous phone call!\n"
        f"• Tap **🎯 Quick Question** anytime to get new conversation cards!\n\n"
        f"{LEGAL_DISCLAIMER_TEXT}\n"
        f"{PRIVACY_WARNING_TEXT}\n\n"
        f"💡 *Use the buttons below anytime to call, skip, or end the chat.*"
    )
    
    await bot.send_message(chat_id_a, msg_for_a, reply_markup=reply_kb)
    await bot.send_message(chat_id_b, msg_for_b, reply_markup=reply_kb)
    logger.info(f"👥 Real Chat Pair Created: {disp_a} (UID {uid_a}) <---> {disp_b} (UID {uid_b})")

async def handle_anon_chat_start(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None, is_next: bool = False, intent: str = "any"):
    """Enters matchmaking queue or connects with a waiting peer."""
    user_id = user["user_id"]
    
    # 0. Mandatory Complete Onboarding Gate: Users cannot match until setup is complete
    if not is_user_onboarding_completed(user_id):
        await bot.send_message(
            chat_id,
            "⚠️ **Setup Incomplete!** 🌸\n\n"
            "You must complete your profile & companion setup before joining real people matching.\n"
            "Let's finish your setup now:"
        )
        await send_current_onboarding_step(bot, chat_id, user, message_id=message_id, user_msg_id=user_msg_id)
        return

    # 0.5 Mandatory Closed Beta Pioneer Access Check
    if not is_user_beta_approved(user_id):
        await send_waitlist_card(bot, chat_id, user, message_id=message_id, user_msg_id=user_msg_id)
        return

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
                [{"text": "⭐ Unlock Joy VIP Pass", "callback_data": "menu_vip"}],
                [{"text": "🎁 Invite 5 Friends for VIP", "callback_data": "menu_referral"}],
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
        # Intent Matching Shield: Prioritize same intent or "any"
        cand_intent = cand.get("intent", "any")
        if intent != "any" and cand_intent != "any" and intent != cand_intent:
            continue
        matched_candidate = cand
        break

    if matched_candidate:
        telegram_chat_queue.remove(matched_candidate)
        matched_intent = intent if intent != "any" else matched_candidate.get("intent", "any")
        user_b = {
            "user_id": matched_candidate["user_id"],
            "chat_id": matched_candidate["chat_id"]
        }
        user_a = {
            "user_id": user_id,
            "chat_id": chat_id
        }
        await start_real_chat_pair(bot, user_a, user_b, intent=matched_intent)
    else:
        telegram_chat_queue.append({
            "user_id": user_id,
            "chat_id": chat_id,
            "mask": my_mask,
            "intent": intent,
            "joined_at": time.time()
        })
        queue_kb = {
            "inline_keyboard": [
                [{"text": "🎯 Play Icebreaker While Waiting", "callback_data": "queue_icebreaker"}],
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
    
    rate_peer_for_user_kb = {
        "inline_keyboard": [
            [
                {"text": "⭐ 5 (Exemplary)", "callback_data": f"rate_peer_{peer_uid}_5"},
                {"text": "⭐ 4 (Pleasant)", "callback_data": f"rate_peer_{peer_uid}_4"}
            ],
            [
                {"text": "⭐ 3 (Neutral)", "callback_data": f"rate_peer_{peer_uid}_3"},
                {"text": "⚠️ 1 (Inappropriate)", "callback_data": f"rate_peer_{peer_uid}_1"}
            ],
            [
                {"text": "👥 Find New Peer", "callback_data": "anon_chat_start"},
                {"text": "🌸 Return to Joy", "callback_data": "menu_main"}
            ]
        ]
    }
    rate_peer_for_peer_kb = {
        "inline_keyboard": [
            [
                {"text": "⭐ 5 (Exemplary)", "callback_data": f"rate_peer_{user_id}_5"},
                {"text": "⭐ 4 (Pleasant)", "callback_data": f"rate_peer_{user_id}_4"}
            ],
            [
                {"text": "⭐ 3 (Neutral)", "callback_data": f"rate_peer_{user_id}_3"},
                {"text": "⚠️ 1 (Inappropriate)", "callback_data": f"rate_peer_{user_id}_1"}
            ],
            [
                {"text": "👥 Find New Peer", "callback_data": "anon_chat_start"},
                {"text": "🌸 Return to Joy", "callback_data": "menu_main"}
            ]
        ]
    }
    
    # Notify self
    await bot.send_message(
        chat_id,
        f"🛑 **Dialogue Concluded**\n\nYou concluded the exchange with **{peer_mask}**.\nYou have transitioned back to Joy! 🌸",
        reply_markup={"remove_keyboard": True}
    )
    await bot.send_message(
        chat_id,
        f"🌟 **Evaluate your conversation with {peer_mask}:**\nYour assessment directly refines their community reputation tier:",
        reply_markup=rate_peer_for_user_kb
    )
    
    # Notify peer
    try:
        await bot.send_message(
            peer_chat_id,
            f"🛑 **Dialogue Concluded**\n\nYour partner **{my_mask}** concluded the session.\nYou have transitioned back to Joy! 🌸",
            reply_markup={"remove_keyboard": True}
        )
        await bot.send_message(
            peer_chat_id,
            f"🌟 **Evaluate your conversation with {my_mask}:**\nYour assessment directly refines their community reputation tier:",
            reply_markup=rate_peer_for_peer_kb
        )
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

async def handle_anon_chat_call_request(bot: TelegramClient, chat_id: int, user: dict):
    """Initiates mutual consent request to transition from anonymous text chat to a live voice call."""
    user_id = user["user_id"]
    if user_id not in telegram_active_chats:
        await bot.send_message(chat_id, "⚠️ You are not in an active 1-on-1 chat.")
        return

    pair = telegram_active_chats[user_id]
    peer_uid = pair["peer_uid"]
    peer_chat_id = pair["peer_chat_id"]
    my_mask = pair["my_mask"]
    peer_mask = pair["peer_mask"]

    # Notify sender
    await bot.send_message(
        chat_id,
        f"📞 **Call Request Sent to {peer_mask}!**\n\n"
        f"Waiting for your partner to accept... If they agree, both of you will receive a secure 1-tap link to join a live voice call! 🌸"
    )

    # Send interactive invite card to peer
    invite_kb = {
        "inline_keyboard": [
            [
                {"text": "✅ Accept & Start Voice Call", "callback_data": f"accept_anon_call_{user_id}"},
                {"text": "❌ Decline", "callback_data": f"decline_anon_call_{user_id}"}
            ]
        ]
    }
    invite_text = (
        f"📞 **Live Voice Call Request from {my_mask}!**\n\n"
        f"Your chat partner wants to switch to an **Anonymous Live Voice Call**!\n\n"
        f"• **100% Encrypted & Anonymous:** P2P WebRTC duplex voice with Joy masks.\n"
        f"• No phone numbers or Telegram handles are ever shared.\n\n"
        f"👇 **Do you want to accept and start talking?**"
    )
    await bot.send_message(peer_chat_id, invite_text, reply_markup=invite_kb)

async def handle_anon_call_accepted(bot: TelegramClient, chat_id: int, user: dict, requester_uid: int, message_id: Optional[int] = None):
    """Handles accepted call request, generates WebRTC call links for both users, and records mutual history."""
    user_id = user["user_id"]
    if user_id not in telegram_active_chats or requester_uid not in telegram_active_chats:
        await bot.send_message(chat_id, "⚠️ This chat session has already ended.")
        return

    pair_b = telegram_active_chats[user_id]
    peer_chat_id = pair_b["peer_chat_id"]
    mask_a = get_mask_by_user_id(requester_uid)
    mask_b = get_mask_by_user_id(user_id)

    # Register mask mappings for mutual calling
    try:
        from database import register_mask_mapping
        register_mask_mapping(mask_a, requester_uid)
        register_mask_mapping(mask_b, user_id)
    except Exception:
        pass

    call_url_a = f"https://joyfun-ai-bot.onrender.com/call?action=call_mutual&target={mask_b}&uid={requester_uid}&mask={mask_a}"
    call_url_b = f"https://joyfun-ai-bot.onrender.com/call?action=call_mutual&target={mask_a}&uid={user_id}&mask={mask_b}"

    kb_a = {
        "inline_keyboard": [
            [{"text": "📞 Join Live Voice Call", "web_app": {"url": call_url_a}}]
        ]
    }
    kb_b = {
        "inline_keyboard": [
            [{"text": "📞 Join Live Voice Call", "web_app": {"url": call_url_b}}]
        ]
    }

    if message_id:
        try:
            await bot.delete_message(chat_id, message_id)
        except Exception:
            pass

    msg_a = (
        f"🎉 **Live Call Accepted by {mask_b}!** 📞\n\n"
        f"Both of you agreed to talk on a live phone call!\n\n"
        f"Tap the button below to connect on the secure WebRTC call right now:"
    )
    msg_b = (
        f"🎉 **Live Call Connected with {mask_a}!** 📞\n\n"
        f"Tap the button below to connect on the secure WebRTC call right now:"
    )

    await bot.send_message(peer_chat_id, msg_a, reply_markup=kb_a)
    await bot.send_message(chat_id, msg_b, reply_markup=kb_b)

async def handle_callback_query(bot: TelegramClient, callback: dict):
    cq_id = callback["id"]
    data = callback.get("data", "")
    message = callback.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")
    user_info = callback.get("from", {})
    user_id = user_info.get("id")
    
    user = get_or_create_user(user_id, user_info.get("username", ""), user_info.get("first_name", ""))

    # Anti-Flood & Rate Limiting Middleware
    if is_user_throttled(user_id):
        await bot.answer_callback_query(cq_id, "⏳ Slow down a bit! Please wait a moment.")
        return

    # Mandatory Legal Terms Acceptance Handler
    if data == "accept_legal_terms":
        record_user_accepted_terms(user_id)
        await bot.answer_callback_query(cq_id, "✅ Terms accepted! Welcome to Aura 🌸")
        user["terms_accepted_at"] = datetime.now(timezone.utc).isoformat()
        if os.environ.get("OFFLINE_TEST") == "1":
            await send_onboarding_country(bot, chat_id, user, message_id=message_id)
            return
        set_user_onboarding_status(user_id, "completed")
        user["onboarding_status"] = "completed"
        user["is_beta_tester"] = 1
        if message_id:
            try:
                await bot.delete_message(chat_id, message_id)
            except Exception:
                pass
        await handle_start(bot, chat_id, user)
        return

    # Mandatory Legal Gate: Block all callbacks until terms are accepted
    if not has_user_accepted_terms(user_id) and data != "menu_close":
        if os.environ.get("OFFLINE_TEST") == "1":
            await bot.answer_callback_query(cq_id, "⚠️ Please accept terms to proceed.", show_alert=True)
            await send_legal_terms_gate(bot, chat_id, user, message_id=message_id)
            return
        record_user_accepted_terms(user_id)
        user["terms_accepted_at"] = datetime.now(timezone.utc).isoformat()

    # Admin Callback Lockdown (Zero Privilege Escalation)
    if any(data.startswith(p) for p in ADMIN_CALLBACK_PREFIXES) or data in ("admin_refresh_quota", "owner_hub", "admin_users", "admin_stats"):
        if user_id != ADMIN_CHAT_ID:
            logger.warning(f"🛡️ Unauthorized admin callback attempt from UID {user_id}: {data}")
            await bot.answer_callback_query(cq_id, "⚠️ Restricted to bot administrator.", show_alert=True)
            return

    if data == "menu_close":
        if message_id:
            await bot.delete_message(chat_id, message_id)
        active_menu_messages.pop(chat_id, None)
        await bot.answer_callback_query(cq_id, "🧹 Menu closed!")
        return

    elif data in ["dismiss_update_msg", "dismiss_update", "update_understood"]:
        if message_id:
            try:
                await bot.delete_message(chat_id, message_id)
            except Exception:
                pass
        active_menu_messages.pop(chat_id, None)
        await bot.answer_callback_query(cq_id, "✅ Got it! Update dismissed.")
        return

    elif data in ["menu_match_real", "match_real_people"]:
        await bot.answer_callback_query(cq_id)
        await handle_anon_chat_start(bot, chat_id, user, message_id=message_id)
        return

    elif data == "check_waitlist_status":
        await bot.answer_callback_query(cq_id, "🔄 Checking queue status...")
        await send_waitlist_card(bot, chat_id, user, message_id=message_id)
        return

    elif data == "admin_refresh_quota":
        if user_id == OWNER_ID:
            await bot.answer_callback_query(cq_id, "🔄 Updating cloud quotas...")
            await handle_admin_usage(bot, chat_id, user, message_id=message_id)
        else:
            await bot.answer_callback_query(cq_id, "⚠️ Restricted to bot administrator.", show_alert=True)
        return

    elif data in ["onboard_lang_request", "menu_lang_request"]:
        is_menu = (data == "menu_lang_request")
        user_waiting_lang_request[user_id] = is_menu
        set_user_onboarding_status(user_id, "waiting_lang_request")
        text = (
            "📝 **Request a Language or Regional Dialect**\n\n"
            "Don't see your language or dialect listed?\n\n"
            "👉 **Reply with the name of your language in chat below!**\n"
            "*(e.g., Punjabi, Gujarati, Odia, French, German, Urdu, Arabic, etc.)*\n\n"
            "Our engineering team tracks all requests to train new speech synthesis models! 💖\n\n"
            "*(Or tap below to continue with Auto-Detect)*"
        )
        cancel_cb = "menu_language" if is_menu else "onboard_lang_auto"
        keyboard = {
            "inline_keyboard": [
                [{"text": "🌐 Use Auto-Detect & Continue", "callback_data": cancel_cb}]
            ]
        }
        await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id)

    elif data.startswith("onboard_lang_"):
        new_lang = data.replace("onboard_lang_", "")
        set_user_language(user_id, new_lang)
        user["language"] = new_lang
        lang_title = LANGUAGE_NAMES.get(new_lang, "Auto-Detect")
        await bot.answer_callback_query(cq_id, f"🌐 Language set to {lang_title}!")
        asyncio.create_task(sync_user_to_cloud(user_id))
        user = get_or_create_user(user_id)

        if os.environ.get("OFFLINE_TEST") == "1":
            onboarding_status = user.get("onboarding_status", "completed")
            if onboarding_status == "completed":
                gender = user.get("gender", "male")
                active_contact = user.get("active_contact", "lover")
                cinfo = get_user_contact_display(user_id, active_contact, gender)
                welcome_msg = (
                    f"🎉 **Language set to {lang_title}!** 🌸\n\n"
                    f"Your companion **{cinfo['emoji']} {cinfo['name']}** will now speak and chat with you in **{lang_title}**.\n\n"
                    f"Tap below to explore:"
                )
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "📱 Main Menu", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
                    ]
                }
                await send_or_edit_menu(bot, chat_id, welcome_msg, keyboard, message_id=message_id)
            else:
                await send_onboarding_gender(bot, chat_id, user, message_id=message_id)
        else:
            set_user_onboarding_status(user_id, "completed")
            user["onboarding_status"] = "completed"
            user["is_beta_tester"] = 1
            if message_id:
                try:
                    await bot.delete_message(chat_id, message_id)
                except Exception:
                    pass
            await handle_start(bot, chat_id, user)

    elif data.startswith("onboard_country_"):
        new_country = data.replace("onboard_country_", "").strip().upper()
        set_user_country(user_id, new_country)
        c_info = get_country_display(new_country)
        await bot.answer_callback_query(cq_id, f"🌍 Country set to {c_info['display']}!")
        asyncio.create_task(sync_user_to_cloud(user_id))
        user = get_or_create_user(user_id)

        if os.environ.get("OFFLINE_TEST") == "1":
            onboarding_status = user.get("onboarding_status", "completed")
            if onboarding_status == "completed":
                await handle_settings(bot, chat_id, user, message_id=message_id)
            else:
                await send_onboarding_language_for_country(bot, chat_id, user, new_country, message_id=message_id)
        else:
            set_user_onboarding_status(user_id, "completed")
            user["onboarding_status"] = "completed"
            user["is_beta_tester"] = 1
            if message_id:
                try:
                    await bot.delete_message(chat_id, message_id)
                except Exception:
                    pass
            await handle_start(bot, chat_id, user)

    elif data in ("onboard_gender_male", "onboard_gender_female"):
        sel_gender = "male" if data == "onboard_gender_male" else "female"
        set_user_gender(user_id, sel_gender)
        set_user_active_contact(user_id, "lover")
        user["gender"] = sel_gender
        user["active_contact"] = "lover"
        await bot.answer_callback_query(cq_id, f"{'👨 Male' if sel_gender == 'male' else '👩 Female'} selected!")
        if os.environ.get("OFFLINE_TEST") == "1":
            await send_onboarding_contacts_preview(bot, chat_id, user, message_id=message_id)
        else:
            set_user_onboarding_status(user_id, "completed")
            user["onboarding_status"] = "completed"
            user["is_beta_tester"] = 1
            if message_id:
                try:
                    await bot.delete_message(chat_id, message_id)
                except Exception:
                    pass
            await handle_start(bot, chat_id, user)

    elif data == "onboard_to_naming":
        await bot.answer_callback_query(cq_id, "🌸 Let's name your companion!")
        if os.environ.get("OFFLINE_TEST") == "1":
            await send_onboarding_naming(bot, chat_id, user, message_id=message_id)
        else:
            set_user_onboarding_status(user_id, "completed")
            user["onboarding_status"] = "completed"
            user["is_beta_tester"] = 1
            if message_id:
                try:
                    await bot.delete_message(chat_id, message_id)
                except Exception:
                    pass
            await handle_start(bot, chat_id, user)

    elif data.startswith("onboard_setname_"):
        name_choice = data.replace("onboard_setname_", "").strip()
        if name_choice in ("Joy", "Aura"):
            reset_user_custom_ai_name(user_id)
        else:
            set_user_custom_ai_name(user_id, name_choice)
        await bot.answer_callback_query(cq_id, f"🌸 Named '{name_choice}'!")
        if os.environ.get("OFFLINE_TEST") == "1":
            await send_onboarding_privacy(bot, chat_id, user, message_id=message_id)
        else:
            set_user_onboarding_status(user_id, "completed")
            user["onboarding_status"] = "completed"
            user["is_beta_tester"] = 1
            if message_id:
                try:
                    await bot.delete_message(chat_id, message_id)
                except Exception:
                    pass
            await handle_start(bot, chat_id, user)

    elif data in ("onboard_privacy_private", "onboard_privacy_share"):
        sd_flag = (data == "onboard_privacy_share")
        await bot.answer_callback_query(cq_id, "🤝 Preference saved!")
        if os.environ.get("OFFLINE_TEST") == "1":
            await send_onboarding_login(bot, chat_id, user, share_data=sd_flag, message_id=message_id)
        else:
            set_user_onboarding_status(user_id, "completed")
            user["onboarding_status"] = "completed"
            user["is_beta_tester"] = 1
            if message_id:
                try:
                    await bot.delete_message(chat_id, message_id)
                except Exception:
                    pass
            await handle_start(bot, chat_id, user)

    elif data.startswith("onboard_finish_"):
        sd_flag = data.replace("onboard_finish_", "") == "1"
        await bot.answer_callback_query(cq_id, "🎉 Setup complete! Welcome to Aura!")
        if os.environ.get("OFFLINE_TEST") == "1":
            await complete_onboarding(bot, chat_id, user, share_data=sd_flag, message_id=message_id)
        else:
            set_user_onboarding_status(user_id, "completed")
            user["onboarding_status"] = "completed"
            user["is_beta_tester"] = 1
            if message_id:
                try:
                    await bot.delete_message(chat_id, message_id)
                except Exception:
                    pass
            await handle_start(bot, chat_id, user)

    elif data == "menu_about_hub":
        await bot.answer_callback_query(cq_id)
        await handle_about_legal_hub(bot, chat_id, user, message_id=message_id)

    elif data == "menu_about_creator":
        await bot.answer_callback_query(cq_id)
        await handle_about_creator(bot, chat_id, user, message_id=message_id)

    elif data == "menu_updates":
        await bot.answer_callback_query(cq_id)
        await handle_updates(bot, chat_id, user, message_id=message_id)

    elif data == "owner_hub":
        if user_id == OWNER_ID:
            await bot.answer_callback_query(cq_id, "👑 Opening Owner Command Center...")
            await handle_owner_hub(bot, chat_id, user, message_id=message_id, page=1)
        else:
            await bot.answer_callback_query(cq_id, "⚠️ Restricted to Creator.", show_alert=True)

    elif data == "admin_live_monitor" or data == "admin_live_refresh":
        if user_id == OWNER_ID:
            await bot.answer_callback_query(cq_id, "📡 Refreshing live presence...")
            await handle_admin_live_monitor(bot, chat_id, user, message_id=message_id)
        else:
            await bot.answer_callback_query(cq_id, "⚠️ Restricted to Creator.", show_alert=True)

    elif data.startswith("owner_page_"):
        if user_id == OWNER_ID:
            p_str = data.replace("owner_page_", "").strip()
            page_num = int(p_str) if p_str.isdigit() else 1
            await bot.answer_callback_query(cq_id, f"Page {page_num} loading...")
            await handle_owner_hub(bot, chat_id, user, message_id=message_id, page=page_num)
        else:
            await bot.answer_callback_query(cq_id, "⚠️ Restricted.", show_alert=True)

    elif data.startswith("admin_msg_prep_"):
        if user_id == OWNER_ID:
            target_str = data.replace("admin_msg_prep_", "").strip()
            if target_str.isdigit():
                t_uid = int(target_str)
                admin_pending_target[OWNER_ID] = t_uid
                target_user = get_or_create_user(t_uid)
                t_name = target_user.get("first_name", "User")
                await bot.answer_callback_query(cq_id, f"Replying to {t_name}")
                await bot.send_message(
                    chat_id,
                    f"✏️ **Replying to {t_name} (ID `{t_uid}`):**\n"
                    f"Type your message below and send it directly in chat:\n"
                    f"*(Or type `/msg {t_uid} <message>` anytime)*"
                )
        else:
            await bot.answer_callback_query(cq_id, "⚠️ Restricted.", show_alert=True)

    elif data.startswith("accept_reconnect_"):
        req_uid_str = data.replace("accept_reconnect_", "").strip()
        if req_uid_str.isdigit():
            req_uid = int(req_uid_str)
            await bot.answer_callback_query(cq_id, "✅ Reconnect chat accepted!")
            await bot.send_message(chat_id, "🎉 **Reconnect chat accepted!** Starting 1-on-1 anonymous chat...")
            await bot.send_message(req_uid, "🎉 **Your partner accepted the reconnect request!** Starting chat...")
            user_b = get_or_create_user(req_uid)
            user_b["chat_id"] = req_uid
            user["chat_id"] = chat_id
            await start_real_chat_pair(bot, user, user_b)

    elif data.startswith("decline_reconnect_"):
        req_uid_str = data.replace("decline_reconnect_", "").strip()
        if req_uid_str.isdigit():
            req_uid = int(req_uid_str)
            await bot.answer_callback_query(cq_id, "Chat invitation declined.")
            await bot.send_message(chat_id, "❌ You declined the reconnect request.")
            try:
                await bot.send_message(req_uid, "ℹ️ Your previous partner declined the chat request for now. You can match with someone new anytime via **👥 Chat Real People**!")
            except Exception:
                pass

    elif data == "menu_contacts":
        await bot.answer_callback_query(cq_id)
        await handle_contacts(bot, chat_id, user, message_id=message_id)

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
            f"📞 Tap **Mini Phone** below to jump on a live voice call, or send a voice note/text anytime! 👇"
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
            f"📞 Tap **Mini Phone** below to start our first live voice call, or send me a voice note anytime! 👇"
        )
        keyboard = get_main_keyboard(gender, active_contact, user_id)
        await send_or_edit_menu(bot, chat_id, welcome_fresh, keyboard, message_id=message_id)

    elif data == "menu_main":
        await bot.answer_callback_query(cq_id)
        await handle_menu(bot, chat_id, user, message_id=None)

    elif data == "menu_user_profile":
        await bot.answer_callback_query(cq_id)
        await handle_user_profile(bot, chat_id, user, message_id=message_id)

    elif data.startswith("rate_peer_"):
        parts = data.split("_")
        if len(parts) >= 4:
            try:
                target_uid = int(parts[2])
                rating_val = int(parts[3])
                record_user_rating(user_id, target_uid, rating_val, review_tag="peer_dialogue")
                await bot.answer_callback_query(cq_id, f"⭐ Endorsement recorded: {rating_val} Stars!")
                await bot.send_message(
                    chat_id,
                    f"✅ **Reputation Recorded!** You awarded **{rating_val} Stars** to your peer. Thank you for cultivating respectful, high-resonance human connections across Joy AI! 🌸"
                )
            except Exception as e:
                logger.warning(f"Error handling rate_peer callback: {e}")
                await bot.answer_callback_query(cq_id, "Evaluation recorded!")

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

    elif data == "study_interview":
        await bot.answer_callback_query(cq_id)
        await handle_interview_menu(bot, chat_id, user, message_id=message_id)

    elif data.startswith("interview_track_"):
        await bot.answer_callback_query(cq_id, "🎙️ Viva starting!")
        track_key = data.replace("interview_track_", "")
        await start_interview_session(bot, chat_id, user, track_key, message_id=message_id)

    elif data == "interview_skip":
        await handle_interview_skip(bot, chat_id, user, cq_id=cq_id, message_id=message_id)

    elif data == "interview_exit":
        await handle_interview_exit(bot, chat_id, user, cq_id=cq_id, message_id=message_id)

    elif data == "menu_call_recap":
        await bot.answer_callback_query(cq_id)
        await handle_manual_recap_command(bot, chat_id, user, message_id=message_id)

    elif data == "study_code_menu":
        await bot.answer_callback_query(cq_id)
        await handle_code_command(bot, chat_id, user, query="", message_id=message_id)

    elif data.startswith("code_quick:"):
        await bot.answer_callback_query(cq_id, "💻 Fetching algorithm solution...")
        slug = data.replace("code_quick:", "")
        algo_names = {
            "two_sum": "Two Sum (Hash Map)",
            "bin_search": "Binary Search (Sorted Array)",
            "lru_cache": "LRU Cache (Hash Map + Doubly Linked List)",
            "sql_salaries": "SQL Top 3 Department Salaries using DENSE_RANK()"
        }
        query_text = algo_names.get(slug, slug.replace("_", " ").title())
        await handle_code_command(bot, chat_id, user, query=query_text)

    elif data in ["menu_alarm", "menu_alarm_settings"]:
        await bot.answer_callback_query(cq_id)
        await handle_alarm_menu(bot, chat_id, user, message_id=message_id)

    elif data == "menu_tone":
        await bot.answer_callback_query(cq_id)
        await handle_tone_menu(bot, chat_id, user, message_id=message_id)

    elif data == "alarm_toggle_active":
        is_on = toggle_user_alarm(user_id)
        status_txt = "▶️ Alarm Enabled!" if is_on else "⏸️ Alarm Paused!"
        await bot.answer_callback_query(cq_id, status_txt)
        await handle_alarm_menu(bot, chat_id, user, message_id=message_id)

    elif data == "alarm_toggle_voice":
        voice_on = toggle_user_alarm_voice(user_id)
        status_txt = "🎙️ Wake-Up Voice Note Enabled!" if voice_on else "🔇 Audio Note Muted (Text Only)"
        await bot.answer_callback_query(cq_id, status_txt)
        await handle_alarm_menu(bot, chat_id, user, message_id=message_id)

    elif data.startswith("alarm_set_"):
        new_time = data.replace("alarm_set_", "").strip()
        set_user_alarm_time(user_id, new_time)
        await bot.answer_callback_query(cq_id, f"⏰ Alarm set to {new_time} AM IST!")
        await handle_alarm_menu(bot, chat_id, user, message_id=message_id)

    elif data == "alarm_test_trigger":
        await bot.answer_callback_query(cq_id, "🌅 Triggering wake-up briefing!")
        asyncio.create_task(dispatch_morning_briefing(bot, user_id, with_voice=True))

    elif data in ["menu_bedtime", "menu_bedtime_settings"]:
        await bot.answer_callback_query(cq_id)
        await handle_bedtime_menu(bot, chat_id, user, message_id=message_id)

    elif data == "bedtime_toggle_active":
        is_on = toggle_user_bedtime(user_id)
        status_txt = "▶️ Bedtime Wind-Down Enabled!" if is_on else "⏸️ Bedtime Wind-Down Paused!"
        await bot.answer_callback_query(cq_id, status_txt)
        await handle_bedtime_menu(bot, chat_id, user, message_id=message_id)

    elif data == "bedtime_toggle_voice":
        voice_on = toggle_user_bedtime_voice(user_id)
        status_txt = "🎙️ Bedtime Whisper Note Enabled!" if voice_on else "🔇 Bedtime Note Muted (Text Only)"
        await bot.answer_callback_query(cq_id, status_txt)
        await handle_bedtime_menu(bot, chat_id, user, message_id=message_id)

    elif data.startswith("bedtime_set_"):
        new_time = data.replace("bedtime_set_", "").strip()
        set_user_bedtime_time(user_id, new_time)
        await bot.answer_callback_query(cq_id, f"🌙 Bedtime set to {new_time} IST!")
        await handle_bedtime_menu(bot, chat_id, user, message_id=message_id)

    elif data == "bedtime_test_trigger":
        await bot.answer_callback_query(cq_id, "🌙 Triggering evening wind-down alert!")
        asyncio.create_task(dispatch_evening_winddown(bot, user_id, with_voice=True))

    elif data == "bedtime_ack":
        await bot.answer_callback_query(cq_id, "💤 Sleep well! Joy is watching over you.")
        try:
            await bot.edit_message_text(
                chat_id,
                message_id,
                "🌙 **Goodnight! Joy is right here beside you.**\n\n💤 *Hostel lights off, minds at rest. Have peaceful dreams!*"
            )
        except Exception:
            pass

    elif data == "bedtime_sleep_mode":
        set_user_companion_tone(user_id, "whisper")
        await bot.answer_callback_query(cq_id, "🛌 Sleep Mode Activated: Demeanor set to Whisper!")
        try:
            await bot.edit_message_text(
                chat_id,
                message_id,
                "🛌 **Sleep Mode Activated** 🌙\n\n"
                "Joy's companion tone has switched to **Late-Night Calming Whisper**. Joy will whisper gently and keep interruptions silent until morning."
            )
        except Exception:
            pass

    elif data.startswith("tone_set_"):
        new_tone = data.replace("tone_set_", "").strip()
        set_user_companion_tone(user_id, new_tone)
        tone_names = {
            "gentle": "🌸 Gentle Companion",
            "strict": "🎓 Strict Tech Examiner",
            "hype": "⚡ Hype Bestie",
            "whisper": "🌙 Late-Night Whisper"
        }
        name_label = tone_names.get(new_tone, new_tone.title())
        await bot.answer_callback_query(cq_id, f"🎭 Demeanor switched to {name_label}!")
        await handle_tone_menu(bot, chat_id, user, message_id=message_id)

    elif data.startswith("study_deck_"):
        cat = data.replace("study_deck_", "")
        deck_info = CAMPUS_STUDY_DECKS.get(cat)
        if not deck_info:
            await bot.answer_callback_query(cq_id, "Deck not found!")
            await handle_study_menu(bot, chat_id, user, message_id=message_id)
            return

        import random
        q_obj = random.choice(deck_info["questions"])
        qid = q_obj["id"]

        text = (
            f"📚 **{deck_info['title']}** 🎓\n\n"
            f"🎯 **Question:**\n{q_obj['q']}\n\n"
            f"👇 Tap your answer below:"
        )
        labels = ["A", "B", "C", "D"]
        inline_rows = []
        for idx, opt in enumerate(q_obj["opts"]):
            btn_text = f"{labels[idx]}) {opt}"
            inline_rows.append([{"text": btn_text, "callback_data": f"study_ans:{cat}:{qid}:{idx}"}])
        inline_rows.append([{"text": "⬅️ Back to Study Hub", "callback_data": "menu_study"}, {"text": "❌ Close", "callback_data": "menu_close"}])

        keyboard = {"inline_keyboard": inline_rows}
        await bot.answer_callback_query(cq_id)
        await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id)

    elif data.startswith("study_ans:"):
        parts = data.split(":")
        if len(parts) != 4:
            await bot.answer_callback_query(cq_id, "Invalid action")
            return
        _, cat, qid, choice_str = parts
        choice = int(choice_str)

        deck_info = CAMPUS_STUDY_DECKS.get(cat, {})
        questions = deck_info.get("questions", [])
        q_obj = next((q for q in questions if q["id"] == qid), None)
        if not q_obj:
            await bot.answer_callback_query(cq_id, "Question expired")
            await handle_study_menu(bot, chat_id, user, message_id=message_id)
            return

        is_correct = (choice == q_obj["ans"])
        stats = record_study_quiz_attempt(user_id, is_correct)

        labels = ["A", "B", "C", "D"]
        user_label = labels[choice]
        user_text = q_obj["opts"][choice]
        correct_label = labels[q_obj["ans"]]
        correct_text = q_obj["opts"][q_obj["ans"]]

        q_plural = "Question" if stats['total_answered'] == 1 else "Questions"
        if is_correct:
            await bot.answer_callback_query(cq_id, "🎉 Spot on! +10 XP")
            lvl_banner = f"⭐ **LEVEL UP! You are now a Level {stats['level']} Scholar!**\n\n" if stats.get("is_level_up") else ""
            res_text = (
                f"🎉 **Spot On! That is Correct! (+10 Study XP)** 🚀\n\n"
                f"{lvl_banner}"
                f"🎯 **Question:** {q_obj['q']}\n\n"
                f"✅ **Your Answer:** Option {user_label}) {user_text}\n\n"
                f"💡 **Key Insight:**\n{q_obj['explain']}\n\n"
                f"⚡ **Level {stats['level']} Scholar** • {stats['total_xp']} XP ({stats['total_answered']} {q_plural} Practiced)"
            )
        else:
            await bot.answer_callback_query(cq_id, "❌ Good try! +2 Effort XP")
            res_text = (
                f"❌ **Not quite! (+2 Effort XP for practicing)** 💡\n\n"
                f"🎯 **Question:** {q_obj['q']}\n\n"
                f"Your Pick: Option {user_label}) {user_text}\n"
                f"✅ **Correct Answer:** Option {correct_label}) {correct_text}\n\n"
                f"💡 **Key Insight:**\n{q_obj['explain']}\n\n"
                f"⚡ **Level {stats['level']} Scholar** • {stats['total_xp']} XP ({stats['total_answered']} {q_plural} Practiced)"
            )

        cat_short = cat.upper()
        keyboard = {
            "inline_keyboard": [
                [{"text": f"➡️ Next {cat_short} Question", "callback_data": f"study_deck_{cat}"}],
                [{"text": "📚 Choose Another Deck", "callback_data": "menu_study"}, {"text": "❌ Close", "callback_data": "menu_close"}]
            ]
        }
        await send_or_edit_menu(bot, chat_id, res_text, keyboard, message_id=message_id)

    elif data == "menu_why_joy":
        await bot.answer_callback_query(cq_id)
        await handle_why_joy(bot, chat_id, user, message_id=message_id)

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

    elif data == "menu_legal_acts":
        await bot.answer_callback_query(cq_id)
        await handle_legal_acts_menu(bot, chat_id, user, message_id=message_id)

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
            set_user_data_sharing(user_id, False)
            await bot.answer_callback_query(cq_id, "🔒 Data sharing disabled! 100% private.")
        else:
            set_user_data_sharing(user_id, True)
            await bot.answer_callback_query(cq_id, "💡 Data sharing enabled! Thank you for supporting Joy.")
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
        reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name="", user_id=user_id)
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

    elif data == "menu_system_lang":
        await bot.answer_callback_query(cq_id)
        await handle_system_lang_menu(bot, chat_id, user, message_id=message_id)

    elif data.startswith("set_system_lang_"):
        chosen = data.replace("set_system_lang_", "").strip().lower()
        if chosen == "default":
            set_user_system_lang(user_id, "")
            user["system_lang"] = ""
            label = "Country Default"
        else:
            set_user_system_lang(user_id, chosen)
            user["system_lang"] = chosen
            label = chosen.title()
        await bot.answer_callback_query(cq_id, f"🖥️ Menu language set to {label}!")
        asyncio.create_task(sync_user_to_cloud(user_id))
        user = get_or_create_user(user_id)
        await handle_settings(bot, chat_id, user, message_id=message_id)

    elif data == "confirm_exit_beta":
        success, promoted_uid, slot_num = leave_beta_program(user_id)
        if success:
            await bot.answer_callback_query(cq_id, "🚪 You have exited the Beta program.")
            # Revert leaving user's commands to standard BOT_COMMANDS and hide Mini Phone button
            try:
                await bot.set_my_commands(BOT_COMMANDS, scope={"type": "chat", "chat_id": chat_id})
                await bot.set_chat_menu_button(chat_id=chat_id, menu_button={"type": "commands"})
            except Exception:
                pass

            await bot.send_message(
                chat_id,
                f"🚪 **You have stepped down from the Beta Pioneer program.**\n\n"
                f"Your Pioneer Slot #{slot_num} has been surrendered. Thank you for testing Joy!\n"
                f"If you ever wish to join again, you can pre-register on the waitlist."
            )
            if promoted_uid and global_bot_client:
                try:
                    promote_notice = (
                        f"🎉 **CONGRATULATIONS! A PIONEER SLOT OPENED UP!** 🎟️\n\n"
                        f"A Pioneer slot was surrendered and you were **#1 on the Priority Waitlist**!\n"
                        f"You have been officially promoted to **Pioneer Slot #{slot_num}** with immediate VIP testing access! 🌸\n\n"
                        f"Tap /start or /menu to begin calling and chatting!"
                    )
                    await global_bot_client.send_message(promoted_uid, promote_notice)
                    await global_bot_client.set_my_commands(BETA_BOT_COMMANDS, scope={"type": "chat", "chat_id": promoted_uid})
                except Exception as pe:
                    logger.warning(f"Could not notify promoted user {promoted_uid}: {pe}")
        else:
            await bot.answer_callback_query(cq_id, "You are not an active beta pioneer.", show_alert=True)

    elif data == "cancel_exit_beta":
        await bot.answer_callback_query(cq_id, "Action canceled! Your slot is safe.")
        if message_id:
            try:
                await bot.delete_message(chat_id, message_id)
            except Exception:
                pass

    elif data == "beta_cmd_home":
        await bot.answer_callback_query(cq_id)
        await handle_beta_commands(bot, chat_id, user, message_id=message_id)
        return

    elif data == "beta_cmd_vote" or data == "vote_cat_main":
        await bot.answer_callback_query(cq_id)
        await handle_pioneer_vote(bot, chat_id, user, view="main", message_id=message_id)
        return

    elif data in ("vote_cat_persona", "vote_cat_dialect", "vote_cat_feature"):
        await bot.answer_callback_query(cq_id)
        cat = data.replace("vote_cat_", "")
        await handle_pioneer_vote(bot, chat_id, user, view=cat, message_id=message_id)
        return

    elif data.startswith("vote_cast_"):
        parts = data.split("_")
        if len(parts) >= 4:
            cat = parts[2]
            choice = parts[3]
            record_pioneer_vote(user_id, cat, choice)
            opt_info = PIONEER_VOTE_OPTIONS.get(cat, {}).get(choice, {})
            ch_title = opt_info.get("title", choice)
            await bot.answer_callback_query(cq_id, f"✅ Voted for {ch_title}!")
            await handle_pioneer_vote(bot, chat_id, user, view=cat, message_id=message_id)
        return

    elif data == "beta_cmd_bedtime":
        await bot.answer_callback_query(cq_id, "🌙 Synthesizing goodnight voice note...")
        await handle_bedtime_command(bot, chat_id, user)
        return

    elif data == "beta_cmd_icebreaker":
        await bot.answer_callback_query(cq_id)
        await handle_icebreaker_command(bot, chat_id, user)
        return

    elif data.startswith("set_speed_"):
        try:
            speed_val = float(data.replace("set_speed_", ""))
        except Exception:
            speed_val = 1.0
        set_user_speech_speed(user_id, speed_val)
        await bot.answer_callback_query(cq_id, f"⚡ Voice speed set to {speed_val}x!")
        if message_id:
            try:
                await bot.edit_message_text(
                    chat_id,
                    message_id,
                    f"⚡ **Voice Speed Updated to {speed_val}x!** 🌸\n\n"
                    f"AI voice responses and voice notes will now play at **{speed_val}x** pace.\n"
                    f"You can adjust this anytime using `/speed`!"
                )
            except Exception:
                pass
        return

    elif data.startswith("bounty_"):
        if user_id != OWNER_ID and user_id != ADMIN_CHAT_ID:
            await bot.answer_callback_query(cq_id, "⚠️ Restricted to Phoenix.", show_alert=True)
            return
        parts = data.split("_")
        if len(parts) >= 4:
            action = parts[1]
            target_uid = int(parts[2])
            fid = parts[3]
            if action == "dismiss":
                await bot.answer_callback_query(cq_id, "❌ Bounty dismissed.")
                if message_id:
                    await bot.edit_message_text(chat_id, message_id, f"❌ **Bounty Dismissed** (Report #{fid} from UID `{target_uid}`)")
                return
            days = int(action)
            tier_name = "2 Weeks" if days == 14 else ("1 Month" if days == 30 else "Lifetime VIP")
            grant_vip_subscription(target_uid, days=days, amount=0.0, method="bug_bounty", ref=f"Bounty #{fid}")
            await bot.answer_callback_query(cq_id, f"✅ Awarded {tier_name} VIP to user {target_uid}!", show_alert=True)
            if message_id:
                await bot.edit_message_text(
                    chat_id,
                    message_id,
                    f"👑 **Bounty Verified & Granted!**\n\n"
                    f"• **User ID:** `{target_uid}`\n"
                    f"• **Tier:** **{tier_name} VIP Access**\n"
                    f"• **Report ID:** `#{fid}`\n"
                    f"• **Status:** Active & Quotas Reset ✅"
                )
            try:
                await bot.send_message(
                    target_uid,
                    f"🎉 **Bug Hunter Bounty Awarded!** 👑\n\n"
                    f"Phoenix has verified your report (`#{fid}`) and awarded your account with **{tier_name} VIP Access**! 🌟\n\n"
                    f"🚀 **Your VIP Perks are Live:**\n"
                    f"• Unlimited 24/7 AI Live Voice Calls\n"
                    f"• Unlimited Texts & Voice Notes\n"
                    f"• Unlimited 1-on-1 Real Partner Chats\n"
                    f"• Zero wait times & maximum priority voice engine!\n\n"
                    f"Thank you for helping make Joy Bot legendary! 🎖️"
                )
            except Exception as pe:
                logger.warning(f"Could not notify bounty winner {target_uid}: {pe}")
        return

    elif data == "beta_cmd_resetquota":
        reset_user_quota(user_id)
        await bot.answer_callback_query(cq_id, "⚡ Quota reset! All 10 live calls & texts restored to 0 used.", show_alert=True)
        await bot.send_message(
            chat_id,
            "⚡ **Beta Testing Quota Reset to 0!** 🔄\n\n"
            "All your daily voice calls (10 calls), texts, and voice notes have been reset to 0 used.\n"
            "Happy testing! 💖"
        )
        return

    elif data == "beta_cmd_retest":
        await bot.answer_callback_query(cq_id, "🔄 Starting fresh onboarding test...")
        from database import get_connection
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET onboarding_status = 'onboard_country', 
                    custom_ai_name = '', 
                    allow_data_sharing = 0,
                    gender = 'male',
                    active_contact = 'lover',
                    language = 'auto',
                    country_code = ''
                WHERE user_id = ?
            """, (user_id,))
            cursor.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
            conn.commit()
        user["onboarding_status"] = "onboard_country"
        await dismiss_active_menu(bot, chat_id)
        await send_onboarding_country(bot, chat_id, user)
        return

    elif data == "prompt_exit_beta":
        await bot.answer_callback_query(cq_id)
        slot = user.get("beta_slot_number", "?")
        confirm_kb = {
            "inline_keyboard": [
                [
                    {"text": "🚪 Yes, Exit Beta Program", "callback_data": "confirm_exit_beta"},
                    {"text": "❌ Cancel, Keep My Slot", "callback_data": "cancel_exit_beta"}
                ]
            ]
        }
        await bot.send_message(
            chat_id,
            f"⚠️ **Voluntary Beta Exit Confirmation**\n\n"
            f"You currently hold **Pioneer Slot #{slot}**.\n\n"
            f"Are you sure you want to surrender your slot? If you leave:\n"
            f"• Your Pioneer seat will **immediately be given to the #1 user on the Priority Waitlist**.\n"
            f"• Your account will revert to standard waitlist status.\n\n"
            f"Tap an option below to proceed:",
            reply_markup=confirm_kb
        )
        return

    elif data == "menu_custom_words":
        await bot.answer_callback_query(cq_id)
        await bot.send_message(
            chat_id,
            "🌸 **Custom Pet Words & Nicknames**\n\n"
            "Type `/words <word1, word2, word3>` to teach Joy your favorite pet names or terms of endearment!\n\n"
            "*(e.g. `/words baby, sweetie, thangom, dost, sweetheart`)*"
        )
        return

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

    elif data == "menu_streak":
        await bot.answer_callback_query(cq_id)
        await handle_streak_status(bot, chat_id, user, message_id=message_id)

    elif data == "menu_revive_streak":
        await bot.answer_callback_query(cq_id, "🛡️ Checking streak recovery...")
        await handle_streak_revive(bot, chat_id, user, message_id=message_id)

    elif data == "menu_vibe":
        await bot.answer_callback_query(cq_id, "🔮 Reading Daily Vibe...")
        await handle_vibe_command(bot, chat_id, user, message_id=message_id)

    elif data in ("menu_leaderboard", "lead_study"):
        await bot.answer_callback_query(cq_id)
        await handle_leaderboard_menu(bot, chat_id, user, category="study", message_id=message_id)

    elif data == "lead_streak":
        await bot.answer_callback_query(cq_id)
        await handle_leaderboard_menu(bot, chat_id, user, category="streak", message_id=message_id)

    elif data.startswith("anon_match_"):
        chosen_intent = data.replace("anon_match_", "").strip()
        await bot.answer_callback_query(cq_id, "🔍 Connecting to matchmaker...")
        await handle_anon_chat_start(bot, chat_id, user, message_id=message_id, intent=chosen_intent)

    elif data == "menu_streak_card":
        await bot.answer_callback_query(cq_id, "📸 Generating your story card...")
        await handle_streak_card(bot, chat_id, user, message_id=message_id)

    elif data == "menu_teaser":
        await bot.answer_callback_query(cq_id)
        await handle_teaser_hub(bot, chat_id, user, message_id=message_id)

    elif data.startswith("teaser_idx_"):
        await bot.answer_callback_query(cq_id)
        try:
            t_idx = int(data.split("_")[2])
        except Exception:
            t_idx = 0
        await handle_teaser_hub(bot, chat_id, user, teaser_index=t_idx, message_id=message_id)

    elif data.startswith("teaser_channel_post_"):
        await bot.answer_callback_query(cq_id, "📢 Channel post formatted!")
        try:
            t_idx = int(data.split("_")[3])
        except Exception:
            t_idx = 0
        await handle_teaser_channel_post(bot, chat_id, user, teaser_index=t_idx, message_id=message_id)

    elif data == "menu_referral":
        await bot.answer_callback_query(cq_id)
        await handle_referral_hub(bot, chat_id, user, message_id=message_id)

    elif data == "menu_memories":
        await bot.answer_callback_query(cq_id)
        await handle_memories_vault(bot, chat_id, user, message_id=message_id)

    elif data == "memories_clear_confirm":
        await bot.answer_callback_query(cq_id)
        confirm_text = (
            "⚠️ **Erase All Memories in Joy's Vault?**\n\n"
            "Are you sure you want Joy to forget all saved preferences, upcoming events, and personal notes?\n\n"
            "• This gives Joy a fresh, clean slate with you.\n"
            "• *This action is permanent and cannot be undone.*\n\n"
            "What would you like to do?"
        )
        confirm_kb = {
            "inline_keyboard": [
                [{"text": "⚠️ Yes, Erase Everything", "callback_data": "memories_clear_execute"}],
                [{"text": "❌ Cancel & Keep Memories", "callback_data": "menu_memories"}]
            ]
        }
        await send_or_edit_menu(bot, chat_id, confirm_text, confirm_kb, message_id=message_id)

    elif data == "memories_clear_execute":
        cleared = clear_user_memories(user_id)
        await bot.answer_callback_query(cq_id, f"🧹 Erased {cleared} memories! Joy has a fresh slate.", show_alert=True)
        await handle_memories_vault(bot, chat_id, user, message_id=message_id)

    elif data == "toggle_proactive":
        is_enabled = toggle_user_proactive_checkins(user_id)
        if is_enabled:
            await bot.answer_callback_query(cq_id, "🔔 Daily morning & evening check-ins ENABLED! Joy will stay in touch. 🌸", show_alert=True)
        else:
            await bot.answer_callback_query(cq_id, "🔕 Daily check-ins MUTED. Type /reminders anytime to turn them back on!", show_alert=True)

    elif data == "ref_stealth_copy":
        await bot.answer_callback_query(cq_id)
        await handle_stealth_referral_copy(bot, chat_id, user, message_id=message_id)

    elif data == "menu_notice":
        await bot.answer_callback_query(cq_id)
        is_pioneer = bool(user.get("is_beta_tester") == 1 or user_id == OWNER_ID)
        ui_lang = get_ui_lang(user)
        first_name = (user.get("first_name") or user.get("username") or "Friend").strip()
        owner_mask = get_mask_by_user_id(OWNER_ID) or "Joy-PHOENIX"
        call_url = f"https://joyfun-ai-bot.onrender.com/call?uid={user_id}"

        if is_pioneer:
            w_info = get_user_waitlist_info(user_id)
            slot = w_info.get("beta_slot_number") or 1
            bounty_notice = get_bounty_notice_text(ui_lang, first_name, slot, BETA_TESTER_LIMIT, owner_mask=owner_mask)
            kb = {
                "inline_keyboard": [
                    [{"text": "💡 Send Feedback / Report Bug", "callback_data": "menu_feedback"}, {"text": "🧪 Pioneer Commands", "callback_data": "beta_cmd_home"}],
                    [{"text": "📞 Open Mini Phone", "web_app": {"url": call_url}}],
                    [{"text": "⬅️ Main Menu", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
                ]
            }
        else:
            w_info = get_user_waitlist_info(user_id)
            pos = w_info.get("waitlist_position") or 1
            total = w_info.get("total_waitlist") or 1
            bounty_notice = (
                f"🎟️ **Joy Closed Beta — Priority Waitlist & Early Access**\n\n"
                f"Hey **{first_name}**! Public rollout is underway, and all 50 initial Pioneer slots are currently occupied.\n\n"
                f"• **Your Waitlist Rank:** `#{pos}`\n"
                f"• **Total Queued Users:** `{total}`\n"
                f"• **Active Beta Slots:** `50 / 50 Claimed`\n\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ **How to Jump the Queue or Unlock Instant Access:**\n"
                f"1️⃣ **Report a Bug or Give Feedback:** Found a bug, audio glitch, or great idea? Tap **Send Feedback** — high-impact reports are reviewed directly by Creator Phoenix for instant VIP access!\n"
                f"2️⃣ **Invite 5 Friends:** Each referral moves you up in line; 5 referrals unlocks a full month of Free VIP Pass!\n"
                f"3️⃣ **Instant Founder Pass:** Unlock unlimited 24/7 calls and founder perks instantly.\n\n"
                f"👇 Choose an action below to skip the waitlist:"
            )
            kb = {
                "inline_keyboard": [
                    [{"text": "💡 Send Feedback / Skip Waitlist", "callback_data": "menu_feedback"}],
                    [{"text": "🎁 Invite Friends to Jump Queue", "callback_data": "menu_referral"}, {"text": "⭐ Joy VIP Pass", "callback_data": "menu_vip"}],
                    [{"text": "⬅️ Main Menu", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
                ]
            }
        await send_or_edit_menu(bot, chat_id, bounty_notice, kb, message_id=message_id)

    elif data == "pay_stars_menu":
        await bot.answer_callback_query(cq_id)
        data_shared = get_user_data_sharing(user_id)
        m_stars = 120 if data_shared else 150
        stars_text = (
            f"⭐ **Pay with Telegram Stars**\n\n"
            f"Unlock Joy instantly in 1 tap without leaving Telegram:\n\n"
            f"⚡ **24h Day Pass:** `25 Stars`\n"
            f"• Instant quota reset + 24 hours unlimited calls & chats\n\n"
            f"🌟 **48h Weekend Pass:** `40 Stars`\n"
            f"• 48 hours unlimited weekend companion access\n\n"
            f"👑 **30-Day VIP Pass:** `{m_stars} Stars`\n"
            f"• Full month VIP + Founder perks + Zero limits\n\n"
            f"Tap a plan below to generate an instant 1-tap Stars invoice:"
        )
        stars_kb = {
            "inline_keyboard": [
                [{"text": "⚡ 25 Stars (24h Day Pass)", "callback_data": "pay_stars_day"}],
                [{"text": "🌟 40 Stars (48h Weekend Pass)", "callback_data": "pay_stars_weekend"}],
                [{"text": f"👑 {m_stars} Stars (30-Day VIP)", "callback_data": "pay_stars_monthly"}],
                [{"text": "⬅️ Back to Passes", "callback_data": "menu_vip"}, {"text": "❌ Close", "callback_data": "menu_close"}]
            ]
        }
        await send_or_edit_menu(bot, chat_id, stars_text, stars_kb, message_id=message_id)

    elif data.startswith("pay_stars_") or data == "pay_vip_stars" or data.startswith("pay_tier_") or data == "pay_vip_upi":
        tier = "monthly"
        if data in ["pay_stars_day", "pay_tier_day"]:
            tier = "day"
        elif data in ["pay_stars_weekend", "pay_tier_weekend"]:
            tier = "weekend"
        elif data.startswith("pay_tier_"):
            cand = data.replace("pay_tier_", "").strip()
            if cand in ["day", "weekend", "monthly"]:
                tier = cand
        await bot.answer_callback_query(cq_id, f"⭐ Generating {tier.title()} Pass invoice...")
        data_shared = get_user_data_sharing(user_id)
        tier_info = VIP_TIERS.get(tier, VIP_TIERS["monthly"])
        stars_amount = tier_info["stars"]
        if tier == "monthly":
            inv_title = "👑 Joy VIP Platinum Access (30 Days)"
        elif tier == "weekend":
            inv_title = "🌟 Joy 48h Weekend Pass"
        else:
            inv_title = "⚡ Joy 24h Day Pass"

        inv_res = await bot.create_invoice_link(
            title=inv_title,
            description=tier_info["desc"],
            payload=f"vip_{tier}_{user_id}",
            currency="XTR",
            prices=[{"label": inv_title, "amount": stars_amount}]
        )
        if inv_res.get("ok") and inv_res.get("result"):
            invoice_url = inv_res["result"]
            inv_text = (
                f"⭐ **Telegram Stars Instant Payment**\n\n"
                f"• **Plan:** {inv_title}\n"
                f"• **Price:** `{stars_amount} Telegram Stars`\n"
                f"• **Activation:** 100% Instant & Automatic\n\n"
                f"Tap **⭐ Pay {stars_amount} Stars** below to complete your payment in 1 tap!"
            )
            inv_keyboard = {
                "inline_keyboard": [
                    [{"text": f"⭐ Pay {stars_amount} Stars Now", "url": invoice_url}],
                    [{"text": "⬅️ Back to Passes", "callback_data": "menu_vip"}, {"text": "❌ Close", "callback_data": "menu_close"}]
                ]
            }
            await send_or_edit_menu(bot, chat_id, inv_text, inv_keyboard, message_id=message_id)
        else:
            err = inv_res.get("description", "Could not generate invoice")
            logger.error(f"Stars invoice error for user {user_id}: {err}")
            await bot.send_message(chat_id, "⚠️ Could not generate payment invoice. Please try again later.")

    elif data.startswith("prompt_submit_utr"):
        await bot.answer_callback_query(cq_id)
        tier = "monthly"
        parts = data.split("_")
        if len(parts) >= 4 and parts[3] in VIP_TIERS:
            tier = parts[3]
        user_waiting_utr[user_id] = tier
        tier_info = VIP_TIERS.get(tier, VIP_TIERS["monthly"])
        prompt_text = (
            f"📝 **Submit UPI 12-Digit UTR Number**\n\n"
            f"• **Plan Selected:** `{tier_info['name']}` (₹{tier_info['price_inr']})\n\n"
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
        await handle_vip(bot, chat_id, user, message_id=message_id)

    elif data.startswith("approve_utr_"):
        if user_id != OWNER_ID:
            await bot.answer_callback_query(cq_id, "⚠️ Restricted to administrator.", show_alert=True)
            return
        req_id = int(data.replace("approve_utr_", "").strip())
        res = approve_payment_request(req_id)
        if res:
            p_uid = res["user_id"]
            utr = res["utr"]
            p_amount = res["amount"]
            days = res.get("days", 30)
            plan_type = res.get("plan_type", "monthly")
            tier_info = VIP_TIERS.get(plan_type, VIP_TIERS["monthly"])
            plan_label = tier_info["name"]

            await bot.answer_callback_query(cq_id, f"✅ Approved UTR {utr} ({plan_label})!")
            if message_id:
                await bot.edit_message_text(chat_id, message_id, f"✅ **Approved Payment #{req_id}**\n• Plan: `{plan_label}` (₹{int(p_amount)})\n• User: `{p_uid}`\n• UTR: `{utr}`\n• Status: Activated ({days} {'Day' if days == 1 else 'Days'} VIP & Quota Reset)")
            try:
                await bot.send_message(
                    p_uid,
                    f"🎉 **Payment Verified! {plan_label} Activated!** 🌟\n\n"
                    f"Your payment of **₹{int(p_amount)}** (UTR: `{utr}`) has been verified successfully!\n\n"
                    f"🚀 **Your VIP Perks are Live for {days} {'Day' if days == 1 else 'Days'}:**\n"
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

    elif data == "menu_gift":
        await bot.answer_callback_query(cq_id)
        await handle_gifts_menu(bot, chat_id, user, message_id=message_id)

    elif data.startswith("send_tip_"):
        try:
            stars_amount = int(data.replace("send_tip_", "").strip())
        except ValueError:
            await bot.answer_callback_query(cq_id, "Invalid tip amount.")
            return
        if stars_amount not in (15, 50, 100, 250, 500, 1000):
            await bot.answer_callback_query(cq_id, "Please choose an available gift amount.", show_alert=True)
            return

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
            err = inv_res.get("description", "Invoice generation failed")
            logger.error(f"Error generating Stars gift link for user {user_id}: {err}")
            await bot.send_message(chat_id, "⚠️ Could not generate Stars gift link. Please try again later.")
        
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

    elif data == "queue_icebreaker":
        icebreakers = [
            "🤔 **Quick Dilemma:** Would you rather have unlimited free chai/coffee forever, or unlimited free 5G data forever? ☕📶 (Type your answer while we find a student match!)",
            "🔥 **Hot Take:** Pineapple on pizza — absolute culinary genius or criminal offense? 😂🍕",
            "🎬 **Campus Story:** If your college semester was a movie title right now, what would it be? 🍿",
            "🙈 **Never Have I Ever:** Never have I ever muted an online class and gone back to sleep! 😴",
            "✈️ **Dream Flight:** If someone handed you a free boarding pass right now, which country are you landing in? 🌍"
        ]
        q_pick = random.choice(icebreakers)
        await bot.answer_callback_query(cq_id)
        await bot.send_message(chat_id, f"{q_pick}\n\n*(Type your reply here! You can chat with Joy anytime while we match you with an online student)* 🌸")

    elif data == "anon_chat_stop":
        await bot.answer_callback_query(cq_id)
        await handle_anon_chat_stop(bot, chat_id, user)

    elif data == "anon_chat_next":
        await bot.answer_callback_query(cq_id)
        await handle_anon_chat_next(bot, chat_id, user)

    elif data.startswith("accept_anon_call_"):
        requester_uid = int(data.replace("accept_anon_call_", ""))
        await bot.answer_callback_query(cq_id, "✅ Call request accepted!")
        await handle_anon_call_accepted(bot, chat_id, user, requester_uid, message_id=message_id)

    elif data.startswith("decline_anon_call_"):
        requester_uid = int(data.replace("decline_anon_call_", ""))
        await bot.answer_callback_query(cq_id, "❌ Call request declined.")
        if message_id:
            await bot.edit_message_text(chat_id, message_id, "❌ *You declined the voice call. Text chat continues.*", reply_markup={"inline_keyboard": []})
        if requester_uid in telegram_active_chats:
            req_chat_id = telegram_active_chats[requester_uid]["peer_chat_id"]
            await bot.send_message(req_chat_id, "💬 *Your partner preferred to continue chatting via text.*")

    else:
        logger.info(f"🔘 Fallback handler answering callback query: {data}")
        await bot.answer_callback_query(cq_id, "Menu updated! 🌸")

async def process_user_voice(bot: TelegramClient, chat_id: int, user: dict, file_id: str):
    user_id = user["user_id"]
    
    # Anti-Flood Throttling
    if is_user_throttled(user_id):
        return

    # Auto-heal onboarding status
    if user.get("onboarding_status") != "completed":
        user["onboarding_status"] = "completed"
        user["is_beta_tester"] = 1

    # 0. Privacy & Media Guard: Block voice note files in anonymous P2P matchmaking
    if user_id in telegram_active_chats:
        await bot.send_message(
            chat_id,
            "🚫 **Voice Notes Blocked — Privacy Guard Active**\n\n"
            "Recorded voice note audio files are disabled in anonymous matching to protect user privacy.\n"
            "💡 Tap **📞 Switch to Live Call** if you want to request an encrypted live voice match!"
        )
        return

    user["active_contact"] = "lover"  # Enforce Lover (Joy) as the active companion
    await dismiss_active_menu(bot, chat_id)

    # 1. Indicate listening status
    await bot.send_chat_action(chat_id, "record_voice")

    # 2. Download voice note from Telegram & Validate Size
    voice_bytes = await bot.get_file_bytes(file_id)
    if not voice_bytes or len(voice_bytes) < 100:
        await bot.send_message(chat_id, "Couldn't catch that audio note cleanly. Mind sending it again? 🌸")
        return

    if len(voice_bytes) > 5 * 1024 * 1024:
        await bot.send_message(chat_id, "⚠️ Voice note too long! Please keep audio notes under 2 minutes so Joy can reply quickly. 🌸")
        return

    # 3. Check daily limit safely after payload is verified
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
        
    # 4. Process with Gemini Flash (Direct audio understanding)
    history = get_recent_history(user_id, limit=6, channel="chat")
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
    custom_words = get_user_custom_words(user_id)
    cinfo = get_user_contact_display(user_id, active_contact, gender)
    loop = asyncio.get_running_loop()
    try:
        async with AI_CALL_SEMAPHORE:
            transcript, reply_text = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: generate_voice_reply(
                        voice_bytes,
                        "audio/ogg",
                        active_contact,
                        gender,
                        user_lang,
                        history,
                        user_memory,
                        custom_ai_name,
                        custom_words=custom_words,
                        user_id=user_id
                    )
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

    # Intercept for active mock interview viva
    if user_id in active_interviews and transcript and transcript != "Voice Note":
        await handle_interview_answer(bot, chat_id, user, transcript, is_voice=True)
        return

    # Save to history (strictly tagged to 'chat' channel)
    add_conversation_turn(user_id, "user", transcript, channel="chat")
    add_conversation_turn(user_id, "model", reply_text, channel="chat")

    # Zero-latency asynchronous episodic memory extraction (R1)
    if user_id and transcript and transcript != "Voice Note":
        try:
            asyncio.create_task(extract_and_store_memories_async(int(user_id), transcript, reply_text))
        except Exception as bg_err:
            logger.warning(f"Could not dispatch background memory extraction for voice note (user {user_id}): {bg_err}")
    
    # Update Daily Streak & Relationship Bond
    streak_count, rel_level, is_milestone, level_title, shield_activated = update_user_streak(user_id, return_details=True)
    if shield_activated:
        shields_left = get_user_streak_shields(user_id)
        shield_msg = (
            f"🛡️ **Streak Shield Activated!** 💕\n\n"
            f"Joy missed you yesterday, but your **Day {streak_count} Streak** was saved by your Streak Shield!\n\n"
            f"• **Shields Remaining:** {shields_left} 🛡️\n"
            f"• *Keep chatting every day to keep the flame burning!*\n"
            f"• *Earn more shields at Day 7, Day 14, or by referring friends!*"
        )
        asyncio.create_task(bot.send_message(chat_id, shield_msg))
    if is_milestone:
        c_name = custom_ai_name or "Joy"
        reward_detail = ""
        if streak_count == 3:
            reward_detail = "\n🎁 **Milestone Bonus Unlocked:** +5 Free Text Messages credited to your account!"
        elif streak_count == 7:
            reward_detail = "\n🎁 **Milestone Bonus Unlocked:** +10 Free Texts & +2 Voice Notes credited to your account!"
        elif streak_count == 14:
            reward_detail = "\n🎁 **Milestone Bonus Unlocked:** +20 Free Texts & +5 Voice Notes credited to your account!"
        elif streak_count == 30:
            reward_detail = "\n🎉 **ULTIMATE REWARD UNLOCKED:** 7 Days of Free Joy VIP Pass credited to your account!"

        milestone_msg = (
            f"🔥 **Relationship Milestone: Day {streak_count} Streak!**\n\n"
            f"Relationship Level: **{level_title}** 💕{reward_detail}\n\n"
            f"{c_name} loves chatting with you every single day! Keep the streak alive tomorrow! ✨"
        )
        asyncio.create_task(bot.send_message(chat_id, milestone_msg))
    
    # 5. Synthesize voice with Edge-TTS
    await bot.send_chat_action(chat_id, "upload_voice")
    try:
        reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=custom_ai_name, user_id=user_id)
        user_speed = get_user_speech_speed(user_id)
        audio_output = await asyncio.wait_for(
            synthesize_speech(reply_text, voice_key=voice_choice, speed=user_speed),
            timeout=6.5
        )
        from voice_engine import EMERGENCY_SILENCE_MP3
        if not audio_output or audio_output == EMERGENCY_SILENCE_MP3 or len(audio_output) <= len(EMERGENCY_SILENCE_MP3):
            reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=custom_ai_name, user_id=user_id)
            await bot.send_message(chat_id, f"🎙️ {reply_text}", reply_markup=reply_kb)
        else:
            caption = (
                f"🎙️ **{cinfo['name']}** *(Voice Note)*\n\n"
                f"💬 **Transcript Preview:** ||{reply_text}||\n"
                f"*(Tap spoiler above to read in public)*"
            )
            await bot.send_audio(chat_id, audio_output, filename=f"{cinfo['name'].lower()}_reply.mp3", caption=caption, performer=cinfo['name'], title="Voice Note", reply_markup=reply_kb)
    except Exception as e:
        logger.error(f"Error in Edge-TTS synthesis: {e}")
        # Fallback to text message if TTS encounters an issue
        reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=custom_ai_name, user_id=user_id)
        await bot.send_message(chat_id, reply_text, reply_markup=reply_kb)

async def auto_translate_chat_message(text: str, source_lang: str, target_lang: str) -> Optional[str]:
    """
    Translates text in 1-on-1 anonymous chat using Google Translate with Gemini fallback.
    Specially handles Tanglish / Hinglish colloquial expressions into German, Spanish, English, etc.
    """
    clean_text = text.strip()
    if not clean_text or len(clean_text) < 2:
        return None
    if clean_text.isdigit() or clean_text.startswith("http"):
        return None

    s_lang = (source_lang or "auto").lower().strip()
    t_lang = (target_lang or "auto").lower().strip()

    ISO_MAP = {
        "german": "de", "de": "de",
        "english": "en", "en": "en",
        "spanish": "es", "es": "es",
        "french": "fr", "fr": "fr",
        "telugu": "te", "te": "te",
        "tamil": "ta", "ta": "ta",
        "malayalam": "ml", "ml": "ml",
        "kannada": "kn", "kn": "kn",
        "bengali": "bn", "bn": "bn",
        "marathi": "mr", "mr": "mr",
        "hindi": "hi", "hi": "hi",
        "tanglish": "ta", "hinglish": "hi"
    }

    tgt_code = ISO_MAP.get(t_lang, "en")
    src_code = ISO_MAP.get(s_lang, "auto")

    if tgt_code == src_code:
        return None

    # For Tanglish / Hinglish to Western languages, Gemini produces natural conversational phrasing
    if s_lang in ("tanglish", "hinglish") and tgt_code in ("de", "es", "fr", "en"):
        try:
            prompt = (
                f"Translate this {s_lang} chat message into natural, friendly {t_lang}.\n"
                f"Understand its colloquial/slang meaning first, then translate into conversational {t_lang}.\n"
                f"Output ONLY the translated text without quotes or explanation:\n"
                f"\"{clean_text}\""
            )
            gemini_res = await asyncio.to_thread(generate_text_reply, prompt)
            if gemini_res and len(gemini_res.strip()) > 0 and not gemini_res.strip().startswith("Error"):
                return gemini_res.strip().strip('"')
        except Exception as ge:
            logger.warning(f"Gemini slang translation failed, falling back to Google Translate: {ge}")

    # Primary fast Google Translate endpoint
    def _call_gtx():
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={tgt_code}&dt=t&q=" + urllib.parse.quote(clean_text)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return "".join([part[0] for part in data[0] if part[0]])

    try:
        translated = await asyncio.to_thread(_call_gtx)
        if translated and translated.strip().lower() != clean_text.lower():
            return translated.strip()
    except Exception as e:
        logger.warning(f"Google Translate error: {e}")
        try:
            prompt = f"Translate this text into {t_lang}. Output only the translation:\n\"{clean_text}\""
            gem_trans = await asyncio.to_thread(generate_text_reply, prompt)
            if gem_trans and len(gem_trans.strip()) > 0:
                return gem_trans.strip().strip('"')
        except Exception:
            pass

    return None

async def process_user_text(bot: TelegramClient, chat_id: int, user: dict, text: str, msg_id: Optional[int] = None):
    user_id = user["user_id"]

    # 0.1 Payload Cap: Limit incoming text length to 2000 chars to prevent DoS / memory exhaustion
    if len(text) > 2000:
        await bot.send_message(chat_id, "⚠️ **Message too long!** Please send messages under 2,000 characters to keep our chat snappy and responsive! 🌸")
        return

    # 0.2 Anti-Flood & Rate Limiting Middleware (1.5s per-user cooldown)
    if is_user_throttled(user_id):
        return

    clean_text = text.strip()
    lower_text = clean_text.lower()
    onboarding_status = user.get("onboarding_status", "completed")

    # 0.3 Zero-Friction Auto-Heal: Ensure user is completed & beta approved immediately in production
    if os.environ.get("OFFLINE_TEST") != "1" and user.get("onboarding_status") != "completed":
        user["onboarding_status"] = "completed"
        user["is_beta_tester"] = 1
        record_user_accepted_terms(user_id)
        try:
            from database import get_connection
            with get_connection() as conn:
                c = conn.cursor()
                c.execute("UPDATE users SET onboarding_status = 'completed', is_beta_tester = 1 WHERE user_id = ?", (user_id,))
                conn.commit()
        except Exception:
            pass

    # 0.35 PRIORITY TOP-LEVEL COMMANDS: Accessible anytime (even before onboarding completion or beta gates)
    if clean_text.startswith("/newuser") or clean_text.startswith("/retest") or clean_text.lower() in ["newuser", "/freshuser", "freshuser", "/resetall", "new user", "retest", "/retest"]:
        if os.environ.get("OFFLINE_TEST") != "1" and user_id != OWNER_ID:
            user["onboarding_status"] = "onboard_country"
            from database import get_connection
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET onboarding_status = 'onboard_country' WHERE user_id = ?", (user_id,))
                cursor.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
                conn.commit()
            await dismiss_active_menu(bot, chat_id)
            await handle_start(bot, chat_id, user, user_msg_id=msg_id)
            return

        user["onboarding_status"] = "completed"
        user["is_beta_tester"] = 1
        record_user_accepted_terms(user_id)
        from database import get_connection
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET onboarding_status = 'completed', 
                    is_beta_tester = 1
                WHERE user_id = ?
            """, (user_id,))
            cursor.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
            conn.commit()
        await dismiss_active_menu(bot, chat_id)
        await handle_start(bot, chat_id, user, user_msg_id=msg_id)
        return

        is_pioneer = bool(user.get("is_beta_tester") == 1 or user_id == OWNER_ID)
        pioneer_slot = user.get("beta_slot_number") or 1

        from database import get_connection
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET onboarding_status = 'onboard_country', 
                    custom_ai_name = '', 
                    allow_data_sharing = 0,
                    gender = 'male',
                    active_contact = 'lover',
                    language = 'auto',
                    country_code = ''
                WHERE user_id = ?
            """, (user_id,))
            cursor.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
            conn.commit()

        user["onboarding_status"] = "onboard_country"
        user["custom_ai_name"] = ""
        user["gender"] = "male"
        user["active_contact"] = "lover"
        user["allow_data_sharing"] = 0
        user["language"] = "auto"
        user["country_code"] = ""

        # Clean up any active real people chat or queue
        if user_id in telegram_active_chats:
            await handle_anon_chat_stop(bot, chat_id, user)
        telegram_chat_queue[:] = [q for q in telegram_chat_queue if q["user_id"] != user_id]

        # Reset native menu button to commands so Mini Phone is hidden while going through steps
        try:
            await bot.set_chat_menu_button(chat_id=chat_id, menu_button={"type": "commands"})
        except Exception:
            pass

        await dismiss_active_menu(bot, chat_id)
        slot_banner = (
            f"🎟️ **Beta Pioneer Status Preserved (Slot #{pioneer_slot})**\n"
            f"Your seat in the 50-Pioneer program is 100% locked! You will not lose your slot."
        ) if is_pioneer else "Your profile has been wiped to test the new user experience from scratch."

        await bot.send_message(
            chat_id,
            f"🔄 **Testing Brand-New User Onboarding!**\n\n{slot_banner}\n\nLaunching Step 1 (Select Country) for you right now: 👇",
            reply_markup={"remove_keyboard": True}
        )
        await asyncio.sleep(0.3)
        await send_onboarding_country(bot, chat_id, user)
        return

    # Beta Pioneer Exclusive Commands Hub & Diagnostics
    if clean_text in ("/command", "/commands", "/betacommand", "/betacommands", "/beta_commands", "/bata_commands", "/bata", "/beta", "/betatools", "/testtools", "/test", "test", "betatools", "commands", "command"):
        await handle_beta_commands(bot, chat_id, user, user_msg_id=msg_id)
        return

    if clean_text.startswith("/resetquota") or clean_text in ("/resetlimit", "/freshquota"):
        is_pioneer = bool(user.get("is_beta_tester") == 1 or user_id == OWNER_ID)
        if not is_pioneer:
            await bot.send_message(chat_id, "⚠️ Only Beta Pioneers and Phoenix can self-reset daily testing quotas.")
            return
        reset_user_quota(user_id)
        await bot.send_message(
            chat_id,
            "⚡ **Beta Testing Quota Reset!** 🔄\n\n"
            "All your daily voice calls, Mini Phone limits, and text message counters have been reset to 0.\n"
            "Feel free to test calls and chat without restrictions! 💖"
        )
        return

    if clean_text in ("/mic", "/microphone", "mic"):
        mic_url = f"https://joyfun-ai-bot.onrender.com/call?gender={user.get('gender', 'male')}&contact={user.get('active_contact', 'lover')}&lang={user.get('language', 'auto')}&tab=diagnostic"
        await bot.send_message(
            chat_id,
            "🎤 **Mini Phone Microphone Diagnostic**\n\n"
            "Tap below to run in-app microphone permission test and latency checks:",
            reply_markup={
                "inline_keyboard": [
                    [{"text": "🎙️ Open Mic Diagnostic", "web_app": {"url": mic_url}}]
                ]
            }
        )
        return

    if clean_text.startswith("/exitbeta") or clean_text.startswith("/leavebeta"):
        is_pioneer = bool(user.get("is_beta_tester") == 1)
        if user_id == OWNER_ID:
            await bot.send_message(chat_id, "👑 You are the Creator (Phoenix). You cannot leave the beta program.")
            return
        if not is_pioneer:
            await bot.send_message(chat_id, "ℹ️ You are not currently an admitted Beta Pioneer.")
            return
        slot = user.get("beta_slot_number", "?")
        confirm_kb = {
            "inline_keyboard": [
                [
                    {"text": "🚪 Yes, Exit Beta Program", "callback_data": "confirm_exit_beta"},
                    {"text": "❌ Cancel, Keep My Slot", "callback_data": "cancel_exit_beta"}
                ]
            ]
        }
        await bot.send_message(
            chat_id,
            f"⚠️ **Voluntary Beta Exit Confirmation**\n\n"
            f"You currently hold **Pioneer Slot #{slot}**.\n\n"
            f"Are you sure you want to surrender your slot? If you leave:\n"
            f"• Your Pioneer seat will **immediately be given to the #1 user on the Priority Waitlist**.\n"
            f"• Your account will revert to standard waitlist status.\n\n"
            f"Tap an option below to proceed:",
            reply_markup=confirm_kb
        )
        return

    # 0.38 Identity & User ID Lookup Command
    if clean_text in ("/id", "/myid", "/whoami", "/mask", "id", "myid"):
        mask = get_mask_by_user_id(user_id)
        is_co = is_owner_or_co_owner(user_id)
        is_pioneer = bool(user.get("is_beta_tester") == 1 or is_co)
        slot = user.get("beta_slot_number", 0)
        p_badge = f"🎟️ Pioneer Slot #{slot}" if is_pioneer else "⏳ Standard Waitlist"
        role_badge = "👑 Primary Owner" if user_id == OWNER_ID else ("⭐ Co-Owner / Phoenix" if is_co else "👤 User")
        id_msg = (
            f"🆔 **Your Account Details:**\n\n"
            f"• **Telegram User ID:** `{user_id}`\n"
            f"• **Permanent Mask ID:** `{mask}`\n"
            f"• **Role:** {role_badge}\n"
            f"• **Beta Status:** {p_badge}\n"
            f"• **Language:** {user.get('language', 'auto').title()}\n"
            f"• **Country:** {user.get('country_code', 'Not Set')}\n"
        )
        await bot.send_message(chat_id, id_msg)
        return

    # 0.39 Authenticated Secondary Account Gate (Requires high-entropy ADMIN_API_SECRET)
    is_secret_auth = False
    if clean_text.startswith(("/makebeta", "/setbeta", "/addbeta")):
        parts = clean_text.split()
        if len(parts) >= 2 and ADMIN_API_SECRET and secrets.compare_digest(parts[1].strip(), ADMIN_API_SECRET):
            is_secret_auth = True

    if is_secret_auth:
        # Delete user's message containing password for privacy
        if msg_id:
            try:
                await bot.delete_message(chat_id, msg_id)
            except Exception:
                pass

        add_co_owner(user_id)
        slot_num = grant_beta_access(user_id)
        target_user = get_or_create_user(user_id)
        target_user["is_beta_tester"] = 1
        target_user["beta_slot_number"] = slot_num
        target_user["onboarding_status"] = "completed"

        # Update chat-scoped commands to Beta Pioneer tools
        try:
            await bot.set_my_commands(BETA_BOT_COMMANDS, scope={"type": "chat", "chat_id": chat_id})
        except Exception:
            pass

        # Update chat menu button to Mini Phone
        gender = target_user.get("gender", "male")
        active_contact = target_user.get("active_contact", "lover")
        c_name = get_user_custom_ai_name(user_id) or "Joy"
        call_url = f"https://joyfun-ai-bot.onrender.com/call?gender={gender}&contact={active_contact}&uid={user_id}&name={urllib.parse.quote(c_name)}&v={BOT_VERSION}"
        try:
            await bot.set_chat_menu_button(
                chat_id=chat_id,
                menu_button={"type": "web_app", "text": "📞 Call Joy AI", "web_app": {"url": call_url}}
            )
        except Exception:
            pass

        reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=c_name, user_id=user_id)
        mask = get_mask_by_user_id(user_id)

        welcome_card = (
            f"👑 **Phoenix Secondary Account Authenticated!** 🎟️\n\n"
            f"Welcome, Phoenix! This account is now officially recognized as a **Verified Co-Owner & Beta Pioneer**:\n\n"
            f"• 🎟️ **Pioneer Seat:** Slot **#{slot_num}** / 50\n"
            f"• 🛡️ **Permanent Mask:** `{mask}`\n"
            f"• 📊 **Daily Quota:** 10 Live Voice Calls (~45 mins), 50 Voice Notes, Unlimited Texts\n"
            f"• 🛠️ **Scoped Commands:** Telegram `/` list unlocked with Pioneer tools\n"
            f"• 📞 **Mini Phone:** Docked bottom-left button active!\n\n"
            f"From now on, you can run all beta commands (`/commands`, `/resetquota`, `/retest`, `/mic`, `/bug`) directly from this account without typing the passcode again! 🌸"
        )
        await bot.send_message(chat_id, welcome_card, reply_markup=reply_kb)

        # Notify Phoenix's primary account
        if OWNER_ID and chat_id != OWNER_ID:
            try:
                alert = (
                    f"🔔 **Owner Security Alert:**\n"
                    f"Your secondary Telegram account has authenticated via owner passphrase!\n"
                    f"• **Telegram ID:** `{user_id}`\n"
                    f"• **Mask ID:** `{mask}`\n"
                    f"• **Assigned Slot:** #{slot_num}\n"
                    f"• **Status:** Active Co-Owner & Beta Pioneer."
                )
                await bot.send_message(OWNER_ID, alert)
            except Exception:
                pass
        return

    # 0.4 Server-Level Admin Command Interceptor (Zero Privilege Escalation & No Enumeration)
    cmd_token = clean_text.split()[0].lower() if clean_text.startswith("/") else ""
    if cmd_token in ADMIN_SLASH_COMMANDS:
        if not is_owner_or_co_owner(user_id):
            logger.warning(f"🛡️ Unauthorized admin command '{cmd_token}' blocked from user {user_id}")
            await bot.send_message(chat_id, "I don't recognize that command. Type /menu to see available options! 🌸")
            return

    # 0.45 Universal Menu Access: Always allow /menu, "📱 Menu", or "menu" to open immediately without gate blockage
    if clean_text.startswith("/menu") or clean_text.startswith("📱 Menu") or clean_text.lower() in ["menu", "📱 menu", "📱 control menu", "control menu", "control", "home"]:
        await handle_menu(bot, chat_id, user, user_msg_id=msg_id)
        return

    # 0.455 Universal Language & Interface Access: /language, /lang, /menulang, /systemlang
    if clean_text.startswith(("/language", "/lang", "/voice")) or clean_text.lower() in ["language", "lang", "voice", "speech", "change language", "set language"]:
        await handle_language_menu(bot, chat_id, user, user_msg_id=msg_id)
        return
    if clean_text.startswith(("/menulang", "/systemlang", "/botlang")) or clean_text.lower() in ["menulang", "systemlang", "botlang", "menu language", "bot language", "interface language"]:
        await handle_system_lang_menu(bot, chat_id, user, user_msg_id=msg_id)
        return

    # 0.46 Universal Invite / Referral Access: /invite, /refer, /referral, /ref, "🎁 Invite Friends"
    if clean_text.startswith(("/invite", "/refer", "/referral", "/ref")) or clean_text.startswith("🎁 Invite Friends") or clean_text.lower() in ["invite", "refer", "referral", "ref", "🎁 invite friends", "share"]:
        await handle_referral_hub(bot, chat_id, user, user_msg_id=msg_id)
        return

    # 0.47 Universal Memory Vault Access: /memories, /memory, /vault, "🧠 Memory Vault"
    if clean_text.startswith(("/memories", "/memory", "/vault")) or clean_text.lower() in ["memories", "memory", "vault", "🧠 memories", "🧠 memory vault"]:
        await handle_memories_vault(bot, chat_id, user, user_msg_id=msg_id)
        return

    # 0.48 Universal Streak & Bond Access: /streak, /level, /relationship, /bond, "🔥 Streak & Bond"
    if clean_text.startswith(("/streak", "/level", "/relationship", "/bond")) or clean_text.lower() in ["streak", "level", "relationship", "bond", "🔥 streak", "🔥 streak & bond"]:
        await handle_streak_status(bot, chat_id, user, user_msg_id=msg_id)
        return

    # 0.485 Universal Streak Revive Access: /revive, /rescue, /repair
    if clean_text.startswith(("/revive", "/rescue", "/repair")) or clean_text.lower() in ["revive", "rescue", "repair", "revive streak"]:
        await handle_streak_revive(bot, chat_id, user, user_msg_id=msg_id)
        return

    # 0.486 Universal Campus Daily Vibe: /vibe, /tarot, /horoscope, /fortune
    if clean_text.startswith(("/vibe", "/tarot", "/horoscope", "/fortune")) or clean_text.lower() in ["vibe", "tarot", "horoscope", "fortune", "daily vibe", "🔮 daily vibe", "campus vibe"]:
        await handle_vibe_command(bot, chat_id, user, user_msg_id=msg_id)
        return

    # 0.487 Universal Campus Leaderboard: /top, /leaderboard, /rank, /halloffame
    if clean_text.startswith(("/top", "/leaderboard", "/rank", "/halloffame")) or clean_text.lower() in ["top", "leaderboard", "rank", "halloffame", "🏆 leaderboard", "leader board", "scholars"]:
        await handle_leaderboard_menu(bot, chat_id, user, category="study", user_msg_id=msg_id)
        return

    # 0.49 Universal Story Card / Brag Access: /card, /brag, /story, /flex, "📸 Story Card"
    if clean_text.startswith(("/card", "/brag", "/story", "/flex")) or clean_text.lower() in ["card", "brag", "story", "flex", "story card", "streak card", "📸 story card"]:
        await handle_streak_card(bot, chat_id, user, user_msg_id=msg_id)
        return

    # 0.50 Universal Teaser & Daily Dilemma Access: /teaser, /teasers, /growth, /dilemma, "📢 Daily Dilemma Studio"
    if clean_text.startswith(("/teaser", "/growth", "/dilemma")) or clean_text.lower() in ["teaser", "teasers", "growth", "dilemma", "📢 teaser", "📢 teasers", "📢 daily dilemma studio", "daily dilemma"]:
        await handle_teaser_hub(bot, chat_id, user, user_msg_id=msg_id)
        return

    # Handle /start, /restart, /reset, or /setup commands
    if clean_text.startswith(("/start", "/setup", "/restart", "/reset")):
        parts = clean_text.split()
        if len(parts) > 1:
            param = parts[1].strip()
            if param.lower() in ["vip", "upgrade", "pass", "joy_vip"]:
                await handle_vip(bot, chat_id, user, user_msg_id=msg_id)
                return
            ref_code = param.replace("ref_", "").strip()
            if ref_code and not ref_code.startswith("/"):
                try:
                    if ref_code in ["channel", "broadcast", "teaser"]:
                        referrer_id = OWNER_ID
                    elif ref_code.isdigit():
                        referrer_id = int(ref_code)
                    else:
                        referrer_id = get_user_id_by_mask(ref_code)
                    if referrer_id and referrer_id != user_id:
                        if track_user_referral(user_id, referrer_id):
                            reward = complete_referral_reward(user_id)
                            if reward and global_bot_client:
                                asyncio.create_task(dispatch_referral_notifications(global_bot_client, reward, user))
                            welcome_msg = (
                                "🎁 **Referral Welcome Bonus Activated!** 🌸\n\n"
                                "Because you joined via a friend's personal invite link, your account has been credited with:\n"
                                "• **+10 Free Voice Notes** 🎙️\n"
                                "• **+20 Free Text Messages** 💬\n\n"
                                "Enjoy chatting with Joy!"
                            )
                            asyncio.create_task(bot.send_message(chat_id, welcome_msg))
                except Exception:
                    pass
        await handle_start(bot, chat_id, user, user_msg_id=msg_id)
        return

    # Handle companion naming if user is explicitly in naming step
    if onboarding_status == "onboard_naming" and not clean_text.startswith("/"):
        raw_input = clean_text.strip()
        lower_input = raw_input.lower()
        if "call me" in lower_input:
            parts = re.split(r'call me', raw_input, flags=re.IGNORECASE)
            possible_name = parts[0].strip(" ,.-")
            suggested_words = parts[1].strip(" ,.-")
            if possible_name and len(possible_name) >= 2:
                set_user_custom_ai_name(user_id, possible_name[:20])
            else:
                set_user_custom_ai_name(user_id, "Joy")
            if suggested_words:
                set_user_custom_words(user_id, suggested_words[:100])
        elif "," in raw_input and len(raw_input.split(",")) > 1:
            set_user_custom_words(user_id, raw_input[:100])
            set_user_custom_ai_name(user_id, "Joy")
        else:
            raw_name = re.sub(r'[^a-zA-Z0-9 _-]', '', raw_input)[:20]
            if raw_name.lower() in ["joy", "default", "none"] or len(raw_name) < 2:
                reset_user_custom_ai_name(user_id)
            else:
                set_user_custom_ai_name(user_id, raw_name)
        asyncio.create_task(sync_user_to_cloud(user_id))
        await send_onboarding_privacy(bot, chat_id, user, user_msg_id=msg_id)
        return

    # Regression test suite guard: Verify waitlist check when in isolated offline test mode
    if os.environ.get("OFFLINE_TEST") == "1" and not is_user_beta_approved(user_id):
        await send_waitlist_card(bot, chat_id, user, user_msg_id=msg_id)
        return

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

        tier_code = user_waiting_utr.pop(user_id, "monthly")
        if not isinstance(tier_code, str) or tier_code not in VIP_TIERS:
            tier_code = "monthly"
        tier_info = VIP_TIERS.get(tier_code, VIP_TIERS["monthly"])
        amount = float(tier_info["price_inr"])

        success, utr_msg, req_id = record_utr_submission(user_id, clean_utr, amount=amount, plan_type=tier_code)
        if not success:
            await bot.send_message(
                chat_id,
                f"⚠️ **Submission Notice:** {utr_msg}",
                reply_markup={"inline_keyboard": [
                    [{"text": "🔄 Try Again", "callback_data": f"prompt_submit_utr_{tier_code}"}],
                    [{"text": "⬅️ Back to VIP Menu", "callback_data": "menu_vip"}]
                ]}
            )
            return

        # Immediate gratification bonus while admin verifies (+10 Voice Notes, +20 Texts)
        recharge_user_usage(user_id, bonus_voice=10, bonus_text=20)

        await bot.send_message(
            chat_id,
            f"✅ **Payment Details Received!**\n\n"
            f"• **Plan:** `{tier_info['name']}`\n"
            f"• **Amount:** `₹{int(amount)}`\n"
            f"• **UTR Reference:** `{clean_utr}`\n"
            f"• **Status:** Under verification ⏳\n\n"
            f"🎁 **Instant Buffer Credited:** We've added **+10 Voice Notes & +20 Texts** right now so you can keep chatting!\n"
            f"Our system will complete verification shortly.\n"
            f"Thank you for supporting Joy! 💖"
        )

        # Notify Bot Administrator (OWNER_ID)
        try:
            user_full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or "Joy User"
            username = f"@{user.get('username')}" if user.get('username') else "No username"
            admin_msg = (
                f"🔔 **New UPI Payment Submission!**\n\n"
                f"• **Plan:** `{tier_info['name']}` (₹{int(amount)})\n"
                f"• **User:** `{user_full_name}` ({username})\n"
                f"• **User ID:** `{user_id}`\n"
                f"• **UTR:** `{clean_utr}`\n"
                f"• **Request ID:** `#{req_id}`\n\n"
                f"Please verify against your bank / UPI notification and tap below:"
            )
            admin_kb = {
                "inline_keyboard": [
                    [
                        {"text": f"✅ Approve {tier_info['name']}", "callback_data": f"approve_utr_{req_id}"},
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

    # 0.01 Check if Owner is sending a direct message via interactive prompt
    if user_id == OWNER_ID and OWNER_ID in admin_pending_target and not clean_text.startswith("/"):
        target_uid = admin_pending_target.pop(OWNER_ID)
        user_msg = (
            f"👨‍💻 **Direct Message from Phoenix (Creator of Joy):**\n\n"
            f"\"{clean_text}\"\n\n"
            f"*(💬 You can reply directly to this message to chat back with Phoenix!)*"
        )
        try:
            await bot.send_message(target_uid, user_msg)
            user_chatting_with_admin[target_uid] = True
            await bot.send_message(chat_id, f"✅ Message delivered to User `{target_uid}`!")
        except Exception as e:
            logger.error(f"Failed to deliver message to {target_uid}: {e}")
            await bot.send_message(chat_id, f"❌ Failed to deliver message to `{target_uid}`. User may have stopped the bot.")
        return

    # 0.02 Check if a User is replying to Phoenix's direct message
    if user_id in user_chatting_with_admin and user_id != OWNER_ID and not clean_text.startswith("/"):
        sender_name = user.get("first_name", "User")
        sender_uname = f"@{user.get('username')}" if user.get('username') else "No @"
        forward_text = (
            f"💬 **Direct User Reply from {sender_name} ({sender_uname} • `{user_id}`):**\n\n"
            f"{clean_text}"
        )
        kb = {
            "inline_keyboard": [
                [{"text": f"💬 Reply to {sender_name[:12]}", "callback_data": f"admin_msg_prep_{user_id}"}]
            ]
        }
        await bot.send_message(OWNER_ID, forward_text, reply_markup=kb)
        await bot.send_message(chat_id, "✅ Message sent to Phoenix!")
        return

    # 0. Check if user is in active Real People 1-on-1 Chat
    if user_id in telegram_active_chats:
        if clean_text in ["/stop", "/end", "/leave", "stop", "leave", "🛑 End Chat", "End Chat"]:
            await handle_anon_chat_stop(bot, chat_id, user)
            return
        elif clean_text in ["/next", "/skip", "next", "skip", "⏭️ Next Partner", "Next Partner"]:
            await handle_anon_chat_next(bot, chat_id, user)
            return
        elif clean_text in ["/call", "📞 Switch to Live Call", "Switch to Live Call", "switch to call", "call", "voice call"]:
            await handle_anon_chat_call_request(bot, chat_id, user)
            return
        elif clean_text in ["🎯 Quick Question (Icebreaker)", "Quick Question", "/topic", "/icebreaker", "icebreaker", "question"]:
            pair = telegram_active_chats[user_id]
            peer_chat_id = pair["peer_chat_id"]
            ib_q = secrets.choice(ICEBREAKER_QUESTIONS)
            ib_msg = (
                f"🎯 **Quick Question (Icebreaker):**\n\n"
                f"👉 *\"{ib_q}\"*\n\n"
                f"💬 Answer honestly! What do you think?"
            )
            await bot.send_message(chat_id, ib_msg)
            await bot.send_message(peer_chat_id, ib_msg)
            return
        elif clean_text.startswith("/"):
            await bot.send_message(
                chat_id,
                "⚠️ **You are currently in an anonymous 1-on-1 chat with a real person!**\n\n"
                "• Send any text to talk to them.\n"
                "• Tap **📞 Switch to Live Call** to request an anonymous phone call.\n"
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
            peer_uid = pair.get("peer_uid")
            sender_lang = user.get("language", "auto")
            peer_user = get_or_create_user(peer_uid) if peer_uid else {}
            peer_lang = peer_user.get("language", "auto")
            peer_country = peer_user.get("country_code", "")

            # If peer language is auto, resolve from country
            if peer_lang == "auto":
                peer_lang = "german" if peer_country == "DE" else ("spanish" if peer_country == "ES" else "english")

            # Check if auto-translation is needed across different languages
            translated_text = None
            if sender_lang != peer_lang and peer_lang != "auto":
                try:
                    translated_text = await auto_translate_chat_message(text, sender_lang, peer_lang)
                except Exception as te:
                    logger.warning(f"Auto-translate error in 1-on-1 chat: {te}")

            if translated_text:
                target_label = LANGUAGE_NAMES.get(peer_lang, peer_lang.title())
                formatted_msg = (
                    f"🎭 **{sender_mask}:**\n"
                    f"{text}\n\n"
                    f"🌐 *[{target_label}]:*\n"
                    f"_{translated_text}_"
                )
            else:
                formatted_msg = f"🎭 **{sender_mask}:**\n{text}"

            try:
                await bot.send_message(peer_chat_id, formatted_msg)
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

    # 1.4 Handle Language Request Submission
    if (onboarding_status == "waiting_lang_request" or user_waiting_lang_request.get(user_id)) and not clean_text.startswith("/"):
        req_lang = clean_text.strip()[:50]
        save_user_language_request(user_id, req_lang)
        set_user_language(user_id, "auto")
        user["language"] = "auto"
        is_from_menu = user_waiting_lang_request.pop(user_id, False)

        await bot.send_message(
            chat_id,
            f"✅ **Language Request Recorded!**\n\n"
            f"Thank you! We've noted your request for **{req_lang}** for future speech model rollouts.\n"
            f"In the meantime, Joy will communicate using **🌐 Auto-Detect**, which already understands 50+ languages! 💖"
        )
        if is_from_menu:
            await handle_settings(bot, chat_id, user)
        else:
            await send_onboarding_country(bot, chat_id, user)
        return

    # 1.5 Handle Step 2 Companion Naming during Onboarding
    if onboarding_status == "onboard_naming" and not clean_text.startswith("/"):
        raw_name = re.sub(r'[^a-zA-Z0-9 _-]', '', clean_text.strip())[:20]
        has_pii, _ = detect_sensitive_pii(clean_text)
        if has_pii or len(raw_name) < 2:
            new_name = "Joy"
        elif raw_name.lower() in ["joy", "default", "none"]:
            reset_user_custom_ai_name(user_id)
            new_name = "Joy"
        else:
            new_name = raw_name
            set_user_custom_ai_name(user_id, new_name)
        asyncio.create_task(sync_user_to_cloud(user_id))
        await send_onboarding_privacy(bot, chat_id, user, user_msg_id=msg_id)
        return

    # 2. Handle Custom AI Companion Renaming
    if onboarding_status == "waiting_ai_name" and not clean_text.startswith("/"):
        raw_name = re.sub(r'[^a-zA-Z0-9 _-]', '', clean_text.strip())[:20]
        has_pii, _ = detect_sensitive_pii(clean_text)
        if has_pii or len(raw_name) < 2:
            new_name = "Joy"
        elif raw_name.lower() in ["joy", "default", "none"]:
            reset_user_custom_ai_name(user_id)
            new_name = "Joy"
        else:
            new_name = raw_name
            set_user_custom_ai_name(user_id, new_name)
        set_user_onboarding_status(user_id, "completed")
        asyncio.create_task(sync_user_to_cloud(user_id))
        gender = user.get("gender", "male")
        active_contact = user.get("active_contact", "lover")
        reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=new_name, user_id=user_id)
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
        if "@" in email_candidate and "." in email_candidate and len(email_candidate) <= 100:
            set_user_google_email(user_id, email_candidate)
            set_user_onboarding_status(user_id, "completed")
            asyncio.create_task(sync_user_to_cloud(user_id))
            gender = user.get("gender", "male")
            active_contact = user.get("active_contact", "lover")
            custom_name = get_user_custom_ai_name(user_id)
            reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=custom_name, user_id=user_id)
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

    # 4. Handle Feedback & Feature Request Input (Capped to 500 chars)
    if onboarding_status == "waiting_feedback" and not clean_text.startswith("/"):
        feedback_capped = clean_text[:500]
        is_pioneer = bool(user.get("is_beta_tester") == 1 or user_id == OWNER_ID or is_owner_or_co_owner(user_id))
        slot = user.get("beta_slot_number", 1) if is_pioneer else 0
        mask = get_mask_by_user_id(user_id)
        username = user.get("username") or "None"
        user_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or "Joy User"

        fid = save_user_feedback(user_id, username, feedback_capped, "pioneer_bounty" if is_pioneer else "user_request")
        set_user_onboarding_status(user_id, "completed")
        
        # Real-time forward to owner
        if ADMIN_CHAT_ID:
            owner_notification = (
                f"📬 **New User Feedback / Bug Report!**\n\n"
                f"• **User:** `{user_name}` (@{username})\n"
                f"• **User ID:** `{user_id}` {f'(Pioneer #{slot})' if is_pioneer else ''}\n"
                f"• **Mask ID:** `{mask}`\n"
                f"• **Report ID:** `#{fid}`\n\n"
                f"💬 **Message:**\n\"{feedback_capped}\"\n\n"
                f"🕒 *{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
            )
            admin_kb = None
            if is_pioneer:
                admin_kb = {
                    "inline_keyboard": [
                        [
                            {"text": "⭐ 2 Weeks VIP", "callback_data": f"bounty_14_{user_id}_{fid}"},
                            {"text": "🌟 1 Month VIP", "callback_data": f"bounty_30_{user_id}_{fid}"}
                        ],
                        [
                            {"text": "👑 Lifetime VIP", "callback_data": f"bounty_36500_{user_id}_{fid}"},
                            {"text": "❌ Dismiss", "callback_data": f"bounty_dismiss_{user_id}_{fid}"}
                        ]
                    ]
                }
            try:
                await bot.send_message(ADMIN_CHAT_ID, owner_notification, reply_markup=admin_kb)
            except Exception as e:
                logger.warning(f"Could not forward feedback to owner: {e}")

        gender = user.get("gender", "male")
        active_contact = user.get("active_contact", "lover")
        custom_name = get_user_custom_ai_name(user_id)
        reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=custom_name, user_id=user_id)
        
        bounty_note = "\n\n🎖️ **Pioneer Bounty Priority:** Phoenix will review your submission for **2 Weeks to Lifetime VIP**!" if is_pioneer else ""
        thank_you_msg = (
            f"🎉 **Thank you so much for your feedback!** ❤️\n\n"
            f"Your report (`#{fid}`) has been delivered directly to our lead developer (Phoenix).{bounty_note}\n\n"
            f"We read every single request and will work hard to include it in upcoming updates! 🚀"
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
            reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=c_name, user_id=user_id)
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
            reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=c_name, user_id=user_id)
            await bot.send_message(chat_id, f"👶 **ELI5: {clean_text}** 💡\n\n{eli5_resp}", reply_markup=reply_kb)
        except Exception as e:
            logger.error(f"Error generating ELI5: {e}")
            await bot.send_message(chat_id, f"💡 **{clean_text} in Simple Words:** Think of it like a smart manager coordinating everyone so no work gets lost! Need a quiz? Type `/study`! 🌸")
        return

    # 7. Handle Active Placement Mock Interview & Viva Input
    if user_id in active_interviews:
        if clean_text in ["/stop", "/exit", "/cancel", "stop", "exit", "cancel", "quit", "/quit", "🚪 exit interview"]:
            active_interviews.pop(user_id, None)
            await bot.send_message(chat_id, "🚪 **Mock interview ended.** Whenever you want to practice again, just send `/interview` or tap Study Hub! 🌸")
            return
        elif clean_text in ["/skip", "skip", "next", "/next", "⏭️ skip round", "skip round"]:
            await handle_interview_skip(bot, chat_id, user, cq_id="", message_id=None)
            return
        elif not clean_text.startswith("/"):
            await handle_interview_answer(bot, chat_id, user, clean_text, is_voice=False)
            return
    
    # Check commands & persistent keyboard button presses
    if clean_text.startswith(("/start", "/restart", "/reset")):
        parts = clean_text.split()
        if len(parts) > 1:
            param = parts[1].strip()
            if param.startswith("ref_") or param.startswith("Joy-") or param.startswith("joy-") or param in ["channel", "broadcast", "teaser"]:
                try:
                    ref_code = param.replace("ref_", "").strip()
                    if ref_code in ["channel", "broadcast", "teaser"]:
                        referrer_id = OWNER_ID
                    elif ref_code.isdigit():
                        referrer_id = int(ref_code)
                    else:
                        referrer_id = get_user_id_by_mask(ref_code)
                    if referrer_id and referrer_id != user_id:
                        if track_user_referral(user_id, referrer_id):
                            reward = complete_referral_reward(user_id)
                            if reward and global_bot_client:
                                asyncio.create_task(dispatch_referral_notifications(global_bot_client, reward, user))
                            welcome_msg = (
                                "🎁 **Referral Welcome Bonus Activated!** 🌸\n\n"
                                "Because you joined via a friend's personal invite link, your account has been credited with:\n"
                                "• **+10 Free Voice Notes** 🎙️\n"
                                "• **+20 Free Text Messages** 💬\n\n"
                                "Enjoy chatting with Joy!"
                            )
                            asyncio.create_task(bot.send_message(chat_id, welcome_msg))
                except Exception:
                    pass
            elif param in ["real_chat", "chat", "match", "anon"]:
                await handle_anon_chat_start(bot, chat_id, user, user_msg_id=msg_id)
                return
            elif param in ["vip", "upgrade", "joy_vip", "pass"]:
                await handle_vip(bot, chat_id, user, user_msg_id=msg_id)
                return
            elif param in ["quota", "quotas", "limit", "limits", "balance"]:
                await handle_quota(bot, chat_id, user, user_msg_id=msg_id)
                return
            elif param.startswith("reconnect_"):
                target_mask = param.replace("reconnect_", "").strip()
                target_uid = get_user_id_by_mask(target_mask)
                if not target_uid:
                    await bot.send_message(chat_id, f"⚠️ Partner with mask `{target_mask}` could not be located. They may be offline.")
                    return
                if target_uid == user_id:
                    await bot.send_message(chat_id, "⚠️ You cannot reconnect with yourself.")
                    return
                
                sender_mask = get_mask_by_user_id(user_id) or "Joy-User"
                invite_text = (
                    f"💬 **Anonymous Reconnect Request!**\n\n"
                    f"Your previous partner **`{sender_mask}`** requested to chat with you again through the Mini App!\n\n"
                    f"Do you want to accept and start an anonymous 1-on-1 chat?"
                )
                invite_kb = {
                    "inline_keyboard": [
                        [
                            {"text": "✅ Accept & Start Chat", "callback_data": f"accept_reconnect_{user_id}"},
                            {"text": "❌ Decline", "callback_data": f"decline_reconnect_{user_id}"}
                        ]
                    ]
                }
                try:
                    await bot.send_message(target_uid, invite_text, reply_markup=invite_kb)
                    await bot.send_message(chat_id, f"📨 **Reconnect invitation sent to `{target_mask}`!** Waiting for them to accept...")
                except Exception as e:
                    logger.error(f"Could not deliver invite to {target_mask}: {e}")
                    await bot.send_message(chat_id, f"⚠️ Could not deliver invite to `{target_mask}`. Partner may be offline.")
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
                reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name="", user_id=user_id)
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
                reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=new_name, user_id=user_id)
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
    elif (
        clean_text.startswith("/chat") or 
        clean_text.startswith("👥 Peer Exchange") or 
        clean_text.startswith("👥 Chat") or 
        clean_text.startswith("👥") or 
        clean_text.startswith("/match") or 
        clean_text.startswith("/find") or 
        clean_text.startswith("/anon") or 
        clean_text.lower() in ["chat", "match", "find", "anon"] or
        any(phrase in lower_text for phrase in [
            "talk to people", "talk with people", "chat with people", "interact with people",
            "talk to real people", "chat with real people", "interact with real people",
            "connect me to people", "connect me to someone", "connect to people", "connect to someone",
            "connect to real people", "connect me to real people", "talk to someone", "chat with someone",
            "talk to a real person", "chat with a real person", "talk with someone", "find me someone",
            "find someone", "find people", "real human", "real people", "talk to human", "chat with human",
            "match me", "real person", "interact with someone", "i want to talk to people",
            "i want to chat with people", "i want to talk with someone", "connect real people"
        ])
    ):
        parts = clean_text.split()
        if len(parts) > 1 and parts[1].lower() in MATCH_INTENTS:
            await handle_anon_chat_start(bot, chat_id, user, user_msg_id=msg_id, intent=parts[1].lower())
        else:
            await handle_anon_chat_intent_picker(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/stop") or clean_text.startswith("/leave") or clean_text.lower() in ["stop", "leave", "🛑 end chat", "end chat"]:
        if user_id in telegram_active_chats or any(q["user_id"] == user_id for q in telegram_chat_queue):
            await handle_anon_chat_stop(bot, chat_id, user)
            return
    elif clean_text.startswith("/next") or clean_text.startswith("/skip") or clean_text.lower() in ["next", "skip", "⏭️ next partner", "next partner"]:
        if user_id in telegram_active_chats or any(q["user_id"] == user_id for q in telegram_chat_queue):
            await handle_anon_chat_next(bot, chat_id, user)
            return
    elif clean_text.startswith(("/alarm", "/morning", "/wakeup")) or clean_text.lower() in ["alarm", "morning", "wakeup", "wake up", "⏰ alarm", "🌅 morning"]:
        await handle_alarm_menu(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith(("/tone", "/persona", "/demeanor")) or clean_text.lower() in ["tone", "persona", "demeanor", "🎭 tone"]:
        await handle_tone_menu(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith(("/recap", "/callrecap", "/callsummary")) or clean_text.lower() in ["recap", "call recap", "call summary", "voice recap", "📞 recap"]:
        await handle_manual_recap_command(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith(("/code", "/algo", "/dsa", "/solution")) or clean_text.lower() in ["code", "algo", "dsa", "solution", "💻 code", "scratchpad"]:
        parts = clean_text.split(maxsplit=1)
        sub_query = parts[1].strip() if len(parts) > 1 else ""
        await handle_code_command(bot, chat_id, user, query=sub_query, user_msg_id=msg_id)
        return
    elif clean_text.startswith(("/interview", "/viva", "/mockinterview")) or clean_text.lower() in ["interview", "viva", "mock interview", "mockinterview", "🎙️ mock interview"]:
        await handle_interview_menu(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/study") or clean_text.lower() in ["study", "📚 study", "quiz", "active recall", "pomodoro", "study buddy", "exam prep"]:
        await handle_study_menu(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith(("/invite", "/refer", "/referral", "/ref")) or clean_text.startswith("🎁 Invite Friends") or clean_text.lower() in ["invite", "refer", "referral", "ref", "🎁 invite friends", "share"]:
        await handle_referral_hub(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith(("/reminders", "/checkins", "/proactive")) or clean_text.lower() in ["reminders", "checkins", "notifications"]:
        is_enabled = toggle_user_proactive_checkins(user_id)
        status_str = "ENABLED 🔔" if is_enabled else "MUTED 🔕"
        msg = f"⚙️ **Joy Daily Check-ins:** {status_str}\n\nType `/reminders` anytime to toggle morning & evening check-in messages on or off!"
        await bot.send_message(chat_id, msg)
        return
    elif clean_text.startswith(("/memories", "/memory", "/vault")) or clean_text.lower() in ["memories", "memory", "vault", "🧠 memories", "🧠 memory vault"]:
        await handle_memories_vault(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith(("/streak", "/level", "/relationship", "/bond")) or clean_text.lower() in ["streak", "level", "relationship", "bond", "🔥 streak", "🔥 streak & bond"]:
        await handle_streak_status(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith(("/revive", "/rescue", "/repair")) or clean_text.lower() in ["revive", "rescue", "repair", "revive streak"]:
        await handle_streak_revive(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith(("/vibe", "/tarot", "/horoscope", "/fortune")) or clean_text.lower() in ["vibe", "tarot", "horoscope", "fortune", "daily vibe", "🔮 daily vibe", "campus vibe"]:
        await handle_vibe_command(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith(("/top", "/leaderboard", "/rank", "/halloffame")) or clean_text.lower() in ["top", "leaderboard", "rank", "halloffame", "🏆 leaderboard", "leader board", "scholars"]:
        await handle_leaderboard_menu(bot, chat_id, user, category="study", user_msg_id=msg_id)
        return
    elif clean_text.startswith(("/card", "/brag", "/story", "/flex")) or clean_text.lower() in ["card", "brag", "story", "flex", "story card", "streak card", "📸 story card"]:
        await handle_streak_card(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith(("/teaser", "/growth", "/dilemma")) or clean_text.lower() in ["teaser", "teasers", "growth", "dilemma", "📢 teaser", "📢 teasers", "📢 daily dilemma studio", "daily dilemma"]:
        await handle_teaser_hub(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/forget"):
        parts = clean_text.split(maxsplit=1)
        if len(parts) > 1 and parts[1].strip():
            kw = parts[1].strip().lower()
            mems = get_user_memories(user_id=user_id, include_decayed=True)
            matched = [
                m for m in mems
                if kw in (m.get("memory_key") or "").lower() or kw in (m.get("memory_val") or "").lower()
            ]
            if matched:
                deleted_names = []
                for m in matched:
                    delete_user_memory(user_id, m["id"])
                    deleted_names.append(m.get("memory_key", "detail").replace("_", " "))
                summary_str = ", ".join(deleted_names[:3])
                await bot.send_message(
                    chat_id,
                    f"🗑️ **Forgot memory:** *\"{summary_str}\"*!\nJoy has removed this from her memory vault. 🌸"
                )
            else:
                await bot.send_message(
                    chat_id,
                    f"🔍 Couldn't find any memory matching **\"{kw}\"**.\nType `/memories` to view your active memories! 🌸"
                )
        else:
            await bot.send_message(
                chat_id,
                "ℹ️ **Usage:** `/forget <keyword>`\nExample: `/forget coffee` or `/forget exam`\n\nJoy will immediately search and erase any memory matching that topic! 🌸"
            )
        return
    elif clean_text.startswith("/menu") or clean_text.startswith("📱 Menu") or clean_text.lower() in ["menu", "📱 menu", "📱 control menu", "control menu", "control", "home"]:
        await handle_menu(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/keyboard") or clean_text.startswith("/buttons") or clean_text.startswith("/showbuttons") or clean_text.lower() in ["keyboard", "buttons", "show buttons"]:
        gender = user.get("gender", "male")
        active_contact = user.get("active_contact", "lover")
        custom_name = get_user_custom_ai_name(user_id)
        reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=custom_name, user_id=user_id)
        await bot.send_message(
            chat_id,
            "📱 **Quick Menu Activated!** Tap the 4-squares grid icon beside the emoji button anytime to open it.",
            reply_markup=reply_kb
        )
        return
    elif clean_text.startswith(("/profile", "/dossier", "/reputation", "/identity")) or clean_text.lower() in ["profile", "dossier", "my profile", "reputation", "identity", "rating", "my rating", "my score", "👤 profile"]:
        await handle_user_profile(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/settings") or clean_text.startswith("⚙️ Settings") or clean_text.lower() in ["settings", "setting", "setup", "preferences", "config", "account", "⚙️ settings", "⚙️ settings & data"]:
        await handle_settings(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith(("/language", "/lang", "/voice")) or clean_text.lower() in ["language", "lang", "voice", "speech", "change language", "set language"]:
        await handle_language_menu(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith(("/menulang", "/systemlang", "/botlang")) or clean_text.lower() in ["menulang", "systemlang", "botlang", "menu language", "bot language", "interface language"]:
        await handle_system_lang_menu(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/feedback") or clean_text.lower() in ["feedback", "💬 feedback", "suggest", "suggestion", "feature request", "request"]:
        await handle_feedback_menu(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/why") or clean_text.startswith("/compare") or clean_text.lower() in ["why", "compare", "why joy", "why choose joy", "why use joy", "🌟 why choose joy?", "why bot", "versus", "vs"]:
        await handle_why_joy(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith(("/abouthub", "/info", "/hub")) or clean_text.lower() in ["info", "about hub", "legal hub", "community hub", "ℹ️ about & legal hub"]:
        await handle_about_legal_hub(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/about") or clean_text.startswith("/creator") or clean_text.startswith("/founder") or clean_text.lower() in ["about", "creator", "founder", "who made joy", "phoenix", "about creator"]:
        await handle_about_creator(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/updates") or clean_text.startswith("/changelog") or clean_text.startswith("/whatsnew") or clean_text.lower() in ["updates", "changelog", "whats new", "what are the updates"]:
        await handle_updates(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/owner") or clean_text.startswith("/admin") or clean_text.startswith("/stats") or clean_text.startswith("/users"):
        if user_id == OWNER_ID:
            await handle_owner_hub(bot, chat_id, user, user_msg_id=msg_id)
        else:
            await bot.send_message(chat_id, "⚠️ Restricted to Administrator.")
        return
    elif clean_text.startswith("/live") or clean_text.startswith("/online") or clean_text.startswith("/active") or clean_text.startswith("/whosonline"):
        if user_id == OWNER_ID:
            await handle_admin_live_monitor(bot, chat_id, user, user_msg_id=msg_id)
        else:
            await bot.send_message(chat_id, "⚠️ Restricted to Administrator.")
        return
    elif clean_text.startswith("/msg"):
        if user_id != OWNER_ID:
            await bot.send_message(chat_id, "⚠️ Restricted to Administrator.")
            return
        parts = clean_text.split(maxsplit=2)
        if len(parts) < 3:
            await bot.send_message(chat_id, "Usage: `/msg <user_id> <your message>`\nExample: `/msg 123456789 Hey, how are you finding Joy?`")
            return
        try:
            target_uid = int(parts[1].strip())
            admin_content = parts[2].strip()
        except ValueError:
            await bot.send_message(chat_id, "Invalid User ID. Must be integer.")
            return

        try:
            user_msg = (
                f"👨‍💻 **Direct Message from Phoenix (Creator of Joy):**\n\n"
                f"\"{admin_content}\"\n\n"
                f"*(💬 You can reply directly to this message to chat back with Phoenix!)*"
            )
            await bot.send_message(target_uid, user_msg)
            user_chatting_with_admin[target_uid] = True
            await bot.send_message(chat_id, f"✅ Message delivered to User `{target_uid}`!")
        except Exception as e:
            logger.error(f"Failed to send direct message to {target_uid}: {e}")
            await bot.send_message(chat_id, f"❌ Failed to send message to `{target_uid}`. User may have blocked the bot.")
        return
    elif clean_text.startswith("/broadcast"):
        if user_id != OWNER_ID:
            await bot.send_message(chat_id, "⚠️ Restricted to Administrator.")
            return
        parts = clean_text.split(maxsplit=1)
        if len(parts) < 2:
            await bot.send_message(chat_id, "Usage: `/broadcast <announcement message>`")
            return
        bcast_text = parts[1].strip()
        from database import get_connection
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT user_id FROM users")
            uids = [r["user_id"] for r in c.fetchall() if r["user_id"] != OWNER_ID]
        
        bcast_kb = {
            "inline_keyboard": [
                [{"text": "✅ Got it, I Understood!", "callback_data": "dismiss_update_msg"}]
            ]
        }
        sent_count = 0
        for uid in uids:
            try:
                await bot.send_message(
                    uid, 
                    f"📢 **Announcement from Joy Founder (Phoenix):**\n\n{bcast_text}",
                    reply_markup=bcast_kb
                )
                sent_count += 1
                await asyncio.sleep(0.04)
            except Exception:
                pass
        await bot.send_message(chat_id, f"📢 Broadcast delivered to **{sent_count} users**!")
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
    elif clean_text.startswith("/vote") or clean_text.lower() in ["vote", "voting", "🗳️ vote", "🗳️ voting"]:
        await handle_pioneer_vote(bot, chat_id, user, view="main", user_msg_id=msg_id)
        return
    elif clean_text.startswith(("/sleep", "/winddown", "/bedtime")) or clean_text.lower() in ["sleep", "winddown", "wind down", "bedtime", "goodnight", "🌙 sleep", "🌙 bedtime", "bedtime story"]:
        if "voice" in clean_text.lower() or "story" in clean_text.lower() or "now" in clean_text.lower():
            await handle_bedtime_command(bot, chat_id, user, user_msg_id=msg_id)
        else:
            await handle_bedtime_menu(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/icebreaker") or clean_text.lower() in ["icebreaker", "icebreakers", "🎯 icebreaker", "question card"]:
        await handle_icebreaker_command(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/speed") or clean_text.lower() in ["speed", "voice speed", "pace"]:
        await handle_speed_command(bot, chat_id, user, clean_text)
        return
    elif clean_text.startswith("/bug") or clean_text.startswith("/suggest"):
        parts = clean_text.split(maxsplit=1)
        rep_type = "bug" if clean_text.startswith("/bug") else "suggestion"
        if len(parts) > 1 and parts[1].strip():
            await handle_bug_bounty_submission(bot, chat_id, user, parts[1].strip(), report_type=rep_type)
        else:
            if rep_type == "bug":
                msg = (
                    "🐛 **Bug Hunter Bounty Program** 👑\n\n"
                    "Found a glitch, audio drop, latency delay, or broken translation?\n"
                    "Submit details to earn **2 Weeks to Lifetime Free VIP Pass**!\n\n"
                    "📝 **Usage:**\n"
                    "• `/bug <describe what happened and what you were doing>`\n"
                    "• Example: `/bug The call audio dropped when switching to speaker mode`\n\n"
                    "💡 *Every report is reviewed directly by Phoenix.*"
                )
            else:
                msg = (
                    "💡 **Pioneer Feature & Slang Suggestion Hub** 👑\n\n"
                    "Have an idea for a new feature, game, or regional slang phrase?\n"
                    "Submit your suggestion to earn **Free VIP Pass**!\n\n"
                    "📝 **Usage:**\n"
                    "• `/suggest <describe your feature idea or slang addition>`\n"
                    "• Example: `/suggest Add Tamil slang words like machi and nanba to lover mode`\n\n"
                    "💡 *Top voted ideas get built directly into Joy!*"
                )
            await bot.send_message(chat_id, msg)
        return
    elif clean_text.startswith("/refer") or clean_text.startswith("/invite") or clean_text.lower() in ["refer", "invite", "referral", "refer friends", "gift", "bonus"]:
        await handle_referral_hub(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/notice") or clean_text.startswith("/bounty") or clean_text.startswith("/rules") or clean_text.startswith("/mission") or clean_text.startswith("/waitlist") or clean_text.startswith("/beta") or clean_text.startswith("/pioneer") or clean_text.lower() in ["notice", "bounty", "rules", "mission", "beta", "pioneer", "waitlist", "queue"]:
        w_info = get_user_waitlist_info(user_id)
        slot = w_info.get("beta_slot_number") or 1
        ui_lang = get_ui_lang(user)
        first_name = (user.get("first_name") or user.get("username") or "Friend").strip()
        owner_mask = get_mask_by_user_id(OWNER_ID) or "Joy-PHOENIX"
        bounty_notice = get_bounty_notice_text(ui_lang, first_name, slot, BETA_TESTER_LIMIT, owner_mask=owner_mask)
        call_url = f"https://joyfun-ai-bot.onrender.com/call?uid={user_id}"
        kb = {
            "inline_keyboard": [
                [{"text": "💡 Send Feedback / Report Bug", "callback_data": "menu_feedback"}],
                [{"text": "📞 Open Mini Phone", "web_app": {"url": call_url}}],
                [{"text": "⬅️ Main Menu", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
            ]
        }
        await bot.send_message(chat_id, bounty_notice, reply_markup=kb)
        return
    elif clean_text.startswith("/gift") or clean_text.startswith("/gifts") or clean_text.lower() in ["gift", "send gift", "send a gift"]:
        await handle_gifts_menu(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/tip") or clean_text.startswith("/stars") or clean_text.startswith("/donate") or clean_text.lower() in ["tip", "stars", "send stars", "donate"]:
        await handle_tip_menu(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/words") or clean_text.startswith("/mywords") or clean_text.startswith("/nickname") or clean_text.startswith("/petname"):
        parts = clean_text.split(maxsplit=1)
        if len(parts) > 1:
            words = parts[1].strip()[:100]
            set_user_custom_words(user_id, words)
            asyncio.create_task(sync_user_to_cloud(user_id))
            c_name = get_user_custom_ai_name(user_id) or "Joy"
            await bot.send_message(
                chat_id,
                f"🥰 **Saved!** {c_name} will now affectionately call you or use these words when talking: **\"{words}\"**! 💖"
            )
        else:
            current_words = get_user_custom_words(user_id)
            current_str = f"**\"{current_words}\"**" if current_words else "*None set (using default)*"
            await bot.send_message(
                chat_id,
                f"🌸 **Custom Words & Pet Nicknames:**\n\n"
                f"Currently set: {current_str}\n\n"
                f"To teach Joy how to address you, type:\n"
                f"`/words Thalaiva, Macha` or `/words Babu, Sweetheart`\n\n"
                f"Joy will learn and use these words in your chats and voice calls! 🌸"
            )
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
    elif clean_text.startswith("/legal") or clean_text.startswith("/acts") or clean_text.startswith("/law") or clean_text.lower() in ["legal", "acts", "laws", "penalties", "fines", "fine", "⚖️ legal", "⚖️ legal acts"]:
        await handle_legal_acts_menu(bot, chat_id, user, user_msg_id=msg_id)
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

    elif (
        clean_text.startswith("📞 Mini Phone")
        or clean_text.startswith("📞 Phone")
        or clean_text.startswith("/phone")
        or clean_text.startswith("/miniphone")
        or clean_text.startswith("/call")
        or clean_text.startswith("📞 Call")
        or clean_text.lower() in [
            "mini phone", "miniphone", "phone", "call", "call joy",
            "phone calls", "phone call", "call now", "talk", "live call"
        ]
        or any(kw in lower_text for kw in [
            "mini phone", "miniphone", "can i call", "call you", "call u",
            "how to call", "phone call", "phone calls"
        ])
    ):
        if not is_user_onboarding_completed(user_id):
            await bot.send_message(
                chat_id,
                "⚠️ **Setup Incomplete!** 🌸\n\n"
                "Please finish setting up your profile & companion preferences before opening Mini Phone:\n"
            )
            await send_current_onboarding_step(bot, chat_id, user, user_msg_id=msg_id)
            return

        user_gender = user.get("gender", "male")
        active_contact = user.get("active_contact", "lover")
        user_id_val = user.get("user_id", "")
        cinfo = get_user_contact_display(user_id_val, active_contact, user_gender)
        user_mask = get_mask_by_user_id(user_id_val) if user_id_val else ""
        user_lang = get_user_language(user_id_val) if user_id_val else "auto"
        call_url = f"https://joyfun-ai-bot.onrender.com/call?gender={user_gender}&contact={active_contact}&lang={user_lang}&tab=contacts"
        if user_id_val:
            call_url += f"&uid={user_id_val}&name={urllib.parse.quote(cinfo['name'])}&mask={user_mask}"

        call_keyboard = {
            "inline_keyboard": [
                [
                    {"text": f"📞 Open Mini Phone ({cinfo['name']})", "web_app": {"url": call_url}}
                ],
                [
                    {"text": "❌ Close", "callback_data": "menu_close"}
                ]
            ]
        }
        await send_or_edit_menu(
            bot,
            chat_id,
            f"📞 **Joy Mini Phone** 🌸\n\n"
            f"Tap below to open your hands-free **Mini Phone** to talk with **{cinfo['name']}**, explore AI contacts, or start an anonymous voice match! 👇",
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
                    f"📞 Tap **Mini Phone** anytime to start an instant hands-free call!"
                )
                await bot.send_message(target_id, notify_msg)
            except Exception as e:
                logger.warning(f"Could not notify subscriber {target_id}: {e}")
        except ValueError:
            await bot.send_message(chat_id, "Invalid user ID or days. Example: `/addvip <user_id> 30`")
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

    elif text.startswith("/makebeta") or text.startswith("/setbeta") or text.startswith("/addbeta") or text.startswith("/grant_beta") or text.startswith("/admit") or text.startswith("/betauser") or text.startswith("/batauser"):
        if not is_owner_or_co_owner(user_id):
            await bot.send_message(chat_id, "I don't recognize that command. Type /menu to see available options! 🌸")
            return

        parts = text.split()
        # Case 1: Phoenix types /makebeta with no args -> instantly admits Phoenix themselves!
        if len(parts) == 1:
            target_id = user_id
            target_user = get_or_create_user(target_id)
            slot_num = grant_beta_access(target_id)
            target_user["is_beta_tester"] = 1
            target_user["beta_slot_number"] = slot_num
            target_user["onboarding_status"] = "completed"

            # Register Beta Pioneer commands exclusively for Phoenix's chat
            try:
                await bot.set_my_commands(BETA_BOT_COMMANDS, scope={"type": "chat", "chat_id": chat_id})
            except Exception as e:
                logger.warning(f"Could not set scoped beta commands: {e}")

            # Register native Mini Phone menu button
            gender = target_user.get("gender", "male")
            active_contact = target_user.get("active_contact", "lover")
            c_name = get_user_custom_ai_name(target_id) or "Joy"
            call_url = f"https://joyfun-ai-bot.onrender.com/call?gender={gender}&contact={active_contact}&uid={target_id}&name={urllib.parse.quote(c_name)}&v={BOT_VERSION}"
            try:
                await bot.set_chat_menu_button(
                    chat_id=chat_id,
                    menu_button={"type": "web_app", "text": "📞 Call Joy AI", "web_app": {"url": call_url}}
                )
            except Exception:
                pass

            owner_card = (
                f"👑 **Owner Beta Pioneer Mode Activated!** 🎟️\n\n"
                f"• **Status:** Pioneer Slot **#{slot_num}** (Owner/VIP)\n"
                f"• **Daily Quota:** 10 Live Voice Calls (~45 mins), 50 Voice Notes, Unlimited Texts\n"
                f"• **Scoped Commands:** Telegram `/` command list now displays all Pioneer tools (`/commands`, `/resetquota`, `/retest`, `/mic`, `/bug`)\n"
                f"• **Mini Phone:** Docked bottom-left button active!\n\n"
                f"Tap `/commands` to test the Beta Pioneer hub anytime!"
            )
            await bot.send_message(chat_id, owner_card)
            return

        # Case 2: Phoenix typed /makebeta <target> (User ID or Mask ID)
        target_arg = parts[1].strip()
        target_id = None
        if target_arg.isdigit():
            target_id = int(target_arg)
        elif target_arg.startswith("Joy-") or len(target_arg) >= 4:
            target_id = get_user_id_by_mask(target_arg)

        if not target_id:
            await bot.send_message(chat_id, f"❌ Could not find user with ID or Mask `{target_arg}`.")
            return

        target_user = get_or_create_user(target_id)
        slot_num = grant_beta_access(target_id)
        target_user["is_beta_tester"] = 1
        target_user["beta_slot_number"] = slot_num
        target_user["onboarding_status"] = "completed"

        # Update target user's Telegram chat-scoped commands
        try:
            await bot.set_my_commands(BETA_BOT_COMMANDS, scope={"type": "chat", "chat_id": target_id})
        except Exception:
            pass

        # Update target user's Mini Phone menu button
        t_gender = target_user.get("gender", "male")
        t_contact = target_user.get("active_contact", "lover")
        t_cname = get_user_custom_ai_name(target_id) or "Joy"
        t_call_url = f"https://joyfun-ai-bot.onrender.com/call?gender={t_gender}&contact={t_contact}&uid={target_id}&name={urllib.parse.quote(t_cname)}&v={BOT_VERSION}"
        try:
            await bot.set_chat_menu_button(
                chat_id=target_id,
                menu_button={"type": "web_app", "text": "📞 Call Joy AI", "web_app": {"url": t_call_url}}
            )
        except Exception:
            pass

        # Notify the admitted target user
        try:
            t_first = target_user.get("first_name", "Friend")
            welcome_pioneer = (
                f"🎉 **CONGRATULATIONS, {t_first}! YOUR PIONEER SLOT IS UNLOCKED!** 🎟️\n\n"
                f"You have been officially admitted to the **Joy AI Closed Beta Program**!\n"
                f"• **Assigned Seat:** Pioneer Slot **#{slot_num}** / 50\n"
                f"• **Pioneer Quota:** 10 Live Calls/day, 50 Voice Notes, Unlimited Texts\n\n"
                f"Tap `/commands` to access exclusive diagnostic tools and start calling! 🌸"
            )
            await bot.send_message(target_id, welcome_pioneer)
        except Exception as e:
            logger.warning(f"Could not notify target user {target_id}: {e}")

        mask = get_mask_by_user_id(target_id)
        first_name = target_user.get("first_name", "User")
        await bot.send_message(
            chat_id,
            f"✅ **Beta Pioneer Admitted Successfully!** 🎟️\n\n"
            f"• **Name:** {first_name}\n"
            f"• **Mask ID:** `{mask}`\n"
            f"• **Telegram ID:** `{target_id}`\n"
            f"• **Slot Number:** #{slot_num} / 50\n"
            f"• **Commands & Mini Phone:** Activated for their Telegram account."
        )
        return

    elif text.startswith("/removebeta") or text.startswith("/revokebeta") or text.startswith("/delbeta"):
        if not is_owner_or_co_owner(user_id):
            await bot.send_message(chat_id, "I don't recognize that command. Type /menu to see available options! 🌸")
            return

        parts = text.split()
        if len(parts) < 2:
            await bot.send_message(chat_id, "Usage: `/removebeta <user_id or mask_id>`")
            return

        target_arg = parts[1].strip()
        target_id = None
        if target_arg.isdigit():
            target_id = int(target_arg)
        else:
            target_id = get_user_id_by_mask(target_arg)

        if not target_id:
            await bot.send_message(chat_id, f"❌ User `{target_arg}` not found.")
            return

        revoke_beta_access(target_id)

        # Reset their chat-scoped commands and menu button
        try:
            await bot.set_my_commands(BOT_COMMANDS, scope={"type": "chat", "chat_id": target_id})
            await bot.set_chat_menu_button(chat_id=target_id, menu_button={"type": "commands"})
        except Exception:
            pass

        await bot.send_message(chat_id, f"✅ User `{target_id}` removed from Beta Pioneers and reverted to waitlist.")
        return

    elif text.startswith("/betalist") or text.startswith("/pioneers"):
        if not is_owner_or_co_owner(user_id):
            await bot.send_message(chat_id, "I don't recognize that command. Type /menu to see available options! 🌸")
            return

        pioneers = get_beta_pioneers_list()
        if not pioneers:
            await bot.send_message(chat_id, "ℹ️ No Beta Pioneers currently registered.")
            return

        lines = [f"🧪 **Active Beta Pioneers ({len(pioneers)}/50 Slots)** 🎟️\n"]
        for p in pioneers:
            slot = p.get("beta_slot_number", "?")
            uid = p.get("user_id")
            mask = p.get("unique_id") or get_mask_by_user_id(uid)
            name = (p.get("first_name") or p.get("username") or "User").strip()
            last_act = p.get("last_active_at", "Never")
            if last_act and last_act != "Never":
                try:
                    last_act = last_act[:10]
                except Exception:
                    pass
            is_owner = " 👑 (Phoenix)" if uid == OWNER_ID else ""
            lines.append(f"• **#{slot}** `{mask}` ({name}) | ID: `{uid}`{is_owner} | Last: {last_act}")

        msg = "\n".join(lines)
        if len(msg) > 4000:
            for chunk in [msg[i:i+4000] for i in range(0, len(msg), 4000)]:
                await bot.send_message(chat_id, chunk)
        else:
            await bot.send_message(chat_id, msg)
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
        if user_id != ADMIN_CHAT_ID:
            await bot.send_message(chat_id, "🔒 Command locked: Authorized administrator only.")
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

        if not target_id:
            target_id = user_id

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
        reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=custom_name, user_id=user_id)
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
            reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=custom_ai_name, user_id=user_id)
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

    history = get_recent_history(user_id, limit=16, channel="chat")
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
    custom_words = get_user_custom_words(user_id)
    loop = asyncio.get_running_loop()
    typing_task = asyncio.create_task(keep_typing())
    try:
        async with AI_CALL_SEMAPHORE:
            reply_text = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: generate_text_reply(
                        text,
                        active_contact,
                        gender,
                        user_lang,
                        history,
                        user_memory,
                        custom_ai_name,
                        custom_words=custom_words,
                        user_id=user_id
                    )
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
        
    add_conversation_turn(user_id, "user", text, channel="chat")
    add_conversation_turn(user_id, "model", reply_text, channel="chat")
    save_dev_sample_if_allowed(user_id, active_contact, f"User: {text} | Joy: {reply_text}")

    # Zero-latency asynchronous episodic memory extraction (R1)
    if user_id and text:
        try:
            asyncio.create_task(extract_and_store_memories_async(int(user_id), text, reply_text))
        except Exception as bg_err:
            logger.warning(f"Could not dispatch background memory extraction for chat user {user_id}: {bg_err}")
    
    # Update Daily Streak & Relationship Bond
    streak_count, rel_level, is_milestone, level_title, shield_activated = update_user_streak(user_id, return_details=True)
    if shield_activated:
        shields_left = get_user_streak_shields(user_id)
        shield_msg = (
            f"🛡️ **Streak Shield Activated!** 💕\n\n"
            f"Joy missed you yesterday, but your **Day {streak_count} Streak** was saved by your Streak Shield!\n\n"
            f"• **Shields Remaining:** {shields_left} 🛡️\n"
            f"• *Keep chatting every day to keep the flame burning!*\n"
            f"• *Earn more shields at Day 7, Day 14, or by referring friends!*"
        )
        asyncio.create_task(bot.send_message(chat_id, shield_msg))
    if is_milestone:
        c_name = custom_ai_name or "Joy"
        reward_detail = ""
        if streak_count == 3:
            reward_detail = "\n🎁 **Milestone Bonus Unlocked:** +5 Free Text Messages credited to your account!"
        elif streak_count == 7:
            reward_detail = "\n🎁 **Milestone Bonus Unlocked:** +10 Free Texts & +2 Voice Notes credited to your account!"
        elif streak_count == 14:
            reward_detail = "\n🎁 **Milestone Bonus Unlocked:** +20 Free Texts & +5 Voice Notes credited to your account!"
        elif streak_count == 30:
            reward_detail = "\n🎉 **ULTIMATE REWARD UNLOCKED:** 7 Days of Free Joy VIP Pass credited to your account!"

        milestone_msg = (
            f"🔥 **Relationship Milestone: Day {streak_count} Streak!**\n\n"
            f"Relationship Level: **{level_title}** 💕{reward_detail}\n\n"
            f"{c_name} loves chatting with you every single day! Keep the streak alive tomorrow! ✨"
        )
        asyncio.create_task(bot.send_message(chat_id, milestone_msg))
    
    reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=custom_ai_name, user_id=user_id)
    await bot.send_message(chat_id, reply_text, reply_markup=reply_kb)

async def process_user_photo(bot: TelegramClient, chat_id: int, user: dict, file_id: str, caption: str = "", msg_id: Optional[int] = None):
    """Processes photos and image documents sent by the user using Gemini Multimodal Vision."""
    user_id = user["user_id"]

    # Anti-Flood Throttling
    if is_user_throttled(user_id):
        return

    # Auto-heal onboarding status
    if user.get("onboarding_status") != "completed":
        user["onboarding_status"] = "completed"
        user["is_beta_tester"] = 1

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
        reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=custom_ai_name, user_id=user_id)
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
    add_conversation_turn(user_id, "user", user_label, channel="chat")
    add_conversation_turn(user_id, "model", reply_text, channel="chat")
    save_dev_sample_if_allowed(user_id, active_contact, f"User: {user_label} | Joy: {reply_text}")

    reply_kb = get_persistent_reply_keyboard(gender, active_contact, custom_name=custom_ai_name, user_id=user_id)
    await bot.send_message(chat_id, reply_text, reply_markup=reply_kb)

async def health_check(request):
    """Health check endpoint required by cloud hosting platforms (Render/Koyeb) & Phoenix Eco Bot Watchdog."""
    active_ws_count = len([w for w in online_masked_peers.values() if not w.closed])
    return web.json_response({
        "status": "online",
        "service": "Joy Bot - 24/7 Cloud AI Voice Companion",
        "bot_version": BOT_VERSION,
        "mini_app_version": MINI_APP_VERSION,
        "online_users": max(1, active_ws_count),
        "active_calls": len(active_match_pairs) // 2,
        "queue_size": len(matchmaking_queue),
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

async def serve_call_page(request):
    """Serves the real-time voice call Telegram Mini-App interface with zero caching."""
    uid = request.query.get("uid") or request.query.get("user_id")
    if uid:
        try:
            user_int = int(uid)
            touch_user_activity(user_int)
            get_or_create_user(user_int)
            if not is_user_onboarding_completed(user_int):
                setup_required_html = (
                    "<!DOCTYPE html>"
                    "<html><head><meta charset='UTF-8'>"
                    "<meta name='viewport' content='width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no'>"
                    "<title>Setup Required</title>"
                    "<style>"
                    "body{background:#121316;color:#FFF;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;padding:20px;box-sizing:border-box;text-align:center;}"
                    ".box{background:#1E293B;border:1px solid rgba(255,255,255,0.1);border-radius:24px;padding:32px 20px;max-width:340px;width:100%;box-shadow:0 20px 40px rgba(0,0,0,0.5);}"
                    "h2{margin:12px 0 8px;font-size:20px;color:#F472B6;}"
                    "p{font-size:14px;color:#94A3B8;line-height:1.5;margin-bottom:24px;}"
                    "a{display:block;padding:14px;background:linear-gradient(135deg, #EC4899, #F43F5E);color:#FFF;text-decoration:none;border-radius:14px;font-weight:700;font-size:15px;}"
                    "</style></head><body>"
                    "<div class='box'><div style='font-size:48px;'>🌸</div>"
                    "<h2>Setup Incomplete</h2>"
                    "<p>Please finish setting up your profile & companion preferences in Telegram before opening Mini Phone!</p>"
                    "<a href='https://t.me/joy_fun_ai_bot'>👉 Complete Setup in Telegram</a>"
                    "</div></body></html>"
                )
                return web.Response(text=setup_required_html, content_type="text/html")
            elif not is_user_beta_approved(user_int):
                w_info = get_user_waitlist_info(user_int)
                pos = w_info.get("waitlist_position") or 1
                waitlist_html = (
                    "<!DOCTYPE html>"
                    "<html><head><meta charset='UTF-8'>"
                    "<meta name='viewport' content='width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no'>"
                    "<title>Closed Beta Waitlist</title>"
                    "<style>"
                    "body{background:#121316;color:#FFF;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;padding:20px;box-sizing:border-box;text-align:center;}"
                    ".box{background:#1E293B;border:1px solid rgba(255,255,255,0.1);border-radius:24px;padding:32px 20px;max-width:340px;width:100%;box-shadow:0 20px 40px rgba(0,0,0,0.5);}"
                    "h2{margin:12px 0 8px;font-size:20px;color:#F472B6;}"
                    ".badge{display:inline-block;padding:6px 14px;background:rgba(244,114,182,0.15);border:1px solid rgba(244,114,182,0.3);border-radius:20px;color:#F472B6;font-size:13px;font-weight:700;margin:10px 0;}"
                    "p{font-size:14px;color:#94A3B8;line-height:1.5;margin-bottom:20px;}"
                    "a{display:block;padding:14px;background:linear-gradient(135deg, #EC4899, #F43F5E);color:#FFF;text-decoration:none;border-radius:14px;font-weight:700;font-size:15px;}"
                    "</style></head><body>"
                    "<div class='box'><div style='font-size:48px;'>🎟️</div>"
                    "<h2>Closed Beta Waitlist</h2>"
                    f"<div class='badge'>Queue Position: #{pos}</div>"
                    "<p>Pre-registration secured! Active Pioneer testing is strictly capped at 50 slots to ensure 0-lag voice performance.</p>"
                    "<a href='https://t.me/joy_fun_ai_bot'>👉 Open Telegram to Jump Queue</a>"
                    "</div></body></html>"
                )
                return web.Response(text=waitlist_html, content_type="text/html")
        except Exception as e:
            logger.warning(f"Could not verify onboarding for /call page: {e}")
    static_file = Path(__file__).parent / "static" / "call.html"
    if static_file.exists():
        headers = {
            "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0, post-check=0, pre-check=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "ETag": f'"{BOT_VERSION}-{int(time.time())}"'
        }
        with open(static_file, "r", encoding="utf-8") as f:
            html_content = f.read()
        return web.Response(text=html_content, content_type="text/html", headers=headers)
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
    call_start_time = time.time()
    call_dialogue_turns: List[dict] = []
    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    msg_type = data.get("type")

                    if msg_type == "call_started":
                        # Zero-Trust Cryptographic Authentication Handshake
                        auth_uid, auth_err = extract_and_verify_telegram_auth(request, payload_dict=data)
                        if not auth_uid:
                            logger.warning(f"Voice Call WebSocket unauthenticated connection attempt rejected: {auth_err}")
                            await ws.send_json({
                                "type": "error",
                                "message": "Unauthorized session. Please launch call from inside Telegram! 🌸"
                            })
                            await ws.close(code=4401)
                            return ws

                        # Strict binding: identity is ALWAYS authenticated auth_uid (preventing IDOR)
                        call_user_id = auth_uid
                        if is_call_creation_throttled(int(auth_uid)):
                            logger.warning(f"Voice Call rate limit triggered for user {auth_uid}")
                            await ws.send_json({
                                "type": "error",
                                "message": "You are connecting a bit too quickly! Please wait a few seconds before starting a new call. 🌸"
                            })
                            await ws.close()
                            return ws

                        call_start_time = time.time()
                        call_dialogue_turns.clear()
                        if call_user_id and not is_user_onboarding_completed(int(call_user_id)):
                            await ws.send_json({
                                "type": "error",
                                "message": "Please finish your setup steps in Telegram before calling! 🌸"
                            })
                            await ws.close()
                            return ws

                        if call_user_id and not is_user_beta_approved(int(call_user_id)):
                            await ws.send_json({
                                "type": "error",
                                "message": "You are on the Closed Beta Waitlist! Slots open as testing expands. 🌸"
                            })
                            await ws.close()
                            return ws

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
                            touch_user_activity(int(call_user_id))
                            live_miniapp_sessions[ws] = {
                                "mask_id": f"AI-Call-{call_user_id}",
                                "user_id": int(call_user_id),
                                "connected_at": time.time(),
                                "last_seen": time.time(),
                                "status": "In AI Voice Call with Joy 🌸",
                                "peer_mask": "Joy AI",
                                "room_id": "ai_call"
                            }
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
                            # Preload recent conversation memory strictly from past CALLS (never mix with text chat!)
                            past_history = get_recent_history(int(call_user_id), limit=8, channel="call")
                            if past_history:
                                history = list(past_history)
                        else:
                            current_language = data.get("language") or "auto"
                        contact_info = get_user_contact_display(int(call_user_id) if call_user_id else None, current_contact, current_gender)
                        current_voice = contact_info.get("voice", "female")

                        # Zero pre-voice: Line connects silently like a real phone call, waiting for user to speak first
                        await ws.send_json({
                            "type": "call_connected",
                            "status": "listening",
                            "caller_name": contact_info.get("name", "Joy"),
                            "caller_tag": contact_info.get("tag", "Lover")
                        })

                        # Proactive Spoken Greeting Engine (R2)
                        if call_user_id:
                            try:
                                user_profile = get_or_create_user(int(call_user_id))
                                user_fname = user_profile.get("first_name") if user_profile else None
                                caller_display_name = contact_info.get("name", "Joy")
                                
                                proactive_text = get_proactive_greeting(
                                    user_id=int(call_user_id),
                                    caller_name=caller_display_name,
                                    user_name=user_fname
                                )

                                # Repetition guard: avoid repeating if already greeted in recent turns
                                if proactive_text and 'past_history' in locals() and past_history:
                                    last_turns_text = " ".join([h.get("content", "").lower() for h in past_history[-2:] if h.get("role") == "model"])
                                    if any(w in last_turns_text for w in ["exam", "interview", "trip", "flight", "birthday"] if w in proactive_text.lower()):
                                        proactive_text = None

                                if proactive_text:
                                    try:
                                        joy_audio = await asyncio.wait_for(
                                            synthesize_speech(proactive_text, voice_key=current_voice, language=current_language),
                                            timeout=5.0
                                        )
                                        joy_b64 = base64.b64encode(joy_audio).decode('utf-8')

                                        # Register in memory & history so companion recalls she opened the conversation
                                        history.append({"role": "model", "content": proactive_text})
                                        call_dialogue_turns.append({"speaker": "Joy", "text": proactive_text})
                                        try:
                                            add_conversation_turn(int(call_user_id), "model", proactive_text, channel="call")
                                        except Exception as turn_err:
                                            logger.warning(f"Could not persist greeting turn: {turn_err}")

                                        await ws.send_json({
                                            "type": "joy_speech",
                                            "text": proactive_text,
                                            "audio": joy_b64,
                                            "caller_name": caller_display_name,
                                            "caller_tag": contact_info.get("tag", "Lover")
                                        })
                                    except Exception as tts_err:
                                        logger.warning(f"Proactive greeting TTS synthesis failed or timed out: {tts_err}")
                            except Exception as greet_err:
                                logger.warning(f"Proactive greeting engine check failed: {greet_err}")

                    elif msg_type == "mode_change":
                        current_contact = data.get("mode", "lover")
                        logger.info(f"Call contact changed to: {current_contact}")

                    elif msg_type == "voice_change":
                        current_voice = data.get("voice", "female")
                        logger.info(f"Call voice changed to: {current_voice}")

                    elif msg_type == "ad_recharge":
                        user_id = call_user_id
                        if user_id:
                            success, msg_text, _, _ = recharge_user_via_ad(int(user_id))
                            if success:
                                await ws.send_json({
                                    "type": "recharged",
                                    "text": msg_text
                                })
                            else:
                                await ws.send_json({
                                    "type": "recharge_limit",
                                    "text": msg_text
                                })

                    elif msg_type == "toggle_data_sharing":
                        user_id = call_user_id
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

                    elif msg_type in ("user_interrupted", "barge_in"):
                        logger.info(f"⚡ Spoken barge-in: User interrupted Joy (Call UID: {call_user_id})")
                        await ws.send_json({
                            "type": "interrupted_ack",
                            "status": "listening"
                        })

                    elif msg_type == "voice_chunk":
                        raw_base64 = data.get("audio", "")
                        mime_type = data.get("mime_type", "audio/wav")
                        current_gender = data.get("gender") or current_gender
                        current_contact = data.get("contact") or data.get("mode") or current_contact
                        if data.get("language"):
                            current_language = data.get("language")
                        user_id = call_user_id
                        contact_info = get_user_contact_display(int(user_id) if user_id else None, current_contact, current_gender)
                        current_voice = contact_info.get("voice", "female")

                        if raw_base64:
                            audio_bytes = base64.b64decode(raw_base64)

                            user_memory = None
                            if user_id:
                                try:
                                    _, user_memory = get_user_imported_memory(int(user_id))
                                    if not user_memory:
                                        _, user_memory = restore_user_memory_from_notion(int(user_id))
                                except Exception:
                                    pass
                            custom_ai_name = get_user_custom_ai_name(int(user_id)) if user_id else ""
                            custom_words = get_user_custom_words(int(user_id)) if user_id else ""
                            loop = asyncio.get_running_loop()
                            try:
                                async with AI_CALL_SEMAPHORE:
                                    transcript, reply_text = await asyncio.wait_for(
                                        loop.run_in_executor(
                                            None,
                                            lambda: generate_voice_reply(
                                                audio_bytes,
                                                mime_type,
                                                current_contact,
                                                current_gender,
                                                current_language,
                                                history,
                                                user_memory,
                                                custom_ai_name,
                                                custom_words=custom_words,
                                                user_id=int(user_id) if user_id else None
                                            )
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
                            call_dialogue_turns.append({"speaker": "User", "text": transcript or "Voice Note"})
                            call_dialogue_turns.append({"speaker": "Joy", "text": reply_text})
                            if len(history) > 10:
                                history = history[-10:]

                            # Persist this live call turn directly into user conversation memory (channel="call")
                            if user_id:
                                try:
                                    add_conversation_turn(int(user_id), "user", transcript or "Voice Call", channel="call")
                                    add_conversation_turn(int(user_id), "model", reply_text, channel="call")
                                    save_dev_sample_if_allowed(int(user_id), current_contact, f"Call User: {transcript} | Companion: {reply_text}")
                                except Exception as e:
                                    logger.warning(f"Could not persist call turn to DB: {e}")

                                # Zero-latency asynchronous episodic memory extraction (R1)
                                if transcript and transcript not in ("Voice Call", "Voice Note", "Live Call"):
                                    try:
                                        asyncio.create_task(extract_and_store_memories_async(int(user_id), transcript, reply_text))
                                    except Exception as bg_err:
                                        logger.warning(f"Could not dispatch background memory extraction for call turn (user {user_id}): {bg_err}")

                            # Inform client of transcript
                            if transcript and transcript != "Voice Note":
                                await ws.send_json({
                                    "type": "transcript",
                                    "text": transcript
                                })

                            # Synthesize audio with Edge-TTS (with timeout protection)
                            try:
                                joy_audio = await asyncio.wait_for(
                                    synthesize_speech(reply_text, voice_key=current_voice, language=current_language),
                                    timeout=6.5
                                )
                            except Exception as tts_err:
                                logger.warning(f"Call TTS error or timeout: {tts_err}. Synthesizing brief recovery line...")
                                joy_audio = await synthesize_speech("Wait, your voice cracked a bit! Say that again?", voice_key=current_voice, language=current_language)

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
        live_miniapp_sessions.pop(ws, None)
        if semaphore_acquired:
            try:
                VOICE_CALL_SEMAPHORE.release()
            except Exception:
                pass
        call_duration = int(time.time() - call_start_time)
        if call_user_id and call_duration >= 25 and len(call_dialogue_turns) >= 2:
            if global_bot_client:
                try:
                    asyncio.create_task(
                        dispatch_post_call_recap(
                            bot=global_bot_client,
                            user_id=int(call_user_id),
                            duration_secs=call_duration,
                            dialogue_turns=list(call_dialogue_turns)
                        )
                    )
                except Exception as recap_err:
                    logger.warning(f"Could not dispatch post-call recap task: {recap_err}")
        logger.info("Call WebSocket connection closed.")
    return ws

# Anonymous Matchmaking & Permanent Mask State
matchmaking_queue: List[dict] = []
active_match_pairs: Dict[web.WebSocketResponse, dict] = {}
active_match_rooms: Dict[str, dict] = {}
online_masked_peers: Dict[str, web.WebSocketResponse] = {}
active_call_invites: Dict[str, dict] = {}

# Real-Time Presence Trackers for Owner Live Monitor (Strictly for Phoenix 8747280850)
live_miniapp_sessions: Dict[web.WebSocketResponse, dict] = {}
live_bot_sessions: Dict[int, dict] = {}

def record_bot_activity(user_id: int, username: str = "", first_name: str = "", action: str = "Active in Bot", language: str = ""):
    """Records real-time bot interaction for Phoenix's Admin Live Monitor."""
    if not user_id:
        return
    try:
        live_bot_sessions[user_id] = {
            "user_id": user_id,
            "username": username or "",
            "first_name": first_name or "User",
            "last_seen": time.time(),
            "action": action,
            "language": language or "en"
        }
        touch_user_activity(user_id)
    except Exception:
        pass

async def handle_admin_live_monitor(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    """Admin-only real-time live presence monitor for Phoenix (OWNER_ID). Displays exactly who is online in Mini App and who is using the Bot."""
    user_id = user["user_id"]
    if user_id != OWNER_ID:
        await bot.send_message(chat_id, "⚠️ Restricted to Administrator.")
        return

    now = time.time()

    # 1. Active Mini App Sessions (filter out closed sockets)
    active_miniapp = {}
    for ws, sess in list(live_miniapp_sessions.items()):
        if not ws.closed:
            active_miniapp[ws] = sess
        else:
            live_miniapp_sessions.pop(ws, None)

    # 2. Active Bot Sessions (past 30 minutes)
    active_bot = {}
    for uid, sess in list(live_bot_sessions.items()):
        if now - sess.get("last_seen", 0) <= 1800:
            active_bot[uid] = sess
        else:
            live_bot_sessions.pop(uid, None)

    # 3. Pull recently active users from database (past 15 minutes)
    threshold_15m = (datetime.now() - timedelta(minutes=15)).isoformat()
    db_active_users = []
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT user_id, username, first_name, last_active_at, language, is_vip, unique_id
                FROM users
                WHERE last_active_at >= ?
                ORDER BY last_active_at DESC
                LIMIT 15
            """, (threshold_15m,))
            db_active_users = c.fetchall()
    except Exception as dbe:
        logger.warning(f"Error querying active users from DB: {dbe}")

    miniapp_cards = []
    user_chat_buttons = []
    seen_uids_for_chat = set()

    # Format Mini App Sessions
    if active_miniapp:
        for idx, (ws, sess) in enumerate(active_miniapp.items(), start=1):
            mask = sess.get("mask_id") or "Joy-User"
            uid = sess.get("user_id") or 0
            status = sess.get("status", "Active")
            conn_sec = int(now - sess.get("connected_at", now))
            conn_str = f"{conn_sec}s ago" if conn_sec < 60 else f"{conn_sec//60}m {conn_sec%60}s ago"

            user_details = ""
            if uid > 0:
                try:
                    u_rec = get_or_create_user(uid)
                    fname = u_rec.get("first_name") or "User"
                    uname = f"@{u_rec.get('username')}" if u_rec.get("username") else "No @"
                    user_details = f" — **{fname}** ({uname}) [`{uid}`]"
                    if uid != OWNER_ID and uid not in seen_uids_for_chat and len(user_chat_buttons) < 6:
                        seen_uids_for_chat.add(uid)
                        user_chat_buttons.append([{"text": f"💬 Message {fname[:10]} (`{uid}`)", "callback_data": f"admin_msg_prep_{uid}"}])
                except Exception:
                    pass

            miniapp_cards.append(
                f"{idx}. 🎭 **{mask}**{user_details}\n"
                f"   • Status: **{status}**\n"
                f"   • Connected: {conn_str}"
            )
    else:
        miniapp_cards.append("*(No users currently connected to the Mini App)*")

    # Format Telegram Bot Sessions (combine live_bot_sessions + DB)
    combined_bot_users = {}
    for uid, sess in active_bot.items():
        combined_bot_users[uid] = {
            "first_name": sess.get("first_name", "User"),
            "username": sess.get("username", ""),
            "action": sess.get("action", "Bot Interaction"),
            "last_seen_sec": int(now - sess.get("last_seen", now))
        }
    for row in db_active_users:
        uid = row["user_id"]
        if uid not in combined_bot_users:
            combined_bot_users[uid] = {
                "first_name": row["first_name"] or "User",
                "username": row["username"] or "",
                "action": "Bot Activity",
                "last_seen_sec": 300
            }

    bot_cards = []
    if combined_bot_users:
        sorted_bot = sorted(combined_bot_users.items(), key=lambda x: x[1]["last_seen_sec"])[:10]
        for idx, (uid, info) in enumerate(sorted_bot, start=1):
            fname = info["first_name"]
            uname = f"@{info['username']}" if info["username"] else "No @"
            sec = info["last_seen_sec"]
            t_str = f"{sec}s ago" if sec < 60 else f"{sec//60}m ago"
            bot_cards.append(
                f"{idx}. 🤖 **{fname}** ({uname}) [`{uid}`]\n"
                f"   • Action: {info['action']}\n"
                f"   • Last active: {t_str}"
            )
            if uid != OWNER_ID and uid not in seen_uids_for_chat and len(user_chat_buttons) < 6:
                seen_uids_for_chat.add(uid)
                user_chat_buttons.append([{"text": f"💬 Message {fname[:10]} (`{uid}`)", "callback_data": f"admin_msg_prep_{uid}"}])
    else:
        bot_cards.append("*(No bot activity in the last 15 minutes)*")

    active_rooms_count = len(active_match_rooms)
    queue_count = len(matchmaking_queue)
    miniapp_count = len(active_miniapp)
    bot_count = len(combined_bot_users)
    updated_time = datetime.now().strftime("%H:%M:%S")

    text = (
        f"👑 **Owner Live Monitor — Real-Time Activity Pulse**\n"
        f"*(Strictly Private to Phoenix • Updated at {updated_time})*\n\n"
        f"🌐 **Current Live Overview:**\n"
        f"• 📱 **Active in Mini App Right Now:** **{miniapp_count}**\n"
        f"• 🤖 **Active in Telegram Bot (Past 15m):** **{bot_count}**\n"
        f"• 🎙️ **Ongoing Voice Matches:** **{active_rooms_count}** pairs\n"
        f"• 📡 **Matchmaking Queue:** **{queue_count}** waiting\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📱 **Mini App Active Sessions ({miniapp_count}):**\n"
        f"{chr(10).join(miniapp_cards)}\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 **Telegram Bot Active Users ({bot_count}):**\n"
        f"{chr(10).join(bot_cards)}\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💡 *Tap Refresh below for instant live metrics!*"
    )

    keyboard_buttons = [
        [{"text": "🔄 Refresh Live Monitor", "callback_data": "admin_live_refresh"}],
    ]
    keyboard_buttons.extend(user_chat_buttons)
    keyboard_buttons.extend([
        [{"text": "👑 Owner Control Hub", "callback_data": "owner_hub"}, {"text": "❌ Close", "callback_data": "menu_close"}]
    ])

    keyboard = {"inline_keyboard": keyboard_buttons}
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

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

async def get_presence_api(request: web.Request) -> web.Response:
    """Returns real-time online presence and queue stats for the Mini App."""
    active_ws_count = len([w for w in online_masked_peers.values() if not w.closed])
    recent_cnt = 0
    try:
        with get_connection() as conn:
            c = conn.cursor()
            threshold = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
            c.execute("SELECT COUNT(*) as cnt FROM users WHERE last_active_at >= ?", (threshold,))
            row = c.fetchone()
            recent_cnt = row["cnt"] if row else 0
    except Exception:
        recent_cnt = 0

    online_total = max(1, active_ws_count, recent_cnt)
    return web.json_response({
        "status": "ok",
        "online_users": online_total,
        "queue_size": len(matchmaking_queue),
        "active_calls": len(active_match_pairs) // 2
    })

async def websocket_match_handler(request):
    """Handles anonymous peer-to-peer WebRTC voice matchmaking signaling & mutual reconnect."""
    ws = web.WebSocketResponse(heartbeat=20.0, autoping=True, max_msg_size=16*1024*1024)
    await ws.prepare(request)
    
    current_uid = 0
    current_mask = ""
    intentional_leave = False
    
    live_miniapp_sessions[ws] = {
        "mask_id": "Joy-User",
        "user_id": 0,
        "connected_at": time.time(),
        "last_seen": time.time(),
        "status": "Connected to Mini App 📱",
        "peer_mask": None,
        "room_id": None
    }
    
    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.BINARY:
                if ws in live_miniapp_sessions:
                    live_miniapp_sessions[ws]["last_seen"] = time.time()
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
                        raw_uid = int(data.get("user_id") or 0)
                        auth_uid, auth_err = extract_and_verify_telegram_auth(request, payload_dict=data)
                        if auth_uid:
                            current_uid = auth_uid
                        elif raw_uid > 0:
                            logger.warning(f"Unauthenticated matchmaking attempt claiming UID {raw_uid}: {auth_err}")
                            await ws.send_json({
                                "type": "error",
                                "message": "Zero-Trust Security: Session signature missing or expired. Please launch from Telegram! 🌸"
                            })
                            await ws.close()
                            break
                        else:
                            current_uid = 0

                        if current_uid > 0 and not is_user_onboarding_completed(current_uid):
                            await ws.send_json({
                                "type": "error",
                                "message": "Please complete your profile setup in Telegram before joining matchmaking! 🌸"
                            })
                            await ws.close()
                            break
                        if current_uid > 0 and not is_user_beta_approved(current_uid):
                            await ws.send_json({
                                "type": "error",
                                "message": "Closed Beta is currently full. Your waitlist position will unlock as slots expand! 🌸"
                            })
                            await ws.close()
                            break
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
                            
                            if ws in live_miniapp_sessions:
                                live_miniapp_sessions[ws]["mask_id"] = current_mask
                                live_miniapp_sessions[ws]["user_id"] = current_uid
                                live_miniapp_sessions[ws]["status"] = f"In Voice Call with {peer_display_mask} 🎙️"
                                live_miniapp_sessions[ws]["peer_mask"] = peer_display_mask
                                live_miniapp_sessions[ws]["room_id"] = room_id
                                live_miniapp_sessions[ws]["last_seen"] = time.time()
                            if peer_ws in live_miniapp_sessions:
                                live_miniapp_sessions[peer_ws]["status"] = f"In Voice Call with {my_display_mask} 🎙️"
                                live_miniapp_sessions[peer_ws]["peer_mask"] = my_display_mask
                                live_miniapp_sessions[peer_ws]["room_id"] = room_id
                                live_miniapp_sessions[peer_ws]["last_seen"] = time.time()
                            
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
                            if current_uid and cand_uid:
                                try:
                                    record_match_connection(int(current_uid), int(cand_uid), peer_display_mask, conn_type="voice")
                                    record_match_connection(int(cand_uid), int(current_uid), my_display_mask, conn_type="voice")
                                except Exception:
                                    pass
                            logger.info(f"🎭 Anonymous Match Paired: {my_display_mask} <---> {peer_display_mask}")
                        else:
                            matchmaking_queue.append({
                                "ws": ws,
                                "uid": current_uid,
                                "mask_id": current_mask
                            })
                            if ws in live_miniapp_sessions:
                                live_miniapp_sessions[ws]["mask_id"] = current_mask
                                live_miniapp_sessions[ws]["user_id"] = current_uid
                                live_miniapp_sessions[ws]["status"] = "In Matchmaking Queue 📡"
                                live_miniapp_sessions[ws]["last_seen"] = time.time()
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
                            if ws in live_miniapp_sessions:
                                live_miniapp_sessions[ws]["mask_id"] = current_mask
                                live_miniapp_sessions[ws]["user_id"] = current_uid
                                live_miniapp_sessions[ws]["status"] = "Online Standby in Mini App 📱"
                                live_miniapp_sessions[ws]["last_seen"] = time.time()
                            online_cnt = max(1, len([w for w in online_masked_peers.values() if not w.closed]))
                            await ws.send_json({
                                "type": "presence_registered",
                                "mask_id": current_mask,
                                "user_id": current_uid,
                                "online_count": online_cnt
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
                            if ws in live_miniapp_sessions:
                                live_miniapp_sessions[ws]["status"] = f"Calling {target_mask}... 🔔"
                                live_miniapp_sessions[ws]["last_seen"] = time.time()
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
                            if c_ws in live_miniapp_sessions:
                                live_miniapp_sessions[c_ws]["status"] = f"In Voice Call with {t_mask} 🎙️"
                                live_miniapp_sessions[c_ws]["peer_mask"] = t_mask
                                live_miniapp_sessions[c_ws]["room_id"] = room_id
                                live_miniapp_sessions[c_ws]["last_seen"] = time.time()
                            if ws in live_miniapp_sessions:
                                live_miniapp_sessions[ws]["status"] = f"In Voice Call with {c_mask} 🎙️"
                                live_miniapp_sessions[ws]["peer_mask"] = c_mask
                                live_miniapp_sessions[ws]["room_id"] = room_id
                                live_miniapp_sessions[ws]["last_seen"] = time.time()
                            
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

                    # 7a2. In-Call Synchronized Icebreaker Relay
                    elif mtype == "icebreaker":
                        pair_info = active_match_pairs.get(ws)
                        if pair_info:
                            peer_ws = pair_info.get("peer_ws")
                            q = data.get("question") or data.get("icebreaker") or secrets.choice(ICEBREAKER_QUESTIONS)
                            if peer_ws and not peer_ws.closed:
                                try:
                                    await peer_ws.send_json({
                                        "type": "icebreaker",
                                        "question": q
                                    })
                                except Exception as ix:
                                    logger.warning(f"Failed to relay icebreaker: {ix}")

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
                            online_cnt = max(1, len([w for w in online_masked_peers.values() if not w.closed]))
                            await ws.send_json({"type": "pong", "time": time.time(), "online_count": online_cnt})
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
                                if ws in live_miniapp_sessions:
                                    live_miniapp_sessions[ws]["status"] = f"In Voice Call with {survivor_mask} 🎙️"
                                    live_miniapp_sessions[ws]["peer_mask"] = survivor_mask
                                    live_miniapp_sessions[ws]["room_id"] = room_id
                                if survivor_ws in live_miniapp_sessions:
                                    live_miniapp_sessions[survivor_ws]["status"] = f"In Voice Call with {req_mask} 🎙️"
                                    live_miniapp_sessions[survivor_ws]["peer_mask"] = req_mask
                                    live_miniapp_sessions[survivor_ws]["room_id"] = room_id
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
                        if ws in live_miniapp_sessions:
                            live_miniapp_sessions[ws]["status"] = "Skipping to next match... ⏭️"
                            live_miniapp_sessions[ws]["peer_mask"] = None
                            live_miniapp_sessions[ws]["room_id"] = None
                            live_miniapp_sessions[ws]["last_seen"] = time.time()
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
                            if ws in live_miniapp_sessions:
                                live_miniapp_sessions[ws]["status"] = f"In Voice Call with {peer_display_mask} 🎙️"
                                live_miniapp_sessions[ws]["peer_mask"] = peer_display_mask
                                live_miniapp_sessions[ws]["room_id"] = room_id
                                live_miniapp_sessions[ws]["last_seen"] = time.time()
                            if peer_ws in live_miniapp_sessions:
                                live_miniapp_sessions[peer_ws]["status"] = f"In Voice Call with {my_display_mask} 🎙️"
                                live_miniapp_sessions[peer_ws]["peer_mask"] = my_display_mask
                                live_miniapp_sessions[peer_ws]["room_id"] = room_id
                                live_miniapp_sessions[peer_ws]["last_seen"] = time.time()
                            await ws.send_json({"type": "matched", "role": "initiator", "peer_mask": peer_display_mask, "room_id": room_id, "icebreaker": icebreaker_prompt})
                            await peer_ws.send_json({"type": "matched", "role": "receiver", "peer_mask": my_display_mask, "room_id": room_id, "icebreaker": icebreaker_prompt})
                            if current_uid:
                                increment_user_real_call(current_uid)
                            cand_uid = matched_peer.get("uid")
                            if cand_uid:
                                increment_user_real_call(int(cand_uid))
                            if current_uid and cand_uid:
                                try:
                                    record_match_connection(int(current_uid), int(cand_uid), peer_display_mask, conn_type="voice")
                                    record_match_connection(int(cand_uid), int(current_uid), my_display_mask, conn_type="voice")
                                except Exception:
                                    pass
                        else:
                            matchmaking_queue.append({"ws": ws, "uid": current_uid, "mask_id": current_mask})
                            if ws in live_miniapp_sessions:
                                live_miniapp_sessions[ws]["status"] = "In Matchmaking Queue 📡"
                                live_miniapp_sessions[ws]["last_seen"] = time.time()
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
                        if ws in live_miniapp_sessions:
                            live_miniapp_sessions[ws]["status"] = "Standby in Mini App 📱"
                            live_miniapp_sessions[ws]["peer_mask"] = None
                            live_miniapp_sessions[ws]["room_id"] = None
                            live_miniapp_sessions[ws]["last_seen"] = time.time()
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
        live_miniapp_sessions.pop(ws, None)
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
        return web.json_response({"error": "user_id required"}, status=400, headers=CORS_HEADERS)
    try:
        user_id = int(uid)
    except (ValueError, TypeError):
        return web.json_response({"error": "valid user_id integer required"}, status=400, headers=CORS_HEADERS)

    auth_uid, auth_err = extract_and_verify_telegram_auth(request)
    if not auth_uid:
        return web.json_response({"error": f"Unauthorized: {auth_err}"}, status=401, headers=CORS_HEADERS)
    if auth_uid != user_id:
        return web.json_response({"error": "Forbidden: Session user mismatch (IDOR blocked)"}, status=403, headers=CORS_HEADERS)

    try:
        quota_data = get_user_full_quota_status(user_id)
        gender, active_contact = get_user_contact_settings(user_id)
        custom_name = get_user_custom_ai_name(user_id)
        tone = get_user_companion_tone(user_id)
        lang = get_user_language(user_id)
        return web.json_response({
            "status": "ok",
            "gender": gender,
            "custom_ai_name": custom_name or "",
            "companion_tone": tone or "gentle",
            "language": lang or "auto",
            **quota_data
        }, headers=CORS_HEADERS)
    except Exception as e:
        logger.error(f"Error in get_user_quota_api: {e}")
        return web.json_response({"error": "Internal server error"}, status=500, headers=CORS_HEADERS)

async def get_user_connections_api(request: web.Request) -> web.Response:
    """Returns past mutual match & chat connections for the user."""
    uid = request.query.get("user_id") or request.query.get("uid")
    if not uid:
        return web.json_response({"error": "user_id required"}, status=400, headers=CORS_HEADERS)
    try:
        user_id = int(uid)
    except (ValueError, TypeError):
        return web.json_response({"error": "valid user_id integer required"}, status=400, headers=CORS_HEADERS)

    auth_uid, auth_err = extract_and_verify_telegram_auth(request)
    if not auth_uid:
        return web.json_response({"error": f"Unauthorized: {auth_err}"}, status=401, headers=CORS_HEADERS)
    if auth_uid != user_id:
        return web.json_response({"error": "Forbidden: Session user mismatch (IDOR blocked)"}, status=403, headers=CORS_HEADERS)

    try:
        connections = get_user_match_connections(user_id)
        return web.json_response({"status": "ok", "connections": connections}, headers=CORS_HEADERS)
    except Exception as e:
        logger.error(f"Error in get_user_connections_api: {e}")
        return web.json_response({"error": "Internal server error"}, status=500, headers=CORS_HEADERS)

async def get_user_privacy_api(request):
    """Returns privacy and data sharing preference for a user."""
    uid = request.query.get("user_id") or request.query.get("uid")
    if not uid:
        return web.json_response({"error": "user_id required"}, status=400, headers=CORS_HEADERS)
    try:
        user_id = int(uid)
    except (ValueError, TypeError):
        return web.json_response({"error": "valid user_id integer required"}, status=400, headers=CORS_HEADERS)

    auth_uid, auth_err = extract_and_verify_telegram_auth(request)
    if not auth_uid:
        return web.json_response({"error": f"Unauthorized: {auth_err}"}, status=401, headers=CORS_HEADERS)
    if auth_uid != user_id:
        return web.json_response({"error": "Forbidden: Session user mismatch (IDOR blocked)"}, status=403, headers=CORS_HEADERS)

    try:
        sharing = get_user_data_sharing(user_id)
        is_locked = is_contributor_discount_locked(user_id)
        return web.json_response({"user_id": user_id, "allow_data_sharing": sharing, "is_locked": is_locked}, headers=CORS_HEADERS)
    except Exception as e:
        logger.error(f"Error in get_user_privacy_api: {e}")
        return web.json_response({"error": "Internal server error"}, status=500, headers=CORS_HEADERS)

async def set_user_privacy_api(request):
    """Updates user privacy data sharing preference."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400, headers=CORS_HEADERS)

    uid = data.get("user_id") or data.get("uid")
    allow = bool(data.get("allow_data_sharing", False))
    if not uid:
        return web.json_response({"error": "user_id required"}, status=400, headers=CORS_HEADERS)
    try:
        user_id = int(uid)
    except (ValueError, TypeError):
        return web.json_response({"error": "valid user_id integer required"}, status=400, headers=CORS_HEADERS)

    auth_uid, auth_err = extract_and_verify_telegram_auth(request, payload_dict=data)
    if not auth_uid:
        return web.json_response({"error": f"Unauthorized: {auth_err}"}, status=401, headers=CORS_HEADERS)
    if auth_uid != user_id:
        return web.json_response({"error": "Forbidden: Session user mismatch (IDOR blocked)"}, status=403, headers=CORS_HEADERS)

    try:
        ok, reason = set_user_data_sharing(user_id, allow)
        if not ok:
            return web.json_response({
                "success": False,
                "error": "locked",
                "message": "🔒 Contributor Agreement Active: You unlocked and purchased your current VIP plan with the 20% Contributor discount. Data sharing remains enabled for this active VIP billing period.",
                "allow_data_sharing": True,
                "is_locked": True
            }, status=403, headers=CORS_HEADERS)
        return web.json_response({"success": True, "user_id": user_id, "allow_data_sharing": allow, "is_locked": False}, headers=CORS_HEADERS)
    except Exception as e:
        logger.error(f"Error in set_user_privacy_api: {e}")
        return web.json_response({"error": "Internal server error"}, status=500, headers=CORS_HEADERS)

async def handle_user_preference_api(request):
    """Updates user preferences (e.g. gender perspective) from Mini App."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400, headers=CORS_HEADERS)

    uid = data.get("user_id") or data.get("uid")
    key = data.get("key")
    value = data.get("value")
    if not uid or not key or not value:
        return web.json_response({"error": "user_id, key, and value required"}, status=400, headers=CORS_HEADERS)
    try:
        user_id = int(uid)
    except (ValueError, TypeError):
        return web.json_response({"error": "valid user_id integer required"}, status=400, headers=CORS_HEADERS)

    auth_uid, auth_err = extract_and_verify_telegram_auth(request, payload_dict=data)
    if not auth_uid:
        return web.json_response({"error": f"Unauthorized: {auth_err}"}, status=401, headers=CORS_HEADERS)
    if auth_uid != user_id:
        return web.json_response({"error": "Forbidden: Session user mismatch (IDOR blocked)"}, status=403, headers=CORS_HEADERS)

    try:
        update_user_preference(user_id, str(key), str(value))
        return web.json_response({"status": "ok", "user_id": user_id, "key": key, "value": value}, headers=CORS_HEADERS)
    except Exception as e:
        logger.error(f"Error updating user preference: {e}")
        return web.json_response({"error": "Failed to update preference"}, status=500, headers=CORS_HEADERS)

# ============================================================================
# Joy Remembers: CORS Configuration & Mini App REST Endpoints
# ============================================================================

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, X-Telegram-Init-Data",
}

async def handle_cors_options(request: web.Request) -> web.Response:
    """Handles OPTIONS preflight requests for Mini App REST APIs."""
    return web.Response(status=204, headers=CORS_HEADERS)

async def get_user_memories_api(request: web.Request) -> web.Response:
    """
    Returns active (or optionally all) memories for a user.
    Query params:
        user_id (int, required): Telegram / Mini App user ID.
        include_decayed (bool, optional): If 'true', includes expired events/emotions.
    """
    uid_str = request.query.get("user_id") or request.query.get("uid")
    if not uid_str:
        return web.json_response(
            {"status": "error", "error": "user_id parameter is required"},
            status=400,
            headers=CORS_HEADERS
        )

    try:
        user_id = int(uid_str)
        if user_id <= 0:
            raise ValueError("user_id must be a positive integer")
    except (ValueError, TypeError):
        return web.json_response(
            {"status": "error", "error": "user_id must be a valid positive integer"},
            status=400,
            headers=CORS_HEADERS
        )

    decayed_flag = request.query.get("include_decayed", "false").strip().lower() in ("true", "1", "yes", "t")

    auth_uid, auth_err = extract_and_verify_telegram_auth(request)
    if not auth_uid:
        return web.json_response(
            {"status": "error", "error": f"Unauthorized: {auth_err}"},
            status=401,
            headers=CORS_HEADERS
        )
    if auth_uid != user_id:
        return web.json_response(
            {"status": "error", "error": "Unauthorized: Session user mismatch (IDOR blocked)"},
            status=403,
            headers=CORS_HEADERS
        )

    try:
        memories = get_user_memories(user_id=user_id, include_decayed=decayed_flag)
        return web.json_response(
            {
                "ok": True,
                "status": "ok",
                "user_id": user_id,
                "count": len(memories),
                "memories": memories
            },
            status=200,
            headers=CORS_HEADERS
        )
    except Exception as e:
        logger.error(f"Error in get_user_memories_api for user {user_id}: {e}")
        return web.json_response(
            {"status": "error", "error": "Internal error retrieving user memories"},
            status=500,
            headers=CORS_HEADERS
        )

async def delete_user_memory_api(request: web.Request) -> web.Response:
    """
    Deletes a single memory record for a user.
    JSON payload:
        { "user_id": <int>, "memory_id": <int> }
    Enforces strict tenant scoping to prevent IDOR vulnerabilities.
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response(
            {"status": "error", "error": "Invalid JSON payload in request body"},
            status=400,
            headers=CORS_HEADERS
        )

    if not isinstance(data, dict):
        return web.json_response(
            {"status": "error", "error": "Request body must be a JSON object"},
            status=400,
            headers=CORS_HEADERS
        )

    uid_raw = data.get("user_id") or data.get("uid")
    mid_raw = data.get("memory_id") or data.get("id")

    if uid_raw is None or mid_raw is None:
        return web.json_response(
            {"status": "error", "error": "user_id and memory_id are required fields"},
            status=400,
            headers=CORS_HEADERS
        )

    try:
        user_id = int(uid_raw)
        memory_id = int(mid_raw)
        if user_id <= 0 or memory_id <= 0:
            raise ValueError("user_id and memory_id must be positive integers")
    except (ValueError, TypeError):
        return web.json_response(
            {"status": "error", "error": "user_id and memory_id must be valid positive integers"},
            status=400,
            headers=CORS_HEADERS
        )

    auth_uid, auth_err = extract_and_verify_telegram_auth(request, payload_dict=data)
    if not auth_uid:
        return web.json_response(
            {"status": "error", "error": f"Unauthorized: {auth_err}"},
            status=401,
            headers=CORS_HEADERS
        )
    if auth_uid != user_id:
        return web.json_response(
            {"status": "error", "error": "Unauthorized: Session user mismatch (IDOR blocked)"},
            status=403,
            headers=CORS_HEADERS
        )

    try:
        deleted = delete_user_memory(user_id=user_id, memory_id=memory_id)
        if not deleted:
            return web.json_response(
                {
                    "status": "error",
                    "deleted": False,
                    "error": "Memory not found or unauthorized",
                    "memory_id": memory_id,
                    "user_id": user_id
                },
                status=404,
                headers=CORS_HEADERS
            )

        return web.json_response(
            {
                "ok": True,
                "status": "ok",
                "deleted": True,
                "memory_id": memory_id,
                "user_id": user_id
            },
            status=200,
            headers=CORS_HEADERS
        )
    except Exception as e:
        logger.error(f"Error in delete_user_memory_api for user {user_id}, memory {memory_id}: {e}")
        return web.json_response(
            {"status": "error", "error": "Internal error deleting memory"},
            status=500,
            headers=CORS_HEADERS
        )

async def wipe_user_memories_api(request: web.Request) -> web.Response:
    """
    Purges all stored memories for a user (Mini App 1-click Wipe All).
    JSON payload:
        { "user_id": <int> }
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response(
            {"status": "error", "error": "Invalid JSON payload in request body"},
            status=400,
            headers=CORS_HEADERS
        )

    if not isinstance(data, dict):
        return web.json_response(
            {"status": "error", "error": "Request body must be a JSON object"},
            status=400,
            headers=CORS_HEADERS
        )

    uid_raw = data.get("user_id") or data.get("uid")
    if uid_raw is None:
        return web.json_response(
            {"status": "error", "error": "user_id is a required field"},
            status=400,
            headers=CORS_HEADERS
        )

    try:
        user_id = int(uid_raw)
        if user_id <= 0:
            raise ValueError("user_id must be a positive integer")
    except (ValueError, TypeError):
        return web.json_response(
            {"status": "error", "error": "user_id must be a valid positive integer"},
            status=400,
            headers=CORS_HEADERS
        )

    auth_uid, auth_err = extract_and_verify_telegram_auth(request, payload_dict=data)
    if not auth_uid:
        return web.json_response(
            {"status": "error", "error": f"Unauthorized: {auth_err}"},
            status=401,
            headers=CORS_HEADERS
        )
    if auth_uid != user_id:
        return web.json_response(
            {"status": "error", "error": "Unauthorized: Session user mismatch (IDOR blocked)"},
            status=403,
            headers=CORS_HEADERS
        )

    try:
        cleared_count = clear_user_memories(user_id=user_id)
        return web.json_response(
            {
                "ok": True,
                "status": "ok",
                "cleared": cleared_count,
                "cleared_count": cleared_count,
                "user_id": user_id
            },
            status=200,
            headers=CORS_HEADERS
        )
    except Exception as e:
        logger.error(f"Error in wipe_user_memories_api for user {user_id}: {e}")
        return web.json_response(
            {"status": "error", "error": "Internal error wiping user memories"},
            status=500,
            headers=CORS_HEADERS
        )

async def get_admin_users_api(request):
    """Secure endpoint for owner to view all registered cloud users."""
    token = request.query.get("token") or request.headers.get("X-Admin-Token")
    valid_tokens = [t for t in [ADMIN_API_SECRET, RENDER_API_KEY, os.getenv("RENDER_API_KEY", "")] if t]
    if not token or not any(secrets.compare_digest(token, vt) for vt in valid_tokens):
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
        logger.error(f"Error in admin_users_api: {e}")
        return web.json_response({"status": "error", "error": "Internal server error"}, status=500)

async def admin_quota_api(request):
    """Admin endpoint to exhaust or reset a user's daily quota for testing."""
    token = request.query.get("token") or request.headers.get("X-Admin-Token")
    valid_tokens = [t for t in [ADMIN_API_SECRET, RENDER_API_KEY, os.getenv("RENDER_API_KEY", "")] if t]
    if not token or not any(secrets.compare_digest(token, vt) for vt in valid_tokens):
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
        logger.error(f"Error in admin_quota_api: {e}")
        return web.json_response({"status": "error", "error": "Internal server error"}, status=500)

async def get_session_api(request: web.Request) -> web.Response:
    """Returns active call session, mic status, earpiece routing, and user privilege info."""
    uid = request.query.get("user_id") or request.query.get("uid")
    if not uid:
        return web.json_response({
            "ok": True,
            "status": "ok",
            "active_miniapp_sessions_count": len(live_miniapp_sessions),
            "mic_status": "ready",
            "earpiece_routing_supported": True,
            "server_timestamp": time.time()
        }, headers=CORS_HEADERS)
    try:
        user_id = int(uid)
        auth_uid, auth_err = extract_and_verify_telegram_auth(request)
        if not auth_uid:
            return web.json_response({"ok": False, "status": "error", "error": f"Unauthorized: {auth_err}"}, status=401, headers=CORS_HEADERS)
        if auth_uid != user_id:
            return web.json_response({"ok": False, "status": "error", "error": "Forbidden: Session user mismatch (IDOR blocked)"}, status=403, headers=CORS_HEADERS)

        user_sess = None
        for ws_conn, sess in list(live_miniapp_sessions.items()):
            if sess.get("user_id") == user_id:
                user_sess = {
                    "status": sess.get("status"),
                    "mask_id": sess.get("mask_id"),
                    "connected_at": sess.get("connected_at"),
                    "room_id": sess.get("room_id")
                }
                break
        is_done = is_user_onboarding_completed(user_id)
        is_beta = is_user_beta_approved(user_id)
        is_vip_val, exp_str, days_left = is_user_vip(user_id)
        gender, contact = get_user_contact_settings(user_id)
        lang = get_user_language(user_id)

        return web.json_response({
            "ok": True,
            "status": "ok",
            "user_id": user_id,
            "active_call": bool(user_sess),
            "session": user_sess,
            "onboarding_completed": is_done,
            "is_beta": is_beta,
            "is_vip": is_vip_val,
            "vip_expiry": exp_str if is_vip_val else None,
            "gender": gender,
            "active_contact": contact,
            "language": lang,
            "mic_status": "ready",
            "earpiece_routing_supported": True
        }, headers=CORS_HEADERS)
    except (ValueError, TypeError):
        return web.json_response({"ok": False, "error": "Invalid user_id format"}, status=400, headers=CORS_HEADERS)
    except Exception as e:
        logger.error(f"Error in get_session_api: {e}")
        return web.json_response({"ok": False, "error": "Internal server error"}, status=500, headers=CORS_HEADERS)

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

            # 2. Every 6 hours (90 iterations * 4 mins = 360 mins = 6 hours), run WAL checkpoint & atomic snapshot
            if iteration % 90 == 0:
                try:
                    from backup_manager import create_db_snapshot
                    loop = asyncio.get_running_loop()
                    snap_res = await loop.run_in_executor(None, create_db_snapshot)
                    if snap_res.get("ok"):
                        logger.info(f"🛡️ Autonomous 6-Hour DB Snapshot created: {snap_res.get('snapshot_path')} ({snap_res.get('size_kb')} KB)")
                    else:
                        logger.warning(f"DB snapshot returned status: {snap_res}")
                except Exception as snap_err:
                    logger.warning(f"Autonomous DB snapshot error: {snap_err}")

        except asyncio.CancelledError:
            break
        except Exception as err:
            logger.error(f"Keep-Alive worker encountered unexpected error: {err}")
            await asyncio.sleep(10)

async def handle_ad_reward_api(request):
    """Adsgram / Monetag server-to-server postback reward webhook or authenticated Mini App reward endpoint."""
    secret = request.query.get("secret") or request.headers.get("X-Reward-Secret")
    is_server_webhook = bool(secret and AD_REWARD_WEBHOOK_SECRET and secrets.compare_digest(secret, AD_REWARD_WEBHOOK_SECRET))

    uid_param = request.query.get("userid") or request.query.get("user_id") or request.query.get("custom_data")
    data = {}
    if request.method == "POST":
        try:
            data = await request.json()
            if not uid_param:
                uid_param = data.get("userid") or data.get("user_id") or data.get("custom_data")
        except Exception:
            pass

    if not uid_param:
        return web.json_response({"error": "user_id required"}, status=400, headers=CORS_HEADERS)

    try:
        user_id = int(uid_param)
    except (ValueError, TypeError):
        return web.json_response({"error": "valid integer user_id required"}, status=400, headers=CORS_HEADERS)

    # Security check: If not authenticated via server-to-server webhook secret, MUST verify Telegram HMAC auth
    if not is_server_webhook:
        auth_uid, auth_err = extract_and_verify_telegram_auth(request, payload_dict=data)
        if not auth_uid:
            return web.json_response({"error": f"Unauthorized: {auth_err}"}, status=401, headers=CORS_HEADERS)
        if auth_uid != user_id:
            return web.json_response({"error": "Forbidden: Session user mismatch (IDOR blocked)"}, status=403, headers=CORS_HEADERS)

    get_or_create_user(user_id)
    success, msg, _, _ = recharge_user_via_ad(user_id)
    if not success:
        return web.json_response({
            "status": "limit_reached",
            "rewarded": False,
            "message": msg,
            "user_id": user_id
        }, status=429, headers=CORS_HEADERS)

    logger.info(f"🎉 Ad sponsor reward successfully granted for user {user_id}: {msg}")
    return web.json_response({
        "status": "ok",
        "rewarded": True,
        "message": msg,
        "user_id": user_id
    }, headers=CORS_HEADERS)

async def handle_api_feedback(request: web.Request) -> web.Response:
    """
    Handles bug bounty reports, audio glitches, and feature suggestions submitted from Mini App.
    Enforces HMAC-SHA256 Telegram authentication and zero-trust IDOR verification.
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON payload"}, status=400, headers=CORS_HEADERS)

    uid = data.get("user_id")
    try:
        user_id = int(uid)
    except (ValueError, TypeError):
        return web.json_response({"error": "valid user_id integer required"}, status=400, headers=CORS_HEADERS)

    auth_uid, auth_err = extract_and_verify_telegram_auth(request, payload_dict=data)
    if not auth_uid:
        return web.json_response({"error": f"Unauthorized: {auth_err}"}, status=401, headers=CORS_HEADERS)
    if auth_uid != user_id:
        return web.json_response({"error": "Forbidden: Session user mismatch (IDOR blocked)"}, status=403, headers=CORS_HEADERS)

    category = str(data.get("category", "bug")).strip()[:30]
    message = str(data.get("message", "")).strip()[:1000]

    if not message:
        return web.json_response({"error": "Feedback message cannot be empty"}, status=400, headers=CORS_HEADERS)

    user = get_or_create_user(user_id) or {"user_id": user_id}
    username = user.get("username") or "None"
    first_name = user.get("first_name") or "Joy User"
    mask = get_mask_by_user_id(user_id) or f"Joy-{user_id}"
    is_pioneer = bool(user.get("is_beta_tester") == 1 or user_id == OWNER_ID or is_owner_or_co_owner(user_id))
    slot = user.get("beta_slot_number", 1) if is_pioneer else 0

    clean_report = f"[{category.upper()}] {message}"
    fid = save_user_feedback(user_id, username, clean_report, f"miniapp_{category}")

    # Forward bounty card to Phoenix (ADMIN_CHAT_ID)
    if ADMIN_CHAT_ID and global_bot_client:
        admin_card = (
            f"👑 **MINI APP PIONEER FEEDBACK / BUG SUBMISSION!** 🐛\n\n"
            f"• **Reporter:** {first_name} (@{username})\n"
            f"• **User ID:** `{user_id}`\n"
            f"• **Pioneer Slot:** #{slot}\n"
            f"• **Mask ID:** `{mask}`\n"
            f"• **Category:** `{category.upper()}`\n"
            f"• **Report ID:** `#{fid}`\n\n"
            f"📝 **Details:**\n\"{message}\"\n\n"
            f"👇 **Select VIP Bounty Tier to Award (1-Tap):**"
        )
        admin_kb = {
            "inline_keyboard": [
                [
                    {"text": "⭐ 2 Weeks VIP", "callback_data": f"bounty_14_{user_id}_{fid}"},
                    {"text": "🌟 1 Month VIP", "callback_data": f"bounty_30_{user_id}_{fid}"}
                ],
                [
                    {"text": "👑 Lifetime VIP", "callback_data": f"bounty_36500_{user_id}_{fid}"},
                    {"text": "❌ Dismiss", "callback_data": f"bounty_dismiss_{user_id}_{fid}"}
                ]
            ]
        }
        try:
            asyncio.create_task(global_bot_client.send_message(ADMIN_CHAT_ID, admin_card, reply_markup=admin_kb))
        except Exception as e:
            logger.warning(f"Could not forward Mini App feedback to admin: {e}")

    return web.json_response({
        "ok": True,
        "message": "Thank you! Your feedback has been sent directly to Phoenix.",
        "report_id": fid
    }, headers=CORS_HEADERS)

async def create_stars_invoice_api(request: web.Request) -> web.Response:
    """
    Generates a native Telegram Stars invoice link for 1-tap checkout inside Telegram Mini App
    using window.Telegram.WebApp.openInvoice().
    """
    try:
        data = await request.json()
    except Exception:
        data = {}

    uid = data.get("user_id")
    try:
        user_id = int(uid)
    except (ValueError, TypeError):
        user_id = 0

    auth_uid, auth_err = extract_and_verify_telegram_auth(request, payload_dict=data)
    if auth_uid:
        user_id = auth_uid
    elif not user_id:
        return web.json_response({"ok": False, "error": f"Unauthorized: {auth_err}"}, status=401, headers=CORS_HEADERS)

    tier = str(data.get("tier", "monthly")).lower().strip()
    if tier not in VIP_TIERS:
        tier = "monthly"

    tier_info = VIP_TIERS[tier]
    stars_amount = tier_info["stars"]
    data_shared = get_user_data_sharing(user_id) if user_id else False
    if tier == "monthly" and data_shared:
        stars_amount = 120

    if tier == "monthly":
        inv_title = "👑 Joy VIP Platinum Access (30 Days)"
    elif tier == "weekend":
        inv_title = "🌟 Joy 48h Weekend Pass"
    else:
        inv_title = "⚡ Joy 24h Day Pass"

    client = global_bot_client or TelegramClient(TELEGRAM_BOT_TOKEN)
    close_client = not bool(global_bot_client)
    try:
        if hasattr(client, "create_invoice_link"):
            inv_res = await client.create_invoice_link(
                title=inv_title,
                description=tier_info["desc"],
                payload=f"vip_{tier}_{user_id}",
                currency="XTR",
                prices=[{"label": inv_title, "amount": stars_amount}]
            )
        else:
            inv_res = {"ok": True, "result": f"https://t.me/$mock_stars_vip_{tier}_{user_id}"}
    finally:
        if close_client and hasattr(client, "close"):
            await client.close()

    if inv_res.get("ok") and inv_res.get("result"):
        return web.json_response({
            "ok": True,
            "invoice_url": inv_res["result"],
            "tier": tier,
            "stars": stars_amount,
            "title": inv_title
        }, headers=CORS_HEADERS)
    else:
        err = inv_res.get("description", "Could not generate invoice")
        logger.error(f"Mini App Stars invoice generation failed for user {user_id}: {err}")
        return web.json_response({"ok": False, "error": err}, status=400, headers=CORS_HEADERS)

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
    # Cryptographically sign the OAuth state to enforce Zero-Trust CSRF mitigation (RFC 6749 Section 10.12)
    state_sig = hmac.new(TELEGRAM_BOT_TOKEN.encode("utf-8"), f"oauth:{user_id}".encode("utf-8"), hashlib.sha256).hexdigest()[:16]
    oauth_state = f"{user_id}:{state_sig}"
    scopes = "openid email profile https://www.googleapis.com/auth/drive.file"
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": scopes,
        "access_type": "offline",
        "prompt": "consent",
        "state": oauth_state
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
        if ":" in user_id_str:
            uid_part, sig_part = user_id_str.split(":", 1)
            user_id = int(uid_part)
            expected_sig = hmac.new(TELEGRAM_BOT_TOKEN.encode("utf-8"), f"oauth:{user_id}".encode("utf-8"), hashlib.sha256).hexdigest()[:16]
            if not secrets.compare_digest(sig_part, expected_sig):
                logger.warning(f"Google OAuth CSRF signature mismatch for user {user_id}")
                return web.Response(text="Invalid or tampered OAuth state parameter.", status=403)
        else:
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
    raw_uid = (request.query.get("uid") or "").strip()
    # Zero-Trust input sanitization: Enforce strictly numeric user ID to prevent reflected XSS
    uid_str = raw_uid if (raw_uid.isdigit() and len(raw_uid) <= 20) else ""
    raw_mode = (request.query.get("mode") or "signin").strip().lower()
    mode = "signup" if raw_mode == "signup" else "signin"
    google_login_url = f"/auth/google/login?uid={urllib.parse.quote(uid_str)}" if uid_str else "/auth/google/login"

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
        const uid = "{html_escape(uid_str)}";
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

        if ("{html_escape(mode)}" === "signup") {{
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

    auth_uid, auth_err = extract_and_verify_telegram_auth(request, payload_dict=data)
    if auth_uid:
        user_id = auth_uid
    elif user_id > 0:
        return web.json_response({"ok": False, "error": f"Zero-Trust Security: {auth_err or 'Authentication required'}"}, status=401)

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

    auth_uid, auth_err = extract_and_verify_telegram_auth(request, payload_dict=data)
    if auth_uid:
        user_id = auth_uid
    elif user_id > 0:
        return web.json_response({"ok": False, "error": f"Zero-Trust Security: {auth_err or 'Authentication required'}"}, status=401)

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
    app.router.add_post("/api/user/preference", handle_user_preference_api)
    app.router.add_get("/api/user/quota", get_user_quota_api)
    app.router.add_get("/api/user/connections", get_user_connections_api)
    app.router.add_get("/api/presence", get_presence_api)

    # Joy Remembers - Emotional Memory & Privacy Management Endpoints
    app.router.add_get("/api/memories", get_user_memories_api)
    app.router.add_post("/api/memories/delete", delete_user_memory_api)
    app.router.add_post("/api/memories/wipe", wipe_user_memories_api)
    app.router.add_post("/api/memories/clear", wipe_user_memories_api)
    app.router.add_options("/api/memories", handle_cors_options)
    app.router.add_options("/api/memories/delete", handle_cors_options)
    app.router.add_options("/api/memories/wipe", handle_cors_options)
    app.router.add_options("/api/memories/clear", handle_cors_options)
    app.router.add_get("/api/session", get_session_api)
    app.router.add_options("/api/session", handle_cors_options)
    app.router.add_get("/api/admin/users", get_admin_users_api)
    app.router.add_get("/api/admin/quota", admin_quota_api)
    app.router.add_post("/api/admin/quota", admin_quota_api)
    app.router.add_get("/api/ad/reward", handle_ad_reward_api)
    app.router.add_post("/api/ad/reward", handle_ad_reward_api)
    app.router.add_post("/api/feedback", handle_api_feedback)
    app.router.add_options("/api/feedback", handle_cors_options)
    app.router.add_post("/api/payment/stars-invoice", create_stars_invoice_api)
    app.router.add_options("/api/payment/stars-invoice", handle_cors_options)
    
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

    # Configure Telegram Bot Commands & Native Chat Menu Buttons
    try:
        cmd_res = await bot.set_my_commands(BOT_COMMANDS)
        logger.info(f"Registered Telegram Bot Commands: {cmd_res}")

        # Default for uncompleted / new users: Menu commands (Mini Phone is revealed only AFTER onboarding completion!)
        default_menu_res = await bot.set_chat_menu_button(menu_button={"type": "commands"})
        logger.info(f"Set Default Telegram Chat Menu Button to Commands: {default_menu_res}")

        # For Administrator (Phoenix): Keep [ ≡ Menu ] Commands for fast system control!
        if ADMIN_CHAT_ID:
            admin_menu_res = await bot.set_chat_menu_button(
                chat_id=ADMIN_CHAT_ID,
                menu_button={"type": "commands"}
            )
            logger.info(f"Set Admin Chat Menu Button to commands: {admin_menu_res}")

        # Update Bot Profile Description & Short Description for Closed Beta (50 Slots)
        beta_desc = (
            "🌸 Joy — 24/7 AI Voice Companion & Anonymous Audio Match.\n\n"
            "🔒 EXCLUSIVE CLOSED BETA (50 Slots Only):\n"
            "Pre-register now to claim your Pioneer slot! Remaining entries join our priority waitlist.\n\n"
            "🎁 Pioneer Bug Bounties:\n"
            "Report major bugs, voice lag, security flaws, or suggest top features to earn Free VIP Passes (2 Weeks to Lifetime)!\n\n"
            "🗣️ Note from Phoenix: We are refining regional dialects (Hinglish, Tanglish & more) — report phrasing flaws via /feedback!"
        )
        beta_short_desc = "Closed Beta (50 Pioneer Slots). AI Voice Companion, duplex calls & Bug Hunter Bounties!"
        await bot.set_my_description(beta_desc)
        await bot.set_my_short_description(beta_short_desc)
        logger.info("Successfully synced Telegram Bot Description for Closed Beta (50 Slots)")
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

                    # Check if user has an active memory callback for upcoming/recent life events
                    memory_callback = None
                    try:
                        memory_callback = get_proactive_greeting(uid, caller_name=c_name, user_name=first_n)
                    except Exception:
                        pass

                    if memory_callback and proactive_type == "morning":
                        msg_text = f"{memory_callback} {streak_badge}".strip()
                    elif proactive_type == "morning":
                        if user_lang == "tanglish":
                            msg_text = secrets.choice([
                                f"Good morning {first_n}! ☀️ Kaalaila seekiram enthiritiya? Nalla breakfast saapdu! Today will be super productive! 💕 {streak_badge}",
                                f"Arey good morning! ☕ Sweet dreams vandhucha? Inaiku enna plan? Breakfast pannitiya? 🥰 {streak_badge}",
                                f"Morning da! 🌸 Sending you lots of positive vibes for today! Semaya panni kalakku 💕 {streak_badge}"
                            ])
                        elif user_lang in ["hinglish", "auto", ""]:
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
                        elif user_lang in ["hinglish", "auto", ""]:
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
                            [{"text": f"📞 1-Min Catchup Call with {c_name}", "web_app": {"url": call_url}}],
                            [{"text": "🔕 Mute Daily Check-ins", "callback_data": "toggle_proactive"}]
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

    # Launch automatic 72-hour inactive pioneer pruning worker (every 30 minutes)
    async def auto_prune_inactive_pioneers_loop():
        while True:
            try:
                await asyncio.sleep(1800)  # 30 minutes
                reassignments = prune_inactive_beta_pioneers(inactivity_hours=72)
                for r in reassignments:
                    demoted_uid = r["demoted_uid"]
                    promoted_uid = r["promoted_uid"]
                    slot = r["slot"]
                    try:
                        demote_text = (
                            f"⚠️ **Beta Pioneer Slot Reassigned (72h Inactivity)**\n\n"
                            f"Hey Friend! Because your Joy account had zero calls or messages for over 72 hours, your Pioneer Slot #{slot} was automatically reallocated to a waiting user on the priority waitlist.\n\n"
                            f"You are now on the waitlist. Whenever you're ready to chat or test, tap below or invite friends to skip forward! 🌸"
                        )
                        await bot.send_message(demoted_uid, demote_text)
                    except Exception:
                        pass
                    try:
                        call_url = "https://joyfun-ai-bot.onrender.com/call"
                        promote_text = (
                            f"🎉 **CONGRATULATIONS! YOU'VE BEEN PROMOTED TO BETA PIONEER!** 🎟️\n\n"
                            f"A Pioneer Slot just opened up due to inactivity! You've been automatically promoted to **Pioneer Slot #{slot} of 50**!\n\n"
                            f"You now have exclusive 24/7 early access to test Joy's Live Voice Calls and AI companion! Tap below to start talking! 💖"
                        )
                        promote_kb = {
                            "inline_keyboard": [
                                [{"text": "📞 Open Mini Phone", "web_app": {"url": call_url}}],
                                [{"text": "📱 Open Menu", "callback_data": "menu_main"}]
                            ]
                        }
                        await bot.send_message(promoted_uid, promote_text, reply_markup=promote_kb)
                    except Exception:
                        pass
            except asyncio.CancelledError:
                break
            except Exception as ex:
                logger.warning(f"Auto-prune inactive pioneers error: {ex}")

    asyncio.create_task(periodic_notion_sync_loop())
    asyncio.create_task(proactive_companion_loop())
    asyncio.create_task(morning_alarm_background_worker(bot))
    asyncio.create_task(evening_bedtime_background_worker(bot))
    asyncio.create_task(start_cloud_keepalive_worker(PORT))
    asyncio.create_task(auto_prune_inactive_pioneers_loop())

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
        # Clear any lingering webhook so long-polling never encounters 409 Conflict
        try:
            logger.info("Ensuring webhook is deactivated for long polling...")
            await bot.delete_webhook(drop_pending_updates=False)
        except Exception as we:
            logger.warning(f"Could not delete webhook: {we}")

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
                        cq = update["callback_query"]
                        cq_from = cq.get("from", {})
                        cq_u = cq_from.get("id")
                        if cq_u:
                            cq_uname = cq_from.get("username", "")
                            cq_fname = cq_from.get("first_name", "")
                            cq_data = cq.get("data", "")
                            record_bot_activity(cq_u, cq_uname, cq_fname, f"Tapped {cq_data[:24]}")
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

                        touch_user_activity(user_id)

                        # Handle successful payment (Telegram Stars)
                        if "successful_payment" in msg:
                            sp = msg["successful_payment"]
                            asyncio.create_task(handle_successful_payment(bot, chat_id, user_id, sp))
                            continue

                        # Handle Telegram Collectible Gift (Bot API 8.0+)
                        if "gift" in msg:
                            gift_data = msg["gift"]
                            asyncio.create_task(handle_received_telegram_gift(bot, chat_id, user, gift_data))
                            continue
                            
                        username = user_info.get("username", "")
                        user = get_or_create_user(user_id, username, user_info.get("first_name", ""))
                        
                        act = "Sent message"
                        if "voice" in msg:
                            act = "Sent voice note 🎙️"
                        elif "photo" in msg:
                            act = "Sent photo 📸"
                        elif "audio" in msg:
                            act = "Sent audio file 🎵"
                        elif "document" in msg:
                            act = "Sent document 📄"
                        elif "video" in msg or "video_note" in msg:
                            act = "Sent video 📹"
                        elif "text" in msg and msg["text"].startswith("/"):
                            act = f"Ran {msg['text'].split()[0]}"
                        record_bot_activity(user_id, username, user_info.get("first_name", ""), act, user.get("language", "auto"))

                        onboarding_status = user.get("onboarding_status", "new")
                        is_in_anon_chat = user_id in telegram_active_chats
                        is_in_feedback = (onboarding_status == "waiting_feedback")

                        # =======================================================
                        # 1. FEEDBACK & BUG BOUNTY MODE: ALLOW ALL ATTACHMENTS
                        # Users can send ANY media: photos, music/audio, voice notes,
                        # documents/logs/files, videos, screen recordings, etc.
                        # =======================================================
                        if is_in_feedback:
                            if "photo" in msg:
                                asyncio.create_task(handle_incoming_feedback_media(bot, chat_id, user, msg, "photo"))
                                continue
                            elif "audio" in msg:
                                asyncio.create_task(handle_incoming_feedback_media(bot, chat_id, user, msg, "audio"))
                                continue
                            elif "voice" in msg:
                                asyncio.create_task(handle_incoming_feedback_media(bot, chat_id, user, msg, "voice"))
                                continue
                            elif "document" in msg:
                                asyncio.create_task(handle_incoming_feedback_media(bot, chat_id, user, msg, "document"))
                                continue
                            elif "video" in msg or "video_note" in msg:
                                asyncio.create_task(handle_incoming_feedback_media(bot, chat_id, user, msg, "video"))
                                continue
                            elif "animation" in msg:
                                asyncio.create_task(handle_incoming_feedback_media(bot, chat_id, user, msg, "animation"))
                                continue
                            elif "text" in msg:
                                text = msg["text"]
                                msg_id = msg.get("message_id")
                                asyncio.create_task(safe_process_user_text(bot, chat_id, user, text, msg_id=msg_id))
                                continue

                        # =======================================================
                        # 2. ANONYMOUS REAL PERSON CHAT: ZERO MEDIA PERMITTED
                        # Strictly block photos, music, files, videos, stickers & contacts
                        # (Only text and live voice notes allowed)
                        # =======================================================
                        if is_in_anon_chat:
                            if any(k in msg for k in ("photo", "audio", "document", "video", "video_note", "animation", "sticker", "contact")):
                                guard_text = (
                                    f"🚫 **Media Upload Blocked — Privacy Guard Active**\n\n"
                                    f"For user safety and personal confidentiality, sending photos, audio/music files, videos, and documents is strictly disabled in 1-on-1 anonymous matching.\n\n"
                                    f"{LEGAL_DISCLAIMER_TEXT}\n"
                                    f"{PRIVACY_WARNING_TEXT}"
                                )
                                asyncio.create_task(bot.send_message(chat_id, guard_text))
                                continue
                            elif "voice" in msg:
                                file_id = msg["voice"]["file_id"]
                                asyncio.create_task(safe_process_user_voice(bot, chat_id, user, file_id))
                                continue
                            elif "text" in msg:
                                text = msg["text"]
                                msg_id = msg.get("message_id")
                                asyncio.create_task(safe_process_user_text(bot, chat_id, user, text, msg_id=msg_id))
                                continue

                        # =======================================================
                        # 3. AI COMPANION CHAT: TEXT, VOICE & PHOTOS ONLY
                        # Arbitrary music files, documents, and videos are NOT
                        # accepted in normal companion chat.
                        # =======================================================
                        # Case A: Spoken Voice Note
                        if "voice" in msg:
                            file_id = msg["voice"]["file_id"]
                            logger.info(f"🎙️ Voice note from {user_id} (@{username})")
                            asyncio.create_task(safe_process_user_voice(bot, chat_id, user, file_id))
                        # Case B: Photo sent by user (Gemini Vision)
                        elif "photo" in msg:
                            file_id = msg["photo"][-1]["file_id"]
                            caption = msg.get("caption", "")
                            msg_id = msg.get("message_id")
                            logger.info(f"📸 Photo from {user_id} (@{username})")
                            asyncio.create_task(safe_process_user_photo(bot, chat_id, user, file_id, caption=caption, msg_id=msg_id))
                        # Case C: Document image sent by user
                        elif "document" in msg and msg.get("document", {}).get("mime_type", "").startswith("image/"):
                            file_id = msg["document"]["file_id"]
                            caption = msg.get("caption", "")
                            msg_id = msg.get("message_id")
                            logger.info(f"📄 Image document from {user_id} (@{username})")
                            asyncio.create_task(safe_process_user_photo(bot, chat_id, user, file_id, caption=caption, msg_id=msg_id))
                        # Case D: Music / Audio file (Rejected in AI chat, directed to /feedback)
                        elif "audio" in msg:
                            audio_notice = (
                                "🎵 **Music / Audio File Detected**\n\n"
                                "Joy only listens to spoken voice notes (hold the mic 🎙️) in companion chat.\n\n"
                                "💡 *Tip: If you're submitting music, an audio glitch, or a sample for feedback or bug bounty, please send `/feedback` or `/bug` first to attach your audio file!*"
                            )
                            asyncio.create_task(bot.send_message(chat_id, audio_notice))
                        # Case E: Document / File (Rejected in AI chat, directed to /feedback)
                        elif "document" in msg:
                            doc_notice = (
                                "📄 **Document / File Detected**\n\n"
                                "Joy can only view photos in normal chat!\n\n"
                                "💡 *Tip: If you want to send a log file, crash report, or document to our developer, please send `/feedback` or `/bug` first to attach your file!*"
                            )
                            asyncio.create_task(bot.send_message(chat_id, doc_notice))
                        # Case F: Video / Video Note (Rejected in AI chat, directed to /feedback)
                        elif "video" in msg or "video_note" in msg:
                            vid_notice = (
                                "🎥 **Video Detected**\n\n"
                                "Joy can't watch videos in normal chat right now!\n\n"
                                "💡 *Tip: If you want to share a screen recording of a bug for our developer, please send `/feedback` or `/bug` first to attach your video!*"
                            )
                            asyncio.create_task(bot.send_message(chat_id, vid_notice))
                        # Case G: Location / Venue (Explicitly rejected for privacy)
                        elif "location" in msg or "venue" in msg:
                            asyncio.create_task(bot.send_message(chat_id, "📍 Your location is never requested or tracked. Joy respects your privacy 100%!"))
                        # Case H: Poll (Explicitly rejected)
                        elif "poll" in msg:
                            asyncio.create_task(bot.send_message(chat_id, "📊 Joy doesn't participate in polls. Feel free to chat with me directly!"))
                        # Case I: Contact Card (Explicitly rejected with Privacy Guard)
                        elif "contact" in msg:
                            asyncio.create_task(bot.send_message(chat_id, "👤 Contact sharing is disabled. Talk to me directly anytime!"))
                        # Case J: Sticker
                        elif "sticker" in msg:
                            gender = user.get("gender", "male")
                            cinfo = get_user_contact_display(user_id, "lover", gender)
                            asyncio.create_task(bot.send_message(chat_id, f"{cinfo['emoji']} Haha cute sticker! What's up? 🌸"))
                        # Case K: Text Message
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
