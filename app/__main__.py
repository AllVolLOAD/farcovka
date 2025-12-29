import logging
import os
from pathlib import Path
import asyncio

from aiogram import Dispatcher, Bot
from sqlalchemy.orm import close_all_sessions
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import uvicorn

from app.config import load_config
from app.config.logging_config import setup_logging
from app.handlers import setup_handlers
#from app.middlewares import setup_middlewares
from app.models.config.main import Paths
from app.models.db import create_pool
# from aiogram.client.default import DefaultBotProperties
from app.middlewares.simple_chain import SimpleConfigMiddleware, SimpleDbMiddleware
from app.services.parser_service import ParserService
from app.api.main import create_app
from app.api import dependencies as api_deps

logger = logging.getLogger(__name__)


def main():
    paths = get_paths()

    setup_logging(paths)
    config = load_config(paths)
    
    # Initialize blockchain config
    if config.blockchain:
        from app.blockchain.provider import set_blockchain_config
        set_blockchain_config(config.blockchain)
        logger.info(f"✅ Blockchain config loaded: Vault={config.blockchain.vault_v2_address}")

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

    # Set pool for FastAPI dependencies
    api_deps.set_pool(pool)
    
    # Create FastAPI app
    api_app = create_app()

    # Создаем планировщик
    scheduler = AsyncIOScheduler()

    # ⚠️ Автоматическое обновление курсов ОТКЛЮЧЕНО
    # Курсы обновляются только по запросу пользователей через кнопку "Обновить курс"
    # Админ запускает парсеры командой /update_rates в админ-чате
    
    async def monitor_deposits():
        """Фоновая задача мониторинга депозитов"""
        try:
            async with pool() as session:
                from app.blockchain.deposit_tracker import DepositTracker
                tracker = DepositTracker(session)
                await tracker.scan_pending_orders()
        except Exception as e:
            logger.error(f"❌ Ошибка мониторинга депозитов: {e}", exc_info=True)
    
    async def monitor_transactions():
        """Фоновая задача мониторинга confirmations транзакций"""
        try:
            async with pool() as session:
                from app.services.tx_service import TxService
                from app.services.notification_service import NotificationService
                from app.blockchain.provider import get_transaction_receipt, get_block_number
                
                tx_service = TxService(session)
                notif_service = NotificationService(bot, session)
                
                # Get pending transactions
                pending_txs = await tx_service.get_pending_transactions()
                
                if not pending_txs:
                    return
                
                logger.info(f"🔍 Checking {len(pending_txs)} pending transactions...")
                current_block = await get_block_number()
                
                for tx in pending_txs:
                    try:
                        # Get transaction receipt
                        receipt = await get_transaction_receipt(tx.tx_hash, tx.chain_id)
                        
                        if receipt:
                            # Calculate confirmations
                            confirmations = current_block - receipt['blockNumber']
                            
                            # Update transaction
                            if receipt['status'] == 1:  # Success
                                if confirmations >= 2:  # Require 2 confirmations
                                    await tx_service.update_transaction_status(
                                        tx.tx_hash,
                                        'confirmed',
                                        confirmations
                                    )
                                    
                                    # Notify user if this is a withdrawal
                                    if tx.type == 'withdrawal' and tx.order_id:
                                        from app.services.order_service import OrderService
                                        order_service = OrderService(session)
                                        order = await order_service.get_order(tx.order_id)
                                        
                                        if order:
                                            await notif_service.notify_withdrawal_confirmed(
                                                user_id=order.user_id,
                                                order_id=order.id,
                                                tx_hash=tx.tx_hash
                                            )
                                    
                                    logger.info(f"✅ Transaction {tx.tx_hash} confirmed with {confirmations} confirmations")
                                else:
                                    # Update confirmations count
                                    await tx_service.update_transaction_status(
                                        tx.tx_hash,
                                        'pending',
                                        confirmations
                                    )
                                    logger.debug(f"Transaction {tx.tx_hash}: {confirmations} confirmations")
                            else:
                                # Transaction failed
                                await tx_service.update_transaction_status(
                                    tx.tx_hash,
                                    'failed',
                                    0
                                )
                                logger.error(f"❌ Transaction {tx.tx_hash} failed")
                    
                    except Exception as e:
                        logger.error(f"Error checking transaction {tx.tx_hash}: {e}")
                        continue
                
        except Exception as e:
            logger.error(f"❌ Ошибка мониторинга транзакций: {e}", exc_info=True)

    async def monitor_vault_events():
        """Фоновая задача мониторинга событий Vault контракта"""
        try:
            async with pool() as session:
                from app.blockchain.vault_listener import VaultEventListener
                listener = VaultEventListener(session)
                await listener.listen_all()
        except Exception as e:
            logger.error(f"❌ Ошибка мониторинга Vault-событий: {e}", exc_info=True)

    async def on_startup():
        # Регистрируем задачи и запускаем планировщик, когда цикл уже запущен
        
        # ⚠️ Автоматическое обновление курсов ОТКЛЮЧЕНО
        # Курсы обновляются только по запросу пользователей через кнопку "Обновить курс"
        # Админ запускает парсеры командой /update_rates
        
        # Мониторинг депозитов каждые 2 минуты
        scheduler.add_job(
            monitor_deposits,
            trigger=CronTrigger(minute='*/2'),
            id='monitor_deposits',
            replace_existing=True
        )
        
        # Мониторинг транзакций каждую минуту
        scheduler.add_job(
            monitor_transactions,
            trigger=CronTrigger(minute='*'),
            id='monitor_transactions',
            replace_existing=True
        )

        # Vault events every 2 minutes
        scheduler.add_job(
            monitor_vault_events,
            trigger=CronTrigger(minute='*/2'),
            id='monitor_vault_events',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("✅ Планировщик задач запущен:")
        logger.info("   - Обновление курсов: ОТКЛЮЧЕНО (только по запросу пользователей)")
        logger.info("   - Мониторинг депозитов: каждые 2 минуты")
        logger.info("   - Мониторинг транзакций: каждую минуту")
        logger.info("   - Vault события: каждые 2 минуты")
        logger.info("✅ FastAPI сервер запущен на http://0.0.0.0:8000")

    async def on_shutdown():
        try:
            scheduler.shutdown()
        except Exception:
            pass

    # Регистрируем хуки старта/остановки (aiogram сам await-ит async callbacks)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    async def run_bot():
        """Run Telegram bot"""
        logger.info("🤖 Запуск Telegram бота...")
        await dp.start_polling(bot)

    async def run_api():
        """Run FastAPI server"""
        logger.info("🚀 Запуск FastAPI сервера...")
        config_uvicorn = uvicorn.Config(
            api_app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
        server = uvicorn.Server(config_uvicorn)
        await server.serve()

    async def run_all():
        """Run both bot and API concurrently"""
        await asyncio.gather(
            run_bot(),
            run_api()
        )

    logger.info("🚀 Запуск FarCovka (Bot + API)...")
    try:
        asyncio.run(run_all())
    finally:
        close_all_sessions()
        logger.info("✅ Остановлено")


def get_paths() -> Paths:
    if path := os.getenv("BOT_PATH"):
        return Paths(Path(path))
    return Paths(Path(__file__).parent.parent)


if __name__ == '__main__':
    main()
