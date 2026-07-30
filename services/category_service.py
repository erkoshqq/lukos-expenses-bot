from __future__ import annotations

from models.category import Category
from repositories.category_repository import CategoryRepository
from services.exceptions import NotFoundError
from services.log_service import LogService
from services.project_service import ProjectService
from utils.ids import new_id
from utils.logger import get_logger

logger = get_logger(__name__)


class CategoryService:
    def __init__(
        self,
        category_repository: CategoryRepository,
        project_service: ProjectService,
        log_service: LogService,
    ) -> None:
        self._categories = category_repository
        self._projects = project_service
        self._logs = log_service

    async def list_categories(self, project_id: str, only_active: bool = False) -> list[Category]:
        return await self._categories.get_by_project(project_id, only_active=only_active)

    async def get_category(self, category_id: str) -> Category:
        category = await self._categories.get_by_id(category_id)
        if not category:
            raise NotFoundError("Категория не найдена.")
        return category

    async def add_category(self, project_id: str, actor_id: int, actor_display: str, name: str) -> Category:
        await self._projects.require_owner(project_id, actor_id)
        category = Category(category_id=new_id(), project_id=project_id, name=name, is_active=True)
        await self._categories.add(category)

        project = await self._projects.get_project(project_id)
        await self._logs.record(project.name, actor_display, "Изменение категорий", f"Добавлена категория «{name}»")
        return category

    async def rename_category(self, project_id: str, actor_id: int, actor_display: str, category_id: str, new_name: str) -> Category:
        await self._projects.require_owner(project_id, actor_id)
        category = await self.get_category(category_id)
        old_name = category.name
        category.name = new_name
        await self._categories.update_category(category)

        project = await self._projects.get_project(project_id)
        await self._logs.record(
            project.name, actor_display, "Изменение категорий",
            f"Категория переименована: «{old_name}» → «{new_name}»",
        )
        return category

    async def toggle_active(self, project_id: str, actor_id: int, actor_display: str, category_id: str) -> Category:
        await self._projects.require_owner(project_id, actor_id)
        category = await self.get_category(category_id)
        category.is_active = not category.is_active
        await self._categories.update_category(category)

        project = await self._projects.get_project(project_id)
        state = "включена" if category.is_active else "отключена"
        await self._logs.record(
            project.name, actor_display, "Изменение категорий", f"Категория «{category.name}» {state}"
        )
        return category
