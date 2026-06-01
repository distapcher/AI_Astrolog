from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
from typing import Any

from bot.services.chart_constants import (
    MAJOR_ASPECT_NAMES,
    MINOR_ASPECT_NAMES,
    PLANET_POSITION_ORDER,
)
from bot.services.chart_patterns import ChartPattern, detect_chart_patterns
from bot.services.kerykeion_chart import NatalInput, _house_ru, _planet_ru, _sign_ru

ASPECT_RU = {
    "conjunction": "соединение",
    "opposition": "оппозиция",
    "trine": "трин",
    "sextile": "секстиль",
    "square": "квадрат",
    "quincunx": "квинконс",
    "quintile": "квинтиль",
    "semi-sextile": "полусекстиль",
    "semi-square": "полуквадрат",
    "sesquiquadrate": "сесквиквадрат",
    "biquintile": "биквинтиль",
}

MOON_PHASE_RU = {
    "New Moon": "Новолуние",
    "Waxing Crescent": "Растущий серп",
    "First Quarter": "Первая четверть",
    "Waxing Gibbous": "Растущая Луна",
    "Full Moon": "Полнолуние",
    "Waning Gibbous": "Убывающая Луна",
    "Last Quarter": "Последняя четверть",
    "Waning Crescent": "Убывающий серп",
}


@dataclass
class NatalReportData:
    chart_data: dict[str, Any]
    moon_phase: dict[str, Any] | None = None
    transit_aspects: list[dict[str, Any]] | None = None


def _dump_model(obj: Any) -> Any:
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return obj


def chart_data_to_dict(chart_data: Any) -> dict[str, Any]:
    if isinstance(chart_data, dict):
        return chart_data
    return _dump_model(chart_data) or {}


def format_degree_dms(position: float | None) -> str:
    if position is None or (isinstance(position, float) and math.isnan(position)):
        return "—"
    pos = float(position) % 30
    deg = int(pos)
    minutes = int(round((pos - deg) * 60))
    if minutes == 60:
        deg += 1
        minutes = 0
    return f"{deg}° {minutes:02d}'"


def format_coords(lat: float, lng: float) -> str:
    lat_dir = "N" if lat >= 0 else "S"
    lng_dir = "E" if lng >= 0 else "W"
    lat_d, lat_m = int(abs(lat)), int(round((abs(lat) % 1) * 60))
    lng_d, lng_m = int(abs(lng)), int(round((abs(lng) % 1) * 60))
    return f"({lat_d}° {lat_m}' {lat_dir}, {lng_d}° {lng_m}' {lng_dir})"


def _collect_bodies(subject: dict[str, Any]) -> dict[str, dict]:
    bodies: dict[str, dict] = {}
    for key, body in subject.items():
        if not isinstance(body, dict):
            continue
        name = body.get("name") or ""
        if not name or not body.get("sign"):
            continue
        if name.endswith("_House") or key.endswith("_house"):
            continue
        bodies[name] = body
    return bodies


def _format_planet_line(body: dict) -> str:
    name = _planet_ru(body.get("name", ""))
    sign = _sign_ru(body.get("sign"))
    deg = format_degree_dms(body.get("position"))
    house = _house_ru(body.get("house"))
    retro = " (R)" if body.get("retrograde") else ""
    house_part = f" ({house} дом)" if house else ""
    return f"• {name} в {deg} {sign}{house_part}{retro}"


def _format_aspect_line(a: dict) -> str:
    p1 = _planet_ru(a.get("p1_name", ""))
    p2 = _planet_ru(a.get("p2_name", ""))
    asp = ASPECT_RU.get((a.get("aspect") or "").lower(), a.get("aspect", ""))
    orb = a.get("orbit")
    orb_s = ""
    if isinstance(orb, (int, float)):
        orb_s = f" (орб {orb:.0f}° {int(round((orb % 1) * 60)):02d}')"
    return f"• {p1} {asp} {p2}{orb_s}"


