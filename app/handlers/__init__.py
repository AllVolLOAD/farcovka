import logging
import traceback
from aiogram import Dispatcher
from app.handlers.base import setup_base
from app.handlers.errors import setup_errors
from app.models.config.main import Config

logger = logging.getLogger(__name__)

def setup_handlers(dp: Dispatcher, config: Config):
    logger.info("🔄 Setting up handlers...")

    # 1. Superuser
    try:
        from app.handlers.superuser import setup_superuser
        setup_superuser(dp, config.bot)
    except Exception as e:
        logger.error(f"❌ SUPERUSER ERROR: {e}")
        traceback.print_exc()

    # 2. Table router
    try:
        from app.handlers.table_handlers import router as table_router
        dp.include_router(table_router)
    except Exception as e:
        logger.error(f"❌ TABLE ROUTER ERROR: {e}")
        traceback.print_exc()

    # 3. Admin handlers
    try:
        from app.handlers.admin_handlers import setup_admin_handlers
        setup_admin_handlers(dp)
    except Exception as e:
        logger.error(f"❌ ADMIN HANDLERS ERROR: {e}")
        traceback.print_exc()

    # 4. Базовые handlers
    setup_errors(dp, config.bot.log_chat)  # Добавил log_chat
    setup_base(dp)

    logger.debug("handlers configured successfully")