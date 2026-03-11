"""
Клавиатуры для обычного пользователя.

Здесь находятся:
- главное меню исполнителя
- кнопки FAQ
- кнопки "назад"
- кнопки для информационных блоков
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def get_registration_reply_keyboard() -> ReplyKeyboardMarkup:
    """
    Простая reply-клавиатура на этапе регистрации.
    Пока без специальных кнопок, но можно расширить позже.
    """
    return ReplyKeyboardMarkup(
        keyboard=[],
        resize_keyboard=True,
    )


def get_main_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """
    Главное меню пользователя.
    Если пользователь — админ, добавляем кнопку входа в админ-меню.
    """
    keyboard = [
        [KeyboardButton(text="Частые вопросы и ответы")],
        [KeyboardButton(text="Еще задания по мерчендайзингу")],
        [KeyboardButton(text="Telegram-чат поддержки")],
        [KeyboardButton(text="Документ для допуска на объект")],
        [KeyboardButton(text="Обучение")],
        [KeyboardButton(text="Задать вопрос")],
    ]

    if is_admin:
        keyboard.append([KeyboardButton(text="Админ-меню")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Выберите раздел",
    )


def get_back_to_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Универсальная клавиатура с кнопкой возврата в главное меню.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Назад в главное меню")],
        ],
        resize_keyboard=True,
    )


def get_faq_categories_keyboard(categories: list[str]) -> InlineKeyboardMarkup:
    """
    Клавиатура со списком категорий FAQ.
    """
    buttons = [
        [InlineKeyboardButton(text=category, callback_data=f"faq_category:{category}")]
        for category in categories
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="faq_back_to_main")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_faq_questions_keyboard(category: str, questions: list[dict]) -> InlineKeyboardMarkup:
    """
    Клавиатура со списком вопросов внутри категории.
    """
    buttons = []
    for item in questions:
        question = item.get("question", "")
        buttons.append(
            [InlineKeyboardButton(
                text=question,
                callback_data=f"faq_question:{category}:{question}",
            )]
        )

    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="faq_back_to_categories")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_faq_answer_keyboard(category: str) -> InlineKeyboardMarkup:
    """
    Кнопки под ответом FAQ.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад к вопросам", callback_data=f"faq_back_to_questions:{category}")],
            [InlineKeyboardButton(text="🏠 В главное меню", callback_data="faq_back_to_main")],
        ]
    )


def build_content_buttons(buttons_data: list[dict]) -> InlineKeyboardMarkup | None:
    """
    Создает inline-кнопки для информационных блоков из данных Google Sheets.

    Ожидаемый формат:
    [
      {"text": "Открыть", "url": "https://example.com"},
      {"text": "Чат", "url": "https://t.me/example"}
    ]
    """
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
