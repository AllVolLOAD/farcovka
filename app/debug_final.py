import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


async def debug_multi_rate():
    """Тестируем мульти-валютную систему"""
    try:
        # Проверяем импорты новых компонентов
        from app.services.multi_rate_service import MultiRateService
        from app.models.multi_rate import ExchangeRate, Base
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

        print("✅ Импорты мульти-валютной системы работают")

        # Проверяем БД
        DATABASE_URL = "postgresql+asyncpg://postgres:Zahodim88@localhost:5432/facovka00"
        engine = create_async_engine(DATABASE_URL, echo=True)

        # Создаем таблицы для мульти-валют
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Таблицы мульти-валютной системы созданы")

        # Тестируем сервис
        async with AsyncSession(engine) as session:
            multi_service = MultiRateService(session)

            # Тест обновления курса
            success = await multi_service.update_rate("RUB/USD", 95.50, 96.00, 12345)
            print(f"🔄 Обновление курса RUB/USD: {'✅' if success else '❌'}")

            # Тест получения курса
            rate = await multi_service.get_rate("RUB/USD")
            print(f"💰 Курс RUB/USD: {rate}")

            # Тест второго курса
            await multi_service.update_rate("USD/USDT", 0.996, 12345)
            usd_rate = await multi_service.get_rate("USD/USDT")
            print(f"💰 Курс USD/USDT: {usd_rate}")

            # Тест всех курсов
            all_rates = await multi_service.get_all_rates()
            print(f"📊 Все курсы: {all_rates}")

            # Тест форматирования сообщения
            message = await multi_service.format_multi_rate_message()
            print("📄 Мульти-валютное табло:")
            print(message)
            # Тест обновления курса
            success = await multi_service.update_rate("RUB/USD", 95.50, 96.00, 12345)
            print(f"🔄 Обновление курса RUB/USD: {'✅' if success else '❌'}")

            # Тест получения курса (теперь возвращает кортеж)
            buy_rate, sell_rate = await multi_service.get_rate("RUB/USD")
            print(f"💰 Курс RUB/USD: {buy_rate}/{sell_rate}")

            # Тест второго курса
            await multi_service.update_rate("USD/USDT", 0.996, 1.002, 12345)
            usd_buy, usd_sell = await multi_service.get_rate("USD/USDT")
            print(f"💰 Курс USD/USDT: {usd_buy}/{usd_sell}")

        # Проверяем старую систему (для совместимости)
        print("\n🔍 Проверяем старую систему...")
        from app.services.rate_service import RateService

        async with AsyncSession(engine) as session:
            old_service = RateService(session)
            old_rate = await old_service.get_current_rate()
            print(f"💰 Старый курс: {old_rate}")

        await engine.dispose()
        print("\n🎉 МУЛЬТИ-ВАЛЮТНАЯ СИСТЕМА ГОТОВА К РАБОТЕ!")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()



if __name__ == "__main__":
    asyncio.run(debug_multi_rate())