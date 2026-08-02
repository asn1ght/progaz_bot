from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_registration_review_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=3)
    keyboard.add(
        InlineKeyboardButton("Админ", callback_data=f"approve:{telegram_id}:admin"),
        InlineKeyboardButton("Инженер", callback_data=f"approve:{telegram_id}:engineer"),
        InlineKeyboardButton("Бухгалтер", callback_data=f"approve:{telegram_id}:accountant"),
    )
    keyboard.add(
        InlineKeyboardButton("Отклонить", callback_data=f"reject:{telegram_id}"),
    )
    return keyboard
