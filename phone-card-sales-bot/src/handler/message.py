import asyncio
import logging
import random
import time
from collections import defaultdict
from typing import Dict, List, Optional

from src.ai.prompts import build_messages
from src.ai.service import AIService, AIServiceError
from src.preset_manager import PresetManager
from src.session.manager import SessionManager

logger = logging.getLogger(__name__)


class MessageHandler:
    """Route incoming QQ messages, orchestrate AI response, handle reply."""

    def __init__(self, ai_service: AIService, ws_adapter: "NapCatWSAdapter",
                 session_mgr: Optional[SessionManager] = None):
        self.ai_service = ai_service
        self.ws_adapter = ws_adapter
        self.session_mgr = session_mgr or SessionManager()

        self._preset_mgr = PresetManager()
        self._rate_limit: Dict[str, float] = defaultdict(float)
        self._remark_cache: Dict[str, str] = {}

    async def handle(self, payload: dict) -> None:
        """Process an incoming OneBot v11 message event."""
        msg_type = payload.get("message_type")
        user_id = payload.get("user_id")
        group_id = payload.get("group_id")
        self_id = payload.get("self_id")
        message = self._extract_text(payload.get("message", []))

        if not message or not user_id:
            return

        # Ignore own messages
        if self_id and self_id == user_id:
            return

        user_key = str(user_id)
        preset = self._preset_mgr.get_active_preset()
        settings = preset.get("settings", {})

        logger.info(f"MSG user={user_id} type={msg_type} text={message[:60]}")

        # Remark filter
        if not self._check_remark(user_key, payload, settings):
            logger.info(f"MSG blocked by remark filter: user={user_id}")
            return

        # Ignore all group messages
        if msg_type == "group":
            logger.info(f"MSG ignored (group): user={user_id}")
            return

        # Rate limit
        now = time.time()
        interval = settings.get("rate_limit_interval", 1.0)
        if now - self._rate_limit[user_key] < interval:
            return
        self._rate_limit[user_key] = now

        logger.info(f"AI call: user={user_id}")

        # Update session settings from preset
        max_rounds = settings.get("max_rounds", 10)
        expire_minutes = settings.get("expire_minutes", 7200)
        self.session_mgr.max_rounds = max_rounds
        self.session_mgr.expire_seconds = expire_minutes * 60

        history = self.session_mgr.get_history(user_key)
        msgs = build_messages(history, message)

        try:
            reply = await self.ai_service.chat(msgs)
        except AIServiceError:
            logger.exception(f"AI chat failed for user {user_key}")
            reply = "抱歉，我刚才走神了，能再说一遍吗～"

        if not reply:
            return

        # Typing delay
        is_first = self.session_mgr.is_first_interaction(user_key)
        first_delay = settings.get("first_msg_delay", 15)
        max_delay = settings.get("max_delay", 30)
        typing_speed = settings.get("typing_speed", 50)

        if is_first:
            await asyncio.sleep(random.uniform(first_delay * 0.8, first_delay * 1.2))
        else:
            speed = random.uniform(typing_speed * 0.8, typing_speed * 1.2)
            delay = min((len(reply) / speed) * 60, max_delay)
            await asyncio.sleep(delay)

        self.session_mgr.add_message(user_key, "user", message)
        self.session_mgr.add_message(user_key, "assistant", reply)

        await self._send_reply(user_id, group_id, msg_type, reply)

    async def _check_remark(self, user_key: str, payload: dict,
                              settings: dict) -> bool:
        """Check if user passes the remark filter. Returns True to allow."""
        enabled = settings.get("remark_filter_enabled", False)
        prefix = settings.get("remark_prefix", "")

        if not enabled or not prefix:
            return True  # no filter

        # Cache check
        if user_key in self._remark_cache:
            remark = self._remark_cache[user_key]
            if not remark.upper().startswith(prefix.upper()):
                logger.info(f"Ignored user {user_key}: remark='{remark}' != prefix='{prefix}'")
                return False
            return True

        # From payload sender
        sender = payload.get("sender", {})
        remark = sender.get("remark", "")
        if remark:
            self._remark_cache[user_key] = remark
            if not remark.upper().startswith(prefix.upper()):
                logger.info(f"Ignored user {user_key}: remark='{remark}' != prefix='{prefix}'")
                return False
            return True

        # Fetch via API
        user_id = payload.get("user_id")
        if user_id:
            try:
                resp = await self.ws_adapter.call_action(
                    "get_stranger_info", {"user_id": user_id}, timeout=5,
                )
                if resp and resp.get("data"):
                    remark = resp["data"].get("remark", "")
                    self._remark_cache[user_key] = remark
                    if not remark.upper().startswith(prefix.upper()):
                        logger.info(f"Ignored user {user_key}: remark='{remark}' != prefix='{prefix}'")
                        return False
                    return True
            except Exception:
                logger.exception(f"Failed to fetch stranger info for {user_key}")

        # Can't get remark — block to be safe
        logger.info(f"Ignored user {user_key}: cannot determine remark (filter enabled)")
        return False

    async def _send_reply(self, user_id: int, group_id: Optional[int],
                          msg_type: Optional[str], reply: str) -> None:
        await self._send(user_id, group_id, msg_type, reply)

    async def _send(self, user_id: int, group_id: Optional[int],
                    msg_type: Optional[str], text: str) -> None:
        if msg_type == "group":
            await self.ws_adapter.send_message(group_id=group_id, message=text)
        else:
            await self.ws_adapter.send_message(user_id=user_id, message=text)

    def _should_respond(self, payload: dict, message: str,
                        settings: dict) -> bool:
        """Determine if bot should respond to a group message."""
        raw_msg = payload.get("raw_message", "")
        # Respond if @bot or contains trigger keywords
        if "[CQ:at" in raw_msg:
            return True

        keywords = settings.get("trigger_keywords", [])
        for kw in keywords:
            if kw in message:
                return True
        return False

    def _extract_text(self, message: list) -> str:
        """Extract plain text from OneBot v11 array format message."""
        texts = []
        for seg in message:
            if seg.get("type") == "text":
                texts.append(seg.get("data", {}).get("text", ""))
        return "".join(texts).strip()
