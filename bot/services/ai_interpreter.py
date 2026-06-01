from __future__ import annotations

import logging

import httpx

from bot.config import Settings, PROMPT_PATH

logger = logging.getLogger(__name__)


class AiInterpreter:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._enabled = bool(settings.openai_api_key)

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def interpret(self, name: str, chart_text: str) -> str:
        if not self._enabled:
            raise RuntimeError("ИИ-расшифровка не настроена (нет OPENAI_API_KEY)")

        system_prompt = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else ""
        user_content = (
            f"Имя: {name}\n\n"
            f"Данные натальной карты (рассчитаны Kerykeion):\n\n{chart_text}\n\n"
            "Проведи полный анализ по структуре из системного промпта."
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
            "max_tokens": 8000,
            "temperature": 0.7,
        }

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(url, json=body, headers=headers)

        if response.status_code >= 400:
            logger.error("LLM error %s: %s", response.status_code, response.text[:300])
            raise RuntimeError("Не удалось получить расшифровку от ИИ.")

        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("Пустой ответ от ИИ.")
        return choices[0]["message"]["content"].strip()
