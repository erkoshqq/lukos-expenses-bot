from __future__ import annotations

from dataclasses import dataclass

# Порядок колонок в листе "Расходы"
HEADERS = [
    "ID расхода",
    "ID проекта",
    "Сумма",
    "Категория",
    "Описание",
    "Комментарий",
    "Создал",
    "Дата создания",
    "Изменено",
    "Кем изменено",
    "Дата изменения",
]


@dataclass
class Expense:
    expense_id: str
    project_id: str
    amount: float
    category: str
    description: str
    comment: str
    created_by: int
    created_at: str
    is_edited: bool = False
    edited_by: int | None = None
    edited_at: str | None = None

    # Заполняются сервисным слоем для отображения (не хранятся в отдельной колонке)
    created_by_name: str = ""
    edited_by_name: str = ""

    def to_row(self) -> list:
        return [
            self.expense_id,
            self.project_id,
            self.amount,
            self.category,
            self.description,
            self.comment,
            self.created_by,
            self.created_at,
            "ДА" if self.is_edited else "НЕТ",
            self.edited_by if self.edited_by else "",
            self.edited_at if self.edited_at else "",
        ]

    @classmethod
    def from_record(cls, record: dict) -> "Expense":
        amount_raw = record.get("Сумма") or 0
        try:
            amount = float(str(amount_raw).replace(",", "."))
        except ValueError:
            amount = 0.0

        edited_by_raw = record.get("Кем изменено") or ""
        edited_by = int(edited_by_raw) if str(edited_by_raw).strip().isdigit() else None

        return cls(
            expense_id=str(record.get("ID расхода") or ""),
            project_id=str(record.get("ID проекта") or ""),
            amount=amount,
            category=str(record.get("Категория") or ""),
            description=str(record.get("Описание") or ""),
            comment=str(record.get("Комментарий") or ""),
            created_by=int(record.get("Создал") or 0),
            created_at=str(record.get("Дата создания") or ""),
            is_edited=str(record.get("Изменено") or "").strip().upper() == "ДА",
            edited_by=edited_by,
            edited_at=str(record.get("Дата изменения") or "") or None,
        )
