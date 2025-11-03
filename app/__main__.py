import logging
import os
from pathlib import Path

from aiogram import Dispatcher, Bot
from sqlalchemy.orm import close_all_sessions
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import load_config
from app.config.logging_config import setup_logging
from app.handlers import setup_handlers
#from app.middlewares import setup_middlewares
from app.models.config.main import Paths
from app.models.db import create_pool
# from aiogram.client.default import DefaultBotProperties
from app.middlewares.simple_chain import SimpleConfigMiddleware, SimpleDbMiddleware
from app.services.parser_service import ParserService

logger = logging.getLogger(__name__)


def main():
    paths = get_paths()

    setup_logging(paths)
    config = load_config(paths)

    dp = Dispatcher()
    pool = create_pool(config.db)
    dp.update.middleware(SimpleConfigMiddleware(config.bot))
    dp.update.middleware(SimpleDbMiddleware(pool))
    setup_handlers(dp, config.bot)
    #setup_middlewares(dp, create_pool(config.db), config.bot)
    bot = Bot(
        token=config.bot.token,
        
        session=config.bot.create_session(),
    )

    # Создаем планировщик
    scheduler = AsyncIOScheduler()

    async def update_auto_rates():
        """Фоновая задача обновления курсов"""
        try:
            async with pool() as session:
                parser_service = ParserService(session)
                await parser_service.update_all_auto_rates()
        except Exception as e:
            logger.error(f"❌ Ошибка фоновой задачи обновления курсов: {e}", exc_info=True)

    async def on_startup():
        # Регистрируем задачу и запускаем планировщик, когда цикл уже запущен
        scheduler.add_job(
            update_auto_rates,
            trigger=CronTrigger(minute=0, hour='9-21'),  # Каждый час с 9 до 21
            id='update_auto_rates',
            replace_existing=True
        )
        scheduler.start()
        logger.info("✅ Планировщик задач запущен (обновление курсов каждый час с 9:00 до 21:00)")

    async def on_shutdown():
        try:
            scheduler.shutdown()
        except Exception:
            pass

    # Регистрируем хуки старта/остановки (aiogram сам await-ит async callbacks)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info("started")
    try:
        dp.run_polling(bot)
    finally:
        close_all_sessions()
        logger.info("stopped")


def get_paths() -> Paths:
    if path := os.getenv("BOT_PATH"):
        return Paths(Path(path))
    return Paths(Path(__file__).parent.parent)


if __name__ == '__main__':
    main()
