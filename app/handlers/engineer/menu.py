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
from app.utils.engineer import matches_engineer_assignment
from app.config import settings


async def _get_current_user(message: types.Message):
    if message.from_user is None:
        return None

    async with AsyncSessionFactory() as session:
        service = UserService(session)
        return await service.get_user_by_telegram_id(message.from_user.id)


async def _is_engineer_user(message: types.Message) -> bool:
    user = await _get_current_user(message)
    return bool(user and user.role == "engineer") or is_admin_user_for_role(user.role if user else None, message.from_user.id, settings.ADMIN_ID) if message.from_user is not None else False




async def show_my_objects(message: types.Message) -> None:
    if not await _is_engineer_user(message):
        return

    user = await _get_current_user(message)
    if user is None:
        return

    async with AsyncSessionFactory() as session:
        object_service = ObjectService(session)
        objects = await object_service.list_objects_by_engineer(user.id)

        if not objects:
            await message.answer(
                "📭 <b>У вас пока нет назначенных объектов.</b>\n\n"
                "Обратитесь к администратору для назначения.",
                reply_markup=get_engineer_reply_keyboard(),
                parse_mode="HTML",
            )
            return

        from app.database.repositories.inspection_repository import InspectionRepository
        inspection_repository = InspectionRepository(session)
        planned_map = await inspection_repository.get_nearest_planned_for_objects([obj.id for obj in objects])

    lines = [f"📋 <b>Ваши объекты</b> ({len(objects)} шт.)\n"]
    for i, obj in enumerate(objects, 1):
        planned = planned_map.get(obj.id)
        next_date_str = (
            f"📅 <i>{planned.planned_date.strftime('%d.%m.%Y')}</i>"
            if planned
            else "⏳ не запланирована"
        )
        lines.append(
            f"<b>{i}. {obj.name}</b>\n"
            f"   📍 {obj.address}\n"
            f"   🔢 День проверки: <b>{obj.monthly_day}</b>\n"
            f"   {next_date_str}"
        )

    await message.answer("\n".join(lines), reply_markup=get_engineer_reply_keyboard(), parse_mode="HTML")


async def show_today_inspections(message: types.Message) -> None:
    if not await _is_engineer_user(message):
        return

    user = await _get_current_user(message)
    today = date.today()
    async with AsyncSessionFactory() as session:
        from app.database.repositories.inspection_repository import InspectionRepository
        inspection_repository = InspectionRepository(session)
        inspections = await inspection_repository.list_by_date(today)

    relevant = [
        insp
        for insp in inspections
        if matches_engineer_assignment(user.id if user else None, insp.engineer_id)
        and insp.planned_date == today
        and insp.status != "completed"
        and insp.status != "cancelled"
    ]
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

    user = await _get_current_user(message)
    tomorrow = date.today() + timedelta(days=1)
    async with AsyncSessionFactory() as session:
        from app.database.repositories.inspection_repository import InspectionRepository
        inspection_repository = InspectionRepository(session)
        inspections = await inspection_repository.list_by_date(tomorrow)

    relevant = [
        insp
        for insp in inspections
        if matches_engineer_assignment(user.id if user else None, insp.engineer_id)
        and insp.planned_date == tomorrow
        and insp.status != "completed"
        and insp.status != "cancelled"
    ]
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

    await callback_query.message.edit_reply_markup()
    await callback_query.message.answer("Введите комментарий по выполненной проверке.")
    await state.update_data(inspection_id=inspection_id)
    await state.set_state(EngineerStates.waiting_comment)
    await callback_query.answer()


