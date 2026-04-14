# Telegram-бот для технологических карт блюд

Готовый MVP-проект Telegram-бота на Python, который помогает собрать технологическую карту блюда, обработать фото, расшифровать голос и сформировать печатный HTML для A4.

## Возможности

- Создание блюда по шагам:
  - название
  - итоговый выход
  - фото блюда
  - голосовое описание
  - комментарий
- Расшифровка `voice` и `audio` через OpenAI Speech-to-Text.
- Ручная проверка/редактирование расшифровки пользователем.
- Добавление компонентов (п/ф) и ингредиентов вручную.
- Обработка фото через `rembg` + `Pillow`:
  - попытка убрать фон
  - компоновка блюда на белом фоне
  - fallback на исходное фото при ошибке
- Генерация автономного HTML:
  - шаблон A4
  - print CSS
  - встроенное изображение через data URI
- Хранение данных в SQLite через SQLAlchemy.
- Готовность к запуску локально и деплою на Railway Worker (polling).

## Стек

- Python 3.11+
- python-telegram-bot
- SQLite
- SQLAlchemy
- Jinja2
- python-dotenv
- OpenAI API
- rembg + Pillow

## Структура проекта

```text
project/
├── main.py
├── config.py
├── database.py
├── models.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── handlers/
│   ├── __init__.py
│   └── bot.py
├── services/
│   ├── __init__.py
│   ├── dish_service.py
│   ├── html_service.py
│   ├── speech_service.py
│   └── image_service.py
├── templates/
│   └── dish_card.html
├── uploads/
│   └── .gitkeep
└── exports/
    └── .gitkeep
```

> В репозитории корень и есть `project/` из схемы выше.

## Как получить BOT_TOKEN

1. Откройте Telegram и найдите `@BotFather`.
2. Выполните команду `/newbot`.
3. Придумайте имя и username бота.
4. Скопируйте выданный токен и сохраните в `BOT_TOKEN`.

## Как указать OPENAI_API_KEY

1. Создайте API-ключ в OpenAI Dashboard.
2. Добавьте его в переменную окружения `OPENAI_API_KEY`.
3. Если ключ не указан, бот не падает, но сообщает, что расшифровка голоса недоступна.

## Установка и локальный запуск

### 1) Клонировать проект

```bash
git clone <your_repo_url>
cd <repo_folder>
```

### 2) Создать виртуальное окружение

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows PowerShell
```

### 3) Установить зависимости

```bash
pip install -r requirements.txt
```

### 4) Создать `.env`

```bash
cp .env.example .env
```

Заполните значения:

```env
BOT_TOKEN=your_telegram_bot_token_here
OPENAI_API_KEY=your_openai_api_key_here
DATABASE_URL=sqlite:///./bot.db
UPLOADS_DIR=./uploads
EXPORTS_DIR=./exports
```

### 5) Запустить бота

```bash
python main.py
```

## Деплой на Railway (Worker, polling)

### 1) Подготовка

- Залейте репозиторий в GitHub.
- В Railway создайте новый проект из GitHub-репозитория.

### 2) Добавьте Volume

1. В сервисе откройте вкладку `Volumes`.
2. Создайте Volume.
3. Укажите mount path: `/data`.

### 3) Переменные окружения в Railway

Добавьте:

```env
BOT_TOKEN=your_telegram_bot_token_here
OPENAI_API_KEY=your_openai_api_key_here
DATABASE_URL=sqlite:////data/bot.db
UPLOADS_DIR=/data/uploads
EXPORTS_DIR=/data/exports
```

### 4) Команда запуска

`Start Command`:

```bash
python main.py
```

### 5) Важные настройки

- Режим: Worker.
- Бот работает через polling (webhook не нужен).
- Public domain для бота не требуется.

## UX-логика бота

### Главное меню

- Создать блюдо
- Мои блюда
- Помощь

### Внутри блюда

- Загрузить фото
- Загрузить голос
- Добавить компонент
- Предпросмотр
- Сформировать HTML
- Редактировать блюдо
- Удалить блюдо
- Назад

## Устойчивость

- Папки uploads/exports создаются автоматически.
- База данных создается автоматически при запуске.
- Если `BOT_TOKEN` отсутствует — понятная ошибка запуска.
- Если `OPENAI_API_KEY` отсутствует — голосовая расшифровка недоступна, но бот работает.
- Если обработка фото падает — используется исходник.
- Если пользователь отправляет неподходящий тип сообщения — бот просит корректный формат.

## Примечания по MVP

- Это именно Telegram-бот (не веб-приложение).
- Рецепт и структура компонентов подтверждаются вручную пользователем.
- PDF не генерируется — экспорт только в HTML, подготовленный к печати A4.
