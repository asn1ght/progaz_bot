from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Object
from app.database.repositories.object_repository import ObjectRepository


class ObjectService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = ObjectRepository(session)

    async def create_object(
        self,
        name: str,
        address: str,
        monthly_day: int,
        invoice_amount: Decimal,
        engineer_id: int | None = None,
        comment: str | None = None,
    ) -> Object:
        obj = Object(
            name=name,
            address=address,
            engineer_id=engineer_id,
            monthly_day=monthly_day,
            invoice_amount=invoice_amount,
            comment=comment,
            semiannual_service=False,
            is_active=True,
        )
        return await self.repository.create(obj)

    async def list_objects(self) -> list[Object]:
        return await self.repository.list_active()

    async def get_object_by_id(self, object_id: int) -> Object | None:
        return await self.repository.get_by_id(object_id)

    async def update_object(self, object_id: int, **kwargs) -> Object | None:
        obj = await self.repository.get_by_id(object_id)
        if obj is None:
            return None

        for key, value in kwargs.items():
            if value is not None:
                setattr(obj, key, value)

        return await self.repository.update(obj)

    async def delete_object(self, object_id: int) -> Object | None:
        obj = await self.repository.get_by_id(object_id)
        if obj is None:
            return None
        return await self.repository.delete(obj)
