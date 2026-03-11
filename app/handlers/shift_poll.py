"""
Обработчики ответов пользователя на опрос по смене.

Логика:
- пользователь получает сообщение с кнопками:
  - Да, буду на задании
  - Нет, нужно отменить задание
  - Есть вопрос
- бот сохраняет ответ в Google Sheets
- если "Есть вопрос" — запускается сценарий вопроса в поддержку
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.keyboards.user import get_back_to_main_menu_keyboard
from app.services.shift_poll import shift_poll_service
from app.services.sheets import sheets_service
from app.states.ask_question import AskQuestionStates
from app.utils.helpers import now_iso

router = Router()


@router.callback_query(F.data.startswith("shift_answer:"))
async def shift_poll_answer(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработка ответа пользователя на опрос по смене.
    Формат callback_data:
    shift_answer:{campaign_id}:{answer}
    """
    data = callback.data or ""
    parts = data.split(":", maxsplit=2)

    if len(parts) != 3:
        await callback.answer("Некорректные данные.", show_alert=True)
        return

    _, campaign_id, answer = parts

    telegram_id = callback.from_user.id
    user = sheets_service.get_user_by_telegram_id(telegram_id)

    if not user:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return

    campaign = shift_poll_service.get_campaign(campaign_id)
    if not campaign:
        await callback.answer(
            "Не удалось найти данные опроса. Возможно, бот перезапускался.",
            show_alert=True,
        )
        return

    shift_date = campaign.get("shift_date", "")
    question_text = campaign.get(
        "question_text",
        "Вы откликнулись на смену, подскажите, Вы выйдете на задание?",
    )

    username = callback.from_user.username or ""
    full_name = str(user.get("full_name_entered", "")).strip()
    phone = str(user.get("phone_entered", "")).strip()

    sheets_service.append_shift_confirmation(
        campaign_id=campaign_id,
        shift_date=shift_date,
        telegram_id=telegram_id,
        username=username,
        full_name=full_name,
        phone=phone,
        question_text=question_text,
        answer=answer,
        answered_at=now_iso(),
    )

    if answer == "yes":
        if callback.message:
            await callback.message.edit_text(
                "Спасибо! Мы отметили, что вы будете на задании."
            )
        await callback.answer()
        return

    if answer == "no":
        if callback.message:
            await callback.message.edit_text(
                "Спасибо! Мы отметили, что задание нужно отменить."
            )
        await callback.answer()
        return

    if answer == "question":
        await state.update_data(
            shift_poll_campaign_id=campaign_id,
            shift_poll_question_text=question_text,
        )
        await state.set_state(AskQuestionStates.waiting_for_question_text)

        if callback.message:
            await callback.message.answer(
                "Пожалуйста, напишите ваш вопрос. Мы передадим его коллегам.",
                reply_markup=get_back_to_main_menu_keyboard(),
            )

        await callback.answer()
        return

    await callback.answer("Неизвестный вариант ответа.", show_alert=True)
