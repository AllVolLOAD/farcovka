import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.config.main import BotConfig
from app.services.rate_service import RateService
from app.keyboards.main_menu import get_main_keyboard

logger = logging.getLogger(__name__)

# Создаем роутер
router = Router()
user_last_table_message = {}

user_last_table_message = {}


@router.message(Command("start"))
async def table_start(message: Message, session: AsyncSession, config: BotConfig):
    """Показывает/обновляет табло"""
    try:
        rate_service = RateService(session)
        message_text = await rate_service.format_rate_message()

        user_id = message.from_user.id

        # Если есть предыдущее табло - редактируем его
        if user_id in user_last_table_message:
            try:
                await message.bot.edit_message_text(
                    chat_id=user_id,
                    message_id=user_last_table_message[user_id],
                    text=message_text,
                    reply_markup=get_main_keyboard(),
                    parse_mode="HTML"
                )
                logger.info(f"✏️ Табло отредактировано для пользователя {user_id}")
                return
            except Exception as e:
                # Если редактирование не удалось, удаляем из кэша
                del user_last_table_message[user_id]
                logger.warning(f"⚠️ Не удалось отредактировать табло: {e}")

        # Отправляем новое сообщение
        new_message = await message.answer(
            message_text,
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
        user_last_table_message[user_id] = new_message.message_id
        logger.info(f"📄 Новое табло создано для пользователя {user_id}")

    except Exception as e:
        logger.error(f"❌ Ошибка табло: {e}")
@router.callback_query(F.data == "update_rate")
async def update_rate_handler(callback: CallbackQuery, session: AsyncSession, config: BotConfig):
    """Обработчик кнопки 'Обновить курс'"""
    try:
        from app.services.queue_service import QueueService
        from app.services.notification_service import NotificationService

        queue_service = QueueService(session)
        notification_service = NotificationService(callback.bot, config)

        username = callback.from_user.username or callback.from_user.full_name
        success, queue_size = await queue_service.add_to_queue(callback.from_user.id, username)

        if success:
            await notification_service.notify_admins_queue_full()

            if queue_size >= 3:
                message = "✅ Очередь заполнена! Админ уведомлен"
            else:
                message = f"✅ Вы в очереди! Ожидающих: {queue_size}/3"
        else:
            message = "⚠️ Вы уже в очереди!"

        await callback.answer(message, show_alert=True)

    except Exception as e:
        logger.error(f"Ошибка очереди: {e}")
        await callback.answer("🔄 Ошибка системы", show_alert=True)


@router.callback_query(F.data == "fix_rate")
async def fix_rate_handler(callback: CallbackQuery):
    """Обработчик кнопки 'Зафиксировать'"""
    await callback.answer("📊 Функция скоро будет доступна!", show_alert=True)