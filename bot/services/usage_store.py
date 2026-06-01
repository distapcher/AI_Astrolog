from __future__ import annotations

import asyncio
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_ANALYTICS_DB = Path("/data/analytics.db")
_db_path: Path | None = None


@dataclass(frozen=True)
class UserStats:
    user_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    first_seen_at: str
    last_seen_at: str
    personality_analysis_count: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

    @property
    def display_name(self) -> str:
        parts = [self.first_name or "", self.last_name or ""]
        name = " ".join(p for p in parts if p).strip()
        if name:
            return name
        if self.username:
            return f"@{self.username}"
        return str(self.user_id)

    @property
    def telegram_link(self) -> str | None:
        if self.username:
            return f"https://t.me/{self.username}"
        return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _resolve_path(db_path: Path | None) -> Path:
    return db_path or _db_path or DEFAULT_ANALYTICS_DB


def init_analytics_db(path: Path | None = None) -> Path:
    global _db_path
    db_path = _resolve_path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path, timeout=30) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bot_users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                personality_analysis_count INTEGER NOT NULL DEFAULT 0,
                prompt_tokens INTEGER NOT NULL DEFAULT 0,
                completion_tokens INTEGER NOT NULL DEFAULT 0,
                total_tokens INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_bot_users_last_seen ON bot_users(last_seen_at DESC)"
        )
    _db_path = db_path
    return db_path


def _connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = _resolve_path(db_path)
    if _db_path is None:
        init_analytics_db(path)
    return sqlite3.connect(path, timeout=30)


def upsert_telegram_user(
    user_id: int,
    *,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    db_path: Path | None = None,
) -> None:
    if not user_id:
        return
    now = _now_iso()
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO bot_users (
                user_id, username, first_name, last_name,
                first_seen_at, last_seen_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = COALESCE(excluded.username, bot_users.username),
                first_name = COALESCE(excluded.first_name, bot_users.first_name),
                last_name = COALESCE(excluded.last_name, bot_users.last_name),
                last_seen_at = excluded.last_seen_at
            """,
            (user_id, username, first_name, last_name, now, now),
        )


def _ensure_user_row(conn: sqlite3.Connection, user_id: int) -> None:
    row = conn.execute(
        "SELECT 1 FROM bot_users WHERE user_id = ?", (user_id,)
    ).fetchone()
    if not row:
        now = _now_iso()
        conn.execute(
            """
            INSERT INTO bot_users (
                user_id, first_seen_at, last_seen_at
            ) VALUES (?, ?, ?)
            """,
            (user_id, now, now),
        )


def record_personality_analysis_start(user_id: int, db_path: Path | None = None) -> None:
    if not user_id:
        return
    now = _now_iso()
    with _connect(db_path) as conn:
        _ensure_user_row(conn, user_id)
        conn.execute(
            """
            UPDATE bot_users SET
                personality_analysis_count = personality_analysis_count + 1,
                last_seen_at = ?
            WHERE user_id = ?
            """,
            (now, user_id),
        )


def add_token_usage(
    user_id: int,
    *,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    db_path: Path | None = None,
) -> None:
    if not user_id:
        return
    if total_tokens <= 0 and (prompt_tokens > 0 or completion_tokens > 0):
        total_tokens = prompt_tokens + completion_tokens
    if total_tokens <= 0 and prompt_tokens <= 0 and completion_tokens <= 0:
        return
    with _connect(db_path) as conn:
        _ensure_user_row(conn, user_id)
        conn.execute(
            """
            UPDATE bot_users SET
                prompt_tokens = prompt_tokens + ?,
                completion_tokens = completion_tokens + ?,
                total_tokens = total_tokens + ?,
                last_seen_at = ?
            WHERE user_id = ?
            """,
            (prompt_tokens, completion_tokens, total_tokens, _now_iso(), user_id),
        )


def list_user_stats(db_path: Path | None = None) -> list[UserStats]:
    with _connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT user_id, username, first_name, last_name,
                   first_seen_at, last_seen_at,
                   personality_analysis_count,
                   prompt_tokens, completion_tokens, total_tokens
            FROM bot_users
            ORDER BY last_seen_at DESC
            """
        ).fetchall()
    return [
        UserStats(
            user_id=row["user_id"],
            username=row["username"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            first_seen_at=row["first_seen_at"],
            last_seen_at=row["last_seen_at"],
            personality_analysis_count=row["personality_analysis_count"],
            prompt_tokens=row["prompt_tokens"],
            completion_tokens=row["completion_tokens"],
            total_tokens=row["total_tokens"],
        )
        for row in rows
    ]


def dashboard_totals(db_path: Path | None = None) -> dict[str, int]:
    with _connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS users,
                COALESCE(SUM(personality_analysis_count), 0) AS analyses,
                COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
                COALESCE(SUM(completion_tokens), 0) AS completion_tokens,
                COALESCE(SUM(total_tokens), 0) AS total_tokens
            FROM bot_users
            """
        ).fetchone()
    return {
        "users": int(row[0]),
        "analyses": int(row[1]),
        "prompt_tokens": int(row[2]),
        "completion_tokens": int(row[3]),
        "total_tokens": int(row[4]),
    }


async def upsert_telegram_user_async(
    user_id: int,
    *,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    db_path: Path | None = None,
) -> None:
    try:
        await asyncio.to_thread(
            upsert_telegram_user,
            user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            db_path=db_path,
        )
    except Exception:
        logger.exception("analytics upsert failed for user %s", user_id)


async def record_personality_analysis_start_async(
    user_id: int, db_path: Path | None = None
) -> None:
    try:
        await asyncio.to_thread(record_personality_analysis_start, user_id, db_path=db_path)
    except Exception:
        logger.exception("analytics analysis start failed for user %s", user_id)


async def add_token_usage_async(
    user_id: int,
    *,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    db_path: Path | None = None,
) -> None:
    try:
        await asyncio.to_thread(
            add_token_usage,
            user_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            db_path=db_path,
        )
    except Exception:
        logger.exception("analytics token usage failed for user %s", user_id)


def schedule_upsert_telegram_user(
    user_id: int,
    *,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    db_path: Path | None = None,
) -> None:
    asyncio.create_task(
        upsert_telegram_user_async(
            user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            db_path=db_path,
        )
    )


def schedule_record_personality_analysis_start(
    user_id: int, db_path: Path | None = None
) -> None:
    asyncio.create_task(
        record_personality_analysis_start_async(user_id, db_path=db_path)
    )


def schedule_add_token_usage(
    user_id: int,
    *,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    db_path: Path | None = None,
) -> None:
    asyncio.create_task(
        add_token_usage_async(
            user_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            db_path=db_path,
        )
    )
