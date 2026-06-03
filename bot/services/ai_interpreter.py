from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from bot.config import Settings
from bot.services.personality_format import format_personality_text

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LlmUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass(frozen=True)
class PersonalityAnalysisResult:
    text: str
    usage: LlmUsage


class AiInterpreter:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._enabled = bool(settings.openai_api_key)
        self._system_prompt: str | None = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _load_system_prompt(self) -> str:
        if self._system_prompt is not None:
            return self._system_prompt
        path = self._settings.personality_prompt_path
        if path.exists():
            self._system_prompt = path.read_text(encoding="utf-8")
            return self._system_prompt
        logger.warning("Personality prompt not found: %s", path)
        self._system_prompt = ""
        return self._system_prompt

    @staticmethod
    def _parse_usage(data: dict) -> LlmUsage:
        usage = data.get("usage") or {}
        prompt = int(usage.get("prompt_tokens") or 0)
        completion = int(usage.get("completion_tokens") or 0)
        total = int(usage.get("total_tokens") or 0)
        if total <= 0:
            total = prompt + completion
        return LlmUsage(
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=total,
        )

    async def interpret_personality(self, name: str, chart_text: str) -> PersonalityAnalysisResult:
        """Расшифровка предназначения и профессии по промпту astrolog_prof_ru."""
        if not self._enabled:
            raise RuntimeError("ИИ не настроен (нет OPENAI_API_KEY)")

        system_prompt = self._load_system_prompt()
        if not system_prompt:
            raise RuntimeError("Файл системного промпта не найден.")

        user_content = (
            f"Имя: {name}\n\n"
            f"Полные данные натальной карты для анализа:\n\n{chart_text}\n\n"
            "Проведи анализ строго по структуре из системного промпта (все 10 разделов). "
            "Сначала — персональное вступление на «ты» (2–4 абзаца), последняя фраза вступления: "
            "«Итак, приступим к разбору твоей «Формулы успеха».» "
            "Затем разделы «Раздел 1: …» … «Раздел 10: …». "
            "Не используй символы * и # и markdown."
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
        text = format_personality_text(choices[0]["message"]["content"].strip())
        return PersonalityAnalysisResult(text=text, usage=self._parse_usage(data))
