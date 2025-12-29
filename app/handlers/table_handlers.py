from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command

from app.services.notification_service import NotificationService
from app.services.rate_service import RateService  # Один курс
from app.services.multi_rate_service import MultiRateService  # Мультикурсы
from app.keyboards.main_menu import get_main_keyboard
from app.config.main import BotConfig
import logging
from app.keyboards.main_menu import get_main_keyboard, get_main_reply_keyboard


logger = logging.getLogger(__name__)

# Создаем роутер
router = Router()
user_last_table_message = {}

user_last_table_message = {}


@router.message(Command("wallet"))
async def open_wallet_command(message: Message):
    """Открывает Mini App кошелька"""
    try:
        # TODO: Replace with actual Mini App URL after deployment
        miniapp_url = "https://yourdomain.com/miniapp"  # Change in production
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="🪙 Открыть кошелёк",
                web_app=WebAppInfo(url=miniapp_url)
            )
        ]])
        
        wallet_message = (
            "💼 <b>FarCovka Wallet</b>\n\n"
            "🔐 Non-custodial кошелёк с WalletConnect\n"
            "⚡ Sepolia Testnet\n"
            "💱 Создание ордеров buy/sell\n\n"
            "Нажмите кнопку ниже для открытия:"
        )
        
        await message.answer(wallet_message, reply_markup=keyboard, parse_mode="HTML")
        logger.info(f"✅ Wallet Mini App opened for user {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"❌ Error opening wallet: {e}")
        await message.answer("❌ Ошибка открытия кошелька. Попробуйте позже.")


@router.message(Command("start"))
async def table_start(message: Message, session: AsyncSession, config: BotConfig):
    """Показывает табло с мультикурсами и устанавливает Reply-клавиатуру"""
    try:
        multi_service = MultiRateService(session)
        message_text = await multi_service.format_multi_rate_message()

        user_id = message.from_user.id

        # Всегда отправляем новое сообщение с табло
        new_message = await message.answer(
            message_text,
            reply_markup=get_main_keyboard(),  # Инлайн-кнопки табло
            parse_mode="Markdown"
        )

        # КРИТИЧЕСКИ ВАЖНО: сохраняем ID сообщения
        user_last_table_message[user_id] = new_message.message_id
        logger.info(f"💾 Сохранен ID сообщения {new_message.message_id} для пользователя {user_id}")

        logger.info(
            f"📄 Новое табло создано для пользователя {user_id}. Всего пользователей: {len(user_last_table_message)}")

    except Exception as e:
        logger.error(f"❌ Ошибка табло: {e}")
        await message.answer("❌ Ошибка загрузки курсов")


@router.callback_query(F.data == "update_rate")
async def update_rate_handler(callback: CallbackQuery, session: AsyncSession):
    """Обработчик кнопки 'Обновить курс' - отправляет уведомление админу"""
    try:
        user_id = callback.from_user.id
        username = callback.from_user.username or callback.from_user.first_name or "Пользователь"
        
        # Отвечаем пользователю
        await callback.answer("📨 Запрос отправлен админу", show_alert=False)
        
        # Отправляем уведомление админам
        admin_ids = [7111883883, 780245577]  # Список админов
        
        notification_text = (
            f"🔔 <b>Запрос на обновление курсов</b>\n\n"
            f"👤 Пользователь: {username} (ID: {user_id})\n"
            f"⏰ Время: {callback.message.date.strftime('%H:%M:%S')}\n\n"
            f"💬 Используйте команду <code>/update_rates</code> для запуска парсеров"
        )
        
        from app.services.notification_service import NotificationService
        notification_service = NotificationService(callback.bot, session)
        
        sent_count = 0
        for admin_id in admin_ids:
            try:
                await callback.bot.send_message(
                    admin_id,
                    notification_text,
                    parse_mode="HTML"
                )
                sent_count += 1
                logger.info(f"✅ Уведомление отправлено админу {admin_id}")
            except Exception as e:
                logger.error(f"❌ Ошибка отправки админу {admin_id}: {e}")
        
        logger.info(f"📨 Запрос на обновление курсов от пользователя {user_id}, уведомлений отправлено: {sent_count}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки запроса обновления: {e}")
        await callback.answer("❌ Ошибка отправки запроса", show_alert=True)


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
            await message.answer("❌ Укажите пары: `USD/RUB 82.80 83.30` или `USD/RUB 82.80 83.30, EUR/RUB 89.50 90.20`")
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

            # ДОБАВИМ ДЕТАЛЬНУЮ ОТЛАДКУ
            logger.info(f"🔄 Сохраняем курс в БД: {pair} buy={buy_rate} sell={sell_rate}")

            success = await multi_service.update_rate(
                pair=pair,
                buy_rate=buy_rate,
                sell_rate=sell_rate,
                admin_id=user_id
            )

            logger.info(f"📊 Результат сохранения {pair}: {success}")

            if success:
                results.append(f"✅ {pair}: {buy_rate}/{sell_rate}")
            else:
                results.append(f"❌ {pair}: ошибка обновления")

        # Формируем итоговое сообщение
        if results:
            result_text = "📊 **Результат обновления:**\n" + "\n".join(results)

            # ПОЛУЧАЕМ ОБНОВЛЕННОЕ ТАБЛО
            current_rates = await multi_service.format_multi_rate_message()
            logger.info(f"📈 Обновленное табло: {current_rates}")

            # КРИТИЧЕСКИ ВАЖНО: ОБНОВЛЯЕМ ТАБЛО У ВСЕХ ПОЛЬЗОВАТЕЛЕЙ
            updated_count = 0
            for user_id, message_id in list(user_last_table_message.items()):
                try:
                    await message.bot.edit_message_text(
                        chat_id=user_id,
                        message_id=message_id,
                        text=current_rates,
                        reply_markup=get_main_keyboard(),
                        parse_mode="Markdown"
                    )
                    updated_count += 1
                    logger.info(f"✅ Табло обновлено для пользователя {user_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось обновить табло для {user_id}: {e}")
                    # Удаляем устаревшее сообщение из кэша
                    del user_last_table_message[user_id]

            logger.info(f"📊 Табло обновлено для {updated_count} пользователей")

            # Уведомление очереди
            try:
                from app.services.notification_service import NotificationService
                notification_service = NotificationService(message.bot, session)
                await notification_service.notify_queue_users_rate_updated(current_rates)
                logger.info("✅ Уведомления отправлены очереди")
            except Exception as e:
                logger.error("❌ Ошибка уведомления очереди: %s", e)

            await message.answer(result_text)

            # Если это новый пользователь, показываем ему табло
            if message.from_user.id not in user_last_table_message:
                new_message = await message.answer(
                    current_rates,
                    reply_markup=get_main_keyboard(),
                    parse_mode="Markdown"
                )
                user_last_table_message[message.from_user.id] = new_message.message_id

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

@router.message(Command("wallet"))
async def wallet_handler(message: Message):
    """Обработчик команды Кошелек"""
    wallet_text = """
💰 <b>Кошелек</b>

Ваши балансы:
💵 USD: 0.00
₽ RUB: 0.00

Раздел в разработке...
"""
    await message.answer(wallet_text, parse_mode="HTML")

@router.message(Command("rates"))
async def rates_handler(message: Message, session: AsyncSession):
    """Обработчик команды Табло - показывает актуальное табло"""
    await table_start(message, session, message.bot)

@router.message(Command("p2p"))
async def p2p_handler(message: Message):
    """Обработчик команды П2П"""
    p2p_text = """
🔁 <b>P2P Обмен</b>

Торговая площадка для обмена между пользователями.

Раздел в разработке...
"""
    await message.answer(p2p_text, parse_mode="HTML")

@router.message(Command("settings"))
async def settings_handler(message: Message):
    """Обработчик команды Настройки"""
    settings_text = f"""
⚙️ <b>Настройки</b>

ID: {message.from_user.id}
Имя: {message.from_user.first_name}

Раздел в разработке...
"""
    await message.answer(settings_text, parse_mode="HTML")