import asyncio
import logging
import random
import time
from collections import defaultdict
from typing import Dict, List, Optional

from src.ai.prompts import build_messages
from src.ai.service import AIService, AIServiceError
from src.order.stub import OrderStub
from src.session.manager import SessionManager

logger = logging.getLogger(__name__)


class MessageHandler:
    """Route incoming QQ messages, orchestrate AI response, handle reply."""

    def __init__(self, session_mgr: SessionManager, ai_service: AIService,
                 order_stub: OrderStub, ws_adapter: "NapCatWSAdapter",
                 product: dict, config: dict):
        self.session_mgr = session_mgr
        self.ai_service = ai_service
        self.order_stub = order_stub
        self.ws_adapter = ws_adapter
        self.product = product
        self.config = config

        # Rate limiting: per-user cooldown in seconds
        self._rate_limit: Dict[str, float] = defaultdict(float)
        self.rate_limit_interval = 1.0

        # Remark cache: user_id -> remark (只查一次，后续复用)
        self._remark_cache: Dict[str, str] = {}

        # Purchase intent keywords
        self.purchase_keywords = ["办卡", "买卡", "下单", "怎么办理", "怎么买"]
        self.purchase_fallbacks = ["办", "买", "要"]
        self.purchase_fallback_min_len = 6

    async def handle(self, payload: dict) -> None:
        """Process an incoming OneBot v11 message event."""
        msg_type = payload.get("message_type")
        user_id = payload.get("user_id")
        group_id = payload.get("group_id")
        self_id = payload.get("self_id")
        message = self._extract_text(payload.get("message", []))

        if not message or not user_id:
            return

        # Ignore own messages (self-chat loop prevention)
        if self_id and self_id == user_id:
            return

        # Remark filter: only respond to users whose remark starts with A
        user_key = str(user_id)
        if not await self._check_remark(user_key, payload):
            return

        if msg_type == "group":
            if not self._should_respond(payload, message):
                return

        # Rate limiting
        now = time.time()
        if now - self._rate_limit[user_key] < self.rate_limit_interval:
            return
        self._rate_limit[user_key] = now

        logger.info(f"Handling message from {user_id}: {message[:50]}")

        history = self.session_mgr.get_history(user_key)
        msgs = build_messages(self.product, history, message)

        try:
            reply = await self.ai_service.chat(msgs)
        except AIServiceError:
            logger.exception(f"AI chat failed for user {user_id}")
            reply = "抱歉，我刚才走神了，能再说一遍吗～"

        if not reply:
            return

        # First message: ~15s, subsequent: based on typing speed, max 30s
        if self.session_mgr.is_first_interaction(user_key):
            await asyncio.sleep(random.uniform(12, 18))
        else:
            speed = random.uniform(40, 60)
            delay = min((len(reply) / speed) * 60, 30)
            await asyncio.sleep(delay)

        if self._is_purchase_intent(message):
            order_result = self.order_stub.create_order(user_key, "campus_card")
            reply += f"\n\n{order_result['message']}"

        self.session_mgr.add_message(user_key, "user", message)
        self.session_mgr.add_message(user_key, "assistant", reply)

        await self._send_reply(user_id, group_id, msg_type, reply)

    async def _check_remark(self, user_key: str, payload: dict) -> bool:
        """Check if user's remark starts with A. Returns True to allow."""
        # Check cache first
        if user_key in self._remark_cache:
            remark = self._remark_cache[user_key]
            if not remark.upper().startswith("A"):
                logger.info(f"Ignored user {user_key}: cached remark='{remark}' not A")
                return False
            return True

        # Try sender.remark from payload
        sender = payload.get("sender", {})
        remark = sender.get("remark", "")
        if remark:
            self._remark_cache[user_key] = remark
            if not remark.upper().startswith("A"):
                logger.info(f"Ignored user {user_key}: remark='{remark}' not A")
                return False
            return True

        # Try to fetch via OneBot API
        user_id = payload.get("user_id")
        if user_id:
            try:
                resp = await self.ws_adapter.call_action(
                    "get_stranger_info",
                    {"user_id": user_id},
                    timeout=5,
                )
                if resp and resp.get("data"):
                    remark = resp["data"].get("remark", "")
                    self._remark_cache[user_key] = remark
                    if not remark.upper().startswith("A"):
                        logger.info(f"Ignored user {user_key}: api remark='{remark}' not A")
                        return False
                    return True
            except Exception:
                logger.exception(f"Failed to fetch stranger info for {user_key}")

        # Can't determine remark — block to be safe
        logger.info(f"Ignored user {user_key}: cannot determine remark")
        return False

    def _is_purchase_intent(self, message: str) -> bool:
        """Detect purchase intent with precise matching."""
        for kw in self.purchase_keywords:
            if kw in message:
                return True
        if len(message) >= self.purchase_fallback_min_len:
            for kw in self.purchase_fallbacks:
                if kw in message:
                    return True
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

    def _should_respond(self, payload: dict, message: str) -> bool:
        """Determine if bot should respond to a group message."""
        raw_msg = payload.get("raw_message", "")
        bot_qq = str(self.config.get("bot", {}).get("qq", ""))
        if bot_qq and f"[CQ:at,qq={bot_qq}]" in raw_msg:
            return True

        keywords = self.config.get("bot", {}).get("trigger_keywords", [])
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

    @staticmethod
    def _split_message(text: str, max_len: int) -> List[str]:
        """Split long message at punctuation boundaries near max_len."""
        if len(text) <= max_len:
            return [text]

        segments = []
        remaining = text
        while remaining:
            if len(remaining) <= max_len:
                segments.append(remaining)
                break

            split_at = -1
            for p in ["。", "！", "？", "\n", "，", "；"]:
                idx = remaining.rfind(p, 0, max_len)
                if idx > split_at:
                    split_at = idx

            if split_at <= 0:
                split_at = max_len
                segments.append(remaining[:split_at])
                remaining = remaining[split_at:]
            else:
                segments.append(remaining[:split_at + 1])
                remaining = remaining[split_at + 1:]

        return segments
