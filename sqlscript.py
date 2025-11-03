# add_bank_columns.py
import asyncio
import asyncpg
from app.config.main import BotConfig  # Или откуда берется конфиг


async def add_columns():
    # Получите настройки БД из вашего конфига
    # Если используете BotConfig, настройте подключение
    database_url = "postgresql://postgres:Qazwsxedc1488@localhost/facovka00"  # Замените на ваши данные

    try:
        conn = await asyncpg.connect(database_url)
        print("✅ Подключение к БД установлено")

        # Добавляем колонки
        await conn.execute("ALTER TABLE exchange_rates ADD COLUMN IF NOT EXISTS buy_bank VARCHAR")
        await conn.execute("ALTER TABLE exchange_rates ADD COLUMN IF NOT EXISTS sell_bank VARCHAR")
        await conn.execute("ALTER TABLE exchange_rates ADD COLUMN IF NOT EXISTS source VARCHAR DEFAULT 'admin'")

        print("✅ Колонки успешно добавлены")

        # Показываем структуру таблицы
        result = await conn.fetch("""
                                  SELECT column_name, data_type, is_nullable
                                  FROM information_schema.columns
                                  WHERE table_name = 'exchange_rates'
                                  ORDER BY ordinal_position
                                  """)

        print("\n📊 Структура таблицы exchange_rates:")
        for row in result:
            print(f"   {row['column_name']} - {row['data_type']} - NULL: {row['is_nullable']}")

        await conn.close()
        print("\n✅ Миграция завершена успешно!")

    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(add_columns())