from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot.keyboards import main_menu_kb
from bot.services.ai_interpreter import AiInterpreter

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Привет! Я <b>ИИ-астролог</b>.\n\n"
        "После ввода даты, времени и места рождения подготовлю "
        "<b>описание личности и профессионального предназначения</b> "
        "по натальной карте (10 разделов: миссия, таланты, карьера, финансы и др.).\n\n"
        "Нажмите «🔮 Анализ личности» или отправьте /chart",
        reply_markup=main_menu_kb(),
    )


@router.message(Command("help"))
@router.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: Message, ai: AiInterpreter) -> None:
    ai_note = (
        "ИИ подключён — анализ доступен."
        if ai.enabled
        else "⚠️ ИИ не настроен — анализ недоступен."
    )
    await message.answer(
        "<b>Как пользоваться</b>\n\n"
        "1. /chart — начать анализ\n"
        "2. Имя (или «—»)\n"
        "3. Дата: <code>ДД.ММ.ГГГГ</code>\n"
        "4. Время: <code>ЧЧ:ММ</code> (местное время рождения)\n"
        "5. Город: <code>Москва</code>\n"
        "6. Страна: <code>RU</code> (или «—» для России)\n\n"
        "Бот рассчитает карту и сразу выдаст текстовое описание — "
        "без таблиц планет и SVG.\n\n"
        f"{ai_note}\n\n"
        "<i>Время указывайте по месту рождения, не по UTC.</i>",
        reply_markup=main_menu_kb(),
    )
