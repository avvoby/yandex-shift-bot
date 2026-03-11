"""
Обработчики админ-меню.

Что умеет:
- открыть админ-меню;
- отправить рассылку всем;
- отправить рассылку по списку Telegram ID;
- запустить опрос по смене;
- принудительно обновить контент из Google Sheets.
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Document, Message, PhotoSize

from app.keyboards.admin import (
    get_admin_menu_keyboard,
    get_broadcast_confirmation_keyboard,
    get_broadcast_message_type_keyboard,
    get_shift_poll_confirmation_keyboard,
)
from app.keyboards.user import get_main_menu_keyboard
from app.services.broadcaster import broadcaster_service
from app.services.content import content_service
from app.services.shift_poll import shift_poll_service
from app.services.sheets import sheets_service
from app.states.admin_broadcast import AdminBroadcastStates
from app.states.admin_shift_poll import AdminShiftPollStates
from app.utils.helpers import now_iso, parse_telegram_ids

router = Router()


async def _is_registered(telegram_id: int) -> bool:
    user = sheets_service.get_user_by_telegram_id(telegram_id)
    if not user:
        return False
    status = str(user.get("registration_status", "")).strip().lower()
    return status == "registered"


async def _require_admin(message: Message) -> bool:
    """
    Проверяем, что пользователь — админ.
    Если нет — отвечаем и возвращаем False.
    """
    if not await _is_registered(message.from_user.id):
        await message.answer("Сначала завершите регистрацию через /start")
        return False

    is_admin = await content_service.is_admin(message.from_user.id)
    if not is_admin:
        await message.answer("У вас нет доступа к админ-меню.")
        return False

    return True


@router.message(F.text == "Админ-меню")
async def admin_menu_entry(message: Message, state: FSMContext) -> None:
    """
    Вход в админ-меню.
    """
    await state.clear()

    if not await _require_admin(message):
        return

    await message.answer(
        "Админ-меню. Выберите действие:",
        reply_markup=get_admin_menu_keyboard(),
    )


@router.message(F.text == "Обновить контент сейчас")
async def admin_reload_content(message: Message) -> None:
    """
    Принудительное обновление контента из Google Sheets.
    """
    if not await _require_admin(message):
        return

    await message.answer("Обновляю контент из Google Sheets...")

    try:
        await content_service.force_reload()
        await message.answer("Готово. Контент успешно обновлен.")
    except Exception as exc:
        await message.answer(f"Ошибка при обновлении контента: {exc}")


# =========================
# Обычная рассылка
# =========================

@router.message(F.text == "Рассылка всем")
async def broadcast_all_start(message: Message, state: FSMContext) -> None:
    """
    Старт сценария рассылки всем.
    """
    if not await _require_admin(message):
        return

    await state.clear()
    await state.update_data(target_type="all", target_ids=[])

    await message.answer(
        "Вы выбрали: рассылка всем.\n\nТеперь выберите тип сообщения:",
        reply_markup=get_broadcast_message_type_keyboard(),
    )
    await state.set_state(AdminBroadcastStates.waiting_for_message_type)


@router.message(F.text == "Рассылка по списку Telegram ID")
async def broadcast_by_ids_start(message: Message, state: FSMContext) -> None:
    """
    Старт сценария рассылки по списку Telegram ID.
    """
    if not await _require_admin(message):
        return

    await state.clear()
    await message.answer(
        "Отправьте список Telegram ID, каждый с новой строки.\n\nПример:\n123456789\n987654321"
    )
    await state.set_state(AdminBroadcastStates.waiting_for_target_ids)


@router.message(AdminBroadcastStates.waiting_for_target_ids, F.text)
async def broadcast_get_target_ids(message: Message, state: FSMContext) -> None:
    """
    Получаем список целевых Telegram ID для рассылки.
    """
    ids = parse_telegram_ids(message.text)

    if not ids:
        await message.answer("Не удалось распознать ни одного Telegram ID. Попробуйте еще раз.")
        return

    await state.update_data(target_type="ids", target_ids=ids)

    await message.answer(
        f"Получено {len(ids)} Telegram ID.\n\nТеперь выберите тип сообщения:",
        reply_markup=get_broadcast_message_type_keyboard(),
    )
    await state.set_state(AdminBroadcastStates.waiting_for_message_type)


@router.message(AdminBroadcastStates.waiting_for_message_type, F.text == "Отмена")
async def broadcast_cancel_from_message_type(message: Message, state: FSMContext) -> None:
    """
    Отмена рассылки на этапе выбора типа сообщения.
    """
    await state.clear()
    await message.answer(
        "Сценарий рассылки отменен.",
        reply_markup=get_admin_menu_keyboard(),
    )


@router.message(AdminBroadcastStates.waiting_for_message_type, F.text.in_({
    "Только текст",
    "Текст + фото",
    "Текст + документ",
    "Только документ",
}))
async def broadcast_get_message_type(message: Message, state: FSMContext) -> None:
    """
    Сохраняем тип сообщения и просим следующий шаг.
    """
    mapping = {
        "Только текст": "text",
        "Текст + фото": "text_photo",
        "Текст + документ": "text_document",
        "Только документ": "document",
    }
    message_type = mapping[message.text]

    await state.update_data(message_type=message_type)

    if message_type == "document":
        await message.answer("Теперь отправьте документ одним сообщением.")
        await state.set_state(AdminBroadcastStates.waiting_for_attachment)
        return

    await message.answer("Теперь отправьте текст сообщения.")
    await state.set_state(AdminBroadcastStates.waiting_for_message_text)


@router.message(AdminBroadcastStates.waiting_for_message_text, F.text)
async def broadcast_get_message_text(message: Message, state: FSMContext) -> None:
    """
    Получаем текст сообщения.
    """
    await state.update_data(message_text=message.text.strip())

    data = await state.get_data()
    message_type = data.get("message_type")

    if message_type == "text":
        # Можно сразу на подтверждение
        target_type = data.get("target_type", "all")
        target_ids = data.get("target_ids", [])

        target_preview = (
            "всем зарегистрированным пользователям"
            if target_type == "all"
            else f"по списку Telegram ID ({len(target_ids)} шт.)"
        )

        preview = (
            "<b>Предпросмотр рассылки</b>\n\n"
            f"<b>Тип:</b> только текст\n"
            f"<b>Кому:</b> {target_preview}\n\n"
            f"<b>Текст:</b>\n{message.text.strip()}"
        )

        await message.answer(
            preview,
            reply_markup=get_broadcast_confirmation_keyboard(),
        )
        await state.set_state(AdminBroadcastStates.waiting_for_confirmation)
        return

    await message.answer("Теперь отправьте вложение одним сообщением.")
    await state.set_state(AdminBroadcastStates.waiting_for_attachment)


@router.message(AdminBroadcastStates.waiting_for_attachment, F.document)
async def broadcast_get_document(message: Message, state: FSMContext) -> None:
    """
    Получаем документ для рассылки.
    """
    data = await state.get_data()
    message_type = data.get("message_type", "")

    if message_type not in {"document", "text_document"}:
        await message.answer("Сейчас ожидается другой тип вложения.")
        return

    document: Document = message.document
    await state.update_data(attachment_file_id=document.file_id, attachment_name=document.file_name or "")

    data = await state.get_data()
    target_type = data.get("target_type", "all")
    target_ids = data.get("target_ids", [])
    message_text = data.get("message_text", "")

    target_preview = (
        "всем зарегистрированным пользователям"
        if target_type == "all"
        else f"по списку Telegram ID ({len(target_ids)} шт.)"
    )

    preview = (
        "<b>Предпросмотр рассылки</b>\n\n"
        f"<b>Тип:</b> {'текст + документ' if message_type == 'text_document' else 'только документ'}\n"
        f"<b>Кому:</b> {target_preview}\n"
        f"<b>Файл:</b> {document.file_name or 'document'}\n\n"
        f"<b>Текст:</b>\n{message_text or '-'}"
    )

    await message.answer(
        preview,
        reply_markup=get_broadcast_confirmation_keyboard(),
    )
    await state.set_state(AdminBroadcastStates.waiting_for_confirmation)


@router.message(AdminBroadcastStates.waiting_for_attachment, F.photo)
async def broadcast_get_photo(message: Message, state: FSMContext) -> None:
    """
    Получаем фото для рассылки.
    """
    data = await state.get_data()
    message_type = data.get("message_type", "")

    if message_type != "text_photo":
        await message.answer("Сейчас ожидается другой тип вложения.")
        return

    photos: list[PhotoSize] = message.photo
    largest_photo = photos[-1]

    await state.update_data(attachment_file_id=largest_photo.file_id, attachment_name="photo")

    data = await state.get_data()
    target_type = data.get("target_type", "all")
    target_ids = data.get("target_ids", [])
    message_text = data.get("message_text", "")

    target_preview = (
        "всем зарегистрированным пользователям"
        if target_type == "all"
        else f"по списку Telegram ID ({len(target_ids)} шт.)"
    )

    preview = (
        "<b>Предпросмотр рассылки</b>\n\n"
        f"<b>Тип:</b> текст + фото\n"
        f"<b>Кому:</b> {target_preview}\n"
        f"<b>Фото:</b> прикреплено\n\n"
        f"<b>Текст:</b>\n{message_text or '-'}"
    )

    await message.answer(
        preview,
        reply_markup=get_broadcast_confirmation_keyboard(),
    )
    await state.set_state(AdminBroadcastStates.waiting_for_confirmation)


@router.callback_query(F.data == "broadcast_cancel")
async def broadcast_cancel_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Отмена рассылки по inline-кнопке.
    """
    await state.clear()

    if callback.message:
        await callback.message.answer(
            "Рассылка отменена.",
            reply_markup=get_admin_menu_keyboard(),
        )

    await callback.answer()


