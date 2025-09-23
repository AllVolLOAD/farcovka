import logging
import traceback
from aiogram import Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message
from app.models.config.main import BotConfig

logger = logging.getLogger(__name__)


def setup_superuser(dp: Dispatcher, bot_config: BotConfig):
    logger.info("🔧 Setting up superuser handlers...")

    try:
        logger.info(f"🔍 Bot config type: {type(bot_config)}")
        logger.info(f"🔍 Bot config attributes: {[attr for attr in dir(bot_config) if not attr.startswith('_')]}")

        superusers = getattr(bot_config, 'superusers', None)
        logger.info(f"🔍 Superusers from bot_config: {superusers} (type: {type(superusers)})")

        if superusers is None and hasattr(bot_config, 'bot'):
            superusers = getattr(bot_config.bot, 'superusers', None)
            logger.info(f"🔍 Superusers from bot_config.bot: {superusers}")

        from app.filters.superusers import IsSuperuser
        logger.info("✅ IsSuperuser imported successfully")

        router = Router(name=__name__)

        @router.message(Command("superuser_test"))
        async def superuser_test(message: Message):
            await message.answer(f"🔧 Superuser test OK! Your ID: {message.from_user.id}")

        dp.include_router(router)
        logger.info("✅ Superuser handlers setup completed")

    except Exception as e:
        logger.error(f"❌ SUPERUSER SETUP ERROR: {e}")
        logger.error(f"🔍 FULL TRACEBACK:\n{traceback.format_exc()}")
        raise