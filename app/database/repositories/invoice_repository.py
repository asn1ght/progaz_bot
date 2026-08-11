from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Invoice


class InvoiceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, invoice: Invoice) -> Invoice:
        self.session.add(invoice)
        await self.session.commit()
        await self.session.refresh(invoice)
        return invoice

    async def list_all(self) -> list[Invoice]:
        result = await self.session.execute(
            select(Invoice).order_by(Invoice.issue_date.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, invoice_id: int) -> Invoice | None:
        result = await self.session.execute(
            select(Invoice).where(Invoice.id == invoice_id)
        )
        return result.scalar_one_or_none()

    async def list_by_status(self, status: str) -> list[Invoice]:
        result = await self.session.execute(
            select(Invoice)
            .where(Invoice.status == status)
            .order_by(Invoice.issue_date.desc())
        )
        return list(result.scalars().all())

    async def update(self, invoice: Invoice) -> Invoice:
        await self.session.commit()
        await self.session.refresh(invoice)
        return invoice
