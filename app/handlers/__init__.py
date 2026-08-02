from app.handlers.admin.inspections import register_inspection_handlers
from app.handlers.admin.menu import register_admin_menu_handlers
from app.handlers.admin.objects import register_object_handlers
from app.handlers.admin.registration_review import register_admin_review_handlers
from app.handlers.start import register_start_handler


def register_handlers(dp) -> None:
    register_start_handler(dp)
    register_admin_review_handlers(dp)
    register_admin_menu_handlers(dp)
    register_object_handlers(dp)
    register_inspection_handlers(dp)
