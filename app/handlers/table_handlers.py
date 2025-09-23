import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.config.main import BotConfig
from app.services.rate_service import RateService
from app.keyboards.main_menu import get_main_keyboard

logger = logging.getLogger(__name__)


# Роутер создается при вызове функции
def get_table_router():
    router = Router(name="table_router")

    @router.message(Command("start"))
    async def table_start(message: Message, session: AsyncSession, config: BotConfig):
        logger.info(f"🎯 TABLE START from user {message.from_user.id}")
        try:
            rate_service = RateService(session)
            message_text = await rate_service.format_rate_message()
            await message.answer(message_text, reply_markup=get_main_keyboard())
        except Exception as e:
            logger.error(f"❌ Ошибка БД: {e}")
            await message.answer("🏦 Текущий курс: 95.50 RUB\n\n(режим без БД)", reply_markup=get_main_keyboard())

    @router.callback_query(F.data == "update_rate")
    async def table_update_rate(
            callback: CallbackQuery,
            session: AsyncSession,
            config: BotConfig
    ):
        """Обработчик кнопки 'Обновить курс' с уведомлениями"""
        try:
            from app.services.queue_service import QueueService
            from app.services.notification_service import NotificationService

            queue_service = QueueService(session)
            notification_service = NotificationService(callback.bot, config)

            username = callback.from_user.username or callback.from_user.full_name
            success, queue_size = await queue_service.add_to_queue(
                callback.from_user.id,
                username
            )

            if success:
                # Проверяем нужно ли уведомлять админов
                await notification_service.notify_admins_queue_full()

                if queue_size >= 3:
                    await callback.answer(
                        f"✅ Очередь заполнена! Администратор осознает факт, что вы не один ждете",
                        show_alert=True
                    )
                else:
                    await callback.answer(
                        f"✅ Вы в очереди! Ожидающих: {queue_size}/3",
                        show_alert=True
                    )
            else:
                await callback.answer(
                    "⚠️ Вы уже в очереди! Ожидайте обновления",
                    show_alert=True
                )


        except Exception as e:

            logger.error(f"Ошибка очереди: {e}")

            try:

                await callback.message.answer("🔄 Ошибка системы, попробуйте позже")

            except:

                pass


    @router.callback_query(F.data == "fix_rate")
    async def table_fix_rate(callback: CallbackQuery, session: AsyncSession):
        await callback.answer("📊 Курс зафиксирован!", show_alert=True)

    @router.message(Command("debug_config"))
    async def debug_config(message: Message, config: BotConfig):
        """Показывает текущую конфигурацию"""
        superusers = getattr(config, 'superusers', [])
        await message.answer(
            f"🔧 <b>Конфигурация бота:</b>\n"
            f"👑 Суперпользователи: {superusers}\n"
            f"📊 Тип: {type(superusers)}",
            parse_mode="HTML"
        )

    @router.message(Command("myid"))
    async def get_my_id(message: Message):
        """Команда для получения своего ID"""
        await message.answer(
            f"🆔 Ваш Telegram ID: <code>{message.from_user.id}</code>\n"
            f"📛 Username: @{message.from_user.username or 'нет'}\n"
            f"👤 Имя: {message.from_user.full_name}",
            parse_mode="HTML"
        )

    @router.message(Command("admin_info"))
    async def admin_info(message: Message, config: BotConfig):
        """Показывает информацию о админах"""
        superusers = getattr(config, 'superusers', 'Не найдено')
        await message.answer(
            f"👑 Superusers: {superusers}\n"
            f"🆔 Твой ID: {message.from_user.id}",
            parse_mode="HTML"
        )

    return router