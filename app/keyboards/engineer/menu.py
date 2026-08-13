from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_engineer_reply_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    keyboard.add(KeyboardButton("🧭 Мои объекты"))
    keyboard.add(KeyboardButton("📅 Сегодня"), KeyboardButton("📅 Завтра"))
    keyboard.add(KeyboardButton("📜 История"))
    return keyboard
