from __future__ import annotations

from datetime import date

from aiogram import types
from aiogram.dispatcher import Dispatcher, FSMContext

from app.config import settings
from app.database.session import AsyncSessionFactory
from app.keyboards.admin.menu import get_admin_reply_keyboard
from app.keyboards.admin.objects import get_object_menu_keyboard
from app.services.object_service import ObjectService
from app.services.schedule_change_service import ScheduleChangeService
from app.services.user_service import UserService
from app.states.object import ObjectStates
from app.utils.admin import is_admin_user_for_role
from app.database.repositories.inspection_repository import InspectionRepository


async def _is_admin_user(message: types.Message) -> bool:
    if message.from_user is None:
        return False

    async with AsyncSessionFactory() as session:
        service = UserService(session)
        user = await service.get_user_by_telegram_id(message.from_user.id)

    return is_admin_user_for_role(user.role if user else None, message.from_user.id, settings.ADMIN_ID)


async def start_schedule_change(message: types.Message, state: FSMContext) -> None:
    if not await _is_admin_user(message):
        return

    await state.set_state(ObjectStates.waiting_schedule_object_id)
    await message.answer("Введите ID объекта для переноса даты.", reply_markup=get_object_menu_keyboard())


async def schedule_change_object_id(message: types.Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Введите корректный ID объекта.")
        return

    try:
        object_id = int(message.text)
    except ValueError:
        await message.answer("ID объекта должен быть числом.")
        return

    async with AsyncSessionFactory() as session:
        service = ObjectService(session)
        obj = await service.get_object_by_id(object_id)
        inspection_repository = InspectionRepository(session)
        planned = await inspection_repository.get_planned_for_object_in_month(object_id, date.today().year, date.today().month)

    if obj is None:
        await message.answer("Объект не найден.", reply_markup=get_object_menu_keyboard())
        await state.finish()
        return

    await state.update_data(object_id=object_id)
    await state.set_state(ObjectStates.waiting_schedule_new_day)

    planned_info = (
        f"Текущая ближайшая плановая проверка: {planned.planned_date}."
        if planned
        else f"Регулярный день проверки: {obj.monthly_day}."
    )
    await message.answer(
        f"Объект #{obj.id} {obj.name}\n{planned_info}\n"
        "Введите новый день месяца для проверки (1-31).",
        reply_markup=get_object_menu_keyboard(),
    )


async def schedule_change_new_day(message: types.Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Введите корректный день месяца.")
        return

    try:
        new_day = int(message.text)
    except ValueError:
        await message.answer("День должен быть числом.")
        return

    if not 1 <= new_day <= 31:
        await message.answer("День должен быть в диапазоне 1-31.")
        return

    await state.update_data(new_day=new_day)
    await state.set_state(ObjectStates.waiting_schedule_mode)

    await message.answer(
        "Выберите вариант переноса:\n"
        "1. Только на этот месяц — изменит текущую запланированную проверку.\n"
        "2. Постоянно — изменит регулярный день для всех следующих проверок.",
        reply_markup=get_object_menu_keyboard(),
    )


async def schedule_change_mode(message: types.Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Введите 1 или 2.")
        return

    data = await state.get_data()
    try:
        new_day = int(data["new_day"])
        object_id = int(data["object_id"])
    except (KeyError, ValueError):
        await message.answer("Сначала задайте объект и день.")
        return

    mode = message.text.strip()
    async with AsyncSessionFactory() as session:
        service = ScheduleChangeService(session)
        if mode == "1":
            await service.create_temporary_change(object_id, new_day)
            await message.answer("Дата перенесена только на этот месяц.", reply_markup=get_object_menu_keyboard())
        elif mode == "2":
            await service.create_permanent_change(object_id, new_day)
            await message.answer("Дата перенесена постоянно.", reply_markup=get_object_menu_keyboard())
        else:
            await message.answer("Неверный вариант. Введите 1 или 2.")
            return

    await state.finish()


def register_schedule_handlers(dp: Dispatcher) -> None:
    dp.register_message_handler(start_schedule_change, text=["🔁 Перенос дат"], state="*")
    dp.register_message_handler(schedule_change_object_id, state=ObjectStates.waiting_schedule_object_id)
    dp.register_message_handler(schedule_change_new_day, state=ObjectStates.waiting_schedule_new_day)
    dp.register_message_handler(schedule_change_mode, state=ObjectStates.waiting_schedule_mode)
