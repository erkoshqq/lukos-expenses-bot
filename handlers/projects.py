from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards.callback_data import NavCB, ProjectCB
from keyboards.main_menu import project_menu_kb, projects_list_kb, settings_menu_kb
from models.member import Role
from models.user import User
from services.exceptions import ServiceError
from services.project_service import ProjectService
from states.states import ProjectCreateStates, ProjectRenameStates
from utils.formatters import format_project_header
from utils.logger import get_logger
from utils.validators import ValidationError, validate_text

logger = get_logger(__name__)

router = Router(name="projects")


def _display_name(user: User | None) -> str:
    if not user:
        return "неизвестный"
    return user.full_name or user.username or str(user.telegram_id)


async def render_project_menu(
    callback: CallbackQuery, project_id: str, current_user: User | None, project_service: ProjectService
) -> None:
    try:
        project = await project_service.get_project(project_id)
        role = await project_service.get_role(project_id, current_user.telegram_id)
    except ServiceError as e:
        await callback.answer(str(e), show_alert=True)
        return

    text = format_project_header(project) + f"\n\nВаша роль: {role.display}"
    await callback.message.edit_text(
        text, reply_markup=project_menu_kb(project_id, is_owner=(role == Role.OWNER))
    )
    await callback.answer()


async def render_settings_menu(
    callback: CallbackQuery, project_id: str, current_user: User | None, project_service: ProjectService
) -> None:
    try:
        await project_service.require_owner(project_id, current_user.telegram_id)
        project = await project_service.get_project(project_id)
    except ServiceError as e:
        await callback.answer(str(e), show_alert=True)
        return

    await callback.message.edit_text(
        f"⚙ Настройки проекта «{project.name}»",
        reply_markup=settings_menu_kb(project_id, project.is_archived),
    )
    await callback.answer()


# ------------------------------------------------------------------ #
# Создание проекта
# ------------------------------------------------------------------ #
@router.callback_query(ProjectCB.filter(F.action == "create"))
async def start_create_project(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ProjectCreateStates.waiting_name)
    await callback.message.edit_text(
        "Введите название нового проекта (например: «Ремонт офиса»):"
    )
    await callback.answer()


@router.message(ProjectCreateStates.waiting_name)
async def process_create_project(
    message: Message, state: FSMContext, current_user: User | None, project_service: ProjectService
) -> None:
    try:
        name = validate_text(message.text or "", "Название проекта", max_len=100)
    except ValidationError as e:
        await message.answer(str(e))
        return

    project = await project_service.create_project(
        owner_id=current_user.telegram_id,
        owner_display=_display_name(current_user),
        name=name,
    )
    await state.clear()
    await message.answer(
        f"✅ Проект «{project.name}» создан! Вы назначены владельцем.",
        reply_markup=project_menu_kb(project.project_id, is_owner=True),
    )


# ------------------------------------------------------------------ #
# Открытие проекта из списка
# ------------------------------------------------------------------ #
@router.callback_query(ProjectCB.filter(F.action == "open"))
async def open_project(
    callback: CallbackQuery, callback_data: ProjectCB, current_user: User | None, project_service: ProjectService
) -> None:
    await render_project_menu(callback, callback_data.project_id, current_user, project_service)


# ------------------------------------------------------------------ #
# Переименование проекта
# ------------------------------------------------------------------ #
@router.callback_query(ProjectCB.filter(F.action == "rename"))
async def start_rename_project(callback: CallbackQuery, callback_data: ProjectCB, state: FSMContext) -> None:
    await state.set_state(ProjectRenameStates.waiting_new_name)
    await state.update_data(project_id=callback_data.project_id)
    await callback.message.edit_text("Введите новое название проекта:")
    await callback.answer()


@router.message(ProjectRenameStates.waiting_new_name)
async def process_rename_project(
    message: Message, state: FSMContext, current_user: User | None, project_service: ProjectService
) -> None:
    data = await state.get_data()
    project_id = data["project_id"]
    try:
        new_name = validate_text(message.text or "", "Название проекта", max_len=100)
        project = await project_service.rename_project(
            project_id, current_user.telegram_id, _display_name(current_user), new_name
        )
    except (ValidationError, ServiceError) as e:
        await message.answer(str(e))
        return

    await state.clear()
    await message.answer(
        f"✅ Проект переименован в «{project.name}».",
        reply_markup=project_menu_kb(project_id, is_owner=True),
    )


# ------------------------------------------------------------------ #
# Архивация / разархивация
# ------------------------------------------------------------------ #
@router.callback_query(ProjectCB.filter(F.action == "archive"))
async def toggle_archive_project(
    callback: CallbackQuery, callback_data: ProjectCB, current_user: User | None, project_service: ProjectService
) -> None:
    try:
        project = await project_service.toggle_archive(
            callback_data.project_id, current_user.telegram_id, _display_name(current_user)
        )
    except ServiceError as e:
        await callback.answer(str(e), show_alert=True)
        return

    status = "заархивирован" if project.is_archived else "восстановлен из архива"
    await callback.answer(f"Проект {status}.")
    await render_settings_menu(callback, callback_data.project_id, current_user, project_service)


@router.callback_query(ProjectCB.filter(F.action == "noop"))
async def project_noop(callback: CallbackQuery) -> None:
    await callback.answer()
