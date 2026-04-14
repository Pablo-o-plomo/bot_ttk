from __future__ import annotations

import logging
import sys

from telegram.ext import Application

from config import BOT_TOKEN, ensure_directories
from database import init_db
from handlers.bot import register_handlers


def configure_logging() -> None:
    logging.basicConfig(
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        level=logging.INFO,
    )


def main() -> None:
    configure_logging()

    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан. Укажите токен в переменной окружения BOT_TOKEN.")

    ensure_directories()
    init_db()

    application = Application.builder().token(BOT_TOKEN).build()
    register_handlers(application)

    logging.getLogger(__name__).info("Бот запущен в режиме polling")
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"Ошибка запуска: {exc}", file=sys.stderr)
        raise
