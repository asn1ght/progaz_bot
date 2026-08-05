from __future__ import annotations

import calendar
from datetime import date

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Inspection


class InspectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, inspection: Inspection) -> Inspection:
        self.session.add(inspection)
        await self.session.commit()
        await self.session.refresh(inspection)
        return inspection

    async def list_by_date(self, from_date: date | None = None) -> list[Inspection]:
        stmt = select(Inspection).order_by(Inspection.planned_date)
        if from_date is not None:
            stmt = stmt.where(Inspection.planned_date >= from_date)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, inspection_id: int) -> Inspection | None:
        result = await self.session.execute(select(Inspection).where(Inspection.id == inspection_id))
        return result.scalar_one_or_none()

    async def get_planned_for_object(self, object_id: int) -> Inspection | None:
        result = await self.session.execute(
            select(Inspection)
            .where(Inspection.object_id == object_id, Inspection.status == "planned")
            .order_by(Inspection.planned_date)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_nearest_planned_for_objects(self, object_ids: list[int]) -> dict[int, Inspection | None]:
        if not object_ids:
            return {}
        result = await self.session.execute(
            select(Inspection)
            .where(
                Inspection.object_id.in_(object_ids),
                Inspection.status == "planned",
            )
            .order_by(Inspection.object_id, Inspection.planned_date)
        )
        inspections = list(result.scalars().all())

        mapping: dict[int, Inspection] = {}
        for insp in inspections:
            if insp.object_id not in mapping:
                mapping[insp.object_id] = insp
        return {oid: mapping.get(oid) for oid in object_ids}

    async def get_planned_for_object_in_month(self, object_id: int, year: int, month: int) -> Inspection | None:
        last_day = calendar.monthrange(year, month)[1]
        result = await self.session.execute(
            select(Inspection)
            .where(
                Inspection.object_id == object_id,
                Inspection.status == "planned",
                Inspection.planned_date >= date(year, month, 1),
                Inspection.planned_date <= date(year, month, last_day),
            )
            .order_by(Inspection.planned_date)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update(self, inspection: Inspection) -> Inspection:
        self.session.add(inspection)
        await self.session.commit()
        await self.session.refresh(inspection)
        return inspection
