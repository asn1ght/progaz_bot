from aiogram.dispatcher import Dispatcher

from app.handlers.accountant.menu import register_accountant_handlers


def register_accountant_handlers_package(dp: Dispatcher) -> None:
    register_accountant_handlers(dp)
