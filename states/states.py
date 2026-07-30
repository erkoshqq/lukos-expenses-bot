from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class ProjectCreateStates(StatesGroup):
    waiting_name = State()


class ProjectRenameStates(StatesGroup):
    waiting_new_name = State()


class MemberInviteStates(StatesGroup):
    waiting_telegram_id = State()
    waiting_role = State()


class ExpenseAddStates(StatesGroup):
    waiting_amount = State()
    waiting_description = State()
    waiting_category = State()
    waiting_comment = State()          # ожидание нажатия кнопки "Добавить"/"Пропустить"
    waiting_comment_text = State()     # ожидание текста комментария после нажатия "Добавить"


class ExpenseEditStates(StatesGroup):
    choosing_field = State()
    waiting_new_value = State()


class ExpenseDeleteStates(StatesGroup):
    waiting_confirmation = State()


class CategoryStates(StatesGroup):
    waiting_new_category_name = State()
    waiting_rename_value = State()
