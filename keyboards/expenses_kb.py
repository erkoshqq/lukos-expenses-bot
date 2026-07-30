from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.callback_data import ExpenseCB, NavCB
from models.expense import Expense
from utils.formatters import format_expense_row_short


def expenses_list_kb(project_id: str, expenses_page: list[Expense], page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for expense in expenses_page:
        builder.button(
            text=format_expense_row_short(expense),
            callback_data=ExpenseCB(action="open", project_id=project_id, expense_id=expense.expense_id),
        )

    # Кнопки пагинации добавляем в тот же builder (не через отдельный attach()),
    # чтобы единственный вызов adjust() ниже корректно рассчитал раскладку по рядам.
    nav_buttons_count = 0
    if page > 0:
        builder.button(text="⬅️", callback_data=ExpenseCB(action="page", project_id=project_id, page=page - 1))
        nav_buttons_count += 1
    builder.button(text=f"{page + 1}/{max(total_pages, 1)}", callback_data=ExpenseCB(action="noop"))
    nav_buttons_count += 1
    if page < total_pages - 1:
        builder.button(text="➡️", callback_data=ExpenseCB(action="page", project_id=project_id, page=page + 1))
        nav_buttons_count += 1

    builder.button(text="⬅ Назад", callback_data=NavCB(to="project", project_id=project_id))

    # ВАЖНО: adjust() задаёт раскладку по рядам для ВСЕХ кнопок билдера целиком и не
    # суммируется с предыдущими вызовами - второй вызов adjust() полностью переопределяет
    # первый. Поэтому здесь один-единственный вызов с явным списком размеров:
    # каждый расход - отдельный ряд, затем ряд пагинации, затем "Назад".
    row_sizes = [1] * len(expenses_page) + [nav_buttons_count, 1]
    builder.adjust(*row_sizes)
    return builder.as_markup()


def expense_card_kb(project_id: str, expense_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Редактировать", callback_data=ExpenseCB(action="edit_menu", project_id=project_id, expense_id=expense_id))
    builder.button(text="🗑 Удалить", callback_data=ExpenseCB(action="delete", project_id=project_id, expense_id=expense_id))
    builder.button(text="⬅ Назад", callback_data=ExpenseCB(action="page", project_id=project_id, page=0))
    builder.adjust(2, 1)
    return builder.as_markup()


def comment_step_kb(project_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💬 Добавить комментарий", callback_data=ExpenseCB(action="comment_add", project_id=project_id))
    builder.button(text="⏭ Пропустить", callback_data=ExpenseCB(action="comment_skip", project_id=project_id))
    builder.adjust(1)
    return builder.as_markup()


def edit_fields_kb(project_id: str, expense_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    fields = [
        ("amount", "💰 Сумма"),
        ("description", "📝 Описание"),
        ("category", "📂 Категория"),
        ("comment", "💬 Комментарий"),
    ]
    for field_key, label in fields:
        builder.button(
            text=label,
            callback_data=ExpenseCB(action="edit_field", project_id=project_id, expense_id=expense_id, field=field_key),
        )
    builder.button(text="⬅ Назад", callback_data=ExpenseCB(action="open", project_id=project_id, expense_id=expense_id))
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def confirm_delete_kb(project_id: str, expense_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data=ExpenseCB(action="confirm_delete", project_id=project_id, expense_id=expense_id))
    builder.button(text="❌ Отмена", callback_data=ExpenseCB(action="open", project_id=project_id, expense_id=expense_id))
    builder.adjust(1)
    return builder.as_markup()
