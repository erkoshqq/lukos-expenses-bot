from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, User as TgUser

from services.user_service import UserService
from utils.logger import get_logger

logger = get_logger(__name__)


class AuthMiddleware(BaseMiddleware):
    """
    Перехватывает каждый апдейт, извлекает Telegram-пользователя и:
    - регистрирует его в листе "Пользователи" при первом обращении;
    - прокидывает объект User (наша модель) в data['current_user'] для хендлеров.
    """

    def __init__(self, user_service: UserService) -> None:
        self._user_service = user_service

    def _extract_tg_user(self, event: TelegramObject) -> TgUser | None:
        if isinstance(event, Update):
            inner = event.event
        else:
            inner = event
        return getattr(inner, "from_user", None)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = self._extract_tg_user(event)
        if tg_user is not None and not tg_user.is_bot:
            try:
                current_user = await self._user_service.get_or_register(
                    telegram_id=tg_user.id,
                    username=tg_user.username,
                    full_name=(tg_user.full_name or str(tg_user.id)),
                )
                data["current_user"] = current_user
            except Exception:
                logger.exception("Не удалось зарегистрировать/обновить пользователя %s", tg_user.id)
                data["current_user"] = None
        else:
            data["current_user"] = None

        return await handler(event, data)
