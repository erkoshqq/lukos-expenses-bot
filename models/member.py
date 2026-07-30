from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# Порядок колонок в листе "Участники"
HEADERS = ["ID проекта", "Telegram ID", "Роль", "Дата добавления"]


class Role(str, Enum):
    OWNER = "owner"
    MEMBER = "member"

    @property
    def display(self) -> str:
        return "Владелец" if self is Role.OWNER else "Участник"


@dataclass
class Member:
    project_id: str
    telegram_id: int
    role: Role
    added_at: str

    def to_row(self) -> list:
        return [self.project_id, self.telegram_id, self.role.value, self.added_at]

    @classmethod
    def from_record(cls, record: dict) -> "Member":
        role_raw = str(record.get("Роль") or Role.MEMBER.value).strip().lower()
        try:
            role = Role(role_raw)
        except ValueError:
            role = Role.MEMBER
        return cls(
            project_id=str(record.get("ID проекта") or ""),
            telegram_id=int(record.get("Telegram ID") or 0),
            role=role,
            added_at=str(record.get("Дата добавления") or ""),
        )
