"""
Здесь создаются основные объекты aiogram:
- Bot
- Dispatcher
- Хранилище состояний FSM

FSM нужен для сценариев:
- регистрация
- задать вопрос
- рассылка
- опрос по смене
"""

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings


def create_bot_and_dispatcher() -> tuple[Bot, Dispatcher]:
    """
    Создаем и возвращаем:
    - объект бота
    - объект диспетчера
    """
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # MemoryStorage подходит для первого этапа.
    # Для очень больших нагрузок позже можно перейти на Redis.
    storage = MemoryStorage()

    dp = Dispatcher(storage=storage)
    return bot, dp
