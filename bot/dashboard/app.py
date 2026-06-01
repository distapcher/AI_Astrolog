from __future__ import annotations

import secrets
from html import escape
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from bot.config import load_settings
from bot.services.usage_store import dashboard_totals, list_user_stats

security = HTTPBasic()
app = FastAPI(title="AI Astrolog Dashboard", docs_url=None, redoc_url=None)


def _verify(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    settings = load_settings()
    user_ok = secrets.compare_digest(
        credentials.username.encode("utf-8"),
        settings.dashboard_user.encode("utf-8"),
    )
    pass_ok = secrets.compare_digest(
        credentials.password.encode("utf-8"),
        settings.dashboard_password.encode("utf-8"),
    )
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def _fmt_num(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def _render_dashboard() -> str:
    settings = load_settings()
    users = list_user_stats(settings.analytics_db_path)
    totals = dashboard_totals(settings.analytics_db_path)

    rows_html = ""
    for u in users:
        username = f"@{escape(u.username)}" if u.username else "—"
        link = (
            f'<a href="{escape(u.telegram_link)}" target="_blank" rel="noopener">открыть</a>'
            if u.telegram_link
            else "—"
        )
        rows_html += f"""
        <tr>
          <td>{u.user_id}</td>
          <td><strong>{escape(u.display_name)}</strong></td>
          <td>{username}</td>
          <td>{link}</td>
          <td class="num">{u.personality_analysis_count}</td>
          <td class="num">{_fmt_num(u.prompt_tokens)}</td>
          <td class="num">{_fmt_num(u.completion_tokens)}</td>
          <td class="num">{_fmt_num(u.total_tokens)}</td>
          <td class="muted">{escape(u.first_seen_at[:19].replace("T", " "))}</td>
          <td class="muted">{escape(u.last_seen_at[:19].replace("T", " "))}</td>
        </tr>
        """

    if not rows_html:
        rows_html = """
        <tr><td colspan="10" class="empty">Пока нет пользователей — данные появятся после первого обращения к боту.</td></tr>
        """

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Astrolog — дашборд</title>
  <style>
    :root {{
      --bg: #0f1419;
      --card: #1a2332;
      --text: #e7ecf3;
      --muted: #8b9cb3;
      --accent: #6c9eff;
      --border: #2a3548;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
    }}
    .wrap {{ max-width: 1200px; margin: 0 auto; padding: 24px 16px 48px; }}
    h1 {{ margin: 0 0 8px; font-size: 1.6rem; }}
    .sub {{ color: var(--muted); margin-bottom: 24px; }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin-bottom: 28px;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px;
    }}
    .card .label {{ font-size: 0.8rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; }}
    .card .value {{ font-size: 1.5rem; font-weight: 700; margin-top: 4px; color: var(--accent); }}
    .table-wrap {{
      overflow-x: auto;
      border: 1px solid var(--border);
      border-radius: 12px;
      background: var(--card);
    }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
    th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); }}
    th {{ color: var(--muted); font-weight: 600; font-size: 0.75rem; text-transform: uppercase; }}
    tr:last-child td {{ border-bottom: none; }}
    tr:hover td {{ background: rgba(108, 158, 255, 0.06); }}
    .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    th.num {{ text-align: right; }}
    .muted {{ color: var(--muted); font-size: 0.85rem; }}
    .empty {{ text-align: center; color: var(--muted); padding: 32px !important; }}
    a {{ color: var(--accent); }}
    footer {{ margin-top: 24px; color: var(--muted); font-size: 0.8rem; }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Космический Астролог — дашборд</h1>
    <p class="sub">Telegram-пользователи, запуски анализа личности и расход токенов ИИ</p>

    <div class="cards">
      <div class="card"><div class="label">Пользователей</div><div class="value">{totals["users"]}</div></div>
      <div class="card"><div class="label">Анализов личности</div><div class="value">{totals["analyses"]}</div></div>
      <div class="card"><div class="label">Токенов (prompt)</div><div class="value">{_fmt_num(totals["prompt_tokens"])}</div></div>
      <div class="card"><div class="label">Токенов (ответ)</div><div class="value">{_fmt_num(totals["completion_tokens"])}</div></div>
      <div class="card"><div class="label">Токенов всего</div><div class="value">{_fmt_num(totals["total_tokens"])}</div></div>
    </div>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Имя</th>
            <th>Username</th>
            <th>Профиль</th>
            <th class="num">Анализов</th>
            <th class="num">Prompt</th>
            <th class="num">Completion</th>
            <th class="num">Всего</th>
            <th>Первый визит</th>
            <th>Последний</th>
          </tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>
    </div>
    <footer>Обновите страницу для актуальных данных · {escape(str(settings.analytics_db_path))}</footer>
  </div>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def dashboard_page(_user: str = Depends(_verify)) -> HTMLResponse:
    return HTMLResponse(_render_dashboard())


@app.get("/api/stats")
def api_stats(_user: str = Depends(_verify)) -> dict:
    settings = load_settings()
    return {
        "totals": dashboard_totals(settings.analytics_db_path),
        "users": [
            {
                "user_id": u.user_id,
                "display_name": u.display_name,
                "username": u.username,
                "personality_analysis_count": u.personality_analysis_count,
                "prompt_tokens": u.prompt_tokens,
                "completion_tokens": u.completion_tokens,
                "total_tokens": u.total_tokens,
                "first_seen_at": u.first_seen_at,
                "last_seen_at": u.last_seen_at,
            }
            for u in list_user_stats(settings.analytics_db_path)
        ],
    }


def run() -> None:
    settings = load_settings()
    uvicorn.run(
        "bot.dashboard.app:app",
        host=settings.dashboard_host,
        port=settings.dashboard_port,
        log_level="info",
    )
