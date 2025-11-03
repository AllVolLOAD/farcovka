import json
import traceback
import tempfile
import os
import time
import shutil
import re

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import config


def setup_driver():
    """Настройка и инициализация Chrome драйвера"""
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless')  # раскомментировать для работы в фоне
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-software-rasterizer')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)

    # Дополнительные параметры для стабильности
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-browser-side-navigation')
    options.add_argument('--disable-features=VizDisplayCompositor')

    # Создаём уникальную временную директорию для каждой сессии
    import tempfile
    import os
    temp_dir = tempfile.mkdtemp(prefix='chrome_profile_')
    options.add_argument(f'--user-data-dir={temp_dir}')

    # Дополнительно указываем уникальную директорию для кэша
    cache_dir = os.path.join(temp_dir, 'cache')
    options.add_argument(f'--disk-cache-dir={cache_dir}')

    print(f"Инициализация Chrome с временной директорией: {temp_dir}")

    try:
        driver = webdriver.Chrome(options=options)
        # Сохраняем путь к временной директории для последующей очистки
        driver.temp_dir = temp_dir
    except Exception as e:
        print(f"Ошибка инициализации Chrome: {e}")
        print("Убедитесь, что ChromeDriver установлен и доступен в PATH")
        # Очищаем временную директорию при ошибке
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass
        raise

    driver.set_page_load_timeout(60)
    driver.set_script_timeout(60)

    return driver


def build_url(currency=None, city=None, diapason=None):
    """Построение URL с параметрами"""
    params = config.DEFAULT_PARAMS.copy()

    if currency is not None:
        params['currency'] = currency
    if city is not None:
        params['city'] = city
    if diapason is not None:
        params['diapason'] = diapason

    query_string = '&'.join([f"{key}={value}" for key, value in params.items()])
    return f"{config.BASE_URL}?{query_string}"


def wait_for_page_ready(driver, timeout=30):
    """Ожидание полной загрузки страницы"""
    try:
        # Ждем готовности DOM
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
        # Дополнительная пауза для выполнения JavaScript
        time.sleep(3)
        return True
    except Exception as e:
        print(f"Ошибка ожидания загрузки страницы: {e}")
        return False


def click_professional_version(driver):
    """Гарантировать режим 'Профессиональная версия'"""
    try:
        # Ждем загрузки страницы
        if not wait_for_page_ready(driver):
            return False

        wait = WebDriverWait(driver, config.ELEMENT_WAIT_TIMEOUT)

        # Пытаемся найти кнопку переключения версий
        try:
            toggle_button = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "js-toggle-versions-text"))
            )
            label = toggle_button.text.strip()

            # Если кнопка показывает 'Стандартная версия' — мы уже в проф. версии
            if 'Стандартная версия' in label:
                print("Уже в профессиональной версии, клик не нужен")
                return True

            # Иначе переключаемся на проф. версию
            btn = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "js-toggle-versions-text")))
            driver.execute_script("arguments[0].click();", btn)
            print("Переключаемся на профессиональную версию...")

            # Ждем пока появится разметка проф.версии
            time.sleep(2)
            return True
        except Exception:
            print("Кнопка переключения версий не найдена, продолжаем без переключения")
            return True

    except Exception as e:
        print(f"Ошибка при переключении версии: {e}")
        return True  # Продолжаем работу даже если не удалось переключить


