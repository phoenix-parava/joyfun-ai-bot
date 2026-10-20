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
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from datetime import datetime, timezone
from aiohttp import web

from config import (
    TELEGRAM_BOT_TOKEN,
    GEMINI_API_KEY,
    OWNER_ID,
    PORT,
    DAILY_FREE_VOICE_LIMIT,
    DAILY_FREE_TEXT_LIMIT,
    VIP_PRICE_INR
)
from database import (
    init_db,
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
    get_user_daily_usage
)
from contacts import (
    CONTACTS_CATALOG,
    get_contacts_for_gender,
    get_contact_info,
    get_contact_prompt
)
from ai_engine import generate_text_reply, generate_voice_reply, get_human_boundary_reply
from voice_engine import synthesize_speech
from telegram_client import TelegramClient
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
    {"command": "call", "description": "📞 Start Live Voice Call"},
    {"command": "contacts", "description": "📇 Switch Contact (Besties, Lover, Crush, Teacher)"},
    {"command": "gender", "description": "👤 Switch Boy / Girl Point of View"},
    {"command": "menu", "description": "📱 Open Interactive Menu"},
    {"command": "keyboard", "description": "⌨️ Show Menu Beside Emoji Button"},
    {"command": "import", "description": "📥 Import Memory from Previous AI"},
    {"command": "settings", "description": "⚙️ Account, Language & Preferences"},
    {"command": "recharge", "description": "🎬 Free Talk Time & Voice Recharge"},
    {"command": "vip", "description": "⭐ Joy VIP Pass (Unlimited Calls)"},
    {"command": "stats", "description": "📊 View My Daily Usage & Balance"},
    {"command": "clean", "description": "🧹 Hide Bottom Buttons (Clean Chat)"},
    {"command": "reset", "description": "🧹 Clear Conversation Memory"}
]

def get_persistent_reply_keyboard(gender: str = "male", active_contact: str = "lover") -> dict:
    """Returns a docked, compact keyboard at the bottom of the chat for fast access beside emoji button."""
    cinfo = get_contact_info(active_contact, gender)
    c_name = cinfo.get("name", "Joy")
    return {
        "keyboard": [
            [{"text": f"📞 Call {c_name}"}, {"text": "📇 Contacts"}],
            [{"text": "⚙️ Settings"}, {"text": "🎬 Recharge"}],
            [{"text": "⭐ Joy VIP"}, {"text": "📱 Menu"}]
        ],
        "resize_keyboard": True,
        "is_persistent": True
    }


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
    "auto": "🌐 Auto-Match",
    "tanglish": "🌴 Tanglish",
    "hinglish": "🇮🇳 Hinglish",
    "english": "🇬🇧 English"
}

def get_main_keyboard(gender: str = "male", active_contact: str = "lover", user_id: Optional[int] = None) -> dict:
    contact = get_contact_info(active_contact, gender)
    c_name = contact.get("name", "Joy")
    c_tag = contact.get("tag", "Girlfriend" if gender == "male" else "Boyfriend")
    c_emoji = contact.get("emoji", "💖")
    user_lang = get_user_language(user_id) if user_id else "auto"
    
    call_url = f"https://joyfun-ai-bot.onrender.com/call?gender={gender}&contact={active_contact}&lang={user_lang}"
    if user_id:
        call_url += f"&uid={user_id}"
    
    gender_label = "👦 Boy's View" if gender == "male" else "👧 Girl's View"
    
    return {
        "inline_keyboard": [
            [
                {"text": f"📞 Call {c_name} ({c_emoji} {c_tag})", "web_app": {"url": call_url}}
            ],
            [
                {"text": f"📇 Contacts ({c_emoji} {c_name})", "callback_data": "menu_contacts"},
                {"text": "⚙️ Settings & Data", "callback_data": "menu_settings"}
            ],
            [
                {"text": f"👤 {gender_label}", "callback_data": "menu_toggle_gender"},
                {"text": "🎬 Free Recharge", "callback_data": "ad_watch"}
            ],
            [
                {"text": "⭐ Joy VIP Pass", "callback_data": "menu_vip"},
                {"text": "📥 Import Memory", "callback_data": "onboard_import"}
            ],
            [
                {"text": "❌ Close / Vanish Menu", "callback_data": "menu_close"}
            ]
        ]
    }

