import unittest

from app.utils.engineer import matches_engineer_assignment


class EngineerAssignmentTests(unittest.TestCase):
    def test_matches_by_db_user_id(self) -> None:
        self.assertTrue(matches_engineer_assignment(current_user_id=4, assigned_engineer_id=4))

    def test_does_not_match_telegram_id(self) -> None:
        self.assertFalse(matches_engineer_assignment(current_user_id=4, assigned_engineer_id=123456789))


if __name__ == "__main__":
    unittest.main()
