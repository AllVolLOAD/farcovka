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
_banki_cache: Optional[List[Dict]] = None


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
    """Получает лучшие курсы РБК через Selenium с сортировкой."""
    import time
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(45)
        
        try:
            # Инициализируем debug log
            debug_log = []
            
            # Определяем функции заранее
            def extract_num(text: str) -> Optional[float]:
                import re
                if not text:
                    return None
                t = text.replace('\xa0', ' ').replace(',', '.').strip()
                m = re.search(r"\d+[.]?\d*", t)
                return float(m.group(0)) if m else None
            
            def get_row_data(row_elem):
                """Извлекает данные из строки"""
                try:
                    name_el = row_elem.find_element(By.CSS_SELECTOR, '.quote__office__one__name')
                    name = name_el.text.strip()
                    
                    # Пропускаем аэропорты (грабительские курсы)
                    airports = ['ВНУКОВО', 'ДОМОДЕДОВО', 'ШЕРЕМЕТЬЕВО', 'ЖУКОВСКИЙ', 'АЭРОПОРТ']
                    if any(airport in name.upper() for airport in airports):
                        return None
                    
                    buy_el = row_elem.find_element(By.CSS_SELECTOR, '.quote__office__one__buy')
                    sell_el = row_elem.find_element(By.CSS_SELECTOR, '.quote__office__one__sell')
                    
                    # РБК: buy и sell уже в перспективе клиента (проверено вручную)
                    buy = extract_num(buy_el.text)  # клиент покупает
                    sell = extract_num(sell_el.text)  # клиент продает
                    
                    return {'bank': name, 'currency': 'USD', 'buy': buy, 'sell': sell, 'address': ''}
                except Exception:
                    return None
            
            # Собираем данные с первых 3 страниц
            all_valid = []
            
            for page_num in range(1, 4):  # Страницы 1, 2, 3
                url = f"https://cash.rbc.ru/cash/?currency=3&city=1&diapason=3&page={page_num}"
                driver.get(url)
                WebDriverWait(driver, 30).until(lambda d: d.execute_script('return document.readyState') == 'complete')
                time.sleep(2)
                
                # Переключаем на профессиональную версию если нужно (только на 1-й странице)
                if page_num == 1:
                    try:
                        toggle = driver.find_element(By.CSS_SELECTOR, '.js-toggle-versions-text')
                        if 'Профессиональная' in toggle.text:
                            driver.execute_script("arguments[0].click();", toggle)
                            time.sleep(2)
                            logger.info("Переключились на профессиональную версию")
                            debug_log.append("✅ Переключились на проф версию")
                    except Exception:
                        logger.debug("Проф версия уже активна или кнопка не найдена")
                
                # Собираем строки с текущей страницы
                rows = driver.find_elements(By.CSS_SELECTOR, '.quote__office__one.js-one-office')
                debug_log.append(f"Страница {page_num}: найдено строк {len(rows)}")
                
                page_count = 0
                for i in range(len(rows)):
                    data = get_row_data(rows[i])
                    if data:
                        all_valid.append(data)
                        page_count += 1
                
                debug_log.append(f"  Собрано с страницы {page_num}: {page_count} валидных")
            
            debug_log.append("")
            debug_log.append(f"ИТОГО собрано {len(all_valid)} валидных записей со всех страниц")
            debug_log.append("ВСЕ валидные записи:")
            for i, d in enumerate(all_valid, 1):
                debug_log.append(f"  {i}. {d['bank']}: buy={d['buy']}, sell={d['sell']}")
            debug_log.append("")
            
            # Используем первые 3 как эталон (точнее)
            ref_buy = [r['buy'] for r in all_valid[:3] if r.get('buy')]
            ref_sell = [r['sell'] for r in all_valid[:3] if r.get('sell')]
            
            avg_buy = sum(ref_buy) / len(ref_buy) if ref_buy else 81
            avg_sell = sum(ref_sell) / len(ref_sell) if ref_sell else 83
            
            debug_log.append(f"Эталон (средний из первых 3): buy={avg_buy:.2f}, sell={avg_sell:.2f}")
            
            # Фильтруем ±1 рубль от эталона (точнее)
            filtered = [r for r in all_valid 
                        if r.get('buy') and r.get('sell')
                        and abs(r['buy'] - avg_buy) <= 1
                        and abs(r['sell'] - avg_sell) <= 1]
            
            debug_log.append(f"После фильтрации ±1 руб: {len(filtered)}")
            debug_log.append("ВСЕ отфильтрованные записи:")
            for i, d in enumerate(filtered, 1):
                debug_log.append(f"  {i}. {d['bank']}: buy={d['buy']}, sell={d['sell']}")
            debug_log.append("")
            
            # Сортируем отфильтрованные по buy (минимальный = лучший для клиента - дешевле купить)
            sorted_by_buy = sorted([r for r in filtered if r.get('buy')], key=lambda x: x['buy'])
            # Сортируем по sell (МАКСИМАЛЬНЫЙ = лучший для клиента - дороже продать)
            sorted_by_sell = sorted([r for r in filtered if r.get('sell')], key=lambda x: x['sell'], reverse=True)
            
            best_buy_data = sorted_by_buy[0] if sorted_by_buy else None
            best_sell_data = sorted_by_sell[0] if sorted_by_sell else None
            
            if best_buy_data:
                debug_log.append(f"✅ Лучший buy (Python sort): {best_buy_data['bank']} - buy={best_buy_data['buy']}, sell={best_buy_data['sell']}")
                logger.info(f"📈 Лучший курс покупки: {best_buy_data['bank']} - buy={best_buy_data['buy']}, sell={best_buy_data['sell']}")
            
            if best_sell_data:
                debug_log.append(f"✅ Лучший sell (Python sort): {best_sell_data['bank']} - buy={best_sell_data['buy']}, sell={best_sell_data['sell']}")
                logger.info(f"📉 Лучший курс продажи: {best_sell_data['bank']} - buy={best_sell_data['buy']}, sell={best_sell_data['sell']}")
            
            # Формируем результат
            results = []
            if best_buy_data:
                results.append(best_buy_data)
            if best_sell_data and best_sell_data != best_buy_data:
                results.append(best_sell_data)
            
            debug_log.append(f"Итого возвращаем {len(results)} записей")
            
            # Сохраняем детальный лог в файл
            try:
                with open('rbc_selenium_debug.txt', 'w', encoding='utf-8') as f:
                    f.write('\n'.join(debug_log))
                logger.info("📋 Детальный лог сохранён в rbc_selenium_debug.txt")
            except Exception:
                pass
            
            logger.info(f"📊 Итого возвращаем {len(results)} записей РБК")
            return results
            
        finally:
            try:
                driver.quit()
            except Exception:
                pass
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

        # Не пропускаем строки, только баннеры фильтруем ниже
        rows_filtered = rows
        
        for row in rows_filtered:
            # Пропускаем рекламные баннеры
            if row.get('data-banner') or 'banner' in str(row.get('class', [])).lower():
                continue
            
            # Пропускаем скрытые элементы
            style = row.get('style', '')
            if 'display:none' in style or 'display: none' in style or 'visibility:hidden' in style:
                continue
            
            # Проверяем класс на hidden
            classes = row.get('class', [])
            if any('hidden' in str(c).lower() for c in classes):
                continue
            
            name_el = row.select_one('.quote__office__one__name')
            buy_el = row.select_one('.quote__office__one__buy')
            sell_el = row.select_one('.quote__office__one__sell')

            name = name_el.get_text(strip=True) if name_el else ''
            
            # Для первых 5 записей логируем сырой текст элементов
            if len(results) < 5:
                buy_text = buy_el.get_text() if buy_el else 'None'
                sell_text = sell_el.get_text() if sell_el else 'None'
                logger.info(f"🔍 DEBUG Playwright #{len(results)+1} {name}: buy_raw_text='{buy_text}', sell_raw_text='{sell_text}'")
            
            # РБК показывает buy/sell с точки зрения банка, меняем местами для клиента
            buy_raw = extract_num(buy_el.get_text()) if buy_el else None
            sell_raw = extract_num(sell_el.get_text()) if sell_el else None
            buy = sell_raw  # То что РБК называет "sell" = buy для клиента
            sell = buy_raw  # То что РБК называет "buy" = sell для клиента

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
    Извлекает лучшие курсы из уже отфильтрованных данных РБК.
    Данные приходят после сортировки Selenium: 1-2 записи с лучшими курсами.
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

    logger.info(f"🔍 Получено {len(usd_rates)} отфильтрованных записей от парсера")
    
    # Логируем что получили
    for i, rate in enumerate(usd_rates, 1):
        logger.info(f"  {i}. {rate.get('bank', 'N/A')}: buy={rate.get('buy')}, sell={rate.get('sell')}")
    
    # Парсер вернул 2 записи: 1-я = лучший buy (после клика "Покупка"), 2-я = лучший sell (после клика "Продажа")
    # Просто возвращаем как есть, без дополнительной обработки
    if len(usd_rates) >= 2:
        result = {
            'buy_bank': {
                'name': clean_bank_name(usd_rates[0]['bank']),
                'buy': usd_rates[0]['buy'],
                'sell': usd_rates[0]['sell']
            },
            'sell_bank': {
                'name': clean_bank_name(usd_rates[1]['bank']),
                'buy': usd_rates[1]['buy'],
                'sell': usd_rates[1]['sell']
            }
        }
        logger.info(f"✅ Два банка: {result['buy_bank']['name']} {result['buy_bank']['buy']}/{result['buy_bank']['sell']} | {result['sell_bank']['name']} {result['sell_bank']['buy']}/{result['sell_bank']['sell']}")
        return result
    elif len(usd_rates) == 1:
        # Если получена только одна запись - используем её для обоих
        logger.warning("⚠️ Получена только 1 запись, используем для обоих курсов")
        result = {
            'buy_bank': {
                'name': clean_bank_name(usd_rates[0]['bank']),
                'buy': usd_rates[0]['buy'],
                'sell': usd_rates[0]['sell']
            },
            'sell_bank': {
                'name': clean_bank_name(usd_rates[0]['bank']),
                'buy': usd_rates[0]['buy'],
                'sell': usd_rates[0]['sell']
            }
        }
        return result
    
    logger.error("❌ Не удалось найти банки")
    return None


