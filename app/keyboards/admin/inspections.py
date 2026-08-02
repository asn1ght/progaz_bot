from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_inspection_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    keyboard.row(
        KeyboardButton("🗓 Создать проверку"),
        KeyboardButton("📜 Список проверок"),
    )
    keyboard.row(KeyboardButton("⬅️ Назад"))
    return keyboard
