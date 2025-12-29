"""
Тестовый скрипт для парсера Banki.ru
Запуск: python test_banki_parser.py

Для полной версии с кликами по "Показать еще":
1. Установите Playwright: pip install playwright
2. Установите браузеры: playwright install chromium
3. Скрипт автоматически использует Playwright для загрузки всех курсов

Без Playwright скрипт получит только первые 10 курсов через HTTP.
"""
import asyncio
import sys
from pathlib import Path
import time

# Добавляем путь к проекту
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import aiohttp
from bs4 import BeautifulSoup
import re
import logging
from typing import Dict, Optional, List

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def parse_banki_rates_playwright() -> Optional[List[Dict]]:
    """
    Парсит курсы с banki.ru используя Playwright для клика по кнопке "Показать еще"
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error("❌ Playwright не установлен. Установите: pip install playwright && playwright install chromium")
        return None
    
    try:
        url = "https://www.banki.ru/products/currency/cash/moskva/"
        
        logger.info(f"🔍 Загружаем страницу: {url}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()
            
            logger.info("📡 Открываем страницу...")
            # Используем 'load' вместо 'networkidle' - страница может постоянно делать запросы
            await page.goto(url, wait_until='load', timeout=30000)
            await asyncio.sleep(3)  # Дополнительная пауза для загрузки контента
            
            logger.info("✅ Страница загружена")
            
            # Кликаем по кнопке "Показать еще" пока список растет
            max_clicks = 60
            click_count = 0
            no_progress = 0
            items_locator = page.locator('div[data-test="currency__rates-form__result-item"]')
            button_locator = page.locator('a[data-test="button"]:has-text("Показать еще")')
            
            while click_count < max_clicks:
                try:
                    if await button_locator.count() == 0:
                        logger.info("ℹ️ Кнопка 'Показать еще' не найдена, возможно все загружено")
                        break
                    
                    button = button_locator.first
                    if not await button.is_visible():
                        logger.info("ℹ️ Кнопка 'Показать еще' не видна")
                        break
                    
                    before_count = await items_locator.count()
                    
                    await button.scroll_into_view_if_needed()
                    await asyncio.sleep(0.5)
                    await button.click()
                    click_count += 1
                    
                    logger.info(f"🖱️ Клик #{click_count} по кнопке 'Показать еще' (элементов было: {before_count})")
                    
                    try:
                        await page.wait_for_function(
                            "(before) => document.querySelectorAll('div[data-test=\"currency__rates-form__result-item\"]').length > before",
                            arg=before_count,
                            timeout=10000,
                        )
                    except Exception:
                        pass
                    
                    after_count = await items_locator.count()
                    if after_count <= before_count:
                        no_progress += 1
                        logger.info(f"📊 Прогресса нет: {after_count} (попытка {no_progress}/2)")
                        if no_progress >= 2:
                            break
                    else:
                        no_progress = 0
                    
                    await asyncio.sleep(1.0)
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка при клике: {e}")
                    break
            
            logger.info(f"✅ Завершено кликов: {click_count}")
            
            # Получаем финальный HTML
            html = await page.content()
            
            # Сохраняем HTML для отладки
            debug_file = project_root / 'banki_debug.html'
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(html)
            logger.info(f"💾 HTML сохранён в {debug_file}")
            
            await browser.close()
            
            # Парсим HTML
            soup = BeautifulSoup(html, 'html.parser')
            results = _parse_banki_html(soup)
            
            return results
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка парсинга Banki.ru: {e}", exc_info=True)
        return []


def _parse_banki_html(soup: BeautifulSoup) -> List[Dict]:
    """Парсит HTML и извлекает курсы"""
    results: List[Dict] = []
    
    # Ищем все контейнеры с банками
    bank_items = soup.find_all('div', {'data-test': 'currency__rates-form__result-item'})
    
    logger.info(f"🔍 Найдено элементов с data-test='currency__rates-form__result-item': {len(bank_items)}")
    
    if not bank_items:
        logger.warning("⚠️ Основной селектор не сработал")
        return []
    
    import re
    
    for idx, bank_item in enumerate(bank_items):
        try:
            # Извлекаем название банка
            bank_name_elem = bank_item.find('div', {'data-test': 'currenct--result-item--name'})
            if not bank_name_elem:
                link_elem = bank_item.find('a', {'data-test': 'currency--result-item--logo'})
                if link_elem:
                    img_elem = link_elem.find('img')
                    if img_elem:
                        bank_name = img_elem.get('alt', f'Банк #{idx + 1}')
                    else:
                        bank_name = f'Банк #{idx + 1}'
                else:
                    bank_name = f'Банк #{idx + 1}'
            else:
                bank_name = bank_name_elem.get_text(strip=True)
            
            # Извлекаем курс покупки
            buy_container = bank_item.find('div', {'data-test': 'currency--result-item---rate-buy'})
            buy_rate = None
            if buy_container:
                buy_text_elem = buy_container.find('div', {'data-test': 'text'})
                if buy_text_elem:
                    buy_text = buy_text_elem.get_text(strip=True)
                    buy_match = re.search(r'(\d+[,.]?\d*)', buy_text.replace(' ', ''))
                    if buy_match:
                        try:
                            buy_rate = float(buy_match.group(1).replace(',', '.'))
                        except (ValueError, AttributeError):
                            pass
            
            # Извлекаем курс продажи
            sell_container = bank_item.find('div', {'data-test': 'currency--result-item---rate-sell'})
            sell_rate = None
            if sell_container:
                sell_text_elem = sell_container.find('div', {'data-test': 'text'})
                if sell_text_elem:
                    sell_text = sell_text_elem.get_text(strip=True)
                    sell_match = re.search(r'(\d+[,.]?\d*)', sell_text.replace(' ', ''))
                    if sell_match:
                        try:
                            sell_rate = float(sell_match.group(1).replace(',', '.'))
                        except (ValueError, AttributeError):
                            pass
            
            # Если не нашли через основные селекторы, пробуем альтернативный поиск
            if not buy_rate and not sell_rate:
                all_text_divs = bank_item.find_all('div', {'data-test': 'text'})
                for text_div in all_text_divs:
                    text = text_div.get_text(strip=True)
                    match = re.search(r'(\d+[,.]?\d*)\s*[₽р]?', text)
                    if match:
                        try:
                            rate = float(match.group(1).replace(',', '.'))
                            if 50 <= rate <= 150:
                                if not buy_rate:
                                    buy_rate = rate
                                elif not sell_rate:
                                    sell_rate = rate
                        except (ValueError, AttributeError):
                            pass
            
            # Проверяем валидность курсов
            if buy_rate and 50 <= buy_rate <= 150:
                results.append({
                    'bank': bank_name,
                    'currency': 'USD',
                    'buy': buy_rate,
                    'sell': sell_rate if sell_rate and 50 <= sell_rate <= 150 else None,
                    'address': ''
                })
            elif sell_rate and 50 <= sell_rate <= 150:
                results.append({
                    'bank': bank_name,
                    'currency': 'USD',
                    'buy': None,
                    'sell': sell_rate,
                    'address': ''
                })
                
        except Exception as e:
            logger.debug(f"Ошибка парсинга элемента банка #{idx + 1}: {e}")
            continue
    
    return results


async def parse_banki_rates() -> Optional[List[Dict]]:
    """
    Парсит курсы наличных с banki.ru
    Использует Selenium для клика по кнопке "Показать еще"
    """
    # Пробуем использовать Playwright
    try:
        results = await parse_banki_rates_playwright()
        if results:
            return results
    except Exception as e:
        logger.warning(f"⚠️ Playwright не доступен: {e}")
        logger.info("🔄 Пробуем простой HTTP запрос (только первые курсы)...")
    
    # Fallback на простой HTTP запрос (только первые курсы без клика)
    try:
        url = "https://www.banki.ru/products/currency/cash/moskva/"
        
        async with aiohttp.ClientSession() as session:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    logger.error(f"❌ Banki.ru вернул статус {response.status}")
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                results = _parse_banki_html(soup)
                
                if results:
                    logger.warning("⚠️ Получены только первые курсы (без клика по 'Показать еще')")
                    return results
                
    except Exception as e:
        logger.error(f"❌ Ошибка HTTP запроса: {e}")
    
    return []


def get_banki_best_rates(data: List[Dict]) -> Optional[Dict]:
    """Извлекает лучшие курсы из данных Banki.ru"""
    if not data:
        logger.warning("❌ Нет данных для анализа")
        return None
    
    # Фильтруем только USD
    usd_rates = [r for r in data if
                 r.get('currency', '').upper() == 'USD' and (r.get('buy') is not None or r.get('sell') is not None)]
    
    if not usd_rates:
        logger.warning("❌ Нет USD курсов")
        return None
    
    logger.info(f"🔍 Анализ {len(usd_rates)} записей USD")
    
    # Находим лучшие курсы
    buy_rates = [r for r in usd_rates if r.get('buy') is not None]
    sell_rates = [r for r in usd_rates if r.get('sell') is not None]
    
    best_buy = min(buy_rates, key=lambda x: x['buy']) if buy_rates else None
    best_sell = max(sell_rates, key=lambda x: x['sell']) if sell_rates else None
    
    if not best_buy and not best_sell:
        logger.error("❌ Не удалось найти курсы")
        return None
    
    # Если есть только один курс, используем его для обоих
    if best_buy and not best_sell:
        best_sell = best_buy
    elif best_sell and not best_buy:
        best_buy = best_sell
    
    result = {
        'buy_bank': {
            'name': best_buy.get('bank', 'Banki.ru') if best_buy else 'Banki.ru',
            'buy': best_buy.get('buy') if best_buy else best_sell.get('buy') if best_sell else None,
            'sell': best_buy.get('sell') if best_buy else best_sell.get('sell') if best_sell else None
        },
        'sell_bank': {
            'name': best_sell.get('bank', 'Banki.ru') if best_sell else 'Banki.ru',
            'buy': best_sell.get('buy') if best_sell else best_buy.get('buy') if best_buy else None,
            'sell': best_sell.get('sell') if best_sell else best_buy.get('sell') if best_buy else None
        }
    }
    
    logger.info(f"✅ Лучшие курсы:")
    logger.info(f"   Покупка: {result['buy_bank']['name']} - {result['buy_bank']['buy']} ₽")
    logger.info(f"   Продажа: {result['sell_bank']['name']} - {result['sell_bank']['sell']} ₽")
    
    return result


async def main():
    """Основная функция для тестирования"""
    print("=" * 60)
    print("🧪 ТЕСТ ПАРСЕРА BANKI.RU")
    print("=" * 60)
    print()
    
    # Парсим курсы
    rates = await parse_banki_rates()
    
    if rates:
        # Сохраняем результаты в JSON/CSV для последующего объединения с другими источниками
        try:
            from datetime import datetime
            import json
            import csv

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_file = f"banki_rates_{timestamp}.json"
            csv_file = f"banki_rates_{timestamp}.csv"

            rates_to_save = []
            for r in rates:
                if isinstance(r, dict):
                    rr = dict(r)
                    rr.setdefault("source", "Banki")
                    rates_to_save.append(rr)

            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(rates_to_save, f, ensure_ascii=False, indent=2)

            if rates_to_save:
                with open(csv_file, "w", encoding="utf-8", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=sorted(rates_to_save[0].keys()))
                    w.writeheader()
                    w.writerows(rates_to_save)

            print(f"\n💾 Сохранено: {json_file}")
            print(f"💾 Сохранено: {csv_file}")
        except Exception as e:
            print(f"\n⚠️ Не удалось сохранить файлы: {e}")

        print(f"\n✅ Успешно получено {len(rates)} курсов")
        
        # Извлекаем лучшие
        best = get_banki_best_rates(rates)
        
        if best:
            print("\n📊 Лучшие курсы:")
            print(f"   Покупка: {best['buy_bank']['name']} - {best['buy_bank']['buy']} ₽")
            print(f"   Продажа: {best['sell_bank']['name']} - {best['sell_bank']['sell']} ₽")
    else:
        print("\n❌ Не удалось получить курсы")
        print("💡 Проверьте файл banki_debug.html для анализа HTML структуры")


if __name__ == "__main__":
    asyncio.run(main())
