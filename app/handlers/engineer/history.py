from __future__ import annotations

from datetime import date

from aiogram import types
from aiogram.dispatcher import Dispatcher

from app.database.session import AsyncSessionFactory
from app.keyboards.engineer.menu import get_engineer_reply_keyboard
from app.services.user_service import UserService
from app.config import settings
from app.utils.admin import is_admin_user_for_role
from app.utils.engineer import matches_engineer_assignment


async def _get_current_user(message: types.Message):
    if message.from_user is None:
        return None

    async with AsyncSessionFactory() as session:
        service = UserService(session)
        return await service.get_user_by_telegram_id(message.from_user.id)


async def _is_engineer_user(message: types.Message) -> bool:
    if message.from_user is None:
        return False

    async with AsyncSessionFactory() as session:
        service = UserService(session)
        user = await service.get_user_by_telegram_id(message.from_user.id)

    return bool(user and user.role == "engineer") or is_admin_user_for_role(user.role if user else None, message.from_user.id, settings.ADMIN_ID)


async def show_history(message: types.Message) -> None:
    if not await _is_engineer_user(message):
        return

    user = await _get_current_user(message)
    today = date.today()
    month_start = today.replace(day=1)

    async with AsyncSessionFactory() as session:
        from app.database.repositories.inspection_repository import InspectionRepository
        inspection_repository = InspectionRepository(session)
        inspections = await inspection_repository.list_by_date(month_start)

    relevant = [
        insp
        for insp in inspections
        if matches_engineer_assignment(user.id if user else None, insp.engineer_id)
        and insp.planned_date.month == today.month
        and insp.planned_date.year == today.year
    ]
    if not relevant:
        await message.answer("История проверок пуста.", reply_markup=get_engineer_reply_keyboard())
        return

    lines = []
    for insp in relevant:
        status_label = "выполнено" if insp.status == "completed" else "в работе"
        lines.append(f"#{insp.id} | {insp.planned_date} | {status_label} | {insp.comment or '-'}")

    await message.answer("\n".join(lines), reply_markup=get_engineer_reply_keyboard())


def register_history_handlers(dp: Dispatcher) -> None:
    dp.register_message_handler(show_history, text=["📜 История"], state="*")
