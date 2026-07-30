from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.callback_data import CategoryCB, NavCB
from models.category import Category


def categories_list_kb(project_id: str, categories: list[Category], is_owner: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for category in categories:
        status = "✅" if category.is_active else "🚫"
        builder.button(
            text=f"{status} {category.name}",
            callback_data=CategoryCB(action="manage", project_id=project_id, category_id=category.category_id)
            if is_owner
            else CategoryCB(action="noop", project_id=project_id),
        )
    if is_owner:
        builder.button(text="➕ Добавить категорию", callback_data=CategoryCB(action="add", project_id=project_id))
    builder.button(text="⬅ Назад", callback_data=NavCB(to="project", project_id=project_id))
    builder.adjust(1)
    return builder.as_markup()


def category_manage_kb(project_id: str, category: Category) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✏️ Переименовать",
        callback_data=CategoryCB(action="rename", project_id=project_id, category_id=category.category_id),
    )
    toggle_text = "🚫 Отключить" if category.is_active else "✅ Включить"
    builder.button(
        text=toggle_text,
        callback_data=CategoryCB(action="toggle", project_id=project_id, category_id=category.category_id),
    )
    builder.button(text="⬅ Назад", callback_data=NavCB(to="categories", project_id=project_id))
    builder.adjust(1)
    return builder.as_markup()


def choose_category_kb(project_id: str, categories: list[Category]) -> InlineKeyboardMarkup:
    """Клавиатура выбора категории при добавлении расхода (только активные)."""
    builder = InlineKeyboardBuilder()
    for category in categories:
        builder.button(
            text=category.name,
            callback_data=CategoryCB(action="choose", project_id=project_id, category_id=category.category_id),
        )
    builder.adjust(2)
    return builder.as_markup()
