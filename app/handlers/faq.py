"""
Обработчики FAQ.
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


def _is_private_message(message: Message) -> bool:
    return message.chat.type == "private"


def _is_private_callback(callback: CallbackQuery) -> bool:
    return callback.message is not None and callback.message.chat.type == "private"


async def _is_registered(telegram_id: int) -> bool:
    user = sheets_service.get_user_by_telegram_id(telegram_id)
    if not user:
        return False
    status = str(user.get("registration_status", "")).strip().lower()
    return status == "registered"


@router.message(F.text == "Частые вопросы и ответы")
async def faq_entry(message: Message) -> None:
    if not _is_private_message(message):
        return

    if not await _is_registered(message.from_user.id):
        await message.answer("Сначала завершите регистрацию через /start")
        return

    sheets_service.update_user_last_seen(message.from_user.id)

    categories = await content_service.get_faq_categories()
    category_names = [item["category"] for item in categories]

    if not category_names:
        await message.answer("FAQ пока не заполнен.")
        return

    await message.answer(
        "Выберите категорию вопроса:",
        reply_markup=get_faq_categories_keyboard(category_names),
    )


@router.callback_query(F.data == "faq_back_to_main")
async def faq_back_to_main(callback: CallbackQuery) -> None:
    if not _is_private_callback(callback):
        await callback.answer()
        return

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
    if not _is_private_callback(callback):
        await callback.answer()
        return

    categories = await content_service.get_faq_categories()
    category_names = [item["category"] for item in categories]

    if callback.message:
        await callback.message.edit_text(
            "Выберите категорию вопроса:",
            reply_markup=get_faq_categories_keyboard(category_names),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("faq_category:"))
async def faq_category_selected(callback: CallbackQuery) -> None:
    if not _is_private_callback(callback):
        await callback.answer()
        return

    data = callback.data or ""
    _, index_str = data.split("faq_category:", maxsplit=1)

    try:
        category_index = int(index_str)
    except ValueError:
        await callback.answer("Некорректные данные.", show_alert=True)
        return

    category_item = await content_service.get_faq_category_by_index(category_index)
    if not category_item:
        await callback.answer("Категория не найдена.", show_alert=True)
        return

    questions = category_item["questions"]

    if callback.message:
        await callback.message.edit_text(
            f"Категория: <b>{category_item['category']}</b>\n\nВыберите вопрос:",
            reply_markup=get_faq_questions_keyboard(category_index, questions),
        )

    await callback.answer()


@router.callback_query(F.data.startswith("faq_back_to_questions:"))
async def faq_back_to_questions(callback: CallbackQuery) -> None:
    if not _is_private_callback(callback):
        await callback.answer()
        return

    data = callback.data or ""
    _, index_str = data.split("faq_back_to_questions:", maxsplit=1)

    try:
        category_index = int(index_str)
    except ValueError:
        await callback.answer("Некорректные данные.", show_alert=True)
        return

    category_item = await content_service.get_faq_category_by_index(category_index)
    if not category_item:
        await callback.answer("Категория не найдена.", show_alert=True)
        return

    if callback.message:
        await callback.message.edit_text(
            f"Категория: <b>{category_item['category']}</b>\n\nВыберите вопрос:",
            reply_markup=get_faq_questions_keyboard(category_index, category_item["questions"]),
        )

    await callback.answer()


@router.callback_query(F.data.startswith("faq_question:"))
async def faq_question_selected(callback: CallbackQuery) -> None:
    if not _is_private_callback(callback):
        await callback.answer()
        return

    data = callback.data or ""
    payload = data.split(":", maxsplit=2)

    if len(payload) != 3:
        await callback.answer("Некорректные данные вопроса.", show_alert=True)
        return

    _, category_index_str, question_index_str = payload

    try:
        category_index = int(category_index_str)
        question_index = int(question_index_str)
    except ValueError:
        await callback.answer("Некорректный индекс вопроса.", show_alert=True)
        return

    category_item = await content_service.get_faq_category_by_index(category_index)
    if not category_item:
        await callback.answer("Категория не найдена.", show_alert=True)
        return

    questions = category_item["questions"]

    if question_index < 0 or question_index >= len(questions):
        await callback.answer("Вопрос не найден.", show_alert=True)
        return

    question = questions[question_index]["question"]
    answer_text = questions[question_index]["answer"]

    if callback.message:
        await callback.message.edit_text(
            f"<b>Вопрос:</b>\n{question}\n\n<b>Ответ:</b>\n{answer_text}",
            reply_markup=get_faq_answer_keyboard(category_index),
        )

    await callback.answer()
