"""
Сервис для опроса по смене.

Что делает:
- создает campaign_id;
- рассылает вопрос с кнопками;
- хранит временные данные кампании в памяти;
- позволяет обработчику ответов понять,
  какой текст и какая дата были у конкретной рассылки.
"""

import asyncio
import logging
import uuid
from typing import Any

from aiogram import Bot

from app.keyboards.shift_poll import get_shift_poll_keyboard
from app.utils.helpers import chunk_list

logger = logging.getLogger(__name__)


class ShiftPollService:
    """
    Сервис опросов по смене.
    """

    def __init__(self) -> None:
        # Временное хранилище кампаний в памяти:
        # campaign_id -> {"shift_date": ..., "question_text": ...}
        # Для первой версии этого достаточно.
        self._campaigns: dict[str, dict[str, Any]] = {}

    def create_campaign(self, shift_date: str, question_text: str) -> str:
        """
        Создаем уникальный campaign_id и запоминаем данные кампании.
        """
        campaign_id = uuid.uuid4().hex[:12]
        self._campaigns[campaign_id] = {
            "shift_date": shift_date,
            "question_text": question_text,
        }
        return campaign_id

    def get_campaign(self, campaign_id: str) -> dict[str, Any] | None:
        """
        Возвращает данные кампании.
        """
        return self._campaigns.get(campaign_id)

    async def send_poll(
        self,
        bot: Bot,
        recipient_ids: list[int],
        shift_date: str,
        question_text: str,
        chunk_size: int = 20,
        delay_between_chunks: float = 0.7,
    ) -> dict[str, Any]:
        """
        Создает кампанию и отправляет опрос по списку пользователей.
        """
        campaign_id = self.create_campaign(
            shift_date=shift_date,
            question_text=question_text,
        )

        recipient_ids = list(dict.fromkeys(recipient_ids))

        success_count = 0
        fail_count = 0

        for chunk in chunk_list(recipient_ids, chunk_size):
            for telegram_id in chunk:
                try:
                    await bot.send_message(
                        chat_id=telegram_id,
                        text=question_text,
                        reply_markup=get_shift_poll_keyboard(campaign_id),
                    )
                    success_count += 1
                except Exception as exc:
                    logger.warning(
                        "Не удалось отправить опрос пользователю %s: %s",
                        telegram_id,
                        exc,
                    )
                    fail_count += 1

            await asyncio.sleep(delay_between_chunks)

        return {
            "campaign_id": campaign_id,
            "recipient_count": len(recipient_ids),
            "success_count": success_count,
            "fail_count": fail_count,
        }


shift_poll_service = ShiftPollService()
