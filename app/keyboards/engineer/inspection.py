from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_inspection_action_keyboard(inspection_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("✅ Отметить выполненной", callback_data=f"complete_inspection:{inspection_id}"))
    return keyboard
