from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard():
    """Инлайн-клавиатура для главного табло"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Обновить курс", callback_data="update_rate"),
            InlineKeyboardButton(text="📊 Зафиксировать", callback_data="fix_rate")
        ]
    ])

def get_main_reply_keyboard():
    """Reply-клавиатура для главного меню (всегда доступна)"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text='💰 Кошелек'),
                KeyboardButton(text='🏦 Табло')
            ],
            [
                KeyboardButton(text='🔁 П2П'),
                KeyboardButton(text='⚙️ Настройки')
            ]
        ],
        resize_keyboard=True,
        input_field_placeholder='Выберите раздел...'
    )