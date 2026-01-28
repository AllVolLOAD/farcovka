"""
Сервис для автоматического обновления курсов из парсеров
"""
import logging
from datetime import datetime, time as dt_time
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.multi_rate_service import MultiRateService
from app.parsers.currency_parsers import parse_cbr_rates, parse_rbc_rates, get_cbr_usd_rate, get_rbc_best_rates

logger = logging.getLogger(__name__)


class ParserService:
    """Сервис для автоматического обновления курсов"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.multi_service = MultiRateService(session)
    
    def is_work_time(self) -> bool:
        """Проверяет рабочее время (9:00 - 21:00)"""
        now = datetime.now()
        work_start = dt_time(9, 0)
        work_end = dt_time(21, 0)
        current_time = now.time()
        return work_start <= current_time <= work_end
    
    async def update_cbr_rates(self) -> bool:
        """Обновляет курсы из ЦБ РФ"""
        try:
            if not self.is_work_time():
                logger.debug("Вне рабочего времени, пропускаем обновление ЦБ")
                return False
            
            logger.info("🔄 Начало обновления курсов ЦБ...")
            data = await parse_cbr_rates()
            if not data:
                logger.warning("⚠️ Не удалось получить данные ЦБ")
                return False
            
            usd_rate = get_cbr_usd_rate(data)
            if not usd_rate:
                logger.warning("⚠️ Не найден курс USD в данных ЦБ")
                return False
            
            # Обновляем курс в БД с source="cbr"
            # Используем спред 0.5% от курса ЦБ
            buy_rate = usd_rate
            sell_rate = usd_rate * 1.005
            
            success = await self.multi_service.update_rate_with_source(
                pair="USD/RUB",
                buy_rate=buy_rate,
                sell_rate=sell_rate,
                source="cbr",
                admin_id=None
            )
            
            if success:
                logger.info(f"✅ Курс ЦБ обновлен: {usd_rate:.2f} RUB")
            else:
                logger.error("❌ Ошибка обновления курса ЦБ в БД")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления ЦБ: {e}", exc_info=True)
            return False

    async def update_rbc_rates(self) -> bool:
        """Обновляет курсы из РБК"""
        try:
            if not self.is_work_time():
                logger.debug("Вне рабочего времени, пропускаем обновление РБК")
                return False

            logger.info("🔄 Начало обновления курсов РБК...")
            data = await parse_rbc_rates()
            if not data:
                logger.warning("⚠️ Не удалось получить данные РБК")
                return False

            best_rates = get_rbc_best_rates(data)
            if not best_rates:
                logger.warning("⚠️ Не найдены лучшие курсы в данных РБК")
                return False

            success = await self.multi_service.update_rate_with_source(
                pair="USD/RUB",
                buy_rate=best_rates['buy_rate'],
                sell_rate=best_rates['sell_rate'],
                source="rbc",
                admin_id=None,
                buy_bank=best_rates['buy_bank'],  # Передаем банки
                sell_bank=best_rates['sell_bank']
            )

            if success:
                logger.info(
                    f"✅ Курс РБК обновлен: {best_rates['buy_bank']} {best_rates['buy_rate']:.2f} / {best_rates['sell_bank']} {best_rates['sell_rate']:.2f}")
            else:
                logger.error("❌ Ошибка обновления курса РБК в БД")

            return success

        except Exception as e:
            logger.error(f"❌ Ошибка обновления РБК: {e}", exc_info=True)
            return False
    
    async def update_all_auto_rates(self):
        """Обновляет все автоматические курсы"""
        logger.info("🔄 Начало обновления всех автоматических курсов...")
        await self.update_cbr_rates()
        await self.update_rbc_rates()
        logger.info("✅ Обновление автоматических курсов завершено")

