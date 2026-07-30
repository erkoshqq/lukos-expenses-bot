from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards.callback_data import NavCB
from keyboards.main_menu import main_menu_kb
from models.user import User
from services.exceptions import ServiceError
from utils.logger import get_logger

logger = get_logger(__name__)

router = Router(name="common")


@router.message(Command("start"))
async def cmd_start(message: Message, current_user: User | None, state: FSMContext) -> None:
    await state.clear()
    name = current_user.full_name if current_user else (message.from_user.full_name if message.from_user else "друг")
    await message.answer(
        f"👋 Привет, {name}!\n\n"
        "Это бот для учёта расходов по проектам.\n"
        "Выберите действие в меню ниже.",
        reply_markup=main_menu_kb(),
    )


@router.message(Command("myid"))
async def cmd_myid(message: Message) -> None:
    tg_id = message.from_user.id if message.from_user else "?"
    await message.answer(
        f"Ваш Telegram ID: <code>{tg_id}</code>\n"
        "Отправьте его владельцу проекта, чтобы он мог добавить вас как участника."
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нечего отменять.")
        return
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=main_menu_kb())


@router.callback_query(NavCB.filter(F.to == "main"))
async def nav_main(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "🏠 Главное меню. Выберите действие:", reply_markup=main_menu_kb()
    )
    await callback.answer()


@router.callback_query(NavCB.filter(F.to == "projects"))
async def nav_projects(callback: CallbackQuery, callback_data: NavCB, current_user: User | None, state: FSMContext, project_service) -> None:
    await state.clear()
    from keyboards.main_menu import projects_list_kb

    projects = await project_service.get_user_projects(current_user.telegram_id)
    if not projects:
        await callback.message.edit_text(
            "У вас пока нет проектов. Создайте новый:",
            reply_markup=projects_list_kb([]),
        )
    else:
        await callback.message.edit_text("📁 Ваши проекты:", reply_markup=projects_list_kb(projects))
    await callback.answer()


@router.callback_query(NavCB.filter(F.to == "project"))
async def nav_project(callback: CallbackQuery, callback_data: NavCB, current_user: User | None, state: FSMContext, project_service) -> None:
    await state.clear()
    from handlers.projects import render_project_menu

    await render_project_menu(callback, callback_data.project_id, current_user, project_service)


@router.callback_query(NavCB.filter(F.to == "settings"))
async def nav_settings(callback: CallbackQuery, callback_data: NavCB, current_user: User | None, project_service) -> None:
    from handlers.projects import render_settings_menu

    await render_settings_menu(callback, callback_data.project_id, current_user, project_service)


@router.callback_query(NavCB.filter(F.to == "expenses"))
async def nav_expenses(callback: CallbackQuery, callback_data: NavCB, current_user: User | None, expense_service) -> None:
    from handlers.expenses import render_expenses_list

    await render_expenses_list(callback, callback_data.project_id, current_user.telegram_id, 0, expense_service)


@router.callback_query(NavCB.filter(F.to == "categories"))
async def nav_categories(callback: CallbackQuery, callback_data: NavCB, current_user: User | None, category_service, project_service) -> None:
    from handlers.categories import render_categories_list

    await render_categories_list(callback, callback_data.project_id, current_user, category_service, project_service)


@router.callback_query(NavCB.filter(F.to == "members"))
async def nav_members(callback: CallbackQuery, callback_data: NavCB, current_user: User | None, member_service, project_service) -> None:
    from handlers.members import render_members_list

    await render_members_list(callback, callback_data.project_id, current_user, member_service, project_service)


@router.callback_query(NavCB.filter(F.to == "expense_add"))
async def nav_expense_add(callback: CallbackQuery, callback_data: NavCB, state: FSMContext) -> None:
    from handlers.expenses import start_add_expense

    await start_add_expense(callback, callback_data.project_id, state)


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery) -> None:
    await callback.answer()


async def handle_service_error(callback: CallbackQuery, error: ServiceError) -> None:
    logger.info("ServiceError показан пользователю: %s", error)
    await callback.answer(str(error), show_alert=True)
