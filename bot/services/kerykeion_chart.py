from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import logging
import tempfile

from kerykeion import AstrologicalSubjectFactory, ChartDataFactory
from kerykeion.charts.chart_drawer import ChartDrawer

from bot.services.geocoding import BirthLocation

logger = logging.getLogger(__name__)

SIGN_RU = {
    "Ari": "Овен",
    "Tau": "Телец",
    "Gem": "Близнецы",
    "Can": "Рак",
    "Leo": "Лев",
    "Vir": "Дева",
    "Lib": "Весы",
    "Sco": "Скорпион",
    "Sag": "Стрелец",
    "Cap": "Козерог",
    "Aqu": "Водолей",
    "Pis": "Рыбы",
}

PLANET_RU = {
    "Sun": "Солнце",
    "Moon": "Луна",
    "Mercury": "Меркурий",
    "Venus": "Венера",
    "Mars": "Марс",
    "Jupiter": "Юпитер",
    "Saturn": "Сатурн",
    "Uranus": "Уран",
    "Neptune": "Нептун",
    "Pluto": "Плутон",
    "Chiron": "Хирон",
    "Mean_Node": "Северный узел",
    "True_Node": "Северный узел",
    "Mean_South_Node": "Южный узел",
    "True_South_Node": "Южный узел",
    "Ascendant": "Асцендент",
    "Medium_Coeli": "MC",
}


@dataclass(frozen=True)
class NatalInput:
    name: str
    year: int
    month: int
    day: int
    hour: int
    minute: int
    location: BirthLocation


def build_subject_payload(natal: NatalInput) -> dict:
    loc = natal.location
    return {
        "name": natal.name,
        "year": natal.year,
        "month": natal.month,
        "day": natal.day,
        "hour": natal.hour,
        "minute": natal.minute,
        "city": loc.city,
        "nation": loc.nation,
        "timezone": loc.timezone,
        "longitude": loc.longitude,
        "latitude": loc.latitude,
    }


def compute_natal_chart(natal: NatalInput):
    loc = natal.location
    subject = AstrologicalSubjectFactory.from_birth_data(
        natal.name,
        natal.year,
        natal.month,
        natal.day,
        natal.hour,
        natal.minute,
        lng=loc.longitude,
        lat=loc.latitude,
        tz_str=loc.timezone,
        online=False,
    )
    return ChartDataFactory.create_natal_chart_data(subject)


def render_local_svg(chart_data, filename: str = "natal") -> Path:
    out_dir = Path(tempfile.mkdtemp(prefix="ai-astrolog-"))
    drawer = ChartDrawer(chart_data=chart_data)
    drawer.save_svg(output_path=out_dir, filename=filename)
    return out_dir / f"{filename}.svg"


def _sign_ru(sign: str | None) -> str:
    if not sign:
        return "—"
    return SIGN_RU.get(sign[:3], sign)


def _planet_ru(name: str) -> str:
    return PLANET_RU.get(name, name.replace("_", " "))


def _house_ru(house: str | None) -> str:
    if not house:
        return ""
    numeral = {
        "First_House": "1",
        "Second_House": "2",
        "Third_House": "3",
        "Fourth_House": "4",
        "Fifth_House": "5",
        "Sixth_House": "6",
        "Seventh_House": "7",
        "Eighth_House": "8",
        "Ninth_House": "9",
        "Tenth_House": "10",
        "Eleventh_House": "11",
        "Twelfth_House": "12",
    }
    return numeral.get(house, house.replace("_", " "))


def format_chart_summary(natal: NatalInput, chart_data) -> str:
    lines: list[str] = [
        f"<b>Натальная карта — {natal.name}</b>",
        "",
        f"📅 {natal.day:02d}.{natal.month:02d}.{natal.year} в {natal.hour:02d}:{natal.minute:02d}",
        f"📍 {natal.location.display_name}",
        f"🕐 {natal.location.timezone}",
        "",
        "<b>Планеты в знаках</b>",
    ]

    subject = getattr(chart_data, "subject", None)
    if hasattr(subject, "model_dump"):
        bodies = subject.model_dump()
    elif isinstance(subject, dict):
        bodies = subject
    else:
        bodies = {}

    for key in (
        "sun",
        "moon",
        "mercury",
        "venus",
        "mars",
        "jupiter",
        "saturn",
        "uranus",
        "neptune",
        "pluto",
        "chiron",
        "true_north_lunar_node",
        "true_south_lunar_node",
        "mean_lilith",
    ):
        body = bodies.get(key)
        if not body or not isinstance(body, dict):
            continue
        label = _planet_ru(body.get("name", key))
        sign = _sign_ru(body.get("sign"))
        house = _house_ru(body.get("house"))
        pos = body.get("position")
        retro = " ℞" if body.get("retrograde") else ""
        house_part = f", {house} дом" if house else ""
        pos_part = f" ({pos:.1f}°)" if isinstance(pos, (int, float)) else ""
        lines.append(f"• {label}: {sign}{house_part}{pos_part}{retro}")

    asc = bodies.get("ascendant")
    if asc:
        lines.append(f"• Асцендент: {_sign_ru(asc.get('sign'))}")

    mc = bodies.get("medium_coeli")
    if mc:
        lines.append(f"• MC: {_sign_ru(mc.get('sign'))}")

    aspects = getattr(chart_data, "aspects", []) or []
    major = [a for a in aspects if getattr(a, "aspect", None) or (isinstance(a, dict) and a.get("aspect"))]
    if major:
        lines.extend(["", "<b>Ключевые аспекты</b>"])
        shown = 0
        for item in major:
            if shown >= 12:
                lines.append("• …")
                break
            if hasattr(item, "model_dump"):
                item = item.model_dump()
            p1 = _planet_ru(str(item.get("p1_name") or item.get("p1") or ""))
            p2 = _planet_ru(str(item.get("p2_name") or item.get("p2") or ""))
            aspect = item.get("aspect") or item.get("name") or ""
            orb = item.get("orbit") or item.get("orb")
            orb_s = f" (орб {orb:.1f}°)" if isinstance(orb, (int, float)) else ""
            lines.append(f"• {p1} — {aspect} — {p2}{orb_s}")
            shown += 1

    elem = getattr(chart_data, "element_distribution", None)
    if elem is not None:
        if hasattr(elem, "model_dump"):
            elem = elem.model_dump()
        lines.extend(
            [
                "",
                "<b>Стихии</b>",
                f"Огонь {getattr(elem, 'fire_percentage', elem.get('fire_percentage', '—'))}% · "
                f"Земля {getattr(elem, 'earth_percentage', elem.get('earth_percentage', '—'))}% · "
                f"Воздух {getattr(elem, 'air_percentage', elem.get('air_percentage', '—'))}% · "
                f"Вода {getattr(elem, 'water_percentage', elem.get('water_percentage', '—'))}%",
            ]
        )

    lines.append("")
    lines.append(
        "<i>Расчёт: Kerykeion (Swiss Ephemeris). Карта на изображении — Astrologer API.</i>"
    )
    return "\n".join(lines)
