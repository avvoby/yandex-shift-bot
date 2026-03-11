"""
Сервис рассылок.

Что умеет:
- отправлять текст;
- отправлять текст + фото;
- отправлять текст + документ;
- отправлять только документ;
- работать по списку Telegram ID;
- работать по всем зарегистрированным пользователям.

Также здесь есть логика "аккуратной" рассылки пачками.
"""

import asyncio
import logging
from typing import Any

from aiogram import Bot
from aiogram.types import FSInputFile

from app.config import settings
from app.services.sheets import sheets_service
from app.utils.helpers import chunk_list

logger = logging.getLogger(__name__)


class BroadcasterService:
    """
    Сервис для отправки сообщений пользователям.
    """

    async def _send_one(
        self,
        bot: Bot,
        telegram_id: int,
        message_type: str,
        message_text: str,
        attachment_file_id: str = "",
    ) -> bool:
        """
        Отправка одного сообщения одному пользователю.
        Возвращает True / False по результату.
        """
        try:
            if message_type == "text":
                await bot.send_message(chat_id=telegram_id, text=message_text)
                return True

            if message_type == "text_photo":
                await bot.send_photo(
                    chat_id=telegram_id,
                    photo=attachment_file_id,
                    caption=message_text or "",
                )
                return True

            if message_type == "text_document":
                await bot.send_document(
                    chat_id=telegram_id,
                    document=attachment_file_id,
                    caption=message_text or "",
                )
                return True

            if message_type == "document":
                await bot.send_document(
                    chat_id=telegram_id,
                    document=attachment_file_id,
                    caption=message_text or "",
                )
                return True

            logger.warning("Неизвестный тип сообщения: %s", message_type)
            return False

        except Exception as exc:
            logger.warning(
                "Не удалось отправить сообщение пользователю %s: %s",
                telegram_id,
                exc,
            )
            return False

    async def send_broadcast(
        self,
        bot: Bot,
        recipient_ids: list[int],
        message_type: str,
        message_text: str,
        attachment_file_id: str = "",
        chunk_size: int | None = None,
        delay_between_chunks: float = 0.7,
    ) -> dict[str, Any]:
        """
        Массовая рассылка.

        chunk_size нужен, чтобы не пытаться отправить всё мгновенно.
        Это безопаснее для Telegram API.
        """
        if chunk_size is None:
            chunk_size = settings.DEFAULT_BROADCAST_CHUNK_SIZE

        recipient_ids = list(dict.fromkeys(recipient_ids))  # убираем дубли, сохраняя порядок

        success_count = 0
        fail_count = 0

        for chunk in chunk_list(recipient_ids, chunk_size):
            for telegram_id in chunk:
                ok = await self._send_one(
                    bot=bot,
                    telegram_id=telegram_id,
                    message_type=message_type,
                    message_text=message_text,
                    attachment_file_id=attachment_file_id,
                )
                if ok:
                    success_count += 1
                else:
                    fail_count += 1

            # Небольшая пауза между пачками
            await asyncio.sleep(delay_between_chunks)

        return {
            "recipient_count": len(recipient_ids),
            "success_count": success_count,
            "fail_count": fail_count,
        }

    def get_all_registered_user_ids(self) -> list[int]:
        """
        Возвращает список telegram_id всех зарегистрированных пользователей.
        """
        users = sheets_service.get_all_users()
        result: list[int] = []

        for user in users:
            status = str(user.get("registration_status", "")).strip().lower()
            is_blocked = str(user.get("is_blocked", "")).strip().lower()

            if status != "registered":
                continue

            if is_blocked in {"true", "1", "yes", "да"}:
                continue

            try:
                result.append(int(str(user.get("telegram_id", "")).strip()))
            except (TypeError, ValueError):
                continue

        return result


broadcaster_service = BroadcasterService()
