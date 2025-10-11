import aiohttp
import asyncio
from app.dao.holder import HolderDao
from app.models.db.parsed_rate import ParsedRate
from app.services.rapira_parser import parse_rapira_complete


class ParserService:
    def __init__(self, dao: HolderDao):
        self.dao = dao

    async def get_rapira_data_from_budget_server(self):
        """Получаем данные RAPIRA с беджет сервера"""
        try:
            # Здесь должен быть код для получения данных с вашего беджет сервера
            # Например, через HTTP запрос или через вызов существующего сервиса

            # ВРЕМЕННАЯ ЗАГЛУШКА - замените на реальный вызов
            card_text = await self.fetch_rapira_data()

            if card_text:
                parsed_data = parse_rapira_complete(card_text)
                return parsed_data
            else:
                print("❌ Не удалось получить данные с беджет сервера")
                return None

        except Exception as e:
            print(f"❌ Ошибка получения данных с беджет сервера: {e}")
            return None

    async def fetch_rapira_data(self):
        """Получаем сырые данные RAPIRA с сервера"""
        # ВРЕМЕННАЯ ЗАГЛУШКА - замените на ваш реальный метод
        # Пример с моковыми данными:
        mock_card_text = """
        RAPIRA
        USDT/RUB
        Bid: 91.50
        Ask: 92.30
        VWAP 50k Bid: 91.45
        VWAP 50k Ask: 92.35
        01.01.2024
        """
        return mock_card_text

    async def parse_exchange_rates(self):
        """Парсим курсы с RAPIRA через беджет сервер"""
        print("🔄 Получаем курсы RAPIRA с беджет сервера...")

        rapira_data = await self.get_rapira_data_from_budget_server()

        if not rapira_data:
            print("❌ Не удалось получить данные RAPIRA")
            return []

        rates = []

        # Создаем записи для Bid и Ask
        if 'Bid' in rapira_data:
            rates.append(ParsedRate(
                currency_from="USDT",
                currency_to="RUB",
                rate=rapira_data['Bid'],
                rate_type="bid",
                source='rapira_budget'
            ))

        if 'Ask' in rapira_data:
            rates.append(ParsedRate(
                currency_from="USDT",
                currency_to="RUB",
                rate=rapira_data['Ask'],
                rate_type="ask",
                source='rapira_budget'
            ))

        print(f"✅ Получено {len(rates)} курсов с RAPIRA")
        return rates

    async def update_rates(self):
        """Обновляем курсы в базе данных"""
        print("🔄 Обновляем курсы RAPIRA...")

        # Деактивируем старые курсы
        await self.dao.parsed_rate.deactivate_all()

        # Получаем новые курсы
        new_rates = await self.parse_exchange_rates()

        # Сохраняем новые курсы
        for rate in new_rates:
            await self.dao.parsed_rate.create_rate(rate)

        print(f"✅ Обновлено {len(new_rates)} курсов")
        return new_rates