from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot.keyboards import main_menu_kb

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Привет! Я <b>ИИ-астролог</b>.\n\n"
        "Построю натальную карту по дате, времени и месту рождения:\n"
        "• расчёт планет и аспектов — <b>Kerykeion</b>\n"
        "• визуальная карта — <b>Astrologer API</b>\n\n"
        "Нажмите «🌟 Натальная карта» или отправьте /chart",
        reply_markup=main_menu_kb(),
    )


@router.message(Command("help"))
@router.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: Message) -> None:
    await message.answer(
        "<b>Как пользоваться</b>\n\n"
        "1. /chart — начать расчёт\n"
        "2. Введите имя (или «—» без имени)\n"
        "3. Дата: <code>ДД.ММ.ГГГГ</code>\n"
        "4. Время: <code>ЧЧ:ММ</code> (местное время рождения)\n"
        "5. Город: <code>Москва</code>\n"
        "6. Страна (код ISO): <code>RU</code> — можно Enter для RU\n\n"
        "<i>Время указывайте по месту рождения, не по UTC.</i>",
        reply_markup=main_menu_kb(),
    )
