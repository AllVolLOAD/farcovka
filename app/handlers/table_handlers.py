from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from app.services.notification_service import NotificationService
from app.services.rate_service import RateService  # Один курс
from app.services.multi_rate_service import MultiRateService  # Мультикурсы
from app.keyboards.main_menu import get_main_keyboard
from app.config.main import BotConfig
import logging

logger = logging.getLogger(__name__)


logger = logging.getLogger(__name__)

# Создаем роутер
router = Router()
user_last_table_message = {}

user_last_table_message = {}


@router.message(Command("start"))
async def table_start(message: Message, session: AsyncSession, config: BotConfig):
    """Показывает/обновляет табло с мультикурсами"""
    try:
        # Используем MultiRateService вместо RateService
        multi_service = MultiRateService(session)
        message_text = await multi_service.format_multi_rate_message()

        user_id = message.from_user.id

        # Если есть предыдущее табло - редактируем его
        if user_id in user_last_table_message:
            try:
                await message.bot.edit_message_text(
                    chat_id=user_id,
                    message_id=user_last_table_message[user_id],
                    text=message_text,
                    reply_markup=get_main_keyboard(),
                    parse_mode="Markdown"  # Измените на Markdown если нужно
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
            parse_mode="Markdown"  # Измените на Markdown если нужно
        )
        user_last_table_message[user_id] = new_message.message_id
        logger.info(f"📄 Новое табло создано для пользователя {user_id}")

    except Exception as e:
        logger.error(f"❌ Ошибка табло: {e}")
        await message.answer("❌ Ошибка загрузки курсов")

@router.callback_query(F.data == "update_rate")
async def update_rate_handler(callback: CallbackQuery, session: AsyncSession):
    """Обработчик кнопки 'Обновить курс'"""
    try:
        from app.services.queue_service import QueueService
        from app.services.notification_service import NotificationService

        queue_service = QueueService(session)
        # Передаем session в NotificationService
        notification_service = NotificationService(callback.bot, session)

        username = callback.from_user.username or callback.from_user.full_name
        success, queue_size = await queue_service.add_to_queue(callback.from_user.id, username)

        if success:
            # Передаем session в метод уведомления
            await notification_service.notify_admins_queue_full(session)

            if queue_size >= 3:
                message = "✅ Очередь заполнена! Админ уведомлен"
            else:
                message = f"✅ Вы в очереди! Ожидающих: {queue_size}/3"
        else:
            message = "⚠️ Вы уже в очереди!"

        await callback.answer(message, show_alert=True)

    except Exception as e:
        logger.error("Ошибка очереди: %s", e)
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

        logger.info("Обработка new_rate от пользователя %s: %s", user_id, text)

        if text == "/new_rate":
            # ... справка ...
            return

        rate_pairs = await parse_rate_input(text)
        logger.info("Распарсенные пары: %s", rate_pairs)

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
            current_rates = await multi_service.format_multi_rate_message()

            # ✅ РАСКОММЕНТИРУЙТЕ ЭТОТ БЛОК - уведомление очереди
            try:
                from app.services.notification_service import NotificationService
                notification_service = NotificationService(message.bot, session)
                await notification_service.notify_queue_users_rate_updated(current_rates)
                logger.info("✅ Уведомления отправлены очереди")
            except Exception as e:
                logger.error("❌ Ошибка уведомления очереди: %s", e)

            await message.answer(result_text)
            await message.answer(current_rates)
        else:
            await message.answer("❌ Не удалось обновить курсы")

    except Exception as e:
        logger.error("❌ Ошибка обработки курса: %s", e)
        await message.answer("❌ Ошибка обработки запроса")


async def parse_rate_input(text: str):
    """Парсит ввод курсов в разных форматах"""
    try:
        # Убираем команду если есть
        if text.startswith('/new_rate'):
            text = text.replace('/new_rate', '').strip()

        # Разделяем на отдельные пары по запятым
        pairs_text = [p.strip() for p in text.split(',') if p.strip()]

        results = []

        for pair_text in pairs_text:
            # Заменяем разные разделители на пробелы и запятые на точки
            normalized = pair_text.replace('/', ' ').replace('-', ' ').replace(',', ' ')
            # Заменяем десятичные запятые на точки
            normalized = normalized.replace(',', '.')
            parts = [p for p in normalized.split() if p]

            if len(parts) < 3:
                continue

            # Первые 3 части: валюта1, валюта2, курс покупки
            currency1 = parts[0].upper()
            currency2 = parts[1].upper()
            pair = f"{currency1}/{currency2}"

            try:
                buy_rate = float(parts[2].replace(',', '.'))  # Заменяем запятые на точки
                # Если есть 4-я часть - курс продажи
                if len(parts) >= 4:
                    sell_rate = float(parts[3].replace(',', '.'))  # Заменяем запятые на точки
                else:
                    sell_rate = buy_rate * 1.01  # Автоматический спред 1%

                results.append({
                    'pair': pair,
                    'buy': buy_rate,
                    'sell': sell_rate
                })

            except ValueError as e:
                logger.error("Ошибка преобразования числа: %s", e)
                continue

        return results

    except Exception as e:
        logger.error("Ошибка парсинга: %s", e)
        return []


@router.callback_query(F.data == "refresh_table")
async def refresh_table_handler(callback: CallbackQuery, session: AsyncSession):
    """Обработчик кнопки обновления табло"""
    try:
        multi_service = MultiRateService(session)
        message_text = await multi_service.format_multi_rate_message()

        # Редактируем текущее сообщение
        await callback.message.edit_text(
            text=message_text,
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
        await callback.answer("✅ Табло обновлено")

    except Exception as e:
        logger.error("Ошибка обновления табло: %s", e)
        await callback.answer("❌ Ошибка обновления")


@router.message(Command("remove_rate"))
async def remove_rate_handler(message: Message, session: AsyncSession):
    """Удаляет пару из табло"""
    try:
        text = message.text.replace('/remove_rate', '').strip().upper()
        if not text:
            await message.answer("❌ Укажите пару: /remove_rate USD/RUB")
            return

        multi_service = MultiRateService(session)
        success = await multi_service.remove_rate(text)

        if success:
            await message.answer(f"✅ Пара {text} удалена с табло")
        else:
            await message.answer(f"❌ Пара {text} не найдена")

    except Exception as e:
        logger.error("Ошибка удаления пары: %s", e)
        await message.answer("❌ Ошибка удаления")


@router.message(Command("clear_rates"))
async def clear_rates_handler(message: Message, session: AsyncSession):
    """Очищает все пары с табло"""
    try:
        multi_service = MultiRateService(session)
        success = await multi_service.clear_all_rates()

        if success:
            await message.answer("✅ Все курсы очищены")
        else:
            await message.answer("❌ Ошибка очистки")

    except Exception as e:
        logger.error("Ошибка очистки курсов: %s", e)
        await message.answer("❌ Ошибка очистки")