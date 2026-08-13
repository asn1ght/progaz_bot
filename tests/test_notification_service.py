import unittest
from datetime import date

from app.services.notification_service import NotificationService


class NotificationServiceTests(unittest.TestCase):
    def test_build_engineer_reminder_message_for_tomorrow(self) -> None:
        message = NotificationService.build_engineer_reminder_message("Объект 2", date(2026, 10, 2), "tomorrow")
        self.assertIn("завтра", message)
        self.assertIn("Объект 2", message)

    def test_build_admin_reminder_message_for_today(self) -> None:
        message = NotificationService.build_admin_reminder_message("Иванов Иван", "Объект 2", date(2026, 10, 2), "today")
        self.assertIn("Иванов Иван", message)
        self.assertIn("сегодня", message)
        self.assertIn("Объект 2", message)


if __name__ == "__main__":
    unittest.main()
