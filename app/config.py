from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

logger.remove()
logger.add(sys.stderr, level="DEBUG", enqueue=True)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
load_dotenv(BASE_DIR / ".env")

logger.add(
    LOG_DIR / "app.log",
    level="INFO",
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    enqueue=True,
)


def _parse_optional_int(value: str | None) -> int | None:
    if value is None or value.strip() == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _parse_int(value: str | None, default: int) -> int:
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _parse_bool(value: str | None, default: bool = True) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    APP_NAME: str = "ProGaz Bot"
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_ID: int = int(os.getenv("ADMIN_ID", 0))
    DB_NAME: str = os.getenv("DB_NAME") or "progaz.db"
    DB_PATH: str = str((DATA_DIR / DB_NAME).resolve())

    DEVELOPER_CHAT_ID: int | None = _parse_optional_int(os.getenv("DEVELOPER_CHAT_ID"))
    ERROR_REPORTING_ENABLED: bool = _parse_bool(os.getenv("ERROR_REPORTING_ENABLED"), default=True)
    ERROR_COOLDOWN_SECONDS: int = _parse_int(os.getenv("ERROR_COOLDOWN_SECONDS"), default=300)
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")


settings = Settings()
logger.info("Application configuration loaded")
