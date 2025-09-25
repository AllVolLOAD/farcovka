import logging
from typing import Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.multi_rate import ExchangeRate

logger = logging.getLogger(__name__)


class MultiRateService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def update_rate(self, pair: str, rate: float, admin_id: int) -> bool:
        """Обновляет курс для указанной пары"""
        try:
            # Находим или создаем запись
            query = select(ExchangeRate).where(ExchangeRate.pair == pair)
            existing = await self.session.scalar(query)

            if existing:
                existing.rate = rate
                existing.last_admin_id = admin_id
            else:
                new_rate = ExchangeRate(pair=pair, rate=rate, last_admin_id=admin_id)
                self.session.add(new_rate)

            await self.session.commit()
            logger.info(f"✅ Курс {pair} обновлен: {rate}")
            return True

        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Ошибка обновления курса {pair}: {e}")
            return False

    async def get_rate(self, pair: str) -> float:
        """Возвращает курс для пары или 0.0 если не найден"""
        try:
            query = select(ExchangeRate).where(ExchangeRate.pair == pair)
            rate_obj = await self.session.scalar(query)
            return rate_obj.rate if rate_obj else 0.0
        except Exception as e:
            logger.error(f"❌ Ошибка получения курса {pair}: {e}")
            return 0.0

    async def get_all_rates(self) -> Dict[str, float]:
        """Возвращает все курсы в виде словаря {пара: курс}"""
        try:
            query = select(ExchangeRate)
            result = await self.session.scalars(query)
            rates = {rate.pair: rate.rate for rate in result}
            return rates
        except Exception as e:
            logger.error(f"❌ Ошибка получения всех курсов: {e}")
            return {}

    async def format_multi_rate_message(self) -> str:
        """Форматирует сообщение со всеми курсами"""
        rates = await self.get_all_rates()

        if not rates:
            return "🏦 Курсы пока не установлены\n\nОжидайте обновления..."

        message = "🏦 **Текущие курсы:**\n\n"
        for pair, rate in rates.items():
            message += f"💵 {pair}: {rate}\n"

        message += "\nНажмите 'Обновить курс' для актуализации"
        return message