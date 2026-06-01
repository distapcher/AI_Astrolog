from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.config import Settings
from bot.services.ai_interpreter import AiInterpreter
from bot.services.astrologer_api import AstrologerClient
from bot.services.chart_report import NatalReportData, build_natal_report, report_to_plain_text
from bot.services.geocoding import (
    parse_birth_date,
    parse_birth_time,
    resolve_place,
    resolve_place_with_geonames,
)
from bot.services.kerykeion_chart import NatalInput, chart_data_as_dict, compute_natal_chart
from bot.services.messaging import send_long_text
from bot.states import NatalChartStates

logger = logging.getLogger(__name__)
router = Router()


async def _start_chart_flow(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(NatalChartStates.name)
    await message.answer(
        "Введите <b>имя</b> для анализа (или «—», если без имени):",
    )


@router.message(Command("chart"))
@router.message(F.text.in_({"🌟 Натальная карта", "🔮 Анализ личности"}))
async def start_chart(message: Message, state: FSMContext, ai: AiInterpreter) -> None:
    if not ai.enabled:
        await message.answer(
            "Сервис анализа временно недоступен: не настроен <code>OPENAI_API_KEY</code>."
        )
        return
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


async def _gather_chart_text(
    natal: NatalInput,
    astrologer: AstrologerClient,
) -> str:
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
    if chart_data_dict and hasattr(chart_data_dict, "model_dump"):
        chart_data_dict = chart_data_dict.model_dump()
    elif local_chart:
        chart_data_dict = chart_data_as_dict(local_chart)
    else:
        raise RuntimeError("Не удалось рассчитать натальную карту.")

    report_data = NatalReportData(
        chart_data=chart_data_dict,
        moon_phase=api_pkg.get("moon_phase"),
        transit_aspects=api_pkg.get("transit_aspects"),
    )
    return report_to_plain_text(build_natal_report(natal, report_data))


@router.message(NatalChartStates.birth_nation)
async def on_birth_nation(
    message: Message,
    state: FSMContext,
    astrologer: AstrologerClient,
    ai: AiInterpreter,
    settings: Settings,
) -> None:
    if not ai.enabled:
        await message.answer("ИИ-анализ недоступен: не настроен API ключ.")
        return

    nation_raw = (message.text or "").strip()
    nation = "RU" if nation_raw in {"", "—", "-", "ru", "RU"} else nation_raw
    data = await state.get_data()
    await state.clear()

    wait_msg = await message.answer(
        "⏳ Рассчитываю карту и готовлю <b>описание личности и предназначения</b>…\n"
        "<i>Это займёт 3–7 минут.</i>"
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

    try:
        chart_text = await _gather_chart_text(natal, astrologer)
    except RuntimeError as exc:
        await wait_msg.edit_text(str(exc))
        return

    try:
        await wait_msg.edit_text(
            "⏳ Карта рассчитана. ИИ пишет описание по 10 разделам…\n"
            "<i>Ещё 2–5 минут.</i>"
        )
        personality_text = await ai.interpret_personality(natal.name, chart_text)
    except Exception as exc:
        logger.exception("AI personality analysis failed")
        await wait_msg.edit_text(f"Не удалось получить описание: {exc}")
        return

    await wait_msg.delete()
    await message.answer(
        f"<b>Описание личности и предназначения — {natal.name}</b>\n"
        f"📅 {natal.day:02d}.{natal.month:02d}.{natal.year}, "
        f"{natal.hour:02d}:{natal.minute:02d} · {natal.location.display_name}"
    )
    await send_long_text(message, personality_text, title="Анализ")
