from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.db.parsed_rate import ParsedRate
from datetime import datetime
import logging


logger = logging.getLogger(__name__)

class ParsedRateDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_rate(self, rate: ParsedRate):
        """Создает новый курс в базе данных"""
        try:
            # Устанавливаем текущее время
            now = datetime.now()
            rate.updated_at = now
            rate.created_at = now

            # Сохраняем в базу
            self.session.add(rate)
            await self.session.commit()

            logger.info(f"💾 Сохранен курс: {rate.currency_from}/{rate.currency_to} {rate.rate_type}: {rate.rate}")
            return rate

        except Exception as e:
            await self.session.rollback()
            print(f"❌ Ошибка сохранения курса: {e}")
            return None

    async def deactivate_all(self):
        """Деактивирует все старые курсы"""
        try:
            stmt = update(ParsedRate).values(is_active=False)
            await self.session.execute(stmt)
            await self.session.commit()
            logger.info("✅ Старые курсы деактивированы")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Ошибка деактивации курсов: {e}")

    async def deactivate_rates(self, source: str):
        """Деактивирует курсы по источнику"""
        try:
            stmt = update(ParsedRate).where(
                ParsedRate.source == source,
                ParsedRate.is_active == True
            ).values(is_active=False)
            await self.session.execute(stmt)
            await self.session.commit()
            logger.info(f"✅ Курсы источника {source} деактивированы")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Ошибка деактивации курсов источника {source}: {e}")

    async def get_active_rates(self):
        """Получает активные курсы из базы"""
        try:
            stmt = select(ParsedRate).where(ParsedRate.is_active == True)
            result = await self.session.execute(stmt)
            rates = result.scalars().all()
            logger.info(f"✅ Получено {len(rates)} активных курсов из базы")
            return rates
        except Exception as e:
            logger.error(f"❌ Ошибка получения курсов: {e}")
            return []

    async def get_active_rates_by_source(self, source: str):
        """Получает активные курсы по источнику"""
        try:
            stmt = select(ParsedRate).where(
                ParsedRate.source == source,
                ParsedRate.is_active == True
            )
            result = await self.session.execute(stmt)
            rates = result.scalars().all()
            logger.info(f"✅ Получено {len(rates)} активных курсов из источника {source}")
            return rates
        except Exception as e:
            logger.error(f"❌ Ошибка получения курсов по источнику {source}: {e}")
            return []