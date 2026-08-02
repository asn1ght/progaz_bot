from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

DB_PATH = Path(settings.DB_PATH).resolve().as_posix()
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    from app.database.base import Base
    from app.database.models import User, Object, Inspection, Invoice, ScheduleChange

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