async def parse_banki_rates() -> Optional[List[Dict]]:
    """
    Парсит курсы наличных с banki.ru
    
    Структура HTML:
    - Контейнер банка: <div data-test="currency__rates-form__result-item">
    - Название банка: <div data-test="currenct--result-item--name">
    - Курс покупки: <div data-test="currency--result-item---rate-buy"> → <div data-test="text">79,70 ₽</div>
    - Курс продажи: <div data-test="currency--result-item---rate-sell"> → <div data-test="text">81,50 ₽</div>
    
    Returns:
        Список словарей с курсами:
        [
            {
                'bank': 'Название банка',
                'currency': 'USD',
                'buy': 79.70,  # курс покупки (клиент покупает)
                'sell': 81.50,  # курс продажи (клиент продает)
                'address': ''
            }
        ]
    """
    global _banki_cache
    
    # Пробуем использовать Playwright для полной загрузки
    try:
        from playwright.async_api import async_playwright
        import asyncio
        
        url = "https://www.banki.ru/products/currency/cash/moskva/"
        
        logger.info(f"🔍 Загружаем страницу Banki.ru: {url}")
        
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
            
            await page.goto(url, wait_until='load', timeout=30000)
            await asyncio.sleep(3)  # Пауза для загрузки контента
            
            # Кликаем по кнопке "Показать еще" несколько раз
            max_clicks = 10
            click_count = 0
            
            while click_count < max_clicks:
                try:
                    button = await page.query_selector('a[data-test="button"]:has-text("Показать еще")')
                    if not button:
                        button = await page.query_selector('xpath=//a[contains(text(), "Показать еще")]')
                    
                    if button and await button.is_visible():
                        await button.scroll_into_view_if_needed()
                        await asyncio.sleep(1)
                        await button.click()
                        click_count += 1
                        logger.debug(f"🖱️ Клик #{click_count} по кнопке 'Показать еще'")
                        await asyncio.sleep(2 + (click_count * 0.5))
                        try:
                            await page.wait_for_load_state('load', timeout=10000)
                        except:
                            pass
                        await asyncio.sleep(2)
                    else:
                        break
                except Exception as e:
                    logger.debug(f"Ошибка при клике: {e}")
                    break
            
            html = await page.content()
            await browser.close()
            
            # Парсим HTML
            soup = BeautifulSoup(html, 'html.parser')
            results = _parse_banki_html(soup)
            
            if results:
                _banki_cache = results
                logger.info(f"✅ Получено {len(results)} курсов USD с Banki.ru (кликов: {click_count})")
                return results
            
    except ImportError:
        logger.warning("⚠️ Playwright не установлен, используем простой HTTP запрос")
    except Exception as e:
        logger.warning(f"⚠️ Ошибка Playwright парсинга Banki.ru: {e}, пробуем HTTP fallback")
    
    # Fallback на простой HTTP запрос
    try:
        url = "https://www.banki.ru/products/currency/cash/moskva/"
        
        async with aiohttp.ClientSession() as session:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status != 200:
                    return _banki_cache or []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                results = _parse_banki_html(soup)
                
                if results:
                    _banki_cache = results
                    logger.info(f"✅ Получено {len(results)} курсов USD с Banki.ru (HTTP fallback)")
                    return results
    except Exception as e:
        logger.error(f"❌ Ошибка HTTP парсинга Banki.ru: {e}")
    
    return _banki_cache or []


