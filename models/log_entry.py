from __future__ import annotations

from dataclasses import dataclass

# Порядок колонок в листе "Журнал действий"
HEADERS = ["Дата", "Проект", "Пользователь", "Действие", "Описание"]


@dataclass
class LogEntry:
    date: str
    project_name: str
    user_display: str
    action: str
    details: str

    def to_row(self) -> list:
        return [self.date, self.project_name, self.user_display, self.action, self.details]

    @classmethod
    def from_record(cls, record: dict) -> "LogEntry":
        return cls(
            date=str(record.get("Дата") or ""),
            project_name=str(record.get("Проект") or ""),
            user_display=str(record.get("Пользователь") or ""),
            action=str(record.get("Действие") or ""),
            details=str(record.get("Описание") or ""),
        )
