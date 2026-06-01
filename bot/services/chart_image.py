from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_WIDTH = 1280


class ChartImageError(Exception):
    pass


def _rsvg_convert(svg_path: Path, png_path: Path, width: int) -> None:
    rsvg = shutil.which("rsvg-convert")
    if not rsvg:
        raise ChartImageError("rsvg-convert не установлен (пакет librsvg2-bin).")
    result = subprocess.run(
        [rsvg, "-w", str(width), str(svg_path), "-o", str(png_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise ChartImageError(stderr or "Ошибка конвертации SVG в PNG")


def _cairosvg_convert(svg_content: str, width: int) -> bytes:
    try:
        import cairosvg
    except ImportError as exc:
        raise ChartImageError("cairosvg не установлен") from exc
    return cairosvg.svg2png(bytestring=svg_content.encode("utf-8"), output_width=width)


def svg_to_png_bytes(svg_content: str, *, width: int = DEFAULT_WIDTH) -> bytes:
    if not svg_content.strip():
        raise ChartImageError("Пустой SVG")

    if shutil.which("rsvg-convert"):
        with tempfile.TemporaryDirectory(prefix="ai-astrolog-svg-") as tmp:
            svg_path = Path(tmp) / "chart.svg"
            png_path = Path(tmp) / "chart.png"
            svg_path.write_text(svg_content, encoding="utf-8")
            _rsvg_convert(svg_path, png_path, width)
            return png_path.read_bytes()

    logger.info("rsvg-convert not found, using cairosvg")
    try:
        return _cairosvg_convert(svg_content, width)
    except ChartImageError as exc:
        raise ChartImageError(
            "Нет конвертера SVG→PNG (librsvg2-bin + libcairo2 или cairosvg)."
        ) from exc


def svg_file_to_png_bytes(svg_path: Path, *, width: int = DEFAULT_WIDTH) -> bytes:
    return svg_to_png_bytes(svg_path.read_text(encoding="utf-8"), width=width)
