import unittest

from app.utils.admin import is_admin_user_for_role


class AdminAccessTests(unittest.TestCase):
    def test_env_admin_id_is_allowed(self) -> None:
        self.assertTrue(is_admin_user_for_role(role=None, telegram_id=100, admin_id=100))

    def test_db_admin_role_is_allowed(self) -> None:
        self.assertTrue(is_admin_user_for_role(role="admin", telegram_id=200, admin_id=0))

    def test_non_admin_role_is_not_allowed(self) -> None:
        self.assertFalse(is_admin_user_for_role(role="engineer", telegram_id=200, admin_id=0))


if __name__ == "__main__":
    unittest.main()
