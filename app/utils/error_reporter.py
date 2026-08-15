"""Centralized error reporting for the ProGaz bot.

This module is responsible for:

- generating unique Error IDs (ERR-YYYYMMDD-XXXXXX);
- building a technical report for the developer;
- writing every error to Loguru;
- sending the report to the developer chat via Telegram;
- protecting the developer from repeated reports of the same error (cooldown);
- redacting secrets before anything leaves the machine.

It must never raise: every external call is wrapped and failures are only
logged, so a broken reporter can never break the bot.
"""

from __future__ import annotations

import asyncio
import os
import re
import secrets
import time
import traceback
from datetime import datetime

from loguru import logger

from app.config import settings

_TELEGRAM_MESSAGE_LIMIT = 4000
_SECRET_ENV_HINTS = ("TOKEN", "PASSWORD", "SECRET", "KEY")


class ErrorReporter:
    def __init__(self) -> None:
        # fingerprint -> last monotonic time a report was sent to Telegram
        self._last_sent: dict[str, float] = {}

    # ------------------------------------------------------------------
    # Bot access (lazy import to avoid circular imports with app.loader)
    # ------------------------------------------------------------------
    @staticmethod
    def _get_bot():
        from app.loader import bot

        return bot

    # ------------------------------------------------------------------
    # Error ID
    # ------------------------------------------------------------------
    @staticmethod
    def _generate_error_id(now: datetime | None = None) -> str:
        current = now or datetime.now()
        suffix = secrets.token_hex(3).upper()
        return f"ERR-{current:%Y%m%d}-{suffix}"

    # ------------------------------------------------------------------
    # Fingerprint / cooldown
    # ------------------------------------------------------------------
    @staticmethod
    def _build_fingerprint(exception: BaseException, context: str) -> str:
        normalized_message = re.sub(r"[0-9]+", "N", str(exception) or "")
        normalized_message = re.sub(r"\s+", " ", normalized_message).strip()
        return f"{type(exception).__name__}:{context}:{normalized_message}"

    def _should_send_to_developer(self, fingerprint: str) -> bool:
        now = time.monotonic()
        last = self._last_sent.get(fingerprint)
        if last is not None and (now - last) < settings.ERROR_COOLDOWN_SECONDS:
            return False
        self._last_sent[fingerprint] = now
        return True

    # ------------------------------------------------------------------
    # Secret redaction
    # ------------------------------------------------------------------
    @staticmethod
    def _collect_secrets() -> list[str]:
        secrets_list: list[str] = []
        if settings.BOT_TOKEN:
            secrets_list.append(settings.BOT_TOKEN)
        for name, value in os.environ.items():
            if value and any(hint in name.upper() for hint in _SECRET_ENV_HINTS):
                secrets_list.append(value)
        return [item for item in secrets_list if len(item) >= 4]

    @classmethod
    def _redact(cls, text: str) -> str:
        redacted = text
        for secret in cls._collect_secrets():
            redacted = redacted.replace(secret, "[REDACTED]")
        return redacted

    # ------------------------------------------------------------------
    # Report building
    # ------------------------------------------------------------------
    def _build_report(
        self,
        error_id: str,
        exception: BaseException,
        context: str,
        user: dict | None,
    ) -> str:
        traceback_text = "".join(
            traceback.format_exception(type(exception), exception, exception.__traceback__)
        )

        lines = [
            "🚨 PROGAZ BOT ERROR",
            "",
            "Error ID:",
            error_id,
            "",
            "Time:",
            datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            "",
            "Environment:",
            settings.ENVIRONMENT,
            "",
            "User:",
            self._format_user_field(user, "username"),
            "",
            "Full name:",
            self._format_user_field(user, "full_name"),
            "",
            "Telegram ID:",
            self._format_user_field(user, "telegram_id"),
            "",
            "Role:",
            self._format_user_field(user, "role"),
            "",
            "Context:",
            context or "N/A",
            "",
            "Exception:",
            f"{type(exception).__module__}.{type(exception).__name__}",
            "",
            "Message:",
            str(exception) or "N/A",
            "",
            "Traceback:",
            traceback_text.strip(),
        ]
        return self._redact("\n".join(lines))

    @staticmethod
    def _format_user_field(user: dict | None, key: str) -> str:
        if not user:
            return "N/A"
        value = user.get(key)
        if value is None or value == "":
            return "N/A"
        if key == "username":
            return f"@{value}"
        return str(value)

    @staticmethod
    def _split_for_telegram(text: str, limit: int = _TELEGRAM_MESSAGE_LIMIT) -> list[str]:
        if len(text) <= limit:
            return [text]

        chunks: list[str] = []
        current = ""
        for line in text.split("\n"):
            if len(current) + len(line) + 1 > limit:
                if current:
                    chunks.append(current)
                current = line
            else:
                current = f"{current}\n{line}" if current else line
        if current:
            chunks.append(current)
        return chunks

    # ------------------------------------------------------------------
    # Telegram delivery (never raises)
    # ------------------------------------------------------------------
    async def _send_report_to_developer(self, text: str) -> bool:
        if not settings.ERROR_REPORTING_ENABLED or not settings.DEVELOPER_CHAT_ID:
            return False

        try:
            bot = self._get_bot()
            for chunk in self._split_for_telegram(text):
                await bot.send_message(settings.DEVELOPER_CHAT_ID, chunk)
            return True
        except Exception as exc:
            # Never raise from the reporter itself: this prevents error loops.
            logger.error("Failed to send error report to developer: {}", exc)
            return False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def report(
        self,
        exception: BaseException,
        context: str = "unknown",
        user: dict | None = None,
    ) -> str:
        """Report an exception. Returns the generated Error ID."""
        error_id = self._generate_error_id()
        report_text = self._build_report(error_id, exception, context, user)

        # Every error is always written to Loguru.
        logger.opt(exception=exception).error(
            "Error {} | context={} | user={} | {}",
            error_id,
            context,
            user.get("telegram_id") if user else "N/A",
            exception,
        )

        if settings.DEVELOPER_CHAT_ID and settings.ERROR_REPORTING_ENABLED:
            fingerprint = self._build_fingerprint(exception, context)
            if self._should_send_to_developer(fingerprint):
                sent = await self._send_report_to_developer(report_text)
                if sent:
                    logger.info(
                        "Error report {} sent to developer (context={})", error_id, context
                    )
                else:
                    logger.warning("Error report {} was not sent", error_id)
            else:
                logger.info(
                    "Error {} suppressed by cooldown (context={})", error_id, context
                )

        return error_id

    @staticmethod
    def build_safe_user_message(error_id: str) -> str:
        return (
            "⚠️ Произошла неизвестная ошибка.\n\n"
            "Попробуйте повторить действие позже.\n\n"
            "Если ошибка повторяется — обратитесь к разработчику.\n\n"
            f"Код ошибки: {error_id}"
        )


error_reporter = ErrorReporter()
