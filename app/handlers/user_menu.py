"""
Обработчики главного меню пользователя.
"""

from aiogram import F, Router
from aiogram.types import Message

from app.keyboards.user import build_content_buttons, get_main_menu_keyboard
from app.services.content import content_service
from app.services.sheets import sheets_service

router = Router()


def _is_private_chat(message: Message) -> bool:
    return message.chat.type == "private"


async def _is_registered(telegram_id: int) -> bool:
    user = sheets_service.get_user_by_telegram_id(telegram_id)
    if not user:
        return False
    status = str(user.get("registration_status", "")).strip().lower()
    return status == "registered"


async def _send_content_block(message: Message, content_key: str, default_text: str) -> None:
    item = await content_service.get_content_item(content_key)
    text = item.get("text") or default_text
    buttons = item.get("buttons", [])
    markup = build_content_buttons(buttons)
    await message.answer(text, reply_markup=markup)


@router.message(F.text == "Назад в главное меню")
async def back_to_main_menu(message: Message) -> None:
    if not _is_private_chat(message):
        return

    if not await _is_registered(message.from_user.id):
        await message.answer("Сначала завершите регистрацию через /start")
        return

    is_admin = await content_service.is_admin(message.from_user.id)
    main_menu_text = await content_service.get_text(
        "main_menu_text",
        default="Выберите нужный раздел.",
    )

    await message.answer(
        main_menu_text,
        reply_markup=get_main_menu_keyboard(is_admin=is_admin),
    )


@router.message(F.text == "Еще задания по мерчандайзингу")
async def more_jobs_handler(message: Message) -> None:
    if not _is_private_chat(message):
        return

    if not await _is_registered(message.from_user.id):
        await message.answer("Сначала завершите регистрацию через /start")
        return

    await _send_content_block(
        message,
        content_key="more_jobs",
        default_text="Раздел с дополнительными заданиями пока не заполнен.",
    )


@router.message(F.text == "Telegram-чат поддержки")
async def support_chat_handler(message: Message) -> None:
    if not _is_private_chat(message):
        return

    if not await _is_registered(message.from_user.id):
        await message.answer("Сначала завершите регистрацию через /start")
        return

    await _send_content_block(
        message,
        content_key="support_chat",
        default_text="Раздел чата поддержки пока не заполнен.",
    )


@router.message(F.text == "Обучение")
async def training_handler(message: Message) -> None:
    if not _is_private_chat(message):
        return

    if not await _is_registered(message.from_user.id):
        await message.answer("Сначала завершите регистрацию через /start")
        return

    await _send_content_block(
        message,
        content_key="training",
        default_text="Раздел обучения пока не заполнен.",
    )
