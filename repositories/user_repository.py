from __future__ import annotations

from models.user import User
from repositories.base_repository import BaseRepository
from repositories.sheets_client import SHEET_USERS


class UserRepository(BaseRepository[User]):
    sheet_name = SHEET_USERS

    def _from_record(self, record: dict) -> User:
        return User.from_record(record)

    def _to_row(self, item: User) -> list:
        return item.to_row()

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        found = await self.find_index(lambda u: u.telegram_id == telegram_id)
        return found[1] if found else None

    async def upsert(self, user: User) -> User:
        found = await self.find_index(lambda u: u.telegram_id == user.telegram_id)
        if found:
            idx, existing = found
            # Обновляем username/имя, дату регистрации сохраняем исходную
            user.registered_at = existing.registered_at
            await self.update_at(idx, user)
        else:
            await self.add(user)
        return user
