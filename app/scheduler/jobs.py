from __future__ import annotations

from datetime import date, timedelta

from loguru import logger

from app.config import settings
from app.database.repositories.inspection_repository import InspectionRepository
from app.database.repositories.user_repository import UserRepository
from app.database.session import AsyncSessionFactory
from app.keyboards.admin.inspections import get_reschedule_keyboard
from app.keyboards.engineer.inspection import get_inspection_action_keyboard
from app.loader import bot
from app.services.inspection_service import InspectionService
from app.services.invoice_service import InvoiceService
from app.services.notification_service import NotificationService
from app.services.object_service import ObjectService
from app.services.user_service import UserService


async def run_daily_checks() -> None:
    logger.info("Starting daily scheduler checks")
    today = date.today()

    async with AsyncSessionFactory() as session:
        object_service = ObjectService(session)
        user_service = UserService(session)
        inspection_repository = InspectionRepository(session)
        user_repository = UserRepository(session)
        objects = await object_service.list_objects()

        for obj in objects:
            if not obj.engineer_id:
                continue

            existing_planned = await inspection_repository.get_planned_for_object(obj.id)
            if existing_planned is not None:
                continue

            effective_day = InspectionService.get_effective_schedule_day(obj, today)
            if effective_day == today.day:
                planned_date = InspectionService.calculate_next_date(effective_day, base_date=today)
                inspection = InspectionService.build_inspection(obj, obj.engineer_id, planned_date)
                await inspection_repository.create(inspection)

                try:
                    engineer = await user_service.get_user_by_id(obj.engineer_id)
                    if engineer is not None:
                        await bot.send_message(
                            engineer.telegram_id,
                            f"У вас запланирована проверка по объекту {obj.name} на {planned_date}.",
                        )
                except Exception as exc:
                    logger.warning("Failed to notify engineer {}: {}", obj.engineer_id, exc)

            if InvoiceService.should_create_invoice_for_date(today, obj.monthly_day):
                invoice = InvoiceService.build_invoice(obj, issue_date=today)
                from app.database.repositories.invoice_repository import InvoiceRepository
                invoice_repository = InvoiceRepository(session)
                await invoice_repository.create(invoice)

                try:
                    await bot.send_message(
                        settings.ADMIN_ID,
                        f"Создан счет для объекта {obj.name} на сумму {obj.invoice_amount}.",
                    )
                except Exception as exc:
                    logger.warning("Failed to notify admin about invoice: {}", exc)

                accountants = await user_repository.list_accountants()
                for accountant in accountants:
                    try:
                        message = NotificationService.build_accountant_invoice_message(
                            invoice.id, obj.name, str(obj.invoice_amount), invoice.issue_date
                        )
                        await bot.send_message(accountant.telegram_id, message)
                    except Exception as exc:
                        logger.warning("Failed to notify accountant {}: {}", accountant.telegram_id, exc)


async def run_morning_reminders() -> None:
    logger.info("Starting morning reminder checks")
    today = date.today()
    tomorrow = today + timedelta(days=1)

    async with AsyncSessionFactory() as session:
        object_service = ObjectService(session)
        user_service = UserService(session)
        inspection_repository = InspectionRepository(session)
        user_repository = UserRepository(session)
        inspections = await inspection_repository.list_by_date(today)

        relevant = [
            insp
            for insp in inspections
            if insp.status == "planned"
            and insp.planned_date in (today, tomorrow)
        ]

        plan_by_engineer: dict[int, dict[str, list[str]]] = {}
        for insp in relevant:
            obj = await object_service.get_object_by_id(insp.object_id)
            if obj is None:
                continue
            plan = plan_by_engineer.setdefault(insp.engineer_id, {"today": [], "tomorrow": []})
            key = "today" if insp.planned_date == today else "tomorrow"
            plan[key].append(obj.name)

        for engineer_id, plan in plan_by_engineer.items():
            lines = []
            if plan["today"]:
                lines.append(f"Сегодня: {', '.join(plan['today'])}")
            if plan["tomorrow"]:
                lines.append(f"Завтра: {', '.join(plan['tomorrow'])}")
            if not lines:
                continue

            engineer = await user_service.get_user_by_id(engineer_id)

            if engineer is not None:
                try:
                    await bot.send_message(
                        engineer.telegram_id,
                        "📅 <b>Напоминание о выездах</b>\n\n" + "\n".join(lines),
                        parse_mode="HTML",
                    )
                    logger.info("Sent morning reminder to engineer {}", engineer.telegram_id)
                except Exception as exc:
                    logger.warning("Failed to notify engineer {}: {}", engineer.telegram_id, exc)

            engineer_label = (
                f"@{engineer.username}"
                if engineer is not None and engineer.username
                else f"инженер #{engineer_id}"
            )
            admin_message = f"📅 <b>Выезды: {engineer_label}</b>\n\n" + "\n".join(lines)
            admins = await user_repository.list_admins()
            for admin in admins:
                if engineer is not None and admin.telegram_id == engineer.telegram_id:
                    continue
                try:
                    await bot.send_message(admin.telegram_id, admin_message, parse_mode="HTML")
                    logger.info("Sent morning reminder to admin {}", admin.telegram_id)
                except Exception as exc:
                    logger.warning("Failed to notify admin {}: {}", admin.telegram_id, exc)


async def run_evening_checks() -> None:
    logger.info("Starting evening scheduler checks")
    today = date.today()

    async with AsyncSessionFactory() as session:
        object_service = ObjectService(session)
        user_service = UserService(session)
        inspection_repository = InspectionRepository(session)
        user_repository = UserRepository(session)
        inspections = await inspection_repository.list_by_date(today)

        overdue = [
            insp
            for insp in inspections
            if insp.planned_date == today and insp.status == "planned"
        ]

        for inspection in overdue:
            obj = await object_service.get_object_by_id(inspection.object_id)
            if obj is None:
                continue

            engineer = await user_service.get_user_by_id(inspection.engineer_id)

            # Уведомление инженеру с кнопками
            if engineer is not None:
                try:
                    await bot.send_message(
                        engineer.telegram_id,
                        f"⏰ <b>Напоминание</b>\n\n"
                        f"Сегодня у вас проверка объекта <b>{obj.name}</b> "
                        f"(#{inspection.id}), она ещё не отмечена выполненной.",
                        reply_markup=get_inspection_action_keyboard(inspection.id),
                        parse_mode="HTML",
                    )
                except Exception as exc:
                    logger.warning("Failed to notify engineer {}: {}", engineer.telegram_id, exc)

            # Уведомление администратору с кнопками переноса
            engineer_label = (
                f"@{engineer.username}"
                if engineer is not None and engineer.username
                else "инженер"
            )
            admins = await user_repository.list_admins()
            for admin in admins:
                if engineer is not None and admin.telegram_id == engineer.telegram_id:
                    continue
                try:
                    await bot.send_message(
                        admin.telegram_id,
                        f"⚠️ <b>Проверка не выполнена</b>\n\n"
                        f"Проверка #{inspection.id} по объекту <b>{obj.name}</b> "
                        f"({engineer_label}) до сих пор не выполнена.\n"
                        f"Перенесите проверку на другой день:",
                        reply_markup=get_reschedule_keyboard(inspection.id),
                        parse_mode="HTML",
                    )
                except Exception as exc:
                    logger.warning("Failed to notify admin {}: {}", admin.telegram_id, exc)