@router.callback_query(F.data == "broadcast_confirm")
async def broadcast_confirm_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Подтверждение и запуск рассылки.
    """
    data = await state.get_data()

    target_type = data.get("target_type", "all")
    target_ids = data.get("target_ids", [])
    message_type = data.get("message_type", "text")
    message_text = data.get("message_text", "")
    attachment_file_id = data.get("attachment_file_id", "")

    if target_type == "all":
        recipient_ids = broadcaster_service.get_all_registered_user_ids()
        target_value = "all"
    else:
        recipient_ids = [int(x) for x in target_ids]
        target_value = ",".join(str(x) for x in recipient_ids)

    if callback.message:
        await callback.message.answer("Начинаю рассылку...")

    result = await broadcaster_service.send_broadcast(
        bot=callback.bot,
        recipient_ids=recipient_ids,
        message_type=message_type,
        message_text=message_text,
        attachment_file_id=attachment_file_id,
    )

    sheets_service.append_broadcast_log(
        admin_telegram_id=callback.from_user.id,
        admin_name=callback.from_user.full_name,
        broadcast_type="regular",
        target_type=target_type,
        target_value=target_value,
        message_text=message_text,
        attachment_type=message_type,
        attachment_file_id=attachment_file_id,
        recipient_count=result["recipient_count"],
        success_count=result["success_count"],
        fail_count=result["fail_count"],
        status="done",
    )

    await state.clear()

    if callback.message:
        await callback.message.answer(
            "Рассылка завершена.\n\n"
            f"Получателей: {result['recipient_count']}\n"
            f"Успешно: {result['success_count']}\n"
            f"Ошибок: {result['fail_count']}",
            reply_markup=get_admin_menu_keyboard(),
        )

    await callback.answer()


# =========================
# Опрос по смене
# =========================

@router.message(F.text == "Опрос по смене")
async def shift_poll_start(message: Message, state: FSMContext) -> None:
    """
    Старт сценария опроса по смене.
    """
    if not await _require_admin(message):
        return

    await state.clear()
    await message.answer(
        "Отправьте список Telegram ID, каждый с новой строки.\n\nПример:\n123456789\n987654321"
    )
    await state.set_state(AdminShiftPollStates.waiting_for_target_ids)


@router.message(AdminShiftPollStates.waiting_for_target_ids, F.text)
async def shift_poll_get_target_ids(message: Message, state: FSMContext) -> None:
    """
    Получаем список пользователей для опроса.
    """
    ids = parse_telegram_ids(message.text)

    if not ids:
        await message.answer("Не удалось распознать ни одного Telegram ID. Попробуйте еще раз.")
        return

    await state.update_data(target_ids=ids)
    await message.answer("Теперь введите дату смены, как хотите показать ее в тексте. Пример: 15.03.2026")
    await state.set_state(AdminShiftPollStates.waiting_for_shift_date)


@router.message(AdminShiftPollStates.waiting_for_shift_date, F.text)
async def shift_poll_get_date(message: Message, state: FSMContext) -> None:
    """
    Получаем дату смены и предлагаем шаблон текста.
    """
    shift_date = message.text.strip()

    default_question_text = (
        f"Вы откликнулись на смену {shift_date}, подскажите, Вы выйдете на задание?"
    )

    await state.update_data(shift_date=shift_date, question_text=default_question_text)

    await message.answer(
        "Теперь отправьте текст вопроса.\n\n"
        "Можно использовать шаблон ниже, можно его изменить:\n\n"
        f"{default_question_text}"
    )
    await state.set_state(AdminShiftPollStates.waiting_for_question_text)


@router.message(AdminShiftPollStates.waiting_for_question_text, F.text)
async def shift_poll_get_question_text(message: Message, state: FSMContext) -> None:
    """
    Получаем итоговый текст вопроса и показываем предпросмотр.
    """
    question_text = message.text.strip()
    data = await state.get_data()
    target_ids = data.get("target_ids", [])
    shift_date = data.get("shift_date", "")

    await state.update_data(question_text=question_text)

    preview = (
        "<b>Предпросмотр опроса по смене</b>\n\n"
        f"<b>Дата смены:</b> {shift_date}\n"
        f"<b>Получателей:</b> {len(target_ids)}\n\n"
        f"<b>Текст:</b>\n{question_text}\n\n"
        "Пользователь увидит кнопки:\n"
        "• Да, буду на задании\n"
        "• Нет, нужно отменить задание\n"
        "• Есть вопрос"
    )

    await message.answer(
        preview,
        reply_markup=get_shift_poll_confirmation_keyboard(),
    )
    await state.set_state(AdminShiftPollStates.waiting_for_confirmation)


@router.callback_query(F.data == "shift_poll_cancel")
async def shift_poll_cancel_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Отмена опроса по shift poll.
    """
    await state.clear()

    if callback.message:
        await callback.message.answer(
            "Опрос по смене отменен.",
            reply_markup=get_admin_menu_keyboard(),
        )

    await callback.answer()


