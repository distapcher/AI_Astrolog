from __future__ import annotations

from aiogram.types import Message


async def send_long_text(
    message: Message,
    text: str,
    *,
    title: str = "Анализ",
    chunk_size: int = 4000,
) -> None:
    parts = [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)] or ["(пусто)"]
    for idx, part in enumerate(parts):
        prefix = f"<b>{title} ({idx + 1}/{len(parts)})</b>\n\n" if len(parts) > 1 else ""
        await message.answer(prefix + part)
