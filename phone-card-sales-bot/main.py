import asyncio
import logging
import signal
import webbrowser
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

from src.adapter.websocket_client import NapCatWSAdapter
from src.ai.service import AIService
from src.config_loader import load_config, ConfigError
from src.handler.message import MessageHandler
from webui import app as web_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_shutdown_event = asyncio.Event()


def _handle_signal():
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

    handler = MessageHandler(
        ai_service=ai_service,
        ws_adapter=ws_adapter,
    )

    ws_adapter.on_message = handler.handle

    logger.info("=" * 50)
    logger.info("  QQ Bot 启动中...")
    logger.info(f"  LLM: {settings['llm']['model']}")
    logger.info(f"  WS 服务: ws://{settings['server']['host']}:{settings['server']['port']}{settings['server'].get('ws_path', '/onebot/v11/ws')}")
    logger.info(f"  管理面板: http://localhost:8767")
    logger.info("=" * 50)

    # Auto open browser after a short delay
    def _open_browser():
        import time
        time.sleep(1.5)
        webbrowser.open("http://localhost:8767")
    import threading
    threading.Thread(target=_open_browser, daemon=True).start()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_signal)
        except NotImplementedError:
            pass

    try:
        async def run():
            ws_task = asyncio.create_task(ws_adapter.start())

            web_config = uvicorn.Config(web_app, host="0.0.0.0", port=8767,
                                        log_level="warning")
            web_server = uvicorn.Server(web_config)
            web_task = asyncio.create_task(web_server.serve())

            done, pending = await asyncio.wait(
                [ws_task, web_task, asyncio.create_task(_shutdown_event.wait())],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, KeyboardInterrupt):
                    pass
            await ai_service.close()

        loop.run_until_complete(run())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        loop.run_until_complete(ai_service.close())
    except Exception:
        logger.exception("Unexpected error")
    finally:
        loop.close()


if __name__ == "__main__":
    main()
