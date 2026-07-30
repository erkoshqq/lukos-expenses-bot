from __future__ import annotations

from models.log_entry import LogEntry
from repositories.log_repository import LogRepository
from utils.ids import now_str


class LogService:
    def __init__(self, log_repository: LogRepository) -> None:
        self._logs = log_repository

    async def record(self, project_name: str, user_display: str, action: str, details: str) -> None:
        entry = LogEntry(
            date=now_str(),
            project_name=project_name,
            user_display=user_display,
            action=action,
            details=details,
        )
        await self._logs.add_entry(entry)
