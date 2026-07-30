"""
Конфигурация приложения. Все параметры читаются из переменных окружения (.env).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _get_env(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(
            f"Обязательная переменная окружения '{name}' не задана. "
            f"Проверьте файл .env (см. .env.example)."
        )
    return value or ""


@dataclass(frozen=True)
class Settings:
    # Telegram
    bot_token: str = field(default_factory=lambda: _get_env("BOT_TOKEN", required=True))

    # Google Sheets
    google_sheet_id: str = field(default_factory=lambda: _get_env("GOOGLE_SHEET_ID", required=True))
    # Путь к JSON-файлу сервисного аккаунта Google (Service Account credentials)
    google_credentials_path: str = field(
        default_factory=lambda: _get_env("GOOGLE_CREDENTIALS_PATH", "credentials.json")
    )
    # Альтернатива: JSON-содержимое сервисного аккаунта прямо в переменной окружения
    google_credentials_json: str = field(
        default_factory=lambda: _get_env("GOOGLE_CREDENTIALS_JSON", "")
    )

    # Логирование
    log_level: str = field(default_factory=lambda: _get_env("LOG_LEVEL", "INFO"))
    log_file: str = field(default_factory=lambda: _get_env("LOG_FILE", "bot.log"))

    # Health-сервер (для Render.com + UptimeRobot)
    health_host: str = field(default_factory=lambda: _get_env("HEALTH_HOST", "0.0.0.0"))
    health_port: int = field(default_factory=lambda: int(_get_env("PORT", "8080")))

    # Пагинация списка расходов
    expenses_page_size: int = 10

    # Категории по умолчанию для нового проекта
    default_categories: tuple[str, ...] = (
        "Материалы",
        "Инструменты",
        "Транспорт",
        "Работа",
        "Прочее",
    )

    @property
    def credentials_path(self) -> Path:
        return Path(self.google_credentials_path)


settings = Settings()
