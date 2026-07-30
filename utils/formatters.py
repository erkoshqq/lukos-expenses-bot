"""
Форматирование текстовых сообщений (карточки расходов, списки, и т.д.).
"""
from __future__ import annotations

from models.expense import Expense
from models.project import Project


def format_amount(amount: float) -> str:
    if amount == int(amount):
        return f"{int(amount):,}".replace(",", " ")
    return f"{amount:,.2f}".replace(",", " ")


def format_expense_card(expense: Expense) -> str:
    lines = [
        "🧾 <b>Расход</b>",
        f"💰 Сумма: <b>{format_amount(expense.amount)}</b>",
        f"📂 Категория: {expense.category}",
        f"📝 Описание: {expense.description}",
    ]
    if expense.comment:
        lines.append(f"💬 Комментарий: {expense.comment}")
    lines.append(f"👤 Создал: {expense.created_by_name or expense.created_by}")
    lines.append(f"📅 Дата создания: {expense.created_at}")

    if expense.is_edited:
        lines.append("")
        lines.append(f"✏️ <i>Изменено {expense.edited_by_name or expense.edited_by} · {expense.edited_at}</i>")

    return "\n".join(lines)


def format_expense_row_short(expense: Expense) -> str:
    mark = " ✏️" if expense.is_edited else ""
    return f"{format_amount(expense.amount)} · {expense.category} · {expense.description}{mark}"


def format_project_header(project: Project) -> str:
    archived = " (архив)" if project.is_archived else ""
    return f"📁 <b>{project.name}</b>{archived}"


def format_log_entry(date: str, project_name: str, user_display: str, action: str, details: str) -> str:
    return f"🕒 {date} | {project_name} | {user_display} | {action} | {details}"
