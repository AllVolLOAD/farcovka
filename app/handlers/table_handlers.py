from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from app.services.rate_service import RateService  # Один курс
from app.services.multi_rate_service import MultiRateService  # Мультикурсы
from app.keyboards.main_menu import get_main_keyboard
from app.config import BotConfig
import logging

logger = logging.getLogger(__name__)


logger = logging.getLogger(__name__)

# Создаем роутер
router = Router()
user_last_table_message = {}

user_last_table_message = {}


@router.message(Command("start"))
async def table_start(message: Message, session: AsyncSession, config: BotConfig):
    """Показывает/обновляет табло"""
    try:
        rate_service = RateService(session)
        message_text = await rate_service.format_rate_message()

        user_id = message.from_user.id

        # Если есть предыдущее табло - редактируем его
        if user_id in user_last_table_message:
            try:
                await message.bot.edit_message_text(
                    chat_id=user_id,
                    message_id=user_last_table_message[user_id],
                    text=message_text,
                    reply_markup=get_main_keyboard(),
                    parse_mode="HTML"
                )
                logger.info(f"✏️ Табло отредактировано для пользователя {user_id}")
                return
            except Exception as e:
                # Если редактирование не удалось, удаляем из кэша
                del user_last_table_message[user_id]
                logger.warning(f"⚠️ Не удалось отредактировать табло: {e}")

        # Отправляем новое сообщение
        new_message = await message.answer(
            message_text,
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
        user_last_table_message[user_id] = new_message.message_id
        logger.info(f"📄 Новое табло создано для пользователя {user_id}")

    except Exception as e:
        logger.error(f"❌ Ошибка табло: {e}")

@router.callback_query(F.data == "update_rate")
async def update_rate_handler(callback: CallbackQuery, session: AsyncSession, config: BotConfig):
    """Обработчик кнопки 'Обновить курс'"""
    try:
        from app.services.queue_service import QueueService
        from app.services.notification_service import NotificationService

        queue_service = QueueService(session)
        notification_service = NotificationService(callback.bot, config)

        username = callback.from_user.username or callback.from_user.full_name
        success, queue_size = await queue_service.add_to_queue(callback.from_user.id, username)

        if success:
            await notification_service.notify_admins_queue_full()

            if queue_size >= 3:
                message = "✅ Очередь заполнена! Админ уведомлен"
            else:
                message = f"✅ Вы в очереди! Ожидающих: {queue_size}/3"
        else:
            message = "⚠️ Вы уже в очереди!"

        await callback.answer(message, show_alert=True)

    except Exception as e:
        logger.error(f"Ошибка очереди: {e}")
        await callback.answer("🔄 Ошибка системы", show_alert=True)


@router.callback_query(F.data == "fix_rate")
async def fix_rate_handler(callback: CallbackQuery):
    """Обработчик кнопки 'Зафиксировать'"""
    await callback.answer("📊 Функция скоро будет доступна!", show_alert=True)


@router.message(Command("new_rate"))
@router.message(F.text.regexp(r'^[A-Za-z]{3}/[A-Za-z]{3}'))
async def handle_new_rate(message: Message, session: AsyncSession):
    """Обработка команды /new_rate и валютных пар в разных форматах"""
    try:
        text = message.text.strip()
        user_id = message.from_user.id

        # Если команда без параметров - показать справку
        if text == "/new_rate":
            help_text = """
💱 **Обновление курса**

Форматы ввода:
`USD/RUB 82.80 83.30`
`USD/RUB 82.80/83.30`  
`USD/RUB 82.80-83.30`
`USD/RUB 82.80,83.30`

Пример:
`USD/RUB 88.50 90.20`
`EUR/RUB 98.40 99.40`

💡 Можно вводить несколько пар через запятую:
`USD/RUB 82.80 83.30, EUR/RUB 98.40 99.40`
"""
            await message.answer(help_text)
            return

        # Извлекаем пары курсов
        rate_pairs = await parse_rate_input(text)

        if not rate_pairs:
            await message.answer("❌ Неверный формат. Пример: `USD/RUB 82.80 83.30`")
            return

        multi_service = MultiRateService(session)
        results = []

        for pair_data in rate_pairs:
            pair = pair_data['pair'].upper()
            buy_rate = pair_data['buy']
            sell_rate = pair_data['sell']

            success = await multi_service.update_rate(
                pair=pair,
                buy_rate=buy_rate,
                sell_rate=sell_rate,
                admin_id=user_id
            )

            if success:
                results.append(f"✅ {pair}: {buy_rate}/{sell_rate}")
            else:
                results.append(f"❌ {pair}: ошибка обновления")

        # Формируем итоговое сообщение
        if results:
            result_text = "📊 **Результат обновления:**\n" + "\n".join(results)
            # Показываем актуальные курсы
            current_rates = await multi_service.format_multi_rate_message()
            await message.answer(result_text)
            await message.answer(current_rates)
        else:
            await message.answer("❌ Не удалось обновить курсы")

    except Exception as e:
        logger.error(f"Ошибка обработки курса: {e}")
        await message.answer("❌ Ошибка обработки запроса")


async def parse_rate_input(text: str) -> List[Dict[str, Any]]:
    """Парсит ввод курсов в разных форматах"""
    try:
        # Убираем команду если есть
        if text.startswith('/new_rate'):
            text = text.replace('/new_rate', '').strip()

        # Разделяем на отдельные пары по запятым
        pairs_text = [p.strip() for p in text.split(',') if p.strip()]

        results = []

        for pair_text in pairs_text:
            # Заменяем разные разделители на пробелы
            normalized = pair_text.replace('/', ' ').replace('-', ' ').replace(',', ' ')
            parts = [p for p in normalized.split() if p]

            if len(parts) < 3:
                continue

            # Первые 3 части: валюта1, валюта2, курс покупки
            currency1 = parts[0].upper()
            currency2 = parts[1].upper()
            pair = f"{currency1}/{currency2}"

            try:
                buy_rate = float(parts[2])
                # Если есть 4-я часть - курс продажи, иначе используем покупку + небольшой спред
                if len(parts) >= 4:
                    sell_rate = float(parts[3])
                else:
                    sell_rate = buy_rate * 1.01  # Автоматический спред 1%

                results.append({
                    'pair': pair,
                    'buy': buy_rate,
                    'sell': sell_rate
                })

            except ValueError:
                continue

        return results

    except Exception as e:
        logger.error(f"Ошибка парсинга: {e}")
        return []