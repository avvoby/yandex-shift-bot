"""
Файл конфигурации проекта.

Что здесь происходит:
- читаем переменные из файла .env
- сохраняем их в удобный объект settings
- потом во всем проекте обращаемся к settings.BOT_TOKEN и т.д.

Это удобнее, чем постоянно читать .env вручную в разных местах.
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
load_dotenv()


@dataclass
class Settings:
    """
    Класс со всеми основными настройками проекта.
    """

    BOT_TOKEN: str
    GOOGLE_SHEETS_ID: str
    GOOGLE_CREDENTIALS_FILE: str
    TIMEZONE: str
    DEFAULT_CACHE_MINUTES: int
    DEFAULT_BROADCAST_CHUNK_SIZE: int
    LOG_LEVEL: str


def load_settings() -> Settings:
    """
    Читаем настройки из .env и возвращаем объект Settings.
    Если какого-то обязательного параметра нет, бот не должен стартовать молча.
    """
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    google_sheets_id = os.getenv("GOOGLE_SHEETS_ID", "").strip()
    google_credentials_file = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json").strip()
    timezone = os.getenv("TIMEZONE", "Europe/Berlin").strip()
    default_cache_minutes = int(os.getenv("DEFAULT_CACHE_MINUTES", "10"))
    default_broadcast_chunk_size = int(os.getenv("DEFAULT_BROADCAST_CHUNK_SIZE", "20"))
    log_level = os.getenv("LOG_LEVEL", "INFO").strip()

    if not bot_token:
        raise ValueError("Не задан BOT_TOKEN в .env")

    if not google_sheets_id:
        raise ValueError("Не задан GOOGLE_SHEETS_ID в .env")

    return Settings(
        BOT_TOKEN=bot_token,
        GOOGLE_SHEETS_ID=google_sheets_id,
        GOOGLE_CREDENTIALS_FILE=google_credentials_file,
        TIMEZONE=timezone,
        DEFAULT_CACHE_MINUTES=default_cache_minutes,
        DEFAULT_BROADCAST_CHUNK_SIZE=default_broadcast_chunk_size,
        LOG_LEVEL=log_level,
    )


# Глобальный объект настроек.
settings = load_settings()
