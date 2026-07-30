"""
Точка входа Telegram-бота учёта расходов по проектам.

Запуск:
    python bot.py
"""
from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ErrorEvent

from config.settings import settings
from handlers import categories as categories_handlers
from handlers import common as common_handlers
from handlers import expenses as expenses_handlers
from handlers import fallback as fallback_handlers
from handlers import members as members_handlers
from handlers import projects as projects_handlers
from health.server import run_health_server
from middlewares.auth_middleware import AuthMiddleware
from middlewares.logging_middleware import LoggingMiddleware
from models import category as category_model
from models import expense as expense_model
from models import log_entry as log_entry_model
from models import member as member_model
from models import project as project_model
from models import user as user_model
from repositories.category_repository import CategoryRepository
from repositories.expense_repository import ExpenseRepository
from repositories.log_repository import LogRepository
from repositories.member_repository import MemberRepository
from repositories.project_repository import ProjectRepository
from repositories.sheets_client import (
    SHEET_CATEGORIES,
    SHEET_EXPENSES,
    SHEET_LOG,
    SHEET_MEMBERS,
    SHEET_PROJECTS,
    SHEET_USERS,
    get_sheets_client,
)
from repositories.user_repository import UserRepository
from services.category_service import CategoryService
from services.expense_service import ExpenseService
from services.exceptions import ServiceError
from services.log_service import LogService
from services.member_service import MemberService
from services.project_service import ProjectService
from services.user_service import UserService
from utils.logger import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)


async def bootstrap_sheets() -> None:
    client = get_sheets_client()
    headers = {
        SHEET_USERS: user_model.HEADERS,
        SHEET_PROJECTS: project_model.HEADERS,
        SHEET_MEMBERS: member_model.HEADERS,
        SHEET_CATEGORIES: category_model.HEADERS,
        SHEET_EXPENSES: expense_model.HEADERS,
        SHEET_LOG: log_entry_model.HEADERS,
    }
    await client.bootstrap(headers)


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())

    # ---- Репозитории ----
    client = get_sheets_client()
    user_repo = UserRepository(client)
    project_repo = ProjectRepository(client)
    member_repo = MemberRepository(client)
    category_repo = CategoryRepository(client)
    expense_repo = ExpenseRepository(client)
    log_repo = LogRepository(client)

    # ---- Сервисы ----
    log_service = LogService(log_repo)
    user_service = UserService(user_repo)
    project_service = ProjectService(project_repo, member_repo, category_repo, log_service)
    member_service = MemberService(member_repo, project_service, user_service, log_service)
    category_service = CategoryService(category_repo, project_service, log_service)
    expense_service = ExpenseService(expense_repo, project_service, user_service, log_service)

    # ---- Внедрение зависимостей: сервисы доступны хендлерам как именованные аргументы ----
    dp["user_service"] = user_service
    dp["project_service"] = project_service
    dp["member_service"] = member_service
    dp["category_service"] = category_service
    dp["expense_service"] = expense_service
    dp["log_service"] = log_service

    # ---- Middlewares ----
    auth_mw = AuthMiddleware(user_service)
    logging_mw = LoggingMiddleware()
    dp.update.outer_middleware(logging_mw)
    dp.update.outer_middleware(auth_mw)

    # ---- Роутеры ----
    dp.include_router(common_handlers.router)
    dp.include_router(projects_handlers.router)
    dp.include_router(members_handlers.router)
    dp.include_router(categories_handlers.router)
    dp.include_router(expenses_handlers.router)

    # ВАЖНО: fallback-роутер подключается строго последним, чтобы не перехватывать
    # сообщения/callback'и, предназначенные для FSM-сценариев в других роутерах.
    dp.include_router(fallback_handlers.router)

    # ---- Глобальный обработчик ошибок ----
    @dp.errors()
    async def global_error_handler(event: ErrorEvent) -> bool:
        exception = event.exception
        update = event.update

        if isinstance(exception, ServiceError):
            # Бизнес-ошибки, не показанные локально, - минимально логируем
            logger.info("Необработанная ServiceError: %s", exception)
            try:
                if update.callback_query:
                    await update.callback_query.answer(str(exception), show_alert=True)
                elif update.message:
                    await update.message.answer(str(exception))
            except Exception:
                logger.exception("Не удалось отправить сообщение об ошибке пользователю")
            return True

        logger.exception("Непредвиденная ошибка при обработке апдейта: %s", exception, exc_info=exception)
        try:
            if update.callback_query:
                await update.callback_query.answer(
                    "Произошла непредвиденная ошибка. Попробуйте ещё раз.", show_alert=True
                )
            elif update.message:
                await update.message.answer("⚠️ Произошла непредвиденная ошибка. Попробуйте ещё раз.")
        except Exception:
            logger.exception("Не удалось отправить сообщение об ошибке пользователю")
        return True

    return dp


async def main() -> None:
    logger.info("Запуск бота учёта расходов...")

    await bootstrap_sheets()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = build_dispatcher()

    health_runner = await run_health_server()

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await health_runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")
