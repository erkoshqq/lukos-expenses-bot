from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards.callback_data import CategoryCB, ExpenseCB, NavCB
from keyboards.categories_kb import choose_category_kb
from keyboards.expenses_kb import (
    comment_step_kb,
    confirm_delete_kb,
    edit_fields_kb,
    expense_card_kb,
    expenses_list_kb,
)
from models.user import User
from services.category_service import CategoryService
from services.exceptions import ServiceError
from services.expense_service import EDITABLE_FIELDS, FIELD_LABELS, ExpenseService
from states.states import ExpenseAddStates, ExpenseEditStates
from utils.formatters import format_expense_card
from utils.logger import get_logger
from utils.validators import ValidationError, parse_amount, validate_text

logger = get_logger(__name__)

router = Router(name="expenses")


def _display_name(user: User | None) -> str:
    if not user:
        return "неизвестный"
    return user.full_name or user.username or str(user.telegram_id)


# ------------------------------------------------------------------ #
# Список расходов (с пагинацией)
# ------------------------------------------------------------------ #
async def render_expenses_list(
    callback: CallbackQuery, project_id: str, actor_id: int, page: int, expense_service: ExpenseService
) -> None:
    try:
        result = await expense_service.get_expenses_page(project_id, actor_id, page)
    except ServiceError as e:
        await callback.answer(str(e), show_alert=True)
        return

    if result.total_count == 0:
        text = "📄 В этом проекте пока нет расходов."
    else:
        text = f"📄 Расходы проекта (всего: {result.total_count}):"

    await callback.message.edit_text(
        text,
        reply_markup=expenses_list_kb(project_id, result.items, result.page, result.total_pages),
    )
    await callback.answer()


@router.callback_query(ExpenseCB.filter(F.action == "page"))
async def paginate_expenses(
    callback: CallbackQuery, callback_data: ExpenseCB, current_user: User | None, expense_service: ExpenseService
) -> None:
    await render_expenses_list(callback, callback_data.project_id, current_user.telegram_id, callback_data.page, expense_service)


@router.callback_query(ExpenseCB.filter(F.action == "noop"))
async def expense_noop(callback: CallbackQuery) -> None:
    await callback.answer()


# ------------------------------------------------------------------ #
# Карточка расхода
# ------------------------------------------------------------------ #
async def render_expense_card(
    callback: CallbackQuery, project_id: str, expense_id: str, actor_id: int, expense_service: ExpenseService
) -> None:
    try:
        expense = await expense_service.get_expense_card(project_id, actor_id, expense_id)
    except ServiceError as e:
        await callback.answer(str(e), show_alert=True)
        return

    await callback.message.edit_text(
        format_expense_card(expense), reply_markup=expense_card_kb(project_id, expense_id)
    )
    await callback.answer()


@router.callback_query(ExpenseCB.filter(F.action == "open"))
async def open_expense(
    callback: CallbackQuery, callback_data: ExpenseCB, current_user: User | None, expense_service: ExpenseService
) -> None:
    await render_expense_card(callback, callback_data.project_id, callback_data.expense_id, current_user.telegram_id, expense_service)


# ------------------------------------------------------------------ #
# Добавление расхода (FSM)
# ------------------------------------------------------------------ #
async def start_add_expense(callback: CallbackQuery, project_id: str, state: FSMContext) -> None:
    await state.set_state(ExpenseAddStates.waiting_amount)
    await state.update_data(project_id=project_id)
    await callback.message.edit_text("Шаг 1/4. Введите сумму расхода:")
    await callback.answer()


@router.message(ExpenseAddStates.waiting_amount)
async def process_amount(message: Message, state: FSMContext) -> None:
    try:
        amount = parse_amount(message.text or "")
    except ValidationError as e:
        await message.answer(str(e))
        return
    await state.update_data(amount=amount)
    await state.set_state(ExpenseAddStates.waiting_description)
    await message.answer("Шаг 2/4. Введите описание расхода:")


