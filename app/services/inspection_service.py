from __future__ import annotations

from datetime import date, timedelta

from app.database.models import Inspection, Object


class InspectionService:
    @staticmethod
    def calculate_next_date(monthly_day: int, base_date: date | None = None) -> date:
        today = base_date or date.today()
        candidate = today.replace(day=monthly_day)
        if candidate < today:
            if today.month == 12:
                candidate = candidate.replace(year=today.year + 1, month=1)
            else:
                candidate = candidate.replace(month=today.month + 1)
        return InspectionService._move_weekend_to_monday(candidate)

    @staticmethod
    def _move_weekend_to_monday(day: date) -> date:
        if day.weekday() == 5:
            return day + timedelta(days=2)
        if day.weekday() == 6:
            return day + timedelta(days=1)
        return day

    @staticmethod
    def build_inspection(object_: Object, engineer_id: int, planned_date: date | None = None) -> Inspection:
        next_date = planned_date or object_.next_inspection_date or InspectionService.calculate_next_date(
            object_.monthly_day
        )
        return Inspection(
            object_id=object_.id,
            engineer_id=engineer_id,
            planned_date=next_date,
            status="planned",
            comment=object_.comment,
        )
