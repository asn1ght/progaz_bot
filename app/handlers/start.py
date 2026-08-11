from __future__ import annotations

from aiogram import types
from aiogram.dispatcher import Dispatcher, FSMContext
from loguru import logger

from app.config import settings
from app.database.session import AsyncSessionFactory
from app.keyboards.accountant.menu import get_accountant_reply_keyboard
from app.keyboards.admin.menu import get_admin_reply_keyboard
from app.keyboards.admin.registration import get_registration_review_keyboard
from app.keyboards.engineer.menu import get_engineer_reply_keyboard
from app.services.user_service import UserService
from app.states.registration import RegistrationStates


async def start_command(message: types.Message, state: FSMContext) -> None:
    logger.debug(
        "start_command invoked: user_id={} chat_id={} text={!r}",
        message.from_user.id if message.from_user else None,
        message.chat.id,
        message.text,
    )

    async with AsyncSessionFactory() as session:
        service = UserService(session)
        user = await service.get_user_by_telegram_id(message.from_user.id)
        if user is not None:
            await state.finish()
            if user.role == "pending":
                await message.answer("Здравствуйте! Ваша заявка уже отправлена и ожидает подтверждения.")
            elif user.role == "admin":
                await message.answer(
                    "Здравствуйте! Вы уже зарегистрированы в боте как администратор.",
                    reply_markup=get_admin_reply_keyboard(),
                )
            elif user.role == "engineer":
                await message.answer(
                    "Здравствуйте! Вы уже зарегистрированы в боте как инженер.",
                    reply_markup=get_engineer_reply_keyboard(),
                )
            elif user.role == "accountant":
                await message.answer(
                    "Здравствуйте! Вы уже зарегистрированы в боте как бухгалтер.",
                    reply_markup=get_accountant_reply_keyboard(),
                )
            else:
                await message.answer(
                    f"Здравствуйте! Вы уже зарегистрированы в боте с ролью: {user.role}."
                )
            return

    await state.set_state(RegistrationStates.full_name)
    logger.debug("FSM state switched to full_name for user_id={}", message.from_user.id if message.from_user else None)
    await message.answer("Здравствуйте! Для регистрации введите ваше ФИО.")


async def handle_full_name(message: types.Message, state: FSMContext) -> None:
    logger.debug(
        "handle_full_name invoked: user_id={} text={!r}",
        message.from_user.id if message.from_user else None,
        message.text,
    )
    if not message.text:
        logger.debug("handle_full_name: empty text received")
        await message.answer("Пожалуйста, введите ФИО текстом.")
        return

    await state.update_data(full_name=message.text)
    await state.set_state(RegistrationStates.phone)
    logger.debug("handle_full_name: stored full_name and switched to phone state")
    await message.answer("Введите номер телефона.")


async def handle_phone(message: types.Message, state: FSMContext) -> None:
    logger.debug(
        "handle_phone invoked: user_id={} text={!r}",
        message.from_user.id if message.from_user else None,
        message.text,
    )
    if not message.text:
        logger.debug("handle_phone: empty text received")
        await message.answer("Пожалуйста, введите номер телефона текстом.")
        return

    phone = message.text
    data = await state.get_data()
    full_name = data.get("full_name", "")
    logger.debug("handle_phone: collected full_name={!r} phone={!r}", full_name, phone)

    async with AsyncSessionFactory() as session:
        service = UserService(session)
        logger.debug("handle_phone: calling register_pending_user for telegram_id={}", message.from_user.id if message.from_user else None)
        await service.register_pending_user(
            telegram_id=message.from_user.id,
            full_name=full_name,
            username=message.from_user.username,
            phone=phone,
        )

    admin_message = (
        f"Новая заявка на регистрацию\n"
        f"Telegram ID: {message.from_user.id}\n"
        f"ФИО: {full_name}\n"
        f"Username: {message.from_user.username or '-'}\n"
        f"Телефон: {phone}"
    )

    await message.answer("Ожидание подтверждения заявки.")
    logger.debug("handle_phone: sending admin notification to admin_id={}", settings.ADMIN_ID)
    await message.bot.send_message(
        settings.ADMIN_ID,
        admin_message,
        reply_markup=get_registration_review_keyboard(message.from_user.id),
    )
    await state.finish()
    logger.debug("handle_phone: FSM finished for user_id={}", message.from_user.id if message.from_user else None)


def register_start_handler(dp: Dispatcher) -> None:
    dp.register_message_handler(start_command, commands=["start"], state="*")
    dp.register_message_handler(
        handle_full_name,
        state=RegistrationStates.full_name,
        content_types=types.ContentType.TEXT,
    )
    dp.register_message_handler(
        handle_phone,
        state=RegistrationStates.phone,
        content_types=types.ContentType.TEXT,
    )
