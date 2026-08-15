from __future__ import annotations

import asyncio

from apscheduler.events import EVENT_JOB_ERROR, JobExecutionEvent
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from app.scheduler.jobs import run_daily_checks, run_evening_checks, run_morning_reminders


def _scheduler_error_listener(event: JobExecutionEvent) -> None:
    """Central APScheduler listener: every failed job is reported exactly once."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.error("Scheduler job error, but no running event loop to report: {}", event.exception)
        return

    loop.create_task(_report_scheduler_error(event))


async def _report_scheduler_error(event: JobExecutionEvent) -> None:
    from app.utils.error_reporter import error_reporter

    context = f"scheduler.{event.job_id or 'unknown'}"
    await error_reporter.report(exception=event.exception, context=context)


def setup_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_daily_checks, "cron", hour=8, minute=0)
    scheduler.add_job(run_morning_reminders, "cron", hour=10, minute=0)
    scheduler.add_job(run_evening_checks, "cron", hour=18, minute=0)
    scheduler.add_listener(_scheduler_error_listener, EVENT_JOB_ERROR)
    scheduler.start()
    logger.info("Scheduler started")
    return scheduler
