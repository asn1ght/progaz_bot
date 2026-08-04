from __future__ import annotations

import calendar
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Object, ScheduleChange
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

        change = ScheduleChange(object_id=object_id, old_date=date.today(), new_date=date.today().replace(day=new_day))
        self.session.add(change)
        await self.session.commit()
        await self.session.refresh(change)
        return change
