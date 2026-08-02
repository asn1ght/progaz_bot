from __future__ import annotations

from aiogram.dispatcher.filters.state import State, StatesGroup


class ObjectStates(StatesGroup):
    waiting_name = State()
    waiting_address = State()
    waiting_engineer_id = State()
    waiting_monthly_day = State()
    waiting_invoice_amount = State()
    waiting_comment = State()

    waiting_edit_object_id = State()
    waiting_delete_object_id = State()
    waiting_new_name = State()
    waiting_new_address = State()
    waiting_new_engineer_id = State()
    waiting_new_monthly_day = State()
    waiting_new_invoice_amount = State()
    waiting_new_comment = State()
