import logging

from aiogram import executor

from app.database.session import init_db
from app.handlers import register_handlers
from app.loader import dp
from loguru import logger


async def on_startup(_dispatcher) -> None:
    await init_db()
    logger.info("Bot startup completed")


register_handlers(dp)


def main() -> None:
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)



if __name__ == "__main__":
    main()
