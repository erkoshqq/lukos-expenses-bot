from __future__ import annotations

from dataclasses import dataclass

# Порядок колонок в листе "Категории"
HEADERS = ["ID категории", "ID проекта", "Название категории", "Активна"]


@dataclass
class Category:
    category_id: str
    project_id: str
    name: str
    is_active: bool = True

    def to_row(self) -> list:
        return [self.category_id, self.project_id, self.name, "ДА" if self.is_active else "НЕТ"]

    @classmethod
    def from_record(cls, record: dict) -> "Category":
        return cls(
            category_id=str(record.get("ID категории") or ""),
            project_id=str(record.get("ID проекта") or ""),
            name=str(record.get("Название категории") or ""),
            is_active=str(record.get("Активна") or "").strip().upper() == "ДА",
        )
