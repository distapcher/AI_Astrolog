from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from bot.config import Settings
from bot.keyboards import SHOW_NATAL_DATA_CALLBACK, after_analysis_kb
from bot.services.ai_interpreter import AiInterpreter
from bot.services.astrologer_api import AstrologerClient
from bot.services.chart_image import ChartImageError, svg_to_png_bytes
from bot.services.geocoding import (
    parse_birth_date,
    parse_birth_time,
    resolve_place,
    resolve_place_with_geonames,
)
from bot.services.kerykeion_chart import NatalInput
from bot.services.messaging import send_long_text
from bot.services.natal_bundle import (
    NatalChartBundle,
    build_natal_bundle,
    bundle_plain_text_for_ai,
    bundle_report_messages,
)
from bot.services.natal_store import load_natal_profile, save_natal_profile
from bot.states import NatalChartStates

logger = logging.getLogger(__name__)
router = Router()

_bundle_cache: dict[int, NatalChartBundle] = {}


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


async def _send_natal_chart_png(message: Message, bundle: NatalChartBundle, astrologer: AstrologerClient) -> None:
    svg_content = bundle.svg_content

    if not svg_content and bundle.local_chart:
        try:
            svg_path = await astrologer.save_chart_svg_fallback(bundle.natal, bundle.local_chart)
            if svg_path and svg_path.exists():
                svg_content = svg_path.read_text(encoding="utf-8")
        except Exception:
            logger.exception("Local SVG render failed")

    if svg_content:
        try:
            png_bytes = svg_to_png_bytes(svg_content)
            photo = BufferedInputFile(png_bytes, filename="natal_chart.png")
            await message.answer_photo(photo, caption="🎴 Натальная карта")
        except ChartImageError as exc:
            logger.warning("SVG to PNG failed: %s", exc)
            await message.answer(
                "<i>Не удалось подготовить изображение карты. Ниже — расчётные данные.</i>"
            )
        except Exception:
            logger.exception("SVG to PNG failed")
            await message.answer(
                "<i>Не удалось подготовить изображение карты. Ниже — расчётные данные.</i>"
            )
    else:
        await message.answer(
            "<i>Карта недоступна. Ниже — все расчётные данные.</i>"
        )


async def _send_natal_data(message: Message, bundle: NatalChartBundle, astrologer: AstrologerClient) -> None:
    await _send_natal_chart_png(message, bundle, astrologer)

    report_messages = bundle_report_messages(bundle)
    for idx, part in enumerate(report_messages):
        prefix = f"<b>Натальные данные ({idx + 1}/{len(report_messages)})</b>\n\n" if len(report_messages) > 1 else ""
        await message.answer(prefix + part)


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

    user_id = message.from_user.id if message.from_user else 0
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
        bundle = await build_natal_bundle(natal, astrologer)
    except RuntimeError as exc:
        await wait_msg.edit_text(str(exc))
        return

    if user_id:
        _bundle_cache[user_id] = bundle
        save_natal_profile(user_id, natal, settings.natal_db_path)

    chart_text = bundle_plain_text_for_ai(bundle)

    try:
        await wait_msg.edit_text(
            "⏳ Расчет карты произведен. Запущен процесс анализа личности…"
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
    await message.answer(
        "Натальная карта и технические данные (планеты, аспекты, паттерны) "
        "можно открыть по кнопке ниже.",
        reply_markup=after_analysis_kb(),
    )


@router.callback_query(F.data == SHOW_NATAL_DATA_CALLBACK)
async def on_show_natal_data(
    callback: CallbackQuery,
    astrologer: AstrologerClient,
    settings: Settings,
) -> None:
    user_id = callback.from_user.id if callback.from_user else 0
    if not user_id:
        await callback.answer("Не удалось определить пользователя.", show_alert=True)
        return

    natal = load_natal_profile(user_id, settings.natal_db_path)
    if not natal:
        await callback.answer(
            "Сначала пройдите «🔮 Анализ личности».",
            show_alert=True,
        )
        return

    await callback.answer()
    status = await callback.message.answer("⏳ Рассчитываю и открываю натальные данные…")

    try:
        bundle = await build_natal_bundle(natal, astrologer)
        _bundle_cache[user_id] = bundle
    except RuntimeError as exc:
        await status.edit_text(str(exc))
        return
    except Exception as exc:
        logger.exception("Show natal data failed")
        await status.edit_text(f"Не удалось показать данные: {exc}")
        return

    try:
        await _send_natal_data(callback.message, bundle, astrologer)
    except Exception as exc:
        logger.exception("Send natal data failed")
        await status.edit_text(f"Не удалось показать данные: {exc}")
        return

    await status.delete()
