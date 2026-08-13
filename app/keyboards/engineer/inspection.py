from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_inspection_action_keyboard(inspection_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("✅ Отметить выполненной", callback_data=f"complete_inspection:{inspection_id}"))
    return keyboard


def get_fail_inspection_keyboard(inspections: list) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=1)
    for insp in inspections:
        keyboard.add(
            InlineKeyboardButton(
                f"#{insp.id} | {insp.planned_date} | объект #{insp.object_id}",
                callback_data=f"fail_inspection:{insp.id}",
            )
        )
    return keyboard
