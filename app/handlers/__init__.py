from app.handlers.accountant import register_accountant_handlers_package
from app.handlers.admin.inspections import register_inspection_handlers
from app.handlers.admin.invoices import register_invoice_handlers
from app.handlers.admin.menu import register_admin_menu_handlers
from app.handlers.admin.objects import register_object_handlers
from app.handlers.admin.registration_review import register_admin_review_handlers
from app.handlers.admin.schedule import register_schedule_handlers
from app.handlers.engineer.history import register_history_handlers
from app.handlers.engineer.menu import register_engineer_handlers
from app.handlers.errors import register_error_handlers
from app.handlers.start import register_start_handler


def register_handlers(dp) -> None:
    register_start_handler(dp)
    register_admin_review_handlers(dp)
    register_admin_menu_handlers(dp)
    register_engineer_handlers(dp)
    register_history_handlers(dp)
    register_accountant_handlers_package(dp)
    register_object_handlers(dp)
    register_inspection_handlers(dp)
    register_invoice_handlers(dp)
    register_schedule_handlers(dp)
    register_error_handlers(dp)
