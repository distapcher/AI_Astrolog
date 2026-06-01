from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot.keyboards import main_menu_kb
from bot.services.ai_interpreter import AiInterpreter

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Привет! Я <b>Космический Астролог нового времени</b>.\n\n"
        "Я работаю на стыке всех современных технологий анализа и интерпретации данных.\n"
        "Моя задача — помочь тебе увидеть глобальную картину твоего существования.\n"
        "Осветить направления и пути, которые наполнят тебя Целостностью и, как следствие, — Счастьем.\n"
        "Это позволит тебе взглянуть шире на свою Личность и увидеть её масштаб.\n\n"
        "Нажми «🔮 Анализ личности» для запуска.",
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
        "Сначала — текстовое описание личности и предназначения. "
        "Кнопка «Показать натальные данные» откроет карту, планеты и аспекты.\n\n"
        f"{ai_note}\n\n"
        "<i>Время указывайте по месту рождения, не по UTC.</i>",
        reply_markup=main_menu_kb(),
    )
