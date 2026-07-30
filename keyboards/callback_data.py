from __future__ import annotations

from aiogram.filters.callback_data import CallbackData

# ВАЖНО: все поля со значением по умолчанию объявлены как Optional (str | None, int | None).
# Это принципиально для aiogram (использующего pydantic v2): при распаковке callback_data
# aiogram считает "необязательным" (nullable) любое поле, имеющее default, и подставляет
# None вместо пустой строки "". Если тип поля объявлен как строгий `str`, pydantic отклоняет
# None валидацией, и фильтр молча возвращает False (кнопка выглядит "не работающей").
# Поэтому: необязательные поля -> Optional-тип, а читать их в коде нужно через `value or ""`.


class NavCB(CallbackData, prefix="nav"):
    """Общая навигация: to = 'main' | 'projects' | 'project' | ..."""
    to: str
    project_id: str | None = ""


class ProjectCB(CallbackData, prefix="proj"):
    action: str  # open, create, rename, archive, noop
    project_id: str | None = ""


class MemberCB(CallbackData, prefix="mem"):
    action: str  # add, remove, set_role, confirm_remove, noop
    project_id: str
    telegram_id: int | None = 0
    role: str | None = ""


class CategoryCB(CallbackData, prefix="cat"):
    action: str  # add, rename, toggle, choose, manage, noop
    project_id: str
    category_id: str | None = ""


class ExpenseCB(CallbackData, prefix="exp"):
    action: str  # add, open, edit_menu, edit_field, delete, confirm_delete, page, comment_skip, comment_add, noop
    project_id: str | None = ""
    expense_id: str | None = ""
    field: str | None = ""
    page: int | None = 0

