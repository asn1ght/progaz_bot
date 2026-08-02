from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Object


class ObjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, obj: Object) -> Object:
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def list_active(self) -> list[Object]:
        result = await self.session.execute(
            select(Object)
            .where(Object.is_active.is_(True))
            .order_by(Object.id)
        )
        return list(result.scalars().all())

    async def get_by_id(self, object_id: int) -> Object | None:
        result = await self.session.execute(
            select(Object).where(Object.id == object_id, Object.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def update(self, obj: Object) -> Object:
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def delete(self, obj: Object) -> Object:
        obj.is_active = False
        await self.session.commit()
        await self.session.refresh(obj)
        return obj
