"""
Парсеры курсов валют ЦБ РФ и РБК
"""
import json
from datetime import datetime
from typing import Dict, Optional, List
import aiohttp
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

# Кэш для хранения последних данных
_cbr_cache: Optional[Dict] = None
_rbc_cache: Optional[List[Dict]] = None


async def parse_cbr_rates() -> Optional[Dict]:
    """
    Парсит официальные курсы ЦБ РФ
    
    Returns:
        {
            'date': '2024-01-15',
            'valutes': {
                'USD': {'name': 'Доллар США', 'course': 95.50}
            }
        }
    """
    global _cbr_cache
    
    try:
        # API ЦБ РФ
        url = "https://www.cbr-xml-daily.ru/daily_json.js"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    # У ЦБ content-type: application/javascript, разрешаем парсинг
                    data = await response.json(content_type=None)
                    
                    result = {
                        'date': data.get('Date', datetime.now().strftime('%Y-%m-%d')),
                        'valutes': {}
                    }
                    
                    # Извлекаем USD
                    if 'Valute' in data:
                        for code, valute in data['Valute'].items():
                            if code == 'USD':
                                result['valutes']['USD'] = {
                                    'name': valute.get('Name', 'Доллар США'),
                                    'course': valute.get('Value', 0)
                                }
                    
                    _cbr_cache = result
                    logger.info(f"✅ Получены курсы ЦБ: USD={result['valutes'].get('USD', {}).get('course', 0)}")
                    return result
                    
    except Exception as e:
        logger.error(f"❌ Ошибка парсинга ЦБ: {e}")
        # Возвращаем кэш если есть
        return _cbr_cache
    
    return None


async def parse_rbc_rates() -> Optional[List[Dict]]:
    """
    Парсит курсы наличных с РБК, используя только headless браузеры:
    1) Selenium → 2) Playwright. Если оба недоступны — возвращает кэш/пусто.
    """
    global _rbc_cache

    try:
        # 1) Selenium
        try:
            rates_s = await _parse_rbc_rates_selenium()
            if rates_s:
                # Фильтруем только USD и валидные записи
                filtered_rates = [
                    r for r in rates_s
                    if r.get('currency') == 'USD' and (r.get('buy') is not None or r.get('sell') is not None)
                ]
                if filtered_rates:
                    _rbc_cache = filtered_rates
                    logger.info(f"✅ Получено {len(filtered_rates)} курсов USD с РБК (Selenium)")
                    return filtered_rates
        except Exception as e:
            logger.debug(f"Selenium недоступен/ошибка: {e}")

        # 2) Playwright
        try:
            rates_p = await _parse_rbc_rates_playwright()
            if rates_p:
                # Фильтруем только USD и валидные записи
                filtered_rates = [
                    r for r in rates_p
                    if r.get('currency') == 'USD' and (r.get('buy') is not None or r.get('sell') is not None)
                ]
                if filtered_rates:
                    _rbc_cache = filtered_rates
                    logger.info(f"✅ Получено {len(filtered_rates)} курсов USD с РБК (Playwright)")
                    return filtered_rates
        except Exception as e:
            logger.debug(f"Playwright недоступен/ошибка: {e}")

        logger.warning("⚠️ РБК недоступен (Selenium и Playwright не сработали)")
        return _rbc_cache or []
    except Exception as e:
        logger.error(f"❌ Ошибка парсинга РБК: {e}", exc_info=True)
        return _rbc_cache or []


