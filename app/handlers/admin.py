"""
Обработчики админ-меню.
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Document, Message, PhotoSize, Video

from app.keyboards.admin import (
    get_admin_client_sections_keyboard,
    get_admin_clients_keyboard,
    get_admin_menu_keyboard,
    get_broadcast_confirmation_keyboard,
    get_broadcast_message_type_keyboard,
    get_shift_poll_confirmation_keyboard,
)
from app.services.broadcaster import broadcaster_service
from app.services.content import content_service
from app.services.shift_poll import shift_poll_service
from app.services.sheets import sheets_service
from app.states.admin_broadcast import AdminBroadcastStates
from app.states.admin_client_file import AdminClientFileStates
from app.states.admin_shift_poll import AdminShiftPollStates
from app.utils.helpers import parse_telegram_ids

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


async def _require_admin(message: Message) -> bool:
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
    if not _is_private_message(message):
        return

    await state.clear()

    if not await _require_admin(message):
        return

    await message.answer(
        "Админ-меню. Выберите действие:",
        reply_markup=get_admin_menu_keyboard(),
    )


@router.message(F.text == "Обновить контент сейчас")
async def admin_reload_content(message: Message) -> None:
    if not _is_private_message(message):
        return

    if not await _require_admin(message):
        return

    await message.answer("Обновляю контент из Google Sheets...")

    try:
        await content_service.force_reload()
        await message.answer("Готово. Контент успешно обновлен.")
    except Exception as exc:
        await message.answer(f"Ошибка при обновлении контента: {exc}")


# =========================
# Загрузка файла для раздела заказчика
# =========================

@router.message(F.text == "Загрузить файл для раздела заказчика")
async def admin_upload_client_file_start(message: Message, state: FSMContext) -> None:
    if not _is_private_message(message):
        return

    if not await _require_admin(message):
        return

    await state.clear()

    clients = await content_service.get_clients()
    client_names = [item["client_name"] for item in clients]

    if not client_names:
        await message.answer(
            "Раздел заказчиков пока не заполнен.\n\n"
            "Сначала создайте строки в листе client_sections, потом нажмите «Обновить контент сейчас»."
        )
        return

    await message.answer(
        "Выберите заказчика, для раздела которого хотите загрузить файл:",
        reply_markup=get_admin_clients_keyboard(client_names),
    )


@router.callback_query(F.data == "admin_file_cancel")
async def admin_file_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_private_callback(callback):
        await callback.answer()
        return

    await state.clear()

    if callback.message:
        await callback.message.answer(
            "Загрузка файла отменена.",
            reply_markup=get_admin_menu_keyboard(),
        )

    await callback.answer()


@router.callback_query(F.data == "admin_file_back_to_clients")
async def admin_file_back_to_clients(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_private_callback(callback):
        await callback.answer()
        return

    clients = await content_service.get_clients()
    client_names = [item["client_name"] for item in clients]

    if callback.message:
        await callback.message.edit_text(
            "Выберите заказчика, для раздела которого хотите загрузить файл:",
            reply_markup=get_admin_clients_keyboard(client_names),
        )

    await callback.answer()


@router.callback_query(F.data.startswith("admin_file_client:"))
async def admin_file_select_client(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_private_callback(callback):
        await callback.answer()
        return

    _, index_str = callback.data.split("admin_file_client:", maxsplit=1)

    try:
        client_index = int(index_str)
    except ValueError:
        await callback.answer("Некорректный заказчик.", show_alert=True)
        return

    client = await content_service.get_client_by_index(client_index)
    if not client:
        await callback.answer("Заказчик не найден.", show_alert=True)
        return

    await state.update_data(client_index=client_index, client_name=client["client_name"])

    if callback.message:
        await callback.message.edit_text(
            f"Заказчик: <b>{client['client_name']}</b>\n\nВыберите внутренний раздел:",
            reply_markup=get_admin_client_sections_keyboard(client_index, client["sections"]),
        )

    await callback.answer()


@router.callback_query(F.data.startswith("admin_file_section:"))
async def admin_file_select_section(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_private_callback(callback):
        await callback.answer()
        return

    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Некорректные данные.", show_alert=True)
        return

    _, client_index_str, section_index_str = parts

    try:
        client_index = int(client_index_str)
        section_index = int(section_index_str)
    except ValueError:
        await callback.answer("Некорректные данные.", show_alert=True)
        return

    client = await content_service.get_client_by_index(client_index)
    if not client:
        await callback.answer("Заказчик не найден.", show_alert=True)
        return

    sections = client["sections"]
    if section_index < 0 or section_index >= len(sections):
        await callback.answer("Раздел не найден.", show_alert=True)
        return

    section = sections[section_index]

    await state.update_data(
        client_name=client["client_name"],
        section_key=section["section_key"],
        section_title=section["section_title"],
    )
    await state.set_state(AdminClientFileStates.waiting_for_file)

    if callback.message:
        await callback.message.answer(
            f"Теперь отправьте файл для раздела:\n\n"
            f"<b>{client['client_name']} → {section['section_title']}</b>\n\n"
            f"Поддерживаются: документ, фото, видео."
        )

    await callback.answer()


@router.message(AdminClientFileStates.waiting_for_file, F.document)
async def admin_file_receive_document(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    client_name = data.get("client_name", "")
    section_key = data.get("section_key", "")

    document: Document = message.document
    ok = sheets_service.update_client_section_file(
        client_name=client_name,
        section_key=section_key,
        file_id=document.file_id,
        file_type="document",
    )

    if not ok:
        await message.answer("Не удалось сохранить file_id в таблицу.")
        return

    await content_service.force_reload()
    await state.clear()

    await message.answer(
        "Файл успешно сохранён для выбранного раздела.",
        reply_markup=get_admin_menu_keyboard(),
    )


@router.message(AdminClientFileStates.waiting_for_file, F.photo)
async def admin_file_receive_photo(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    client_name = data.get("client_name", "")
    section_key = data.get("section_key", "")

    photos: list[PhotoSize] = message.photo
    largest_photo = photos[-1]

    ok = sheets_service.update_client_section_file(
        client_name=client_name,
        section_key=section_key,
        file_id=largest_photo.file_id,
        file_type="photo",
    )

    if not ok:
        await message.answer("Не удалось сохранить file_id в таблицу.")
        return

    await content_service.force_reload()
    await state.clear()

    await message.answer(
        "Фото успешно сохранено для выбранного раздела.",
        reply_markup=get_admin_menu_keyboard(),
    )


@router.message(AdminClientFileStates.waiting_for_file, F.video)
async def admin_file_receive_video(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    client_name = data.get("client_name", "")
    section_key = data.get("section_key", "")

    video: Video = message.video

    ok = sheets_service.update_client_section_file(
        client_name=client_name,
        section_key=section_key,
        file_id=video.file_id,
        file_type="video",
    )

    if not ok:
        await message.answer("Не удалось сохранить file_id в таблицу.")
        return

    await content_service.force_reload()
    await state.clear()

    await message.answer(
        "Видео успешно сохранено для выбранного раздела.",
        reply_markup=get_admin_menu_keyboard(),
    )


# =========================
# Обычная рассылка
# =========================

@router.message(F.text == "Рассылка всем")
async def broadcast_all_start(message: Message, state: FSMContext) -> None:
    if not _is_private_message(message):
        return

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
    if not _is_private_message(message):
        return

    if not await _require_admin(message):
        return

    await state.clear()
    await message.answer(
        "Отправьте список Telegram ID, каждый с новой строки.\n\nПример:\n123456789\n987654321"
    )
    await state.set_state(AdminBroadcastStates.waiting_for_target_ids)


@router.message(AdminBroadcastStates.waiting_for_target_ids, F.text)
async def broadcast_get_target_ids(message: Message, state: FSMContext) -> None:
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
    await state.update_data(message_text=message.text.strip())

    data = await state.get_data()
    message_type = data.get("message_type")

    if message_type == "text":
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
    if not _is_private_callback(callback):
        await callback.answer()
        return

    await state.clear()

    if callback.message:
        await callback.message.answer(
            "Рассылка отменена.",
            reply_markup=get_admin_menu_keyboard(),
        )

    await callback.answer()


@router.callback_query(F.data == "broadcast_confirm")
async def broadcast_confirm_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_private_callback(callback):
        await callback.answer()
        return

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
    if not _is_private_message(message):
        return

    if not await _require_admin(message):
        return

    await state.clear()
    await message.answer(
        "Отправьте список Telegram ID, каждый с новой строки.\n\nПример:\n123456789\n987654321"
    )
    await state.set_state(AdminShiftPollStates.waiting_for_target_ids)


@router.message(AdminShiftPollStates.waiting_for_target_ids, F.text)
async def shift_poll_get_target_ids(message: Message, state: FSMContext) -> None:
    ids = parse_telegram_ids(message.text)

    if not ids:
        await message.answer("Не удалось распознать ни одного Telegram ID. Попробуйте еще раз.")
        return

    await state.update_data(target_ids=ids)
    await message.answer("Теперь введите дату смены, как хотите показать ее в тексте. Пример: 15.03.2026")
    await state.set_state(AdminShiftPollStates.waiting_for_shift_date)


@router.message(AdminShiftPollStates.waiting_for_shift_date, F.text)
async def shift_poll_get_date(message: Message, state: FSMContext) -> None:
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
    if not _is_private_callback(callback):
        await callback.answer()
        return

    await state.clear()

    if callback.message:
        await callback.message.answer(
            "Опрос по смене отменен.",
            reply_markup=get_admin_menu_keyboard(),
        )

    await callback.answer()


@router.callback_query(F.data == "shift_poll_confirm")
async def shift_poll_confirm_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_private_callback(callback):
        await callback.answer()
        return

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
