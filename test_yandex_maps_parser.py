"""
Парсер Яндекс Карт для получения данных о точках обмена валют
Запуск: python test_yandex_maps_parser.py

Для полной версии с прокруткой страницы:
1. Установите Playwright: pip install playwright
2. Установите браузеры: playwright install chromium
3. Скрипт автоматически использует Playwright для загрузки всех точек

Без Playwright скрипт получит только первые результаты через HTTP.
"""
import asyncio
import sys
from pathlib import Path
import json
import csv
from datetime import datetime

# Добавляем путь к проекту
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import aiohttp
from bs4 import BeautifulSoup
import logging
from typing import Dict, Optional, List

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def parse_yandex_maps_playwright(search_query: str = "Обмен валюты") -> Optional[List[Dict]]:
    """
    Парсит точки обмена валют с Яндекс Карт используя Playwright для прокрутки страницы
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error("❌ Playwright не установлен. Установите: pip install playwright && playwright install chromium")
        return None
    
    try:
        # URL для поиска обмена валют в Москве
        url = f"https://yandex.ru/maps/213/moscow/search/{search_query}"
        
        logger.info(f"🔍 Загружаем страницу: {url}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,  # Показываем браузер для более естественного поведения
                args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-blink-features=AutomationControlled']
            )
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='ru-RU',
                timezone_id='Europe/Moscow',
                permissions=['geolocation'],
                geolocation={'latitude': 55.7558, 'longitude': 37.6173},  # Москва
                extra_http_headers={
                    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                }
            )
            page = await context.new_page()
            
            # Убираем признаки автоматизации
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.navigator.chrome = {
                    runtime: {},
                };
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
            """)
            
            logger.info("📡 Открываем страницу...")
            await page.goto(url, wait_until='networkidle', timeout=60000)
            await asyncio.sleep(10)  # Дополнительная пауза для загрузки контента и прохождения капчи
            
            logger.info("✅ Страница загружена")
            
            # Проверяем, не показывается ли капча
            captcha_check = await page.evaluate("""
                () => {
                    const title = document.title;
                    const hasCaptcha = title.includes('робот') || title.includes('robot') || 
                                     document.querySelector('#checkbox-captcha-form') !== null;
                    return hasCaptcha;
                }
            """)
            
            if captcha_check:
                logger.warning("⚠️ Обнаружена капча! Пожалуйста, пройдите проверку вручную в открывшемся браузере.")
                logger.info("⏳ Ожидаем прохождения капчи (до 60 секунд)...")
                # Ждем, пока капча не исчезнет или не пройдет 60 секунд
                for i in range(60):
                    await asyncio.sleep(1)
                    captcha_check = await page.evaluate("""
                        () => {
                            const title = document.title;
                            const hasCaptcha = title.includes('робот') || title.includes('robot') || 
                                             document.querySelector('#checkbox-captcha-form') !== null;
                            return hasCaptcha;
                        }
                    """)
                    if not captcha_check:
                        logger.info("✅ Капча пройдена!")
                        await asyncio.sleep(5)  # Дополнительная пауза после прохождения капчи
                        break
                    if i % 10 == 0 and i > 0:
                        logger.info(f"⏳ Ожидание... ({i}/60 секунд)")
                else:
                    logger.warning("⚠️ Капча не была пройдена, продолжаем...")
            
            # Ждем появления списка результатов
            logger.info("⏳ Ожидаем загрузки списка результатов...")
            try:
                await page.wait_for_selector('ul.search-list-view__list', timeout=15000)
                logger.info("✅ Список результатов найден")
            except:
                logger.warning("⚠️ Список результатов не найден, продолжаем...")
            
            # Дополнительная пауза для загрузки первых элементов
            await asyncio.sleep(3)
            
            # Проверяем начальное количество элементов
            initial_count = await page.evaluate("""
                () => {
                    const items = document.querySelectorAll('li.search-snippet-view');
                    let count = 0;
                    items.forEach(item => {
                        if (!item.querySelector('.search-snippet-view__placeholder')) {
                            count++;
                        }
                    });
                    return count;
                }
            """)
            logger.info(f"📊 Начальное количество элементов: {initial_count}")
            
            if initial_count == 0:
                logger.warning("⚠️ Элементы не найдены, возможно страница загружается...")
                await asyncio.sleep(5)  # Дополнительная пауза
                initial_count = await page.evaluate("""
                    () => {
                        const items = document.querySelectorAll('li.search-snippet-view');
                        let count = 0;
                        items.forEach(item => {
                            if (!item.querySelector('.search-snippet-view__placeholder')) {
                                count++;
                            }
                        });
                        return count;
                    }
                """)
                logger.info(f"📊 Количество элементов после ожидания: {initial_count}")
            
            # Прокручиваем страницу до конца для загрузки всех результатов
            logger.info("📜 Прокручиваем страницу для загрузки всех результатов...")
            
            import random
            
            last_items_count = initial_count
            scroll_attempts = 0
            max_scroll_attempts = 1000  # Максимальное количество попыток прокрутки
            no_change_count = 0
            max_no_change = 10  # Количество попыток без изменений перед остановкой
            
            while scroll_attempts < max_scroll_attempts:
                # Считаем количество элементов в списке (исключая placeholder)
                items_count = await page.evaluate("""
                    () => {
                        const items = document.querySelectorAll('li.search-snippet-view');
                        let count = 0;
                        items.forEach(item => {
                            // Пропускаем placeholder элементы
                            if (!item.querySelector('.search-snippet-view__placeholder')) {
                                count++;
                            }
                        });
                        return count;
                    }
                """)
                
                # Получаем текущую позицию прокрутки и высоту страницы
                scroll_info = await page.evaluate("""
                    () => {
                        return {
                            scrollTop: window.pageYOffset || document.documentElement.scrollTop,
                            scrollHeight: document.body.scrollHeight,
                            clientHeight: window.innerHeight
                        };
                    }
                """)
                
                current_height = scroll_info['scrollHeight']
                current_scroll = scroll_info['scrollTop']
                viewport_height = scroll_info['clientHeight']
                
                # Прокручиваем плавно, не сразу до конца (как человек)
                # Прокручиваем на 80% высоты экрана за раз
                scroll_step = int(viewport_height * 0.8)
                target_scroll = current_scroll + scroll_step
                
                # Плавная прокрутка с анимацией
                await page.evaluate(f"""
                    window.scrollTo({{
                        top: {target_scroll},
                        behavior: 'smooth'
                    }});
                """)
                
                # Случайная пауза между 3-6 секундами для более естественного поведения
                pause_time = random.uniform(3.0, 6.0)
                await asyncio.sleep(pause_time)
                
                # Проверяем количество элементов после прокрутки
                new_items_count = await page.evaluate("""
                    () => {
                        const items = document.querySelectorAll('li.search-snippet-view');
                        let count = 0;
                        items.forEach(item => {
                            if (!item.querySelector('.search-snippet-view__placeholder')) {
                                count++;
                            }
                        });
                        return count;
                    }
                """)
                
                # Если количество элементов не изменилось
                if new_items_count == last_items_count:
                    no_change_count += 1
                    logger.info(f"📊 Элементов: {new_items_count}, без изменений: {no_change_count}/{max_no_change}")
                    
                    if no_change_count >= max_no_change:
                        logger.info(f"✅ Новые данные перестали добавляться. Всего элементов: {new_items_count}")
                        break
                else:
                    # Если количество изменилось, сбрасываем счетчик
                    if new_items_count > last_items_count:
                        logger.info(f"📈 Найдено новых элементов: {new_items_count - last_items_count} (всего: {new_items_count})")
                    no_change_count = 0
                    last_items_count = new_items_count
                
                scroll_attempts += 1
                
                if scroll_attempts % 10 == 0:
                    logger.info(f"📜 Прокрутка #{scroll_attempts}, элементов: {new_items_count}, без изменений: {no_change_count}")
            
            if scroll_attempts >= max_scroll_attempts:
                logger.warning(f"⚠️ Достигнут лимит прокруток ({max_scroll_attempts}), но данные могли не загрузиться полностью")
            
            logger.info(f"✅ Завершена прокрутка после {scroll_attempts} попыток")
            
            # Дополнительная пауза для завершения загрузки
            await asyncio.sleep(3)
            
            # Получаем финальный HTML
            html = await page.content()
            
            # Сохраняем HTML для отладки
            debug_file = project_root / 'yandex_maps_debug.html'
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(html)
            logger.info(f"💾 HTML сохранён в {debug_file}")
            
            await browser.close()
            
            # Парсим HTML
            soup = BeautifulSoup(html, 'html.parser')
            results = _parse_yandex_maps_html(soup)
            
            return results
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка парсинга Яндекс Карт: {e}", exc_info=True)
        return []


