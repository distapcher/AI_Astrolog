from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from bot.config import Settings
from bot.services.ai_interpreter import AiInterpreter
from bot.services.astrologer_api import AstrologerClient


class ServicesMiddleware(BaseMiddleware):
    def __init__(self, settings: Settings, astrologer: AstrologerClient, ai: AiInterpreter) -> None:
        self._settings = settings
        self._astrologer = astrologer
        self._ai = ai

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data["settings"] = self._settings
        data["astrologer"] = self._astrologer
        data["ai"] = self._ai
        return await handler(event, data)


__all__ = ["ServicesMiddleware"]
