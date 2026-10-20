"""
Joy Bot - Lightweight Async Telegram Client (Powered by aiohttp)
High-performance, zero-framework-bloat async client.
"""

import json
import aiohttp
from typing import Optional, Dict, Any

class TelegramClient:
    def __init__(self, token: str):
        self.token = token
        self.api_url = f"https://api.telegram.org/bot{token}"
        self.file_url = f"https://api.telegram.org/file/bot{token}"
        self.session: Optional[aiohttp.ClientSession] = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def get_me(self) -> dict:
        session = await self.get_session()
        async with session.get(f"{self.api_url}/getMe") as resp:
            return await resp.json()

    async def get_updates(self, offset: Optional[int] = None, timeout: int = 25) -> dict:
        session = await self.get_session()
        params = {"timeout": timeout}
        if offset is not None:
            params["offset"] = offset
        async with session.get(f"{self.api_url}/getUpdates", params=params) as resp:
            return await resp.json()

    async def send_message(self, chat_id: int, text: str, reply_markup: Optional[dict] = None, parse_mode: Optional[str] = "Markdown") -> dict:
        session = await self.get_session()
        payload = {
            "chat_id": chat_id,
            "text": text
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        if parse_mode:
            payload["parse_mode"] = parse_mode
            
        async with session.post(f"{self.api_url}/sendMessage", json=payload) as resp:
            # Fallback if markdown parsing fails due to special characters
            result = await resp.json()
            if not result.get("ok") and parse_mode:
                payload.pop("parse_mode", None)
                async with session.post(f"{self.api_url}/sendMessage", json=payload) as retry_resp:
                    return await retry_resp.json()
            return result

    async def edit_message_text(self, chat_id: int, message_id: int, text: str, reply_markup: Optional[dict] = None, parse_mode: Optional[str] = "Markdown") -> dict:
        session = await self.get_session()
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        if parse_mode:
            payload["parse_mode"] = parse_mode
            
        async with session.post(f"{self.api_url}/editMessageText", json=payload) as resp:
            result = await resp.json()
            if not result.get("ok") and parse_mode:
                payload.pop("parse_mode", None)
                async with session.post(f"{self.api_url}/editMessageText", json=payload) as retry_resp:
                    return await retry_resp.json()
            return result

    async def delete_message(self, chat_id: int, message_id: int) -> dict:
        session = await self.get_session()
        payload = {
            "chat_id": chat_id,
            "message_id": message_id
        }
        try:
            async with session.post(f"{self.api_url}/deleteMessage", json=payload) as resp:
                return await resp.json()
        except Exception:
            return {"ok": False}

    async def send_chat_action(self, chat_id: int, action: str = "typing") -> dict:
        session = await self.get_session()
        payload = {"chat_id": chat_id, "action": action}
        async with session.post(f"{self.api_url}/sendChatAction", json=payload) as resp:
            return await resp.json()

    async def send_audio(self, chat_id: int, audio_bytes: bytes, filename: str = "joy_voice.mp3", caption: Optional[str] = None, performer: str = "Joy", title: str = "Voice Message", reply_markup: Optional[dict] = None) -> dict:
        session = await self.get_session()
        data = aiohttp.FormData()
        data.add_field("chat_id", str(chat_id))
        data.add_field("audio", audio_bytes, filename=filename, content_type="audio/mpeg")
        data.add_field("performer", performer)
        data.add_field("title", title)
        if caption:
            data.add_field("caption", caption)
        if reply_markup:
            data.add_field("reply_markup", json.dumps(reply_markup))
            
        async with session.post(f"{self.api_url}/sendAudio", data=data) as resp:
            return await resp.json()

    async def send_document(self, chat_id: int, file_bytes: bytes, filename: str = "backup.json", caption: Optional[str] = None, reply_markup: Optional[dict] = None) -> dict:
        session = await self.get_session()
        data = aiohttp.FormData()
        data.add_field("chat_id", str(chat_id))
        data.add_field("document", file_bytes, filename=filename, content_type="application/octet-stream")
        if caption:
            data.add_field("caption", caption)
        if reply_markup:
            data.add_field("reply_markup", json.dumps(reply_markup))
            
        async with session.post(f"{self.api_url}/sendDocument", data=data) as resp:
            return await resp.json()

    async def get_file_bytes(self, file_id: str) -> Optional[bytes]:
        session = await self.get_session()
        # 1. Get file path
        async with session.get(f"{self.api_url}/getFile", params={"file_id": file_id}) as resp:
            data = await resp.json()
            if not data.get("ok"):
                return None
            file_path = data["result"].get("file_path")
            if not file_path:
                return None
                
        # 2. Download file contents
        async with session.get(f"{self.file_url}/{file_path}") as file_resp:
            if file_resp.status == 200:
                return await file_resp.read()
            return None

    async def answer_callback_query(self, callback_query_id: str, text: Optional[str] = None) -> dict:
        session = await self.get_session()
        payload = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        async with session.post(f"{self.api_url}/answerCallbackQuery", json=payload) as resp:
            return await resp.json()

    async def set_chat_menu_button(self, menu_button: Optional[dict] = None) -> dict:
        session = await self.get_session()
        payload = {}
        if menu_button:
            payload["menu_button"] = menu_button
        else:
            payload["menu_button"] = {"type": "commands"}
        async with session.post(f"{self.api_url}/setChatMenuButton", json=payload) as resp:
            return await resp.json()

    async def set_my_commands(self, commands: list) -> dict:
        session = await self.get_session()
        payload = {"commands": commands}
        async with session.post(f"{self.api_url}/setMyCommands", json=payload) as resp:
            return await resp.json()


