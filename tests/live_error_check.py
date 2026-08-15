"""Manual live check of the error reporting pipeline.

Sends real reports to the developer chat configured in .env.
Run: python tests/live_error_check.py
"""

import asyncio

from app.config import settings
from app.loader import bot
from app.utils.error_reporter import error_reporter


async def main() -> None:
    print("=== 1. Прямой вызов reporter (должно уйти сообщение разработчику) ===")
    err1 = await error_reporter.report(ValueError("live check 1"), context="live.test.first")
    print("Error ID 1:", err1)

    print("=== 2. Та же ошибка ещё раз (cooldown, НЕ должно уйти) ===")
    err2 = await error_reporter.report(ValueError("live check 1"), context="live.test.first")
    print("Error ID 2:", err2)

    print("=== 3. Другой context (должно уйти снова) ===")
    err3 = await error_reporter.report(ValueError("live check 2"), context="live.test.second")
    print("Error ID 3:", err3)

    print("=== 4. Проверка redact: токен не должен попасть в отчёт ===")
    report_text = error_reporter._build_report("ERR-TEST", ValueError("token check"), "live.test.secret", None)
    print("BOT_TOKEN утёк в отчёт:", settings.BOT_TOKEN in report_text)

    print("=== 5. Имитация ошибки APScheduler job (listener-путь) ===")
    event = type("JobErrorEvent", (), {"exception": RuntimeError("scheduler live failure"), "job_id": "run_evening_checks"})()
    from app.scheduler.setup import _report_scheduler_error
    await _report_scheduler_error(event)
    print("Scheduler report sent")

    print("=== 6. Глобальный aiogram handler (фейковый update без message) ===")
    from app.handlers.errors import handle_unhandled_error
    fake_update = type("FakeUpdate", (), {"message": None, "callback_query": None})()
    handled = await handle_unhandled_error(fake_update, RuntimeError("handler live failure"))
    print("Handler result (должно быть True):", handled)

    session = await bot.get_session()
    await session.close()
    print("=== DONE ===")


if __name__ == "__main__":
    asyncio.run(main())
