from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def list_admins(self) -> list[User]:
        result = await self.session.execute(select(User).where(User.role == "admin", User.is_active.is_(True)))
        return list(result.scalars().all())

    async def list_accountants(self) -> list[User]:
        result = await self.session.execute(select(User).where(User.role == "accountant", User.is_active.is_(True)))
        return list(result.scalars().all())

    async def list_engineers(self) -> list[User]:
        result = await self.session.execute(select(User).where(User.role == "engineer", User.is_active.is_(True)))
        return list(result.scalars().all())

    async def update_role(self, user: User, role: str) -> User:
        user.role = role
        user.is_active = True
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def list_all(self) -> list[User]:
        result = await self.session.execute(select(User).order_by(User.id))
        return list(result.scalars().all())
