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
    set_vip_status
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

def get_main_keyboard(user_mode: str = "companion", user_voice: str = "female") -> dict:
    mode_text = "💖 Best Friend Mode" if user_mode == "companion" else "📚 English Practice Mode"
    voice_label = {"female": "👩 Female Voice", "male": "👨 Male Voice", "hindi": "🇮🇳 Hindi Voice"}.get(user_voice, "👩 Female Voice")
    
    return {
        "inline_keyboard": [
            [
                {"text": "📞 Call Joy Now (Live Audio)", "web_app": {"url": "https://joyfun-ai-bot.onrender.com/call"}}
            ],
            [
                {"text": f"Mode: {mode_text}", "callback_data": "menu_mode"},
            ],
            [
                {"text": f"Voice: {voice_label}", "callback_data": "menu_voice"},
                {"text": "⭐ Joy VIP Pass", "callback_data": "menu_vip"}
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

async def handle_vip(bot: TelegramClient, chat_id: int, user: dict):
    is_vip = user.get("is_vip", 0)
    if is_vip:
        text = (
            "🌟 **You are a Joy VIP Member!**\n\n"
            "✨ Unlimited daily voice chats\n"
            "✨ Zero cooldowns or recharge limits\n"
            "✨ Priority high-speed neural speech synthesis\n"
            "Thank you for supporting Joy! 🥰"
        )
    else:
        text = (
            f"⭐ **Unlock Joy VIP Pass**\n\n"
            f"Never run out of talk time! Get unlimited 24/7 voice conversations with your AI companion.\n\n"
            f"✨ **Unlimited Voice Notes** (Talk for hours every night)\n"
            f"✨ **Fluent English Coaching & Feedback**\n"
            f"✨ **Ultra-Fast Voice Replies**\n\n"
            f"💰 **Only ₹{VIP_PRICE_INR} / month** (Less than ₹5 a day!)\n\n"
            f"📲 To activate, send a payment of ₹{VIP_PRICE_INR} via UPI / GPay to the owner, or contact @Anish for instant VIP activation!"
        )
    await bot.send_message(chat_id, text)

async def handle_stats(bot: TelegramClient, chat_id: int, user: dict):
    user_id = user["user_id"]
    is_vip = user.get("is_vip", 0)
    
    if is_vip:
        msg = "⭐ **Account Status:** VIP Member (Unlimited Voice & Text Chats)"
    else:
        msg = (
            f"📊 **Your Daily Usage:**\n\n"
            f"🎙️ Daily Free Voice Limit: {DAILY_FREE_VOICE_LIMIT} notes/day\n"
            f"💬 Daily Free Text Limit: {DAILY_FREE_TEXT_LIMIT} messages/day\n\n"
            f"Limits reset every midnight! Type /vip to unlock unlimited conversations."
        )
    await bot.send_message(chat_id, msg)

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

async def process_user_voice(bot: TelegramClient, chat_id: int, user: dict, file_id: str):
    user_id = user["user_id"]
    
    # 1. Check daily limit
    allowed, used, limit = check_and_increment_usage(user_id, "voice")
    if not allowed:
        limit_msg = (
            f"Aww, your free daily voice notes ({limit}/{limit}) are finished for today! 🥰\n\n"
            f"Joy loves chatting with you! To talk unlimited anytime day or night, tap below to unlock the **Joy VIP Pass**."
        )
        keyboard = {"inline_keyboard": [[{"text": f"⭐ Unlock Joy VIP (₹{VIP_PRICE_INR}/mo)", "callback_data": "menu_vip"}]]}
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
    
    # Check commands
    if text.startswith("/start"):
        await handle_start(bot, chat_id, user)
        return
    elif text.startswith("/vip"):
        await handle_vip(bot, chat_id, user)
        return
    elif text.startswith("/stats"):
        await handle_stats(bot, chat_id, user)
        return
    elif text.startswith("/mode"):
        await bot.send_message(chat_id, "Choose Joy's mode:", reply_markup=get_mode_keyboard())
        return
    elif text.startswith("/voice"):
        await bot.send_message(chat_id, "Choose Joy's voice:", reply_markup=get_voice_keyboard())
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
        limit_msg = f"You've reached your free daily text limit ({limit}/{limit})! Upgrade to VIP for unlimited texting and voice chats."
        await bot.send_message(chat_id, limit_msg)
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
    
    await bot.send_message(chat_id, f"💖 {reply_text}")

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
                        greeting = "Hey! I'm on the line. How are you doing today?" if current_mode == "companion" else "Hey there! Ready to practice your English today? What would you like to talk about?"
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

                    elif msg_type == "voice_chunk":
                        raw_base64 = data.get("audio", "")
                        mime_type = data.get("mime_type", "audio/webm")
                        current_mode = data.get("mode", current_mode)
                        current_voice = data.get("voice", current_voice)

                        if raw_base64:
                            audio_bytes = base64.b64decode(raw_base64)
                            # Generate conversational reply with Gemini Flash in executor
                            loop = asyncio.get_running_loop()
                            transcript, reply_text = await loop.run_in_executor(
                                None,
                                generate_voice_reply,
                                audio_bytes,
                                mime_type,
                                current_mode,
                                history
                            )

                            history.append({"role": "user", "content": transcript})
                            history.append({"role": "model", "content": reply_text})
                            if len(history) > 10:
                                history = history[-10:]

                            # Inform client of transcript
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
                    fallback_text = "I'm listening, friend! Could you say that once more?"
                    try:
                        joy_audio = await synthesize_speech(fallback_text, voice_key=current_voice)
                        joy_b64 = base64.b64encode(joy_audio).decode('utf-8')
                        await ws.send_json({
                            "type": "joy_speech",
                            "text": fallback_text,
                            "audio": joy_b64
                        })
                    except Exception:
                        pass

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

    # Configure Telegram Persistent Bottom Menu Button
    try:
        menu_res = await bot.set_chat_menu_button(menu_button={
            "type": "web_app",
            "text": "📞 Call Joy",
            "web_app": {
                "url": "https://joyfun-ai-bot.onrender.com/call"
            }
        })
        logger.info(f"Set Telegram Chat Menu Button: {menu_res}")
    except Exception as e:
        logger.warning(f"Could not configure menu button: {e}")

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
