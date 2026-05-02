import json
import asyncio
import logging
from typing import Callable, Awaitable, Optional

import websockets
from websockets.server import WebSocketServerProtocol

logger = logging.getLogger(__name__)


class NapCatWSAdapter:
    """WebSocket server that receives/sends messages via NapCatQQ (OneBot v11)."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765,
                 path: str = "/onebot/v11/ws"):
        self.host = host
        self.port = port
        self.path = path
        self._ws: Optional[WebSocketServerProtocol] = None
        self.on_message: Optional[Callable[[dict], Awaitable[None]]] = None

    async def start(self) -> None:
        """Start WebSocket server and wait for NapCatQQ connection."""

        async def handler(websocket: WebSocketServerProtocol):
            self._ws = websocket
            logger.info("NapCatQQ connected")
            try:
                async for raw in websocket:
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        logger.warning("Received malformed JSON from NapCatQQ, skipping")
                        continue

                    logger.debug("Received: %s", data)
                    if self.on_message:
                        asyncio.create_task(self._safe_handle(data))
            except websockets.exceptions.WebSocketException:
                logger.warning("NapCatQQ connection lost")
                self._ws = None

        async with websockets.serve(handler, self.host, self.port):
            logger.info(f"WS server started on ws://{self.host}:{self.port}{self.path}")
            await asyncio.Future()  # run forever

    async def _safe_handle(self, data: dict) -> None:
        """Call on_message callback, catching and logging exceptions."""
        if self.on_message:
            try:
                await self.on_message(data)
            except Exception:
                logger.exception("Unhandled error in message handler")

    async def send_message(self, user_id: Optional[int] = None,
                           group_id: Optional[int] = None,
                           message: str = "") -> bool:
        """Send a QQ message via OneBot v11 API (array format to prevent CQ injection)."""
        if not self._ws:
            logger.error("No NapCatQQ connection available")
            return False

        payload = {
            "action": "send_msg",
            "params": {
                # Use array format so NapCat won't parse CQ codes in AI output
                "message": [{"type": "text", "data": {"text": message}}],
            },
        }
        if group_id:
            payload["params"]["group_id"] = group_id
        elif user_id:
            payload["params"]["user_id"] = user_id

        try:
            await self._ws.send(json.dumps(payload))
            return True
        except websockets.exceptions.WebSocketException:
            logger.exception("Failed to send message over WebSocket")
            self._ws = None
            return False