def get_contacts_keyboard(gender: str = "male", active_contact: str = "lover") -> dict:
    contacts = get_contacts_for_gender(gender)
    buttons = []
    
    for cid, cinfo in contacts.items():
        is_active = (cid == active_contact)
        mark = "✓ " if is_active else ""
        btn_text = f"{mark}{cinfo['emoji']} {cinfo['name']} ({cinfo['tag']})"
        buttons.append([{"text": btn_text, "callback_data": f"contact_sel_{cid}"}])
    
    other_gender = "female" if gender == "male" else "male"
    switch_label = "🔄 Switch to Girl's View" if gender == "male" else "🔄 Switch to Boy's View"
    
    buttons.append([{"text": switch_label, "callback_data": f"set_gender_{other_gender}"}])
    buttons.append([{"text": "⬅️ Back", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}])
    
    return {"inline_keyboard": buttons}

async def handle_contacts(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    gender = user.get("gender", "male")
    active_contact = user.get("active_contact", "lover")
    cinfo = get_contact_info(active_contact, gender)
    view_title = "Boy's Point of View" if gender == "male" else "Girl's Point of View"
    text = (
        f"📇 **Your Contacts ({view_title})**\n\n"
        f"Currently talking to: **{cinfo['emoji']} {cinfo['name']}** ({cinfo['role_title']})\n"
        f"*{cinfo['description']}*\n\n"
        f"👇 Tap any contact below to switch who you chat and call with:"
    )
    keyboard = get_contacts_keyboard(gender, active_contact)
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_menu(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    gender = user.get("gender", "male")
    active_contact = user.get("active_contact", "lover")
    keyboard = get_main_keyboard(gender, active_contact, user.get("user_id"))
    cinfo = get_contact_info(active_contact, gender)
    text = (
        f"📱 **Joy Control Menu**\n\n"
        f"Active Contact: **{cinfo['emoji']} {cinfo['name']}** ({cinfo['tag']})\n"
        f"Point of View: **{'👦 Boy' if gender == 'male' else '👧 Girl'}**\n\n"
        f"Tap **Close / Vanish Menu** below anytime to dismiss this card."
    )
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_settings(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    user_id = user["user_id"]
    first_name = user.get("first_name", "Friend")
    gender = user.get("gender", "male")
    active_contact = user.get("active_contact", "lover")
    user_lang = get_user_language(user_id)
    cinfo = get_contact_info(active_contact, gender)
    vip_active, expiry_formatted, days_left = is_user_vip(user_id)
    voice_used, text_used = get_user_daily_usage(user_id)
    _, user_memory = get_user_imported_memory(user_id)
    if not user_memory:
        try:
            _, user_memory = restore_user_memory_from_notion(user_id)
        except Exception:
            pass

    gender_label = "👦 Boy's View" if gender == "male" else "👧 Girl's View"
    lang_label = LANGUAGE_NAMES.get(user_lang, "🌐 Auto-Match")

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

    card_text = (
        f"⚙️ **Joy Account & Settings Hub**\n\n"
        f"👤 **User Data:**\n"
        f"• **Name:** {first_name}\n"
        f"• **User ID:** `{user_id}`\n"
        f"• **Perspective:** **{gender_label}**\n"
        f"• **Active Contact:** {cinfo['emoji']} **{cinfo['name']}** ({cinfo['tag']})\n"
        f"• **Preferred Language:** **{lang_label}**\n"
        f"• **VIP Status:** {vip_str}\n"
        f"• **Today's Balance:** {usage_str}\n"
        f"• **Imported Memory:** {mem_str}\n\n"
        f"👇 *Customize settings, change language, switch perspective, recharge, or call right now:*"
    )

    call_url = f"https://joyfun-ai-bot.onrender.com/call?gender={gender}&contact={active_contact}&lang={user_lang}&uid={user_id}"

    keyboard = {
        "inline_keyboard": [
            [
                {"text": f"📞 Call {cinfo['name']} Now ({cinfo['emoji']} {cinfo['tag']})", "web_app": {"url": call_url}}
            ],
            [
                {"text": f"🌐 Language: {lang_label}", "callback_data": "menu_language"},
                {"text": f"👤 View: {gender_label}", "callback_data": "menu_toggle_gender"}
            ],
            [
                {"text": f"📇 Switch Contact ({cinfo['name']})", "callback_data": "menu_contacts"},
                {"text": "🎬 Free Recharge (+5)", "callback_data": "ad_watch"}
            ],
            [
                {"text": "⭐ Joy VIP Pass", "callback_data": "menu_vip"},
                {"text": "📥 Import Memories", "callback_data": "onboard_import"}
            ],
            [
                {"text": "🧹 Reset Chat Memory", "callback_data": "menu_reset_confirm"}
            ],
            [
                {"text": "⬅️ Main Menu", "callback_data": "menu_main"},
                {"text": "❌ Close / Vanish Menu", "callback_data": "menu_close"}
            ]
        ]
    }
    await send_or_edit_menu(bot, chat_id, card_text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def handle_language_menu(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    user_id = user["user_id"]
    current_lang = get_user_language(user_id)
    
    text = (
        "🌐 **Select Conversation Language**\n\n"
        "Choose how you want your companion circle to chat and talk with you in live calls and voice notes:\n\n"
        "• **🌐 Auto-Match:** Automatically detects and replies in your language\n"
        "• **🌴 Tanglish:** Friendly Tamil + English in English letters (*'machi', 'sapdiya', 'seri', 'rombha'*)\n"
        "• **🇮🇳 Hinglish:** Casual Hindi + English in English letters (*'bhai', 'yaar', 'kya scene', 'khana khaya'*)\n"
        "• **🇬🇧 English:** Natural, everyday conversational English\n\n"
        f"Current Setting: **{LANGUAGE_NAMES.get(current_lang, '🌐 Auto-Match')}**\n\n"
        "👇 Tap your preferred language below:"
    )
    
    def mark(val):
        return "✓ " if current_lang == val else ""
        
    keyboard = {
        "inline_keyboard": [
            [{"text": f"{mark('auto')}🌐 Auto-Match (Recommended)", "callback_data": "set_lang_auto"}],
            [{"text": f"{mark('tanglish')}🌴 Tanglish (Tamil + English)", "callback_data": "set_lang_tanglish"}],
            [{"text": f"{mark('hinglish')}🇮🇳 Hinglish (Hindi + English)", "callback_data": "set_lang_hinglish"}],
            [{"text": f"{mark('english')}🇬🇧 English (Everyday English)", "callback_data": "set_lang_english"}],
            [{"text": "⬅️ Back to Settings", "callback_data": "menu_settings"}, {"text": "❌ Close", "callback_data": "menu_close"}]
        ]
    }
    await send_or_edit_menu(bot, chat_id, text, keyboard, message_id=message_id, user_msg_id=user_msg_id)

async def send_onboarding_welcome(bot: TelegramClient, chat_id: int, user: dict, user_msg_id: Optional[int] = None):
    first_name = user.get("first_name", "Friend")
    text = (
        f"Hey {first_name}! 💖 Welcome to **Joy**!\n\n"
        f"Your private, real-time AI circle for phone calls, voice notes, and late-night chats.\n\n"
        f"To set up your personalized circle of contacts and point of view:\n"
        f"👉 **Are you a Boy or a Girl?**"
    )
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "👦 I am a Boy", "callback_data": "onboard_gender_male"},
                {"text": "👧 I am a Girl", "callback_data": "onboard_gender_female"}
            ],
            [
                {"text": "📥 Import Memory from Old AI", "callback_data": "onboard_import"}
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
    contact = get_contact_info(active_contact, gender)
    c_name = contact.get("name", "Joy")
    c_role = contact.get("tag", "Friend")
    c_emoji = contact.get("emoji", "💖")

    welcome_text = (
        f"Hey {first_name}! {c_emoji} **{c_name}** ({c_role}) is right here with you.\n\n"
        f"We can chat and talk on calls in **Tanglish**, **Hinglish**, or **English** naturally! ✨\n\n"
        f"📞 **Live Voice Call:** Tap **Call {c_name} Now** below for a private, hands-free call!\n"
        f"📇 **Switch Contact:** Tap **Contacts** to switch between besties, lover, crush, and teacher.\n\n"
        f"Ready to talk? Tap below to start your call! 👇"
    )
    keyboard = get_main_keyboard(gender, active_contact, user.get("user_id"))
    await send_or_edit_menu(bot, chat_id, welcome_text, keyboard, user_msg_id=user_msg_id)

async def handle_vip(bot: TelegramClient, chat_id: int, user: dict, message_id: Optional[int] = None, user_msg_id: Optional[int] = None):
    user_id = user["user_id"]
    vip_active, expiry_formatted, days_left = is_user_vip(user_id)
    gender = user.get("gender", "male")
    active_contact = user.get("active_contact", "lover")
    contact = get_contact_info(active_contact, gender)
    
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
        call_url = f"https://joyfun-ai-bot.onrender.com/call?gender={gender}&contact={active_contact}&uid={user_id}"
        keyboard = {
            "inline_keyboard": [
                [{"text": f"📞 Call {contact['name']} Now (Live Audio)", "web_app": {"url": call_url}}],
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
            f"2. Contact owner **@phoenix_parava_0** with your User ID (`{user_id}`) for instant VIP activation!\n\n"
            f"🎬 *Tip: You can also tap 'Watch Ad to Recharge' below to get free talk time without paying!*"
        )
        keyboard = {
            "inline_keyboard": [
                [{"text": "🎬 Watch Ad for Free (+5 Notes)", "callback_data": "ad_watch"}],
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
            f"🎬 Tap **Free Recharge** below to get +5 Free Notes anytime!\n"
            f"⭐ Or tap **Joy VIP Pass** to unlock unlimited conversations."
        )
    keyboard = {
        "inline_keyboard": [
            [{"text": "🎬 Free Recharge (+5 Notes)", "callback_data": "ad_watch"}, {"text": "⭐ Joy VIP Pass", "callback_data": "menu_vip"}],
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
            f"🎉 **Awesome! Your Boy's Circle is ready!** 👦\n\n"
            f"Your companion is **{cinfo['emoji']} {cinfo['name']}** ({cinfo['role_title']}).\n"
            f"In your contacts you have **2 Boy Besties**, **1 Girl Bestie**, **Lover**, **Crush**, and an **English Teacher**!\n\n"
            f"📞 Tap **Call {cinfo['name']}** below to start your first live voice call, or tap **Contacts** to switch! 👇"
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
        await bot.answer_callback_query(cq_id, "👧 Girl's Circle activated!")
        cinfo = get_contact_info("lover", "female")
        welcome_msg = (
            f"🎉 **Awesome! Your Girl's Circle is ready!** 👧\n\n"
            f"Your companion is **{cinfo['emoji']} {cinfo['name']}** ({cinfo['role_title']}).\n"
            f"In your contacts you have **2 Girl Besties**, **1 Boy Bestie**, **Lover**, **Crush**, and a **Maths Teacher (Male)**!\n\n"
            f"📞 Tap **Call {cinfo['name']}** below to start your first live voice call, or tap **Contacts** to switch! 👇"
        )
        keyboard = get_main_keyboard("female", "lover", user_id)
        await send_or_edit_menu(bot, chat_id, welcome_msg, keyboard, message_id=message_id)

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
        await handle_contacts(bot, chat_id, user, message_id=message_id)

    elif data.startswith("contact_sel_"):
        cid = data.replace("contact_sel_", "")
        gender = user.get("gender", "male")
        cinfo = get_contact_info(cid, gender)
        set_user_active_contact(user_id, cid)
        update_user_preference(user_id, "voice", cinfo.get("voice", "female"))
        user["active_contact"] = cid
        user["voice"] = cinfo.get("voice", "female")
        await bot.answer_callback_query(cq_id, f"Switched to {cinfo['name']} ({cinfo['tag']})!")

        intro_text = (
            f"{cinfo['emoji']} **{cinfo['name']} ({cinfo['role_title']}):**\n\n"
            f"\"{cinfo.get('greeting', 'Hey! Ready to talk?')}\"\n\n"
            f"📞 Tap **Call {cinfo['name']} Now** below to jump on a live voice call, or send a voice note/text anytime! 👇"
        )
        keyboard = get_main_keyboard(gender, cid, user_id)
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
            f"📞 Tap **Call {cinfo['name']} Now** below to start our first live voice call, or send me a voice note anytime! 👇"
        )
        keyboard = get_main_keyboard(gender, active_contact, user_id)
        await send_or_edit_menu(bot, chat_id, welcome_fresh, keyboard, message_id=message_id)

    elif data == "menu_main":
        await bot.answer_callback_query(cq_id)
        await handle_menu(bot, chat_id, user, message_id=message_id)

    elif data == "menu_settings":
        await bot.answer_callback_query(cq_id)
        await handle_settings(bot, chat_id, user, message_id=message_id)

    elif data == "menu_language":
        await bot.answer_callback_query(cq_id)
        await handle_language_menu(bot, chat_id, user, message_id=message_id)

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
        await bot.answer_callback_query(cq_id, "🎬 Loading sponsor...")
        ad_text = (
            "📺 **Sponsor Spotlight & Free Recharge**\n\n"
            "✨ *Support Joy by checking out our sponsor! Sponsors make free AI voice companion conversations possible for everyone.*\n\n"
            "🚀 **Today's Featured Sponsor:** Google DeepMind & Antigravity Cloud\n"
            "💡 *Next-generation agentic AI and multi-modal intelligence for developers & learners worldwide.*\n\n"
            "🎁 **Reward:** **+5 Free Voice Notes** and **+20 Text Messages**!\n\n"
            "Tap below to claim your free recharge:"
        )
        keyboard = {
            "inline_keyboard": [
                [{"text": "✅ Claim +5 Free Notes & Call Time", "callback_data": "ad_claim"}],
                [{"text": "⬅️ Back", "callback_data": "menu_main"}, {"text": "❌ Close", "callback_data": "menu_close"}]
            ]
        }
        await send_or_edit_menu(bot, chat_id, ad_text, keyboard, message_id=message_id)

    elif data == "ad_claim":
        recharge_user_usage(user_id, bonus_voice=5, bonus_text=20)
        await bot.answer_callback_query(cq_id, "🎉 Recharged! +5 Voice Notes added.")
        gender = user.get("gender", "male")
        active_contact = user.get("active_contact", "lover")
        cinfo = get_contact_info(active_contact, gender)
        success_text = (
            "🎉 **Account Recharged Successfully!**\n\n"
            f"Added **+5 Voice Notes** and **+20 Text Messages** to your balance for today! 🥰\n\n"
            f"📞 Tap **Call {cinfo['name']}** below or send a voice note to keep chatting right away!"
        )
        keyboard = get_main_keyboard(gender, active_contact, user_id)
        await send_or_edit_menu(bot, chat_id, success_text, keyboard, message_id=message_id)

async def process_user_voice(bot: TelegramClient, chat_id: int, user: dict, file_id: str):
    user_id = user["user_id"]
    await dismiss_active_menu(bot, chat_id)
    
    # 1. Check daily limit
    allowed, used, limit = check_and_increment_usage(user_id, "voice")
    if not allowed:
        limit_msg = (
            f"Aww, your free daily voice notes ({limit}/{limit}) are finished for today! 🥰\n\n"
            f"Don't worry, you don't have to stop chatting! You can recharge right now:\n\n"
            f"🎬 **Watch a quick sponsor ad** to claim **+5 Free Voice Notes** instantly!\n"
            f"⭐ Or unlock the **Joy VIP Pass** for unlimited 24/7 calls."
        )
        keyboard = {
            "inline_keyboard": [
                [{"text": "🎬 Watch Ad to Recharge (+5 Notes)", "callback_data": "ad_watch"}],
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
    try:
        transcript, reply_text = generate_voice_reply(
            voice_bytes,
            mime_type="audio/ogg",
            mode=active_contact,
            gender=gender,
            language=user_lang,
            history=history,
            user_memory=user_memory
        )
    except Exception as e:
        logger.error(f"Error in Gemini audio generation: {e}")
        reply_text = "I heard you! But I had a slight hiccup thinking of a reply. Could you say that again?"
        transcript = "Voice Note"

    if not reply_text:
        reply_text = "Hey, I couldn't quite hear what you said! Could you send that once more?"
        transcript = "Voice Note"

    # Save to history
    add_conversation_turn(user_id, "user", transcript)
    add_conversation_turn(user_id, "model", reply_text)
    
    # 5. Synthesize voice with Edge-TTS
    await bot.send_chat_action(chat_id, "upload_voice")
    try:
        reply_kb = get_persistent_reply_keyboard(gender, active_contact)
        audio_output = await synthesize_speech(reply_text, voice_key=voice_choice)
        caption = f"🎙️ *{cinfo['name']}:* {reply_text}"
        await bot.send_audio(chat_id, audio_output, filename=f"{cinfo['name'].lower()}_reply.mp3", caption=caption, performer=cinfo['name'], title="Voice Note", reply_markup=reply_kb)
    except Exception as e:
        logger.error(f"Error in Edge-TTS synthesis: {e}")
        # Fallback to text message if TTS encounters an issue
        reply_kb = get_persistent_reply_keyboard(gender, active_contact)
        await bot.send_message(chat_id, reply_text, reply_markup=reply_kb)

async def process_user_text(bot: TelegramClient, chat_id: int, user: dict, text: str, msg_id: Optional[int] = None):
    user_id = user["user_id"]
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
    
    # Check commands & persistent keyboard button presses
    if clean_text.startswith("/start"):
        await handle_start(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/import") or clean_text.startswith("/transfer"):
        await send_memory_import_guide(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/contacts") or clean_text.startswith("/contact") or clean_text.lower() in ["contacts", "contact", "📇 contacts", "switch contact", "switch", "circle"]:
        await handle_contacts(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/gender") or clean_text.lower() in ["gender", "switch gender", "boy", "girl", "view", "👤 gender"]:
        curr_g = user.get("gender", "male")
        new_g = "female" if curr_g == "male" else "male"
        set_user_gender(user_id, new_g)
        set_user_active_contact(user_id, "lover")
        user["gender"] = new_g
        user["active_contact"] = "lover"
        await handle_contacts(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/menu") or clean_text.lower() in ["menu", "📱 menu", "📱 control menu", "control menu", "control", "home"]:
        await handle_menu(bot, chat_id, user, user_msg_id=msg_id)
        return
    elif clean_text.startswith("/keyboard") or clean_text.startswith("/buttons") or clean_text.startswith("/showbuttons") or clean_text.lower() in ["keyboard", "buttons", "show buttons"]:
        gender = user.get("gender", "male")
        active_contact = user.get("active_contact", "lover")
        reply_kb = get_persistent_reply_keyboard(gender, active_contact)
        await bot.send_message(
            chat_id,
            "📱 **Quick Menu Activated!** Tap the 4-squares grid icon beside the emoji button anytime to open it.",
            reply_markup=reply_kb
        )
        return
    elif clean_text.startswith("/settings") or clean_text.lower() in ["settings", "setting", "setup", "preferences", "config", "account", "profile", "⚙️ settings", "⚙️ settings & data"]:
        await handle_settings(bot, chat_id, user, user_msg_id=msg_id)
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
        await handle_contacts(bot, chat_id, user, user_msg_id=msg_id)
        return

    elif clean_text.startswith("/call") or clean_text.startswith("📞 Call") or clean_text.lower() in ["call", "call joy", "call now", "phone call", "talk", "live call"] or any(kw in lower_text for kw in ["can i call", "call you", "call u", "how to call", "phone call"]):
        user_gender = user.get("gender", "male")
        active_contact = user.get("active_contact", "lover")
        cinfo = get_contact_info(active_contact, user_gender)
        user_id_val = user.get("user_id", "")
        call_url = f"https://joyfun-ai-bot.onrender.com/call?gender={user_gender}&contact={active_contact}&uid={user_id_val}"
        call_keyboard = {
            "inline_keyboard": [
                [
                    {"text": f"📞 Call {cinfo['name']} ({cinfo['emoji']} {cinfo['tag']})", "web_app": {"url": call_url}}
                ],
                [
                    {"text": "📇 Switch Contact", "callback_data": "menu_contacts"},
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
        keyboard = {
            "inline_keyboard": [
                [{"text": "🎬 Watch Ad Now (+5 Notes)", "callback_data": "ad_watch"}],
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
                    f"📞 Tap **Call Joy** anytime to start an instant hands-free call!"
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

    elif clean_text.startswith("/reset") or clean_text.lower() in ["reset", "clear", "clear memory", "restart", "refresh", "🧹 reset"]:

        # Reset conversation memory
        with bot.get_session():
            from database import get_connection
            with get_connection() as conn:
                conn.cursor().execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
                conn.commit()
        gender = user.get("gender", "male")
        active_contact = user.get("active_contact", "lover")
        reply_kb = get_persistent_reply_keyboard(gender, active_contact)
        await bot.send_message(chat_id, "🧹 Conversation memory refreshed! Let's start fresh. What's up?", reply_markup=reply_kb)
        return

    # Dismiss any lingering menu card so chat remains 100% human and clean
    await dismiss_active_menu(bot, chat_id)

    # Check text usage limit
    allowed, used, limit = check_and_increment_usage(user_id, "text")
    if not allowed:
        limit_msg = (
            f"You've reached your free daily text limit ({limit}/{limit})! 🥰\n\n"
            f"🎬 **Watch a quick sponsor ad** to claim **+20 Free Messages** right now, or unlock VIP!"
        )
        keyboard = {
            "inline_keyboard": [
                [{"text": "🎬 Watch Ad to Recharge (+20 Msgs)", "callback_data": "ad_watch"}],
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
    try:
        reply_text = generate_text_reply(text, mode=active_contact, gender=gender, language=user_lang, history=history, user_memory=user_memory)
    except Exception as e:
        logger.error(f"Error in Gemini text generation: {e}")
        reply_text = get_human_boundary_reply(text)
        
    add_conversation_turn(user_id, "user", text)
    add_conversation_turn(user_id, "model", reply_text)
    
    reply_kb = get_persistent_reply_keyboard(gender, active_contact)
    await bot.send_message(chat_id, reply_text, reply_markup=reply_kb)

async def health_check(request):
    """Health check endpoint required by cloud hosting platforms (Render/Koyeb)."""
    return web.json_response({
        "status": "online",
        "service": "Joy Bot - 24/7 Cloud AI Voice Companion",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

async def serve_call_page(request):
    """Serves the real-time voice call Telegram Mini-App interface."""
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
                                db_gender, db_contact = get_user_contact_settings(int(call_user_id))
                            except Exception:
                                pass

                        current_gender = data.get("gender") or db_gender
                        current_contact = data.get("contact") or data.get("mode") or db_contact

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
                        contact_info = get_contact_info(current_contact, current_gender)
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

                    elif msg_type == "voice_chunk":
                        raw_base64 = data.get("audio", "")
                        mime_type = data.get("mime_type", "audio/wav")
                        current_gender = data.get("gender") or current_gender
                        current_contact = data.get("contact") or data.get("mode") or current_contact
                        if data.get("language"):
                            current_language = data.get("language")
                        contact_info = get_contact_info(current_contact, current_gender)
                        current_voice = contact_info.get("voice", "female")

                        if raw_base64:
                            audio_bytes = base64.b64decode(raw_base64)
                            user_id = data.get("user_id") or call_user_id
                            user_memory = None
                            if user_id:
                                try:
                                    _, user_memory = get_user_imported_memory(int(user_id))
                                    if not user_memory:
                                        _, user_memory = restore_user_memory_from_notion(int(user_id))
                                except Exception:
                                    pass
                            loop = asyncio.get_running_loop()
                            transcript, reply_text = await loop.run_in_executor(
                                None,
                                generate_voice_reply,
                                audio_bytes,
                                mime_type,
                                current_contact,
                                current_gender,
                                current_language,
                                history,
                                user_memory
                            )

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
                                except Exception as e:
                                    logger.warning(f"Could not persist call turn to DB: {e}")

                            # Inform client of transcript
                            if transcript and transcript != "Voice Note":
                                await ws.send_json({
                                    "type": "transcript",
                                    "text": transcript
                                })

                            # Synthesize audio with Edge-TTS
                            joy_audio = await synthesize_speech(reply_text, voice_key=current_voice)
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

async def start_web_server(port: int = 8080):
    """Starts a non-blocking background HTTP server for 24/7 cloud keep-alive & real-time calls."""
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    app.router.add_get("/call", serve_call_page)
    app.router.add_get("/ws/call", websocket_call_handler)
    
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

    bot = TelegramClient(TELEGRAM_BOT_TOKEN)
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
