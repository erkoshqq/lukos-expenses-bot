from __future__ import annotations

from models.category import Category
from repositories.base_repository import BaseRepository
from repositories.sheets_client import SHEET_CATEGORIES


class CategoryRepository(BaseRepository[Category]):
    sheet_name = SHEET_CATEGORIES

    def _from_record(self, record: dict) -> Category:
        return Category.from_record(record)

    def _to_row(self, item: Category) -> list:
        return item.to_row()

    async def get_by_project(self, project_id: str, only_active: bool = False) -> list[Category]:
        items = await self.get_all()
        result = [c for c in items if c.project_id == project_id]
        if only_active:
            result = [c for c in result if c.is_active]
        return result

    async def get_by_id(self, category_id: str) -> Category | None:
        found = await self.find_index(lambda c: c.category_id == category_id)
        return found[1] if found else None

    async def update_category(self, category: Category) -> None:
        found = await self.find_index(lambda c: c.category_id == category.category_id)
        if not found:
            raise ValueError(f"Категория {category.category_id} не найдена")
        idx, _ = found
        await self.update_at(idx, category)
