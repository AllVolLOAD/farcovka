import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


async def debug_handlers_simple():
    """Простая проверка handlers"""
    try:
        from aiogram import Dispatcher
        from app.handlers.rate import setup_rate

        # Просто проверяем что наш router импортируется и регистрируется
        dp = Dispatcher()
        setup_rate(dp)

        print("✅ Наш rate router зарегистрирован!")
        print(f"📋 Всего routers: {len(dp.include_routers)}")

        # Проверяем конкретно наш handler
        for router in dp.include_routers:
            if 'rate' in router.name:
                print(f"🎯 Найден rate router: {router.name}")
                for handler in router.message.handlers:
                    print(f"   - Handler: {handler}")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_handlers_simple())