from __future__ import annotations

from models.project import Project
from repositories.base_repository import BaseRepository
from repositories.sheets_client import SHEET_PROJECTS


class ProjectRepository(BaseRepository[Project]):
    sheet_name = SHEET_PROJECTS

    def _from_record(self, record: dict) -> Project:
        return Project.from_record(record)

    def _to_row(self, item: Project) -> list:
        return item.to_row()

    async def get_by_id(self, project_id: str) -> Project | None:
        found = await self.find_index(lambda p: p.project_id == project_id)
        return found[1] if found else None

    async def get_by_owner(self, owner_id: int) -> list[Project]:
        items = await self.get_all()
        return [p for p in items if p.owner_id == owner_id]

    async def update_project(self, project: Project) -> None:
        found = await self.find_index(lambda p: p.project_id == project.project_id)
        if not found:
            raise ValueError(f"Проект {project.project_id} не найден")
        idx, _ = found
        await self.update_at(idx, project)
