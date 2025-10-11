from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard():
    """Клавиатура для главного табло"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Обновить курс", callback_data="update_rate"),
            InlineKeyboardButton(text="📊 Зафиксировать", callback_data="fix_rate")
        ]
    ])
