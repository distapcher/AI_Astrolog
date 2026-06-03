from __future__ import annotations

import html
import re

# Строка-заголовок раздела: «Раздел 1: …», «РАЗДЕЛ 2 …», «### РАЗДЕЛ 3:»
_SECTION_LINE = re.compile(
    r"^\s*(?:#{1,6}\s*)?"
    r"(?:\*{1,2}\s*)?"
    r"(?:РАЗДЕЛ|Раздел)\s*(\d+)\s*"
    r"(?:[:\.\—\-–]\s*|\s+)"
    r"(.*)?"
    r"(?:\s*\*{1,2})?\s*$",
    re.IGNORECASE,
)


def _strip_markdown_chars(line: str) -> str:
    """Убирает *, # и markdown-заголовки в начале строки."""
    s = re.sub(r"^\s*#{1,6}\s*", "", line)
    return s.replace("*", "").replace("#", "").strip()


def format_personality_text(text: str) -> str:
    """Готовит текст анализа личности для Telegram (HTML, parse_mode=HTML)."""
    if not text:
        return ""

    out: list[str] = []
    for raw_line in text.splitlines():
        stripped = _strip_markdown_chars(raw_line)
        if not stripped:
            out.append("")
            continue

        match = _SECTION_LINE.match(raw_line) or _SECTION_LINE.match(stripped)
        if match:
            num = match.group(1)
            title = (match.group(2) or "").strip()
            title = _strip_markdown_chars(title)
            heading = f"Раздел {num}: {title}" if title else f"Раздел {num}"
            out.append(f"<b>{html.escape(heading)}</b>")
            continue

        out.append(html.escape(stripped))

    return "\n".join(out)