@router.message(ExpenseAddStates.waiting_description)
async def process_description(message: Message, state: FSMContext, category_service: CategoryService) -> None:
    try:
        description = validate_text(message.text or "", "Описание", max_len=300)
    except ValidationError as e:
        await message.answer(str(e))
        return

    data = await state.get_data()
    project_id = data["project_id"]
    await state.update_data(description=description)
    await state.set_state(ExpenseAddStates.waiting_category)

    categories = await category_service.list_categories(project_id, only_active=True)
    if not categories:
        await message.answer(
            "В проекте нет активных категорий. Обратитесь к владельцу проекта, чтобы он их добавил."
        )
        await state.clear()
        return

    await message.answer(
        "Шаг 3/4. Выберите категорию:", reply_markup=choose_category_kb(project_id, categories)
    )


@router.callback_query(CategoryCB.filter(F.action == "choose"), ExpenseAddStates.waiting_category)
async def process_category_choice(
    callback: CallbackQuery, callback_data: CategoryCB, state: FSMContext, category_service: CategoryService
) -> None:
    try:
        category = await category_service.get_category(callback_data.category_id)
    except ServiceError as e:
        await callback.answer(str(e), show_alert=True)
        return

    await state.update_data(category=category.name)
    await state.set_state(ExpenseAddStates.waiting_comment)
    await callback.message.edit_text(
        "Шаг 4/4. Добавить комментарий к расходу?",
        reply_markup=comment_step_kb(callback_data.project_id),
    )
    await callback.answer()


@router.callback_query(ExpenseCB.filter(F.action == "comment_skip"), ExpenseAddStates.waiting_comment)
async def process_comment_skip(
    callback: CallbackQuery, current_user: User | None, state: FSMContext, expense_service: ExpenseService
) -> None:
    await _finalize_expense(callback.message, current_user, state, expense_service, comment="", via_callback=callback)


@router.callback_query(ExpenseCB.filter(F.action == "comment_add"), ExpenseAddStates.waiting_comment)
async def process_comment_add(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ExpenseAddStates.waiting_comment_text)
    await callback.message.edit_text("Введите текст комментария:")
    await callback.answer()


@router.message(ExpenseAddStates.waiting_comment_text)
async def process_comment_text(message: Message, current_user: User | None, state: FSMContext, expense_service: ExpenseService) -> None:
    try:
        comment = validate_text(message.text or "", "Комментарий", max_len=300)
    except ValidationError as e:
        await message.answer(str(e))
        return
    await _finalize_expense(message, current_user, state, expense_service, comment=comment, via_callback=None)


async def _finalize_expense(
    message: Message,
    current_user: User | None,
    state: FSMContext,
    expense_service: ExpenseService,
    comment: str,
    via_callback: CallbackQuery | None,
) -> None:
    data = await state.get_data()
    try:
        expense = await expense_service.add_expense(
            project_id=data["project_id"],
            actor_id=current_user.telegram_id,
            actor_display=_display_name(current_user),
            amount=data["amount"],
            description=data["description"],
            category=data["category"],
            comment=comment,
        )
    except ServiceError as e:
        await message.answer(str(e))
        await state.clear()
        return

    await state.clear()
    text = "✅ Расход добавлен!\n\n" + format_expense_card(expense)
    kb = expense_card_kb(data["project_id"], expense.expense_id)
    if via_callback is not None:
        await via_callback.message.edit_text(text, reply_markup=kb)
        await via_callback.answer()
    else:
        await message.answer(text, reply_markup=kb)


# ------------------------------------------------------------------ #
# Редактирование расхода
# ------------------------------------------------------------------ #
@router.callback_query(ExpenseCB.filter(F.action == "edit_menu"))
async def open_edit_menu(callback: CallbackQuery, callback_data: ExpenseCB) -> None:
    await callback.message.edit_text(
        "Что вы хотите изменить?",
        reply_markup=edit_fields_kb(callback_data.project_id, callback_data.expense_id),
    )
    await callback.answer()