async def _parse_rbc_rates_selenium() -> List[Dict]:
    """Пытается получить курсы через Selenium. Возвращает список записей или пустой список."""
    try:
        # Импорты лениво, чтобы не требовать зависимостей всегда
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-software-rasterizer')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(45)
        try:
            url = "https://cash.rbc.ru/cash/"
            driver.get(url)
            WebDriverWait(driver, 30).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            # небольшая задержка для динамики
            try:
                WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.quote__office__one')))
            except Exception:
                pass

            html = driver.page_source
        finally:
            try:
                driver.quit()
            except Exception:
                pass

        soup = BeautifulSoup(html, 'html.parser')
        rows = soup.select('.quote__office__one.js-one-office') or soup.select('.quote__office__one')
        results: List[Dict] = []

        def extract_num(text: str) -> Optional[float]:
            import re
            if not text:
                return None
            t = text.replace('\xa0', ' ').replace(',', '.').strip()
            m = re.search(r"\d+[.]?\d*", t)
            return float(m.group(0)) if m else None

        for row in rows:
            name_el = row.select_one('.quote__office__one__name')
            buy_el = row.select_one('.quote__office__one__buy')
            sell_el = row.select_one('.quote__office__one__sell')

            name = name_el.get_text(strip=True) if name_el else ''
            buy = extract_num(buy_el.get_text()) if buy_el else None
            sell = extract_num(sell_el.get_text()) if sell_el else None

            # Извлекаем адрес если есть
            address = ''
            address_el = row.select_one('.quote__office__one__address')
            if address_el:
                address = address_el.get_text(strip=True)

            if name and (buy is not None or sell is not None):
                results.append({
                    'bank': name,
                    'currency': 'USD',
                    'buy': buy,
                    'sell': sell,
                    'address': address
                })

        # фильтрация только USD записей и уникализация
        uniq = []
        seen = set()
        for r in results:
            key = (r['bank'], r['buy'], r['sell'])
            if key not in seen:
                seen.add(key)
                uniq.append(r)
        return uniq
    except Exception as e:
        logger.debug(f"Selenium fallback failed: {e}")
        return []


async def _parse_rbc_rates_playwright() -> List[Dict]:
    """Пытается получить курсы через Playwright. Возвращает список записей или пустой список."""
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            try:
                await page.goto('https://cash.rbc.ru/cash/', timeout=45000)
                # ожидание таблицы/элементов
                try:
                    await page.wait_for_selector('.quote__office__one', timeout=10000)
                except Exception:
                    pass
                html = await page.content()
            finally:
                await browser.close()

        soup = BeautifulSoup(html, 'html.parser')
        rows = soup.select('.quote__office__one.js-one-office') or soup.select('.quote__office__one')
        results: List[Dict] = []

        def extract_num(text: str) -> Optional[float]:
            import re
            if not text:
                return None
            t = text.replace('\xa0', ' ').replace(',', '.').strip()
            m = re.search(r"\d+[.]?\d*", t)
            return float(m.group(0)) if m else None

        for row in rows:
            name_el = row.select_one('.quote__office__one__name')
            buy_el = row.select_one('.quote__office__one__buy')
            sell_el = row.select_one('.quote__office__one__sell')

            name = name_el.get_text(strip=True) if name_el else ''
            buy = extract_num(buy_el.get_text()) if buy_el else None
            sell = extract_num(sell_el.get_text()) if sell_el else None

            # Извлекаем адрес если есть
            address = ''
            address_el = row.select_one('.quote__office__one__address')
            if address_el:
                address = address_el.get_text(strip=True)

            if name and (buy is not None or sell is not None):
                results.append({
                    'bank': name,
                    'currency': 'USD',
                    'buy': buy,
                    'sell': sell,
                    'address': address
                })

        uniq = []
        seen = set()
        for r in results:
            key = (r['bank'], r['buy'], r['sell'])
            if key not in seen:
                seen.add(key)
                uniq.append(r)
        return uniq
    except Exception as e:
        logger.debug(f"Playwright fallback failed: {e}")
        return []


def get_cbr_usd_rate(data: Dict) -> Optional[float]:
    """Извлекает курс USD из данных ЦБ"""
    if data and 'valutes' in data:
        usd = data['valutes'].get('USD')
        if usd:
            return usd.get('course')
    return None


