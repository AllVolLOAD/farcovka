import logging
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config.main import BotConfig

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, bot, session):
        self.bot = bot
        self.session = session

    async def notify_queue_users_rate_updated(self, new_rates_message: str):
        """Уведомляет всех пользователей в очереди об обновлении курса"""
        try:
            from app.services.queue_service import QueueService
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

            queue_service = QueueService(self.session)
            queue_users = await queue_service.get_queue_users()

            logger.info("Отправка уведомлений %d пользователям в очереди", len(queue_users))

            # Создаем клавиатуру с кнопкой обновления
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Обновить табло", callback_data="refresh_table")]
            ])

            for user_id in queue_users:
                try:
                    # Отправляем обновленное табло с кнопкой
                    await self.bot.send_message(
                        chat_id=user_id,
                        text=new_rates_message,                        reply_markup=keyboard,
                        parse_mode="Markdown"
                    )
                    logger.info("✅ Уведомление отправлено пользователю %s", user_id)

                except Exception as e:
                    logger.error("❌ Ошибка отправки пользователю %s: %s", user_id, e)

            # Очищаем очередь после уведомления
            await queue_service.clear_queue()
            logger.info("✅ Очередь очищена")

        except Exception as e:
            logger.error("❌ Ошибка уведомления очереди: %s", e)


    async def notify_admins_queue_full(self, session: AsyncSession):
        """Уведомляем админов с текущими курсами"""
        try:
            from app.services.queue_service import QueueService
            from app.services.multi_rate_service import MultiRateService

            queue_service = QueueService(session)
            multi_service = MultiRateService(session)

            queue_size = await queue_service.get_queue_size()
            if queue_size < 3:
                return False

            waiting_users = await queue_service.get_waiting_users()

            # Получаем актуальные курсы
            current_rates = await multi_service.get_all_rates()
            rates_text = "\n".join([f"{pair}: {rate}" for pair, rate in
                                    current_rates.items()]) if current_rates else "Курсы не установлены"

            users_list = "\n".join([f"• {user.username or 'Без username'}" for user in waiting_users[:3]])

            message_text = (
                "🚨 <b>Очередь на обновление курсов заполнена!</b>\n\n"
                f"<b>Текущие курсы:</b>\n{rates_text}\n\n"
                f"<b>Запросы:</b> {len(waiting_users)} пользователей\n"
                f"<b>Пользователи:</b>\n{users_list}\n\n"
                "💵 <b>Обновите курсы командами:</b>\n"
                "<code>/rate_now RUB/USD 95.50</code>\n"
                "<code>/rate_now USD/USDT 0.996</code>\n\n"
                "⚡ <b>Или просто введите число</b> для обновления основного курса"
            )

            admin_ids = [7111883883, 780245577]

            for admin_id in admin_ids:
                try:
                    await self.bot.send_message(admin_id, message_text, parse_mode="HTML")
                    logger.info(f"✅ Уведомление отправлено админу {admin_id}")
                except Exception as e:
                    logger.error(f"❌ Ошибка отправки админу {admin_id}: {e}")

            return True

        except Exception as e:
            logger.error(f"❌ Ошибка уведомления админов: {e}")
            return False


    async def notify_users_rate_updated(self, new_rate: float):
        """Уведомляет всех пользователей об обновлении курса"""
        # TODO: Реализуем позже
        pass