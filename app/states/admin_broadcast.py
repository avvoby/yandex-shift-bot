"""
Состояния для сценария админской рассылки.
"""

from aiogram.fsm.state import State, StatesGroup


class AdminBroadcastStates(StatesGroup):
    """
    Сценарий подготовки рассылки:
    1. выбрать тип аудитории
    2. ввести список id (если нужен)
    3. выбрать тип сообщения
    4. ввести текст
    5. прислать вложение (если нужно)
    6. подтвердить отправку
    """
    waiting_for_target_type = State()
    waiting_for_target_ids = State()
    waiting_for_message_type = State()
    waiting_for_message_text = State()
    waiting_for_attachment = State()
    waiting_for_confirmation = State()
