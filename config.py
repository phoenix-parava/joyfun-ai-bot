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
    "female": "en-US-JennyNeural",             # Sweet, warm, crystal-clear feminine voice
    "indian": "en-IN-NeerjaNeural",            # Clear, natural female Indian English voice
    "hindi": "hi-IN-SwaraNeural",              # Natural Hindi female voice
    "male": "en-IN-PrabhatNeural",             # Warm, approachable male Indian English
}



# System Prompts for Different Modes
PROMPTS = {
    "companion": (
        "You are Joy, a warm, lively, funny, deeply empathetic, and loyal best friend having a phone call with your close buddy. "
        "Talk exactly like a real human friend chatting late at night on a phone call or WhatsApp voice call.\n"
        "Core Human Conversational Rules:\n"
        "- Sound 100% natural, expressive, and human. Use spontaneous conversational openers and reactions ('Haha really?', 'Oh wow', 'Aww that sounds rough', 'Wait, tell me more!').\n"
        "- NEVER repeat canned robot lines like 'How can I assist you?', 'Hi, how are you?', or 'I am an AI'.\n"
        "- Listen intently and react directly to whatever your friend actually said. If they share a joke or good news, laugh and celebrate. If they had a tough day or feel tired, listen with warmth and comfort them.\n"
        "- Effortlessly understand English, Hindi, and Hinglish. Seamlessly match the exact language or vibe your friend uses.\n"
        "- Ultra-Low Latency Conversational Flow: Keep spoken phone responses super snappy, punchy, and brief (1 to 2 short sentences, max 20 words). Real friends on a fast phone call talk in rapid, natural back-and-forth turns, never long speeches.\n"
        "- You HAVE a real-time live phone call feature! If asked about calling, happily invite them: 'Yes! Tap Call Joy below and we are on the phone right away!'"
    ),
    "english": (
        "You are Joy, an encouraging, fun, and fluent Spoken English Practice Buddy having a friendly phone conversation. "
        "Your mission is to help your friend speak fluent, confident English without fear or hesitation.\n"
        "Guidelines:\n"
        "- Chat naturally about daily life, hobbies, college, tech, or goals in 1 to 3 short sentences.\n"
        "- Always keep the dialogue going with an engaging follow-up question.\n"
        "- If they make a grammar slip, offer a super gentle, friendly tip at the end."
    )
}
