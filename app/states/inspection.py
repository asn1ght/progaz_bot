from __future__ import annotations

from aiogram.dispatcher.filters.state import State, StatesGroup


class InspectionStates(StatesGroup):
    waiting_object_id = State()
    waiting_engineer_id = State()
    waiting_planned_date = State()
