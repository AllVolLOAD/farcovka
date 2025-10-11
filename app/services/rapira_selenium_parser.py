import time
import json
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from datetime import datetime


def enhanced_rapira_parser():
    """Улучшенный парсер для правильного извлечения данных RAPIRA"""
    print("🎯 УЛУЧШЕННЫЙ ПАРСЕР RAPIRA")

    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--headless")  # Добавляем headless для сервера

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get("http://212.8.226.71:8080/")
        print("⏳ Ожидаем загрузки страницы...")
        time.sleep(5)

        # Выполняем полную последовательность действий
        print("🔄 Выполняем последовательность действий...")

        # 1. Тестовый сбор
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            if "Тестовый сбор" in btn.text:
                driver.execute_script("arguments[0].click();", btn)
                print("✅ Тестовый сбор запущен")
                time.sleep(3)
                break

        # 2. Запустить (если есть)
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            if "Запустить" in btn.text and btn.is_displayed():
                driver.execute_script("arguments[0].click();", btn)
                print("✅ Процесс запущен")
                time.sleep(3)
                break

        # 3. Переключаемся на вкладку Биржи
        exchanges_tab = driver.find_element(By.XPATH, "//button[contains(., 'Биржи')]")
        driver.execute_script("arguments[0].click();", exchanges_tab)
        print("✅ Переключились на вкладку 'Биржи'")
        time.sleep(3)

        # 4. Обновляем данные
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            if "Обновить" in btn.text and btn.is_displayed():
                driver.execute_script("arguments[0].click();", btn)
                print("✅ Данные обновлены")
                time.sleep(10)
                break

        # Ждем появления данных RAPIRA
        print("⏳ Ожидаем данные RAPIRA...")
        start_time = time.time()

        while time.time() - start_time < 60:  # Ждем до 1 минуты
            cards = driver.find_elements(By.CSS_SELECTOR, '[data-slot="card"]')

            for card in cards:
                text = card.text
                if "RAPIRA" in text and "USDT/RUB" in text:
                    print("🎯 Найдена карточка RAPIRA!")

                    # Парсим данные с улучшенной функцией
                    data = parse_rapira_complete(text)

                    if data:
                        print("✅ Данные успешно получены")
                        return data

            time.sleep(5)
            print(f"⏰ Проверка... ({int(time.time() - start_time)} сек)")

        print("❌ Данные не найдены")
        return None

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None
    finally:
        driver.quit()


def parse_rapira_complete(card_text):
    """Полный парсинг данных RAPIRA с учетом реального формата"""
    print("🔧 Начинаем полный парсинг данных...")

    data = {
        'exchange': 'RAPIRA',
        'symbol': 'USDT/RUB',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'source': 'selenium_parser'
    }

    # Разбиваем текст на строки и ищем блок RAPIRA
    lines = card_text.split('\n')
    rapira_start = -1

    # Находим начало блока RAPIRA
    for i, line in enumerate(lines):
        if line.strip() == 'RAPIRA':
            rapira_start = i
            break

    if rapira_start == -1:
        print("❌ Не найден блок RAPIRA")
        return None

    print(f"📌 Найден блок RAPIRA на строке {rapira_start}")

    # Извлекаем данные из блока RAPIRA
    i = rapira_start
    while i < len(lines):
        line = lines[i].strip()

        if line == 'USDT/RUB':
            # Следующие строки содержат данные
            i += 1
            while i < len(lines) and lines[i].strip() and not any(
                    x in lines[i] for x in ['RAPIRA', 'MOEX', 'ICE', 'KASE']):
                current_line = lines[i].strip()
                print(f"📄 Обрабатываем строку: {current_line}")

                # Обрабатываем разные форматы данных
                if 'Bid:' in current_line and 'Ask:' not in current_line:
                    # Простой Bid
                    match = re.search(r'Bid:\s*([\d.]+)', current_line)
                    if match:
                        data['Bid'] = float(match.group(1))
                        print(f"✅ Bid: {data['Bid']}")

                elif 'Ask:' in current_line and 'Bid:' not in current_line:
                    # Простой Ask
                    match = re.search(r'Ask:\s*([\d.]+)', current_line)
                    if match:
                        data['Ask'] = float(match.group(1))
                        print(f"✅ Ask: {data['Ask']}")

                elif 'Bid:' in current_line and 'Ask:' in current_line:
                    # Bid и Ask в одной строке
                    bid_match = re.search(r'Bid:\s*([\d.]+)', current_line)
                    ask_match = re.search(r'Ask:\s*([\d.]+)', current_line)
                    if bid_match:
                        data['Bid'] = float(bid_match.group(1))
                        print(f"✅ Bid: {data['Bid']}")
                    if ask_match:
                        data['Ask'] = float(ask_match.group(1))
                        print(f"✅ Ask: {data['Ask']}")

                # Обрабатываем VWAP значения
                elif 'VWAP' in current_line:
                    # VWAP 50k Bid/Ask
                    if '50k Bid' in current_line:
                        match = re.search(r'VWAP 50k Bid:\s*([\d.]+)', current_line)
                        if match:
                            data['VWAP_50k_Bid'] = float(match.group(1))
                            print(f"✅ VWAP 50k Bid: {data['VWAP_50k_Bid']}")

                    elif '50k Ask' in current_line:
                        match = re.search(r'VWAP 50k Ask:\s*([\d.]+)', current_line)
                        if match:
                            data['VWAP_50k_Ask'] = float(match.group(1))
                            print(f"✅ VWAP 50k Ask: {data['VWAP_50k_Ask']}")

                    # VWAP 250k Bid/Ask
                    elif '250k Bid' in current_line:
                        match = re.search(r'VWAP 250k Bid:\s*([\d.]+)', current_line)
                        if match:
                            data['VWAP_250k_Bid'] = float(match.group(1))
                            print(f"✅ VWAP 250k Bid: {data['VWAP_250k_Bid']}")

                    elif '250k Ask' in current_line:
                        match = re.search(r'VWAP 250k Ask:\s*([\d.]+)', current_line)
                        if match:
                            data['VWAP_250k_Ask'] = float(match.group(1))
                            print(f"✅ VWAP 250k Ask: {data['VWAP_250k_Ask']}")

                i += 1
            break
        i += 1

    # Рассчитываем спред
    if 'Bid' in data and 'Ask' in data:
        data['Spread'] = data['Ask'] - data['Bid']
        data['Spread_Percent'] = (data['Spread'] / data['Bid']) * 100
        print(f"✅ Спред: {data['Spread']:.4f} ({data['Spread_Percent']:.4f}%)")

    print(f"📊 Всего извлечено полей: {len(data) - 4}")

    return data