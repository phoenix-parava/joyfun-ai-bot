"""
Joy Bot - Gemini Flash Multi-Modal Intelligence Engine
Handles both text and direct audio voice input with context memory.
"""

import os
from typing import List, Dict, Optional, Tuple
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, PROMPTS

# Initialize Gemini Client
client = None
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)

def get_gemini_client() -> genai.Client:
    global client
    if client is None:
        key = os.getenv("GEMINI_API_KEY", "")
        if not key:
            raise ValueError("GEMINI_API_KEY is not configured in .env or environment!")
        client = genai.Client(api_key=key)
    return client

def generate_text_reply(user_text: str, mode: str = "companion", history: List[Dict[str, str]] = None) -> str:
    """Generates a conversational response to text input."""
    ai_client = get_gemini_client()
    system_instruction = PROMPTS.get(mode, PROMPTS["companion"])
    
    # Build conversational history
    conversation_context = ""
    if history:
        for turn in history:
            role_label = "User" if turn["role"] == "user" else "Joy"
            conversation_context += f"{role_label}: {turn['content']}\n"
    
    prompt = (
        f"{conversation_context}"
        f"User: {user_text}\n"
        f"Joy:"
    )
    
    response = ai_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.8,
            max_output_tokens=300
        )
    )
    
    return response.text.strip() if response.text else "Hey! I'm here. What's on your mind?"

def generate_voice_reply(audio_bytes: bytes, mime_type: str = "audio/ogg", mode: str = "companion", history: List[Dict[str, str]] = None) -> Tuple[str, str]:
    """
    Directly processes audio bytes from Telegram voice note using Gemini's native audio listening.
    Returns: (transcript_summary, joy_reply)
    """
    ai_client = get_gemini_client()
    system_instruction = PROMPTS.get(mode, PROMPTS["companion"])
    
    # Build conversational history
    conversation_context = ""
    if history:
        for turn in history:
            role_label = "User" if turn["role"] == "user" else "Joy"
            conversation_context += f"{role_label}: {turn['content']}\n"
    
    audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
    
    instruction_prompt = (
        f"Listen carefully to this voice note from the user.\n"
        f"Recent conversation:\n{conversation_context}\n\n"
        f"Task:\n"
        f"1. Transcribe what the user said in the audio.\n"
        f"2. Respond directly as Joy according to your persona.\n"
        f"Format your output exactly as:\n"
        f"TRANSCRIPT: <what the user said in the audio>\n"
        f"REPLY: <your friendly conversational reply to speak back>"
    )
    
    response = ai_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[audio_part, instruction_prompt],
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.8,
            max_output_tokens=350
        )
    )
    
    raw_text = response.text.strip() if response.text else ""
    
    transcript = "Voice Note"
    reply = raw_text
    
    if "TRANSCRIPT:" in raw_text and "REPLY:" in raw_text:
        try:
            parts = raw_text.split("REPLY:", 1)
            transcript_part = parts[0].replace("TRANSCRIPT:", "").strip()
            reply_part = parts[1].strip()
            if transcript_part:
                transcript = transcript_part
            if reply_part:
                reply = reply_part
        except Exception:
            pass
            
    return transcript, reply
