from __future__ import annotations

import calendar
from datetime import date, timedelta

from app.database.models import Inspection, Object, ScheduleChange


class InspectionService:
    @staticmethod
    def calculate_next_date(monthly_day: int, base_date: date | None = None) -> date:
        today = base_date or date.today()
        last_day = calendar.monthrange(today.year, today.month)[1]
        day = min(monthly_day, last_day)
        candidate = today.replace(day=day)
        if candidate < today:
            if today.month == 12:
                candidate = candidate.replace(year=today.year + 1, month=1, day=min(monthly_day, calendar.monthrange(today.year + 1, 1)[1]))
            else:
                next_month = today.month + 1
                next_year = today.year
                if next_month > 12:
                    next_month = 1
                    next_year += 1
                candidate = candidate.replace(year=next_year, month=next_month, day=min(monthly_day, calendar.monthrange(next_year, next_month)[1]))
        return InspectionService._move_weekend_to_monday(candidate)

    @staticmethod
    def get_effective_schedule_day(object_: Object, base_date: date | None = None) -> int:
        today = base_date or date.today()
        relevant_changes = [
            change
            for change in getattr(object_, "schedule_changes", [])
            if change.new_date.year == today.year and change.new_date.month == today.month
        ]
        if relevant_changes:
            return relevant_changes[-1].new_date.day
        return object_.monthly_day

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
