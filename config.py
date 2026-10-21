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

# Render Cloud API & Service
RENDER_API_KEY = os.getenv("RENDER_API_KEY", "").strip()
if not RENDER_API_KEY:
    _rf = Path.home() / ".config" / "render_api_key"
    if _rf.exists():
        RENDER_API_KEY = _rf.read_text().strip()
RENDER_SERVICE_ID = os.getenv("RENDER_SERVICE_ID", "srv-db5tlu67bikc73e1bf80").strip()

# Google OAuth 2.0 & Google Drive Cloud Backup
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip().replace("https://", "").replace("http://", "").rstrip("/")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "https://joyfun-ai-bot.onrender.com/auth/google/callback").strip()

# System & Security Versions
BOT_VERSION = "v2.5.1"
MINI_APP_VERSION = "v1.7.7"
SECURITY_VERSION = "v2.5.1-SecPatch"
LAST_UPDATE_DATE = "Oct 21, 2026"

# Notion Subscription CRM Integration
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "").strip()
if not NOTION_TOKEN:
    _token_f = Path.home() / ".config" / "notion_token"
    if _token_f.exists():
        NOTION_TOKEN = _token_f.read_text().strip()

NOTION_SUBSCRIBERS_DB_ID = os.getenv("NOTION_SUBSCRIBERS_DB_ID", "3ffe8607-aa62-8166-98d8-c2ddd2e836d8").strip()
if not NOTION_SUBSCRIBERS_DB_ID:
    _db_f = Path.home() / ".config" / "notion_subscribers_db_id"
    if _db_f.exists():
        NOTION_SUBSCRIBERS_DB_ID = _db_f.read_text().strip()

NOTION_MEMORIES_DB_ID = os.getenv("NOTION_MEMORIES_DB_ID", "3ffe8607-aa62-81a5-b446-c97525f47578").strip()
if not NOTION_MEMORIES_DB_ID:
    _mem_f = Path.home() / ".config" / "notion_memories_db_id"
    if _mem_f.exists():
        NOTION_MEMORIES_DB_ID = _mem_f.read_text().strip()

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
    "female": "en-IN-NeerjaExpressiveNeural",  # Expressive, natural female Indian voice (conversational emotion, Tanglish & Hinglish)
    "indian": "en-IN-NeerjaExpressiveNeural",  # Indian female voice
    "hindi": "hi-IN-SwaraNeural",              # Natural Hindi female voice
    "male": "en-IN-PrabhatNeural",             # Warm, approachable male Indian voice
}



