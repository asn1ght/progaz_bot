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
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    APP_NAME: str = "ProGaz Bot"
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_ID: int = int(os.getenv("ADMIN_ID", 0))
    DB_NAME: str = os.getenv("DB_NAME") or "progaz.db"
    DB_PATH: str = str((DATA_DIR / DB_NAME).resolve())


settings = Settings()
logger.info("Application configuration loaded")
