from aiogram import Router, types
from aiogram.filters import Command
from app.filters.superusers import SuperuserFilter

router = Router()
router.message.filter(SuperuserFilter())


@router.message(Command("stats"))
async def show_stats(message: types.Message):
    """Показать статистику"""
    # Базовая реализация
    stats_text = "📊 Статистика:\n\n"
    stats_text += "👥 Пользователей: 0\n"
    stats_text += "💬 Чатов: 0\n"
    stats_text += "📋 Записей в очереди: 0\n"
    stats_text += "⚡ Активных сессий: 0"

    await message.answer(stats_text)
