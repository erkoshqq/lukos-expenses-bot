from __future__ import annotations

from models.log_entry import LogEntry
from repositories.base_repository import BaseRepository
from repositories.sheets_client import SHEET_LOG


class LogRepository(BaseRepository[LogEntry]):
    sheet_name = SHEET_LOG

    def _from_record(self, record: dict) -> LogEntry:
        return LogEntry.from_record(record)

    def _to_row(self, item: LogEntry) -> list:
        return item.to_row()

    async def add_entry(self, entry: LogEntry) -> None:
        await self.add(entry)