@router.callback_query(ExpenseCB.filter(F.action == "edit_field"))
async def choose_edit_field(
    callback: CallbackQuery, callback_data: ExpenseCB, state: FSMContext, category_service: CategoryService
) -> None:
    field = callback_data.field
    if field not in EDITABLE_FIELDS:
        await callback.answer("Неизвестное поле.", show_alert=True)
        return

    await state.set_state(ExpenseEditStates.waiting_new_value)
    await state.update_data(project_id=callback_data.project_id, expense_id=callback_data.expense_id, field=field)

    if field == "category":
        categories = await category_service.list_categories(callback_data.project_id, only_active=True)
        await callback.message.edit_text(
            "Выберите новую категорию:",
            reply_markup=choose_category_kb(callback_data.project_id, categories),
        )
    else:
        await callback.message.edit_text(f"Введите новое значение поля «{FIELD_LABELS[field]}»:")
    await callback.answer()


@router.callback_query(CategoryCB.filter(F.action == "choose"), ExpenseEditStates.waiting_new_value)
async def process_edit_category_choice(
    callback: CallbackQuery,
    callback_data: CategoryCB,
    state: FSMContext,
    current_user: User | None,
    category_service: CategoryService,
    expense_service: ExpenseService,
) -> None:
    data = await state.get_data()
    try:
        category = await category_service.get_category(callback_data.category_id)
        expense = await expense_service.edit_field(
            data["project_id"], current_user.telegram_id, _display_name(current_user),
            data["expense_id"], "category", category.name,
        )
    except ServiceError as e:
        await callback.answer(str(e), show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        "✅ Изменено.\n\n" + format_expense_card(expense),
        reply_markup=expense_card_kb(data["project_id"], expense.expense_id),
    )
    await callback.answer()


@router.message(ExpenseEditStates.waiting_new_value)
async def process_edit_value(
    message: Message, state: FSMContext, current_user: User | None, expense_service: ExpenseService
) -> None:
    data = await state.get_data()
    field = data["field"]
    raw = message.text or ""

    try:
        if field == "amount":
            value: str | float = parse_amount(raw)
        elif field == "description":
            value = validate_text(raw, "Описание", max_len=300)
        elif field == "comment":
            value = validate_text(raw, "Комментарий", min_len=0, max_len=300) if raw.strip() else ""
        else:
            await message.answer("Это поле редактируется через кнопки категории.")
            return

        expense = await expense_service.edit_field(
            data["project_id"], current_user.telegram_id, _display_name(current_user),
            data["expense_id"], field, value,
        )
    except (ValidationError, ServiceError) as e:
        await message.answer(str(e))
        return

    await state.clear()
    await message.answer(
        "✅ Изменено.\n\n" + format_expense_card(expense),
        reply_markup=expense_card_kb(data["project_id"], expense.expense_id),
    )


# ------------------------------------------------------------------ #
# Удаление расхода
# ------------------------------------------------------------------ #
@router.callback_query(ExpenseCB.filter(F.action == "delete"))
async def confirm_delete_expense(callback: CallbackQuery, callback_data: ExpenseCB) -> None:
    await callback.message.edit_text(
        "Вы уверены, что хотите удалить этот расход?",
        reply_markup=confirm_delete_kb(callback_data.project_id, callback_data.expense_id),
    )
    await callback.answer()


@router.callback_query(ExpenseCB.filter(F.action == "confirm_delete"))
async def do_delete_expense(
    callback: CallbackQuery, callback_data: ExpenseCB, current_user: User | None, expense_service: ExpenseService
) -> None:
    try:
        await expense_service.delete_expense(
            callback_data.project_id, current_user.telegram_id, _display_name(current_user), callback_data.expense_id
        )
    except ServiceError as e:
        await callback.answer(str(e), show_alert=True)
        return

    await callback.answer("Расход удалён.")
    await render_expenses_list(callback, callback_data.project_id, current_user.telegram_id, 0, expense_service)
