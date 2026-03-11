"""
Состояния для сценария опроса исполнителей по смене.
"""

from aiogram.fsm.state import State, StatesGroup


class AdminShiftPollStates(StatesGroup):
    """
    Этапы:
    1. ввод списка Telegram ID
    2. ввод даты смены
    3. ввод/редактирование текста вопроса
    4. подтверждение отправки
    """
    waiting_for_target_ids = State()
    waiting_for_shift_date = State()
    waiting_for_question_text = State()
    waiting_for_confirmation = State()
