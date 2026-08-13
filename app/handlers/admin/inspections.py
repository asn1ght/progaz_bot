from __future__ import annotations

from datetime import date, datetime, timedelta

from aiogram import types
from aiogram.dispatcher import Dispatcher, FSMContext

from app.config import settings
from app.database.models import Inspection, Object
from app.database.repositories.user_repository import UserRepository
from app.database.session import AsyncSessionFactory
from app.keyboards.admin.inspections import (
    get_inspection_menu_keyboard,
    get_reschedule_confirm_keyboard,
    get_reschedule_keyboard,
)
from app.keyboards.admin.menu import get_admin_reply_keyboard
from app.keyboards.admin.objects import get_engineer_selection_keyboard
from app.loader import bot
from app.services.inspection_service import InspectionService
from app.services.object_service import ObjectService
from app.services.user_service import UserService
from app.states.inspection import InspectionStates
from app.utils.admin import is_admin_user_for_role


async def _is_admin_user(message: types.Message) -> bool:
    if message.from_user is None:
        return False

    async with AsyncSessionFactory() as session:
        service = UserService(session)
        user = await service.get_user_by_telegram_id(message.from_user.id)

    return is_admin_user_for_role(user.role if user else None, message.from_user.id, settings.ADMIN_ID)


async def show_inspection_menu(message: types.Message) -> None:
    if not await _is_admin_user(message):
        return

    await message.answer(
        "🛠 <b>Управление проверками</b>\n\n"
        "🗓 Создать — назначить новую проверку\n"
        "📜 Список — показать все проверки",
        reply_markup=get_inspection_menu_keyboard(),
        parse_mode="HTML",
    )


async def list_inspections(message: types.Message) -> None:
    if not await _is_admin_user(message):
        return

    async with AsyncSessionFactory() as session:
        from app.database.repositories.inspection_repository import InspectionRepository
        repository = InspectionRepository(session)
        inspections = await repository.list_by_date()

    if not inspections:
        await message.answer(
            "📭 <b>Список проверок пуст.</b>",
            reply_markup=get_inspection_menu_keyboard(),
            parse_mode="HTML",
        )
        return

    status_labels = {"planned": "⏳ запланирована", "completed": "✅ выполнена", "cancelled": "❌ отменена"}
    lines = [f"📜 <b>Проверки</b> ({len(inspections)} шт.)\n"]
    for insp in inspections:
        status = status_labels.get(insp.status, insp.status)
        lines.append(
            f"<b>#{insp.id}</b>  |  объект #{insp.object_id}  |  инженер #{insp.engineer_id}\n"
            f"   📅 {insp.planned_date}  |  {status}\n"
            f"   ─────────────────────"
        )

    await message.answer("\n".join(lines), reply_markup=get_inspection_menu_keyboard(), parse_mode="HTML")


async def start_create_inspection(message: types.Message, state: FSMContext) -> None:
    if not await _is_admin_user(message):
        return

    await state.set_state(InspectionStates.waiting_object_id)
    await message.answer(
        "🏷 <b>Введите ID объекта</b> для проверки.",
        reply_markup=get_inspection_menu_keyboard(),
        parse_mode="HTML",
    )


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

    async with AsyncSessionFactory() as session:
        user_repository = UserRepository(session)
        engineers = await user_repository.list_engineers()

    if not engineers:
        await message.answer(
            "⚠️ <b>В системе нет зарегистрированных инженеров.</b>",
            reply_markup=get_inspection_menu_keyboard(),
            parse_mode="HTML",
        )
        await state.finish()
        return

    await state.set_state(InspectionStates.waiting_engineer_id)
    await message.answer(
        "👷 <b>Выберите инженера</b> для проверки:",
        reply_markup=get_engineer_selection_keyboard(engineers),
        parse_mode="HTML",
    )


