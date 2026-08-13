from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


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


def get_engineer_selection_keyboard(engineers: list) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=1)
    for eng in engineers:
        label = f"{eng.full_name} (ID: {eng.id})"
        keyboard.add(InlineKeyboardButton(label, callback_data=f"pick_engineer:{eng.id}"))
    keyboard.add(InlineKeyboardButton("⏭ Пропустить / без инженера", callback_data="pick_engineer:skip"))
    return keyboard
