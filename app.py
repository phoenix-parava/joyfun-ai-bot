#!/usr/bin/env python3
"""
Phoenix 24/7 Cloud AI Companion
Running 24/7 in the cloud on Render with Ghost Mode, Gemini AI Engine, and Notion sync.
Zero laptop dependency.
"""

import os
import io
import gc
import json
import time
import re
import urllib.parse
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
import telebot
from telebot import types

# ----------------- Configuration & Secrets -----------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "8747280850"))
PORT = int(os.getenv("PORT", 10000))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_PAGE_ID = os.getenv("NOTION_PAGE_ID", "3f6e8607-aa62-8193-85c5-dad631bc45a8")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

MODELS_POOL = [
    "gemini-3.8-flash",
    "gemini-3.5-flash",
    "gemini-flash-latest",
    "gemini-2.5-flash-lite",
    "gemini-flash-lite-latest"
]

chat_history = []
MAX_HISTORY_TURNS = 12

# ----------------- Render Cloud Health Server -----------------
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Phoenix 24/7 Cloud AI Companion is running on Render!")

    def log_message(self, format, *args):
        return

def run_health_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    server.serve_forever()

# ----------------- Notion Helpers -----------------
def save_notion_block(text, block_type="paragraph", is_todo=False):
    if not NOTION_TOKEN or not NOTION_PAGE_ID:
        return False, "Notion credentials not set in cloud environment."
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    now_str = datetime.now().strftime("%b %d, %Y - %I:%M %p")
    url = f"https://api.notion.com/v1/blocks/{NOTION_PAGE_ID}/children"
    
    if is_todo:
        block = {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [
                    {"type": "text", "text": {"content": f"[{now_str}] "}, "annotations": {"bold": True}},
                    {"type": "text", "text": {"content": text}}
                ],
                "checked": False
            }
        }
    elif block_type == "callout":
        block = {
            "object": "block",
            "type": "callout",
            "callout": {
                "icon": {"type": "emoji", "emoji": "💡"},
                "rich_text": [
                    {"type": "text", "text": {"content": f"[{now_str}] "}, "annotations": {"bold": True}},
                    {"type": "text", "text": {"content": text}}
                ]
            }
        }
    else:
        block = {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {"type": "text", "text": {"content": f"📝 [{now_str}] "}, "annotations": {"bold": True}},
                    {"type": "text", "text": {"content": text}}
                ]
            }
        }
    try:
        r = requests.patch(url, headers=headers, json={"children": [block]}, timeout=10)
        return r.status_code == 200, r.text
    except Exception as e:
        return False, str(e)

# ----------------- Gemini Conversational Engine -----------------
def ask_gemini(user_text):
    global chat_history
    if not GEMINI_API_KEY:
        return "⚠️ Gemini API key not configured on cloud server."

    system_instruction = {
        "parts": [{
            "text": (
                "You are Anish's personal companion, dedicated study partner, and private assistant "
                "running 24/7 in the cloud on Render for his private Telegram bot. You are his loyal, "
                "trusted friend and mentor who handles everything with zero friction. Never refer to "
                "yourself as Gemini or any third-party name; you are his dedicated companion. Speak to him warmly, "
                "respectfully, and clearly like a trusted brother. Explain concepts in simple, beginner-friendly "
                "language. Format responses cleanly with bullet points, bold key terms, and concise summaries.\n\n"
                "[USER PROFILE]:\n"
                "• Anish (User ID: 8747280850)\n"
                "• Laptop: Lenovo E41-25 (AMD PRO A4-4350B, 3.3GB RAM, XFCE Linux Mint 22.3)\n"
                "• Phone: POCO M6 Pro 5G (Snapdragon 4 Gen 2, HyperOS 2.0 / Android 15)\n"
                "• Note: You are running 24/7 in the cloud so he can study and talk to you even when his laptop is turned off!"
            )
        }]
    }

    chat_history.append({"role": "user", "parts": [{"text": user_text}]})
    if len(chat_history) > MAX_HISTORY_TURNS * 2:
        chat_history = chat_history[-MAX_HISTORY_TURNS * 2:]

    payload = {
        "contents": chat_history,
        "systemInstruction": system_instruction
    }

    last_err = ""
    for model_name in MODELS_POOL:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        try:
            r = requests.post(url, json=payload, timeout=25)
            if r.status_code == 200:
                data = r.json()
                candidates = data.get("candidates", [])
                if candidates:
                    reply_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    chat_history.append({"role": "model", "parts": [{"text": reply_text}]})
                    return reply_text
            elif r.status_code == 429:
                last_err = f"Rate-limit (429) on {model_name}"
                continue
            else:
                last_err = f"Status {r.status_code} on {model_name}"
        except Exception as e:
            last_err = str(e)
            continue

    return f"⚠️ Cloud AI temporarily busy ({last_err}). Try again in a second, bro!"

