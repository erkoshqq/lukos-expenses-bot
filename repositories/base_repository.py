"""
Базовый класс репозитория с общими операциями поиска/обновления/удаления строк.
Конкретные репозитории наследуются от него и работают с типизированными моделями.
"""
from __future__ import annotations

from typing import Any, Callable, Generic, TypeVar

from repositories.sheets_client import SheetsClient

T = TypeVar("T")


class BaseRepository(Generic[T]):
    sheet_name: str = ""

    def __init__(self, client: SheetsClient) -> None:
        self._client = client

    def _from_record(self, record: dict[str, Any]) -> T:
        raise NotImplementedError

    def _to_row(self, item: T) -> list:
        raise NotImplementedError

    async def get_all(self) -> list[T]:
        records = await self._client.get_all_records(self.sheet_name)
        return [self._from_record(r) for r in records if any(str(v).strip() for v in r.values())]

    async def find_index(self, predicate: Callable[[T], bool]) -> tuple[int, T] | None:
        """Возвращает (индекс_строки_данных, объект) первой записи, удовлетворяющей предикату."""
        items = await self.get_all()
        for idx, item in enumerate(items, start=1):
            if predicate(item):
                return idx, item
        return None

    async def add(self, item: T) -> T:
        await self._client.append_row(self.sheet_name, self._to_row(item))
        return item

    async def update_at(self, row_index: int, item: T) -> None:
        await self._client.update_row(self.sheet_name, row_index, self._to_row(item))

    async def delete_at(self, row_index: int) -> None:
        await self._client.delete_row(self.sheet_name, row_index)
