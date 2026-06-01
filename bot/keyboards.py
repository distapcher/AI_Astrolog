from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

SHOW_NATAL_DATA_CALLBACK = "show_natal_data"


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔮 Анализ личности")],
            [KeyboardButton(text="ℹ️ Помощь")],
        ],
        resize_keyboard=True,
    )


def after_analysis_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 Показать натальные данные",
                    callback_data=SHOW_NATAL_DATA_CALLBACK,
                )
            ],
        ]
    )


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
