from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from app.dao.holder import HolderDao
from app.services.dashboard_sevice import DashboardService
from app.services.notification_service import NotificationService
from app.services.rapira_parser_service import RapiraParserService
from app.services.rbc_cash_service import RbcCashParserService  # Новый парсер
from app.services.rate_service import RateService  # Один курс
from app.services.multi_rate_service import MultiRateService  # Мультикурсы
from app.keyboards.main_menu import get_main_keyboard
from app.config.main import BotConfig
import logging

logger = logging.getLogger(__name__)

# Создаем роутер
router = Router()
user_last_table_message = {}


@router.message(Command("start"))
async def table_start(
        message: Message,
        session: AsyncSession,
        config: BotConfig,
        dashboard_service: DashboardService
):
    """Показывает/обновляет табло с разделенными курсами (парсер + админские)"""
    try:
        # Получаем отформатированное табло из нашего сервиса
        message_text = await dashboard_service.format_dashboard_message()

        user_id = message.from_user.id

        # Если есть предыдущее табло - редактируем его
        if user_id in user_last_table_message:
            try:
                await message.bot.edit_message_text(
                    chat_id=user_id,
                    message_id=user_last_table_message[user_id],
                    text=message_text,
                    reply_markup=get_main_keyboard(),
                    parse_mode="Markdown"
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
            parse_mode="Markdown"
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
        notification_service = NotificationService(callback.bot, session)

        username = callback.from_user.username or callback.from_user.full_name
        success, queue_size = await queue_service.add_to_queue(callback.from_user.id, username)

        if success:
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
            # Показываем справку
            help_text = """
📊 <b>Добавление курсов</b>

<b>Форматы:</b>
• <code>USD/RUB 82.80 83.30</code>
• <code>EUR/RUB 89.50 90.10</code>  
• <code>CNY/RUB 11.20 11.40</code>

<b>Несколько пар через запятые:</b>
• <code>USD/RUB 82.80 83.30, EUR/RUB 89.50 90.10</code>

<b>Автоматический спред:</b>
• <code>USD/RUB 82.80</code> → 82.80 / 83.63 (+1%)
            """
            await message.answer(help_text, parse_mode="HTML")
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
            await session.commit()
            if success:
                results.append(f"✅ {pair}: {buy_rate}/{sell_rate}")
            else:
                results.append(f"❌ {pair}: ошибка обновления")

        # Формируем итоговое сообщение
        if results:
            result_text = "📊 **Результат обновления:**\n" + "\n".join(results)

            # Получаем обновленное табло через DashboardService
            dashboard_service = DashboardService(session)
            current_rates = await dashboard_service.format_dashboard_message()

            # Уведомляем очередь
            try:
                from app.services.notification_service import NotificationService
                notification_service = NotificationService(message.bot, session)
                await notification_service.notify_queue_users_rate_updated(current_rates)
                logger.info("✅ Уведомления отправлены очереди")
            except Exception as e:
                logger.error("❌ Ошибка уведомления очереди: %s", e)

            await message.answer(result_text)
            await message.answer(current_rates, parse_mode="Markdown")
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
            # Заменяем разные разделители на пробелы
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
                buy_rate = float(parts[2].replace(',', '.'))
                # Если есть 4-я часть - курс продажи
                if len(parts) >= 4:
                    sell_rate = float(parts[3].replace(',', '.'))
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
async def refresh_table_handler(
        callback: CallbackQuery,
        session: AsyncSession,
        dashboard_service: DashboardService  # Добавляем зависимость
):
    """Обработчик кнопки обновления табло"""
    try:
        message_text = await dashboard_service.format_dashboard_message()

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

# ИСПРАВЬТЕ эти строки в table_handlers.py:

@router.message(Command("обновить_рапиру"))
async def update_rapira_manual(
        message: Message,
        session: AsyncSession,
        dashboard_service: DashboardService
):
    """Ручное обновление курсов RAPIRA"""
    try:
        # УБЕРИТЕ СКОБКИ - передавайте session, а не session()
        rapira_parser = RapiraParserService(session)  # БЫЛО: session()
        success = await rapira_parser.update_rapira_rates()

        if success:
            # Получаем обновленное табло
            message_text = await dashboard_service.format_dashboard_message()
            await message.answer("✅ Курсы RAPIRA обновлены вручную!")
            await message.answer(message_text, parse_mode="Markdown")
        else:
            await message.answer("❌ Ошибка обновления курсов RAPIRA")
    except Exception as e:
        logger.error(f"❌ Ошибка ручного обновления RAPIRA: {e}")
        await message.answer("❌ Ошибка обновления RAPIRA")


@router.message(Command("обновить_рбк"))
async def update_rbc_cash_manual(
        message: Message,
        session: AsyncSession,
        dashboard_service: DashboardService
):
    """Ручное обновление курсов RBC Cash"""
    try:
        # УБЕРИТЕ СКОБКИ - передавайте session, а не session()
        rbc_parser = RbcCashParserService(session)  # БЫЛО: session()
        rates = await rbc_parser.update_rbc_cash_rates()

        if rates:
            # Получаем обновленное табло
            message_text = await dashboard_service.format_dashboard_message()
            await message.answer(f"✅ RBC Cash обновлен! Получено {len(rates)} курсов")
            await message.answer(message_text, parse_mode="Markdown")
        else:
            await message.answer("❌ Не удалось обновить RBC Cash")
    except Exception as e:
        logger.error(f"❌ Ошибка ручного обновления RBC Cash: {e}")
        await message.answer("❌ Ошибка обновления RBC Cash")


@router.message(Command("обновить_все"))
async def update_all_parsers(
        message: Message,
        session: AsyncSession,
        dashboard_service: DashboardService
):
    """Обновление всех парсеров одновременно"""
    try:
        results = []

        # УБЕРИТЕ СКОБКИ
        rapira_parser = RapiraParserService(session)  # БЫЛО: session()
        rapira_success = await rapira_parser.update_rapira_rates()
        results.append(f"RAPIRA: {'✅' if rapira_success else '❌'}")

        # УБЕРИТЕ СКОБКИ
        rbc_parser = RbcCashParserService(session)  # БЫЛО: session()
        rbc_rates = await rbc_parser.update_rbc_cash_rates()
        results.append(f"RBC Cash: {'✅' if rbc_rates else '❌'}")

        # Формируем итоговое сообщение
        result_text = "🔄 <b>Результат обновления парсеров:</b>\n" + "\n".join(results)

        # Получаем обновленное табло
        message_text = await dashboard_service.format_dashboard_message()

        await message.answer(result_text, parse_mode="HTML")
        await message.answer(message_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"❌ Ошибка обновления всех парсеров: {e}")
        await message.answer("❌ Ошибка обновления парсеров")


@router.message(Command("статус_парсеров"))
async def parsers_status(
        message: Message,
        session: AsyncSession,
        dashboard_service: DashboardService
):
    """Показывает статус всех парсеров"""
    try:
        from app.dao.parsed_rate import ParsedRateDAO

        # Создаем DAO с сессией
        parsed_rate_dao = ParsedRateDAO(session)

        # Получаем последние курсы по источникам
        rapira_rates = await parsed_rate_dao.get_active_rates_by_source('rapira')
        rbc_rates = await parsed_rate_dao.get_active_rates_by_source('rbc_cash')

        status_text = "📊 <b>СТАТУС ПАРСЕРОВ</b>\n\n"

        # RAPIRA статус
        if rapira_rates:
            latest_rapira = max(rapira_rates, key=lambda x: x.updated_at)
            time_diff = await dashboard_service.get_time_diff(latest_rapira.updated_at)
            status_text += f"🤖 <b>RAPIRA</b>: ✅ Активен\n"
            status_text += f"   Последнее обновление: {time_diff} мин назад\n"
            status_text += f"   Курсы: {len(rapira_rates)} пар\n"
        else:
            status_text += f"🤖 <b>RAPIRA</b>: ❌ Нет данных\n"

        status_text += "\n"

        # RBC Cash статус
        if rbc_rates:
            latest_rbc = max(rbc_rates, key=lambda x: x.updated_at)
            time_diff = await dashboard_service.get_time_diff(latest_rbc.updated_at)
            status_text += f"🏦 <b>RBC Cash</b>: ✅ Активен\n"
            status_text += f"   Последнее обновление: {time_diff} мин назад\n"
            status_text += f"   Курсы: {len(rbc_rates)} пар\n"
        else:
            status_text += f"🏦 <b>RBC Cash</b>: ❌ Нет данных\n"

        await message.answer(status_text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"❌ Ошибка получения статуса парсеров: {e}")
        await message.answer("❌ Ошибка получения статуса")