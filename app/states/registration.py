from aiogram.dispatcher.filters.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    full_name = State()
    phone = State()
    waiting_admin = State()
