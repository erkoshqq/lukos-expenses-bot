from __future__ import annotations

from config.settings import settings
from models.category import Category
from models.member import Member, Role
from models.project import Project
from repositories.category_repository import CategoryRepository
from repositories.member_repository import MemberRepository
from repositories.project_repository import ProjectRepository
from services.exceptions import NotFoundError, PermissionDeniedError
from services.log_service import LogService
from utils.ids import new_id, now_str
from utils.logger import get_logger

logger = get_logger(__name__)


class ProjectService:
    def __init__(
        self,
        project_repository: ProjectRepository,
        member_repository: MemberRepository,
        category_repository: CategoryRepository,
        log_service: LogService,
    ) -> None:
        self._projects = project_repository
        self._members = member_repository
        self._categories = category_repository
        self._logs = log_service

    async def create_project(self, owner_id: int, owner_display: str, name: str) -> Project:
        project = Project(
            project_id=new_id(),
            name=name,
            owner_id=owner_id,
            created_at=now_str(),
            is_archived=False,
        )
        await self._projects.add(project)

        member = Member(
            project_id=project.project_id,
            telegram_id=owner_id,
            role=Role.OWNER,
            added_at=now_str(),
        )
        await self._members.add(member)

        for cat_name in settings.default_categories:
            category = Category(
                category_id=new_id(),
                project_id=project.project_id,
                name=cat_name,
                is_active=True,
            )
            await self._categories.add(category)

        await self._logs.record(project.name, owner_display, "Создание проекта", f"Проект «{name}» создан")
        logger.info("Проект создан: %s (%s) владелец=%s", project.project_id, name, owner_id)
        return project

    async def get_user_projects(self, telegram_id: int) -> list[Project]:
        project_ids = set(await self._members.get_projects_for_user(telegram_id))
        if not project_ids:
            return []
        all_projects = await self._projects.get_all()
        return [p for p in all_projects if p.project_id in project_ids]

    async def get_project(self, project_id: str) -> Project:
        project = await self._projects.get_by_id(project_id)
        if not project:
            raise NotFoundError("Проект не найден.")
        return project

    async def get_role(self, project_id: str, telegram_id: int) -> Role:
        membership = await self._members.get_membership(project_id, telegram_id)
        if not membership:
            raise PermissionDeniedError("У вас нет доступа к этому проекту.")
        return membership.role

    async def require_owner(self, project_id: str, telegram_id: int) -> None:
        role = await self.get_role(project_id, telegram_id)
        if role != Role.OWNER:
            raise PermissionDeniedError("Это действие доступно только владельцу проекта.")

    async def rename_project(self, project_id: str, telegram_id: int, actor_display: str, new_name: str) -> Project:
        await self.require_owner(project_id, telegram_id)
        project = await self.get_project(project_id)
        old_name = project.name
        project.name = new_name
        await self._projects.update_project(project)
        await self._logs.record(
            project.name, actor_display, "Изменение категорий" if False else "Изменение проекта",
            f"Название изменено: «{old_name}» → «{new_name}»",
        )
        return project

    async def toggle_archive(self, project_id: str, telegram_id: int, actor_display: str) -> Project:
        await self.require_owner(project_id, telegram_id)
        project = await self.get_project(project_id)
        project.is_archived = not project.is_archived
        await self._projects.update_project(project)
        action = "Архивирование проекта" if project.is_archived else "Разархивирование проекта"
        await self._logs.record(project.name, actor_display, action, f"Проект «{project.name}»")
        return project
