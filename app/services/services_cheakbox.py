import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


async def debug_service():
    try:
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from app.services.rate_service import RateService

        DATABASE_URL = "postgresql+asyncpg://postgres:Zahodim88@localhost:5432/facovka00"
        engine = create_async_engine(DATABASE_URL, echo=True)

        async with AsyncSession(engine) as session:
            rate_service = RateService(session)

            # Тест получения курса
            rate = await rate_service.get_current_rate()
            print(f"💰 Текущий курс: {rate}")

            # Тест форматирования сообщения
            message = await rate_service.format_rate_message()
            print(f"📄 Сообщение табло: {message}")

            # Тест обновления курса
            success = await rate_service.update_rate(95.50, 12345)
            print(f"🔄 Обновление курса: {'✅' if success else '❌'}")

            # Проверяем обновленный курс
            new_rate = await rate_service.get_current_rate()
            print(f"💰 Новый курс: {new_rate}")

        await engine.dispose()
        print("🎉 Сервис работает!")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_service())