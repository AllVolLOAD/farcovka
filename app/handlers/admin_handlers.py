import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.main_menu import get_main_keyboard

logger = logging.getLogger(__name__)

# Создаем роутер на уровне модуля
admin_router = Router()

# Вспомогательные функции
def is_admin(user_id: int) -> bool:
    admin_ids = [7111883883, 780245577]
    return user_id in admin_ids


async def send_new_table_to_all_users(bot, new_rate: float, session: AsyncSession):
    """Отправляем новое табло всем пользователям"""
    try:
        from app.services.rate_service import RateService
        from app.keyboards.main_menu import get_main_keyboard

        rate_service = RateService(session)
        message_text = await rate_service.format_rate_message()

        # Получаем всех пользователей у которых есть активная сессия
        # Пока отправим только тем, кто был в очереди (как пример)
        from app.services.queue_service import QueueService
        queue_service = QueueService(session)
        waiting_users = await queue_service.get_waiting_users()

        sent_count = 0
        for user in waiting_users:
            try:
                await bot.send_message(
                    user.user_id,
                    message_text,
                    reply_markup=get_main_keyboard(),
                    parse_mode="HTML"
                )
                sent_count += 1
                logger.info(f"📄 Новое табло отправлено пользователю {user.user_id}")
            except Exception as e:
                logger.error(f"❌ Ошибка отправки табло пользователю {user.user_id}: {e}")

        logger.info(f"📊 Новые табло отправлены {sent_count} пользователям")

    except Exception as e:
        logger.error(f"❌ Ошибка отправки табло: {e}")


async def update_all_user_tables(bot, new_rate: float, session: AsyncSession):
    """Обновляет табло у всех пользователей"""
    try:
        from app.handlers.table_handlers import user_last_table_message
        from app.services.rate_service import RateService

        rate_service = RateService(session)
        message_text = await rate_service.format_rate_message()

        updated_count = 0
        for user_id, message_id in user_last_table_message.items():
            try:
                await bot.edit_message_text(
                    chat_id=user_id,
                    message_id=message_id,
                    text=message_text,
                    reply_markup=get_main_keyboard(),
                    parse_mode="HTML"
                )
                updated_count += 1
                logger.info(f"✏️ Табло обновлено для {user_id}")
            except Exception as e:
                logger.error(f"❌ Ошибка обновления табло для {user_id}: {e}")

        logger.info(f"📊 Табло обновлено у {updated_count} пользователей")

    except Exception as e:
        logger.error(f"❌ Ошибка массового обновления табло: {e}")

async def notify_waiting_users(bot, new_rate: float, session: AsyncSession):
    """Уведомляем только пользователей из очереди"""
    try:
        from app.services.queue_service import QueueService
        queue_service = QueueService(session)
        waiting_users = await queue_service.get_waiting_users()

        notified_count = 0
        for user in waiting_users:
            try:
                await bot.send_message(
                    user.user_id,
                    f"🎉 <b>Курс обновлен!</b>\n\nНовый курс: {new_rate} RUB",
                    parse_mode="HTML"
                )
                logger.info(f"✅ Уведомление отправлено пользователю {user.user_id}")
                notified_count += 1
            except Exception as e:
                logger.error(f"❌ Ошибка отправки пользователю {user.user_id}: {e}")

        logger.info(f"📨 Всего уведомлений отправлено: {notified_count}")

    except Exception as e:
        logger.error(f"❌ Ошибка уведомления: {e}")

# Обработчики
async def handle_rates_bulk(message: Message, session: AsyncSession, text: str):
    """Обрабатывает пакетное обновление курсов"""
    try:
        lines = text.strip().split('\n')
        rates_to_update = {}

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Парсим: USD/RUB 82.80 83.50
            parts = line.split()
            if len(parts) == 3:
                pair = parts[0]  # USD/RUB
                buy_rate = float(parts[1])
                sell_rate = float(parts[2])

                rates_to_update[f"{pair}_BUY"] = buy_rate
                rates_to_update[f"{pair}_SELL"] = sell_rate

        if not rates_to_update:
            await message.answer("❌ Не найдены курсы. Формат:\nUSD/RUB 82.80 83.50\nEUR/RUB 98.40 99.20")
            return

        # Обновляем в БД
        from app.services.multi_rate_service import MultiRateService
        multi_service = MultiRateService(session)

        updated_count = 0
        for pair_key, rate in rates_to_update.items():
            if await multi_service.update_rate(pair_key, rate, message.from_user.id):
                updated_count += 1

        if updated_count > 0:
            # Очищаем очередь
            from app.services.queue_service import QueueService
            queue_service = QueueService(session)
            await queue_service.clear_queue()

            # Уведомляем пользователей
            await notify_waiting_users(message.bot, "все курсы", session)

            await message.answer(f"✅ Обновлено {updated_count} курсов")
        else:
            await message.answer("❌ Ошибка обновления")

    except Exception as e:
        logger.error(f"❌ Ошибка парсинга: {e}")
        await message.answer("❌ Ошибка формата. Пример:\nUSD/RUB 82.80 83.50\nEUR/RUB 98.40 99.20")

@admin_router.message(F.text)
async def handle_admin_messages(message: Message, session: AsyncSession):
    if not is_admin(message.from_user.id):
        return

    text = message.text.strip()

    # Быстрый ввод числа - обновляем основной курс
    if text.replace('.', '').isdigit():
        try:
            new_rate = float(text)
            logger.info(f"💰 Админ ввел основной курс: {new_rate}")

            from app.services.multi_rate_service import MultiRateService
            from app.services.queue_service import QueueService

            multi_service = MultiRateService(session)
            success = await multi_service.update_rate("USD/RUB", new_rate, new_rate * 1.01, message.from_user.id)

            if success:
                queue_service = QueueService(session)
                waiting_users = await queue_service.get_waiting_users()

                await notify_waiting_users(message.bot, new_rate, session)
                await queue_service.clear_queue()

                await message.answer(f"✅ Основной курс RUB/USD обновлен: {new_rate}")
            else:
                await message.answer("❌ Ошибка обновления курса")

        except ValueError:
            await message.answer("❌ Введите число, например: 95.50")


def setup_admin_handlers(dp):
    dp.include_router(admin_router)
    logger.info("✅ Admin handlers registered")

