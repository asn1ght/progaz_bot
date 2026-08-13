from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from app.scheduler.jobs import run_daily_checks, run_evening_checks, run_morning_reminders


def setup_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_daily_checks, "cron", hour=8, minute=0)
    scheduler.add_job(run_morning_reminders, "cron", hour=10, minute=0)
    scheduler.add_job(run_evening_checks, "cron", hour=18, minute=0)
    scheduler.start()
    logger.info("Scheduler started")
    return scheduler
