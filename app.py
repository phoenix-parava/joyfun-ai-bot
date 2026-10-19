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
    get_all_subscribers
)
from ai_engine import generate_text_reply, generate_voice_reply
from voice_engine import synthesize_speech
from telegram_client import TelegramClient

# Setup logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("JoyBot")

BOT_COMMANDS = [
    {"command": "call", "description": "📞 Start Live Voice Call with Joy"},
    {"command": "menu", "description": "📱 Open Interactive Menu"},
    {"command": "settings", "description": "⚙️ Customize Mode & Voice"},
    {"command": "recharge", "description": "🎬 Free Talk Time & Voice Recharge"},
    {"command": "vip", "description": "⭐ Joy VIP Pass (Unlimited Calls)"},
    {"command": "mode", "description": "💖 Switch Best Friend / English Coach"},
    {"command": "voice", "description": "🌸 Change Joy's Voice"},
    {"command": "stats", "description": "📊 View My Daily Usage & Balance"},
    {"command": "reset", "description": "🧹 Clear Conversation Memory"}
]

def get_persistent_reply_keyboard() -> dict:
    """Returns a docked, compact 2x2 keyboard at the bottom of the chat for fast, thumb-friendly access."""
    return {
        "keyboard": [
            [{"text": "📞 Call Joy"}, {"text": "🎬 Recharge"}],
            [{"text": "⚙️ Settings"}, {"text": "⭐ VIP"}]
        ],
        "resize_keyboard": True,
        "is_persistent": True
    }


def get_main_keyboard(user_mode: str = "companion", user_voice: str = "female") -> dict:
    mode_emoji = "💖 Best Friend" if user_mode == "companion" else "📚 English Coach"
    voice_emoji = {"female": "👩 Neerja", "male": "👨 Prabhat", "hindi": "🇮🇳 Swara"}.get(user_voice, "👩 Neerja")
    
    return {
        "inline_keyboard": [
            [
                {"text": "📞 Call Joy Now (Live Audio)", "web_app": {"url": "https://joyfun-ai-bot.onrender.com/call"}}
            ],
            [
                {"text": f"🎭 {mode_emoji}", "callback_data": "menu_mode"},
                {"text": f"🗣️ {voice_emoji}", "callback_data": "menu_voice"}
            ],
            [
                {"text": "🎬 Free Recharge", "callback_data": "ad_watch"},
                {"text": "⭐ Joy VIP Pass", "callback_data": "menu_vip"}
            ],
            [
                {"text": "📊 My Usage & Balance", "callback_data": "menu_stats"}
            ]
        ]
    }

def get_mode_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "💖 Best Friend (Venting & Daily Life)", "callback_data": "set_mode_companion"}],
            [{"text": "📚 English Practice Partner (Fluency & Tips)", "callback_data": "set_mode_english"}],
            [{"text": "⬅️ Back", "callback_data": "menu_main"}]
        ]
    }

def get_voice_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "👩 Neerja (Expressive Indian English)", "callback_data": "set_voice_female"}],
            [{"text": "👨 Prabhat (Friendly Male English)", "callback_data": "set_voice_male"}],
            [{"text": "🇮🇳 Swara (Natural Hindi Voice)", "callback_data": "set_voice_hindi"}],
            [{"text": "⬅️ Back", "callback_data": "menu_main"}]
        ]
    }

async def handle_menu(bot: TelegramClient, chat_id: int, user: dict):
    keyboard = get_main_keyboard(user.get("mode", "companion"), user.get("voice", "female"))
    text = (
        "📱 **Joy Control Menu**\n\n"
        "Here are all your quick options to talk, recharge, and customize Joy!\n"
        "You can also use the buttons pinned directly to your keyboard below 👇"
    )
    await bot.send_message(chat_id, text, reply_markup=keyboard)

