from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_invoice_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    keyboard.row(
        KeyboardButton("📜 Все счета"),
        KeyboardButton("💰 Оплатить счет"),
    )
    keyboard.row(KeyboardButton("⬅️ Назад"))
    return keyboard