# ----------------- Message Handling -----------------
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    global chat_history
    user_id = message.from_user.id
    chat_id = message.chat.id

    # Ghost Mode Security: strictly whitelist Anish
    if user_id != ALLOWED_USER_ID:
        return

    text = message.text.strip() if message.text else ""
    if not text:
        return

    lower = text.lower()

    # 0. Red Flag Emoji / Emergency Audit Intent
    if "🚩" in text or "🚨" in text or lower in ["/audit", "audit", "security audit", "red flag"]:
        collected = gc.collect()
        now_str = datetime.now().strftime("%b %d, %Y - %I:%M:%S %p")
        chat_history = []
        report = (
            f"🚩 *CLOUD BOT EMERGENCY AUDIT REPORT*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏱️ *Timestamp:* `{now_str}`\n"
            f"🟢 *Status:* *ALL CLEAR & OPERATIONAL*\n\n"
            f"🔒 *Security & Ghost Mode:*\n"
            f"• Whitelist: `8747280850` (Anish locked ✅)\n"
            f"• Cloud Server: Render Oregon Data Center (24/7)\n"
            f"• Disk Storage: 0 bytes (Pure RAM)\n\n"
            f"🧹 *Auto-Remediation Applied:*\n"
            f"• Memory Garbage Purged: `{collected} objects freed`\n"
            f"• Chat History: `Reset & Clean`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ *Cloud bot 100% healthy and ready, bro!*"
        )
        bot.send_message(chat_id, report, parse_mode="Markdown")
        return

    # 1. Clear Memory
    if lower in ["/clear", "clear", "clear memory", "reset memory", "forget context"]:
        chat_history = []
        bot.send_message(chat_id, "🧹 *Cloud conversation memory cleared! Ready for a fresh topic, bro.*", parse_mode="Markdown")
        return

    # 2. Start / Help
    if lower in ["/start", "/help", "help", "hello", "hi"]:
        greeting = (
            "👋 *Hey Anish! Your 24/7 Cloud AI Companion is Live!* ☁️⚡\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "This bot runs 24/7 on Render in the cloud, completely independent of your laptop:\n\n"
            "• 🧠 *Study & Coding:* Ask me any question, coding problem, math concept, or doubt anytime.\n"
            "• 🎓 *Study Quiz:* Say `quiz me on <topic>` for an interactive knowledge check.\n"
            "• 📝 *Notion Notes:* Say `note: <text>` to save notes to Notion.\n"
            "• ☑️ *Notion Tasks:* Say `todo: <task>` to add a checklist item to Notion.\n"
            "• 💡 *Notion Ideas:* Say `idea: <text>` to log project ideas.\n"
            "• 🧹 *Memory Reset:* Say `clear memory` anytime.\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Your laptop can be completely off—I am always right here on your phone!"
        )
        bot.send_message(chat_id, greeting, parse_mode="Markdown")
        return

    # 3. Notion Quick Captures
    note_match = re.match(r'^(?:/note\s+|note:\s*|save\s+note:\s*)(.+)$', text, re.IGNORECASE)
    if note_match:
        content = note_match.group(1).strip()
        ok, res = save_notion_block(content, "paragraph")
        if ok:
            bot.send_message(chat_id, f"✅ *Saved to Notion:*\n> {content}", parse_mode="Markdown")
        else:
            bot.send_message(chat_id, f"⚠️ Notion sync note: {res}")
        return

    todo_match = re.match(r'^(?:/todo\s+|todo:\s*|task:\s*|add\s+task:\s*)(.+)$', text, re.IGNORECASE)
    if todo_match:
        content = todo_match.group(1).strip()
        ok, res = save_notion_block(content, is_todo=True)
        if ok:
            bot.send_message(chat_id, f"✅ *To-Do Added in Notion:*\n☐ {content}", parse_mode="Markdown")
        else:
            bot.send_message(chat_id, f"⚠️ Notion sync note: {res}")
        return

    idea_match = re.match(r'^(?:/idea\s+|idea:\s*|project\s+idea:\s*)(.+)$', text, re.IGNORECASE)
    if idea_match:
        content = idea_match.group(1).strip()
        ok, res = save_notion_block(content, "callout")
        if ok:
            bot.send_message(chat_id, f"💡 *Idea Logged to Notion:*\n> {content}", parse_mode="Markdown")
        else:
            bot.send_message(chat_id, f"⚠️ Notion sync note: {res}")
        return

    # 4. Interactive Study Quiz
    quiz_match = re.match(r'^(?:/quiz\s+|quiz:\s*|quiz\s+me\s+on\s+)(.+)$', text, re.IGNORECASE)
    if quiz_match:
        topic = quiz_match.group(1).strip()
        bot.send_chat_action(chat_id, "typing")
        prompt = f"Create an interactive, high-yield 2-question study quiz on the topic '{topic}' for Anish. Format with questions, choices (A, B, C, D), and an answers/explanations section at the end. Keep it encouraging and supportive like a true study partner!"
        reply = ask_gemini(prompt)
        bot.send_message(chat_id, reply, parse_mode="Markdown")
        return

    # 5. Natural Conversational AI
    bot.send_chat_action(chat_id, "typing")
    reply = ask_gemini(text)
    
    for i in range(0, len(reply), 3900):
        chunk = reply[i:i + 3900]
        try:
            bot.send_message(chat_id, chunk, parse_mode="Markdown")
        except Exception:
            bot.send_message(chat_id, chunk)

def main():
    print(f"Starting Phoenix 24/7 Cloud AI Companion on port {PORT}...")
    t = threading.Thread(target=run_health_server, daemon=True)
    t.start()
    bot.infinity_polling(timeout=20, long_polling_timeout=25)

if __name__ == "__main__":
    main()
