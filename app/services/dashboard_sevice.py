from datetime import datetime
import pytz
from app.dao.holder import HolderDao
from app.services.multi_rate_service import MultiRateService
import logging

logger = logging.getLogger(__name__)


class DashboardService:
    def __init__(self, session):
        self.session = session

    def _format_time_ago(self, timestamp):
        """Форматирует время в формате 'X мин назад' с учетом часового пояса"""
        if not timestamp:
            return "неизвестно"

        try:
            # Убедимся что timestamp в московском времени
            moscow_tz = pytz.timezone('Europe/Moscow')

            # Если timestamp наивный (без часового пояса), считаем что это UTC
            if timestamp.tzinfo is None:
                # Предполагаем что timestamp из БД в UTC
                utc_tz = pytz.UTC
                timestamp = utc_tz.localize(timestamp)

            # Конвертируем в московское время
            moscow_time = timestamp.astimezone(moscow_tz)
            now_moscow = datetime.now(moscow_tz)

            diff = now_moscow - moscow_time
            total_seconds = diff.total_seconds()
            minutes = int(total_seconds / 60)

            logger.debug(f"🕒 DEBUG: timestamp={timestamp}, moscow_time={moscow_time}, now_moscow={now_moscow}, diff={diff}, minutes={minutes}")

            if minutes < 1:
                return "только что"
            elif minutes < 60:
                return f"{minutes} мин назад"
            else:
                hours = minutes // 60
                return f"{hours} ч назад"

        except Exception as e:
            logger.error(f"❌ Ошибка форматирования времени: {e}")
            return "ошибка времени"

    async def get_dashboard_data(self):
        """Получаем данные для табло: парсерные и админские курсы"""
        try:
            # Получаем курсы с парсера RAPIRA
            from app.dao.parsed_rate import ParsedRateDAO
            parsed_rate_dao = ParsedRateDAO(self.session)
            parsed_rates = await parsed_rate_dao.get_active_rates()

            # Детальное логирование источников
            sources = {}
            for rate in parsed_rates:
                source = rate.source
                if source not in sources:
                    sources[source] = []
                sources[source].append(f"{rate.currency_from}/{rate.currency_to} ({rate.rate_type})")

            for source, pairs in sources.items():
                logger.info(f"📊 Источник '{source}': {len(pairs)} курсов - {', '.join(pairs)}")
            # ... остальной код без изменений

            # Получаем админские курсы
            admin_rates = []
            try:
                from sqlalchemy import select
                from app.models.multi_rate import ExchangeRate

                # Получаем полные объекты с временем обновления
                stmt = select(ExchangeRate)
                result = await self.session.execute(stmt)
                admin_rates_objects = result.scalars().all()
                logger.info(f"🔄 Получено {len(admin_rates_objects)} полных объектов админских курсов")

                # Преобразуем в удобный формат для отображения
                for rate_obj in admin_rates_objects:
                    admin_rates.append({
                        'pair': rate_obj.pair,
                        'buy_rate': rate_obj.buy_rate,
                        'sell_rate': rate_obj.sell_rate,
                        'last_updated': rate_obj.last_updated
                    })

            except Exception as e:
                logger.error(f"❌ Ошибка получения админских курсов: {e}")

            return {
                'parsed_rates': parsed_rates,
                'admin_rates': admin_rates
            }
        except Exception as e:
            logger.error(f"❌ Ошибка получения данных для табло: {e}")
            return {'parsed_rates': [], 'admin_rates': []}

    async def format_dashboard_message(self) -> str:
        """Форматируем сообщение табло с временем для каждого курса"""
        data = await self.get_dashboard_data()

        # ЛЕВАЯ ЧАСТЬ - Курсы парсера RAPIRA
        parsed_section = "🔄 *КУРСЫ RAPIRA:*\n"
        if data['parsed_rates']:
            # Группируем по валютным парам и находим время для каждой пары
            rates_by_pair = {}

            for rate in data['parsed_rates']:
                pair = f"{rate.currency_from}/{rate.currency_to}"
                if pair not in rates_by_pair:
                    rates_by_pair[pair] = {'bid': None, 'ask': None, 'time': None}

                if rate.rate_type == 'bid':
                    rates_by_pair[pair]['bid'] = rate.rate
                elif rate.rate_type == 'ask':
                    rates_by_pair[pair]['ask'] = rate.rate

                # Берем время из любого курса этой пары
                if rate.updated_at:
                    rates_by_pair[pair]['time'] = rate.updated_at

            for pair, rates_data in rates_by_pair.items():
                bid = rates_data['bid']
                ask = rates_data['ask']
                time = rates_data['time']

                if bid and ask:
                    time_ago = self._format_time_ago(time) if time else "давно"
                    parsed_section += f"• {pair}: `{bid:.2f}` / `{ask:.2f}` _{time_ago}_\n"
        else:
            parsed_section += "_Нет данных_\n"

        # ПРАВАЯ ЧАСТЬ - Админские курсы (время для каждого курса)
        admin_section = "👨‍💼 *АДМИНСКИЕ КУРСЫ:*\n"
        if data['admin_rates']:
            for rate in data['admin_rates']:
                if rate['buy_rate'] > 0 and rate['sell_rate'] > 0:
                    time_ago = self._format_time_ago(rate['last_updated']) if rate['last_updated'] else "давно"
                    admin_section += f"• {rate['pair']}: `{rate['buy_rate']:.2f}` / `{rate['sell_rate']:.2f}` _{time_ago}_\n"
        else:
            admin_section += "_Нет данных_\n"

        dashboard_text = (
            "📊 *ТЕКУЩИЕ КУРСЫ*\n\n"
            f"{parsed_section}\n"
            f"{admin_section}"
        )

        return dashboard_text

    async def get_time_diff(self, timestamp):
        """Вспомогательный метод для получения разницы во времени в минутах"""
        return self._format_time_ago(timestamp)