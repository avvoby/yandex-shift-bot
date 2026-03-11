"""
Обработчики регистрации пользователя.

Сценарий:
1. Пользователь нажимает /start
2. Если не зарегистрирован — просим ФИО
3. Потом просим телефон
4. Сохраняем пользователя в Google Sheets
5. Показываем главное меню
"""

import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.keyboards.user import (
    get_back_to_main_menu_keyboard,
    get_main_menu_keyboard,
)
from app.services.content import content_service
from app.services.sheets import sheets_service
from app.states.registration import RegistrationStates
from app.utils.phone import is_valid_russian_phone, normalize_phone

router = Router()
logger = logging.getLogger(__name__)


async def _is_registered(telegram_id: int) -> bool:
    """
    Проверяем, зарегистрирован ли пользователь.
    """
    user = sheets_service.get_user_by_telegram_id(telegram_id)
    if not user:
        return False

    status = str(user.get("registration_status", "")).strip().lower()
    return status == "registered"


@router.message(CommandStart())
async def start_command(message: Message, state: FSMContext) -> None:
    """
    Точка входа в бота.
    """
    await state.clear()

    telegram_id = message.from_user.id
    is_registered = await _is_registered(telegram_id)

    if is_registered:
        # Обновим last_seen_at и покажем меню
        sheets_service.update_user_last_seen(telegram_id)
        is_admin = await content_service.is_admin(telegram_id)

        welcome_text = await content_service.get_text(
            "main_menu_text",
            default="Выберите нужный раздел.",
        )

        await message.answer(
            welcome_text,
            reply_markup=get_main_menu_keyboard(is_admin=is_admin),
        )
        return

    # Если пользователь еще не зарегистрирован
    registration_welcome = await content_service.get_text(
        "registration_welcome",
        default=(
            "Здравствуйте! Для работы с ботом нужно пройти регистрацию.\n\n"
            "Пожалуйста, введите ваши ФИО полностью."
        ),
    )

    await message.answer(
        registration_welcome,
        reply_markup=get_back_to_main_menu_keyboard(),
    )
    await state.set_state(RegistrationStates.waiting_for_full_name)


@router.message(RegistrationStates.waiting_for_full_name, F.text)
async def registration_get_full_name(message: Message, state: FSMContext) -> None:
    """
    Получаем ФИО пользователя.
    """
    full_name = message.text.strip()

    if len(full_name) < 5:
        await message.answer("Пожалуйста, введите корректные ФИО полностью.")
        return

    await state.update_data(full_name=full_name)

    await message.answer(
        "Теперь введите номер телефона, привязанный к приложению Яндекс Смена.\n\n"
        "Формат: +7XXXXXXXXXX"
    )
    await state.set_state(RegistrationStates.waiting_for_phone)


@router.message(RegistrationStates.waiting_for_phone, F.text)
async def registration_get_phone(message: Message, state: FSMContext) -> None:
    """
    Получаем телефон, проверяем формат, сохраняем пользователя.
    """
    raw_phone = message.text.strip()
    normalized_phone = normalize_phone(raw_phone)

    if not is_valid_russian_phone(normalized_phone):
        await message.answer(
            "Номер телефона введен неверно.\n"
            "Пожалуйста, отправьте его в формате: +7XXXXXXXXXX"
        )
        return

    data = await state.get_data()
    full_name = data.get("full_name", "").strip()

    if not full_name:
        await message.answer("Ошибка регистрации. Пожалуйста, начните заново командой /start")
        await state.clear()
        return

    from_user = message.from_user

    sheets_service.upsert_user(
        telegram_id=from_user.id,
        username=from_user.username or "",
        first_name=from_user.first_name or "",
        last_name=from_user.last_name or "",
        full_name_entered=full_name,
        phone_entered=normalized_phone,
    )

    await state.clear()

    is_admin = await content_service.is_admin(from_user.id)
    main_menu_text = await content_service.get_text(
        "main_menu_text",
        default="Регистрация завершена. Выберите нужный раздел.",
    )

    await message.answer(
        "Спасибо! Регистрация успешно завершена.",
        reply_markup=get_main_menu_keyboard(is_admin=is_admin),
    )
    await message.answer(
        main_menu_text,
        reply_markup=get_main_menu_keyboard(is_admin=is_admin),
    )


@router.message(
    RegistrationStates.waiting_for_full_name,
    F.text == "Назад в главное меню"
)
@router.message(
    RegistrationStates.waiting_for_phone,
    F.text == "Назад в главное меню"
)
async def registration_back_to_start(message: Message, state: FSMContext) -> None:
    """
    Во время регистрации пользователь не может попасть в меню,
    потому что регистрация обязательна.
    Поэтому просто начинаем регистрацию сначала.
    """
    await state.clear()

    await message.answer(
        "Для использования бота нужно завершить регистрацию.\n\n"
        "Пожалуйста, введите ваши ФИО полностью."
    )
    await state.set_state(RegistrationStates.waiting_for_full_name)