async def complete_inspection(message: types.Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Введите текст комментария.")
        return

    user = await _get_current_user(message)
    data = await state.get_data()
    inspection_id = data.get("inspection_id")

    async with AsyncSessionFactory() as session:
        from app.database.repositories.inspection_repository import InspectionRepository
        inspection_repository = InspectionRepository(session)
        inspection = await inspection_repository.get_by_id(inspection_id) if inspection_id is not None else None

        if inspection is None or not matches_engineer_assignment(user.id if user else None, inspection.engineer_id):
            await message.answer("Выезд не найден или не принадлежит вам.")
            await state.finish()
            return

        inspection.comment = message.text
        inspection.status = "completed"
        await inspection_repository.update(inspection)

        await state.finish()
        user_repository = UserRepository(session)
        admins = await user_repository.list_admins()
        for admin in admins:
            await bot.send_message(
                admin.telegram_id,
                f"Инженер {message.from_user.full_name if message.from_user else 'инженер'} завершил проверку #{inspection.id}.\nКомментарий: {inspection.comment}",
            )

    await message.answer("Проверка отмечена как выполненная.", reply_markup=get_engineer_reply_keyboard())


async def cannot_complete_from_callback(callback_query: types.CallbackQuery, state: FSMContext) -> None:
    if callback_query.data is None:
        await callback_query.answer("Не удалось определить выезд.")
        return

    _, inspection_id_raw = callback_query.data.split(":", 1)
    try:
        inspection_id = int(inspection_id_raw)
    except ValueError:
        await callback_query.answer("Некорректный идентификатор выезда.")
        return

    await callback_query.message.edit_reply_markup()
    await state.update_data(inspection_id=inspection_id)
    await state.set_state(EngineerStates.waiting_fail_reason)
    await callback_query.message.answer(
        "📝 <b>Укажите причину</b>, почему выезд не может быть выполнен.\n\n"
        "Если нужна помощь — свяжитесь с администратором.\n"
        "Администратор получит уведомление.",
        reply_markup=get_engineer_reply_keyboard(),
        parse_mode="HTML",
    )
    await callback_query.answer()


async def cannot_complete_reason(message: types.Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Введите текст причины.")
        return

    user = await _get_current_user(message)
    data = await state.get_data()
    inspection_id = data.get("inspection_id")

    async with AsyncSessionFactory() as session:
        from app.database.repositories.inspection_repository import InspectionRepository
        inspection_repository = InspectionRepository(session)
        inspection = await inspection_repository.get_by_id(inspection_id) if inspection_id is not None else None

        if inspection is None or not matches_engineer_assignment(user.id if user else None, inspection.engineer_id):
            await message.answer("Выезд не найден или не принадлежит вам.")
            await state.finish()
            return

        inspection.comment = message.text
        inspection.status = "cancelled"
        await inspection_repository.update(inspection)

        await state.finish()
        user_repository = UserRepository(session)
        admins = await user_repository.list_admins()
        engineer_name = message.from_user.full_name if message.from_user else "инженер"
        for admin in admins:
            await bot.send_message(
                admin.telegram_id,
                f"⚠️ Инженер {engineer_name} не может выполнить проверку #{inspection.id} "
                f"(объект #{inspection.object_id}, {inspection.planned_date}).\n"
                f"Причина: {inspection.comment}",
            )

    await message.answer(
        "⚠️ Выезд отмечен как невыполненный. Администратор уведомлен.",
        reply_markup=get_engineer_reply_keyboard(),
    )


def register_engineer_handlers(dp: Dispatcher) -> None:
    dp.register_message_handler(show_my_objects, text=["🧭 Мои объекты"], state="*")
    dp.register_message_handler(show_today_inspections, text=["📅 Сегодня"], state="*")
    dp.register_message_handler(show_tomorrow_inspections, text=["📅 Завтра"], state="*")
    dp.register_callback_query_handler(complete_inspection_from_callback, lambda c: c.data and c.data.startswith("complete_inspection:"), state="*")
    dp.register_message_handler(complete_inspection, state=EngineerStates.waiting_comment)
    dp.register_callback_query_handler(cannot_complete_from_callback, lambda c: c.data and c.data.startswith("fail_inspection:"), state="*")
    dp.register_message_handler(cannot_complete_reason, state=EngineerStates.waiting_fail_reason)
