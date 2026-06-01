from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from bot.config import BASE_DIR
from bot.services.geocoding import BirthLocation
from bot.services.kerykeion_chart import NatalInput

DEFAULT_DB_PATH = Path(os.getenv("NATAL_DB_PATH", str(BASE_DIR / "data" / "natal_profiles.db")))


def _ensure_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS natal_profiles (
                user_id INTEGER PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def _natal_to_dict(natal: NatalInput) -> dict:
    loc = natal.location
    return {
        "name": natal.name,
        "year": natal.year,
        "month": natal.month,
        "day": natal.day,
        "hour": natal.hour,
        "minute": natal.minute,
        "location": {
            "city": loc.city,
            "nation": loc.nation,
            "latitude": loc.latitude,
            "longitude": loc.longitude,
            "timezone": loc.timezone,
            "display_name": loc.display_name,
        },
    }


def _natal_from_dict(data: dict) -> NatalInput:
    loc = data["location"]
    return NatalInput(
        name=data["name"],
        year=int(data["year"]),
        month=int(data["month"]),
        day=int(data["day"]),
        hour=int(data["hour"]),
        minute=int(data["minute"]),
        location=BirthLocation(
            city=loc["city"],
            nation=loc["nation"],
            latitude=float(loc["latitude"]),
            longitude=float(loc["longitude"]),
            timezone=loc["timezone"],
            display_name=loc["display_name"],
        ),
    )


def save_natal_profile(user_id: int, natal: NatalInput, db_path: Path | None = None) -> None:
    path = db_path or DEFAULT_DB_PATH
    _ensure_db(path)
    payload = json.dumps(_natal_to_dict(natal), ensure_ascii=False)
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            INSERT INTO natal_profiles (user_id, payload, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(user_id) DO UPDATE SET
                payload = excluded.payload,
                updated_at = excluded.updated_at
            """,
            (user_id, payload),
        )


def load_natal_profile(user_id: int, db_path: Path | None = None) -> NatalInput | None:
    path = db_path or DEFAULT_DB_PATH
    if not path.exists():
        return None
    with sqlite3.connect(path) as conn:
        row = conn.execute(
            "SELECT payload FROM natal_profiles WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    if not row:
        return None
    return _natal_from_dict(json.loads(row[0]))
