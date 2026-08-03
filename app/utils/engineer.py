from __future__ import annotations


def matches_engineer_assignment(current_user_id: int | None, assigned_engineer_id: int | None) -> bool:
    if current_user_id is None or assigned_engineer_id is None:
        return False
    return current_user_id == assigned_engineer_id