def _parse_banki_html(soup: BeautifulSoup) -> List[Dict]:
    """Парсит HTML и извлекает курсы"""
    results: List[Dict] = []
    
    bank_items = soup.find_all('div', {'data-test': 'currency__rates-form__result-item'})
    
    if not bank_items:
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
                    bank_name = img_elem.get('alt', f'Банк #{idx + 1}') if img_elem else f'Банк #{idx + 1}'
                else:
                    bank_name = f'Банк #{idx + 1}'
            else:
                bank_name = bank_name_elem.get_text(strip=True)
            
            # Извлекаем курсы
            buy_rate = None
            sell_rate = None
            
            # Пробуем основные селекторы
            buy_container = bank_item.find('div', {'data-test': 'currency--result-item---rate-buy'})
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
            
            sell_container = bank_item.find('div', {'data-test': 'currency--result-item---rate-sell'})
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
            
            # Если не нашли, пробуем альтернативный поиск
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
            
            # Добавляем запись
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
        except Exception:
            continue
    
    return results


def get_banki_best_rates(data: List[Dict]) -> Optional[Dict]:
    """
    Извлекает лучшие курсы из данных Banki.ru.
    Аналогично get_rbc_best_rates - возвращает лучший buy и лучший sell.
    """
    if not data:
        logger.warning("❌ Нет данных для анализа Banki.ru")
        return None
    
    # Фильтруем только USD
    usd_rates = [r for r in data if
                 r.get('currency', '').upper() == 'USD' and (r.get('buy') is not None or r.get('sell') is not None)]
    
    if not usd_rates:
        logger.warning("❌ Нет USD курсов в данных Banki.ru")
        return None
    
    logger.info(f"🔍 Получено {len(usd_rates)} записей от парсера Banki.ru")
    
    # Находим лучшие курсы
    # Лучший buy = минимальный (дешевле купить)
    # Лучший sell = максимальный (дороже продать)
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
    
    logger.info(f"✅ Banki.ru: {result['buy_bank']['name']} buy={result['buy_bank']['buy']}, sell={result['buy_bank']['sell']}")
    return result