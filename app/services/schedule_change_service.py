from __future__ import annotations

import calendar
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Object, ScheduleChange
from app.database.repositories.inspection_repository import InspectionRepository
from app.database.repositories.object_repository import ObjectRepository


class ScheduleChangeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.object_repository = ObjectRepository(session)

    async def create_temporary_change(self, object_id: int, new_day: int, current_date: date | None = None) -> ScheduleChange | None:
        obj = await self.object_repository.get_by_id(object_id)
        if obj is None:
            return None

        old_date = current_date or date.today()
        last_day = calendar.monthrange(old_date.year, old_date.month)[1]
        safe_day = min(new_day, last_day)
        new_date = date(old_date.year, old_date.month, safe_day)
        inspection_repository = InspectionRepository(self.session)
        planned = await inspection_repository.get_planned_for_object_in_month(object_id, old_date.year, old_date.month)
        if planned is not None:
            planned.planned_date = new_date
            await inspection_repository.update(planned)
        else:
            obj.next_inspection_date = new_date
            await self.session.commit()
            await self.session.refresh(obj)

        change = ScheduleChange(object_id=object_id, old_date=old_date, new_date=new_date)
        self.session.add(change)
        await self.session.commit()
        await self.session.refresh(change)
        return change

    async def create_permanent_change(self, object_id: int, new_day: int) -> ScheduleChange | None:
        obj = await self.object_repository.get_by_id(object_id)
        if obj is None:
            return None

        obj.monthly_day = new_day
        await self.session.commit()
        await self.session.refresh(obj)

        inspection_repository = InspectionRepository(self.session)
        planned = await inspection_repository.get_planned_for_object(object_id)
        today = date.today()
        last_day = calendar.monthrange(today.year, today.month)[1]
        safe_day = min(new_day, last_day)
        new_date = date(today.year, today.month, safe_day)
        if planned is not None:
            planned.planned_date = new_date
            await inspection_repository.update(planned)
        elif today.day <= safe_day:
            obj.next_inspection_date = new_date
            await self.session.commit()
            await self.session.refresh(obj)

        change = ScheduleChange(object_id=object_id, old_date=today, new_date=new_date)
        self.session.add(change)
        await self.session.commit()
        await self.session.refresh(change)
        return change
