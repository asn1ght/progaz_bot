from __future__ import annotations

from typing import Optional


def is_admin_user_for_role(role: Optional[str], telegram_id: int, admin_id: int) -> bool:
    """Return True when the user should be treated as an admin.

    Admin access is granted either by the legacy ENV-based admin ID or by the
    database role assigned to the user.
    """
    if admin_id and telegram_id == admin_id:
        return True

    return role == "admin"
