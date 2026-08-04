from __future__ import annotations

from decimal import Decimal, InvalidOperation

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


async def _is_admin_user(message: types.Message) -> bool:
    if message.from_user is None:
        return False

    async with AsyncSessionFactory() as session:
        service = UserService(session)
        user = await service.get_user_by_telegram_id(message.from_user.id)

    return is_admin_user_for_role(user.role if user else None, message.from_user.id, settings.ADMIN_ID)


async def show_object_menu(message: types.Message) -> None:
    if not await _is_admin_user(message):
        return

    await message.answer(
        "Меню управления объектами:\n"
        "• Добавить объект\n"
        "• Список объектов\n"
        "• Изменить объект\n"
        "• Удалить объект",
        reply_markup=get_object_menu_keyboard(),
    )


async def list_objects(message: types.Message) -> None:
    if not await _is_admin_user(message):
        return

    async with AsyncSessionFactory() as session:
        service = ObjectService(session)
        objects = await service.list_objects()

    if not objects:
        await message.answer("Список объектов пуст.", reply_markup=get_object_menu_keyboard())
        return

    lines = [
        f"#{obj.id} | {obj.name} | {obj.address} | engineer_id={obj.engineer_id or '-'} | day={obj.monthly_day} | amount={obj.invoice_amount}"
        for obj in objects
    ]
    await message.answer("\n".join(lines), reply_markup=get_object_menu_keyboard())


async def start_add_object(message: types.Message, state: FSMContext) -> None:
    if not await _is_admin_user(message):
        return

    await state.set_state(ObjectStates.waiting_name)
    await message.answer("Введите название объекта.", reply_markup=get_object_menu_keyboard())


