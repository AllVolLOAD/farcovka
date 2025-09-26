# Simple Aiogram 3.x template
[![wakatime](https://wakatime.com/badge/user/929ee39b-4eb0-4076-ab5e-5ade3c56e464/project/7d995a8f-0e9f-428a-a098-5186c70b6d6e.svg)](https://wakatime.com/badge/user/929ee39b-4eb0-4076-ab5e-5ade3c56e464/project/7d995a8f-0e9f-428a-a098-5186c70b6d6e)

## How to run

Required launched PostgreSQL and installed Python3.10

* copy config template
```bash
cp -r config config
```
* Fill config/config.yml in with required values 
* Create and activate venv
```bash
python -m venv venv
source venv/bin/activate
```
* install dependencies
```bash
pip install -r requirements.txt
```
* Fill in alembic.ini (probably only db url)
* apply migrations
```bash
alembic upgrade head
```
* ... and run
```bash
python -m app
```
create script for make DB

#!/usr/bin/env python3
import asyncio
import os
import sys
from pathlib import Path

# Добавляем путь к app в PYTHONPATH
sys.path.append(str(Path(__file__).parent.parent))

async def init_database():
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from app.config.db import DatabaseConfig
        
        # Берем URL из конфига
        config = DatabaseConfig()
        database_url = config.url
        
        print(f"🔗 Подключаемся к БД: {database_url.split('@')[-1]}")
        
        # Создаем engine
        engine = create_async_engine(database_url, echo=True)
        
        # Импортируем модели после создания engine
        from app.models.queue import Base as QueueBase
        from app.models.user import Base as UserBase
        from app.models.chat import Base as ChatBase
        
        # Создаем все таблицы
        async with engine.begin() as conn:
            print("🗃️ Создаем таблицы...")
            await conn.run_sync(QueueBase.metadata.create_all)
            await conn.run_sync(UserBase.metadata.create_all) 
            await conn.run_sync(ChatBase.metadata.create_all)
            print("✅ Все таблицы созданы успешно!")
        
        await engine.dispose()
        
    except Exception as e:
        print(f"❌ Ошибка инициализации БД: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(init_database())

    cheak it one more time

    import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

async def check_database():
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from app.config.db import DatabaseConfig
        
        config = DatabaseConfig()
        engine = create_async_engine(config.url, echo=False)
        
        async with engine.connect() as conn:
            # Проверяем подключение
            result = await conn.scalar("SELECT version()")
            print(f"✅ Подключение к БД успешно! PostgreSQL: {result.split(',')[0]}")
            
            # Проверяем существующие таблицы
            tables = await conn.scalar(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
            )
            print(f"📊 Найдено таблиц в БД: {tables}")
        
        await engine.dispose()
        
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(check_database())
