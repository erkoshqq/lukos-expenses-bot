"""
Валидация пользовательского ввода.
"""
from __future__ import annotations


class ValidationError(Exception):
    """Ошибка валидации пользовательского ввода."""


def parse_amount(raw: str) -> float:
    """
    Парсит сумму расхода из текста.
    Допускает запятую как десятичный разделитель, пробелы-разделители тысяч.
    """
    if raw is None:
        raise ValidationError("Сумма не может быть пустой.")

    cleaned = raw.strip().replace(" ", "").replace(",", ".")
    if not cleaned:
        raise ValidationError("Сумма не может быть пустой.")

    try:
        value = float(cleaned)
    except ValueError:
        raise ValidationError(
            "Не удалось распознать сумму. Введите число, например: 1500 или 1500.50"
        )

    if value <= 0:
        raise ValidationError("Сумма должна быть больше нуля.")

    if value > 1_000_000_000:
        raise ValidationError("Сумма слишком большая. Проверьте ввод.")

    return round(value, 2)


def validate_text(raw: str, field_name: str, min_len: int = 1, max_len: int = 500) -> str:
    """Валидирует текстовое поле (описание, название, комментарий)."""
    if raw is None:
        raise ValidationError(f"Поле «{field_name}» не может быть пустым.")

    cleaned = raw.strip()
    if len(cleaned) < min_len:
        raise ValidationError(f"Поле «{field_name}» не может быть пустым.")
    if len(cleaned) > max_len:
        raise ValidationError(
            f"Поле «{field_name}» слишком длинное (максимум {max_len} символов)."
        )
    return cleaned


def validate_telegram_id(raw: str) -> int:
    """Валидирует Telegram ID, введённый вручную владельцем проекта."""
    cleaned = raw.strip().lstrip("@")
    if not cleaned.isdigit():
        raise ValidationError(
            "Telegram ID должен быть числом. Попросите участника прислать команду /myid боту."
        )
    return int(cleaned)