def _parse_yandex_maps_html(soup: BeautifulSoup) -> List[Dict]:
    """Парсит HTML и извлекает данные о точках обмена валют"""
    results: List[Dict] = []
    
    # Ищем все элементы с точками обмена валют
    # Основной селектор: <li class="search-snippet-view">
    exchange_points = soup.find_all('li', class_='search-snippet-view')
    
    logger.info(f"🔍 Найдено элементов с классом 'search-snippet-view': {len(exchange_points)}")
    
    if not exchange_points:
        logger.warning("⚠️ Основной селектор не сработал")
        return []
    
    for idx, point in enumerate(exchange_points):
        try:
            # Пропускаем placeholder элементы
            if point.find('div', class_='search-snippet-view__placeholder'):
                continue
            
            # Извлекаем данные из data-атрибутов
            body_div = point.find('div', class_='search-snippet-view__body')
            if not body_div:
                continue
            
            point_id = body_div.get('data-id', '')
            coordinates = body_div.get('data-coordinates', '')
            
            # Извлекаем название
            title_elem = point.find('div', class_='search-business-snippet-view__title')
            name = title_elem.get_text(strip=True) if title_elem else ''
            
            # Извлекаем адрес
            address_elem = point.find('a', class_='search-business-snippet-view__address')
            address = address_elem.get_text(strip=True) if address_elem else ''
            
            # Извлекаем рейтинг
            rating_elem = point.find('span', class_='business-rating-badge-view__rating-text')
            rating = rating_elem.get_text(strip=True) if rating_elem else ''
            
            # Извлекаем количество оценок
            reviews_elem = point.find('span', class_='business-rating-amount-view')
            reviews_count = reviews_elem.get_text(strip=True) if reviews_elem else ''
            
            # Извлекаем статус работы
            status_elem = point.find('div', class_='business-working-status-view')
            working_status = status_elem.get_text(strip=True) if status_elem else ''
            
            # Извлекаем ссылку на организацию
            link_elem = point.find('a', class_='link-overlay')
            org_url = ''
            if link_elem:
                href = link_elem.get('href', '')
                if href:
                    org_url = f"https://yandex.ru{href}" if href.startswith('/') else href
            
            # Извлекаем категории
            categories = []
            category_elems = point.find_all('a', class_='search-business-snippet-view__category')
            for cat_elem in category_elems:
                cat_text = cat_elem.get_text(strip=True)
                if cat_text:
                    categories.append(cat_text)
            
            # Проверяем, что это действительно точка обмена валют
            if not name or 'обмен' not in name.lower() and 'валюта' not in name.lower():
                # Проверяем категории
                is_currency_exchange = any('обмен' in cat.lower() or 'валюта' in cat.lower() 
                                         for cat in categories)
                if not is_currency_exchange:
                    continue
            
            # Парсим координаты
            lat, lon = None, None
            if coordinates:
                try:
                    coords = coordinates.split(',')
                    if len(coords) == 2:
                        lon = float(coords[0].strip())
                        lat = float(coords[1].strip())
                except (ValueError, AttributeError):
                    pass
            
            # Парсим рейтинг в число
            rating_value = None
            if rating:
                try:
                    rating_value = float(rating.replace(',', '.'))
                except (ValueError, AttributeError):
                    pass
            
            # Парсим количество оценок
            reviews_num = None
            if reviews_count:
                try:
                    # Убираем слово "оценок" или "оценки" и извлекаем число
                    import re
                    match = re.search(r'(\d+)', reviews_count)
                    if match:
                        reviews_num = int(match.group(1))
                except (ValueError, AttributeError):
                    pass
            
            result = {
                'id': point_id,
                'name': name,
                'address': address,
                'rating': rating_value,
                'rating_text': rating,
                'reviews_count': reviews_num,
                'reviews_text': reviews_count,
                'working_status': working_status,
                'latitude': lat,
                'longitude': lon,
                'coordinates': coordinates,
                'url': org_url,
                'categories': ', '.join(categories) if categories else '',
            }
            
            results.append(result)
            
        except Exception as e:
            logger.debug(f"Ошибка парсинга элемента #{idx + 1}: {e}")
            continue
    
    logger.info(f"✅ Успешно извлечено {len(results)} точек обмена валют")
    return results


