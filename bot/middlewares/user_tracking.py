from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, User

from bot.config import Settings
from bot.services.usage_store import schedule_upsert_telegram_user


def _user_from_event(event: TelegramObject) -> User | None:
    if isinstance(event, Message):
        return event.from_user
    if isinstance(event, CallbackQuery):
        return event.from_user
    return None


class UserTrackingMiddleware(BaseMiddleware):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Сначала отвечаем пользователю, аналитику пишем в фоне (не блокируем event loop).
        try:
            return await handler(event, data)
        finally:
            user = _user_from_event(event)
            if user:
                schedule_upsert_telegram_user(
                    user.id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    db_path=self._settings.analytics_db_path,
                )
