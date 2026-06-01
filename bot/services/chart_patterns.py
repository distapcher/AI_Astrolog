from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class ChartPattern:
    name: str
    name_ru: str
    bodies: tuple[str, ...]
    detail: str


def _aspect_map(aspects: list[dict]) -> dict[tuple[str, str], str]:
    out: dict[tuple[str, str], str] = {}
    for a in aspects:
        p1 = a.get("p1_name") or ""
        p2 = a.get("p2_name") or ""
        asp = (a.get("aspect") or "").lower()
        if not p1 or not p2 or not asp:
            continue
        key = tuple(sorted((p1, p2)))
        out[key] = asp
    return out


def _has_aspect(am: dict[tuple[str, str], str], a: str, b: str, aspect: str) -> bool:
    return am.get(tuple(sorted((a, b)))) == aspect


def detect_stelliums(bodies: dict[str, dict], min_count: int = 3) -> list[ChartPattern]:
    by_sign: dict[str, list[str]] = defaultdict(list)
    skip = {
        "Ascendant",
        "Descendant",
        "Medium_Coeli",
        "Imum_Coeli",
        "Vertex",
        "Pars_Fortunae",
        "First_House",
        "Second_House",
        "Third_House",
        "Fourth_House",
        "Fifth_House",
        "Sixth_House",
        "Seventh_House",
        "Eighth_House",
        "Ninth_House",
        "Tenth_House",
        "Eleventh_House",
        "Twelfth_House",
    }
    for name, data in bodies.items():
        if name in skip or "House" in name:
            continue
        sign = data.get("sign")
        if sign:
            by_sign[sign].append(name)

    patterns: list[ChartPattern] = []
    for sign, names in by_sign.items():
        if len(names) >= min_count:
            patterns.append(
                ChartPattern(
                    name="Stellium",
                    name_ru="Стеллиум",
                    bodies=tuple(names),
                    detail=f"Скопление в {sign}: {', '.join(names)}",
                )
            )
    return patterns


def detect_yods(aspects: list[dict], max_orb: float = 3.0) -> list[ChartPattern]:
    """Yod: две планеты в секстиле, обе в квинконсе к третьей (апекс)."""
    quincunx: dict[str, set[str]] = defaultdict(set)
    sextile: set[tuple[str, str]] = set()

    for a in aspects:
        asp = (a.get("aspect") or "").lower()
        p1, p2 = a.get("p1_name"), a.get("p2_name")
        orb = float(a.get("orbit") or 99)
        if not p1 or not p2 or orb > max_orb:
            continue
        if asp == "quincunx":
            quincunx[p1].add(p2)
            quincunx[p2].add(p1)
        elif asp == "sextile":
            sextile.add(tuple(sorted((p1, p2))))

    patterns: list[ChartPattern] = []
    seen: set[tuple[str, str, str]] = set()
    for (b, c) in sextile:
        common = quincunx[b] & quincunx[c]
        for apex in common:
            if apex in (b, c):
                continue
            key = tuple(sorted((apex, b, c)))
            if key in seen:
                continue
            seen.add(key)
            patterns.append(
                ChartPattern(
                    name="Yod",
                    name_ru="Йод",
                    bodies=(apex, b, c),
                    detail=f"Апекс {apex}: квинконс к {b} и {c}, между ними секстиль",
                )
            )
    return patterns


def detect_chart_patterns(bodies: dict[str, dict], aspects: list[dict]) -> list[ChartPattern]:
    found: list[ChartPattern] = []
    found.extend(detect_stelliums(bodies))
    found.extend(detect_yods(aspects))
    return found
