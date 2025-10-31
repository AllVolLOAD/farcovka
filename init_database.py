#!/usr/bin/env python3
"""
Скрипт инициализации базы данных для FarCovka бота

Перед первым запуском контейнеров выполните:
python init_database.py

Это создаст все необходимые таблицы в базе данных.
"""

import asyncio
import sys
import os

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.db.base import Base, create_pool
from app.models.config.db import config as db_config
from app.models.rate import CurrentRate, RateHistory
from app.models.queue import QueueEntry
from app.models.multi_rate import ExchangeRate
from sqlalchemy.ext.asyncio import create_async_engine

async def init_database():
    """Инициализирует базу данных - создает все таблицы"""
    try:
        print("🚀 Запуск инициализации базы данных...")
        print(f"📊 Подключаемся к БД: {db_config.database_url.split('@')[-1]}")
        
        # Создаем engine
        engine = create_async_engine(db_config.database_url)
        
        # Создаем таблицы
        async with engine.begin() as conn:
            print("🔄 Создаем таблицы...")
            await conn.run_sync(Base.metadata.create_all)
            print("✅ Все таблицы успешно созданы!")
            
            # Показываем созданные таблицы
            result = await conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            )
            tables = [row[0] for row in result]
            print(f"📋 Созданные таблицы: {', '.join(tables)}")
        
        await engine.dispose()
        print("🎉 Инициализация базы данных завершена успешно!")
        print("💡 Теперь можно запускать контейнеры: docker-compose up -d")
        
    except Exception as e:
        print(f"❌ Ошибка инициализации базы данных: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(init_database())
