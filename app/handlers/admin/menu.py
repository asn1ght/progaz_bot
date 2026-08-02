from __future__ import annotations

from aiogram import types
from aiogram.dispatcher import Dispatcher

from app.config import settings
from app.keyboards.admin.menu import get_admin_reply_keyboard

MENU_TITLES = {
    "📦 Объекты": "Объекты",
    "🛠 Проверки": "Проверки",
    "🧾 Счета": "Счета",
    "👥 Пользователи": "Пользователи",
}


async def admin_menu_command(message: types.Message) -> None:
    if message.from_user is None or message.from_user.id != settings.ADMIN_ID:
        await message.answer("Доступ к административному меню ограничен.")
        return

    await message.answer(
        "Главное административное меню",
        reply_markup=get_admin_reply_keyboard(),
    )


async def admin_menu_text_handler(message: types.Message) -> None:
    if message.from_user is None or message.from_user.id != settings.ADMIN_ID:
        return

    section = message.text or ""
    section_title = MENU_TITLES.get(section, section)
    await message.answer(
        f"Раздел: {section_title}\n"
        "Здесь будет навигация и дальнейшие действия по выбранному модулю.",
        reply_markup=get_admin_reply_keyboard(),
    )


def register_admin_menu_handlers(dp: Dispatcher) -> None:
    dp.register_message_handler(admin_menu_command, commands=["admin"], state="*")
    dp.register_message_handler(
        admin_menu_text_handler,
        text=[" Проверки", "🧾 Счета", "👥 Пользователи"],
        state="*",
    )
