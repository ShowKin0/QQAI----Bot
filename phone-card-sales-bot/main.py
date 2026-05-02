import asyncio
import logging
import signal
from pathlib import Path

from dotenv import load_dotenv

from src.adapter.websocket_client import NapCatWSAdapter
from src.ai.service import AIService
from src.config_loader import load_config, ConfigError
from src.handler.message import MessageHandler
from src.order.stub import OrderStub
from src.session.manager import SessionManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_shutdown_event = asyncio.Event()


def _handle_signal():
    """Signal handler to trigger graceful shutdown."""
    logger.info("Received shutdown signal, shutting down gracefully...")
    _shutdown_event.set()


def main():
    load_dotenv()

    base_dir = Path(__file__).parent
    try:
        config = load_config(base_dir)
    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        return

    settings = config["settings"]

    ws_adapter = NapCatWSAdapter(
        host=settings["server"]["host"],
        port=settings["server"]["port"],
        path=settings["server"].get("ws_path", "/onebot/v11/ws"),
    )

    ai_service = AIService(
        api_key=settings["llm"]["api_key"],
        base_url=settings["llm"]["base_url"],
        model=settings["llm"]["model"],
        temperature=settings["llm"].get("temperature", 0.7),
        max_tokens=settings["llm"].get("max_tokens", 1024),
    )

    session_mgr = SessionManager(
        max_rounds=settings["session"].get("max_rounds", 10),
        expire_minutes=settings["session"].get("expire_minutes", 30),
    )

    order_stub = OrderStub()
    product = config["product"]

    handler = MessageHandler(
        session_mgr=session_mgr,
        ai_service=ai_service,
        order_stub=order_stub,
        ws_adapter=ws_adapter,
        product=product,
        config=settings,
    )

    ws_adapter.on_message = handler.handle

    logger.info("Starting Phone Card Sales Bot...")
    logger.info(f"LLM: {settings['llm']['model']} @ {settings['llm']['base_url']}")
    logger.info(f"WS server: ws://{settings['server']['host']}:{settings['server']['port']}{settings['server'].get('ws_path', '/onebot/v11/ws')}")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_signal)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            pass

    try:
        # Run until shutdown is requested
        async def run_until_shutdown():
            ws_task = asyncio.create_task(ws_adapter.start())
            done, pending = await asyncio.wait(
                [ws_task, asyncio.create_task(_shutdown_event.wait())],
                return_when=asyncio.FIRST_COMPLETED,
            )
            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            await ai_service.close()

        loop.run_until_complete(run_until_shutdown())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        loop.run_until_complete(ai_service.close())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
