"""
Сервис для работы с контентом из Google Sheets.

Важно:
- автоперечитывание таблицы отключено для ускорения работы;
- данные загружаются:
  1) при старте бота
  2) вручную по кнопке админа "Обновить контент сейчас"
"""

import json
import logging
from typing import Any

from app.services.cache import SimpleCache
from app.services.sheets import sheets_service
from app.utils.helpers import safe_int

logger = logging.getLogger(__name__)


class ContentService:
    CONTENT_KEY = "content"
    FAQ_KEY = "faq"
    SETTINGS_KEY = "settings"
    ADMINS_KEY = "admins"
    FIRST_DAY_KEY = "first_day_flow"
    CLIENTS_KEY = "client_sections"

    def __init__(self) -> None:
        self.cache = SimpleCache()

    async def force_reload(self) -> None:
        logger.info("Принудительное обновление контента...")

        sheets_service.ensure_required_sheets()

        content_rows = sheets_service.get_all_records("content")
        faq_rows = sheets_service.get_all_records("faq")
        settings_dict = sheets_service.get_settings_dict()
        admin_ids = sheets_service.get_active_admin_ids()

        # first_day_flow и client_sections могут появиться позже — не падаем, если листов ещё нет
        try:
            first_day_rows = sheets_service.get_all_records("first_day_flow")
        except Exception:
            first_day_rows = []

        try:
            client_rows = sheets_service.get_all_records("client_sections")
        except Exception:
            client_rows = []

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

        # FAQ
        faq_categories: list[dict[str, Any]] = []
        category_map: dict[str, dict[str, Any]] = {}

        for row in faq_rows:
            category = str(row.get("category", "")).strip()
            question = str(row.get("question", "")).strip()
            answer = str(row.get("answer", "")).strip()
            sort_order_category = safe_int(row.get("sort_order_category"), 0)
            sort_order_question = safe_int(row.get("sort_order_question"), 0)

            if not category or not question:
                continue

            if category not in category_map:
                category_map[category] = {
                    "category": category,
                    "sort_order_category": sort_order_category,
                    "questions": [],
                }

            category_map[category]["questions"].append(
                {
                    "question": question,
                    "answer": answer,
                    "sort_order_question": sort_order_question,
                }
            )

        faq_categories = list(category_map.values())
        faq_categories.sort(key=lambda x: (x["sort_order_category"], x["category"]))

        for item in faq_categories:
            item["questions"].sort(key=lambda x: (x["sort_order_question"], x["question"]))

        # first_day_flow
        first_day_steps = []
        for row in first_day_rows:
            step = safe_int(row.get("step"), 0)
            title = str(row.get("title", "")).strip()
            text = str(row.get("text", "")).strip()
            buttons_json = str(row.get("buttons_json", "")).strip()

            buttons = []
            if buttons_json:
                try:
                    buttons = json.loads(buttons_json)
                except json.JSONDecodeError:
                    logger.warning("Не удалось распарсить buttons_json в first_day_flow, step=%s", step)

            if step <= 0:
                continue

            first_day_steps.append(
                {
                    "step": step,
                    "title": title,
                    "text": text,
                    "buttons": buttons,
                }
            )

        first_day_steps.sort(key=lambda x: x["step"])

        # client_sections
        clients_map: dict[str, list[dict[str, Any]]] = {}
        for row in client_rows:
            client_name = str(row.get("client_name", "")).strip()
            section_key = str(row.get("section_key", "")).strip()
            section_title = str(row.get("section_title", "")).strip()
            text = str(row.get("text", "")).strip()
            buttons_json = str(row.get("buttons_json", "")).strip()
            file_id = str(row.get("file_id", "")).strip()
            sort_order = safe_int(row.get("sort_order"), 0)

            if not client_name or not section_key or not section_title:
                continue

            buttons = []
            if buttons_json:
                try:
                    buttons = json.loads(buttons_json)
                except json.JSONDecodeError:
                    logger.warning("Не удалось распарсить buttons_json для client=%s, section=%s", client_name, section_key)

            if client_name not in clients_map:
                clients_map[client_name] = []

            clients_map[client_name].append(
                {
                    "section_key": section_key,
                    "section_title": section_title,
                    "text": text,
                    "buttons": buttons,
                    "file_id": file_id,
                    "sort_order": sort_order,
                }
            )

        client_list = []
        for client_name, sections in clients_map.items():
            sections.sort(key=lambda x: (x["sort_order"], x["section_title"]))
            client_list.append(
                {
                    "client_name": client_name,
                    "sections": sections,
                }
            )

        client_list.sort(key=lambda x: x["client_name"])

        self.cache.set(self.CONTENT_KEY, content_map)
        self.cache.set(self.FAQ_KEY, faq_categories)
        self.cache.set(self.SETTINGS_KEY, settings_dict)
        self.cache.set(self.ADMINS_KEY, admin_ids)
        self.cache.set(self.FIRST_DAY_KEY, first_day_steps)
        self.cache.set(self.CLIENTS_KEY, client_list)

        logger.info("Контент успешно обновлен.")

    async def get_content_item(self, key: str) -> dict[str, Any]:
        content_map = self.cache.get(self.CONTENT_KEY) or {}
        return content_map.get(key, {})

    async def get_text(self, key: str, default: str = "") -> str:
        item = await self.get_content_item(key)
        return item.get("text", "") or default

    async def get_title(self, key: str, default: str = "") -> str:
        item = await self.get_content_item(key)
        return item.get("title", "") or default

    async def get_buttons(self, key: str) -> list[dict[str, Any]]:
        item = await self.get_content_item(key)
        buttons = item.get("buttons", [])
        return buttons if isinstance(buttons, list) else []

    async def get_settings(self) -> dict[str, str]:
        return self.cache.get(self.SETTINGS_KEY) or {}

    async def get_admin_ids(self) -> list[int]:
        return self.cache.get(self.ADMINS_KEY) or []

    async def is_admin(self, telegram_id: int) -> bool:
        admin_ids = await self.get_admin_ids()
        return telegram_id in admin_ids

    async def get_faq_categories(self) -> list[dict[str, Any]]:
        return self.cache.get(self.FAQ_KEY) or []

    async def get_faq_category_by_index(self, index: int) -> dict[str, Any] | None:
        categories = await self.get_faq_categories()
        if index < 0 or index >= len(categories):
            return None
        return categories[index]

    async def get_first_day_steps(self) -> list[dict[str, Any]]:
        return self.cache.get(self.FIRST_DAY_KEY) or []

    async def get_first_day_step(self, index: int) -> dict[str, Any] | None:
        steps = await self.get_first_day_steps()
        if index < 0 or index >= len(steps):
            return None
        return steps[index]

    async def get_clients(self) -> list[dict[str, Any]]:
        return self.cache.get(self.CLIENTS_KEY) or []

    async def get_client_by_index(self, index: int) -> dict[str, Any] | None:
        clients = await self.get_clients()
        if index < 0 or index >= len(clients):
            return None
        return clients[index]


content_service = ContentService()
