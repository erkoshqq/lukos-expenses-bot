"""
Генерация уникальных идентификаторов и работа с датой/временем.
"""
from __future__ import annotations

import uuid
from datetime import datetime

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def new_id() -> str:
    """
    Короткий уникальный идентификатор (10 hex-символов = 40 бит).

    ВАЖНО: ID проектов/категорий/расходов используются внутри callback_data
    инлайн-кнопок, а Telegram ограничивает callback_data 64 байтами. Полный
    uuid4().hex (32 символа) не помещается в этот лимит, если в одной кнопке
    встречаются сразу два ID (например, project_id + expense_id). 10 hex-символов
    (~1 триллион комбинаций) дают пренебрежимо малую вероятность коллизий для
    реального масштаба использования и оставляют запас по длине callback_data.
    """
    return uuid.uuid4().hex[:10]


def now_str() -> str:
    """Текущая дата/время в виде строки для записи в таблицу."""
    return datetime.now().strftime(DATETIME_FORMAT)
