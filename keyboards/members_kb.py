from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.callback_data import MemberCB, NavCB
from models.member import Member, Role
from models.user import User


def members_list_kb(project_id: str, members: list[Member], users_by_id: dict[int, User], is_owner: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for member in members:
        user = users_by_id.get(member.telegram_id)
        name = user.full_name if user and user.full_name else str(member.telegram_id)
        label = f"{name} — {member.role.display}"
        if is_owner and member.role != Role.OWNER:
            builder.button(
                text=f"❌ {label}",
                callback_data=MemberCB(action="remove", project_id=project_id, telegram_id=member.telegram_id),
            )
        else:
            builder.button(text=label, callback_data=MemberCB(action="noop", project_id=project_id))
    if is_owner:
        builder.button(text="➕ Добавить участника", callback_data=MemberCB(action="add", project_id=project_id))
    builder.button(text="⬅ Назад", callback_data=NavCB(to="project", project_id=project_id))
    builder.adjust(1)
    return builder.as_markup()


def role_choice_kb(project_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Owner", callback_data=MemberCB(action="set_role", project_id=project_id, role=Role.OWNER.value))
    builder.button(text="Member", callback_data=MemberCB(action="set_role", project_id=project_id, role=Role.MEMBER.value))
    builder.adjust(2)
    return builder.as_markup()


def confirm_remove_kb(project_id: str, telegram_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Да, удалить",
        callback_data=MemberCB(action="confirm_remove", project_id=project_id, telegram_id=telegram_id),
    )
    builder.button(text="❌ Отмена", callback_data=NavCB(to="members", project_id=project_id))
    builder.adjust(1)
    return builder.as_markup()
