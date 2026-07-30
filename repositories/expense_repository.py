from __future__ import annotations

from models.expense import Expense
from repositories.base_repository import BaseRepository
from repositories.sheets_client import SHEET_EXPENSES


class ExpenseRepository(BaseRepository[Expense]):
    sheet_name = SHEET_EXPENSES

    def _from_record(self, record: dict) -> Expense:
        return Expense.from_record(record)

    def _to_row(self, item: Expense) -> list:
        return item.to_row()

    async def get_by_project(self, project_id: str) -> list[Expense]:
        items = await self.get_all()
        result = [e for e in items if e.project_id == project_id]
        # Сначала новые
        result.sort(key=lambda e: e.created_at, reverse=True)
        return result

    async def get_by_id(self, expense_id: str) -> Expense | None:
        found = await self.find_index(lambda e: e.expense_id == expense_id)
        return found[1] if found else None

    async def update_expense(self, expense: Expense) -> None:
        found = await self.find_index(lambda e: e.expense_id == expense.expense_id)
        if not found:
            raise ValueError(f"Расход {expense.expense_id} не найден")
        idx, _ = found
        await self.update_at(idx, expense)

    async def delete_expense(self, expense_id: str) -> bool:
        found = await self.find_index(lambda e: e.expense_id == expense_id)
        if not found:
            return False
        idx, _ = found
        await self.delete_at(idx)
        return True