def parse_rates_table(driver):
    """Парсинг таблицы с курсами"""
    try:
        print("Ожидаем загрузку таблицы...")

        # Увеличиваем время ожидания и используем более гибкую стратегию
        wait = WebDriverWait(driver, 30)

        # Пробуем разные селекторы
        selectors = [
            '.quote__office__row',
            '[class*="quote"][class*="office"][class*="row"]',
            '.quote__office',
            '[data-quote-id]',
            'div[class*="quote"]'
        ]

        element_found = False
        for selector in selectors:
            try:
                print(f"Пробуем селектор: {selector}")
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                print(f"Успешно найден элемент с селектором: {selector}")
                element_found = True
                break
            except Exception as e:
                print(f"Селектор {selector} не сработал: {str(e)[:100]}")
                continue

        if not element_found:
            print("ВНИМАНИЕ: Не удалось найти элементы таблицы с помощью стандартных селекторов")
            print("Пробуем работать с загруженным HTML...")

        # Дополнительная пауза для полной загрузки
        time.sleep(5)

        # Скроллим страницу для загрузки всех элементов
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)

        # Получаем HTML после загрузки
        html = driver.page_source

        # Сохраним HTML для отладки
        with open('page_content_debug.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("HTML сохранён в page_content_debug.html")

        soup = BeautifulSoup(html, 'html.parser')

        print("HTML загружен, начинаем парсинг...")

        # Пробуем разные селекторы для поиска строк
        # Правильный селектор: quote__office__one с классом js-one-office
        rows = soup.select('.quote__office__one.js-one-office')

        if not rows:
            print("Ищем по альтернативному селектору...")
            rows = soup.select('.quote__office__one')

        if not rows:
            print("Ищем по альтернативным селекторам...")
            rows = soup.find_all('div', class_=lambda x: x and 'quote__office__one' in ' '.join(x) if x else False)

        if not rows:
            # Еще одна попытка - ищем любые div с id office_id_
            rows = soup.find_all('div', id=lambda x: x and 'office_id_' in str(x))

        print(f"Найдено строк в HTML: {len(rows)}")

        if not rows:
            print("\n=== ОТЛАДКА: Структура страницы ===")
            all_quotes = soup.find_all('div', class_=lambda x: x and 'quote' in x.lower())
            print(f"Найдено div с 'quote' в классе: {len(all_quotes)}")
            if all_quotes:
                print("Первые 3 элемента:")
                for i, elem in enumerate(all_quotes[:3]):
                    print(f"{i + 1}. Классы: {elem.get('class')}")
                    print(f"   Текст: {elem.get_text(strip=True)[:100]}")

            tables = soup.find_all(['table', 'tbody', 'tr'])
            print(f"\nНайдено table/tbody/tr элементов: {len(tables)}")

            print("\nСтраница может требовать авторизации или изменила структуру")
            return []

        if rows and len(rows) > 0:
            print("Первая найденная строка:")
            print(rows[0].prettify()[:500])

        results = []
        for idx, row in enumerate(rows):
            # Пропускаем скрытые строки
            style = row.get('style', '')
            if 'display:none' in style or 'display: none' in style:
                continue

            # Пропускаем баннеры
            if row.find(attrs={'data-banner': True}):
                continue

            # Пропускаем заголовки таблицы (они имеют класс quote__office_head)
            classes = row.get('class', [])
            if 'quote__office_head' in classes or 'quote__office_head__one' in str(classes):
                continue

            # Ищем название банка - пробуем разные селекторы
            name_elem = (
                    row.select_one('.quote__office__one__name') or
                    row.select_one('div.quote__office__one__name') or
                    row.find('div', class_='quote__office__one__name')
            )
            
            # Если не найдено напрямую, пробуем альтернативные методы
            if not name_elem:
                name_elem = (
                    row.select_one('[class*="name"]') or
                    row.find('div', class_=lambda x: x and 'name' in x.lower() if x else False)
                )

            # Ищем курс покупки (buy - это курс, по которому банк ПРОДАЕТ валюту)
            buy_elem = (
                    row.select_one('.quote__office__cell.quote__office__one__buy') or
                    row.select_one('.quote__office__one__buy') or
                    row.select_one('[class*="buy"]') or
                    row.find('div', class_=lambda x: x and 'buy' in x.lower() if x else False)
            )

            # Ищем курс продажи (sell - это курс, по которому банк ПОКУПАЕТ валюту)
            sell_elem = (
                    row.select_one('.quote__office__cell.quote__office__one__sell') or
                    row.select_one('.quote__office__one__sell') or
                    row.select_one('[class*="sell"]') or
                    row.find('div', class_=lambda x: x and 'sell' in x.lower() if x else False)
            )

            def get_text(elem):
                if not elem:
                    return None
                # Получаем весь текст и очищаем от лишних символов
                text = elem.get_text(strip=True, separator=' ')
                # Удаляем неразрывные пробелы и заменяем запятую на точку
                text = text.replace('\xa0', ' ').replace(',', '.')
                # Удаляем все лишние пробелы
                text = ' '.join(text.split())
                # Извлекаем только числовые значения (могут быть в формате "80.90" или "80.90 %")
                # Ищем первое число с возможной десятичной частью
                match = re.search(r'\d+\.?\d*', text)
                if match:
                    return match.group(0)
                return text if text else None
            
            def get_name_text(elem):
                """Извлекает полный текст для названия банка (не только числа)"""
                if not elem:
                    return None
                # Получаем весь текст без извлечения чисел
                text = elem.get_text(strip=True, separator=' ')
                # Удаляем неразрывные пробелы
                text = text.replace('\xa0', ' ')
                # Удаляем все лишние пробелы
                text = ' '.join(text.split())
                # Если текст содержит только цифры и точки/запятые - это скорее всего не название банка
                cleaned_for_check = text.replace('.', '').replace(',', '').replace(' ', '').replace('-', '').replace('+', '')
                if cleaned_for_check.isdigit() and len(cleaned_for_check) < 5:
                    # Это похоже на номер или короткий идентификатор, пропускаем
                    return None
                return text if text else None

            name = get_name_text(name_elem)
            buy = get_text(buy_elem)
            sell = get_text(sell_elem)

            # Отладка для первых строк
            if idx < 3:
                print(f"\nСтрока {idx}: Name={name}, Buy={buy}, Sell={sell}")

            # Пропускаем строки-заголовки и записи без названия
            if name in ['Банк', 'Продажа', 'Покупка', None] or not name or len(name.strip()) < 3:
                continue
            
            # Пропускаем записи, где название - это только числа (скорее всего телефон или ID)
            if name.strip().replace('.', '').replace(',', '').replace(' ', '').replace('-', '').isdigit():
                continue
            
            # Проверяем, что курс покупки - это число
            def is_number(s):
                if not s:
                    return False
                try:
                    # Удаляем точку и пробелы для проверки
                    cleaned = s.replace('.', '').replace('-', '').replace(' ', '').strip()
                    # Проверяем что это число
                    float(s)
                    return len(cleaned) > 0
                except (ValueError, AttributeError):
                    return False
            
            if is_number(buy) or is_number(sell):
                try:
                    buy_float = float(buy) if buy and is_number(buy) else None
                    sell_float = float(sell) if sell and is_number(sell) else None
                    
                    # Проверяем что хотя бы один курс есть
                    if buy_float is not None or sell_float is not None:
                        results.append({
                            'bank': name or 'Не указано',
                            'buy': buy_float,
                            'sell': sell_float
                        })
                except (ValueError, TypeError) as e:
                    if idx < 5:  # Показываем ошибки только для первых строк
                        print(f"Ошибка преобразования: buy={buy}, sell={sell}, error={e}")
                    continue

        # Удаляем дубликаты
        unique_results = []
        seen = set()
        for r in results:
            key = (r['bank'], r['buy'], r['sell'])
            if key not in seen:
                seen.add(key)
                unique_results.append(r)

        # Сортируем по курсу покупки
        unique_results.sort(key=lambda x: (x['buy'] if x['buy'] is not None else 1e9, x['bank']))

        print(f"\n{'=' * 60}")
        print(f"Найдено уникальных записей: {len(unique_results)}")
        print(f"{'=' * 60}")

        # Выводим первые 20 результатов
        for i, r in enumerate(unique_results[:20], 1):
            print(f"{i}. {r}")

        # Сохраняем в JSON
        with open('rates.json', 'w', encoding='utf-8') as f:
            json.dump(unique_results, f, ensure_ascii=False, indent=2)

        print(f"\nРезультаты сохранены в rates.json")

        return unique_results

    except Exception as e:
        print(f"Ошибка при парсинге таблицы: {e}")
        traceback.print_exc()
        return []


def main():
    """Основная функция"""
    driver = None
    temp_dir = None

    try:
        print("Запуск парсера курсов валют РБК...")

        # Настройка драйвера
        driver = setup_driver()
        temp_dir = getattr(driver, 'temp_dir', None)

        # Построение URL
        url = build_url()
        print(f"Открываем страницу: {url}")

        # Открываем страницу
        driver.get(url)
        print("Страница загружена")

        # Ждем загрузки динамического контента
        wait_for_page_ready(driver)

        # Кликаем на профессиональную версию
        if click_professional_version(driver):
            print("Профессиональная версия активирована (или уже активна)")
        else:
            print("Работаем со стандартной версией")

        # Парсим таблицу
        results = parse_rates_table(driver)

        if results:
            print(f"\n✓ Успешно получено {len(results)} записей")
        else:
            print("\n✗ Не удалось получить данные. Проверьте page_content_debug.html для анализа")

        # Пауза для просмотра результата
        print("\nБраузер останется открытым 5 секунд для просмотра...")
        time.sleep(5)

    except Exception as e:
        print(f"Произошла ошибка: {e}")
        traceback.print_exc()

    finally:
        if driver:
            try:
                driver.quit()
                print("Браузер закрыт")
            except Exception as e:
                print(f"Ошибка при закрытии браузера: {e}")

        # Очищаем временную директорию с увеличенной задержкой для Windows
        if temp_dir and os.path.exists(temp_dir):
            try:
                time.sleep(2)  # Увеличена задержка для Windows
                # Попытка удалить несколько раз при неудаче (для Windows)
                for attempt in range(3):
                    try:
                        shutil.rmtree(temp_dir, ignore_errors=False)
                        print(f"Временная директория очищена: {temp_dir}")
                        break
                    except Exception as cleanup_error:
                        if attempt < 2:
                            time.sleep(1)
                        else:
                            print(f"Не удалось очистить временную директорию после 3 попыток: {cleanup_error}")
            except Exception as e:
                print(f"Ошибка при очистке временной директории: {e}")

if __name__ == "__main__":
    main()