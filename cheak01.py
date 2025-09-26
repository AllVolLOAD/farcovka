import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


async def check_database():
    db_url = "postgresql+asyncpg://postgres:Zahodim88@localhost:5432/facovka00"
    engine = create_async_engine(db_url)

    async with engine.connect() as conn:
        # 1. Проверяем таблицу
        print("1. Проверяем таблицу user_stats...")
        result = await conn.execute(text("SELECT COUNT(*) FROM user_stats"))
        count = result.scalar()
        print(f"   ✅ Записей в user_stats: {count}")

        # 2. Проверяем структуру
        print("2. Проверяем структуру таблицы...")
        result = await conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'user_stats'
        """))
        print("   📊 Структура user_stats:")
        for col_name, data_type in result:
            print(f"      {col_name}: {data_type}")

        # 3. Добавляем тестовую запись
        print("3. Тестируем добавление записи...")
        await conn.execute(text("""
            INSERT INTO user_stats (user_id, action) 
            VALUES (123456, 'test')
        """))
        await conn.commit()

        # 4. Проверяем добавление
        result = await conn.execute(text("SELECT COUNT(*) FROM user_stats"))
        count = result.scalar()
        print(f"   ✅ Теперь записей: {count}")

    await engine.dispose()
    print("✅ Проверка завершена!")


if __name__ == "__main__":
    asyncio.run(check_database())