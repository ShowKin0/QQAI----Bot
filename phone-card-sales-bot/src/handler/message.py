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

        # Purchase intent keywords (with word-boundary matching for Chinese)
        self.purchase_keywords = ["办卡", "买卡", "下单", "怎么办理", "怎么买"]
        self.purchase_fallbacks = ["办", "买", "要"]
        self.purchase_fallback_min_len = 6  # only apply fallbacks for longer messages

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

        # Only respond to users whose ID starts with A (case-insensitive)
        user_key = str(user_id)
        if not user_key.upper().startswith("A"):
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

        if self._is_purchase_intent(message):
            order_result = self.order_stub.create_order(user_key, "campus_card")
            reply += f"\n\n{order_result['message']}"

        self.session_mgr.add_message(user_key, "user", message)
        self.session_mgr.add_message(user_key, "assistant", reply)

        await self._send_reply(user_id, group_id, msg_type, reply)

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
        settings = self.config.get("human_like", {})
        split_enabled = settings.get("enable_message_split", True)
        max_len = settings.get("max_segment_length", 80)
        base_delay = settings.get("split_delay", 0.8)

        if split_enabled and len(reply) > max_len:
            segments = self._split_message(reply, max_len)
            for i, seg in enumerate(segments):
                stripped = seg.strip()
                if stripped:
                    await self._send(user_id, group_id, msg_type, stripped)
                    if i < len(segments) - 1:
                        jitter = random.uniform(-0.3, 0.3)
                        await asyncio.sleep(max(0.3, base_delay + jitter))
        else:
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
