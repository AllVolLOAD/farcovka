import asyncio
import sys
import os

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


async def debug_models():
    """Простой дебаг моделей"""
    try:
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from app.models.rate import CurrentRate, Base

        # URL из твоего alembic.ini - ПРОВЕРЬ ПАРОЛЬ!
        DATABASE_URL = "postgresql+asyncpg://postgres:Zahodim88@localhost:5432/facovka00"

        print("🔌 Подключаемся к БД...")
        engine = create_async_engine(DATABASE_URL, echo=True)

        print("📦 Создаем таблицы...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        print("✅ Таблицы созданы!")

        await engine.dispose()
        print("🎉 Всё работает!")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_models())