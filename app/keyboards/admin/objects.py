from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_object_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    keyboard.row(
        KeyboardButton("➕ Добавить объект"),
        KeyboardButton("📋 Список объектов"),
    )
    keyboard.row(
        KeyboardButton("✏️ Изменить объект"),
        KeyboardButton("🗑 Удалить объект"),
    )
    keyboard.row(KeyboardButton("🔁 Перенос дат"))
    keyboard.row(KeyboardButton("⬅️ Назад"))
    return keyboard
