import logging
from aiogram import Router
from app.filters.superusers import SuperuserFilter
from app.config.main import BotConfig

logger = logging.getLogger(__name__)

def setup_superuser(router: Router, config: BotConfig):  # Убрал async
    """Настройка суперпользовательских обработчиков"""
    try:
        logger.info("🔧 Setting up superuser handlers...")

        # Создаем фильтр с superusers
        superuser_filter = SuperuserFilter(superusers=config.superusers)

        logger.info(f"🔍 Superusers list: {config.superusers}")

        # УБЕРИТЕ все @SuperuserFilter() без аргументов!
        # Вместо этого используйте superuser_filter в регистрации обработчиков

        # Пример правильной регистрации:
        # router.message.register(your_admin_handler, superuser_filter, Command("admin_command"))

        logger.info("✅ Superuser handlers setup completed")

    except Exception as e:
        logger.error(f"❌ Superuser setup error: {e}")
        raise