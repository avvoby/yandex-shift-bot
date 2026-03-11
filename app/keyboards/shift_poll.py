"""
Кнопки для опроса по смене.

Эти кнопки отправляются исполнителю после выборочной рассылки от админа.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_shift_poll_keyboard(campaign_id: str) -> InlineKeyboardMarkup:
    """
    Кнопки ответа на вопрос о выходе на смену.

    campaign_id нужен, чтобы понимать,
    к какой именно рассылке относится ответ пользователя.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Да, буду на задании",
                    callback_data=f"shift_answer:{campaign_id}:yes",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Нет, нужно отменить задание",
                    callback_data=f"shift_answer:{campaign_id}:no",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Есть вопрос",
                    callback_data=f"shift_answer:{campaign_id}:question",
                )
            ],
        ]
    )
