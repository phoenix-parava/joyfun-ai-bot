"""
Lightweight WebRTC Signaling Server & Matchmaking Router
Zero Audio Buffering in RAM: Strictly exchanges SDP offers, answers, ICE candidates, and icebreaker cards.
"""

import json
import time
import asyncio
import logging
from typing import Dict, List, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from config import get_icebreaker_list
from security import sanitize_pii
from database import (
    get_user,
    consume_quota,
    get_user_quota_summary
)
from ai_service import generate_ai_text_reply

logger = logging.getLogger("WebRTCSignaling")

class PeerSession:
    def __init__(self, ws: WebSocket, user_id: int, pseudonym: str, language: str, modality: str, preference: str):
        self.ws = ws
        self.user_id = user_id
        self.pseudonym = pseudonym
        self.language = language
        self.modality = modality            # 'voice' or 'text'
        self.preference = preference        # 'real_or_ai', 'real_only', 'ai_only'
        self.matched_peer: Optional["PeerSession"] = None
        self.room_id: Optional[str] = None
        self.is_ai_mode = False
        self.connected_at = time.time()
        self.call_start_time: Optional[float] = None
        self.ai_history: List[Dict[str, str]] = []
        self.icebreaker_idx = 0

class SignalingManager:
    def __init__(self):
        # Matchmaking queues: { (modality, language): [PeerSession, ...] }
        self.queues: Dict[tuple, List[PeerSession]] = {}
        # Active connected sessions: { user_id: PeerSession }
        self.active_peers: Dict[int, PeerSession] = {}
        # Lock for thread-safe matching
        self._lock = asyncio.Lock()

    async def register_peer(self, ws: WebSocket, user_id: int) -> PeerSession:
        user = await get_user(user_id) or {}
        pseudonym = user.get("pseudonym", f"Peer-{str(user_id)[-4:]}")
        language = user.get("language", "tanglish")
        modality = user.get("modality", "voice")
        preference = user.get("partner_preference", "real_or_ai")

        peer = PeerSession(ws, user_id, pseudonym, language, modality, preference)
        self.active_peers[user_id] = peer
        return peer

    async def unregister_peer(self, peer: PeerSession):
        async with self._lock:
            # Remove from queues
            for q in self.queues.values():
                if peer in q:
                    q.remove(peer)
            self.active_peers.pop(peer.user_id, None)

        # Notify matched human peer if connected
        if peer.matched_peer and not peer.is_ai_mode:
            other = peer.matched_peer
            peer.matched_peer = None
            other.matched_peer = None
            try:
                await other.ws.send_json({
                    "type": "diagnostic",
                    "code": "PEER_DROPPED",
                    "message": "Your partner disconnected. Returning to matchmaking..."
                })
                # Settle voice quota consumed
                if peer.call_start_time:
                    duration = int(time.time() - peer.call_start_time)
                    await consume_quota(peer.user_id, "p2p_voice", duration)
                    await consume_quota(other.user_id, "p2p_voice", duration)
            except Exception:
                pass

    async def join_matchmaking(self, peer: PeerSession):
        """Enqueues user for P2P matching or transitions to AI partner."""
        if peer.preference == "ai_only":
            await self._start_ai_session(peer)
            return

        key = (peer.modality, peer.language)
        async with self._lock:
            if key not in self.queues:
                self.queues[key] = []

            # Check if there is an eligible peer in queue
            available_peer: Optional[PeerSession] = None
            for candidate in list(self.queues[key]):
                if candidate.user_id != peer.user_id:
                    available_peer = candidate
                    self.queues[key].remove(candidate)
                    break

            if available_peer:
                # Form P2P Match
                room_id = f"room_{min(peer.user_id, available_peer.user_id)}_{max(peer.user_id, available_peer.user_id)}_{int(time.time())}"
                peer.matched_peer = available_peer
                available_peer.matched_peer = peer
                peer.room_id = room_id
                available_peer.room_id = room_id
                peer.is_ai_mode = False
                available_peer.is_ai_mode = False
                peer.call_start_time = time.time()
                available_peer.call_start_time = time.time()

                # Notify initiator (peer A) to generate SDP Offer
                await peer.ws.send_json({
                    "type": "matched",
                    "role": "initiator",
                    "room_id": room_id,
                    "peer_pseudonym": available_peer.pseudonym,
                    "language": peer.language,
                    "modality": peer.modality,
                    "is_human": True
                })

                # Notify receiver (peer B)
                await available_peer.ws.send_json({
                    "type": "matched",
                    "role": "receiver",
                    "room_id": room_id,
                    "peer_pseudonym": peer.pseudonym,
                    "language": available_peer.language,
                    "modality": available_peer.modality,
                    "is_human": True
                })
                logger.info(f"P2P Match Formed: {peer.pseudonym} ({peer.user_id}) <-> {available_peer.pseudonym} ({available_peer.user_id})")
                return

            # Otherwise, add to queue
            self.queues[key].append(peer)

        # Notify user that matchmaking is in progress and offer Instant AI Warm-Up
        await peer.ws.send_json({
            "type": "queued",
            "message": "Searching for a partner online...",
            "warmup_available": True
        })

        # Launch matching timeout watcher
        asyncio.create_task(self._match_timeout_watcher(peer, key))

    async def _match_timeout_watcher(self, peer: PeerSession, key: tuple):
        """Watches queue wait time. If timeout expires and user allows AI fallback, switches smoothly."""
        await asyncio.sleep(15.0)
        async with self._lock:
            if key in self.queues and peer in self.queues[key] and not peer.matched_peer:
                self.queues[key].remove(peer)
                needs_fallback = (peer.preference == "real_or_ai")

        if needs_fallback and not peer.matched_peer:
            await peer.ws.send_json({
                "type": "diagnostic",
                "code": "MATCH_TIMEOUT_NO_PEER",
                "message": "No human partner found right now. Connecting to AI Companion..."
            })
            await self._start_ai_session(peer)

    async def _start_ai_session(self, peer: PeerSession):
        peer.is_ai_mode = True
        peer.matched_peer = None
        peer.call_start_time = time.time()
        peer.ai_history = []

        await peer.ws.send_json({
            "type": "matched",
            "role": "initiator",
            "room_id": f"ai_room_{peer.user_id}",
            "peer_pseudonym": "Joy AI",
            "language": peer.language,
            "modality": peer.modality,
            "is_human": False
        })

        # Send initial warm greeting in user's language
        greeting = await generate_ai_text_reply(
            "Hello! I am ready to talk.",
            language=peer.language,
            pseudonym=peer.pseudonym,
            is_voice=(peer.modality == "voice")
        )
        peer.ai_history.append({"role": "model", "content": greeting})

        await peer.ws.send_json({
            "type": "text_message",
            "sender": "Joy AI",
            "text": greeting,
            "is_ai": True
        })

    async def handle_peer_message(self, peer: PeerSession, data: dict):
        msg_type = data.get("type")

        # 1. Matchmaking Start
        if msg_type == "join_queue":
            await self.join_matchmaking(peer)

        # 2. Cancel Queue
        elif msg_type == "leave_queue":
            key = (peer.modality, peer.language)
            async with self._lock:
                if key in self.queues and peer in self.queues[key]:
                    self.queues[key].remove(peer)
            await peer.ws.send_json({"type": "queue_cancelled"})

        # 3. WebRTC SDP Signaling (Offer, Answer)
        elif msg_type in ("offer", "answer"):
            if peer.matched_peer:
                await peer.matched_peer.ws.send_json({
                    "type": msg_type,
                    "sdp": data.get("sdp")
                })

        # 4. WebRTC ICE Candidate Exchange
        elif msg_type == "ice_candidate":
            if peer.matched_peer:
                await peer.matched_peer.ws.send_json({
                    "type": "ice_candidate",
                    "candidate": data.get("candidate")
                })

        # 5. Bilingual Topic Icebreaker Deck Request
        elif msg_type == "request_icebreaker":
            deck = get_icebreaker_list(peer.language)
            card = deck[peer.icebreaker_idx % len(deck)]
            peer.icebreaker_idx += 1

            # Broadcast to both peers
            payload = {"type": "icebreaker_card", "topic": card}
            await peer.ws.send_json(payload)
            if peer.matched_peer:
                await peer.matched_peer.ws.send_json(payload)

        # 5b. Instant AI Warm-Up while in queue
        elif msg_type == "warmup_message":
            user_text = data.get("text", "")
            is_blocked, clean_text, _ = sanitize_pii(user_text)
            if not is_blocked and clean_text:
                peer.ai_history.append({"role": "user", "content": clean_text})
                ai_reply = await generate_ai_text_reply(
                    clean_text,
                    language=peer.language,
                    pseudonym=peer.pseudonym,
                    history=peer.ai_history,
                    is_voice=(peer.modality == "voice")
                )
                peer.ai_history.append({"role": "model", "content": ai_reply})
                await peer.ws.send_json({
                    "type": "warmup_reply",
                    "text": ai_reply
                })

        # 6. Real-Time Text Messages (with PII sanitizer)
        elif msg_type == "text_message":
            raw_text = data.get("text", "")
            is_blocked, clean_text, violation = sanitize_pii(raw_text)

            if is_blocked:
                await peer.ws.send_json({
                    "type": "diagnostic",
                    "code": "PII_BLOCKED",
                    "message": f"🚫 Message blocked: Sharing {violation or 'personal info'} is strictly prohibited."
                })
                return

            if peer.is_ai_mode:
                # Deduct AI Text quota
                allowed, rem, limit = await consume_quota(peer.user_id, "ai_text", 1)
                if not allowed:
                    await peer.ws.send_json({
                        "type": "diagnostic",
                        "code": "QUOTA_EXHAUSTED",
                        "message": "Daily AI Text quota exhausted (50 messages/day)."
                    })
                    return

                peer.ai_history.append({"role": "user", "content": clean_text})
                ai_reply = await generate_ai_text_reply(
                    clean_text,
                    language=peer.language,
                    pseudonym=peer.pseudonym,
                    history=peer.ai_history,
                    is_voice=False
                )
                peer.ai_history.append({"role": "model", "content": ai_reply})

                await peer.ws.send_json({
                    "type": "text_message",
                    "sender": "Joy AI",
                    "text": ai_reply,
                    "is_ai": True
                })
            elif peer.matched_peer:
                # Forward to human peer
                await peer.matched_peer.ws.send_json({
                    "type": "text_message",
                    "sender": peer.pseudonym,
                    "text": clean_text,
                    "is_ai": False
                })

        # 7. End Call / End Chat
        elif msg_type == "end_session":
            if peer.matched_peer:
                other = peer.matched_peer
                peer.matched_peer = None
                other.matched_peer = None
                await other.ws.send_json({
                    "type": "session_ended",
                    "message": "Your partner ended the session."
                })
            peer.is_ai_mode = False
            await peer.ws.send_json({"type": "session_ended", "message": "Session ended."})

        # 8. Report Diagnostics
        elif msg_type == "report_error":
            err_code = data.get("code", "UNKNOWN")
            logger.warning(f"Client reported diagnostic [{err_code}] for user {peer.user_id}")

signaling_hub = SignalingManager()
