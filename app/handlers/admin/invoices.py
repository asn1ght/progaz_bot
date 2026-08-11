from __future__ import annotations

from datetime import date

from aiogram import types
from aiogram.dispatcher import Dispatcher, FSMContext

from app.config import settings
from app.database.session import AsyncSessionFactory
from app.database.repositories.invoice_repository import InvoiceRepository
from app.keyboards.admin.invoices import get_invoice_menu_keyboard
from app.services.user_service import UserService
from app.states.invoice import AdminInvoiceStates
from app.utils.admin import is_admin_user_for_role


async def _is_admin_user(message: types.Message) -> bool:
    if message.from_user is None:
        return False

    async with AsyncSessionFactory() as session:
        service = UserService(session)
        user = await service.get_user_by_telegram_id(message.from_user.id)

    return is_admin_user_for_role(user.role if user else None, message.from_user.id, settings.ADMIN_ID)


async def show_invoice_menu(message: types.Message) -> None:
    if not await _is_admin_user(message):
        return

    await message.answer(
        "📑 <b>Управление счетами</b>\n\n"
        "• Все счета — полный список\n"
        "• Оплатить счет — отметить счет оплаченным",
        reply_markup=get_invoice_menu_keyboard(),
        parse_mode="HTML",
    )


async def list_all_invoices(message: types.Message) -> None:
    if not await _is_admin_user(message):
        return

    async with AsyncSessionFactory() as session:
        invoice_repository = InvoiceRepository(session)
        invoices = await invoice_repository.list_all()

    if not invoices:
        await message.answer("Список счетов пуст.", reply_markup=get_invoice_menu_keyboard())
        return

    lines = ["📑 <b>Все счета</b>\n"]
    for inv in invoices:
        status_icon = "✅" if inv.status == "paid" else "⏳"
        lines.append(
            f"#{inv.id} | объект #{inv.object_id} | {inv.issue_date} | "
            f"{inv.amount} ₽ | {status_icon} {inv.status}"
        )

    await message.answer("\n".join(lines), reply_markup=get_invoice_menu_keyboard())


async def start_pay_invoice(message: types.Message, state: FSMContext) -> None:
    if not await _is_admin_user(message):
        return

    await state.set_state(AdminInvoiceStates.waiting_invoice_id)
    await message.answer(
        "Введите ID счета, который нужно отметить оплаченным.",
        reply_markup=get_invoice_menu_keyboard(),
    )


async def pay_invoice_by_id(message: types.Message, state: FSMContext) -> None:
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
            await message.answer("Счет не найден.", reply_markup=get_invoice_menu_keyboard())
            await state.finish()
            return

        if invoice.status == "paid":
            await message.answer(
                f"Счет #{invoice.id} уже оплачен ({invoice.paid_date}).",
                reply_markup=get_invoice_menu_keyboard(),
            )
            await state.finish()
            return

        invoice.status = "paid"
        invoice.paid_date = date.today()
        await invoice_repository.update(invoice)

    await state.finish()
    await message.answer(
        f"✅ Счет #{invoice.id} на сумму {invoice.amount} ₽ отмечен оплаченным.",
        reply_markup=get_invoice_menu_keyboard(),
    )


def register_invoice_handlers(dp: Dispatcher) -> None:
    dp.register_message_handler(show_invoice_menu, text=["🧾 Счета"], state="*")
    dp.register_message_handler(list_all_invoices, text=["📜 Все счета"], state="*")
    dp.register_message_handler(start_pay_invoice, text=["💰 Оплатить счет"], state="*")
    dp.register_message_handler(pay_invoice_by_id, state=AdminInvoiceStates.waiting_invoice_id)
