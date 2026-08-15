"""Global aiogram error handlers.

Catches unhandled exceptions raised inside Telegram handlers, reports them to
the developer and sends the user a safe message with an Error ID.

Never exposes tracebacks, SQL or server paths to the user.
"""

from __future__ import annotations

from aiogram import types
from aiogram.dispatcher import Dispatcher
from loguru import logger

from app.database.session import AsyncSessionFactory
from app.services.user_service import UserService
from app.utils.error_reporter import error_reporter


async def _resolve_user_role(telegram_id: int) -> str | None:
    try:
        async with AsyncSessionFactory() as session:
            service = UserService(session)
            user = await service.get_user_by_telegram_id(telegram_id)
        return user.role if user is not None else None
    except Exception as exc:
        logger.warning("Failed to resolve user role for error report: {}", exc)
        return None


def _extract_user_info(update: types.Update) -> dict | None:
    message = getattr(update, "message", None)
    if message is None:
        callback_query = getattr(update, "callback_query", None)
        message = callback_query.message if callback_query is not None else None

    if message is None or message.from_user is None:
        return None

    user = message.from_user
    return {
        "telegram_id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": None,
    }


def _determine_context(update: types.Update) -> str:
    if getattr(update, "callback_query", None) is not None:
        data = update.callback_query.data or ""
        return f"telegram.callback:{data.split(':')[0] if data else 'unknown'}"
    if getattr(update, "message", None) is not None:
        text = update.message.text or update.message.caption or ""
        return f"telegram.message:{text[:50] if text else 'no_text'}"
    return "telegram.update"


async def _safe_notify_user(update: types.Update, error_id: str) -> None:
    safe_message = error_reporter.build_safe_user_message(error_id)

    callback_query = getattr(update, "callback_query", None)
    if callback_query is not None:
        # Never leave the user waiting on a callback without an answer.
        try:
            await callback_query.answer("⚠️ Произошла ошибка. Попробуйте позже.")
        except Exception as exc:
            logger.warning("Failed to answer callback query on error: {}", exc)
        try:
            await callback_query.message.answer(safe_message)
        except Exception as exc:
            logger.warning("Failed to send error message for callback query: {}", exc)
        return

    message = getattr(update, "message", None)
    if message is not None:
        try:
            await message.answer(safe_message)
        except Exception as exc:
            logger.warning("Failed to send error message to user: {}", exc)


async def handle_unhandled_error(update: types.Update, exception: Exception) -> bool:
    user_info = _extract_user_info(update)

    if user_info is not None:
        user_info["role"] = await _resolve_user_role(user_info["telegram_id"])

    error_id = await error_reporter.report(
        exception=exception,
        context=_determine_context(update),
        user=user_info,
    )

    await _safe_notify_user(update, error_id)
    return True


def register_error_handlers(dp: Dispatcher) -> None:
    dp.register_errors_handler(handle_unhandled_error)
