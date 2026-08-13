from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.database.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = UserRepository(session)

    async def register_pending_user(self, telegram_id: int, full_name: str, username: str | None, phone: str) -> User:
        existing_user = await self.repository.get_by_telegram_id(telegram_id)
        if existing_user is not None:
            return existing_user

        user = User(
            telegram_id=telegram_id,
            full_name=full_name,
            username=username,
            phone=phone,
            role="pending",
            is_active=False,
        )
        return await self.repository.create(user)

    async def get_user_by_telegram_id(self, telegram_id: int) -> User | None:
        return await self.repository.get_by_telegram_id(telegram_id)

    async def get_user_by_id(self, user_id: int) -> User | None:
        return await self.repository.get_by_id(user_id)

    async def approve_user(self, telegram_id: int, role: str) -> User | None:
        user = await self.repository.get_by_telegram_id(telegram_id)
        if user is None:
            return None
        return await self.repository.update_role(user, role)

    async def reject_user(self, telegram_id: int) -> User | None:
        user = await self.repository.get_by_telegram_id(telegram_id)
        if user is None:
            return None
        user.is_active = False
        await self.session.commit()
        await self.session.refresh(user)
        return user
