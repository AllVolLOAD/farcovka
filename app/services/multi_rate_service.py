import logging
from datetime import datetime
from typing import Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.multi_rate import ExchangeRate

logger = logging.getLogger(__name__)


class MultiRateService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def update_rate(self, pair: str, buy_rate: float, sell_rate: float, admin_id: int) -> bool:
        """Обновляет курс покупки и продажи"""
        try:
            query = select(ExchangeRate).where(ExchangeRate.pair == pair)
            existing = await self.session.scalar(query)

            if existing:
                existing.buy_rate = buy_rate
                existing.sell_rate = sell_rate
                existing.last_admin_id = admin_id
                existing.last_updated = datetime.utcnow()
            else:
                new_rate = ExchangeRate(
                    pair=pair,
                    buy_rate=buy_rate,
                    sell_rate=sell_rate,
                    last_admin_id=admin_id
                )
                self.session.add(new_rate)

            await self.session.commit()
            return True
        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Ошибка обновления курса {pair}: {e}")
            return False

    async def get_rate(self, pair: str) -> tuple[float, float]:
        """Возвращает курс (покупка, продажа) - упрощенная версия без времени"""
        try:
            query = select(ExchangeRate).where(ExchangeRate.pair == pair)
            rate_obj = await self.session.scalar(query)
            if rate_obj:
                return (rate_obj.buy_rate, rate_obj.sell_rate)
            return (0.0, 0.0)
        except Exception as e:
            logger.error(f"❌ Ошибка получения курса {pair}: {e}")
            return (0.0, 0.0)

    async def get_rate_with_time(self, pair: str) -> tuple[tuple[float, float], str]:
        """Возвращает курс (покупка, продажа) и время"""
        try:
            query = select(ExchangeRate).where(ExchangeRate.pair == pair)
            rate_obj = await self.session.scalar(query)
            if rate_obj:
                time_str = rate_obj.last_updated.strftime("%H:%M")
                return (rate_obj.buy_rate, rate_obj.sell_rate), time_str
            return (0.0, 0.0), "не обновлялся"
        except Exception as e:
            logger.error(f"❌ Ошибка получения курса с временем {pair}: {e}")
            return (0.0, 0.0), "ошибка"

    async def get_all_rates(self) -> Dict[str, tuple[float, float]]:
        """Возвращает все курсы в виде {пара: (покупка, продажа)}"""
        try:
            query = select(ExchangeRate)
            result = await self.session.scalars(query)
            rates = {rate.pair: (rate.buy_rate, rate.sell_rate) for rate in result}
            return rates
        except Exception as e:
            logger.error(f"❌ Ошибка получения всех курсов: {e}")
            return {}

    async def format_multi_rate_message(self) -> str:
        """Форматирует: USD/RUB 81.89/82.80 (в 14:25)"""
        try:
            query = select(ExchangeRate)
            result = await self.session.scalars(query)
            rates = list(result)

            if not rates:
                return "🏦 Курсы пока не установлены"

            message = "🏦 **Текущие курсы:**\n\n"
            for rate in rates:
                time_str = rate.last_updated.strftime("%H:%M")
                message += f"💵 {rate.pair} {rate.buy_rate}/{rate.sell_rate} (в {time_str})\n"

            return message
        except Exception as e:
            logger.error(f"❌ Ошибка форматирования сообщения: {e}")
            return "🏦 Курсы временно недоступны"


    async def update_multiple_rates(self, rates_data: List[Dict], admin_id: int) -> Dict[str, bool]:
            """Обновляет несколько курсов одновременно"""
            results = {}
            for rate_data in rates_data:
                success = await self.update_rate(
                    pair=rate_data['pair'],
                    buy_rate=rate_data['buy'],
                    sell_rate=rate_data['sell'],
                    admin_id=admin_id
                )
                results[rate_data['pair']] = success
            return results