def get_rbc_best_rates(data: List[Dict]) -> Optional[Dict]:
    """
    Находит банки с лучшими курсами покупки и продажи из РБК
    """

    def clean_bank_name(bank_name: str) -> str:
        """
        Очищает название банка от юридических обозначений и аббревиатур
        """
        if not bank_name:
            return ""

        # Убираем юридические обозначения в скобках и кавычках
        import re

        # Убираем (АО), (ПАО) и т.д.
        cleaned = re.sub(r'\([А-Я]+\)', '', bank_name)

        # Убираем КБ ", " в кавычках
        cleaned = cleaned.replace('КБ "', '').replace('"', '')

        # Убираем ДО " и ДО « с кавычками, но оставляем номер отделения
        cleaned = re.sub(r'ДО\s*["«]([^"»]*)["»]', r'\1', cleaned)

        # Убираем отдельные аббревиатуры ДО, но оставляем номера
        cleaned = re.sub(r'\bДО\b', '', cleaned)

        # Убираем ПАО, АО, ОАО, ЗАО как отдельные слова
        cleaned = re.sub(r'\b(ПАО|АО|ОАО|ЗАО|КБ)\b', '', cleaned)

        # Убираем лишние пробелы
        cleaned = ' '.join(cleaned.split())

        # Убираем запятые в начале и конце
        cleaned = cleaned.strip(' ,')

        return cleaned

    if not data:
        logger.warning("❌ Нет данных для анализа РБК")
        return None

    # Фильтруем только USD
    usd_rates = [r for r in data if
                 r.get('currency', '').upper() == 'USD' or 'USD' in str(r.get('currency', '')).upper()]

    if not usd_rates:
        logger.warning("❌ Нет USD курсов в данных РБК")
        return None

    logger.info(f"🔍 Анализируем {len(usd_rates)} записей РБК")

    # Находим банк с лучшим курсом покупки (максимальный buy)
    best_buy_record = None
    for rate in usd_rates:
        if rate.get('buy') is not None:
            if best_buy_record is None or rate['buy'] > best_buy_record['buy']:
                best_buy_record = rate

    # Находим банк с лучшим курсом продажи (минимальный sell)
    best_sell_record = None
    for rate in usd_rates:
        if rate.get('sell') is not None:
            if best_sell_record is None or rate['sell'] < best_sell_record['sell']:
                best_sell_record = rate

    # Логируем найденные записи для отладки
    if best_buy_record:
        logger.info(f"🏆 Лучший курс покупки: {best_buy_record['bank']} - {best_buy_record['buy']}")
    else:
        logger.warning("⚠️ Не найден лучший курс покупки")

    if best_sell_record:
        logger.info(f"🏆 Лучший курс продажи: {best_sell_record['bank']} - {best_sell_record['sell']}")
    else:
        logger.warning("⚠️ Не найден лучший курс продажи")

    if best_buy_record and best_sell_record:
        buy_bank_clean = clean_bank_name(best_buy_record.get('bank', ''))
        sell_bank_clean = clean_bank_name(best_sell_record.get('bank', ''))

        result = {
            'buy': best_buy_record['buy'],
            'sell': best_sell_record['sell'],
            'buy_rate': best_buy_record['buy'],
            'sell_rate': best_sell_record['sell'],
            'buy_bank': buy_bank_clean,
            'sell_bank': sell_bank_clean,
            'buy_bank_original': best_buy_record.get('bank', ''),
            'sell_bank_original': best_sell_record.get('bank', ''),
            'buy_address': best_buy_record.get('address', ''),
            'sell_address': best_sell_record.get('address', '')
        }
        logger.info(
            f"✅ Сформирован результат: {result['buy_bank']} {result['buy_rate']} / {result['sell_bank']} {result['sell_rate']}")
        return result

    # Fallback если нет обоих курсов
    if best_buy_record:
        buy_bank_clean = clean_bank_name(best_buy_record.get('bank', ''))
        result = {
            'buy': best_buy_record['buy'],
            'sell': best_buy_record['buy'] * 1.01,
            'buy_rate': best_buy_record['buy'],
            'sell_rate': best_buy_record['buy'] * 1.01,
            'buy_bank': buy_bank_clean,
            'sell_bank': buy_bank_clean,
            'buy_bank_original': best_buy_record.get('bank', ''),
            'sell_bank_original': best_buy_record.get('bank', ''),
            'buy_address': best_buy_record.get('address', ''),
            'sell_address': best_buy_record.get('address', '')
        }
        logger.warning(f"⚠️ Используем fallback (только покупка): {result['buy_rate']} / {result['sell_rate']}")
        return result

    if best_sell_record:
        sell_bank_clean = clean_bank_name(best_sell_record.get('bank', ''))
        result = {
            'buy': best_sell_record['sell'] * 0.99,
            'sell': best_sell_record['sell'],
            'buy_rate': best_sell_record['sell'] * 0.99,
            'sell_rate': best_sell_record['sell'],
            'buy_bank': sell_bank_clean,
            'sell_bank': sell_bank_clean,
            'buy_bank_original': best_sell_record.get('bank', ''),
            'sell_bank_original': best_sell_record.get('bank', ''),
            'buy_address': best_sell_record.get('address', ''),
            'sell_address': best_sell_record.get('address', '')
        }
        logger.warning(f"⚠️ Используем fallback (только продажа): {result['buy_rate']} / {result['sell_rate']}")
        return result

    logger.error("❌ Не удалось найти ни одного валидного курса")
    return None