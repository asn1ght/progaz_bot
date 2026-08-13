from __future__ import annotations

from aiogram import types
from aiogram.dispatcher import Dispatcher

from app.config import settings
from app.database.repositories.user_repository import UserRepository
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
        "🏠 <b>Главное меню администратора</b>\n\n"
        "📦 Объекты — управление объектами\n"
        "🛠 Проверки — планирование выездов\n"
        "🧾 Счета — финансовый учет\n"
        "👥 Пользователи — управление доступом",
        reply_markup=get_admin_reply_keyboard(),
        parse_mode="HTML",
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


async def list_users(message: types.Message) -> None:
    if message.from_user is None:
        return

    async with AsyncSessionFactory() as session:
        service = UserService(session)
        user = await service.get_user_by_telegram_id(message.from_user.id)

    if not is_admin_user_for_role(user.role if user else None, message.from_user.id, settings.ADMIN_ID):
        return

    async with AsyncSessionFactory() as session:
        user_repository = UserRepository(session)
        users = await user_repository.list_all()

    if not users:
        await message.answer(
            "📭 <b>Список пользователей пуст.</b>",
            reply_markup=get_admin_reply_keyboard(),
            parse_mode="HTML",
        )
        return

    role_labels = {
        "admin": "👑 админ",
        "engineer": "👷 инженер",
        "accountant": "📊 бухгалтер",
        "pending": "⏳ ожидает",
    }
    active_icon = {True: "✅", False: "🚫"}

    lines = [f"👥 <b>Пользователи</b> ({len(users)} чел.)\n"]
    for u in users:
        role = role_labels.get(u.role, u.role)
        icon = active_icon.get(u.is_active, "❓")
        lines.append(
            f"<b>#{u.id}</b> {u.full_name}\n"
            f"   {role}  |  {icon}\n"
            f"   ─────────────────────"
        )

    await message.answer("\n".join(lines), reply_markup=get_admin_reply_keyboard(), parse_mode="HTML")


def register_admin_menu_handlers(dp: Dispatcher) -> None:
    dp.register_message_handler(admin_menu_command, commands=["admin"], state="*")
    dp.register_message_handler(
        admin_menu_text_handler,
        text=[" Проверки"],
        state="*",
    )
    dp.register_message_handler(list_users, text=["👥 Пользователи"], state="*")
