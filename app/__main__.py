import logging
import os
import asyncio
from pathlib import Path
from aiogram import Dispatcher, Bot
from sqlalchemy.orm import close_all_sessions
from app.config.main import load_config
from app.config.logging_config import setup_logging
from app.handlers import setup_handlers
from app.models.config.main import Paths
from app.models.db import create_pool
from aiogram.client.default import DefaultBotProperties
from app.middlewares.simple_chain import SimpleConfigMiddleware, SimpleDbMiddleware
from app.middlewares.services_middleware import ServicesMiddleware
from app.services.rapira_parser_service import RapiraParserService
from app.services.scheduler_service import SchedulerService
from app.services.rbc_cash_service import RbcCashParserService  # Убрал дублирование

logger = logging.getLogger(__name__)


async def init_services(session_pool, config):
    """Инициализация сервисов"""
    # Инициализация парсера RAPIRA
    rapira_parser_service = RapiraParserService(session_pool)

    # Инициализация парсера RBC Cash
    rbc_cash_parser_service = RbcCashParserService(session_pool)

    # Инициализация планировщика
    scheduler_service = SchedulerService()

    # Добавляем задание для парсера RAPIRA
    scheduler_service.add_job(
        rapira_parser_service.update_rapira_rates,
        'interval',
        hours=1,
        id='rapira_parser'
    )

    # Добавляем задание для парсера RBC Cash
    scheduler_service.add_job(
        rbc_cash_parser_service.update_rbc_cash_rates,
        'interval',
        hours=1,
        id='rbc_cash_parser'
    )

    # Запускаем планировщик
    scheduler_service.start()

    logger.info("✅ Планировщики инициализированы: RAPIRA и RBC Cash")

    return rapira_parser_service, rbc_cash_parser_service, scheduler_service


async def main_async():
    paths = get_paths()

    setup_logging(paths)
    config = load_config(paths)

    dp = Dispatcher()
    dp.update.middleware(SimpleConfigMiddleware(config.bot))

    # Создаем пул сессий
    session_pool = create_pool(config.db)
    dp.update.middleware(SimpleDbMiddleware(session_pool))
    dp.update.middleware(ServicesMiddleware(session_pool))

    setup_handlers(dp, config)

    bot = Bot(
        token=config.bot.token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )

    # Инициализируем сервисы
    rapira_parser_service, rbc_cash_parser_service, scheduler_service = await init_services(session_pool, config)

    logger.info("started")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Polling error: {e}")
    finally:
        # Корректно останавливаем планировщик
        try:
            scheduler_service.shutdown()
        except Exception as e:
            logger.error(f"Error shutting down scheduler: {e}")

        close_all_sessions()
        logger.info("stopped")


def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Application error: {e}")


def get_paths() -> Paths:
    if path := os.getenv("BOT_PATH"):
        return Paths(Path(path))
    return Paths(Path(__file__).parent.parent)


if __name__ == '__main__':
    main()