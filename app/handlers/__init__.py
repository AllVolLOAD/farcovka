import logging
import traceback
from aiogram import Dispatcher
from app.handlers.base import setup_base
from app.handlers.errors import setup_errors
from app.models.config.main import BotConfig
from app.handlers.admin_handlers import setup_admin_handlers


logger = logging.getLogger(__name__)


def setup_handlers(dp: Dispatcher, bot_config: BotConfig):
    logger.info("🔄 Setting up handlers...")

    # Сначала пробуем superuser
    try:
        from app.handlers.superuser import setup_superuser
        logger.info("✅ Superuser module imported")
        setup_superuser(dp, bot_config)
    except Exception as e:
        logger.error(f"❌ SUPERUSER ERROR: {e}")
        logger.error(f"🔍 TRACEBACK:\n{traceback.format_exc()}")

    # Затем наш table router
    try:
        from app.handlers.table_handlers import get_table_router
        table_router = get_table_router()
        dp.include_router(table_router)
        logger.info("✅ Table router registered")
    except Exception as e:
        logger.error(f"❌ TABLE ROUTER ERROR: {e}")

    # Базовые handlers
    setup_errors(dp, bot_config.log_chat)
    setup_base(dp)
    setup_admin_handlers(dp)

    logger.debug("handlers configured successfully")