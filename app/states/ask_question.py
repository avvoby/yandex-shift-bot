"""
Состояния для сценария "Задать вопрос".
"""

from aiogram.fsm.state import State, StatesGroup


class AskQuestionStates(StatesGroup):
    """
    Бот ждет текст вопроса от пользователя.
    """
    waiting_for_question_text = State()
