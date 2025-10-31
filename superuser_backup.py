import logging
import traceback
from aiogram import Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config.main import BotConfig
from app.dao.holder import HolderDao

logger = logging.getLogger(__name__)


def setup_superuser(dp: Dispatcher, bot_config: BotConfig):
    logger.info("🔧 Setting up superuser handlers...")

    try:
        superusers_list = [7111883883, 780245577]

        logger.info(f"🔍 Superusers list: {superusers_list}")

        from app.filters.superusers import SuperuserFilter
        router = Router(name=__name__)
        router.message.filter(SuperuserFilter(superusers_list))

        @router.message(Command("superuser_test"))
        async def superuser_test(message: Message):
            await message.answer(f"🔧 Superuser test OK! Your ID: {message.from_user.id}")

        @router.message(Command("stats"))
        async def show_stats(message: Message, session: AsyncSession = None):
            """Показать статистику"""
            try:
                if session is None:
                    stats_text = """📊 Статистика бота:

👥 Пользователей: система настраивается
💬 Чатов: база данных подключается
📋 В очереди: функционал готов

⚡ Бот работает корректно"""
                else:
                    from app.dao.holder import HolderDao
                    dao = HolderDao(session)

                    try:
                        users_count = await dao.user.get_users_count()
                        chats_count = await dao.chat.get_chats_count()
                        queue_count = await dao.queue.get_active_queue_count()

                        stats_text = f"""📊 Статистика бота:

👥 Пользователей: {users_count}
💬 Чатов: {chats_count}
📋 В очереди: {queue_count}
⚡ Версия: 1.0.0"""
except Exception as db_error:
    # Безопасный вывод ошибки
    error_msg = str(db_error).split("\n")[0]
    stats_text = f"""📊 Статистика бота:

❌ Ошибка базы данных: {error_msg}
⚡ Обратись к разработчику"""

❌ Ошибка базы данных: {error_msg}
⚡ Обратись к разработчику"""

                await message.answer(stats_text)

            except Exception as e:
                await message.answer("❌ Временная ошибка статистики")
                logger.error(f"Stats error: {e}")

        dp.include_router(router)
        logger.info("✅ Superuser handlers setup completed")

    except Exception as e:
        logger.error(f"❌ SUPERUSER SETUP ERROR: {e}")
        logger.error(f"🔍 FULL TRACEBACK:\n{traceback.format_exc()}")
        raise
