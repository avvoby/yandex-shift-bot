"""
Общие обработчики.

Этот файл должен идти последним в подключении роутеров,
потому что здесь лежит "запасной" ответ на сообщения,
которые не подошли ни под один другой сценарий.
"""

from aiogram import Router
from aiogram.types import Message

from app.keyboards.user import get_main_menu_keyboard
from app.services.content import content_service
from app.services.sheets import sheets_service

router = Router()


async def _is_registered(telegram_id: int) -> bool:
    """
    Проверяем, зарегистрирован ли пользователь.
    """
    user = sheets_service.get_user_by_telegram_id(telegram_id)
    if not user:
        return False

    status = str(user.get("registration_status", "")).strip().lower()
    return status == "registered"


@router.message()
async def fallback_handler(message: Message) -> None:
    """
    Ответ по умолчанию на непонятные сообщения.
    """
    telegram_id = message.from_user.id

    if not await _is_registered(telegram_id):
        await message.answer(
            "Для начала работы с ботом, пожалуйста, используйте команду /start"
        )
        return

    sheets_service.update_user_last_seen(telegram_id)

    fallback_text = await content_service.get_text(
        "fallback_message",
        default=(
            "Мы не можем помочь в этом формате. "
            "Пожалуйста, обратитесь в чат поддержки в Telegram или в приложении."
        ),
    )

    is_admin = await content_service.is_admin(telegram_id)

    await message.answer(
        fallback_text,
        reply_markup=get_main_menu_keyboard(is_admin=is_admin),
    )
