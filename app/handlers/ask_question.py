"""
Сценарий "Задать вопрос".
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.keyboards.user import get_back_to_main_menu_keyboard, get_main_menu_keyboard
from app.services.content import content_service
from app.services.sheets import sheets_service
from app.states.ask_question import AskQuestionStates
from app.utils.helpers import now_iso

router = Router()


def _is_private_chat(message: Message) -> bool:
    return message.chat.type == "private"


async def _is_registered(telegram_id: int) -> bool:
    user = sheets_service.get_user_by_telegram_id(telegram_id)
    if not user:
        return False
    status = str(user.get("registration_status", "")).strip().lower()
    return status == "registered"


@router.message(F.text == "Задать вопрос")
async def ask_question_entry(message: Message, state: FSMContext) -> None:
    if not _is_private_chat(message):
        return

    if not await _is_registered(message.from_user.id):
        await message.answer("Сначала завершите регистрацию через /start")
        return


    prompt_text = await content_service.get_text(
        "ask_question_prompt",
        default="Напишите ваш вопрос. Мы передадим его коллегам.",
    )

    await message.answer(
        prompt_text,
        reply_markup=get_back_to_main_menu_keyboard(),
    )
    await state.set_state(AskQuestionStates.waiting_for_question_text)


@router.callback_query(F.data == "faq_no_answer")
async def ask_question_from_faq(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None or callback.message.chat.type != "private":
        await callback.answer()
        return

    prompt_text = await content_service.get_text(
        "ask_question_prompt",
        default="Напишите ваш вопрос. Мы передадим его коллегам.",
    )

    await callback.message.answer(
        prompt_text,
        reply_markup=get_back_to_main_menu_keyboard(),
    )
    await state.set_state(AskQuestionStates.waiting_for_question_text)
    await callback.answer()


@router.message(AskQuestionStates.waiting_for_question_text, F.text == "Назад в главное меню")
async def ask_question_cancel(message: Message, state: FSMContext) -> None:
    if not _is_private_chat(message):
        return

    await state.clear()

    is_admin = await content_service.is_admin(message.from_user.id)
    main_menu_text = await content_service.get_text(
        "main_menu_text",
        default="Выберите нужный раздел.",
    )

    await message.answer(
        main_menu_text,
        reply_markup=get_main_menu_keyboard(is_admin=is_admin),
    )


@router.message(AskQuestionStates.waiting_for_question_text, F.text)
async def ask_question_receive_text(message: Message, state: FSMContext) -> None:
    if not _is_private_chat(message):
        return

    question_text = message.text.strip()

    if len(question_text) < 2:
        await message.answer("Пожалуйста, напишите более подробный вопрос.")
        return

    telegram_id = message.from_user.id
    user = sheets_service.get_user_by_telegram_id(telegram_id)

    if not user:
        await message.answer("Не удалось найти ваши данные. Пожалуйста, начните заново через /start")
        await state.clear()
        return

    full_name = str(user.get("full_name_entered", "")).strip()
    phone = str(user.get("phone_entered", "")).strip()
    username = message.from_user.username or ""

    settings_dict = await content_service.get_settings()
    support_group_chat_id = settings_dict.get("support_group_chat_id", "").strip()

    support_message = (
        "<b>Новое обращение от исполнителя</b>\n\n"
        f"<b>ФИО:</b> {full_name}\n"
        f"<b>Телефон:</b> {phone}\n"
        f"<b>Telegram ID:</b> {telegram_id}\n"
        f"<b>Username:</b> @{username if username else '-'}\n"
        f"<b>Время:</b> {now_iso()}\n\n"
        f"<b>Вопрос:</b>\n{question_text}"
    )

    forwarded_to_chat = "no"
    if support_group_chat_id:
        try:
            await message.bot.send_message(
                chat_id=int(support_group_chat_id),
                text=support_message,
            )
            forwarded_to_chat = "yes"
        except Exception:
            forwarded_to_chat = "error"

    sheets_service.append_support_request(
        telegram_id=telegram_id,
        username=username,
        full_name=full_name,
        phone=phone,
        message_text=question_text,
        forwarded_to_chat=forwarded_to_chat,
        status="sent" if forwarded_to_chat == "yes" else forwarded_to_chat,
    )

    await state.clear()

    success_text = await content_service.get_text(
        "ask_question_success",
        default="Спасибо! Ваш вопрос передан коллегам. Скоро с вами свяжутся.",
    )

    is_admin = await content_service.is_admin(telegram_id)
    await message.answer(
        success_text,
        reply_markup=get_main_menu_keyboard(is_admin=is_admin),
    )
