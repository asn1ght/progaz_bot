from __future__ import annotations

from decimal import Decimal, InvalidOperation

from aiogram import types
from aiogram.dispatcher import Dispatcher, FSMContext

from app.config import settings
from app.database.repositories.user_repository import UserRepository
from app.database.session import AsyncSessionFactory
from app.keyboards.admin.menu import get_admin_reply_keyboard
from app.keyboards.admin.objects import get_engineer_selection_keyboard, get_object_menu_keyboard
from app.services.object_service import ObjectService
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
        "📦 <b>Управление объектами</b>\n\n"
        "➕ Добавить — создать новый объект\n"
        "📋 Список — показать все объекты\n"
        "✏️ Изменить — редактировать объект\n"
        "🗑 Удалить — деактивировать объект\n"
        "🔁 Перенос дат — изменить график проверок",
        reply_markup=get_object_menu_keyboard(),
        parse_mode="HTML",
    )


async def list_objects(message: types.Message) -> None:
    if not await _is_admin_user(message):
        return

    async with AsyncSessionFactory() as session:
        service = ObjectService(session)
        objects = await service.list_objects()

    if not objects:
        await message.answer(
            "📭 <b>Список объектов пуст.</b>",
            reply_markup=get_object_menu_keyboard(),
            parse_mode="HTML",
        )
        return

    lines = [f"📋 <b>Объекты</b> ({len(objects)} шт.)\n"]
    for obj in objects:
        eng = f"инженер #{obj.engineer_id}" if obj.engineer_id else "не назначен"
        lines.append(
            f"<b>#{obj.id} — {obj.name}</b>\n"
            f"   📍 {obj.address}\n"
            f"   👷 {eng}  |  📅 день: <b>{obj.monthly_day}</b>  |  💰 {obj.invoice_amount} ₽\n"
            f"   ─────────────────────"
        )

    await message.answer("\n".join(lines), reply_markup=get_object_menu_keyboard(), parse_mode="HTML")


async def start_add_object(message: types.Message, state: FSMContext) -> None:
    if not await _is_admin_user(message):
        return

    await state.set_state(ObjectStates.waiting_name)
    await message.answer("🏷 <b>Введите название объекта.</b>", reply_markup=get_object_menu_keyboard(), parse_mode="HTML")


async def add_object_name(message: types.Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Введите корректное название.")
        return

    await state.update_data(name=message.text)
    await state.set_state(ObjectStates.waiting_address)
    await message.answer("📍 <b>Введите адрес объекта.</b>", parse_mode="HTML")


async def add_object_address(message: types.Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Введите корректный адрес.")
        return

    await state.update_data(address=message.text)

    async with AsyncSessionFactory() as session:
        user_repository = UserRepository(session)
        engineers = await user_repository.list_engineers()

    if not engineers:
        await state.update_data(engineer_id=None)
        await state.set_state(ObjectStates.waiting_monthly_day)
        await message.answer(
            "⚠️ <b>В системе нет зарегистрированных инженеров.</b>\nИнженер не назначен.\n\n🔢 Введите день проверки объекта (1-31).",
            reply_markup=get_object_menu_keyboard(),
            parse_mode="HTML",
        )
        return

    await state.set_state(ObjectStates.waiting_engineer_id)
    await message.answer(
        "Выберите инженера из списка:",
        reply_markup=get_engineer_selection_keyboard(engineers),
    )


async def pick_engineer_callback(callback_query: types.CallbackQuery, state: FSMContext) -> None:
    if callback_query.data is None:
        await callback_query.answer("Некорректные данные.")
        return

    _, value = callback_query.data.split(":", 1)

    if value == "skip":
        await state.update_data(engineer_id=None)
        await callback_query.message.edit_reply_markup()  # remove inline keyboard
    else:
        try:
            engineer_id = int(value)
        except ValueError:
            await callback_query.answer("Некорректный ID инженера.")
            return
        await state.update_data(engineer_id=engineer_id)

    await state.set_state(ObjectStates.waiting_monthly_day)
    await callback_query.message.answer(
        "🔢 <b>Введите день проверки объекта</b> (1-31).",
        reply_markup=get_object_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback_query.answer()


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
    await message.answer("💰 <b>Введите сумму обслуживания</b> (например: 15000.00).", parse_mode="HTML")


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
    await message.answer("💬 <b>Введите комментарий</b> или отправьте \"-\" если комментария нет.", parse_mode="HTML")


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
        "✅ <b>Объект успешно создан!</b>",
        reply_markup=get_object_menu_keyboard(),
        parse_mode="HTML",
    )


async def start_edit_object(message: types.Message, state: FSMContext) -> None:
    if not await _is_admin_user(message):
        return

    await state.set_state(ObjectStates.waiting_edit_object_id)
    await message.answer(
        "✏️ <b>Введите ID объекта</b> для редактирования.",
        reply_markup=get_object_menu_keyboard(),
        parse_mode="HTML",
    )


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
    await message.answer("✏️ <b>Введите новое название объекта.</b>", parse_mode="HTML")


async def edit_object_name(message: types.Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Введите корректное название.")
        return

    data = await state.get_data()
    async with AsyncSessionFactory() as session:
        service = ObjectService(session)
        await service.update_object(data["object_id"], name=message.text)

    await state.set_state(ObjectStates.waiting_new_address)
    await message.answer("📍 <b>Введите новый адрес объекта.</b>", parse_mode="HTML")


async def edit_object_address(message: types.Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Введите корректный адрес.")
        return

    data = await state.get_data()
    async with AsyncSessionFactory() as session:
        service = ObjectService(session)
        await service.update_object(data["object_id"], address=message.text)

    await state.set_state(ObjectStates.waiting_new_engineer_id)
    await message.answer(
        "👷 <b>Введите новый ID инженера</b> или 0, если инженер не назначен.",
        parse_mode="HTML",
    )


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
    await message.answer("🔢 <b>Введите новый день проверки</b> (1-31).", parse_mode="HTML")


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
    await message.answer("💰 <b>Введите новую сумму обслуживания</b> (например: 15000.00).", parse_mode="HTML")


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
    await message.answer("💬 <b>Введите новый комментарий</b> или отправьте \"-\" если комментария нет.", parse_mode="HTML")


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
    await message.answer(
        "✅ <b>Объект успешно обновлен.</b>",
        reply_markup=get_object_menu_keyboard(),
        parse_mode="HTML",
    )


async def start_delete_object(message: types.Message, state: FSMContext) -> None:
    if not await _is_admin_user(message):
        return

    await state.set_state(ObjectStates.waiting_delete_object_id)
    await message.answer(
        "🗑 <b>Введите ID объекта</b> для удаления.",
        reply_markup=get_object_menu_keyboard(),
        parse_mode="HTML",
    )


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
        await message.answer(
            "❌ <b>Объект не найден.</b>",
            reply_markup=get_object_menu_keyboard(),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            f"🗑 <b>Объект #{obj.id} ({obj.name}) деактивирован.</b>",
            reply_markup=get_object_menu_keyboard(),
            parse_mode="HTML",
        )
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
    dp.register_callback_query_handler(
        pick_engineer_callback,
        lambda c: c.data and c.data.startswith("pick_engineer:"),
        state=ObjectStates.waiting_engineer_id,
    )
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

    dp.register_message_handler(back_to_admin_menu, text=["⬅️ Назад"], state="*")
