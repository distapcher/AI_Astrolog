from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from bot.services.astrologer_api import AstrologerClient
from bot.services.chart_report import NatalReportData, build_natal_report, report_to_plain_text
from bot.services.kerykeion_chart import NatalInput, chart_data_as_dict, compute_natal_chart

logger = logging.getLogger(__name__)


@dataclass
class NatalChartBundle:
    natal: NatalInput
    chart_data: dict[str, Any]
    moon_phase: dict[str, Any] | None
    transit_aspects: list[dict[str, Any]] | None
    svg_content: str
    local_chart: Any | None


async def build_natal_bundle(natal: NatalInput, astrologer: AstrologerClient) -> NatalChartBundle:
    local_chart = None
    try:
        local_chart = compute_natal_chart(natal)
    except Exception:
        logger.exception("Kerykeion calculation failed")

    api_pkg: dict = {}
    try:
        api_pkg = await astrologer.fetch_complete_natal_package(natal, include_svg=True)
    except Exception:
        logger.exception("Astrologer API package failed")

    chart_data_dict = api_pkg.get("chart_data")
    if chart_data_dict and hasattr(chart_data_dict, "model_dump"):
        chart_data_dict = chart_data_dict.model_dump()
    elif local_chart:
        chart_data_dict = chart_data_as_dict(local_chart)
    else:
        raise RuntimeError("Не удалось рассчитать натальную карту.")

    return NatalChartBundle(
        natal=natal,
        chart_data=chart_data_dict,
        moon_phase=api_pkg.get("moon_phase"),
        transit_aspects=api_pkg.get("transit_aspects"),
        svg_content=api_pkg.get("svg") or "",
        local_chart=local_chart,
    )


def bundle_plain_text_for_ai(bundle: NatalChartBundle) -> str:
    report_data = NatalReportData(
        chart_data=bundle.chart_data,
        moon_phase=bundle.moon_phase,
        transit_aspects=bundle.transit_aspects,
    )
    return report_to_plain_text(build_natal_report(bundle.natal, report_data))


def bundle_report_messages(bundle: NatalChartBundle) -> list[str]:
    report_data = NatalReportData(
        chart_data=bundle.chart_data,
        moon_phase=bundle.moon_phase,
        transit_aspects=bundle.transit_aspects,
    )
    return build_natal_report(bundle.natal, report_data)
