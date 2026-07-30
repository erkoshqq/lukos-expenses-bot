from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.callback_data import NavCB, ProjectCB
from models.project import Project


def main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📁 Проекты", callback_data=NavCB(to="projects"))
    builder.button(text="➕ Создать проект", callback_data=ProjectCB(action="create"))
    builder.adjust(1)
    return builder.as_markup()


def projects_list_kb(projects: list[Project]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for project in projects:
        title = project.name + (" 🗄" if project.is_archived else "")
        builder.button(
            text=title, callback_data=ProjectCB(action="open", project_id=project.project_id)
        )
    builder.button(text="➕ Создать проект", callback_data=ProjectCB(action="create"))
    builder.button(text="⬅ Назад", callback_data=NavCB(to="main"))
    builder.adjust(1)
    return builder.as_markup()


def project_menu_kb(project_id: str, is_owner: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 Добавить расход", callback_data=NavCB(to="expense_add", project_id=project_id))
    builder.button(text="📄 Расходы", callback_data=NavCB(to="expenses", project_id=project_id))
    builder.button(text="📂 Категории", callback_data=NavCB(to="categories", project_id=project_id))
    builder.button(text="👥 Участники", callback_data=NavCB(to="members", project_id=project_id))
    if is_owner:
        builder.button(text="⚙ Настройки", callback_data=NavCB(to="settings", project_id=project_id))
    builder.button(text="⬅ Назад", callback_data=NavCB(to="projects"))
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()


def settings_menu_kb(project_id: str, is_archived: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Переименовать проект", callback_data=ProjectCB(action="rename", project_id=project_id))
    archive_text = "♻️ Разархивировать" if is_archived else "🗄 Архивировать проект"
    builder.button(text=archive_text, callback_data=ProjectCB(action="archive", project_id=project_id))
    builder.button(text="⬅ Назад", callback_data=NavCB(to="project", project_id=project_id))
    builder.adjust(1)
    return builder.as_markup()


def back_kb(to: str, project_id: str = "") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅ Назад", callback_data=NavCB(to=to, project_id=project_id))
    return builder.as_markup()
