"""
Клавиатуры для обычного пользователя.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def get_registration_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[],
        resize_keyboard=True,
    )


def get_main_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """
    Новый порядок кнопок главного меню.
    """
    keyboard = [
        [KeyboardButton(text="Частые вопросы и ответы")],
        [KeyboardButton(text="Telegram-чат поддержки")],
        [KeyboardButton(text="Задать вопрос")],
        [KeyboardButton(text="Обучение")],
        [KeyboardButton(text="Особенности разных заказчиков")],
        [KeyboardButton(text="Еще задания по мерчандайзингу")],
        [KeyboardButton(text="Я первый раз на задании")],
    ]

    if is_admin:
        keyboard.append([KeyboardButton(text="Админ-меню")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Выберите раздел",
    )


def get_back_to_main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Назад в главное меню")],
        ],
        resize_keyboard=True,
    )


def get_faq_categories_keyboard(categories: list[str]) -> InlineKeyboardMarkup:
    """
    Категории FAQ: используем индекс, а не длинный текст.
    """
    buttons = []
    for i, category in enumerate(categories):
        buttons.append(
            [InlineKeyboardButton(text=category, callback_data=f"faq_category:{i}")]
        )

    buttons.append([InlineKeyboardButton(text="Не нашлось ответа на вопрос", callback_data="faq_no_answer")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="faq_back_to_main")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_faq_questions_keyboard(category_index: int, questions: list[dict]) -> InlineKeyboardMarkup:
    buttons = []

    for i, item in enumerate(questions):
        question = item.get("question", "")
        buttons.append(
            [InlineKeyboardButton(
                text=question,
                callback_data=f"faq_question:{category_index}:{i}",
            )]
        )

    buttons.append([InlineKeyboardButton(text="Не нашлось ответа на вопрос", callback_data="faq_no_answer")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="faq_back_to_categories")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_faq_answer_keyboard(category_index: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Не нашлось ответа на вопрос", callback_data="faq_no_answer")],
            [InlineKeyboardButton(text="⬅️ Назад к вопросам", callback_data=f"faq_back_to_questions:{category_index}")],
            [InlineKeyboardButton(text="🏠 В главное меню", callback_data="faq_back_to_main")],
        ]
    )


def build_content_buttons(buttons_data: list[dict]) -> InlineKeyboardMarkup | None:
    if not buttons_data:
        return None

    inline_buttons = []

    for item in buttons_data:
        text = str(item.get("text", "")).strip()
        url = str(item.get("url", "")).strip()

        if not text or not url:
            continue

        inline_buttons.append([InlineKeyboardButton(text=text, url=url)])

    if not inline_buttons:
        return None

    return InlineKeyboardMarkup(inline_keyboard=inline_buttons)


def get_consent_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Политика конфиденциальности",
                    url="https://yandex.ru/legal/confidential/ru/"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Пользовательское соглашение",
                    url="https://yandex.ru/legal/smena_termsofuse/"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Я согласен",
                    callback_data="consent_accept"
                )
            ]
        ]
    )


def get_first_day_step_keyboard(
    current_step_index: int,
    total_steps: int,
    buttons_data: list[dict] | None = None,
) -> InlineKeyboardMarkup:
    """
    Кнопки для сценария "Я первый раз на задании".
    """
    rows = []

    if buttons_data:
        for item in buttons_data:
            text = str(item.get("text", "")).strip()
            url = str(item.get("url", "")).strip()
            if text and url:
                rows.append([InlineKeyboardButton(text=text, url=url)])

    if current_step_index < total_steps - 1:
        rows.append([InlineKeyboardButton(text="Дальше", callback_data=f"first_day_next:{current_step_index + 1}")])

    rows.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="first_day_back_to_main")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_clients_keyboard(client_names: list[str]) -> InlineKeyboardMarkup:
    rows = []

    for i, client_name in enumerate(client_names):
        rows.append([InlineKeyboardButton(text=client_name, callback_data=f"client_open:{i}")])

    rows.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="clients_back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_client_sections_keyboard(client_index: int, sections: list[dict]) -> InlineKeyboardMarkup:
    rows = []

    for i, section in enumerate(sections):
        title = str(section.get("section_title", "")).strip()
        rows.append([InlineKeyboardButton(text=title, callback_data=f"client_section:{client_index}:{i}")])

    rows.append([InlineKeyboardButton(text="⬅️ Назад к заказчикам", callback_data="clients_back_to_clients")])
    rows.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="clients_back_to_main")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_client_section_actions_keyboard(
    client_index: int,
    buttons_data: list[dict] | None = None,
) -> InlineKeyboardMarkup:
    rows = []

    if buttons_data:
        for item in buttons_data:
            text = str(item.get("text", "")).strip()
            url = str(item.get("url", "")).strip()
            if text and url:
                rows.append([InlineKeyboardButton(text=text, url=url)])

    rows.append([InlineKeyboardButton(text="⬅️ Назад к разделам", callback_data=f"client_back_to_sections:{client_index}")])
    rows.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="clients_back_to_main")])

    return InlineKeyboardMarkup(inline_keyboard=rows)
