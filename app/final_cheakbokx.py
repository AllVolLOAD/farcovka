import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


async def debug_final():
    """Финальная проверка всех компонентов"""
    try:
        # Проверяем импорты
        from app.handlers.rate import setup_rate
        from app.keyboards.main_menu import get_main_keyboard
        from app.services.rate_service import RateService
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

        print("✅ Все импорты работают")

        # Проверяем БД
        DATABASE_URL = "postgresql+asyncpg://postgres:Zahodim88@localhost:5432/facovka00"
        engine = create_async_engine(DATABASE_URL)

        async with AsyncSession(engine) as session:
            rate_service = RateService(session)

            # Тест курса
            rate = await rate_service.get_current_rate()
            print(f"💰 Текущий курс в БД: {rate}")

            # Тест сообщения
            message = await rate_service.format_rate_message()
            print("📄 Сообщение табло:")
            print(message)

            # Тест клавиатуры
            keyboard = get_main_keyboard()
            print(f"⌨️  Клавиатура: {len(keyboard.inline_keyboard[0])} кнопок")

        await engine.dispose()
        print("🎉 ВСЕ КОМПОНЕНТЫ ГОТОВЫ К РАБОТЕ!")
        print("\n🚀 Можно запускать бота командой: python -m app")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_final())