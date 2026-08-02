from __future__ import annotations

from aiogram import types
from aiogram.dispatcher import Dispatcher

from app.database.session import AsyncSessionFactory
from app.services.user_service import UserService

ROLE_LABELS = {
    "admin": "администратора",
    "engineer": "инженера",
    "accountant": "бухгалтера",
}


async def review_registration_callback(call: types.CallbackQuery) -> None:
    await call.answer()
    data = call.data or ""
    if not data.startswith("approve:") and not data.startswith("reject:"):
        return

    parts = data.split(":")
    telegram_id = int(parts[1])

    async with AsyncSessionFactory() as session:
        service = UserService(session)
        if data.startswith("approve:"):
            role = parts[2]
            user = await service.approve_user(telegram_id, role)
            await call.message.edit_text(
                f"Заявка подтверждена для пользователя {telegram_id} с ролью {role}."
            )
            if user is not None:
                role_label = ROLE_LABELS.get(role, role)
                await call.bot.send_message(
                    telegram_id,
                    f"Ваша заявка на регистрацию подтверждена. Вам назначена роль: {role_label}.",
                )
        else:
            user = await service.reject_user(telegram_id)
            await call.message.edit_text(f"Заявка отклонена для пользователя {telegram_id}.")
            if user is not None:
                await call.bot.send_message(
                    telegram_id,
                    "Ваша заявка на регистрацию отклонена.",
                )


def register_admin_review_handlers(dp: Dispatcher) -> None:
    dp.register_callback_query_handler(review_registration_callback, text_startswith="approve:", state="*")
    dp.register_callback_query_handler(review_registration_callback, text_startswith="reject:", state="*")
