from __future__ import annotations

from aiogram.dispatcher.filters.state import State, StatesGroup


class InvoiceStates(StatesGroup):
    waiting_invoice_id = State()


class AdminInvoiceStates(StatesGroup):
    waiting_invoice_id = State()
