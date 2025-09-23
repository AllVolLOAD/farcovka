import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def is_admin(user_id: int) -> bool:
    """Проверяем что пользователь админ"""
    admin_ids = [7111883883, 780245577]  # хардкод
    return user_id in admin_ids


def setup_admin_handlers(dp):
    admin_router = Router()

    @admin_router.message(Command("admin_test"))
    async def admin_test(message: Message):
        """Тестовая команда"""
        logger.info(f"🎯 ADMIN_TEST от {message.from_user.id}")
        await message.answer("✅ Admin handlers работают!")

    @admin_router.message(F.text)
    async def handle_admin_messages(message: Message, session: AsyncSession):
        """Обрабатываем сообщения от админов"""
        if not is_admin(message.from_user.id):
            return

        text = message.text.strip()
        logger.info(f"📨 Сообщение от админа {message.from_user.id}: '{text}'")

        # Проверяем что это число (курс)
        if text.replace('.', '').isdigit():
            try:
                new_rate = float(text)
                logger.info(f"💰 Админ ввел курс: {new_rate}")

                # TODO: Добавить логику обновления курса и очистки очереди
                await message.answer(f"✅ Курс принят: {new_rate} RUB (функция в разработке)")

            except ValueError:
                await message.answer("❌ Введите число, например: 95.50")
        else:
            logger.info(f"ℹ️ Нечисловое сообщение от админа: {text}")

    dp.include_router(admin_router)
    logger.info("✅ Admin handlers registered")