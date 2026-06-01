from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import logging
import tempfile
from typing import Any

from kerykeion import AstrologicalSubjectFactory, ChartDataFactory
from kerykeion.charts.chart_drawer import ChartDrawer

from bot.services.chart_constants import PDF_ACTIVE_ASPECTS, PDF_ACTIVE_POINTS
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
    "Mean_North_Lunar_Node": "Северный узел",
    "True_North_Lunar_Node": "Северный узел",
    "Mean_South_Lunar_Node": "Южный узел",
    "True_South_Lunar_Node": "Южный узел",
    "Mean_Lilith": "Чёрная Луна (Лилит)",
    "True_Lilith": "Чёрная Луна (Лилит)",
    "Ascendant": "Асцендент",
    "Descendant": "Десцендент",
    "Medium_Coeli": "MC (Середина неба)",
    "Imum_Coeli": "IC (Глубина неба)",
    "Vertex": "Вертекс",
    "Pars_Fortunae": "Парс Фортуны",
    "Ceres": "Церера",
    "Pallas": "Паллада",
    "Juno": "Юнона",
    "Vesta": "Веста",
    "Pholus": "Фолус",
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
        "houses_system_identifier": "P",
    }


def _api_chart_payload(natal: NatalInput) -> dict:
    return {
        "subject": build_subject_payload(natal),
        "active_points": list(PDF_ACTIVE_POINTS),
        "active_aspects": list(PDF_ACTIVE_ASPECTS),
        "distribution_method": "weighted",
    }


def create_subject(natal: NatalInput):
    loc = natal.location
    return AstrologicalSubjectFactory.from_birth_data(
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
        active_points=list(PDF_ACTIVE_POINTS),
    )


def compute_natal_chart(natal: NatalInput):
    subject = create_subject(natal)
    return ChartDataFactory.create_natal_chart_data(
        subject,
        active_points=list(PDF_ACTIVE_POINTS),
        active_aspects=list(PDF_ACTIVE_ASPECTS),
    )


def chart_data_as_dict(chart_data: Any) -> dict[str, Any]:
    if isinstance(chart_data, dict):
        return chart_data
    if hasattr(chart_data, "model_dump"):
        return chart_data.model_dump()
    return {}


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
