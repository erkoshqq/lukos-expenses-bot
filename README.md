# Telegram-бот учёта расходов по проектам

Бот на **aiogram 3.x** для учёта расходов внутри проектов. В качестве базы данных
используется **Google Sheets** (через `gspread`), что позволяет бухгалтерии
работать с данными напрямую в таблице, а в будущем — безболезненно перенести
хранение в PostgreSQL (вся работа с данными инкапсулирована в слое `repositories`).

## Архитектура

```
handlers/      — приём апдейтов Telegram, валидация ввода, вызов сервисов
services/      — бизнес-логика, проверка ролей (Owner/Member), журнал действий
repositories/  — единственный слой, знающий про структуру Google Sheets
models/        — dataclass-модели сущностей (User, Project, Member, Category, Expense, LogEntry)
keyboards/     — инлайн-клавиатуры и CallbackData-схемы
middlewares/   — авто-регистрация пользователя, логирование апдейтов
states/        — FSM-сценарии (aiogram StatesGroup)
health/        — aiohttp /health эндпоинт для UptimeRobot
```

## 1. Подготовка Google Sheets

1. Создайте новую Google Таблицу (пустую — листы бот создаст сам при первом запуске).
2. Скопируйте её ID из адресной строки:
   `https://docs.google.com/spreadsheets/d/ЭТОТ_ID/edit`
3. Зайдите в [Google Cloud Console](https://console.cloud.google.com/), создайте проект,
   включите **Google Sheets API** и **Google Drive API**.
4. Создайте сервисный аккаунт (Service Account), скачайте JSON-ключ.
5. Откройте вашу Google Таблицу и предоставьте доступ **Редактор** на e-mail сервисного
   аккаунта (он указан в поле `client_email` внутри скачанного JSON).

## 2. Установка и запуск локально

```bash
git clone <репозиторий>
cd expense_bot

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# заполните .env: BOT_TOKEN, GOOGLE_SHEET_ID
# положите скачанный JSON сервисного аккаунта рядом с ботом как credentials.json
# (или задайте его содержимое в GOOGLE_CREDENTIALS_JSON внутри .env)

python bot.py
```

При первом запуске бот автоматически создаст все необходимые листы
(«Пользователи», «Проекты», «Участники», «Категории», «Расходы», «Журнал действий»)
и заголовки колонок, если их ещё нет.

## 3. Переменные окружения

| Переменная | Обязательна | Описание |
|---|---|---|
| `BOT_TOKEN` | да | токен бота от @BotFather |
| `GOOGLE_SHEET_ID` | да | ID Google Таблицы |
| `GOOGLE_CREDENTIALS_PATH` | нет (по умолчанию `credentials.json`) | путь к JSON-ключу сервисного аккаунта |
| `GOOGLE_CREDENTIALS_JSON` | нет | JSON-ключ одной строкой (удобно для Render.com, приоритетнее `GOOGLE_CREDENTIALS_PATH`) |
| `LOG_LEVEL` | нет (`INFO`) | уровень логирования |
| `LOG_FILE` | нет (`bot.log`) | путь к файлу логов |
| `PORT` | нет (`8080`) | порт health-check сервера |

## 4. Деплой на Render.com

1. Запушьте проект в свой Git-репозиторий (GitHub/GitLab).
2. На [render.com](https://render.com) создайте **Background Worker** или **Web Service**
   (для health-check эндпоинта подойдёт **Web Service**, Render сам пробросит `PORT`).
3. Build command: `pip install -r requirements.txt`
4. Start command: `python bot.py`
5. В разделе **Environment** добавьте переменные: `BOT_TOKEN`, `GOOGLE_SHEET_ID`,
   `GOOGLE_CREDENTIALS_JSON` (содержимое JSON-ключа сервисного аккаунта одной строкой).
6. После деплоя Render выдаст публичный URL вида `https://your-service.onrender.com`.
   Эндпоинт здоровья: `https://your-service.onrender.com/health`.

## 5. UptimeRobot

Бесплатный план Render "засыпает" сервис без активности. Чтобы бот не "спал":

1. Зарегистрируйтесь на [uptimerobot.com](https://uptimerobot.com).
2. Создайте монитор типа **HTTP(s)**, URL — `https://your-service.onrender.com/health`.
3. Интервал проверки — 5 минут.

## 6. Использование бота

- `/start` — регистрация и главное меню.
- `/myid` — узнать свой Telegram ID (нужно для приглашения в проект владельцем).
- `/cancel` — отменить текущий пошаговый сценарий (FSM).

Основной сценарий: создать проект → пригласить участников → добавлять расходы →
просматривать/редактировать/удалять расходы → все действия фиксируются в
листе «Журнал действий».

## 7. Роли

- **Owner** (владелец) — полный доступ: управление участниками, категориями,
  переименование/архивирование проекта, плюс всё, что доступно Member.
- **Member** (участник) — просмотр, добавление, редактирование и удаление расходов.

## 8. Дальнейшее расширение

Чтобы заменить Google Sheets на PostgreSQL, потребуется переписать только классы
в `repositories/` (реализовать те же публичные методы поверх SQL-запросов).
Слои `services/` и `handlers/` останутся без изменений.
