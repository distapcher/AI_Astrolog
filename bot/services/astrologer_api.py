from __future__ import annotations

from datetime import datetime, timezone
import logging
from pathlib import Path
import tempfile
from typing import Any

import httpx

from bot.config import Settings
from bot.services.chart_constants import PDF_ACTIVE_ASPECTS, PDF_ACTIVE_POINTS
from bot.services.kerykeion_chart import NatalInput, _api_chart_payload, build_subject_payload

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

    async def _post(self, path: str, payload: dict, *, timeout: float = 120.0) -> dict:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{self._base}{path}",
                json=payload,
                headers=self._headers,
            )
        if response.status_code >= 400:
            logger.error("Astrologer API %s -> %s: %s", path, response.status_code, response.text[:500])
            raise AstrologerApiError(f"API {path}: ошибка {response.status_code}")
        data = response.json()
        if data.get("status") == "ERROR":
            raise AstrologerApiError(data.get("message", "Ошибка Astrologer API"))
        return data

    async def fetch_birth_chart_svg(self, natal: NatalInput) -> tuple[str, dict]:
        payload = {
            **_api_chart_payload(natal),
            "theme": self._settings.chart_theme,
            "language": self._settings.chart_language,
        }
        data = await self._post("/chart/birth-chart", payload)
        svg = data.get("chart") or data.get("chart_wheel") or ""
        if not svg:
            raise AstrologerApiError("API не вернул SVG карты.")
        return svg, data

    async def fetch_birth_chart_data(self, natal: NatalInput) -> dict:
        data = await self._post("/chart-data/birth-chart", _api_chart_payload(natal))
        return data.get("chart_data") or data

    async def fetch_moon_phase(self, natal: NatalInput) -> dict:
        loc = natal.location
        payload = {
            "year": natal.year,
            "month": natal.month,
            "day": natal.day,
            "hour": natal.hour,
            "minute": natal.minute,
            "second": 0,
            "latitude": loc.latitude,
            "longitude": loc.longitude,
            "timezone": loc.timezone,
            "using_default_location": False,
            "location_precision": 4,
        }
        return await self._post("/moon-phase", payload, timeout=60.0)

    async def fetch_current_transits(self, natal: NatalInput) -> list[dict[str, Any]]:
        """Транзиты на текущий момент к натальной карте."""
        now = datetime.now(timezone.utc)
        loc = natal.location
        payload = {
            "first_subject": build_subject_payload(natal),
            "transit_subject": {
                "name": "Transit",
                "year": now.year,
                "month": now.month,
                "day": now.day,
                "hour": now.hour,
                "minute": now.minute,
                "city": loc.city,
                "nation": loc.nation,
                "timezone": "UTC",
                "longitude": 0.0,
                "latitude": 51.48,
            },
            "include_house_comparison": False,
            "active_points": list(PDF_ACTIVE_POINTS),
            "active_aspects": list(PDF_ACTIVE_ASPECTS),
            "distribution_method": "weighted",
        }
        try:
            data = await self._post("/chart-data/transit", payload, timeout=90.0)
        except AstrologerApiError:
            payload["transit_subject"] = {
                "name": "Transit",
                "year": now.year,
                "month": now.month,
                "day": now.day,
                "hour": now.hour,
                "minute": now.minute,
                "city": loc.city,
                "nation": loc.nation,
                "timezone": loc.timezone,
                "longitude": loc.longitude,
                "latitude": loc.latitude,
            }
            data = await self._post("/chart-data/transit", payload, timeout=90.0)

        chart_data = data.get("chart_data") or data
        aspects = chart_data.get("aspects") or []
        return sorted(
            [a for a in aspects if isinstance(a, dict)],
            key=lambda x: float(x.get("orbit") or 99),
        )

    async def fetch_complete_natal_package(
        self, natal: NatalInput, *, include_svg: bool = False
    ) -> dict[str, Any]:
        """chart_data + moon phase + transits; SVG только если include_svg=True."""
        result: dict[str, Any] = {
            "svg": "",
            "chart_data": None,
            "moon_phase": None,
            "transit_aspects": None,
        }
        if include_svg:
            try:
                svg, raw = await self.fetch_birth_chart_svg(natal)
                result["svg"] = svg
                result["chart_data"] = raw.get("chart_data")
            except AstrologerApiError as exc:
                logger.warning("birth-chart SVG: %s", exc)

        if not result["chart_data"]:
            try:
                result["chart_data"] = await self.fetch_birth_chart_data(natal)
            except AstrologerApiError as exc:
                logger.warning("birth-chart data: %s", exc)

        try:
            result["moon_phase"] = await self.fetch_moon_phase(natal)
        except AstrologerApiError as exc:
            logger.warning("moon-phase: %s", exc)

        try:
            result["transit_aspects"] = await self.fetch_current_transits(natal)
        except AstrologerApiError as exc:
            logger.warning("transit: %s", exc)

        return result

    async def save_chart_svg_fallback(self, natal: NatalInput, chart_data) -> Path | None:
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
