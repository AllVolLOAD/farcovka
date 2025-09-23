import asyncio
import asyncpg


async def reset_queue():
    try:
        # Подключаемся напрямую к БД
        conn = await asyncpg.connect(
            "postgresql://postgres:Zahodim88@localhost:5432/facovka00"
        )

        # Выполняем простой SQL
        await conn.execute("UPDATE queue_entries SET is_processed = true;")
        print("✅ Очередь очищена!")

        # Проверяем
        count = await conn.fetchval("SELECT COUNT(*) FROM queue_entries WHERE is_processed = false;")
        print(f"📊 Осталось активных записей: {count}")

        await conn.close()

    except Exception as e:
        print(f"❌ Ошибка: {e}")


asyncio.run(reset_queue())