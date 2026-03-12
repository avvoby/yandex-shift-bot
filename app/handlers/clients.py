"""
Раздел "Особенности разных заказчиков".
"""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.keyboards.user import (
    get_client_section_actions_keyboard,
    get_client_sections_keyboard,
    get_clients_keyboard,
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


@router.message(F.text == "Особенности разных заказчиков")
async def clients_entry(message: Message) -> None:
    if not _is_private_message(message):
        return

    if not await _is_registered(message.from_user.id):
        await message.answer("Сначала завершите регистрацию через /start")
        return

    clients = await content_service.get_clients()
    client_names = [item["client_name"] for item in clients]

    if not client_names:
        await message.answer("Раздел пока не заполнен.")
        return

    await message.answer(
        "Выберите заказчика:",
        reply_markup=get_clients_keyboard(client_names),
    )


@router.callback_query(F.data == "clients_back_to_main")
async def clients_back_to_main(callback: CallbackQuery) -> None:
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


@router.callback_query(F.data == "clients_back_to_clients")
async def clients_back_to_clients(callback: CallbackQuery) -> None:
    if not _is_private_callback(callback):
        await callback.answer()
        return

    clients = await content_service.get_clients()
    client_names = [item["client_name"] for item in clients]

    if callback.message:
        await callback.message.edit_text(
            "Выберите заказчика:",
            reply_markup=get_clients_keyboard(client_names),
        )

    await callback.answer()


@router.callback_query(F.data.startswith("client_open:"))
async def client_open(callback: CallbackQuery) -> None:
    if not _is_private_callback(callback):
        await callback.answer()
        return

    _, index_str = callback.data.split("client_open:", maxsplit=1)

    try:
        client_index = int(index_str)
    except ValueError:
        await callback.answer("Некорректный заказчик.", show_alert=True)
        return

    client = await content_service.get_client_by_index(client_index)
    if not client:
        await callback.answer("Заказчик не найден.", show_alert=True)
        return

    if callback.message:
        await callback.message.edit_text(
            f"Заказчик: <b>{client['client_name']}</b>\n\nВыберите раздел:",
            reply_markup=get_client_sections_keyboard(client_index, client["sections"]),
        )

    await callback.answer()


@router.callback_query(F.data.startswith("client_back_to_sections:"))
async def client_back_to_sections(callback: CallbackQuery) -> None:
    if not _is_private_callback(callback):
        await callback.answer()
        return

    _, index_str = callback.data.split("client_back_to_sections:", maxsplit=1)

    try:
        client_index = int(index_str)
    except ValueError:
        await callback.answer("Некорректный заказчик.", show_alert=True)
        return

    client = await content_service.get_client_by_index(client_index)
    if not client:
        await callback.answer("Заказчик не найден.", show_alert=True)
        return

    if callback.message:
        await callback.message.answer(
            f"Заказчик: <b>{client['client_name']}</b>\n\nВыберите раздел:",
            reply_markup=get_client_sections_keyboard(client_index, client["sections"]),
        )

    await callback.answer()


@router.callback_query(F.data.startswith("client_section:"))
async def client_section_open(callback: CallbackQuery) -> None:
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

    text = str(section.get("text", "")).strip()
    file_id = str(section.get("file_id", "")).strip()
    buttons = section.get("buttons", [])
    section_title = str(section.get("section_title", "")).strip()

    if callback.message:
        if text:
            await callback.message.answer(
                f"<b>{section_title}</b>\n\n{text}",
                reply_markup=get_client_section_actions_keyboard(client_index, buttons),
            )
        else:
            await callback.message.answer(
                f"<b>{section_title}</b>",
                reply_markup=get_client_section_actions_keyboard(client_index, buttons),
            )

        if file_id:
            try:
                await callback.message.answer_document(document=file_id)
            except Exception:
                await callback.message.answer("Не удалось отправить файл из этого раздела.")

    await callback.answer()
