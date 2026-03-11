"""
Состояния для сценария регистрации пользователя.
"""

from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    """
    Этапы регистрации:
    1. ввод ФИО
    2. ввод телефона
    """
    waiting_for_full_name = State()
    waiting_for_phone = State()
