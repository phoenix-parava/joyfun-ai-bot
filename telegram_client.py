"""
Joy Bot - Lightweight Async Telegram Client (Powered by aiohttp)
High-performance, zero-framework-bloat async client.
"""

import json
import asyncio
import logging
import aiohttp
from typing import Optional, Dict, Any

logger = logging.getLogger("JoyTelegram")

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

    async def send_message(self, chat_id: int, text: str, reply_markup: Optional[dict] = None, parse_mode: Optional[str] = "Markdown", protect_content: bool = True) -> dict:
        session = await self.get_session()
        payload = {
            "chat_id": chat_id,
            "text": text,
            "protect_content": protect_content
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        if parse_mode:
            payload["parse_mode"] = parse_mode
            
        for attempt in range(3):
            async with session.post(f"{self.api_url}/sendMessage", json=payload) as resp:
                result = await resp.json()
                # Check for Telegram FloodWait / RetryAfter
                if result.get("error_code") == 429:
                    retry_after = result.get("parameters", {}).get("retry_after", 1)
                    wait_time = min(retry_after, 5)
                    logger.warning(f"Telegram FloodWait 429: Sleeping {wait_time}s before retry")
                    await asyncio.sleep(wait_time)
                    continue

                # Fallback if markdown parsing fails due to special characters
                if not result.get("ok") and parse_mode:
                    payload.pop("parse_mode", None)
                    async with session.post(f"{self.api_url}/sendMessage", json=payload) as retry_resp:
                        r2 = await retry_resp.json()
                        if not r2.get("ok"):
                            logger.error(f"Telegram API sendMessage error (retry without parse_mode): {r2}")
                        return r2
                if not result.get("ok"):
                    logger.error(f"Telegram API sendMessage error: {result}")
                return result
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
            
        for attempt in range(3):
            async with session.post(f"{self.api_url}/editMessageText", json=payload) as resp:
                result = await resp.json()
                # Check for Telegram FloodWait / RetryAfter
                if result.get("error_code") == 429:
                    retry_after = result.get("parameters", {}).get("retry_after", 1)
                    wait_time = min(retry_after, 5)
                    logger.warning(f"Telegram FloodWait 429 in edit: Sleeping {wait_time}s before retry")
                    await asyncio.sleep(wait_time)
                    continue

                # If message is not modified, treat as clean success (do not throw or error)
                desc = str(result.get("description", "")).lower()
                if "message is not modified" in desc:
                    return {"ok": True, "result": True, "description": "Message is already up to date"}

                if not result.get("ok") and parse_mode:
                    payload.pop("parse_mode", None)
                    async with session.post(f"{self.api_url}/editMessageText", json=payload) as retry_resp:
                        r2 = await retry_resp.json()
                        if "message is not modified" in str(r2.get("description", "")).lower():
                            return {"ok": True, "result": True, "description": "Message is already up to date"}
                        return r2
                return result
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
        data.add_field("protect_content", "true")
        if caption:
            data.add_field("caption", caption)
        if reply_markup:
            data.add_field("reply_markup", json.dumps(reply_markup))
            
        async with session.post(f"{self.api_url}/sendAudio", data=data) as resp:
            return await resp.json()

    async def send_photo(self, chat_id: int, photo_bytes: bytes, filename: str = "joy_pic.jpg", caption: Optional[str] = None, reply_markup: Optional[dict] = None, parse_mode: Optional[str] = None) -> dict:
        session = await self.get_session()
        data = aiohttp.FormData()
        data.add_field("chat_id", str(chat_id))
        data.add_field("photo", photo_bytes, filename=filename, content_type="image/jpeg")
        data.add_field("protect_content", "true")
        if caption:
            data.add_field("caption", caption)
        if reply_markup:
            data.add_field("reply_markup", json.dumps(reply_markup))
        if parse_mode:
            data.add_field("parse_mode", parse_mode)
            
        async with session.post(f"{self.api_url}/sendPhoto", data=data) as resp:
            result = await resp.json()
            if not result.get("ok") and parse_mode:
                # Retry without parse mode if markdown parsing failed in caption
                data2 = aiohttp.FormData()
                data2.add_field("chat_id", str(chat_id))
                data2.add_field("photo", photo_bytes, filename=filename, content_type="image/jpeg")
                data2.add_field("protect_content", "true")
                if caption:
                    data2.add_field("caption", caption)
                if reply_markup:
                    data2.add_field("reply_markup", json.dumps(reply_markup))
                async with session.post(f"{self.api_url}/sendPhoto", data=data2) as retry_resp:
                    return await retry_resp.json()
            return result

    async def send_document(self, chat_id: int, file_bytes: bytes, filename: str = "backup.json", caption: Optional[str] = None, reply_markup: Optional[dict] = None) -> dict:
        session = await self.get_session()
        data = aiohttp.FormData()
        data.add_field("chat_id", str(chat_id))
        data.add_field("document", file_bytes, filename=filename, content_type="application/octet-stream")
        data.add_field("protect_content", "true")
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

    async def set_chat_menu_button(self, menu_button: Optional[dict] = None, chat_id: Optional[int] = None) -> dict:
        session = await self.get_session()
        payload = {}
        if chat_id:
            payload["chat_id"] = chat_id
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

    async def set_my_description(self, description: str, language_code: Optional[str] = None) -> dict:
        session = await self.get_session()
        payload = {"description": str(description)[:512]}
        if language_code:
            payload["language_code"] = language_code
        async with session.post(f"{self.api_url}/setMyDescription", json=payload) as resp:
            return await resp.json()

    async def set_my_short_description(self, short_description: str, language_code: Optional[str] = None) -> dict:
        session = await self.get_session()
        payload = {"short_description": str(short_description)[:120]}
        if language_code:
            payload["language_code"] = language_code
        async with session.post(f"{self.api_url}/setMyShortDescription", json=payload) as resp:
            return await resp.json()

    async def create_invoice_link(
        self,
        title: str,
        description: str,
        payload: str,
        currency: str,
        prices: list
    ) -> dict:
        session = await self.get_session()
        data = {
            "title": title,
            "description": description,
            "payload": payload,
            "currency": currency,
            "prices": prices
        }
        async with session.post(f"{self.api_url}/createInvoiceLink", json=data) as resp:
            return await resp.json()

    async def answer_pre_checkout_query(self, pre_checkout_query_id: str, ok: bool = True, error_message: Optional[str] = None) -> dict:
        session = await self.get_session()
        data = {"pre_checkout_query_id": pre_checkout_query_id, "ok": ok}
        if error_message:
            data["error_message"] = error_message
        async with session.post(f"{self.api_url}/answerPreCheckoutQuery", json=data) as resp:
            return await resp.json()

    async def send_voice_file_id(self, chat_id: int, file_id: str, caption: Optional[str] = None, reply_markup: Optional[dict] = None) -> dict:
        session = await self.get_session()
        payload = {"chat_id": chat_id, "voice": file_id, "protect_content": True}
        if caption:
            payload["caption"] = caption
        if reply_markup:
            payload["reply_markup"] = reply_markup
        async with session.post(f"{self.api_url}/sendVoice", json=payload) as resp:
            return await resp.json()

    async def send_photo_file_id(self, chat_id: int, file_id: str, caption: Optional[str] = None, reply_markup: Optional[dict] = None) -> dict:
        session = await self.get_session()
        payload = {"chat_id": chat_id, "photo": file_id, "protect_content": True}
        if caption:
            payload["caption"] = caption
        if reply_markup:
            payload["reply_markup"] = reply_markup
        async with session.post(f"{self.api_url}/sendPhoto", json=payload) as resp:
            return await resp.json()

    async def send_sticker_file_id(self, chat_id: int, file_id: str, reply_markup: Optional[dict] = None) -> dict:
        session = await self.get_session()
        payload = {"chat_id": chat_id, "sticker": file_id, "protect_content": True}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        async with session.post(f"{self.api_url}/sendSticker", json=payload) as resp:
            return await resp.json()

    async def delete_webhook(self, drop_pending_updates: bool = False) -> dict:
        session = await self.get_session()
        payload = {"drop_pending_updates": drop_pending_updates}
        async with session.post(f"{self.api_url}/deleteWebhook", json=payload) as resp:
            return await resp.json()

    async def get_available_gifts(self) -> dict:
        session = await self.get_session()
        async with session.get(f"{self.api_url}/getAvailableGifts") as resp:
            return await resp.json()




