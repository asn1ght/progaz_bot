from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.database.models import Invoice, Object


class InvoiceService:
    @staticmethod
    def should_create_invoice_for_date(current_date: date, monthly_day: int) -> bool:
        return current_date.day == monthly_day

    @staticmethod
    def build_invoice(object_: Object, issue_date: date | None = None) -> Invoice:
        invoice_date = issue_date or date.today()
        return Invoice(
            object_id=object_.id,
            amount=object_.invoice_amount,
            issue_date=invoice_date,
            paid_date=None,
            status="waiting",
            comment=object_.comment,
        )
