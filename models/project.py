from __future__ import annotations

from dataclasses import dataclass

# Порядок колонок в листе "Проекты"
HEADERS = ["ID проекта", "Название проекта", "Владелец", "Дата создания", "Архив"]


@dataclass
class Project:
    project_id: str
    name: str
    owner_id: int
    created_at: str
    is_archived: bool = False

    def to_row(self) -> list:
        return [
            self.project_id,
            self.name,
            self.owner_id,
            self.created_at,
            "ДА" if self.is_archived else "НЕТ",
        ]

    @classmethod
    def from_record(cls, record: dict) -> "Project":
        return cls(
            project_id=str(record.get("ID проекта") or ""),
            name=str(record.get("Название проекта") or ""),
            owner_id=int(record.get("Владелец") or 0),
            created_at=str(record.get("Дата создания") or ""),
            is_archived=str(record.get("Архив") or "").strip().upper() == "ДА",
        )
