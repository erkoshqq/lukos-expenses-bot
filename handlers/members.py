from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards.callback_data import MemberCB
from keyboards.members_kb import confirm_remove_kb, members_list_kb, role_choice_kb
from models.member import Role
from models.user import User
from services.exceptions import ServiceError
from services.member_service import MemberService
from services.project_service import ProjectService
from states.states import MemberInviteStates
from utils.logger import get_logger
from utils.validators import ValidationError, validate_telegram_id

logger = get_logger(__name__)

router = Router(name="members")


def _display_name(user: User | None) -> str:
    if not user:
        return "неизвестный"
    return user.full_name or user.username or str(user.telegram_id)


async def render_members_list(
    callback: CallbackQuery,
    project_id: str,
    current_user: User | None,
    member_service: MemberService,
    project_service: ProjectService,
) -> None:
    try:
        role = await project_service.get_role(project_id, current_user.telegram_id)
    except ServiceError as e:
        await callback.answer(str(e), show_alert=True)
        return

    members, users = await member_service.list_members_with_users(project_id)
    await callback.message.edit_text(
        "👥 Участники проекта:",
        reply_markup=members_list_kb(project_id, members, users, is_owner=(role == Role.OWNER)),
    )
    await callback.answer()


@router.callback_query(MemberCB.filter(F.action == "add"))
async def start_invite_member(callback: CallbackQuery, callback_data: MemberCB, state: FSMContext) -> None:
    await state.set_state(MemberInviteStates.waiting_telegram_id)
    await state.update_data(project_id=callback_data.project_id)
    await callback.message.edit_text(
        "Введите Telegram ID участника.\n"
        "Участник может узнать свой ID командой /myid у этого бота."
    )
    await callback.answer()


@router.message(MemberInviteStates.waiting_telegram_id)
async def process_invite_telegram_id(message: Message, state: FSMContext) -> None:
    try:
        telegram_id = validate_telegram_id(message.text or "")
    except ValidationError as e:
        await message.answer(str(e))
        return

    data = await state.get_data()
    await state.update_data(target_telegram_id=telegram_id)
    await state.set_state(MemberInviteStates.waiting_role)
    await message.answer("Выберите роль участника:", reply_markup=role_choice_kb(data["project_id"]))


@router.callback_query(MemberCB.filter(F.action == "set_role"), MemberInviteStates.waiting_role)
async def process_invite_role(
    callback: CallbackQuery,
    callback_data: MemberCB,
    state: FSMContext,
    current_user: User | None,
    member_service: MemberService,
) -> None:
    data = await state.get_data()
    project_id = data["project_id"]
    target_telegram_id = data["target_telegram_id"]
    role = Role(callback_data.role)

    try:
        await member_service.invite_member(
            project_id, current_user.telegram_id, _display_name(current_user), target_telegram_id, role
        )
    except ServiceError as e:
        await callback.answer(str(e), show_alert=True)
        return

    await state.clear()
    members, users = await member_service.list_members_with_users(project_id)
    await callback.message.edit_text(
        "✅ Участник добавлен.",
        reply_markup=members_list_kb(project_id, members, users, is_owner=True),
    )
    await callback.answer()


@router.callback_query(MemberCB.filter(F.action == "remove"))
async def confirm_remove_member(callback: CallbackQuery, callback_data: MemberCB) -> None:
    await callback.message.edit_text(
        "Вы уверены, что хотите удалить этого участника из проекта?",
        reply_markup=confirm_remove_kb(callback_data.project_id, callback_data.telegram_id),
    )
    await callback.answer()


@router.callback_query(MemberCB.filter(F.action == "confirm_remove"))
async def do_remove_member(
    callback: CallbackQuery, callback_data: MemberCB, current_user: User | None, member_service: MemberService, project_service: ProjectService
) -> None:
    try:
        await member_service.remove_member(
            callback_data.project_id, current_user.telegram_id, _display_name(current_user), callback_data.telegram_id
        )
    except ServiceError as e:
        await callback.answer(str(e), show_alert=True)
        return

    await callback.answer("Участник удалён.")
    await render_members_list(callback, callback_data.project_id, current_user, member_service, project_service)


@router.callback_query(MemberCB.filter(F.action == "noop"))
async def member_noop(callback: CallbackQuery) -> None:
    await callback.answer()
