from __future__ import annotations

from datetime import date, datetime, timedelta

from zoneinfo import ZoneInfo


class NotificationService:
    MOSCOW_TZ = ZoneInfo("Europe/Moscow")

    @staticmethod
    def reminder_kind(planned_date: date, today: date) -> str | None:
        if planned_date == today:
            return "today"
        if planned_date == today + timedelta(days=1):
            return "tomorrow"
        return None

    @staticmethod
    def should_send_reminder(now: datetime | None = None) -> bool:
        current_time = now or datetime.now(NotificationService.MOSCOW_TZ)
        return current_time.hour == 10 and current_time.minute == 0

    @staticmethod
    def build_engineer_reminder_message(object_name: str, planned_date: date, kind: str) -> str:
        label = "сегодня" if kind == "today" else "завтра"
        return f"Напоминание: {label} у вас запланирован выезд на объект {object_name} ({planned_date})."

    @staticmethod
    def build_admin_reminder_message(full_name: str, object_name: str, planned_date: date, kind: str) -> str:
        label = "сегодня" if kind == "today" else "завтра"
        name_text = full_name or "инженер"
        return f"Напоминание: {name_text} {label} будет выезд на объект {object_name} ({planned_date})."

    @staticmethod
    def build_accountant_invoice_message(invoice_id: int, object_name: str, amount: str, issue_date: date) -> str:
        return (
            f"📑 Новый счет #{invoice_id}: объект {object_name}, "
            f"сумма {amount} ₽, дата {issue_date}."
        )
