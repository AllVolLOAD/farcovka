"""
Пример интеграции парсеров в бот
Можно использовать в Telegram боте или другом мессенджере
"""

import asyncio
from datetime import datetime
from currency_parsers import parse_cbr_rates, parse_rbc_rates


# ========== ФУНКЦИИ ДЛЯ БОТА ==========

async def update_cbr_rates_task():
    """
    Задача для периодического обновления курсов ЦБ РФ
    Запускается раз в час
    """
    while True:
        try:
            print(f"[{datetime.now()}] Обновление курсов ЦБ РФ...")
            data = parse_cbr_rates()
            
            if data:
                # Здесь можно отправить данные в базу данных бота
                # или сохранить в кэш для быстрого доступа
                usd_rate = data['valutes'].get('USD', {}).get('course', 0)
                eur_rate = data['valutes'].get('EUR', {}).get('course', 0)
                print(f"✓ Курсы обновлены: USD={usd_rate}, EUR={eur_rate}")
            else:
                print("✗ Не удалось получить курсы ЦБ")
                
        except Exception as e:
            print(f"✗ Ошибка обновления ЦБ: {e}")
        
        # Ждем 1 час (3600 секунд)
        await asyncio.sleep(3600)


async def update_rbc_rates_task():
    """
    Задача для периодического обновления курсов РБК
    Запускается раз в час
    Внимание: РБК парсер медленнее (использует браузер)
    """
    while True:
        try:
            print(f"[{datetime.now()}] Обновление курсов РБК...")
            data = parse_rbc_rates()
            
            if data:
                # Здесь можно отправить данные в базу данных бота
                print(f"✓ Получено {len(data)} записей с РБК")
            else:
                print("✗ Не удалось получить курсы РБК")
                
        except Exception as e:
            print(f"✗ Ошибка обновления РБК: {e}")
        
        # Ждем 1 час (3600 секунд)
        await asyncio.sleep(3600)


# ========== ФУНКЦИИ ДЛЯ ОТВЕТОВ БОТА ==========

def get_cbr_rate_message(currency_code: str = 'USD') -> str:
    """
    Формирует сообщение с курсом валюты ЦБ РФ
    
    Args:
        currency_code: Код валюты (USD, EUR, CNY и т.д.)
    
    Returns:
        str: Текст сообщения
    """
    try:
        import json
        with open('cbr_rates.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        valute = data['valutes'].get(currency_code.upper())
        if not valute:
            return f"❌ Валюта {currency_code} не найдена"
        
        return (
            f"💱 Курс {valute['name']} ({currency_code.upper()})\n"
            f"📊 Официальный курс ЦБ РФ: {valute['course']:.2f} руб.\n"
            f"📅 Дата: {data['date']}"
        )
    except FileNotFoundError:
        return "❌ Данные курсов еще не загружены. Подождите немного."
    except Exception as e:
        return f"❌ Ошибка: {e}"


def get_rbc_best_rates_message() -> str:
    """
    Формирует сообщение с лучшими курсами наличных с РБК
    
    Returns:
        str: Текст сообщения
    """
    try:
        import json
        with open('rbc_rates.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not data:
            return "❌ Данные курсов еще не загружены."
        
        # Находим лучшие курсы
        best_buy = max((r for r in data if r.get('buy')), key=lambda x: x['buy'], default=None)
        best_sell = min((r for r in data if r.get('sell')), key=lambda x: x['sell'], default=None)
        
        message = "💵 Лучшие курсы наличных (РБК):\n\n"
        
        if best_buy:
            message += f"💰 Лучший курс ПРОДАЖИ валюты:\n"
            message += f"🏦 {best_buy['bank']}\n"
            message += f"📈 {best_buy['buy']:.2f} руб.\n\n"
        
        if best_sell:
            message += f"💸 Лучший курс ПОКУПКИ валюты:\n"
            message += f"🏦 {best_sell['bank']}\n"
            message += f"📉 {best_sell['sell']:.2f} руб."
        
        return message
    except FileNotFoundError:
        return "❌ Данные курсов еще не загружены. Подождите немного."
    except Exception as e:
        return f"❌ Ошибка: {e}"


# ========== ПРИМЕР ИСПОЛЬЗОВАНИЯ ==========

async def main():
    """
    Пример запуска задач обновления курсов
    В реальном боте эти задачи запускаются в фоне
    """
    print("Запуск задач обновления курсов...")
    print("Они будут обновляться раз в час\n")
    
    # Запускаем обе задачи параллельно
    await asyncio.gather(
        update_cbr_rates_task(),
        update_rbc_rates_task()
    )


if __name__ == "__main__":
    # Для тестирования запустим один раз каждую функцию
    print("Тестовый запуск парсеров...\n")
    
    # Тест ЦБ (быстрый)
    print("=" * 60)
    print("1. Тест парсера ЦБ РФ")
    print("=" * 60)
    cbr_data = parse_cbr_rates()
    if cbr_data:
        print(f"✓ Получено {len(cbr_data['valutes'])} валют")
        print(f"Пример сообщения:\n{get_cbr_rate_message('USD')}\n")
    
    # Тест РБК (медленный - можно закомментировать для быстрого теста)
    # print("=" * 60)
    # print("2. Тест парсера РБК")
    # print("=" * 60)
    # rbc_data = parse_rbc_rates()
    # if rbc_data:
    #     print(f"✓ Получено {len(rbc_data)} записей")
    #     print(f"Пример сообщения:\n{get_rbc_best_rates_message()}")