def build_natal_report(natal: NatalInput, data: NatalReportData) -> list[str]:
    """Возвращает список HTML-сообщений для Telegram (≤4096 символов каждое)."""
    cd = data.chart_data
    subject = cd.get("subject") or {}
    if hasattr(subject, "model_dump"):
        subject = subject.model_dump()

    bodies = _collect_bodies(subject)
    aspects_raw = cd.get("aspects") or []
    aspects = [_dump_model(a) for a in aspects_raw]
    aspects = [a for a in aspects if isinstance(a, dict)]

    sun = bodies.get("Sun", {})
    moon = bodies.get("Moon", {})
    asc = bodies.get("Ascendant", {})

    sections: list[str] = []

    # --- Шапка ---
    header = [
        f"<b>Натальная карта — {natal.name}</b>",
        "",
        "<b>Личные данные</b>",
        f"Дата рождения: {natal.year}-{natal.month:02d}-{natal.day:02d} в {natal.hour:02d}:{natal.minute:02d}",
        f"Место: {natal.location.display_name}",
        format_coords(natal.location.latitude, natal.location.longitude),
        f"Часовой пояс: {natal.location.timezone}",
        "",
        "<b>Астрологические знаки</b>",
        f"Солнце: {_sign_ru(sun.get('sign'))}",
        f"Луна: {_sign_ru(moon.get('sign'))}",
        f"Асцендент: {_sign_ru(asc.get('sign'))}",
        "",
        "<b>Параметры карты</b>",
        f"Система домов: {subject.get('houses_system_name') or subject.get('houses_system_identifier') or 'Плацидус'}",
    ]
    sections.append("\n".join(header))

    # --- Позиции планет ---
    planet_lines = ["<b>Позиции планет</b>", ""]
    subject_keys = {k: subject.get(k) for k, _ in PLANET_POSITION_ORDER}
    for key, _ in PLANET_POSITION_ORDER:
        body = subject.get(key)
        if isinstance(body, dict) and body.get("sign"):
            planet_lines.append(_format_planet_line(body))
    sections.append("\n".join(planet_lines))

    # --- Фаза Луны ---
    if data.moon_phase:
        mp = data.moon_phase.get("moon_phase_overview") or data.moon_phase
        lunar = mp.get("lunar_phase") or subject.get("lunar_phase") or {}
        if hasattr(lunar, "model_dump"):
            lunar = lunar.model_dump()
        phase_name = lunar.get("moon_phase_name") or mp.get("phase_name") or ""
        phase_ru = MOON_PHASE_RU.get(phase_name, phase_name)
        moon_body = bodies.get("Moon", {})
        moon_lines = [
            "<b>Фаза Луны при рождении</b>",
            "",
            f"Фаза: {phase_ru} {lunar.get('moon_emoji', '')}".strip(),
            f"Луна: {_sign_ru(moon_body.get('sign'))} · {format_degree_dms(moon_body.get('position'))}"
            + (f" · {_house_ru(moon_body.get('house'))} дом" if moon_body.get("house") else ""),
        ]
        illum = mp.get("illumination") or mp.get("moon_illumination")
        if illum is not None:
            moon_lines.append(f"Освещённость: {illum}%")
        sections.append("\n".join(moon_lines))
    elif subject.get("lunar_phase"):
        lunar = subject["lunar_phase"]
        if hasattr(lunar, "model_dump"):
            lunar = lunar.model_dump()
        phase_name = lunar.get("moon_phase_name", "")
        sections.append(
            "\n".join(
                [
                    "<b>Фаза Луны при рождении</b>",
                    f"{MOON_PHASE_RU.get(phase_name, phase_name)} {lunar.get('moon_emoji', '')}".strip(),
                ]
            )
        )

    # --- Стихии и кресты ---
    elem = cd.get("element_distribution") or {}
    qual = cd.get("quality_distribution") or {}
    if hasattr(elem, "model_dump"):
        elem = elem.model_dump()
    if hasattr(qual, "model_dump"):
        qual = qual.model_dump()
    if elem or qual:
        dist_lines = ["<b>Стихии и кресты</b>", ""]
        if elem:
            dist_lines.append(
                f"Огонь {elem.get('fire_percentage', '—')}% · "
                f"Земля {elem.get('earth_percentage', '—')}% · "
                f"Воздух {elem.get('air_percentage', '—')}% · "
                f"Вода {elem.get('water_percentage', '—')}%"
            )
        if qual:
            dist_lines.append(
                f"Кардинальный {qual.get('cardinal_percentage', '—')}% · "
                f"Фиксированный {qual.get('fixed_percentage', '—')}% · "
                f"Мутабельный {qual.get('mutable_percentage', '—')}%"
            )
        sections.append("\n".join(dist_lines))

    # --- Паттерны карты ---
    patterns = detect_chart_patterns(bodies, aspects)
    if patterns:
        pat_lines = ["<b>Паттерны карты</b>", ""]
        for p in patterns:
            pat_lines.append(f"<b>{p.name_ru}</b> ({p.name})")
            pat_lines.append(f"  {p.detail}")
            pat_lines.append("")
        sections.append("\n".join(pat_lines).rstrip())

    # --- Мажорные аспекты ---
    major = [a for a in aspects if (a.get("aspect") or "").lower() in MAJOR_ASPECT_NAMES]
    if major:
        major_lines = ["<b>Мажорные аспекты</b>", ""]
        for a in sorted(major, key=lambda x: float(x.get("orbit") or 0)):
            major_lines.append(_format_aspect_line(a))
        sections.append("\n".join(major_lines))

    # --- Минорные аспекты ---
    minor = [a for a in aspects if (a.get("aspect") or "").lower() in MINOR_ASPECT_NAMES]
    if minor:
        minor_lines = ["<b>Минорные аспекты</b>", ""]
        for a in sorted(minor, key=lambda x: float(x.get("orbit") or 0)):
            minor_lines.append(_format_aspect_line(a))
        sections.append("\n".join(minor_lines))

    # --- Транзиты ---
    if data.transit_aspects:
        now = datetime.now(timezone.utc)
        tr_lines = [
            "<b>Важные транзиты (ближайшие аспекты)</b>",
            f"<i>На {now.strftime('%d.%m.%Y')} UTC</i>",
            "",
        ]
        shown = 0
        for a in data.transit_aspects[:15]:
            if not isinstance(a, dict):
                continue
            p1 = a.get("p1_name") or a.get("transit_point") or "Транзит"
            p2 = a.get("p2_name") or a.get("natal_point") or ""
            asp = ASPECT_RU.get((a.get("aspect") or "").lower(), a.get("aspect", ""))
            orb = a.get("orbit") or a.get("orb")
            orb_s = f" (орб {orb:.1f}°)" if isinstance(orb, (int, float)) else ""
            tr_lines.append(f"• {_planet_ru(p1)} {asp} {_planet_ru(p2)}{orb_s}")
            shown += 1
        if shown:
            sections.append("\n".join(tr_lines))

    sections.append(
        "<i>Расчёт: Kerykeion / Astrologer API. White Moon Selena в библиотеке не поддерживается.</i>"
    )

    return _chunk_messages(sections)


def _chunk_messages(sections: list[str], limit: int = 4000) -> list[str]:
    messages: list[str] = []
    current = ""
    for block in sections:
        if len(current) + len(block) + 2 <= limit:
            current = f"{current}\n\n{block}".strip() if current else block
        else:
            if current:
                messages.append(current)
            if len(block) <= limit:
                current = block
            else:
                for i in range(0, len(block), limit):
                    messages.append(block[i : i + limit])
                current = ""
    if current:
        messages.append(current)
    return messages or ["(нет данных)"]


def report_to_plain_text(html_messages: list[str]) -> str:
    import re

    text = "\n\n".join(html_messages)
    return re.sub(r"<[^>]+>", "", text)
