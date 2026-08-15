"""Unit tests for the centralized error handling system."""

from __future__ import annotations

import re
import unittest
from datetime import datetime
from unittest.mock import AsyncMock, patch

from app.utils.error_reporter import ErrorReporter, error_reporter

ERROR_ID_PATTERN = re.compile(r"^ERR-\d{8}-[0-9A-F]{6}$")


class ErrorIdTests(unittest.TestCase):
    def test_error_id_format(self) -> None:
        error_id = ErrorReporter._generate_error_id(datetime(2026, 8, 13, 12, 0, 0))
        self.assertRegex(error_id, ERROR_ID_PATTERN)

    def test_error_id_uses_current_date(self) -> None:
        error_id = ErrorReporter._generate_error_id(datetime(2026, 8, 13, 12, 0, 0))
        self.assertTrue(error_id.startswith("ERR-20260813-"), error_id)

    def test_error_ids_are_unique(self) -> None:
        ids = {ErrorReporter._generate_error_id() for _ in range(200)}
        self.assertEqual(len(ids), 200)


class FingerprintTests(unittest.TestCase):
    def test_same_error_has_same_fingerprint(self) -> None:
        first = ErrorReporter._build_fingerprint(ValueError("Object 42 not found"), "admin.objects")
        second = ErrorReporter._build_fingerprint(ValueError("Object 42 not found"), "admin.objects")
        self.assertEqual(first, second)

    def test_numbers_are_normalized(self) -> None:
        first = ErrorReporter._build_fingerprint(ValueError("invoice 7 failed"), "db")
        second = ErrorReporter._build_fingerprint(ValueError("invoice 99 failed"), "db")
        self.assertEqual(first, second)

    def test_different_context_has_different_fingerprint(self) -> None:
        first = ErrorReporter._build_fingerprint(ValueError("boom"), "admin.objects")
        second = ErrorReporter._build_fingerprint(ValueError("boom"), "scheduler.job")
        self.assertNotEqual(first, second)


class CooldownTests(unittest.TestCase):
    def test_second_report_within_cooldown_is_suppressed(self) -> None:
        reporter = ErrorReporter()
        fingerprint = "ValueError:test:boom"
        self.assertTrue(reporter._should_send_to_developer(fingerprint))
        self.assertFalse(reporter._should_send_to_developer(fingerprint))


class RedactionTests(unittest.TestCase):
    def test_secrets_are_redacted(self) -> None:
        text = "Failed with token 123456789:AAHsuperSecretToken and more"
        with patch.object(
            ErrorReporter,
            "_collect_secrets",
            return_value=["123456789:AAHsuperSecretToken"],
        ):
            redacted = ErrorReporter._redact(text)
        self.assertNotIn("superSecretToken", redacted)
        self.assertIn("[REDACTED]", redacted)


class ReportTests(unittest.IsolatedAsyncioTestCase):
    async def test_report_returns_error_id_without_developer(self) -> None:
        reporter = ErrorReporter()
        send_mock = AsyncMock(return_value=False)
        with patch.object(reporter, "_send_report_to_developer", new=send_mock):
            error_id = await reporter.report(
                ValueError("test failure"),
                context="test.report",
                user={"telegram_id": 123, "username": "tester", "full_name": "Test User", "role": "admin"},
            )
        self.assertRegex(error_id, ERROR_ID_PATTERN)

    async def test_report_message_is_safe_for_user(self) -> None:
        error_id = "ERR-20260813-ABCDEF"
        message = ErrorReporter.build_safe_user_message(error_id)
        self.assertIn("Произошла неизвестная ошибка", message)
        self.assertIn(error_id, message)

    async def test_report_build_contains_required_fields(self) -> None:
        reporter = ErrorReporter()
        report = reporter._build_report(
            "ERR-20260813-ABCDEF",
            ValueError("broken"),
            "admin.objects",
            {"telegram_id": 1, "username": "u", "full_name": "Name", "role": "admin"},
        )
        for field in ("Error ID:", "ERR-20260813-ABCDEF", "Context:", "admin.objects", "Exception:", "Traceback:"):
            self.assertIn(field, report)

    async def test_unknown_fields_reported_as_na(self) -> None:
        reporter = ErrorReporter()
        report = reporter._build_report("ERR-20260813-ABCDEF", ValueError("x"), "ctx", None)
        self.assertIn("N/A", report)


class SplitTests(unittest.TestCase):
    def test_long_report_is_split(self) -> None:
        long_text = "\n".join(f"line {i}" for i in range(500))
        chunks = ErrorReporter._split_for_telegram(long_text, limit=500)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 500 for chunk in chunks))

    def test_short_report_is_not_split(self) -> None:
        chunks = ErrorReporter._split_for_telegram("short", limit=4000)
        self.assertEqual(chunks, ["short"])


if __name__ == "__main__":
    unittest.main()
