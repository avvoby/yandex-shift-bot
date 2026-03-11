"""
Сервис для работы с контентом из Google Sheets.

Что здесь хранится:
- content
- faq
- settings
- admins

Задача сервиса:
- загрузить данные из таблицы
- положить их в кэш
- отдавать их другим частям проекта
- уметь делать force reload по кнопке админа
"""

import json
import logging
from typing import Any

from app.config import settings
from app.services.cache import SimpleCache
from app.services.sheets import sheets_service
from app.utils.helpers import safe_int

logger = logging.getLogger(__name__)


class ContentService:
    """
    Центральный сервис контента.
    """

    CONTENT_KEY = "content"
    FAQ_KEY = "faq"
    SETTINGS_KEY = "settings"
    ADMINS_KEY = "admins"

    def __init__(self) -> None:
        self.cache = SimpleCache()

    async def force_reload(self) -> None:
        """
        Принудительно перечитываем все данные из Google Sheets.
        Это нужно:
        - при старте бота
        - при нажатии админом "Обновить контент сейчас"
        """
        logger.info("Принудительное обновление контента...")

        # На всякий случай сначала создаем недостающие листы
        sheets_service.ensure_required_sheets()

        content_rows = sheets_service.get_all_records("content")
        faq_rows = sheets_service.get_all_records("faq")
        settings_dict = sheets_service.get_settings_dict()
        admin_ids = sheets_service.get_active_admin_ids()

        content_map: dict[str, dict[str, Any]] = {}
        for row in content_rows:
            key = str(row.get("key", "")).strip()
            if not key:
                continue

            buttons_json = str(row.get("buttons_json", "")).strip()
            parsed_buttons = []

            if buttons_json:
                try:
                    parsed_buttons = json.loads(buttons_json)
                except json.JSONDecodeError:
                    logger.warning("Не удалось распарсить buttons_json для key=%s", key)

            content_map[key] = {
                "title": str(row.get("title", "")).strip(),
                "text": str(row.get("text", "")).strip(),
                "buttons": parsed_buttons,
                "updated_at": str(row.get("updated_at", "")).strip(),
            }

        faq_map: dict[str, list[dict[str, Any]]] = {}
        for row in faq_rows:
            category = str(row.get("category", "")).strip()
            question = str(row.get("question", "")).strip()
            answer = str(row.get("answer", "")).strip()
            sort_order_question = safe_int(row.get("sort_order_question"), 0)

            if not category or not question:
                continue

            if category not in faq_map:
                faq_map[category] = []

            faq_map[category].append(
                {
                    "question": question,
                    "answer": answer,
                    "sort_order_question": sort_order_question,
                }
            )

        # Сортируем вопросы внутри категории
        for category in faq_map:
            faq_map[category].sort(key=lambda x: (x["sort_order_question"], x["question"]))

        self.cache.set(self.CONTENT_KEY, content_map)
        self.cache.set(self.FAQ_KEY, faq_map)
        self.cache.set(self.SETTINGS_KEY, settings_dict)
        self.cache.set(self.ADMINS_KEY, admin_ids)

        logger.info("Контент успешно обновлен.")

    async def ensure_fresh(self) -> None:
        """
        Проверяем, не устарели ли данные.
        Если устарели — перечитываем.
        """
        settings_dict = self.cache.get(self.SETTINGS_KEY) or {}

        cache_minutes = safe_int(
            settings_dict.get("content_cache_minutes"),
            settings.DEFAULT_CACHE_MINUTES,
        )

        if (
            self.cache.is_expired(self.CONTENT_KEY, cache_minutes)
            or self.cache.is_expired(self.FAQ_KEY, cache_minutes)
            or self.cache.is_expired(self.SETTINGS_KEY, cache_minutes)
            or self.cache.is_expired(self.ADMINS_KEY, cache_minutes)
        ):
            await self.force_reload()

    async def get_content_item(self, key: str) -> dict[str, Any]:
        """
        Возвращает один контентный блок по ключу.
        """
        await self.ensure_fresh()
        content_map = self.cache.get(self.CONTENT_KEY) or {}
        return content_map.get(key, {})

    async def get_faq_categories(self) -> list[str]:
        """
        Возвращает список категорий FAQ.
        Пока сортируем просто по алфавиту.
        Потом можно улучшить по sort_order_category.
        """
        await self.ensure_fresh()
        faq_map = self.cache.get(self.FAQ_KEY) or {}
        return sorted(faq_map.keys())

    async def get_faq_questions(self, category: str) -> list[dict[str, Any]]:
        """
        Возвращает список вопросов внутри категории.
        """
        await self.ensure_fresh()
        faq_map = self.cache.get(self.FAQ_KEY) or {}
        return faq_map.get(category, [])

    async def get_settings(self) -> dict[str, str]:
        """
        Возвращает словарь настроек из листа settings.
        """
        await self.ensure_fresh()
        return self.cache.get(self.SETTINGS_KEY) or {}

    async def get_admin_ids(self) -> list[int]:
        """
        Возвращает список активных админов.
        """
        await self.ensure_fresh()
        return self.cache.get(self.ADMINS_KEY) or []

    async def is_admin(self, telegram_id: int) -> bool:
        """
        Проверка, является ли пользователь админом.
        """
        admin_ids = await self.get_admin_ids()
        return telegram_id in admin_ids

    async def get_text(self, key: str, default: str = "") -> str:
        """
        Удобный метод: получить только текст из content.
        """
        item = await self.get_content_item(key)
        text = item.get("text", "")
        return text or default

    async def get_title(self, key: str, default: str = "") -> str:
        """
        Удобный метод: получить только title из content.
        """
        item = await self.get_content_item(key)
        title = item.get("title", "")
        return title or default

    async def get_buttons(self, key: str) -> list[dict[str, Any]]:
        """
        Возвращает список кнопок для контентного блока.
        Формат ожидается такой:
        [
          {"text": "Открыть", "url": "https://..."},
          {"text": "Чат", "url": "https://..."}
        ]
        """
        item = await self.get_content_item(key)
        buttons = item.get("buttons", [])
        return buttons if isinstance(buttons, list) else []


# Один общий сервис контента
content_service = ContentService()
