from __future__ import annotations

from dataclasses import dataclass

# Порядок колонок в листе "Пользователи"
HEADERS = ["Telegram ID", "Username", "Имя", "Дата регистрации"]


@dataclass
class User:
    telegram_id: int
    username: str
    full_name: str
    registered_at: str

    def to_row(self) -> list:
        return [self.telegram_id, self.username, self.full_name, self.registered_at]

    @classmethod
    def from_record(cls, record: dict) -> "User":
        return cls(
            telegram_id=int(record.get("Telegram ID") or 0),
            username=str(record.get("Username") or ""),
            full_name=str(record.get("Имя") or ""),
            registered_at=str(record.get("Дата регистрации") or ""),
        )
