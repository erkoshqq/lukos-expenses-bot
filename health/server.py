"""
Простой aiohttp-сервер с эндпоинтом /health.
Нужен для того, чтобы Render.com видел открытый порт, а UptimeRobot мог
периодически "пинговать" бота и не давать бесплатному сервису "засыпать".
"""
from __future__ import annotations

from aiohttp import web

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


async def health_handler(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def root_handler(request: web.Request) -> web.Response:
    return web.json_response({"service": "expense-bot", "status": "running"})


def create_health_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/health", health_handler)
    app.router.add_get("/", root_handler)
    return app


async def run_health_server() -> web.AppRunner:
    app = create_health_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, settings.health_host, settings.health_port)
    await site.start()
    logger.info("Health-сервер запущен на %s:%s", settings.health_host, settings.health_port)
    return runner
