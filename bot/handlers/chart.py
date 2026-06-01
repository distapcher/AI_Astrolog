from __future__ import annotations

import logging
import re

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.services.ai_interpreter import AiInterpreter
from bot.services.astrologer_api import AstrologerApiError, AstrologerClient, svg_to_temp_file
from bot.config import Settings
from bot.services.chart_report import NatalReportData, build_natal_report, report_to_plain_text
from bot.services.geocoding import (
    parse_birth_date,
    parse_birth_time,
    resolve_place,
    resolve_place_with_geonames,
)
from bot.services.kerykeion_chart import NatalInput, chart_data_as_dict, compute_natal_chart
from bot.states import NatalChartStates

logger = logging.getLogger(__name__)
router = Router()

_pending_interpret: dict[int, dict[str, str]] = {}

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _HTML_TAG_RE.sub("", text)


async def _start_chart_flow(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(NatalChartStates.name)
    await message.answer(
        "Введите <b>имя</b> для карты (или «—», если без имени):",
    )


@router.message(Command("chart"))
@router.message(F.text == "🌟 Натальная карта")
async def start_chart(message: Message, state: FSMContext) -> None:
    await _start_chart_flow(message, state)


@router.message(NatalChartStates.name)
async def on_name(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    name = "Гость" if raw in {"", "—", "-"} else raw[:64]
    await state.update_data(name=name)
    await state.set_state(NatalChartStates.birth_date)
    await message.answer("Дата рождения (<code>ДД.ММ.ГГГГ</code>):")


@router.message(NatalChartStates.birth_date)
async def on_birth_date(message: Message, state: FSMContext) -> None:
    try:
        year, month, day = parse_birth_date(message.text or "")
    except ValueError as exc:
        await message.answer(str(exc))
        return
    await state.update_data(year=year, month=month, day=day)
    await state.set_state(NatalChartStates.birth_time)
    await message.answer("Время рождения (<code>ЧЧ:ММ</code>, местное):")


@router.message(NatalChartStates.birth_time)
async def on_birth_time(message: Message, state: FSMContext) -> None:
    try:
        hour, minute = parse_birth_time(message.text or "")
    except ValueError as exc:
        await message.answer(str(exc))
        return
    await state.update_data(hour=hour, minute=minute)
    await state.set_state(NatalChartStates.birth_place)
    await message.answer("Город рождения (например: <code>Санкт-Петербург</code>):")


@router.message(NatalChartStates.birth_place)
async def on_birth_place(message: Message, state: FSMContext) -> None:
    city = (message.text or "").strip()
    if len(city) < 2:
        await message.answer("Укажите название города.")
        return
    await state.update_data(city=city)
    await state.set_state(NatalChartStates.birth_nation)
    await message.answer(
        "Страна (код ISO, например <code>RU</code>). "
        "Отправьте «—» или <code>RU</code> для России:"
    )


@router.message(NatalChartStates.birth_nation)
async def on_birth_nation(
    message: Message,
    state: FSMContext,
    astrologer: AstrologerClient,
    ai: AiInterpreter,
    settings: Settings,
) -> None:
    nation_raw = (message.text or "").strip()
    nation = "RU" if nation_raw in {"", "—", "-", "ru", "RU"} else nation_raw
    data = await state.get_data()
    await state.clear()

    user_id = message.from_user.id if message.from_user else 0
    wait_msg = await message.answer(
        "⏳ Считаю натальную карту (планеты, аспекты, фаза Луны, транзиты)…"
    )

    try:
        location = resolve_place(data["city"], nation)
    except ValueError as exc:
        if settings.geonames_username:
            try:
                location = resolve_place_with_geonames(
                    data["city"],
                    nation,
                    settings.geonames_username,
                    year=data["year"],
                    month=data["month"],
                    day=data["day"],
                    hour=data["hour"],
                    minute=data["minute"],
                )
            except Exception:
                logger.exception("GeoNames fallback failed")
                await wait_msg.edit_text(str(exc))
                return
        else:
            await wait_msg.edit_text(str(exc))
            return

    natal = NatalInput(
        name=data["name"],
        year=data["year"],
        month=data["month"],
        day=data["day"],
        hour=data["hour"],
        minute=data["minute"],
        location=location,
    )

    local_chart = None
    try:
        local_chart = compute_natal_chart(natal)
    except Exception:
        logger.exception("Kerykeion calculation failed")

    api_pkg: dict = {}
    try:
        api_pkg = await astrologer.fetch_complete_natal_package(natal)
    except Exception:
        logger.exception("Astrologer API package failed")

    chart_data_dict = api_pkg.get("chart_data")
    if chart_data_dict:
        if hasattr(chart_data_dict, "model_dump"):
            chart_data_dict = chart_data_dict.model_dump()
    elif local_chart:
        chart_data_dict = chart_data_as_dict(local_chart)
    else:
        await wait_msg.edit_text("Ошибка расчёта карты. Проверьте дату, время и место.")
        return

    report_data = NatalReportData(
        chart_data=chart_data_dict,
        moon_phase=api_pkg.get("moon_phase"),
        transit_aspects=api_pkg.get("transit_aspects"),
    )
    report_messages = build_natal_report(natal, report_data)
    plain_report = report_to_plain_text(report_messages)

    svg_path = None
    if api_pkg.get("svg"):
        svg_path = svg_to_temp_file(api_pkg["svg"])
    elif local_chart:
        try:
            svg_path = await astrologer.save_chart_png_fallback(natal, local_chart)
        except Exception:
            pass

    await wait_msg.delete()

    if svg_path and svg_path.exists():
        doc = BufferedInputFile(svg_path.read_bytes(), filename="natal_chart.svg")
        await message.answer_document(doc, caption="🎴 Натальная карта")

    for idx, part in enumerate(report_messages):
        prefix = f"<b>Отчёт ({idx + 1}/{len(report_messages)})</b>\n\n" if len(report_messages) > 1 else ""
        await message.answer(prefix + part)

    if ai.enabled and user_id:
        _pending_interpret[user_id] = {
            "name": natal.name,
            "summary_plain": plain_report,
        }
        builder = InlineKeyboardBuilder()
        builder.button(text="📜 Полная ИИ-расшифровка", callback_data="interpret:1")
        await message.answer(
            "Могу подготовить подробную расшифровку по 10 разделам (нужно 2–5 минут).",
            reply_markup=builder.as_markup(),
        )
    else:
        await message.answer(
            "Для полной ИИ-расшифровки добавьте <code>OPENAI_API_KEY</code> в настройки бота.",
        )


@router.callback_query(F.data.startswith("interpret:"))
async def on_interpret(callback: CallbackQuery, ai: AiInterpreter) -> None:
    if not ai.enabled:
        await callback.answer("ИИ не настроен", show_alert=True)
        return

    user_id = callback.from_user.id if callback.from_user else 0
    pending = _pending_interpret.get(user_id)
    if not pending:
        await callback.answer("Данные устарели. Постройте карту заново.", show_alert=True)
        return

    await callback.answer()
    status = await callback.message.answer("⏳ Готовлю расшифровку… это может занять несколько минут.")

    try:
        text = await ai.interpret(pending["name"], pending["summary_plain"])
    except Exception as exc:
        logger.exception("AI interpret failed")
        await status.edit_text(f"Не удалось получить расшифровку: {exc}")
        return

    chunk_size = 4000
    parts = [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)] or ["(пусто)"]
    await status.delete()
    for idx, part in enumerate(parts):
        prefix = f"<b>Расшифровка ({idx + 1}/{len(parts)})</b>\n\n" if len(parts) > 1 else ""
        await callback.message.answer(prefix + part)
