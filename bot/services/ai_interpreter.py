from __future__ import annotations

import logging

import httpx

from bot.config import Settings

logger = logging.getLogger(__name__)


class AiInterpreter:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._enabled = bool(settings.openai_api_key)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _load_system_prompt(self) -> str:
        path = self._settings.personality_prompt_path
        if path.exists():
            return path.read_text(encoding="utf-8")
        logger.warning("Personality prompt not found: %s", path)
        return ""

    async def interpret_personality(self, name: str, chart_text: str) -> str:
        """Расшифровка предназначения и профессии по промпту astrolog_prof_ru."""
        if not self._enabled:
            raise RuntimeError("ИИ не настроен (нет OPENAI_API_KEY)")

        system_prompt = self._load_system_prompt()
        if not system_prompt:
            raise RuntimeError("Файл системного промпта не найден.")

        user_content = (
            f"Имя: {name}\n\n"
            f"Полные данные натальной карты для анализа:\n\n{chart_text}\n\n"
            "Проведи анализ строго по структуре из системного промпта (все 10 разделов)."
        )

        url = f"{self._settings.openai_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self._settings.openai_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": self._settings.ai_max_tokens,
            "temperature": 0.7,
        }

        async with httpx.AsyncClient(timeout=600.0) as client:
            response = await client.post(url, json=body, headers=headers)

        if response.status_code >= 400:
            logger.error("LLM error %s: %s", response.status_code, response.text[:500])
            raise RuntimeError("Не удалось получить описание от ИИ.")

        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("Пустой ответ от ИИ.")
        return choices[0]["message"]["content"].strip()
