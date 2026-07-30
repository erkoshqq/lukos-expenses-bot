from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from utils.logger import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Логирует каждое входящее сообщение/callback и ошибки внутри обработчиков."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            if isinstance(event, Message):
                logger.info("MSG from=%s text=%r", event.from_user.id if event.from_user else "?", event.text)
            elif isinstance(event, CallbackQuery):
                logger.info("CALLBACK from=%s data=%r", event.from_user.id if event.from_user else "?", event.data)

            return await handler(event, data)
        except Exception:
            logger.exception("Необработанная ошибка при обработке апдейта")
            raise