async def handle_settings(bot: TelegramClient, chat_id: int, user: dict):
    mode_text = "💖 Best Friend" if user.get("mode") == "companion" else "📚 English Coach"
    voice_label = {"female": "👩 Neerja", "male": "👨 Prabhat", "hindi": "🇮🇳 Swara"}.get(user.get("voice"), "👩 Neerja")
    keyboard = {
        "inline_keyboard": [
            [{"text": f"🎭 Mode: {mode_text}", "callback_data": "menu_mode"}],
            [{"text": f"🗣️ Voice: {voice_label}", "callback_data": "menu_voice"}],
            [{"text": "⬅️ Main Menu", "callback_data": "menu_main"}]
        ]
    }
    await bot.send_message(chat_id, "⚙️ **Joy Customization Settings:**\n\nCustomize how Joy talks and sounds with you:", reply_markup=keyboard)

async def handle_start(bot: TelegramClient, chat_id: int, user: dict):
    first_name = user.get("first_name", "Friend")
    welcome_text = (
        f"Hey {first_name}! 💖 I'm **Joy**, your 24/7 AI best friend & voice companion.\n\n"
        f"Whenever you want to talk about your day, vent your stress, share good news, "
        f"or practice fluent spoken English without any judgment, I'm right here with you!\n\n"
        f"📞 **Live Voice Call:** Tap **Call Joy Now** below to start an instant, continuous phone call with me!\n"
        f"🎙️ **Voice Notes:** You can also hold the mic button and send voice notes anytime.\n\n"
        f"Ready to talk? Tap below to start your call! 👇"
    )
    keyboard = get_main_keyboard(user.get("mode", "companion"), user.get("voice", "female"))
    await bot.send_message(chat_id, welcome_text, reply_markup=keyboard)
    # Ensure persistent reply keyboard is docked
    await bot.send_message(
        chat_id,
        "💡 *Tip: Quick menu shortcuts are pinned to your bottom keyboard. You can also tap the blue [ ≡ Menu ] button anytime!*",
        reply_markup=get_persistent_reply_keyboard()
    )

async def handle_vip(bot: TelegramClient, chat_id: int, user: dict):
    user_id = user["user_id"]
    vip_active, expiry_formatted, days_left = is_user_vip(user_id)
    
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
        keyboard = {
            "inline_keyboard": [
                [{"text": "📞 Call Joy Now (Live Audio)", "web_app": {"url": "https://joyfun-ai-bot.onrender.com/call"}}],
                [{"text": "⬅️ Main Menu", "callback_data": "menu_main"}]
            ]
        }
        await bot.send_message(chat_id, text, reply_markup=keyboard)
    else:
        text = (
            f"⭐ **Unlock Joy VIP Pass**\n\n"
            f"Never run out of talk time! Get unlimited 24/7 live calls and voice conversations with Joy.\n\n"
            f"✨ **Unlimited 24/7 Live Voice Calls** (Talk for hours every night)\n"
            f"✨ **Unlimited Voice Notes & Text Chats**\n"
            f"✨ **Zero Wait Times & No Ads**\n"
            f"✨ **Fluent English Coaching & Feedback**\n"
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
                [{"text": "⬅️ Back", "callback_data": "menu_main"}]
            ]
        }
        await bot.send_message(chat_id, text, reply_markup=keyboard)

async def handle_stats(bot: TelegramClient, chat_id: int, user: dict):
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
    await bot.send_message(chat_id, msg, reply_markup=get_persistent_reply_keyboard())

