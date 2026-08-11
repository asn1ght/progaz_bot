from __future__ import annotations

from datetime import date

from aiogram import types
from aiogram.dispatcher import Dispatcher, FSMContext

from app.config import settings
from app.database.session import AsyncSessionFactory
from app.database.repositories.invoice_repository import InvoiceRepository
from app.keyboards.accountant.menu import get_accountant_reply_keyboard
from app.loader import bot
from app.services.user_service import UserService
from app.states.invoice import InvoiceStates


async def _get_current_user(message: types.Message):
    if message.from_user is None:
        return None

    async with AsyncSessionFactory() as session:
        service = UserService(session)
        return await service.get_user_by_telegram_id(message.from_user.id)


async def _is_accountant_user(message: types.Message) -> bool:
    if message.from_user is None:
        return False
    user = await _get_current_user(message)
    return bool(user and user.role == "accountant")


async def show_unpaid_invoices(message: types.Message) -> None:
    if not await _is_accountant_user(message):
        return

    async with AsyncSessionFactory() as session:
        invoice_repository = InvoiceRepository(session)
        invoices = await invoice_repository.list_by_status("waiting")

    if not invoices:
        await message.answer(
            "✅ Нет неоплаченных счетов.",
            reply_markup=get_accountant_reply_keyboard(),
        )
        return

    total = sum(inv.amount for inv in invoices)
    lines = [f"📑 <b>Неоплаченные счета</b> (на сумму {total} ₽)\n"]
    for inv in invoices:
        lines.append(
            f"#{inv.id} | объект #{inv.object_id} | {inv.issue_date} | "
            f"{inv.amount} ₽"
        )

    await message.answer("\n".join(lines), reply_markup=get_accountant_reply_keyboard())


async def start_mark_paid(message: types.Message, state: FSMContext) -> None:
    if not await _is_accountant_user(message):
        return

    await state.set_state(InvoiceStates.waiting_invoice_id)
    await message.answer(
        "Введите ID счета, который нужно отметить оплаченным.",
        reply_markup=get_accountant_reply_keyboard(),
    )


async def mark_paid_by_id(message: types.Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Введите корректный ID счета.")
        return

    try:
        invoice_id = int(message.text)
    except ValueError:
        await message.answer("ID счета должен быть числом.")
        return

    async with AsyncSessionFactory() as session:
        invoice_repository = InvoiceRepository(session)
        invoice = await invoice_repository.get_by_id(invoice_id)

        if invoice is None:
            await message.answer(
                "Счет не найден.",
                reply_markup=get_accountant_reply_keyboard(),
            )
            await state.finish()
            return

        if invoice.status == "paid":
            await message.answer(
                f"Счет #{invoice.id} уже оплачен ({invoice.paid_date}).",
                reply_markup=get_accountant_reply_keyboard(),
            )
            await state.finish()
            return

        invoice.status = "paid"
        invoice.paid_date = date.today()
        await invoice_repository.update(invoice)

        # Notify admin
        try:
            await bot.send_message(
                settings.ADMIN_ID,
                f"💰 Бухгалтер отметил оплату счета #{invoice.id} "
                f"на сумму {invoice.amount} ₽ (объект #{invoice.object_id}).",
            )
        except Exception:
            pass

    await state.finish()
    await message.answer(
        f"✅ Счет #{invoice.id} на сумму {invoice.amount} ₽ отмечен оплаченным. "
        "Администратор уведомлен.",
        reply_markup=get_accountant_reply_keyboard(),
    )


def register_accountant_handlers(dp: Dispatcher) -> None:
    dp.register_message_handler(show_unpaid_invoices, text=["🧾 Неоплаченные счета"], state="*")
    dp.register_message_handler(start_mark_paid, text=["💰 Отметить оплату"], state="*")
    dp.register_message_handler(mark_paid_by_id, state=InvoiceStates.waiting_invoice_id)
