from __future__ import annotations

from dataclasses import dataclass

from config.settings import settings
from models.expense import Expense
from repositories.expense_repository import ExpenseRepository
from services.exceptions import NotFoundError
from services.log_service import LogService
from services.project_service import ProjectService
from services.user_service import UserService
from utils.ids import new_id, now_str
from utils.logger import get_logger

logger = get_logger(__name__)

EDITABLE_FIELDS = {"amount", "description", "category", "comment"}
FIELD_LABELS = {
    "amount": "Сумма",
    "description": "Описание",
    "category": "Категория",
    "comment": "Комментарий",
}


@dataclass
class ExpensesPage:
    items: list[Expense]
    page: int
    total_pages: int
    total_count: int


class ExpenseService:
    def __init__(
        self,
        expense_repository: ExpenseRepository,
        project_service: ProjectService,
        user_service: UserService,
        log_service: LogService,
    ) -> None:
        self._expenses = expense_repository
        self._projects = project_service
        self._users = user_service
        self._logs = log_service

    async def _ensure_access(self, project_id: str, telegram_id: int) -> None:
        # Любая роль (owner/member) имеет доступ к расходам проекта
        await self._projects.get_role(project_id, telegram_id)

    async def add_expense(
        self,
        project_id: str,
        actor_id: int,
        actor_display: str,
        amount: float,
        description: str,
        category: str,
        comment: str,
    ) -> Expense:
        await self._ensure_access(project_id, actor_id)

        expense = Expense(
            expense_id=new_id(),
            project_id=project_id,
            amount=amount,
            category=category,
            description=description,
            comment=comment,
            created_by=actor_id,
            created_at=now_str(),
            is_edited=False,
        )
        await self._expenses.add(expense)

        project = await self._projects.get_project(project_id)
        await self._logs.record(
            project.name, actor_display, "Создание расхода",
            f"{amount} · {category} · {description}",
        )

        expense.created_by_name = actor_display
        return expense

    async def get_expenses_page(self, project_id: str, actor_id: int, page: int) -> ExpensesPage:
        await self._ensure_access(project_id, actor_id)
        all_expenses = await self._expenses.get_by_project(project_id)
        page_size = settings.expenses_page_size
        total_count = len(all_expenses)
        total_pages = max((total_count + page_size - 1) // page_size, 1)
        page = max(0, min(page, total_pages - 1))
        start = page * page_size
        items = all_expenses[start:start + page_size]
        return ExpensesPage(items=items, page=page, total_pages=total_pages, total_count=total_count)

    async def get_expense_card(self, project_id: str, actor_id: int, expense_id: str) -> Expense:
        await self._ensure_access(project_id, actor_id)
        expense = await self._expenses.get_by_id(expense_id)
        if not expense or expense.project_id != project_id:
            raise NotFoundError("Расход не найден (возможно, уже удалён).")

        ids_to_load = [expense.created_by]
        if expense.edited_by:
            ids_to_load.append(expense.edited_by)
        users = await self._users.get_many_by_ids(ids_to_load)
        creator = users.get(expense.created_by)
        expense.created_by_name = creator.full_name if creator else str(expense.created_by)
        if expense.edited_by:
            editor = users.get(expense.edited_by)
            expense.edited_by_name = editor.full_name if editor else str(expense.edited_by)
        return expense

    async def edit_field(
        self,
        project_id: str,
        actor_id: int,
        actor_display: str,
        expense_id: str,
        field: str,
        new_value: str | float,
    ) -> Expense:
        if field not in EDITABLE_FIELDS:
            raise ValueError(f"Неизвестное поле для редактирования: {field}")

        await self._ensure_access(project_id, actor_id)
        expense = await self._expenses.get_by_id(expense_id)
        if not expense or expense.project_id != project_id:
            raise NotFoundError("Расход не найден (возможно, уже удалён).")

        old_value = getattr(expense, field)
        setattr(expense, field, new_value)
        expense.is_edited = True
        expense.edited_by = actor_id
        expense.edited_at = now_str()

        await self._expenses.update_expense(expense)

        project = await self._projects.get_project(project_id)
        await self._logs.record(
            project.name, actor_display, "Редактирование расхода",
            f"{FIELD_LABELS[field]}: «{old_value}» → «{new_value}»",
        )
        return expense

    async def delete_expense(self, project_id: str, actor_id: int, actor_display: str, expense_id: str) -> None:
        await self._ensure_access(project_id, actor_id)
        expense = await self._expenses.get_by_id(expense_id)
        if not expense or expense.project_id != project_id:
            raise NotFoundError("Расход не найден (возможно, уже удалён).")

        project = await self._projects.get_project(project_id)
        # Запись в журнал действий делается ДО физического удаления (по требованиям ТЗ)
        await self._logs.record(
            project.name, actor_display, "Удаление расхода",
            f"{expense.amount} · {expense.category} · {expense.description}",
        )
        deleted = await self._expenses.delete_expense(expense_id)
        if not deleted:
            raise NotFoundError("Расход не найден (возможно, уже удалён).")
