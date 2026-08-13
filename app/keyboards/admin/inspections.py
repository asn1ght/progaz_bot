from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def get_inspection_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    keyboard.row(
        KeyboardButton("🗓 Создать проверку"),
        KeyboardButton("📜 Список проверок"),
    )
    keyboard.row(KeyboardButton("⬅️ Назад"))
    return keyboard


def get_reschedule_keyboard(inspection_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=3)
    keyboard.row(
        InlineKeyboardButton("📅 Завтра", callback_data=f"reschedule:{inspection_id}:1"),
        InlineKeyboardButton("📅 Послезавтра", callback_data=f"reschedule:{inspection_id}:2"),
        InlineKeyboardButton("📅 Через 3 дня", callback_data=f"reschedule:{inspection_id}:3"),
    )
    return keyboard


def get_reschedule_confirm_keyboard(inspection_id: int, new_date) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.row(
        InlineKeyboardButton("✅ Да, перенести", callback_data=f"confirm_reschedule:{inspection_id}:{new_date.isoformat()}"),
        InlineKeyboardButton("❌ Отмена", callback_data=f"cancel_reschedule:{inspection_id}"),
    )
    return keyboard
