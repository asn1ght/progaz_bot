from aiogram.dispatcher import Dispatcher

from app.handlers.engineer.history import register_history_handlers
from app.handlers.engineer.menu import register_engineer_handlers


def register_engineer_handlers_package(dp: Dispatcher) -> None:
    register_engineer_handlers(dp)
    register_history_handlers(dp)
