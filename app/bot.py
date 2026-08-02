import logging

from aiogram import executor

from app.database.session import init_db
from app.handlers import register_handlers
from app.loader import dp
from app.scheduler.setup import setup_scheduler
from loguru import logger

_scheduler = None


async def on_startup(_dispatcher) -> None:
    global _scheduler
    await init_db()
    if _scheduler is None:
        _scheduler = setup_scheduler()
    logger.info("Bot startup completed")


register_handlers(dp)


def main() -> None:
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)



if __name__ == "__main__":
    main()
