from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards.callback_data import CategoryCB, NavCB
from keyboards.categories_kb import categories_list_kb, category_manage_kb
from models.member import Role
from models.user import User
from services.category_service import CategoryService
from services.exceptions import ServiceError
from services.project_service import ProjectService
from states.states import CategoryStates
from utils.logger import get_logger
from utils.validators import ValidationError, validate_text

logger = get_logger(__name__)

router = Router(name="categories")


def _display_name(user: User | None) -> str:
    if not user:
        return "неизвестный"
    return user.full_name or user.username or str(user.telegram_id)


async def render_categories_list(
    callback: CallbackQuery,
    project_id: str,
    current_user: User | None,
    category_service: CategoryService,
    project_service: ProjectService,
) -> None:
    try:
        role = await project_service.get_role(project_id, current_user.telegram_id)
    except ServiceError as e:
        await callback.answer(str(e), show_alert=True)
        return

    categories = await category_service.list_categories(project_id)
    await callback.message.edit_text(
        "📂 Категории проекта:",
        reply_markup=categories_list_kb(project_id, categories, is_owner=(role == Role.OWNER)),
    )
    await callback.answer()


@router.callback_query(CategoryCB.filter(F.action == "add"))
async def start_add_category(callback: CallbackQuery, callback_data: CategoryCB, state: FSMContext) -> None:
    await state.set_state(CategoryStates.waiting_new_category_name)
    await state.update_data(project_id=callback_data.project_id)
    await callback.message.edit_text("Введите название новой категории:")
    await callback.answer()


@router.message(CategoryStates.waiting_new_category_name)
async def process_add_category(
    message: Message, state: FSMContext, current_user: User | None, category_service: CategoryService
) -> None:
    data = await state.get_data()
    project_id = data["project_id"]
    try:
        name = validate_text(message.text or "", "Название категории", max_len=50)
        category = await category_service.add_category(
            project_id, current_user.telegram_id, _display_name(current_user), name
        )
    except (ValidationError, ServiceError) as e:
        await message.answer(str(e))
        return

    await state.clear()
    categories = await category_service.list_categories(project_id)
    await message.answer(
        f"✅ Категория «{category.name}» добавлена.",
        reply_markup=categories_list_kb(project_id, categories, is_owner=True),
    )


@router.callback_query(CategoryCB.filter(F.action == "manage"))
async def open_category_manage(
    callback: CallbackQuery, callback_data: CategoryCB, current_user: User | None, category_service: CategoryService, project_service: ProjectService
) -> None:
    try:
        await project_service.require_owner(callback_data.project_id, current_user.telegram_id)
        category = await category_service.get_category(callback_data.category_id)
    except ServiceError as e:
        await callback.answer(str(e), show_alert=True)
        return

    status = "активна ✅" if category.is_active else "отключена 🚫"
    await callback.message.edit_text(
        f"Категория: <b>{category.name}</b>\nСтатус: {status}",
        reply_markup=category_manage_kb(callback_data.project_id, category),
    )
    await callback.answer()


@router.callback_query(CategoryCB.filter(F.action == "rename"))
async def start_rename_category(callback: CallbackQuery, callback_data: CategoryCB, state: FSMContext) -> None:
    await state.set_state(CategoryStates.waiting_rename_value)
    await state.update_data(project_id=callback_data.project_id, category_id=callback_data.category_id)
    await callback.message.edit_text("Введите новое название категории:")
    await callback.answer()


@router.message(CategoryStates.waiting_rename_value)
async def process_rename_category(
    message: Message, state: FSMContext, current_user: User | None, category_service: CategoryService
) -> None:
    data = await state.get_data()
    project_id, category_id = data["project_id"], data["category_id"]
    try:
        name = validate_text(message.text or "", "Название категории", max_len=50)
        category = await category_service.rename_category(
            project_id, current_user.telegram_id, _display_name(current_user), category_id, name
        )
    except (ValidationError, ServiceError) as e:
        await message.answer(str(e))
        return

    await state.clear()
    await message.answer(
        f"✅ Категория переименована в «{category.name}».",
        reply_markup=category_manage_kb(project_id, category),
    )


@router.callback_query(CategoryCB.filter(F.action == "toggle"))
async def toggle_category(
    callback: CallbackQuery, callback_data: CategoryCB, current_user: User | None, category_service: CategoryService, project_service: ProjectService
) -> None:
    try:
        category = await category_service.toggle_active(
            callback_data.project_id, current_user.telegram_id, _display_name(current_user), callback_data.category_id
        )
    except ServiceError as e:
        await callback.answer(str(e), show_alert=True)
        return

    status = "включена ✅" if category.is_active else "отключена 🚫"
    await callback.answer(f"Категория {status}.")
    await callback.message.edit_text(
        f"Категория: <b>{category.name}</b>\nСтатус: {status}",
        reply_markup=category_manage_kb(callback_data.project_id, category),
    )


@router.callback_query(CategoryCB.filter(F.action == "noop"))
async def category_noop(callback: CallbackQuery) -> None:
    await callback.answer("Только владелец может управлять категориями.", show_alert=False)
