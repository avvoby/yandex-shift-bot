"""
Состояния для загрузки файла в раздел заказчика.
"""

from aiogram.fsm.state import State, StatesGroup


class AdminClientFileStates(StatesGroup):
    waiting_for_file = State()
