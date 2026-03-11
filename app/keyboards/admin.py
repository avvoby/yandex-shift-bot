"""
Клавиатуры для админ-панели.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def get_admin_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Главное меню администратора.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Рассылка всем")],
            [KeyboardButton(text="Рассылка по списку Telegram ID")],
            [KeyboardButton(text="Опрос по смене")],
            [KeyboardButton(text="Обновить контент сейчас")],
            [KeyboardButton(text="Назад в главное меню")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие администратора",
    )


def get_broadcast_message_type_keyboard() -> ReplyKeyboardMarkup:
    """
    Выбор типа сообщения для рассылки.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Только текст")],
            [KeyboardButton(text="Текст + фото")],
            [KeyboardButton(text="Текст + документ")],
            [KeyboardButton(text="Только документ")],
            [KeyboardButton(text="Отмена")],
        ],
        resize_keyboard=True,
    )


def get_broadcast_confirmation_keyboard() -> InlineKeyboardMarkup:
    """
    Подтверждение отправки рассылки.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить отправку", callback_data="broadcast_confirm"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel"),
            ]
        ]
    )


def get_shift_poll_confirmation_keyboard() -> InlineKeyboardMarkup:
    """
    Подтверждение отправки опроса по смене.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Отправить опрос", callback_data="shift_poll_confirm"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="shift_poll_cancel"),
            ]
        ]
    )
