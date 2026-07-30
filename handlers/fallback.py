"""
Fallback-роутер. Подключается в bot.py ПОСЛЕДНИМ, после всех остальных роутеров.
Если апдейт (сообщение или callback) не подошёл ни под один из специфичных хендлеров
(например, пользователь написал произвольный текст вне активного FSM-сценария,
или нажал на устаревшую inline-кнопку из старого сообщения) - сюда попадает
"страховка", чтобы бот не оставался немым и не оставлял "часики" на кнопке.
"""
from __future__ import annotations

from aiogram import Router
from aiogram.types import CallbackQuery, Message

from keyboards.main_menu import main_menu_kb
from utils.logger import get_logger

logger = get_logger(__name__)

router = Router(name="fallback")


@router.message()
async def unknown_message(message: Message) -> None:
    logger.info("Необработанное сообщение (fallback): %r", message.text)
    await message.answer(
        "Я не понял это сообщение 🤔\n"
        "Пожалуйста, пользуйтесь кнопками меню ниже, либо отправьте /start, "
        "чтобы вернуться в главное меню.",
        reply_markup=main_menu_kb(),
    )


@router.callback_query()
async def unknown_callback(callback: CallbackQuery) -> None:
    logger.info("Необработанный callback (fallback): %r", callback.data)
    await callback.answer(
        "Это меню устарело. Отправьте /start, чтобы открыть актуальное меню.",
        show_alert=True,
    )