async def handle_callback_query(bot: TelegramClient, callback: dict):
    cq_id = callback["id"]
    data = callback.get("data", "")
    message = callback.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    user_info = callback.get("from", {})
    user_id = user_info.get("id")
    
    user = get_or_create_user(user_id, user_info.get("username", ""), user_info.get("first_name", ""))
    
    if data == "menu_main":
        await bot.answer_callback_query(cq_id)
        keyboard = get_main_keyboard(user.get("mode", "companion"), user.get("voice", "female"))
        await bot.send_message(chat_id, "Choose how you'd like to interact with Joy:", reply_markup=keyboard)
        
    elif data == "menu_mode":
        await bot.answer_callback_query(cq_id)
        await bot.send_message(chat_id, "Select Joy's conversation mode:", reply_markup=get_mode_keyboard())
        
    elif data == "menu_voice":
        await bot.answer_callback_query(cq_id)
        await bot.send_message(chat_id, "Select the voice Joy uses to speak with you:", reply_markup=get_voice_keyboard())
        
    elif data == "menu_vip":
        await bot.answer_callback_query(cq_id)
        await handle_vip(bot, chat_id, user)
        
    elif data == "menu_stats":
        await bot.answer_callback_query(cq_id)
        await handle_stats(bot, chat_id, user)
        
    elif data == "set_mode_companion":
        update_user_preference(user_id, "mode", "companion")
        await bot.answer_callback_query(cq_id, "💖 Switched to Best Friend Mode!")
        await bot.send_message(chat_id, "💖 Mode updated! Joy is now in **Best Friend Mode**. Share anything on your mind!")
        
    elif data == "set_mode_english":
        update_user_preference(user_id, "mode", "english")
        await bot.answer_callback_query(cq_id, "📚 Switched to English Practice Mode!")
        await bot.send_message(chat_id, "📚 Mode updated! Joy is now your **English Practice Buddy**. Send a voice note in English to start practicing!")
        
    elif data == "set_voice_female":
        update_user_preference(user_id, "voice", "female")
        await bot.answer_callback_query(cq_id, "👩 Voice set to Neerja (Expressive)!")
        await bot.send_message(chat_id, "Voice updated to **Neerja (Female Expressive)**! Send a voice note to hear Joy speak.")
        
    elif data == "set_voice_male":
        update_user_preference(user_id, "voice", "male")
        await bot.answer_callback_query(cq_id, "👨 Voice set to Prabhat (Male)!")
        await bot.send_message(chat_id, "Voice updated to **Prabhat (Male)**! Send a voice note to hear Joy speak.")
        
    elif data == "set_voice_hindi":
        update_user_preference(user_id, "voice", "hindi")
        await bot.answer_callback_query(cq_id, "🇮🇳 Voice set to Swara (Hindi)!")
        await bot.send_message(chat_id, "Voice updated to **Swara (Hindi)**! Send a voice note to hear Joy speak.")

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
                [{"text": "⬅️ Back", "callback_data": "menu_main"}]
            ]
        }
        await bot.send_message(chat_id, ad_text, reply_markup=keyboard)

    elif data == "ad_claim":
        recharge_user_usage(user_id, bonus_voice=5, bonus_text=20)
        await bot.answer_callback_query(cq_id, "🎉 Recharged! +5 Voice Notes added.")
        success_text = (
            "🎉 **Account Recharged Successfully!**\n\n"
            "Joy added **+5 Voice Notes** and **+20 Text Messages** to your balance for today! 🥰\n\n"
            "📞 Tap **Call Joy** below or send a voice note to keep chatting right away!"
        )
        keyboard = {
            "inline_keyboard": [
                [{"text": "📞 Call Joy Now (Live Audio)", "web_app": {"url": "https://joyfun-ai-bot.onrender.com/call"}}],
                [{"text": "⬅️ Main Menu", "callback_data": "menu_main"}]
            ]
        }
        await bot.send_message(chat_id, success_text, reply_markup=keyboard)

async def process_user_voice(bot: TelegramClient, chat_id: int, user: dict, file_id: str):
    user_id = user["user_id"]
    
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
                [{"text": f"⭐ Unlock Joy VIP (₹{VIP_PRICE_INR}/mo)", "callback_data": "menu_vip"}]
            ]
        }
        await bot.send_message(chat_id, limit_msg, reply_markup=keyboard)
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
    mode = user.get("mode", "companion")
    voice_choice = user.get("voice", "female")
    
    try:
        transcript, reply_text = generate_voice_reply(voice_bytes, mime_type="audio/ogg", mode=mode, history=history)
    except Exception as e:
        logger.error(f"Error in Gemini audio generation: {e}")
        reply_text = "I heard you, friend! But I had a slight hiccup thinking of a reply. Could you say that again?"
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
        audio_output = await synthesize_speech(reply_text, voice_key=voice_choice)
        caption = f"🎙️ *Joy:* {reply_text}"
        await bot.send_audio(chat_id, audio_output, filename="joy_reply.mp3", caption=caption, performer="Joy", title="Voice Note")
    except Exception as e:
        logger.error(f"Error in Edge-TTS synthesis: {e}")
        # Fallback to text message if TTS encounters an issue
        await bot.send_message(chat_id, f"💖 *Joy:* {reply_text}")

