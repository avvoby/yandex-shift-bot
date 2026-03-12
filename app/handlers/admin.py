"""
Клавиатуры для админ-панели.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def get_admin_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Рассылка всем")],
            [KeyboardButton(text="Рассылка по списку Telegram ID")],
            [KeyboardButton(text="Опрос по смене")],
            [KeyboardButton(text="Загрузить файл для раздела заказчика")],
            [KeyboardButton(text="Обновить контент сейчас")],
            [KeyboardButton(text="Назад в главное меню")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие администратора",
    )


def get_broadcast_message_type_keyboard() -> ReplyKeyboardMarkup:
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
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить отправку", callback_data="broadcast_confirm"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel"),
            ]
        ]
    )


def get_shift_poll_confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Отправить опрос", callback_data="shift_poll_confirm"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="shift_poll_cancel"),
            ]
        ]
    )


def get_admin_clients_keyboard(client_names: list[str]) -> InlineKeyboardMarkup:
    rows = []

    for i, client_name in enumerate(client_names):
        rows.append([InlineKeyboardButton(text=client_name, callback_data=f"admin_file_client:{i}")])

    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin_file_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_admin_client_sections_keyboard(client_index: int, sections: list[dict]) -> InlineKeyboardMarkup:
    rows = []

    for i, section in enumerate(sections):
        title = str(section.get("section_title", "")).strip()
        rows.append([InlineKeyboardButton(text=title, callback_data=f"admin_file_section:{client_index}:{i}")])

    rows.append([InlineKeyboardButton(text="⬅️ Назад к заказчикам", callback_data="admin_file_back_to_clients")])
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin_file_cancel")])

    return InlineKeyboardMarkup(inline_keyboard=rows)
