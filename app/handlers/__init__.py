import logging
import traceback
from aiogram import Dispatcher
from app.handlers.base import setup_base
from app.handlers.errors import setup_errors
from app.models.config.main import BotConfig

logger = logging.getLogger(__name__)

def setup_handlers(dp: Dispatcher, bot_config: BotConfig):
    logger.info("🔄 Setting up handlers...")

    # 1. Superuser
    try:
        from app.handlers.superuser import setup_superuser
        setup_superuser(dp, bot_config)
    except Exception as e:
        logger.error(f"❌ SUPERUSER ERROR: {e}")

    # 2. Table router
    try:
        from app.handlers.table_handlers import router as table_router
        dp.include_router(table_router)
    except Exception as e:
        logger.error(f"❌ TABLE ROUTER ERROR: {e}")

    # 3. Admin handlers (ТОЛЬКО ОДИН РАЗ!)
    try:
        from app.handlers.admin_handlers import setup_admin_handlers
        setup_admin_handlers(dp)
    except Exception as e:
        logger.error(f"❌ ADMIN HANDLERS ERROR: {e}")

    # 4. Базовые handlers
    setup_errors(dp, bot_config.log_chat)
    setup_base(dp)

    logger.debug("handlers configured successfully")
