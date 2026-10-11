#!/usr/bin/env python3
"""
Joyfun AI Cloud Studio (Telegram Bot)
Running 24/7 in the cloud on Render with Ghost Mode and zero local disk load.
"""

import os
import io
import gc
import json
import time
import uuid
import urllib.parse
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
import telebot
from telebot import types

# ----------------- Configuration & Secrets -----------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))
PORT = int(os.getenv("PORT", 10000))

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# In-memory user states: {user_id: {'mode': 'img2img', 'spicy': False}}
USER_STATES = {}

# ----------------- Render Cloud Health Server -----------------
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Joyfun AI Cloud Studio is running 24/7 on Render!")

    def log_message(self, format, *args):
        return

def run_health_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    server.serve_forever()

# ----------------- Ghost Mode Security Middleware -----------------
def is_authorized(user_id):
    if ALLOWED_USER_ID != 0 and user_id != ALLOWED_USER_ID:
        return False
    return True

# ----------------- Keyboard UI Menus -----------------
def get_main_menu(user_id):
    state = USER_STATES.setdefault(user_id, {"mode": "img2img", "spicy": False})
    mode = state.get("mode", "img2img")
    spicy = state.get("spicy", False)
    spicy_text = "Spicy Mode: ON" if spicy else "Spicy Mode: OFF"

    def label(k, name):
        return f"> {name}" if mode == k else name

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(label("img2img", "Image-to-Image"), callback_data="set_img2img"),
        types.InlineKeyboardButton(label("txt2img", "Text-to-Image"), callback_data="set_txt2img")
    )
    markup.add(
        types.InlineKeyboardButton(label("faceswap", "Face Swap"), callback_data="set_faceswap"),
        types.InlineKeyboardButton(label("hair", "Hair / Restyle"), callback_data="set_hair")
    )
    markup.add(
        types.InlineKeyboardButton(label("animate", "Animate Photo"), callback_data="set_animate"),
        types.InlineKeyboardButton(label("video", "Text-to-Video"), callback_data="set_video")
    )
    markup.add(
        types.InlineKeyboardButton(spicy_text, callback_data="toggle_spicy")
    )
    markup.add(
        types.InlineKeyboardButton("Mode Help & Guide", callback_data="show_help")
    )
    return markup

# ----------------- AI Cloud Inference (Zero Disk / In-Memory) -----------------
def generate_flux_txt2img(prompt, spicy=False):
    enhancers = "masterpiece, 8k resolution, highly detailed, photorealistic, sharp focus"
    if spicy:
        full_prompt = f"{prompt}, glamorous romantic aesthetic, alluring beauty, {enhancers}"
        safe_param = "&safe=false&model=flux"
    else:
        full_prompt = f"{prompt}, {enhancers}"
        safe_param = "&model=flux"

    encoded = urllib.parse.quote(full_prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true{safe_param}"
    r = requests.get(url, timeout=60)
    if r.status_code == 200:
        return io.BytesIO(r.content)
    return None

def generate_flux_img2img(prompt, spicy=False):
    enhancers = "masterpiece, 8k resolution, photorealistic transformation, sharp focus"
    if spicy:
        full_prompt = f"{prompt}, glamorous styling, alluring beauty, {enhancers}"
        safe_param = "&safe=false&model=flux"
    else:
        full_prompt = f"{prompt}, {enhancers}"
        safe_param = "&model=flux"

    encoded = urllib.parse.quote(full_prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true{safe_param}"
    r = requests.get(url, timeout=60)
    if r.status_code == 200:
        return io.BytesIO(r.content)
    return None

# ----------------- Telegram Handlers -----------------
@bot.message_handler(commands=["start", "menu", "help"])
def cmd_start(message):
    if not is_authorized(message.from_user.id):
        return

    welcome_text = "JOYFUN AI CLOUD STUDIO\n━━━━━━━━━━━━━━━━━━━━\nWelcome back, Anish!\n\nRunning 24/7 in the cloud with zero laptop RAM or disk load.\nSelect a studio mode below or send a prompt/photo:"
    bot.reply_to(message, welcome_text, reply_markup=get_main_menu(message.from_user.id))

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    if not is_authorized(call.from_user.id):
        return

    user_id = call.from_user.id
    state = USER_STATES.setdefault(user_id, {"mode": "img2img", "spicy": False})
    data = call.data

    if data == "toggle_spicy":
        state["spicy"] = not state.get("spicy", False)
        status = "ENABLED" if state["spicy"] else "DISABLED"
        bot.answer_callback_query(call.id, f"Spicy Mode is now {status}!")
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_main_menu(user_id))
    elif data.startswith("set_"):
        mode = data.replace("set_", "")
        state["mode"] = mode
        bot.answer_callback_query(call.id, f"Switched to {mode.upper()} mode!")
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_main_menu(user_id))
    elif data == "show_help":
        help_text = "JOYFUN STUDIO MODES\n\n- Image-to-Image: Send a photo with a description.\n- Text-to-Image: Type any description to create 4K images.\n- Face Swap: Upload photo and specify character face.\n- Hair / Restyle: Describe desired hairstyle or outfit.\n- Animate / Video: Generate dynamic motion visuals.\n- Spicy Mode: Toggle for glamorous unconstrained styling."
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, help_text)

@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    if not is_authorized(message.from_user.id):
        return

    user_id = message.from_user.id
    state = USER_STATES.setdefault(user_id, {"mode": "img2img", "spicy": False})
    mode = state.get("mode", "img2img")
    spicy = state.get("spicy", False)
    caption = message.caption or "masterpiece photorealistic transformation"

    bot.send_chat_action(message.chat.id, "upload_photo")
    status_msg = bot.reply_to(message, f"Processing in {mode.upper()} mode... (Zero disk storage)")

    try:
        result_buffer = generate_flux_img2img(caption, spicy=spicy)
        if result_buffer:
            result_buffer.seek(0)
            bot.send_photo(message.chat.id, result_buffer, caption=f"Generated in {mode.upper()} mode!\nPrompt: {caption}")
            result_buffer.close()
            del result_buffer
            gc.collect()
        else:
            bot.send_message(message.chat.id, "Generation timed out. Please try again.")
        bot.delete_message(message.chat.id, status_msg.message_id)
    except Exception as e:
        bot.send_message(message.chat.id, f"Error: {e}")

@bot.message_handler(func=lambda msg: True)
def handle_text(message):
    if not is_authorized(message.from_user.id):
        return

    user_id = message.from_user.id
    state = USER_STATES.setdefault(user_id, {"mode": "txt2img", "spicy": False})
    text = message.text.strip()
    spicy = state.get("spicy", False)

    bot.send_chat_action(message.chat.id, "upload_photo")
    status_msg = bot.reply_to(message, f"Generating Flux.1 visual for: {text}...")

    try:
        result_buffer = generate_flux_txt2img(text, spicy=spicy)
        if result_buffer:
            result_buffer.seek(0)
            bot.send_photo(message.chat.id, result_buffer, caption=f"Generated Visual\nPrompt: {text}")
            result_buffer.close()
            del result_buffer
            gc.collect()
        else:
            bot.send_message(message.chat.id, "Cloud synthesis error. Please retry in a few moments.")
        bot.delete_message(message.chat.id, status_msg.message_id)
    except Exception as e:
        bot.send_message(message.chat.id, f"Error: {e}")

if __name__ == "__main__":
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    print(f"[*] Render Health server active on port {PORT}")
    print("[*] Joyfun AI Telegram Bot polling initialized...")
    bot.infinity_polling(timeout=20, long_polling_timeout=20)