@router.callback_query(F.data == "shift_poll_confirm")
async def shift_poll_confirm_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Подтверждаем и рассылаем опрос по смене.
    """
    data = await state.get_data()

    target_ids = [int(x) for x in data.get("target_ids", [])]
    shift_date = data.get("shift_date", "")
    question_text = data.get("question_text", "")

    if callback.message:
        await callback.message.answer("Отправляю опрос по смене...")

    result = await shift_poll_service.send_poll(
        bot=callback.bot,
        recipient_ids=target_ids,
        shift_date=shift_date,
        question_text=question_text,
    )

    sheets_service.append_broadcast_log(
        admin_telegram_id=callback.from_user.id,
        admin_name=callback.from_user.full_name,
        broadcast_type="shift_poll",
        target_type="ids",
        target_value=",".join(str(x) for x in target_ids),
        message_text=question_text,
        attachment_type="shift_poll",
        attachment_file_id=result["campaign_id"],
        recipient_count=result["recipient_count"],
        success_count=result["success_count"],
        fail_count=result["fail_count"],
        status="done",
    )

    await state.clear()

    if callback.message:
        await callback.message.answer(
            "Опрос по смене отправлен.\n\n"
            f"Campaign ID: {result['campaign_id']}\n"
            f"Получателей: {result['recipient_count']}\n"
            f"Успешно: {result['success_count']}\n"
            f"Ошибок: {result['fail_count']}",
            reply_markup=get_admin_menu_keyboard(),
        )

    await callback.answer()
