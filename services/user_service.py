from __future__ import annotations

from models.user import User
from repositories.user_repository import UserRepository
from utils.ids import now_str
from utils.logger import get_logger

logger = get_logger(__name__)


class UserService:
    def __init__(self, user_repository: UserRepository) -> None:
        self._users = user_repository

    async def get_or_register(self, telegram_id: int, username: str | None, full_name: str) -> User:
        existing = await self._users.get_by_telegram_id(telegram_id)
        if existing:
            # Обновляем актуальные username/имя (могли смениться), дата регистрации не меняется
            if existing.username != (username or "") or existing.full_name != full_name:
                existing.username = username or ""
                existing.full_name = full_name
                await self._users.upsert(existing)
            return existing

        user = User(
            telegram_id=telegram_id,
            username=username or "",
            full_name=full_name,
            registered_at=now_str(),
        )
        await self._users.upsert(user)
        logger.info("Зарегистрирован новый пользователь: %s (%s)", telegram_id, full_name)
        return user

    async def get_by_id(self, telegram_id: int) -> User | None:
        return await self._users.get_by_telegram_id(telegram_id)

    async def get_many_by_ids(self, telegram_ids: list[int]) -> dict[int, User]:
        all_users = await self._users.get_all()
        wanted = set(telegram_ids)
        return {u.telegram_id: u for u in all_users if u.telegram_id in wanted}
