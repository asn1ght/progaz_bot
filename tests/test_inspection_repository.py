import unittest

from app.database.models import Inspection
from app.database.repositories.inspection_repository import InspectionRepository


class InspectionRepositoryTests(unittest.TestCase):
    def test_update_accepts_persistent_instance(self) -> None:
        class DummySession:
            def add(self, inspection):
                return None

            async def commit(self):
                return None

            async def refresh(self, inspection):
                return None

        repo = InspectionRepository(DummySession())
        inspection = Inspection(
            object_id=1,
            engineer_id=1,
            planned_date="2026-01-01",
            status="scheduled",
            comment=None,
        )

        async def run() -> None:
            await repo.update(inspection)

        import asyncio
        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
