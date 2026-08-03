from __future__ import annotations

from datetime import date

from sqlalchemy import select
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

    async def update(self, inspection: Inspection) -> Inspection:
        self.session.add(inspection)
        await self.session.commit()
        await self.session.refresh(inspection)
        return inspection
