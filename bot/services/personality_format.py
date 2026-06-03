from __future__ import annotations

import html
import re

# Строка-заголовок раздела: «Раздел 1: …», «РАЗДЕЛ 2 …», «### РАЗДЕЛ 3:»
_INTRO_CLOSING = "Итак, приступим к разбору твоей «Формулы успеха»."
_OLD_CLOSING = re.compile(
    r"Давай\s+разбер[её]м\s+тво[юеё]\s+"
    r"[«\"']?Формулу\s+успеха[»\"']?\s+по\s+шагам\.?",
    re.IGNORECASE,
)


def _normalize_intro_closing(text: str) -> str:
    return _OLD_CLOSING.sub(_INTRO_CLOSING, text)


_SUBLABEL_LINE = re.compile(
    r"^(\s*(?:\d+\.\s*)?)(Тезис:|Обоснование:)(.*)$",
    re.IGNORECASE,
)

_SECTION_LINE = re.compile(
    r"^\s*(?:#{1,6}\s*)?"
    r"(?:\*{1,2}\s*)?"
    r"(?:РАЗДЕЛ|Раздел)\s*(\d+)\s*"
    r"(?:[:\.\—\-–]\s*|\s+)"
    r"(.*)?"
    r"(?:\s*\*{1,2})?\s*$",
    re.IGNORECASE,
)


def _format_body_line(stripped: str) -> str:
    m = _SUBLABEL_LINE.match(stripped)
    if m:
        prefix = html.escape(m.group(1))
        label = m.group(2)
        if label.lower().startswith("тезис"):
            label = "Тезис:"
        else:
            label = "Обоснование:"
        rest = html.escape(m.group(3))
        return f"{prefix}<i>{html.escape(label)}</i>{rest}"
    return html.escape(stripped)


def _strip_markdown_chars(line: str) -> str:
    """Убирает *, # и markdown-заголовки в начале строки."""
    s = re.sub(r"^\s*#{1,6}\s*", "", line)
    return s.replace("*", "").replace("#", "").strip()


def format_personality_text(text: str) -> str:
    """Готовит текст анализа личности для Telegram (HTML, parse_mode=HTML)."""
    if not text:
        return ""

    text = _normalize_intro_closing(text)
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

        out.append(_format_body_line(stripped))

    return "\n".join(out)
