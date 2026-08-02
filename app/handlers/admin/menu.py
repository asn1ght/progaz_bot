from __future__ import annotations

from aiogram import types
from aiogram.dispatcher import Dispatcher

from app.config import settings
from app.database.session import AsyncSessionFactory
from app.keyboards.admin.menu import get_admin_reply_keyboard
from app.services.user_service import UserService
from app.utils.admin import is_admin_user_for_role

MENU_TITLES = {
    "📦 Объекты": "Объекты",
    "🛠 Проверки": "Проверки",
    "🧾 Счета": "Счета",
    "👥 Пользователи": "Пользователи",
}


async def admin_menu_command(message: types.Message) -> None:
    if message.from_user is None:
        return

    async with AsyncSessionFactory() as session:
        service = UserService(session)
        user = await service.get_user_by_telegram_id(message.from_user.id)

    if not is_admin_user_for_role(user.role if user else None, message.from_user.id, settings.ADMIN_ID):
        await message.answer("Доступ к административному меню ограничен.")
        return

    await message.answer(
        "Главное административное меню",
        reply_markup=get_admin_reply_keyboard(),
    )


async def admin_menu_text_handler(message: types.Message) -> None:
    if message.from_user is None:
        return

    async with AsyncSessionFactory() as session:
        service = UserService(session)
        user = await service.get_user_by_telegram_id(message.from_user.id)

    if not is_admin_user_for_role(user.role if user else None, message.from_user.id, settings.ADMIN_ID):
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
