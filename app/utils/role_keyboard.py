from __future__ import annotations

from typing import Any

from app.keyboards.admin.menu import get_admin_reply_keyboard
from app.keyboards.engineer.menu import get_engineer_reply_keyboard


def get_role_keyboard(role: str | None) -> Any | None:
    if role == "admin":
        return get_admin_reply_keyboard()
    if role == "engineer":
        return get_engineer_reply_keyboard()
    return None
