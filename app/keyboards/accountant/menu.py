from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_accountant_reply_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    keyboard.row(
        KeyboardButton("🧾 Неоплаченные счета"),
        KeyboardButton("💰 Отметить оплату"),
    )
    return keyboard
