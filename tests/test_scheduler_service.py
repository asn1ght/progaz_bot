from datetime import date
import unittest

from app.services.invoice_service import InvoiceService


class InvoiceServiceTests(unittest.TestCase):
    def test_create_invoice_on_due_day(self) -> None:
        self.assertTrue(InvoiceService.should_create_invoice_for_date(date(2026, 8, 15), 15))

    def test_skip_invoice_on_other_day(self) -> None:
        self.assertFalse(InvoiceService.should_create_invoice_for_date(date(2026, 8, 16), 15))


if __name__ == "__main__":
    unittest.main()
