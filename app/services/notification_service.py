import logging
from aiogram import Bot
from app.models.config.main import BotConfig

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, bot: Bot, config: BotConfig):
        self.bot = bot
        self.config = config

    async def notify_admins_queue_full(self):
        """Упрощенная версия - только уведомления"""
        try:
            message_text = (
                "🚨 <b>Очередь на обновление курса заполнена!</b>\n\n"
                "💵 <b>Введите новый курс командой:</b> /rate 95.50\n\n"
                "Примеры:\n"
                "<code>/rate 95.50</code>\n"
                "<code>/rate 102.75</code>"
            )

            admin_ids = [7111883883, 780245577]

            for admin_id in admin_ids:
                try:
                    await self.bot.send_message(
                        admin_id,
                        message_text,
                        parse_mode="HTML"
                    )
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