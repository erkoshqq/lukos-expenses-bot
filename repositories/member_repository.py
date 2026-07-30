from __future__ import annotations

from models.member import Member, Role
from repositories.base_repository import BaseRepository
from repositories.sheets_client import SHEET_MEMBERS


class MemberRepository(BaseRepository[Member]):
    sheet_name = SHEET_MEMBERS

    def _from_record(self, record: dict) -> Member:
        return Member.from_record(record)

    def _to_row(self, item: Member) -> list:
        return item.to_row()

    async def get_by_project(self, project_id: str) -> list[Member]:
        items = await self.get_all()
        return [m for m in items if m.project_id == project_id]

    async def get_membership(self, project_id: str, telegram_id: int) -> Member | None:
        found = await self.find_index(
            lambda m: m.project_id == project_id and m.telegram_id == telegram_id
        )
        return found[1] if found else None

    async def get_projects_for_user(self, telegram_id: int) -> list[str]:
        items = await self.get_all()
        return [m.project_id for m in items if m.telegram_id == telegram_id]

    async def remove_member(self, project_id: str, telegram_id: int) -> bool:
        found = await self.find_index(
            lambda m: m.project_id == project_id and m.telegram_id == telegram_id
        )
        if not found:
            return False
        idx, _ = found
        await self.delete_at(idx)
        return True

    async def update_role(self, project_id: str, telegram_id: int, role: Role) -> bool:
        found = await self.find_index(
            lambda m: m.project_id == project_id and m.telegram_id == telegram_id
        )
        if not found:
            return False
        idx, member = found
        member.role = role
        await self.update_at(idx, member)
        return True
