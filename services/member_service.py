from __future__ import annotations

from models.member import Member, Role
from models.user import User
from repositories.member_repository import MemberRepository
from services.exceptions import NotFoundError, PermissionDeniedError
from services.log_service import LogService
from services.project_service import ProjectService
from services.user_service import UserService
from utils.ids import now_str
from utils.logger import get_logger

logger = get_logger(__name__)


class MemberService:
    def __init__(
        self,
        member_repository: MemberRepository,
        project_service: ProjectService,
        user_service: UserService,
        log_service: LogService,
    ) -> None:
        self._members = member_repository
        self._projects = project_service
        self._users = user_service
        self._logs = log_service

    async def list_members_with_users(self, project_id: str) -> tuple[list[Member], dict[int, User]]:
        members = await self._members.get_by_project(project_id)
        users = await self._users.get_many_by_ids([m.telegram_id for m in members])
        return members, users

    async def invite_member(
        self,
        project_id: str,
        actor_id: int,
        actor_display: str,
        target_telegram_id: int,
        role: Role,
    ) -> Member:
        await self._projects.require_owner(project_id, actor_id)

        target_user = await self._users.get_by_id(target_telegram_id)
        if not target_user:
            raise NotFoundError(
                "Этот пользователь ещё не запускал бота. Попросите его отправить боту команду /start."
            )

        existing = await self._members.get_membership(project_id, target_telegram_id)
        if existing:
            raise PermissionDeniedError("Этот пользователь уже добавлен в проект.")

        member = Member(
            project_id=project_id,
            telegram_id=target_telegram_id,
            role=role,
            added_at=now_str(),
        )
        await self._members.add(member)

        project = await self._projects.get_project(project_id)
        await self._logs.record(
            project.name,
            actor_display,
            "Добавление участника",
            f"Добавлен {target_user.full_name or target_telegram_id} с ролью {role.display}",
        )
        return member

    async def remove_member(self, project_id: str, actor_id: int, actor_display: str, target_telegram_id: int) -> None:
        await self._projects.require_owner(project_id, actor_id)

        membership = await self._members.get_membership(project_id, target_telegram_id)
        if not membership:
            raise NotFoundError("Участник не найден.")
        if membership.role == Role.OWNER:
            raise PermissionDeniedError("Нельзя удалить владельца проекта.")

        removed = await self._members.remove_member(project_id, target_telegram_id)
        if not removed:
            raise NotFoundError("Участник не найден.")

        target_user = await self._users.get_by_id(target_telegram_id)
        project = await self._projects.get_project(project_id)
        await self._logs.record(
            project.name,
            actor_display,
            "Удаление участника",
            f"Удалён {target_user.full_name if target_user else target_telegram_id}",
        )
