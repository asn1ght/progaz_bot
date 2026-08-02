from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_admin_reply_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    keyboard.row(
        KeyboardButton("📦 Объекты"),
        KeyboardButton("🛠 Проверки"),
    )
    keyboard.row(
        KeyboardButton("🧾 Счета"),
        KeyboardButton("👥 Пользователи"),
    )
    return keyboard
