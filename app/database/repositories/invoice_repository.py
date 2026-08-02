from __future__ import annotations

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