async def parse_yandex_maps(search_query: str = "Обмен валюты") -> Optional[List[Dict]]:
    """
    Парсит точки обмена валют с Яндекс Карт
    """
    # Пробуем использовать Playwright
    try:
        results = await parse_yandex_maps_playwright(search_query)
        if results:
            return results
    except Exception as e:
        logger.warning(f"⚠️ Playwright не доступен: {e}")
        logger.info("🔄 Пробуем простой HTTP запрос (только первые результаты)...")
    
    # Fallback на простой HTTP запрос (только первые результаты без прокрутки)
    try:
        url = f"https://yandex.ru/maps/213/moscow/search/{search_query}"
        
        async with aiohttp.ClientSession() as session:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    logger.error(f"❌ Яндекс Карты вернули статус {response.status}")
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                results = _parse_yandex_maps_html(soup)
                
                if results:
                    logger.warning("⚠️ Получены только первые результаты (без прокрутки страницы)")
                    return results
                
    except Exception as e:
        logger.error(f"❌ Ошибка HTTP запроса: {e}")
    
    return []


def save_results_to_file(results: List[Dict], output_file: Optional[str] = None):
    """Сохраняет результаты в файл (JSON и CSV)"""
    if not results:
        logger.warning("⚠️ Нет данных для сохранения")
        return
    
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"yandex_maps_results_{timestamp}"
    
    # Сохраняем в JSON
    json_file = project_root / f"{output_file}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.info(f"💾 JSON сохранён в {json_file}")
    
    # Сохраняем в CSV
    csv_file = project_root / f"{output_file}.csv"
    if results:
        fieldnames = results[0].keys()
        with open(csv_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        logger.info(f"💾 CSV сохранён в {csv_file}")


async def main():
    """Основная функция для тестирования"""
    print("=" * 60)
    print("🧪 ТЕСТ ПАРСЕРА ЯНДЕКС КАРТ")
    print("=" * 60)
    print()
    
    search_query = "Обмен валюты"
    
    # Парсим точки обмена валют
    results = await parse_yandex_maps(search_query)
    
    if results:
        print(f"\n✅ Успешно получено {len(results)} точек обмена валют")
        
        # Выводим первые 5 результатов для примера
        print("\n📊 Первые 5 результатов:")
        for i, result in enumerate(results[:5], 1):
            print(f"\n{i}. {result.get('name', 'N/A')}")
            print(f"   Адрес: {result.get('address', 'N/A')}")
            print(f"   Рейтинг: {result.get('rating_text', 'N/A')} ({result.get('reviews_text', 'N/A')})")
            print(f"   Статус: {result.get('working_status', 'N/A')}")
            if result.get('coordinates'):
                print(f"   Координаты: {result.get('coordinates')}")
        
        # Сохраняем результаты в файл
        save_results_to_file(results)
        
    else:
        print("\n❌ Не удалось получить данные")
        print("💡 Проверьте файл yandex_maps_debug.html для анализа HTML структуры")


if __name__ == "__main__":
    asyncio.run(main())

