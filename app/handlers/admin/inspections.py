from __future__ import annotations

from datetime import datetime

from aiogram import types
from aiogram.dispatcher import Dispatcher, FSMContext

from app.config import settings
from app.database.models import Inspection, Object
from app.database.session import AsyncSessionFactory
from app.keyboards.admin.inspections import get_inspection_menu_keyboard
from app.keyboards.admin.menu import get_admin_reply_keyboard
from app.services.inspection_service import InspectionService
from app.services.object_service import ObjectService
from app.states.inspection import InspectionStates


async def show_inspection_menu(message: types.Message) -> None:
    if message.from_user is None or message.from_user.id != settings.ADMIN_ID:
        return

    await message.answer(
        "Меню управления проверками:\n"
        "• Создать проверку\n"
        "• Список проверок",
        reply_markup=get_inspection_menu_keyboard(),
    )


async def list_inspections(message: types.Message) -> None:
    if message.from_user is None or message.from_user.id != settings.ADMIN_ID:
        return

    async with AsyncSessionFactory() as session:
        from app.database.repositories.inspection_repository import InspectionRepository
        repository = InspectionRepository(session)
        inspections = await repository.list_by_date()

    if not inspections:
        await message.answer("Список проверок пуст.", reply_markup=get_inspection_menu_keyboard())
        return

    lines = [
        f"#{inspection.id} | object_id={inspection.object_id} | engineer_id={inspection.engineer_id} | date={inspection.planned_date} | status={inspection.status}"
        for inspection in inspections
    ]
    await message.answer("\n".join(lines), reply_markup=get_inspection_menu_keyboard())


async def start_create_inspection(message: types.Message, state: FSMContext) -> None:
    if message.from_user is None or message.from_user.id != settings.ADMIN_ID:
        return

    await state.set_state(InspectionStates.waiting_object_id)
    await message.answer("Введите ID объекта для проверки.", reply_markup=get_inspection_menu_keyboard())


async def create_inspection_object_id(message: types.Message, state: FSMContext) -> None:
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

    if obj is None:
        await message.answer("Объект не найден.", reply_markup=get_inspection_menu_keyboard())
        await state.finish()
        return

    await state.update_data(object_id=object_id)
    await state.set_state(InspectionStates.waiting_engineer_id)
    await message.answer("Введите ID инженера для этой проверки.")


async def create_inspection_engineer_id(message: types.Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Введите корректный ID инженера.")
        return

    try:
        engineer_id = int(message.text)
    except ValueError:
        await message.answer("ID инженера должен быть числом.")
        return

    data = await state.get_data()
    async with AsyncSessionFactory() as session:
        service = ObjectService(session)
        obj = await service.get_object_by_id(data["object_id"])

    if obj is None:
        await message.answer("Объект не найден.", reply_markup=get_inspection_menu_keyboard())
        await state.finish()
        return

    planned_date = InspectionService.calculate_next_date(obj.monthly_day)
    inspection = InspectionService.build_inspection(obj, engineer_id, planned_date)

    async with AsyncSessionFactory() as session:
        from app.database.repositories.inspection_repository import InspectionRepository
        repository = InspectionRepository(session)
        await repository.create(inspection)

    await state.finish()
    await message.answer(
        f"Проверка создана для объекта #{data['object_id']} на дату {planned_date}.",
        reply_markup=get_inspection_menu_keyboard(),
    )


async def back_to_admin_menu(message: types.Message) -> None:
    if message.from_user is None or message.from_user.id != settings.ADMIN_ID:
        return

    await message.answer("Главное административное меню", reply_markup=get_admin_reply_keyboard())


def register_inspection_handlers(dp: Dispatcher) -> None:
    dp.register_message_handler(show_inspection_menu, text=["🛠 Проверки"], state="*")
    dp.register_message_handler(list_inspections, text=["📜 Список проверок"], state="*")
    dp.register_message_handler(start_create_inspection, text=["🗓 Создать проверку"], state="*")
    dp.register_message_handler(create_inspection_object_id, state=InspectionStates.waiting_object_id)
    dp.register_message_handler(create_inspection_engineer_id, state=InspectionStates.waiting_engineer_id)
    dp.register_message_handler(back_to_admin_menu, text=["⬅️ Назад"], state="*")
