"""
Главный файл запуска Telegram-бота.

Что делает этот файл:
1. Загружает настройки
2. Создает бота и диспетчер
3. Подключает все обработчики
4. Подгружает контент из Google Sheets
5. Запускает long polling
"""

import asyncio
import logging

from app.bot import create_bot_and_dispatcher
from app.config import settings
from app.handlers import register_all_routers
from app.services.content import content_service
from app.utils.logger import setup_logging


async def main() -> None:
    """
    Основная функция запуска приложения.
    """
    setup_logging(settings.LOG_LEVEL)
    logging.info("Запуск бота...")

    # Создаем объекты aiogram
    bot, dp = create_bot_and_dispatcher()

    # Подключаем все роутеры
    register_all_routers(dp)

    # Перед стартом пробуем подгрузить данные из Google Sheets
    try:
        await content_service.force_reload()
        logging.info("Контент успешно загружен при старте.")
    except Exception as exc:
        logging.exception("Ошибка первичной загрузки контента: %s", exc)

    # Запускаем long polling
    logging.info("Бот запущен.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен вручную.")
