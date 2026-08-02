from __future__ import annotations

from datetime import date, datetime

from loguru import logger

from app.config import settings
from app.database.repositories.inspection_repository import InspectionRepository
from app.database.repositories.user_repository import UserRepository
from app.database.session import AsyncSessionFactory
from app.loader import bot
from app.services.inspection_service import InspectionService
from app.services.invoice_service import InvoiceService
from app.services.notification_service import NotificationService
from app.services.object_service import ObjectService
from app.services.user_service import UserService


async def run_daily_checks() -> None:
    logger.info("Starting daily scheduler checks")
    today = date.today()
    now = datetime.now(NotificationService.MOSCOW_TZ)

    async with AsyncSessionFactory() as session:
        object_service = ObjectService(session)
        user_service = UserService(session)
        inspection_repository = InspectionRepository(session)
        user_repository = UserRepository(session)
        objects = await object_service.list_objects()

        for obj in objects:
            if not obj.engineer_id:
                continue

            if obj.monthly_day == today.day:
                planned_date = InspectionService.calculate_next_date(obj.monthly_day, base_date=today)
                inspection = InspectionService.build_inspection(obj, obj.engineer_id, planned_date)
                await inspection_repository.create(inspection)

                try:
                    engineer = await user_service.get_user_by_telegram_id(obj.engineer_id)
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

        if not NotificationService.should_send_reminder(now):
            logger.info("Skipping reminder dispatch outside 10:00 Moscow time")
            return

        reminders = await inspection_repository.list_by_date(today)
        for inspection in reminders:
            if inspection.object_id is None:
                continue
            obj = await object_service.get_object_by_id(inspection.object_id)
            if obj is None:
                continue

            kind = NotificationService.reminder_kind(inspection.planned_date, today)
            if kind is None:
                continue

            try:
                engineer = await user_service.get_user_by_telegram_id(inspection.engineer_id)
                if engineer is not None:
                    engineer_message = NotificationService.build_engineer_reminder_message(
                        obj.name,
                        inspection.planned_date,
                        kind,
                    )
                    await bot.send_message(engineer.telegram_id, engineer_message)
                    logger.info(
                        "Sent reminder to engineer {} for inspection {} ({})",
                        engineer.telegram_id,
                        inspection.id,
                        kind,
                    )

                admins = await user_repository.list_admins()
                admin_message = NotificationService.build_admin_reminder_message(
                    engineer.username if engineer is not None else "",
                    obj.name,
                    inspection.planned_date,
                    kind,
                )
                for admin in admins:
                    if engineer is not None and admin.telegram_id == engineer.telegram_id:
                        continue
                    await bot.send_message(admin.telegram_id, admin_message)
                    logger.info(
                        "Sent reminder to admin {} for inspection {} ({})",
                        admin.telegram_id,
                        inspection.id,
                        kind,
                    )
            except Exception as exc:
                logger.warning("Failed to send reminder for inspection {}: {}", inspection.id, exc)