async def pick_inspection_engineer(callback_query: types.CallbackQuery, state: FSMContext) -> None:
    if callback_query.data is None:
        await callback_query.answer("Некорректные данные.")
        return

    _, value = callback_query.data.split(":", 1)

    if value == "skip":
        await callback_query.answer("Для проверки необходимо выбрать инженера.")
        return

    try:
        engineer_id = int(value)
    except ValueError:
        await callback_query.answer("Некорректный ID инженера.")
        return

    data = await state.get_data()
    async with AsyncSessionFactory() as session:
        service = ObjectService(session)
        obj = await service.get_object_by_id(data["object_id"])

    if obj is None:
        await callback_query.message.answer(
            "❌ Объект не найден.",
            reply_markup=get_inspection_menu_keyboard(),
        )
        await state.finish()
        await callback_query.answer()
        return

    from app.database.repositories.inspection_repository import InspectionRepository

    async with AsyncSessionFactory() as session:
        repository = InspectionRepository(session)
        today = datetime.utcnow().date()
        already_planned = await repository.get_planned_for_object_in_month(
            data["object_id"], today.year, today.month
        )
        if already_planned is not None:
            await callback_query.message.edit_reply_markup()
            await callback_query.message.answer(
                f"⚠️ <b>Дублирование запрещено!</b>\n\n"
                f"На объект #{data['object_id']} уже создана плановая проверка "
                f"<b>#{already_planned.id}</b> на {already_planned.planned_date} в текущем месяце.",
                reply_markup=get_inspection_menu_keyboard(),
                parse_mode="HTML",
            )
            await state.finish()
            await callback_query.answer()
            return

        planned_date = InspectionService.calculate_next_date(obj.monthly_day)
        inspection = InspectionService.build_inspection(obj, engineer_id, planned_date)
        await repository.create(inspection)

    await callback_query.message.edit_reply_markup()
    await state.finish()
    await callback_query.message.answer(
        f"✅ <b>Проверка создана!</b>\nОбъект #{data['object_id']}  |  📅 {planned_date}",
        reply_markup=get_inspection_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback_query.answer()


async def back_to_admin_menu(message: types.Message) -> None:
    if not await _is_admin_user(message):
        return

    await message.answer("Главное административное меню", reply_markup=get_admin_reply_keyboard())


async def reschedule_callback(callback_query: types.CallbackQuery) -> None:
    if callback_query.data is None:
        await callback_query.answer("Некорректные данные.")
        return

    _, inspection_id_raw, offset_raw = callback_query.data.split(":", 2)
    try:
        inspection_id = int(inspection_id_raw)
        offset = int(offset_raw)
    except ValueError:
        await callback_query.answer("Некорректные данные.")
        return

    new_date = datetime.utcnow().date() + timedelta(days=offset)
    await callback_query.message.edit_reply_markup()
    await callback_query.message.answer(
        f"❓ <b>Подтвердите перенос</b>\n\n"
        f"Перенести проверку <b>#{inspection_id}</b> на <b>{new_date}</b>?\n"
        f"Выбранная дата: {new_date}",
        reply_markup=get_reschedule_confirm_keyboard(inspection_id, new_date),
        parse_mode="HTML",
    )
    await callback_query.answer()


async def confirm_reschedule_callback(callback_query: types.CallbackQuery) -> None:
    if callback_query.data is None:
        await callback_query.answer("Некорректные данные.")
        return

    _, inspection_id_raw, date_raw = callback_query.data.split(":", 2)
    try:
        inspection_id = int(inspection_id_raw)
        new_date = date.fromisoformat(date_raw)
    except ValueError:
        await callback_query.answer("Некорректные данные.")
        return

    async with AsyncSessionFactory() as session:
        from app.database.repositories.inspection_repository import InspectionRepository
        from app.database.repositories.object_repository import ObjectRepository
        inspection_repository = InspectionRepository(session)
        inspection = await inspection_repository.get_by_id(inspection_id)

        if inspection is None:
            await callback_query.message.edit_reply_markup()
            await callback_query.message.answer("❌ Проверка не найдена.")
            await callback_query.answer()
            return

        inspection.planned_date = new_date
        await inspection_repository.update(inspection)

        object_repository = ObjectRepository(session)
        obj = await object_repository.get_by_id(inspection.object_id)
        obj_name = obj.name if obj else f"#{inspection.object_id}"

        try:
            from app.services.user_service import UserService
            user_service = UserService(session)
            engineer = await user_service.get_user_by_telegram_id(inspection.engineer_id)
            if engineer is not None:
                await bot.send_message(
                    engineer.telegram_id,
                    f"📅 Проверка #{inspection.id} по объекту {obj_name} перенесена на {new_date}.",
                )
        except Exception:
            pass

    await callback_query.message.edit_reply_markup()
    await callback_query.message.answer(
        f"✅ <b>Проверка #{inspection_id} перенесена на {new_date}.</b>\n"
        f"Инженер уведомлен.",
        parse_mode="HTML",
    )
    await callback_query.answer()


async def cancel_reschedule_callback(callback_query: types.CallbackQuery) -> None:
    await callback_query.message.edit_reply_markup()
    await callback_query.message.answer("❌ Перенос отменен.")
    await callback_query.answer()


def register_inspection_handlers(dp: Dispatcher) -> None:
    dp.register_message_handler(show_inspection_menu, text=["🛠 Проверки"], state="*")
    dp.register_message_handler(list_inspections, text=["📜 Список проверок"], state="*")
    dp.register_message_handler(start_create_inspection, text=["🗓 Создать проверку"], state="*")
    dp.register_message_handler(create_inspection_object_id, state=InspectionStates.waiting_object_id)
    dp.register_callback_query_handler(
        pick_inspection_engineer,
        lambda c: c.data and c.data.startswith("pick_engineer:"),
        state=InspectionStates.waiting_engineer_id,
    )
    dp.register_message_handler(back_to_admin_menu, text=["⬅️ Назад"], state="*")
    dp.register_callback_query_handler(
        reschedule_callback,
        lambda c: c.data and c.data.startswith("reschedule:") and not c.data.startswith("confirm_reschedule:"),
        state="*",
    )
    dp.register_callback_query_handler(
        confirm_reschedule_callback,
        lambda c: c.data and c.data.startswith("confirm_reschedule:"),
        state="*",
    )
    dp.register_callback_query_handler(
        cancel_reschedule_callback,
        lambda c: c.data and c.data.startswith("cancel_reschedule:"),
        state="*",
    )
