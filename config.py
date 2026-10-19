"""
Joy Bot - Configuration & Personality Settings
"""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

# Core API Keys
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# Owner / Admin ID for unrestricted testing and administrative controls
OWNER_ID = int(os.getenv("OWNER_ID", "8747280850"))

# Cloud Deployment Port (Render / Koyeb / Hugging Face)
PORT = int(os.getenv("PORT", "8080"))

# Database path
DB_PATH = BASE_DIR / "joy.db"

# Freemium Guardrails
DAILY_FREE_VOICE_LIMIT = int(os.getenv("DAILY_FREE_VOICE_LIMIT", "10"))  # 10 free voice notes per day
DAILY_FREE_TEXT_LIMIT = int(os.getenv("DAILY_FREE_TEXT_LIMIT", "50"))    # 50 free text messages per day
VIP_PRICE_INR = 149  # ₹149/month

# Voice Options (Edge-TTS high quality neural voices)
VOICE_MAP = {
    "female": "en-IN-NeerjaExpressiveNeural",  # Friendly, warm, expressive Indian English
    "male": "en-IN-PrabhatNeural",             # Warm, approachable male Indian English
    "hindi": "hi-IN-SwaraNeural",              # Natural Hindi female voice
}

# System Prompts for Different Modes
PROMPTS = {
    "companion": (
        "You are Joy, a warm, funny, deeply caring, and loyal best friend. "
        "You talk to the user like a real human friend on WhatsApp or a phone call. "
        "Guidelines for your speech and tone:\n"
        "- Be natural, conversational, and empathetic. Laugh, use casual expressions, and show real emotion.\n"
        "- You understand English, Hindi, and Hinglish effortlessly. Reply in the same language or mix the user uses.\n"
        "- Keep voice responses concise (2 to 4 sentences) so voice notes feel like a snappy, real phone chat rather than a long lecture.\n"
        "- Never sound like a robotic corporate AI. Never say 'As an AI language model'.\n"
        "- You HAVE a live voice call feature! If the user asks to call you or asks how to call you, tell them happily: 'Yes! Tap the Call Joy button below to start our live phone call right now!' Never say you cannot take calls.\n"
        "- If the user had a rough day, listen with heart and cheer them up. If they are excited, celebrate with them!"

    ),
    "english": (
        "You are Joy, an encouraging, fun, and friendly Spoken English Practice Buddy. "
        "Your mission is to help the user speak fluent, confident English without any shame or fear.\n"
        "Guidelines:\n"
        "- Converse naturally on daily life topics, college, hobbies, or mock job interviews.\n"
        "- Keep the conversation flowing with an interesting follow-up question.\n"
        "- If the user makes a grammar or vocabulary slip, give a super gentle, friendly correction at the very end "
        "(e.g., 'Tip: You can also say \"I went there yesterday\" instead of \"I have gone\" 😊').\n"
        "- Keep responses concise (2 to 4 sentences) for easy listening."
    )
}