async def process_user_text(bot: TelegramClient, chat_id: int, user: dict, text: str):
    user_id = user["user_id"]
    clean_text = text.strip()
    lower_text = clean_text.lower()
    
    # Check commands & persistent keyboard button presses
    if clean_text.startswith("/start"):
        await handle_start(bot, chat_id, user)
        return
    elif clean_text.startswith("/menu") or clean_text in ["Menu", "menu", "📱 Control Menu", "Control Menu"]:
        await handle_menu(bot, chat_id, user)
        return
    elif clean_text.startswith("/settings") or clean_text in ["⚙️ Settings", "Settings", "settings"]:
        await handle_settings(bot, chat_id, user)
        return
    elif clean_text.startswith("/clean") or clean_text.startswith("/hidebuttons"):
        await bot.send_message(
            chat_id,
            "🧹 **Bottom buttons hidden!**\n\nYour chat is now completely clean and full-screen.\n"
            "Use the blue **[ ≡ Menu ]** button anytime on the bottom-left to run commands, or type `/menu` to bring the buttons back!",
            reply_markup={"remove_keyboard": True}
        )
        return
    elif clean_text.startswith("/vip") or clean_text in ["⭐ VIP", "VIP", "vip", "⭐ Joy VIP Pass", "Joy VIP Pass"]:
        await handle_vip(bot, chat_id, user)
        return
    elif clean_text.startswith("/stats") or clean_text in ["📊 My Status", "📊 Status", "Status", "stats"]:
        await handle_stats(bot, chat_id, user)
        return
    elif clean_text.startswith("/mode") or clean_text in ["💖 Change Mode", "Change Mode", "mode"]:
        await bot.send_message(chat_id, "Choose Joy's mode:", reply_markup=get_mode_keyboard())
        return
    elif clean_text.startswith("/voice") or clean_text in ["🌸 Change Voice", "Change Voice", "voice"]:
        await bot.send_message(chat_id, "Choose Joy's voice:", reply_markup=get_voice_keyboard())
        return
    elif clean_text.startswith("/call") or clean_text in ["📞 Call Joy", "📞 Call Joy Now", "Call Joy Now", "Call Joy"] or any(kw in lower_text for kw in ["can i call", "call you", "call u", "how to call", "phone call"]):
        call_keyboard = {
            "inline_keyboard": [
                [
                    {"text": "📞 Call Joy Now (Live Audio)", "web_app": {"url": "https://joyfun-ai-bot.onrender.com/call"}}
                ],
                [
                    {"text": "🌐 Open Call in Browser", "url": "https://joyfun-ai-bot.onrender.com/call"}
                ]
            ]
        }
        await bot.send_message(
            chat_id,
            "Yes! Of course you can call me! 🥰\n\nTap **Call Joy Now** below to start our live, hands-free phone call right now 👇",
            reply_markup=call_keyboard
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
                [{"text": "⬅️ Back", "callback_data": "menu_main"}]
            ]
        }
        await bot.send_message(chat_id, msg, reply_markup=keyboard)
        return
    elif text.startswith("/subscribers") or text.startswith("/vips"):
        if user_id != OWNER_ID:
            await bot.send_message(chat_id, "🔒 This command is only available to the bot owner.")
            return

        subs = get_all_subscribers()
        if not subs:
            await bot.send_message(chat_id, "⭐ No active subscribers found.")
            return

        lines = [f"⭐ **Active VIP Subscribers ({len(subs)} total):**\n"]
        for idx, s in enumerate(subs, 1):
            lines.append(
                f"{idx}. **{s['first_name']}** (@{s['username']}) - ID: `{s['user_id']}`\n"
                f"   ⏳ {s['status']} | Expires: {s['expires_at']}"
            )
        lines.append("\n💡 *To add a subscriber:* `/addvip <user_id> [days]`\n💡 *To remove:* `/removevip <user_id>`")
        await bot.send_message(chat_id, "\n".join(lines))
        return

    elif text.startswith("/addvip"):
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
            sub_info = grant_vip_subscription(target_id, days=days, amount=149.0, method="upi")
            
            await bot.send_message(
                chat_id,
                f"✅ **VIP Subscription Activated!**\n\n"
                f"👤 **User ID:** `{target_id}`\n"
                f"⏳ **Duration:** {days} days\n"
                f"📅 **Expires:** {sub_info['expires_at']}\n"
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

    elif text.startswith("/reset"):

        # Reset conversation memory
        with bot.get_session():
            from database import get_connection
            with get_connection() as conn:
                conn.cursor().execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
                conn.commit()
        await bot.send_message(chat_id, "🧹 Conversation memory refreshed! Let's start fresh. What's up?")
        return

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
                [{"text": f"⭐ Unlock Joy VIP (₹{VIP_PRICE_INR}/mo)", "callback_data": "menu_vip"}]
            ]
        }
        await bot.send_message(chat_id, limit_msg, reply_markup=keyboard)
        return

    await bot.send_chat_action(chat_id, "typing")
    
    history = get_recent_history(user_id, limit=6)
    mode = user.get("mode", "companion")
    
    try:
        reply_text = generate_text_reply(text, mode=mode, history=history)
    except Exception as e:
        logger.error(f"Error in Gemini text generation: {e}")
        reply_text = "Hey, my thoughts got tangled for a second! What did you say?"
        
    add_conversation_turn(user_id, "user", text)
    add_conversation_turn(user_id, "model", reply_text)
    
    await bot.send_message(chat_id, f"💖 {reply_text}", reply_markup=get_persistent_reply_keyboard())

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
    current_mode = "companion"
    current_voice = "female"

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    msg_type = data.get("type")

                    if msg_type == "call_started":
                        current_mode = data.get("mode", "companion")
                        current_voice = data.get("voice", "female")
                        import random
                        companion_greetings = [
                            "Hey! So good to hear from you. How was your day today?",
                            "Hey! I'm right here on the line. What's on your mind?",
                            "Hey there! So glad you called. What are you up to right now?"
                        ]
                        greeting = random.choice(companion_greetings) if current_mode == "companion" else "Hey there! Ready to practice your English today? What would you like to talk about?"
                        audio_bytes = await synthesize_speech(greeting, voice_key=current_voice)
                        base64_audio = base64.b64encode(audio_bytes).decode('utf-8')
                        await ws.send_json({
                            "type": "joy_speech",
                            "text": greeting,
                            "audio": base64_audio
                        })

                    elif msg_type == "mode_change":
                        current_mode = data.get("mode", "companion")
                        logger.info(f"Call mode changed to: {current_mode}")

                    elif msg_type == "voice_change":
                        current_voice = data.get("voice", "female")
                        logger.info(f"Call voice changed to: {current_voice}")

                    elif msg_type == "ad_recharge":
                        user_id = data.get("user_id", 0)
                        if user_id:
                            recharge_user_usage(int(user_id), bonus_voice=5, bonus_text=20)
                        await ws.send_json({
                            "type": "recharged",
                            "text": "🎉 Recharged +5 Mins Talk Time!"
                        })

                    elif msg_type == "voice_chunk":
                        raw_base64 = data.get("audio", "")
                        mime_type = data.get("mime_type", "audio/wav")
                        current_mode = data.get("mode", current_mode)
                        current_voice = data.get("voice", current_voice)

                        if raw_base64:
                            audio_bytes = base64.b64decode(raw_base64)
                            loop = asyncio.get_running_loop()
                            transcript, reply_text = await loop.run_in_executor(
                                None,
                                generate_voice_reply,
                                audio_bytes,
                                mime_type,
                                current_mode,
                                history
                            )

                            # If chunk was silent or empty, unlock client without generating audio
                            if not reply_text:
                                await ws.send_json({"type": "no_speech"})
                                continue

                            history.append({"role": "user", "content": transcript or "Voice Note"})
                            history.append({"role": "model", "content": reply_text})
                            if len(history) > 10:
                                history = history[-10:]

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
                                "audio": joy_b64
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
                            asyncio.create_task(process_user_text(bot, chat_id, user, text))

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
