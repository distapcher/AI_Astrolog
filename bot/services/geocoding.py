from dataclasses import dataclass
import logging
import re

from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

logger = logging.getLogger(__name__)

_geolocator = Nominatim(user_agent="ai-astrolog-bot/0.1", timeout=10)
_tz_finder = TimezoneFinder()


@dataclass(frozen=True)
class BirthLocation:
    city: str
    nation: str
    latitude: float
    longitude: float
    timezone: str
    display_name: str


def _normalize_nation(raw: str) -> str:
    value = raw.strip().upper()
    if len(value) == 2:
        return value
    aliases = {
        "РОССИЯ": "RU",
        "RUSSIA": "RU",
        "УКРАИНА": "UA",
        "UKRAINE": "UA",
        "БЕЛАРУСЬ": "BY",
        "КАЗАХСТАН": "KZ",
    }
    return aliases.get(value, value[:2] if len(value) >= 2 else "RU")


def resolve_place_with_geonames(
    city: str,
    nation: str,
    geonames_username: str,
    *,
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int,
) -> BirthLocation:
    """Резерв: координаты через Kerykeion + GeoNames."""
    from kerykeion import AstrologicalSubjectFactory

    nation_code = _normalize_nation(nation)
    subject = AstrologicalSubjectFactory.from_birth_data(
        "GeoLookup",
        year,
        month,
        day,
        hour,
        minute,
        city=city.strip(),
        nation=nation_code,
        geonames_username=geonames_username,
        online=True,
    )
    tz = getattr(subject, "tz_str", None) or getattr(subject, "timezone", None)
    if not tz:
        tz = _tz_finder.timezone_at(lat=subject.lat, lng=subject.lng)
    if not tz:
        raise ValueError("Не удалось определить часовой пояс.")
    return BirthLocation(
        city=city.strip(),
        nation=nation_code,
        latitude=float(subject.lat),
        longitude=float(subject.lng),
        timezone=str(tz),
        display_name=f"{city.strip()}, {nation_code}",
    )


def resolve_place(city: str, nation: str = "RU") -> BirthLocation:
    nation_code = _normalize_nation(nation)
    query = f"{city.strip()}, {nation_code}"
    try:
        location = _geolocator.geocode(query, language="ru", addressdetails=True, timeout=10)
    except (GeocoderTimedOut, GeocoderServiceError) as exc:
        raise ValueError("Сервис геокодирования временно недоступен. Попробуйте позже.") from exc

    if location is None:
        raise ValueError(
            f"Не удалось найти место «{city}». "
            "Уточните название города или укажите страну (например: Москва, RU)."
        )

    tz = _tz_finder.timezone_at(lat=location.latitude, lng=location.longitude)
    if not tz:
        raise ValueError("Не удалось определить часовой пояс для этого места.")

    display = location.address or query
    return BirthLocation(
        city=city.strip(),
        nation=nation_code,
        latitude=float(location.latitude),
        longitude=float(location.longitude),
        timezone=tz,
        display_name=display,
    )


_DATE_RE = re.compile(r"^(\d{1,2})[./](\d{1,2})[./](\d{4})$")
_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})$")


def parse_birth_date(text: str) -> tuple[int, int, int]:
    match = _DATE_RE.match(text.strip())
    if not match:
        raise ValueError("Формат даты: ДД.ММ.ГГГГ (например 15.05.1990)")
    day, month, year = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    if not (1 <= month <= 12 and 1 <= day <= 31 and 1900 <= year <= 2100):
        raise ValueError("Некорректная дата.")
    return year, month, day


def parse_birth_time(text: str) -> tuple[int, int]:
    match = _TIME_RE.match(text.strip())
    if not match:
        raise ValueError("Формат времени: ЧЧ:ММ (например 14:30)")
    hour, minute = int(match.group(1)), int(match.group(2))
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("Некорректное время.")
    return hour, minute
