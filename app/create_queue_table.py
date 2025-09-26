import asyncio
import sys
import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def create_queue_table():
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from app.models.queue import QueueEntry, Base

        # Берем URL из переменных окружения
        DATABASE_URL = os.getenv("DATABASE_URL")
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL не найден в .env файле")

        engine = create_async_engine(DATABASE_URL, echo=True)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        print("✅ Таблица queue_entries создана!")
        await engine.dispose()

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(create_queue_table())