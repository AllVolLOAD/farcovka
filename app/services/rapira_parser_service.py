import asyncio
from datetime import datetime, timedelta
from app.dao.holder import HolderDao
from app.models.db.parsed_rate import ParsedRate
from app.services.rapira_parser import parse_rapira_complete
from app.services.rapira_selenium_parser import enhanced_rapira_parser
import logging

logger = logging.getLogger(__name__)

class RapiraParserService:
    def __init__(self, session_pool):  # Принимаем session_pool вместо dao
        self.session_pool = session_pool
        self.last_run = None

    async def fetch_rapira_data(self):
        """Получаем реальные данные RAPIRA через твой парсер"""
        try:
            logger.info("🔄 Запуск реального парсера RAPIRA...")

            # Вызываем твой готовый парсер
            rapira_data = enhanced_rapira_parser()

            if rapira_data:
                logger.info(f"✅ Получены данные RAPIRA: Bid={rapira_data.get('Bid')}, Ask={rapira_data.get('Ask')}")
                return rapira_data
            else:
                logger.warning("❌ Парсер не вернул данные")
                return None

        except Exception as e:
            logger.error(f"❌ Ошибка парсера RAPIRA: {e}")
            return None

    async def update_rapira_rates(self):
        """Обновляет курсы RAPIRA в базе данных"""
        logger.info("🔄 Запуск обновления курсов RAPIRA...")

        # Создаем сессию для этого вызова
        async with self.session_pool() as session:
            dao = HolderDao(session)  # Создаем dao с сессией

            try:
                # Получаем данные через твой парсер
                rapira_data = await self.fetch_rapira_data()
                if not rapira_data:
                    logger.error("❌ Не удалось получить данные RAPIRA")
                    return False

                # Деактивируем старые курсы
                await dao.parsed_rate.deactivate_all()

                # Сохраняем новые курсы
                new_rates = []

                if 'Bid' in rapira_data:
                    new_rates.append(ParsedRate(
                        currency_from="USDT",
                        currency_to="RUB",
                        rate=rapira_data['Bid'],
                        rate_type="bid",
                        source='rapira'
                    ))

                if 'Ask' in rapira_data:
                    new_rates.append(ParsedRate(
                        currency_from="USDT",
                        currency_to="RUB",
                        rate=rapira_data['Ask'],
                        rate_type="ask",
                        source='rapira'
                    ))

                # Сохраняем в базу
                for rate in new_rates:
                    await dao.parsed_rate.create_rate(rate)

                self.last_run = datetime.now()
                logger.info(f"✅ Парсер RAPIRA обновил {len(new_rates)} курсов")
                return True

            except Exception as e:
                logger.error(f"❌ Ошибка обновления RAPIRA: {e}")
                return False