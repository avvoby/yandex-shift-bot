"""
Обработчики FAQ.

Логика:
1. Пользователь нажимает "Частые вопросы и ответы"
2. Бот показывает категории
3. Пользователь выбирает категорию
4. Бот показывает вопросы
5. Пользователь выбирает вопрос
6. Бот показывает ответ
"""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.keyboards.user import (
    get_faq_answer_keyboard,
    get_faq_categories_keyboard,
    get_faq_questions_keyboard,
    get_main_menu_keyboard,
)
from app.services.content import content_service
from app.services.sheets import sheets_service

router = Router()


async def _is_registered(telegram_id: int) -> bool:
    user = sheets_service.get_user_by_telegram_id(telegram_id)
    if not user:
        return False
    status = str(user.get("registration_status", "")).strip().lower()
    return status == "registered"


@router.message(F.text == "Частые вопросы и ответы")
async def faq_entry(message: Message) -> None:
    """
    Вход в FAQ.
    """
    if not await _is_registered(message.from_user.id):
        await message.answer("Сначала завершите регистрацию через /start")
        return

    sheets_service.update_user_last_seen(message.from_user.id)

    categories = await content_service.get_faq_categories()
    if not categories:
        await message.answer("FAQ пока не заполнен.")
        return

    await message.answer(
        "Выберите категорию вопроса:",
        reply_markup=get_faq_categories_keyboard(categories),
    )


@router.callback_query(F.data == "faq_back_to_main")
async def faq_back_to_main(callback: CallbackQuery) -> None:
    """
    Возврат в главное меню.
    """
    is_admin = await content_service.is_admin(callback.from_user.id)
    main_menu_text = await content_service.get_text(
        "main_menu_text",
        default="Выберите нужный раздел.",
    )

    if callback.message:
        await callback.message.answer(
            main_menu_text,
            reply_markup=get_main_menu_keyboard(is_admin=is_admin),
        )

    await callback.answer()


@router.callback_query(F.data == "faq_back_to_categories")
async def faq_back_to_categories(callback: CallbackQuery) -> None:
    """
    Назад к категориям FAQ.
    """
    categories = await content_service.get_faq_categories()
    if callback.message:
        await callback.message.edit_text(
            "Выберите категорию вопроса:",
            reply_markup=get_faq_categories_keyboard(categories),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("faq_category:"))
async def faq_category_selected(callback: CallbackQuery) -> None:
    """
    Пользователь выбрал категорию FAQ.
    """
    data = callback.data or ""
    _, category = data.split("faq_category:", maxsplit=1)

    questions = await content_service.get_faq_questions(category)

    if not questions:
        await callback.answer("В этой категории пока нет вопросов.", show_alert=True)
        return

    if callback.message:
        await callback.message.edit_text(
            f"Категория: <b>{category}</b>\n\nВыберите вопрос:",
            reply_markup=get_faq_questions_keyboard(category, questions),
        )

    await callback.answer()


@router.callback_query(F.data.startswith("faq_back_to_questions:"))
async def faq_back_to_questions(callback: CallbackQuery) -> None:
    """
    Возврат к вопросам внутри категории.
    """
    data = callback.data or ""
    _, category = data.split("faq_back_to_questions:", maxsplit=1)

    questions = await content_service.get_faq_questions(category)

    if callback.message:
        await callback.message.edit_text(
            f"Категория: <b>{category}</b>\n\nВыберите вопрос:",
            reply_markup=get_faq_questions_keyboard(category, questions),
        )

    await callback.answer()


@router.callback_query(F.data.startswith("faq_question:"))
async def faq_question_selected(callback: CallbackQuery) -> None:
    """
    Пользователь выбрал вопрос — показываем ответ.
    """
    data = callback.data or ""
    # Формат: faq_question:{category}:{question}
    payload = data.split(":", maxsplit=2)

    if len(payload) != 3:
        await callback.answer("Некорректные данные вопроса.", show_alert=True)
        return

    _, category, question = payload

    questions = await content_service.get_faq_questions(category)

    answer_text = None
    for item in questions:
        if item.get("question") == question:
            answer_text = item.get("answer", "")
            break

    if answer_text is None:
        await callback.answer("Ответ не найден.", show_alert=True)
        return

    if callback.message:
        await callback.message.edit_text(
            f"<b>Вопрос:</b>\n{question}\n\n<b>Ответ:</b>\n{answer_text}",
            reply_markup=get_faq_answer_keyboard(category),
        )

    await callback.answer()
