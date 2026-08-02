from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup


class EngineerStates(StatesGroup):
    waiting_comment = State()
    waiting_completion = State()
