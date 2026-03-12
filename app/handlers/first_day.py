"""
Сценарий "Я первый раз на задании".
"""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.keyboards.user import get_first_day_step_keyboard, get_main_menu_keyboard
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


async def _send_first_day_step(target_message: Message, step_index: int) -> None:
    step = await content_service.get_first_day_step(step_index)
    steps = await content_service.get_first_day_steps()

    if not step:
        await target_message.answer("Сценарий пока не заполнен.")
        return

    title = str(step.get("title", "")).strip()
    text = str(step.get("text", "")).strip()
    buttons = step.get("buttons", [])

    full_text = f"<b>{title}</b>\n\n{text}" if title else text

    await target_message.answer(
        full_text,
        reply_markup=get_first_day_step_keyboard(
            current_step_index=step_index,
            total_steps=len(steps),
            buttons_data=buttons,
        ),
    )


@router.message(F.text == "Я первый раз на задании")
async def first_day_entry(message: Message) -> None:
    if not _is_private_message(message):
        return

    if not await _is_registered(message.from_user.id):
        await message.answer("Сначала завершите регистрацию через /start")
        return

    await _send_first_day_step(message, 0)


@router.callback_query(F.data.startswith("first_day_next:"))
async def first_day_next(callback: CallbackQuery) -> None:
    if not _is_private_callback(callback):
        await callback.answer()
        return

    _, index_str = callback.data.split("first_day_next:", maxsplit=1)

    try:
        step_index = int(index_str)
    except ValueError:
        await callback.answer("Некорректный шаг.", show_alert=True)
        return

    if callback.message:
        await _send_first_day_step(callback.message, step_index)

    await callback.answer()


@router.callback_query(F.data == "first_day_back_to_main")
async def first_day_back_to_main(callback: CallbackQuery) -> None:
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
