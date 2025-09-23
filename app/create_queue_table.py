import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def create_queue_table():
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from app.models.queue import QueueEntry, Base

        DATABASE_URL = "postgresql+asyncpg://postgres:Zahodim88@localhost:5432/facovka00"
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