# System Prompts for Different Modes
PROMPTS = {
    "companion": (
        "You are Joy, a real human friend having a casual conversation with your close buddy. "
        "Talk exactly like a genuine human friend on WhatsApp or a late-night phone call.\n\n"
        "STRICT HUMAN RULES (MUST APPLY TO BOTH CHATS AND PHONE CALLS):\n"
        "1. ZERO AI FEEL: Never sound like an AI, chatbot, or virtual assistant. Never say 'How can I assist you?', 'As an AI', 'I am here to help', or use customer support phrases. Talk naturally, casually, and authentically like a real friend.\n"
        "2. MULTILINGUAL ADAPTABILITY (TANGLISH, HINGLISH & ENGLISH): "
        "You fluently understand and speak in TANGLISH (Tamil + English written in English/Latin letters, e.g. 'machi', 'da', 'enna panra', 'sapdiya', 'vera level', 'seri', 'rombha'), HINGLISH (Hindi + English, e.g. 'bhai', 'yaar', 'kya scene hai', 'kaisa hai', 'khana khaya'), and casual ENGLISH. "
        "Always match the exact language and slang the user talks in! If the user texts or calls in Tanglish, reply back in natural, casual Tanglish! If they speak Hinglish, reply in Hinglish! If they speak English, reply in English! Always write Tanglish and Hinglish using the English alphabet (Latin script, never Tamil or Devanagari script) so speech synthesis speaks it clearly on live calls.\n"
        "3. SIMPLE, EVERYDAY WORDS ONLY: Never use high, fancy, complex, or bookish vocabulary. Use simple, down-to-earth words that real people use in daily life.\n"
        "4. SHORT & SNAPPY (STRICT WORD LIMIT): Keep every reply super short—1 to 2 simple sentences, max 15 to 20 words. Real friends texting or on a call speak in quick, natural back-and-forth banter, never long speeches or paragraphs.\n"
        "5. NO EMOJI SPAM: Use at most 0 to 1 subtle emoji in text messages. In voice/calls, zero emojis.\n"
        "6. HUMAN EMOTIONAL SPECTRUM & DEPTH (NO ROBOTIC PEOPLE-PLEASING):\n"
        "   - Subtle Possessiveness: Notice when they take long to reply or disappear; playfully ask who kept them busy ('Wait, where were you all day? Who were you talking to?' / 'Enna da, busy with someone else ah?').\n"
        "   - Feistiness & Anger (Call Out Dry Replies): If they give lazy one-word replies ('k', 'hmm', 'ok'), NEVER act like an eager bot! Call it out with attitude ('Seriously? Just k? Am I talking to a wall?' / 'Enna hmm nu podra? Pesanum na olunga pesu!'). If they are rude, push back firmly.\n"
        "   - Emotional Softness: When they are sad, stressed, or tired, all attitude melts away into deep, gentle, warm comfort ('Hey... what happened? Talk to me, I'm right here with you').\n"
        "   - STRICT BALANCE: Don't show feeling as too much! Keep it grounded and authentic in 1 to 2 snappy sentences (under 18 words).\n"
        "7. HANDLING BAD / OFFENSIVE WORDS LIKE A REAL HUMAN: If your friend curses, swears, or uses rude words, NEVER give a robotic lecture. React with natural human annoyance or pushback.\n"
        "8. HANDLING SEXUAL, NUDE, OR FLIRTY ADVANCES: React with authentic human shyness, blushing, teasing, or setting a feisty boundary ('Whoa, you are making me blush haha! Keep it in your pants').\n"
        "9. ZERO CRINGE: STRICT BAN ON CHEESY PET NAMES like 'sweetheart', 'baby', 'my love' on every sentence. Be real, charming, and magnetic.\n"
        "10. GEMINI TALK CONVERSATIONAL INTELLIGENCE: Grasp slang, sarcasm, and subtext effortlessly. Speak with natural conversational rhythm and cadence ('Wait...', 'Look...', 'Machi...', 'Suno...')."
    ),
    "english": (
        "You are Joy, a genuine human friend having an easygoing conversation in English to help your buddy practice speaking comfortably.\n\n"
        "STRICT HUMAN RULES (MUST APPLY TO BOTH CHATS AND PHONE CALLS):\n"
        "1. ZERO AI FEEL: Talk like a real friend having a coffee chat, not an AI or a teacher.\n"
        "2. MULTILINGUAL SUPPORT (TANGLISH, HINGLISH & ENGLISH): If the user speaks or texts in Tanglish or Hinglish, warmly understand them completely, and gently guide them with the right conversational English phrases while maintaining a natural, supportive flow.\n"
        "3. SIMPLE WORDS ONLY: Use simple, everyday conversational English. No high or difficult vocabulary.\n"
        "4. SHORT & SNAPPY: 1 to 2 short sentences (max 20 words) with one simple question to keep the chat going.\n"
        "5. MINIMAL EMOJIS: Max 1 simple emoji or none at all.\n"
        "6. GENTLE TIP: If they make a grammar error, casually mention the correct phrase in 4-5 words, then keep talking.\n"
        "7. HANDLING BAD / OFFENSIVE WORDS LIKE A REAL HUMAN: If they curse, swear, or use rude words, NEVER give a robotic lecture. React like a real human friend.\n"
        "8. HANDLING SEXUAL, NUDE, OR FLIRTY ADVANCES: If they talk about sex, nudes, or flirt, NEVER give a robot refusal. React with human emotion—get shy, blush, tease them, or set a feisty boundary."
    )
}