async def add_object_name(message: types.Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Введите корректное название.")
        return

    await state.update_data(name=message.text)
    await state.set_state(ObjectStates.waiting_address)
    await message.answer("Введите адрес объекта.")


async def add_object_address(message: types.Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Введите корректный адрес.")
        return

    await state.update_data(address=message.text)
    await state.set_state(ObjectStates.waiting_engineer_id)
    await message.answer("Введите ID инженера или 0, если инженер пока не назначен.")


async def add_object_engineer_id(message: types.Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Введите корректный ID инженера.")
        return

    try:
        engineer_id = int(message.text)
    except ValueError:
        await message.answer("ID инженера должен быть числом.")
        return

    await state.update_data(engineer_id=None if engineer_id == 0 else engineer_id)
    await state.set_state(ObjectStates.waiting_monthly_day)
    await message.answer("Введите день проверки объекта (1-31).")


async def add_object_monthly_day(message: types.Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Введите корректный день месяца.")
        return

    try:
        monthly_day = int(message.text)
    except ValueError:
        await message.answer("День должен быть числом.")
        return

    if not 1 <= monthly_day <= 31:
        await message.answer("День должен быть в диапазоне 1-31.")
        return

    await state.update_data(monthly_day=monthly_day)
    await state.set_state(ObjectStates.waiting_invoice_amount)
    await message.answer("Введите сумму обслуживания (например: 15000.00).")


async def add_object_invoice_amount(message: types.Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Введите корректную сумму.")
        return

    try:
        invoice_amount = Decimal(message.text)
    except InvalidOperation:
        await message.answer("Сумма должна быть числом, например 15000.00.")
        return

    await state.update_data(invoice_amount=invoice_amount)
    await state.set_state(ObjectStates.waiting_comment)
    await message.answer("Введите комментарий или отправьте '-' если комментария нет.")


async def add_object_comment(message: types.Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Введите корректный комментарий.")
        return

    data = await state.get_data()
    comment = None if message.text.strip() == "-" else message.text

    async with AsyncSessionFactory() as session:
        service = ObjectService(session)
        await service.create_object(
            name=data["name"],
            address=data["address"],
            monthly_day=data["monthly_day"],
            invoice_amount=data["invoice_amount"],
            engineer_id=data.get("engineer_id"),
            comment=comment,
        )

    await state.finish()
    await message.answer(
        "Объект успешно создан.",
        reply_markup=get_object_menu_keyboard(),
    )


async def start_edit_object(message: types.Message, state: FSMContext) -> None:
    if not await _is_admin_user(message):
        return

    await state.set_state(ObjectStates.waiting_edit_object_id)
    await message.answer("Введите ID объекта, который хотите изменить.", reply_markup=get_object_menu_keyboard())


async def edit_object_id(message: types.Message, state: FSMContext) -> None:
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
        await message.answer("Объект не найден.", reply_markup=get_object_menu_keyboard())
        await state.finish()
        return

    await state.update_data(object_id=object_id)
    await state.set_state(ObjectStates.waiting_new_name)
    await message.answer("Введите новое название объекта.")


async def edit_object_name(message: types.Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Введите корректное название.")
        return

    data = await state.get_data()
    async with AsyncSessionFactory() as session:
        service = ObjectService(session)
        await service.update_object(data["object_id"], name=message.text)

    await state.set_state(ObjectStates.waiting_new_address)
    await message.answer("Введите новый адрес объекта.")


async def edit_object_address(message: types.Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Введите корректный адрес.")
        return

    data = await state.get_data()
    async with AsyncSessionFactory() as session:
        service = ObjectService(session)
        await service.update_object(data["object_id"], address=message.text)

    await state.set_state(ObjectStates.waiting_new_engineer_id)
    await message.answer("Введите новый ID инженера или 0, если инженер не назначен.")


async def edit_object_engineer_id(message: types.Message, state: FSMContext) -> None:
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
        await service.update_object(data["object_id"], engineer_id=None if engineer_id == 0 else engineer_id)

    await state.set_state(ObjectStates.waiting_new_monthly_day)
    await message.answer("Введите новый день проверки объекта (1-31).")


async def edit_object_monthly_day(message: types.Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Введите корректный день месяца.")
        return

    try:
        monthly_day = int(message.text)
    except ValueError:
        await message.answer("День должен быть числом.")
        return

    if not 1 <= monthly_day <= 31:
        await message.answer("День должен быть в диапазоне 1-31.")
        return

    data = await state.get_data()
    async with AsyncSessionFactory() as session:
        service = ObjectService(session)
        await service.update_object(data["object_id"], monthly_day=monthly_day)

    await state.set_state(ObjectStates.waiting_new_invoice_amount)
    await message.answer("Введите новую сумму обслуживания (например: 15000.00).")


async def edit_object_invoice_amount(message: types.Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Введите корректную сумму.")
        return

    try:
        invoice_amount = Decimal(message.text)
    except InvalidOperation:
        await message.answer("Сумма должна быть числом, например 15000.00.")
        return

    data = await state.get_data()
    async with AsyncSessionFactory() as session:
        service = ObjectService(session)
        await service.update_object(data["object_id"], invoice_amount=invoice_amount)

    await state.set_state(ObjectStates.waiting_new_comment)
    await message.answer("Введите новый комментарий или отправьте '-' если комментария нет.")


async def edit_object_comment(message: types.Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Введите корректный комментарий.")
        return

    data = await state.get_data()
    comment = None if message.text.strip() == "-" else message.text
    async with AsyncSessionFactory() as session:
        service = ObjectService(session)
        await service.update_object(data["object_id"], comment=comment)

    await state.finish()
    await message.answer("Объект успешно обновлен.", reply_markup=get_object_menu_keyboard())


async def start_delete_object(message: types.Message, state: FSMContext) -> None:
    if not await _is_admin_user(message):
        return

    await state.set_state(ObjectStates.waiting_delete_object_id)
    await message.answer("Введите ID объекта, который хотите удалить.", reply_markup=get_object_menu_keyboard())


async def delete_object(message: types.Message, state: FSMContext) -> None:
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
        obj = await service.delete_object(object_id)

    if obj is None:
        await message.answer("Объект не найден.", reply_markup=get_object_menu_keyboard())
    else:
        await message.answer(
            f"Объект #{obj.id} удален.",
            reply_markup=get_object_menu_keyboard(),
        )
    await state.finish()


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

    if obj is None:
        await message.answer("Объект не найден.", reply_markup=get_object_menu_keyboard())
        await state.finish()
        return

    await state.update_data(object_id=object_id)
    await state.set_state(ObjectStates.waiting_schedule_new_day)
    await message.answer("Введите новый день месяца для проверки (1-31).")


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
    await message.answer("Выберите вариант переноса:\n1. Только на этот месяц\n2. Постоянно", reply_markup=get_object_menu_keyboard())


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
        if mode in {"1", "только на этот месяц", "этот месяц"}:
            await service.create_temporary_change(object_id, new_day)
            await message.answer("Дата перенесена только на этот месяц.", reply_markup=get_object_menu_keyboard())
        else:
            await service.create_permanent_change(object_id, new_day)
            await message.answer("Дата перенесена постоянно.", reply_markup=get_object_menu_keyboard())

    await state.finish()


async def back_to_admin_menu(message: types.Message) -> None:
    if not await _is_admin_user(message):
        return

    await message.answer("Главное административное меню", reply_markup=get_admin_reply_keyboard())


def register_object_handlers(dp: Dispatcher) -> None:
    dp.register_message_handler(show_object_menu, text=["📦 Объекты"], state="*")
    dp.register_message_handler(list_objects, text=["📋 Список объектов"], state="*")
    dp.register_message_handler(start_add_object, text=["➕ Добавить объект"], state="*")
    dp.register_message_handler(add_object_name, state=ObjectStates.waiting_name)
    dp.register_message_handler(add_object_address, state=ObjectStates.waiting_address)
    dp.register_message_handler(add_object_engineer_id, state=ObjectStates.waiting_engineer_id)
    dp.register_message_handler(add_object_monthly_day, state=ObjectStates.waiting_monthly_day)
    dp.register_message_handler(add_object_invoice_amount, state=ObjectStates.waiting_invoice_amount)
    dp.register_message_handler(add_object_comment, state=ObjectStates.waiting_comment)

    dp.register_message_handler(start_edit_object, text=["✏️ Изменить объект"], state="*")
    dp.register_message_handler(edit_object_id, state=ObjectStates.waiting_edit_object_id)
    dp.register_message_handler(edit_object_name, state=ObjectStates.waiting_new_name)
    dp.register_message_handler(edit_object_address, state=ObjectStates.waiting_new_address)
    dp.register_message_handler(edit_object_engineer_id, state=ObjectStates.waiting_new_engineer_id)
    dp.register_message_handler(edit_object_monthly_day, state=ObjectStates.waiting_new_monthly_day)
    dp.register_message_handler(edit_object_invoice_amount, state=ObjectStates.waiting_new_invoice_amount)
    dp.register_message_handler(edit_object_comment, state=ObjectStates.waiting_new_comment)

    dp.register_message_handler(start_delete_object, text=["🗑 Удалить объект"], state="*")
    dp.register_message_handler(delete_object, state=ObjectStates.waiting_delete_object_id)

    dp.register_message_handler(start_schedule_change, text=["🔁 Перенос дат"], state="*")
    dp.register_message_handler(schedule_change_object_id, state=ObjectStates.waiting_schedule_object_id)
    dp.register_message_handler(schedule_change_new_day, state=ObjectStates.waiting_schedule_new_day)
    dp.register_message_handler(schedule_change_mode, state=ObjectStates.waiting_schedule_mode)

    dp.register_message_handler(back_to_admin_menu, text=["⬅️ Назад"], state="*")
