import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.multi_rate import ExchangeRate

logger = logging.getLogger(__name__)


class MultiRateService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def update_rate(self, pair: str, buy_rate: float, sell_rate: float, admin_id: int) -> bool:
        """Обновляет курс покупки и продажи (админский)"""
        return await self.update_rate_with_source(pair, buy_rate, sell_rate, "admin", admin_id)

    async def update_rate_with_source(
            self,
            pair: str,
            buy_rate: float,
            sell_rate: float,
            source: str,
            admin_id: int = None,
            buy_bank: str = None,  # Добавляем параметры банков
            sell_bank: str = None
    ) -> bool:
        """Обновляет курс с указанием источника и банков"""
        try:
            # Ищем курс по паре И источнику
            query = select(ExchangeRate).where(
                ExchangeRate.pair == pair,
                ExchangeRate.source == source
            )
            existing = await self.session.scalar(query)

            if existing:
                existing.buy_rate = buy_rate
                existing.sell_rate = sell_rate
                existing.last_admin_id = admin_id
                existing.last_updated = datetime.utcnow()
                # Обновляем банки если переданы
                if buy_bank is not None:
                    existing.buy_bank = buy_bank
                if sell_bank is not None:
                    existing.sell_bank = sell_bank
            else:
                new_rate = ExchangeRate(
                    pair=pair,
                    buy_rate=buy_rate,
                    sell_rate=sell_rate,
                    last_admin_id=admin_id,
                    source=source,
                    buy_bank=buy_bank,  # Сохраняем банки
                    sell_bank=sell_bank
                )
                self.session.add(new_rate)

            await self.session.commit()
            return True
        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Ошибка обновления курса {pair} ({source}): {e}")
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
        """Форматирует: USD/RUB 81.89/82.80 (в 14:25) - использует новый формат с источниками"""
        return await self.format_multi_rate_message_with_sources()

    async def get_rates_by_source(self, pair: str) -> Dict[str, tuple]:
        """Возвращает все курсы для пары по источникам"""
        try:
            query = select(ExchangeRate).where(ExchangeRate.pair == pair)
            result = await self.session.scalars(query)
            rates = {}
            for rate in result:
                rates[rate.source] = (rate.buy_rate, rate.sell_rate, rate.last_updated, rate.buy_bank, rate.sell_bank)
            return rates
        except Exception as e:
            logger.error(f"❌ Ошибка получения курсов по источникам: {e}")
            return {}

    async def format_multi_rate_message_with_sources(self) -> str:
        """Форматирует табло со ВСЕМИ парами из БД в новом формате"""
        try:
            # Получаем ВСЕ курсы из базы
            query = select(ExchangeRate)
            result = await self.session.scalars(query)
            all_rates = list(result)

            if not all_rates:
                return "Курсы пока не установлены"

            message = ""

            def fmt_msk(dt: datetime) -> str:
                if not dt:
                    return "—"
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(ZoneInfo("Europe/Moscow")).strftime("%H:%M")

            # Группируем по парам
            pairs = {}
            for rate in all_rates:
                if rate.pair not in pairs:
                    pairs[rate.pair] = []
                pairs[rate.pair].append(rate)

            # Форматируем каждую пару
            for pair, rates in pairs.items():
                message += f"{pair}:\n"

                # Админский курс - ПЕРВЫЙ как "ОФИС"
                admin_rates = [r for r in rates if r.source == 'admin']
                if admin_rates:
                    rate = admin_rates[0]
                    time_str = fmt_msk(rate.last_updated)
                    message += f"ОФИС: {rate.buy_rate:.2f} / {rate.sell_rate:.2f} ({time_str})\n"

                # ЦБ
                cbr_rates = [r for r in rates if r.source == 'cbr']
                if cbr_rates:
                    rate = cbr_rates[0]
                    time_str = fmt_msk(rate.last_updated)
                    message += f"ЦБ: {rate.buy_rate:.2f} / {rate.sell_rate:.2f} ({time_str})\n"

                # РБК - два банка
                rbc_buy_rates = [r for r in rates if r.source == 'rbc_buy']
                if rbc_buy_rates:
                    rate = rbc_buy_rates[0]
                    time_str = fmt_msk(rate.last_updated)
                    message += f"РБК (покупка): {rate.buy_rate:.2f} / {rate.sell_rate:.2f} ({time_str})\n"
                
                rbc_sell_rates = [r for r in rates if r.source == 'rbc_sell']
                if rbc_sell_rates:
                    rate = rbc_sell_rates[0]
                    time_str = fmt_msk(rate.last_updated)
                    message += f"РБК (продажа): {rate.buy_rate:.2f} / {rate.sell_rate:.2f} ({time_str})\n"

                message += "\n"

            return message.strip()
        except Exception as e:
            logger.error(f"❌ Ошибка форматирования: {e}")
            return "Курсы временно недоступны"


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

    async def remove_rate(self, pair: str) -> bool:
        """Удаляет конкретную пару из базы"""
        try:
            query = select(ExchangeRate).where(ExchangeRate.pair == pair)
            rate = await self.session.scalar(query)

            if rate:
                await self.session.delete(rate)
                await self.session.commit()
                logger.info("✅ Пара %s удалена", pair)
                return True
            return False
        except Exception as e:
            await self.session.rollback()
            logger.error("❌ Ошибка удаления пары %s: %s", pair, e)
            return False

    async def clear_all_rates(self) -> bool:
        """Очищает все курсы"""
        try:
            await self.session.execute(delete(ExchangeRate))
            await self.session.commit()
            logger.info("✅ Все курсы очищены")
            return True
        except Exception as e:
            await self.session.rollback()
            logger.error("❌ Ошибка очистки курсов: %s", e)
            return False
