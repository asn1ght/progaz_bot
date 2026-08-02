from __future__ import annotations

from datetime import date, timedelta

from aiogram import types
from aiogram.dispatcher import Dispatcher, FSMContext

from app.database.repositories.user_repository import UserRepository
from app.database.session import AsyncSessionFactory
from app.keyboards.engineer.inspection import get_inspection_action_keyboard
from app.keyboards.engineer.menu import get_engineer_reply_keyboard
from app.loader import bot
from app.services.object_service import ObjectService
from app.services.user_service import UserService
from app.states.engineer import EngineerStates
from app.utils.admin import is_admin_user_for_role
from app.config import settings


async def _is_engineer_user(message: types.Message) -> bool:
    if message.from_user is None:
        return False

    async with AsyncSessionFactory() as session:
        service = UserService(session)
        user = await service.get_user_by_telegram_id(message.from_user.id)

    return bool(user and user.role == "engineer") or is_admin_user_for_role(user.role if user else None, message.from_user.id, settings.ADMIN_ID)


async def engineer_menu(message: types.Message) -> None:
    if not await _is_engineer_user(message):
        return

    await message.answer(
        "Кабинет инженера",
        reply_markup=get_engineer_reply_keyboard(),
    )


async def show_my_objects(message: types.Message) -> None:
    if not await _is_engineer_user(message):
        return

    async with AsyncSessionFactory() as session:
        object_service = ObjectService(session)
        objects = await object_service.list_objects()

    engineer_objects = [obj for obj in objects if obj.engineer_id == message.from_user.id]
    if not engineer_objects:
        await message.answer("У вас нет назначенных объектов.", reply_markup=get_engineer_reply_keyboard())
        return

    lines = [f"{obj.name} | {obj.address} | день проверки: {obj.monthly_day}" for obj in engineer_objects]
    await message.answer("\n".join(lines), reply_markup=get_engineer_reply_keyboard())


async def show_today_inspections(message: types.Message) -> None:
    if not await _is_engineer_user(message):
        return

    today = date.today()
    async with AsyncSessionFactory() as session:
        from app.database.repositories.inspection_repository import InspectionRepository
        inspection_repository = InspectionRepository(session)
        inspections = await inspection_repository.list_by_date(today)

    relevant = [insp for insp in inspections if insp.engineer_id == message.from_user.id and insp.planned_date == today]
    if not relevant:
        await message.answer("Сегодня нет выездов.", reply_markup=get_engineer_reply_keyboard())
        return

    lines = []
    for insp in relevant:
        lines.append(f"Сегодня: #{insp.id} | дата {insp.planned_date}")
    await message.answer("\n".join(lines), reply_markup=get_engineer_reply_keyboard())

    for insp in relevant:
        obj = None
        async with AsyncSessionFactory() as session:
            object_service = ObjectService(session)
            obj = await object_service.get_object_by_id(insp.object_id)
        if obj is not None:
            await message.answer(
                f"Выезд #{insp.id}\nОбъект: {obj.name}\nАдрес: {obj.address}\nДата: {insp.planned_date}",
                reply_markup=get_inspection_action_keyboard(insp.id),
            )


async def show_tomorrow_inspections(message: types.Message) -> None:
    if not await _is_engineer_user(message):
        return

    tomorrow = date.today() + timedelta(days=1)
    async with AsyncSessionFactory() as session:
        from app.database.repositories.inspection_repository import InspectionRepository
        inspection_repository = InspectionRepository(session)
        inspections = await inspection_repository.list_by_date(tomorrow)

    relevant = [insp for insp in inspections if insp.engineer_id == message.from_user.id and insp.planned_date == tomorrow]
    if not relevant:
        await message.answer("Завтра нет выездов.", reply_markup=get_engineer_reply_keyboard())
        return

    lines = []
    for insp in relevant:
        lines.append(f"Завтра: #{insp.id} | дата {insp.planned_date}")
    await message.answer("\n".join(lines), reply_markup=get_engineer_reply_keyboard())

    for insp in relevant:
        obj = None
        async with AsyncSessionFactory() as session:
            object_service = ObjectService(session)
            obj = await object_service.get_object_by_id(insp.object_id)
        if obj is not None:
            await message.answer(
                f"Выезд #{insp.id}\nОбъект: {obj.name}\nАдрес: {obj.address}\nДата: {insp.planned_date}",
                reply_markup=get_inspection_action_keyboard(insp.id),
            )


async def start_complete_inspection(message: types.Message, state: FSMContext) -> None:
    if not await _is_engineer_user(message):
        return

    await state.set_state(EngineerStates.waiting_comment)
    await message.answer("Введите комментарий по выполненной проверке.", reply_markup=get_engineer_reply_keyboard())


async def complete_inspection_from_callback(callback_query: types.CallbackQuery, state: FSMContext) -> None:
    if callback_query.data is None:
        await callback_query.answer("Не удалось определить выезд.")
        return

    _, inspection_id_raw = callback_query.data.split(":", 1)
    try:
        inspection_id = int(inspection_id_raw)
    except ValueError:
        await callback_query.answer("Некорректный идентификатор выезда.")
        return

    await callback_query.message.answer("Введите комментарий по выполненной проверке.")
    await state.update_data(inspection_id=inspection_id)
    await state.set_state(EngineerStates.waiting_comment)
    await callback_query.answer()


async def complete_inspection(message: types.Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Введите текст комментария.")
        return

    data = await state.get_data()
    inspection_id = data.get("inspection_id")

    async with AsyncSessionFactory() as session:
        from app.database.repositories.inspection_repository import InspectionRepository
        inspection_repository = InspectionRepository(session)
        inspection = await inspection_repository.get_by_id(inspection_id) if inspection_id is not None else None

    if inspection is None or inspection.engineer_id != message.from_user.id:
        await message.answer("Выезд не найден или не принадлежит вам.")
        await state.finish()
        return

    inspection.comment = message.text
    inspection.status = "completed"
    async with AsyncSessionFactory() as session:
        from app.database.repositories.inspection_repository import InspectionRepository
        inspection_repository = InspectionRepository(session)
        await inspection_repository.update(inspection)

    await state.finish()
    async with AsyncSessionFactory() as session:
        user_repository = UserRepository(session)
        admins = await user_repository.list_admins()
        for admin in admins:
            await bot.send_message(
                admin.telegram_id,
                f"Инженер {message.from_user.full_name if message.from_user else 'инженер'} завершил проверку #{inspection.id}.\nКомментарий: {inspection.comment}",
            )

    await message.answer("Проверка отмечена как выполненная.", reply_markup=get_engineer_reply_keyboard())


def register_engineer_handlers(dp: Dispatcher) -> None:
    dp.register_message_handler(engineer_menu, text=["🧭 Мои объекты"], state="*")
    dp.register_message_handler(show_my_objects, text=["🧭 Мои объекты"], state="*")
    dp.register_message_handler(show_today_inspections, text=["📅 Сегодня"], state="*")
    dp.register_message_handler(show_tomorrow_inspections, text=["📅 Завтра"], state="*")
    dp.register_message_handler(start_complete_inspection, text=["✅ Проверка выполнена"], state="*")
    dp.register_callback_query_handler(complete_inspection_from_callback, lambda c: c.data and c.data.startswith("complete_inspection:"), state="*")
    dp.register_message_handler(complete_inspection, state=EngineerStates.waiting_comment)
