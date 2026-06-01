from __future__ import annotations

import logging
from pathlib import Path
import tempfile

import httpx

from bot.config import Settings
from bot.services.kerykeion_chart import NatalInput, build_subject_payload

logger = logging.getLogger(__name__)

BASE_PATH = "/api/v5"


class AstrologerApiError(Exception):
    pass


class AstrologerClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._headers = {
            "Content-Type": "application/json",
            "X-RapidAPI-Key": settings.rapidapi_key,
            "X-RapidAPI-Host": settings.rapidapi_host,
        }
        self._base = f"https://{settings.rapidapi_host}{BASE_PATH}"

    async def fetch_birth_chart_svg(self, natal: NatalInput) -> tuple[str, dict]:
        payload = {
            "subject": build_subject_payload(natal),
            "theme": self._settings.chart_theme,
            "language": self._settings.chart_language,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self._base}/chart/birth-chart",
                json=payload,
                headers=self._headers,
            )

        if response.status_code >= 400:
            logger.error("Astrologer API error %s: %s", response.status_code, response.text[:500])
            raise AstrologerApiError(
                f"API вернул ошибку {response.status_code}. Попробуйте позже."
            )

        data = response.json()
        if data.get("status") == "ERROR":
            raise AstrologerApiError(data.get("message", "Ошибка Astrologer API"))

        svg = data.get("chart") or data.get("chart_wheel") or ""
        if not svg:
            raise AstrologerApiError("API не вернул SVG карты.")

        return svg, data

    async def save_chart_png_fallback(self, natal: NatalInput, chart_data) -> Path | None:
        """Локальный SVG, если RapidAPI недоступен."""
        from bot.services.kerykeion_chart import render_local_svg

        try:
            slug = natal.name.replace(" ", "_")[:32] or "natal"
            return render_local_svg(chart_data, filename=slug)
        except Exception:
            logger.exception("Local SVG render failed")
            return None


def svg_to_temp_file(svg_content: str, suffix: str = ".svg") -> Path:
    path = Path(tempfile.mkdtemp(prefix="ai-astrolog-chart-")) / f"chart{suffix}"
    path.write_text(svg_content, encoding="utf-8")
    return path
