"""
SheetsClient - единственный модуль, который напрямую работает с gspread.
Все обращения выполняются в отдельном потоке (asyncio.to_thread), т.к. gspread синхронный,
чтобы не блокировать event loop aiogram.

ВАЖНО про квоту Google Sheets API: по умолчанию у сервисного аккаунта лимит
60 запросов на ЧТЕНИЕ в минуту (и отдельно - на запись). Каждое открытие меню
в боте потенциально требует нескольких чтений (участники, проекты, категории...),
поэтому здесь реализованы два механизма защиты от 429 Too Many Requests:

1. Кэш объектов Worksheet по имени листа - без него gspread делает ДОПОЛНИТЕЛЬНЫЙ
   API-запрос (fetch_sheet_metadata) при КАЖДОМ обращении к листу, что удваивает
   расход квоты на пустом месте.
2. Короткоживущий (TTL) кэш результатов get_all_records на лист - в течение одного
   и того же апдейта (и следующих 2-3 секунд) один и тот же лист часто читается
   несколько раз подряд; кэш убирает эти повторные чтения. Кэш инвалидируется
   сразу после любой записи (append/update/delete) в соответствующий лист.
3. Retry с экспоненциальной паузой конкретно на ошибку 429 - на случай, если,
   несмотря на кэш, квота всё равно временно исчерпана (например, при резком
   всплеске активности нескольких пользователей одновременно).
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Имена листов
SHEET_USERS = "Пользователи"
SHEET_PROJECTS = "Проекты"
SHEET_MEMBERS = "Участники"
SHEET_CATEGORIES = "Категории"
SHEET_EXPENSES = "Расходы"
SHEET_LOG = "Журнал действий"

SHEET_HEADERS: dict[str, list[str]] = {}  # заполняется в bootstrap() из models, чтобы избежать циклических импортов

# Сколько секунд считать закэшированные данные листа актуальными
CACHE_TTL_SECONDS = 4.0

# Параметры retry при 429 Too Many Requests
MAX_RETRIES_ON_RATE_LIMIT = 5
RETRY_BASE_DELAY_SECONDS = 2.0


def _is_rate_limit_error(exc: Exception) -> bool:
    if isinstance(exc, gspread.exceptions.APIError):
        try:
            status = exc.response.status_code
        except Exception:
            status = None
        return status == 429 or "429" in str(exc) or "Quota exceeded" in str(exc)
    return False


class SheetsClient:
    """Синглтон-обёртка над gspread.Client и открытой таблицей."""

    _instance: "SheetsClient | None" = None

    def __init__(self) -> None:
        self._client: gspread.Client | None = None
        self._spreadsheet: gspread.Spreadsheet | None = None
        self._lock = asyncio.Lock()

        # Кэш объектов Worksheet, чтобы не дёргать fetch_sheet_metadata на каждый чих
        self._worksheets: dict[str, gspread.Worksheet] = {}
        self._worksheets_lock = asyncio.Lock()

        # TTL-кэш данных: sheet_name -> (unix_timestamp_записи, записи)
        self._data_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
        self._data_cache_lock = asyncio.Lock()

    @classmethod
    def instance(cls) -> "SheetsClient":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------ #
    # Инициализация
    # ------------------------------------------------------------------ #
    def _build_client_sync(self) -> gspread.Client:
        if settings.google_credentials_json:
            info = json.loads(settings.google_credentials_json)
            creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        else:
            creds = Credentials.from_service_account_file(
                str(settings.credentials_path), scopes=SCOPES
            )
        return gspread.authorize(creds)

    def _open_spreadsheet_sync(self) -> gspread.Spreadsheet:
        client = self._build_client_sync()
        self._client = client
        return client.open_by_key(settings.google_sheet_id)

    async def connect(self) -> None:
        async with self._lock:
            if self._spreadsheet is not None:
                return
            logger.info("Подключение к Google Sheets...")
            self._spreadsheet = await asyncio.to_thread(self._open_spreadsheet_sync)
            logger.info("Подключение к Google Sheets установлено.")

    async def bootstrap(self, sheets_headers: dict[str, list[str]]) -> None:
        """Создаёт недостающие листы и проставляет заголовки, если лист пустой."""
        await self.connect()
        await asyncio.to_thread(self._bootstrap_sync, sheets_headers)

    def _bootstrap_sync(self, sheets_headers: dict[str, list[str]]) -> None:
        assert self._spreadsheet is not None
        all_worksheets = self._spreadsheet.worksheets()
        existing_by_title = {ws.title: ws for ws in all_worksheets}

        for sheet_name, headers in sheets_headers.items():
            ws = existing_by_title.get(sheet_name)
            if ws is None:
                logger.info("Создаю недостающий лист: %s", sheet_name)
                ws = self._spreadsheet.add_worksheet(
                    title=sheet_name, rows=1000, cols=max(len(headers), 10)
                )
                ws.append_row(headers, value_input_option="USER_ENTERED")
            else:
                first_row = ws.row_values(1)
                if not first_row:
                    ws.append_row(headers, value_input_option="USER_ENTERED")

            # Сразу кладём в кэш, чтобы не резолвить лист заново при первом обращении
            self._worksheets[sheet_name] = ws

    # ------------------------------------------------------------------ #
    # Retry-обёртка на 429
    # ------------------------------------------------------------------ #
    async def _run_with_retry(self, func, *args, **kwargs):
        attempt = 0
        while True:
            try:
                return await asyncio.to_thread(func, *args, **kwargs)
            except Exception as exc:  # noqa: BLE001 - осознанно ловим широко, фильтруем ниже
                if _is_rate_limit_error(exc) and attempt < MAX_RETRIES_ON_RATE_LIMIT:
                    delay = RETRY_BASE_DELAY_SECONDS * (2 ** attempt)
                    logger.warning(
                        "Google Sheets API квота исчерпана (429), попытка %s/%s, "
                        "жду %.1f сек...",
                        attempt + 1, MAX_RETRIES_ON_RATE_LIMIT, delay,
                    )
                    await asyncio.sleep(delay)
                    attempt += 1
                    continue
                raise

    # ------------------------------------------------------------------ #
    # Доступ к листам (с кэшированием объекта Worksheet)
    # ------------------------------------------------------------------ #
    def _get_worksheet_sync(self, sheet_name: str) -> gspread.Worksheet:
        assert self._spreadsheet is not None, "Spreadsheet не инициализирован, вызовите connect()"
        ws = self._worksheets.get(sheet_name)
        if ws is not None:
            return ws
        ws = self._spreadsheet.worksheet(sheet_name)
        self._worksheets[sheet_name] = ws
        return ws

    async def _invalidate_data_cache(self, sheet_name: str) -> None:
        async with self._data_cache_lock:
            self._data_cache.pop(sheet_name, None)

    async def get_all_records(self, sheet_name: str) -> list[dict[str, Any]]:
        await self.connect()

        async with self._data_cache_lock:
            cached = self._data_cache.get(sheet_name)
            if cached is not None:
                cached_at, records = cached
                if time.monotonic() - cached_at < CACHE_TTL_SECONDS:
                    return records

        def _fetch() -> list[dict[str, Any]]:
            ws = self._get_worksheet_sync(sheet_name)
            return ws.get_all_records()

        records = await self._run_with_retry(_fetch)

        async with self._data_cache_lock:
            self._data_cache[sheet_name] = (time.monotonic(), records)
        return records

    async def append_row(self, sheet_name: str, row: list) -> None:
        await self.connect()

        def _append() -> None:
            ws = self._get_worksheet_sync(sheet_name)
            ws.append_row(row, value_input_option="USER_ENTERED")

        await self._run_with_retry(_append)
        await self._invalidate_data_cache(sheet_name)

    async def update_row(self, sheet_name: str, row_index: int, row: list) -> None:
        """row_index - номер строки в данных (1 = первая строка данных, без заголовка)."""
        await self.connect()

        def _update() -> None:
            ws = self._get_worksheet_sync(sheet_name)
            sheet_row = row_index + 1  # +1 за строку заголовка
            end_col = gspread.utils.rowcol_to_a1(1, len(row)).rstrip("1")
            cell_range = f"A{sheet_row}:{end_col}{sheet_row}"
            ws.update(cell_range, [row], value_input_option="USER_ENTERED")

        await self._run_with_retry(_update)
        await self._invalidate_data_cache(sheet_name)

    async def delete_row(self, sheet_name: str, row_index: int) -> None:
        """row_index - номер строки в данных (1 = первая строка данных, без заголовка)."""
        await self.connect()

        def _delete() -> None:
            ws = self._get_worksheet_sync(sheet_name)
            sheet_row = row_index + 1
            ws.delete_rows(sheet_row)

        await self._run_with_retry(_delete)
        await self._invalidate_data_cache(sheet_name)


def get_sheets_client() -> SheetsClient:
    return SheetsClient.instance()

