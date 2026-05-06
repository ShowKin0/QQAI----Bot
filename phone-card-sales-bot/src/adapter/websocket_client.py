import json
import asyncio
import logging
import uuid
from typing import Callable, Awaitable, Dict, Optional

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
        self._pending: Dict[str, asyncio.Future] = {}
        self._conn_id = 0  # prevent stale handlers from clobbering _ws

    async def start(self) -> None:
        """Start WebSocket server and wait for NapCatQQ connection."""

        async def handler(websocket: WebSocketServerProtocol):
            self._conn_id += 1
            conn_id = self._conn_id
            self._ws = websocket
            logger.info(f"[{conn_id}] NapCatQQ connected")
            try:
                async for raw in websocket:
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        logger.warning(f"[{conn_id}] Received malformed JSON, skipping")
                        continue

                    echo = data.get("echo")
                    if echo and echo in self._pending:
                        future = self._pending.pop(echo)
                        future.set_result(data)
                        continue

                    logger.debug(f"[{conn_id}] Received: post_type={data.get('post_type')}, "
                                 f"msg_type={data.get('message_type')}, "
                                 f"user_id={data.get('user_id')}")
                    if self.on_message:
                        asyncio.create_task(self._safe_handle(data))
            except websockets.exceptions.WebSocketException:
                logger.warning(f"[{conn_id}] NapCatQQ connection lost")
                # Only clobber _ws if we're still the active connection
                if self._conn_id == conn_id:
                    self._ws = None
                    self._fail_pending()
                else:
                    logger.debug(f"[{conn_id}] stale connection, ignored")

        async with websockets.serve(handler, self.host, self.port):
            logger.info(f"WS server started on ws://{self.host}:{self.port}{self.path}")
            await asyncio.Future()  # run forever

    def _fail_pending(self) -> None:
        """Fail all pending actions when connection drops."""
        for echo, future in list(self._pending.items()):
            if not future.done():
                future.set_exception(ConnectionError("NapCatQQ disconnected"))
            del self._pending[echo]

    async def _safe_handle(self, data: dict) -> None:
        """Call on_message callback, catching and logging exceptions."""
        if self.on_message:
            try:
                await self.on_message(data)
            except Exception:
                logger.exception("Unhandled error in message handler")

    async def call_action(self, action: str, params: Optional[dict] = None,
                          timeout: float = 10.0) -> Optional[dict]:
        """Send a OneBot v11 action and wait for the response."""
        if not self._ws:
            logger.error("No NapCatQQ connection available")
            return None

        echo = str(uuid.uuid4())
        payload = {
            "action": action,
            "params": params or {},
            "echo": echo,
        }

        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[echo] = future

        try:
            await self._ws.send(json.dumps(payload))
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            self._pending.pop(echo, None)
            logger.warning(f"Action {action} timed out after {timeout}s")
            return None
        except websockets.exceptions.WebSocketException:
            self._pending.pop(echo, None)
            logger.exception("WebSocket error during call_action")
            self._ws = None
            return None

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
