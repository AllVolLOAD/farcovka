# check_exchange_rates.py
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

env_path = Path(__file__).parent / '.env.prod'
load_dotenv(env_path)

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Qazwsxedc1488")
DB_NAME = os.getenv("DB_NAME", "facovka00")

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


async def check_exchange_rates():
    engine = create_async_engine(DATABASE_URL, echo=True)

    async with engine.begin() as conn:
        # Проверяем структуру exchange_rates
        result = await conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'exchange_rates'
            ORDER BY ordinal_position;
        """))

        print("📊 Структура таблицы exchange_rates:")
        for row in result:
            print(f"  {row[0]}: {row[1]}")

        # Проверяем есть ли данные
        count_result = await conn.execute(text("SELECT COUNT(*) FROM exchange_rates"))
        count = count_result.scalar()
        print(f"📊 Количество записей в exchange_rates: {count}")

    await engine.dispose()


if __name__ == '__main__':
    asyncio.run(check_exchange_rates())