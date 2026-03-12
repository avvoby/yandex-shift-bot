from aiogram import Dispatcher

from app.handlers.registration import router as registration_router
from app.handlers.user_menu import router as user_menu_router
from app.handlers.faq import router as faq_router
from app.handlers.ask_question import router as ask_question_router
from app.handlers.admin import router as admin_router
from app.handlers.shift_poll import router as shift_poll_router
from app.handlers.first_day import router as first_day_router
from app.handlers.clients import router as clients_router
from app.handlers.common import router as common_router


def register_all_routers(dp: Dispatcher) -> None:
    dp.include_router(registration_router)
    dp.include_router(user_menu_router)
    dp.include_router(faq_router)
    dp.include_router(ask_question_router)
    dp.include_router(admin_router)
    dp.include_router(shift_poll_router)
    dp.include_router(first_day_router)
    dp.include_router(clients_router)
    dp.include_router(common_router)
