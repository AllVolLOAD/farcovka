"""
Парсер для получения ВСЕХ банков с РБК через Selenium
Переходит по страницам 1, 2, 3, 4, 5... пока есть данные
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import logging
import time
import re

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_all_rbc_banks() -> List[Dict]:
    """Получает ВСЕ банки с РБК, переходя по страницам через Selenium"""
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        # Браузер ВИДИМЫЙ - обязательно!
        options = webdriver.ChromeOptions()
        # НЕ используем headless - браузер должен быть видимым
        # options.add_argument('--headless')  # ЗАКОММЕНТИРОВАНО - браузер должен быть видимым!
        options.add_argument('--start-maximized')  # Полный экран
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        print("🔧 Создаем драйвер Chrome (БРАУЗЕР БУДЕТ ВИДИМЫМ)...")
        print("   ⚠️ ВАЖНО: Браузер откроется и вы увидите весь процесс!")
        print("   ⚠️ Вы должны видеть окно Chrome с прокруткой страниц!")
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(60)
        print("✅ Драйвер создан, браузер открыт - ВЫ ДОЛЖНЫ ВИДЕТЬ ОКНО CHROME!")
        
        all_results = []
        page_num = 1
        max_pages = 100
        
        def extract_num(text: str):
            if not text:
                return None
            t = text.replace('\xa0', ' ').replace(',', '.').strip()
            m = re.search(r"\d+[.]?\d*", t)
            return float(m.group(0)) if m else None
        
        def get_row_data(row_elem):
            """Извлекает данные из строки - собираем ВСЕ"""
            try:
                name_el = row_elem.find_element(By.CSS_SELECTOR, '.quote__office__one__name')
                name = name_el.text.strip() if name_el else ''
                
                if not name:
                    return None
                
                buy_el = row_elem.find_element(By.CSS_SELECTOR, '.quote__office__one__buy')
                sell_el = row_elem.find_element(By.CSS_SELECTOR, '.quote__office__one__sell')
                
                buy = extract_num(buy_el.text) if buy_el else None
                sell = extract_num(sell_el.text) if sell_el else None
                
                # Собираем даже если только один курс есть
                if buy is None and sell is None:
                    return None
                
                address = ''
                try:
                    address_el = row_elem.find_element(By.CSS_SELECTOR, '.quote__office__one__address')
                    address = address_el.text.strip() if address_el else ''
                except:
                    pass
                
                return {
                    'source': 'RBC',
                    'bank': name,
                    'currency': 'USD',
                    'buy': buy,
                    'sell': sell,
                    'address': address
                }
            except Exception as e:
                return None
        
        try:
            while page_num <= max_pages:
                url = f"https://cash.rbc.ru/cash/?currency=3&city=1&diapason=3&page={page_num}"
                
                print(f"\n{'='*70}")
                print(f"📄 СТРАНИЦА {page_num}: {url}")
                print(f"{'='*70}")
                
                try:
                    driver.get(url)
                    time.sleep(2)
                    
                    WebDriverWait(driver, 30).until(
                        lambda d: d.execute_script('return document.readyState') == 'complete'
                    )
                    time.sleep(3)
                    
                    # Переключаем на профессиональную версию только на первой странице
                    if page_num == 1:
                        try:
                            toggle = driver.find_element(By.CSS_SELECTOR, '.js-toggle-versions-text')
                            if toggle and 'Профессиональная' in toggle.text:
                                driver.execute_script("arguments[0].click();", toggle)
                                time.sleep(3)
                                print("   ✅ Переключились на профессиональную версию")
                        except:
                            pass
                    
                    # Ждем появления элементов
                    try:
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, '.quote__office__one.js-one-office'))
                        )
                    except:
                        pass
                    
                    # ПРОКРУЧИВАЕМ страницу до конца, чтобы загрузить все элементы
                    print(f"   📜 ПРОКРУЧИВАЕМ страницу {page_num} до конца (вы увидите это в браузере)...")
                    last_height = driver.execute_script("return document.body.scrollHeight")
                    scroll_attempts = 0
                    max_scroll_attempts = 15  # Увеличиваем количество попыток
                    
                    while scroll_attempts < max_scroll_attempts:
                        # Прокручиваем вниз плавно
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(1.5)  # Ждем загрузки новых элементов
                        
                        # Проверяем новую высоту
                        new_height = driver.execute_script("return document.body.scrollHeight")
                        if new_height == last_height:
                            # Высота не изменилась, значит прокрутили до конца
                            print(f"      ✅ Прокрутка завершена (высота не изменилась)")
                            break
                        last_height = new_height
                        scroll_attempts += 1
                        print(f"      📜 Прокрутка {scroll_attempts}/{max_scroll_attempts}, высота: {new_height}px")
                    
                    # Прокручиваем обратно вверх для удобства
                    print(f"   ⬆️ Прокручиваем обратно вверх...")
                    driver.execute_script("window.scrollTo(0, 0);")
                    time.sleep(1)
                    print(f"   ✅ Страница {page_num} полностью прокручена и готова к парсингу")
                    
                    # Собираем строки ПОСЛЕ прокрутки
                    rows = driver.find_elements(By.CSS_SELECTOR, '.quote__office__one.js-one-office')
                    if len(rows) == 0:
                        rows = driver.find_elements(By.CSS_SELECTOR, '.quote__office__one')
                    
                    print(f"   📋 Найдено строк: {len(rows)}")
                    
                    if len(rows) == 0:
                        print(f"   ⚠️ Строк не найдено, останавливаемся")
                        break
                    
                    # Парсим ВСЕ строки
                    page_count = 0
                    for i in range(len(rows)):
                        data = get_row_data(rows[i])
                        if data:
                            all_results.append(data)
                            page_count += 1
                    
                    print(f"   ✅ Собрано валидных: {page_count}")
                    print(f"   📦 ВСЕГО собрано за все страницы: {len(all_results)}")
                    
                    if page_count == 0:
                        print(f"   ⚠️ Валидных данных нет, останавливаемся")
                        break
                    
                    # ПРОСТАЯ ЛОГИКА: просто переходим на следующую страницу по порядку (1, 2, 3, 4...)
                    # Если на странице нет данных или мало данных - останавливаемся
                    next_page = page_num + 1
                    
                    # Если собрали мало данных (меньше 10), вероятно это последняя страница
                    if page_count < 10:
                        print(f"   ⚠️ Собрано мало данных ({page_count}), вероятно последняя страница")
                        print(f"   ✅ Останавливаемся на странице {page_num}")
                        break
                    
                    # Переходим на следующую страницу по порядку
                    print(f"   ➡️ Переходим на страницу {next_page} (последовательный переход)...")
                    page_num = next_page
                    time.sleep(2)  # Пауза перед переходом
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка на странице {page_num}: {e}")
                    print(f"   ❌ Ошибка: {e}")
                    break
            
            # Убираем дубликаты только в конце
            unique_results = []
            seen = set()
            for r in all_results:
                key = (r.get('bank', '').strip(), r.get('buy'), r.get('sell'))
                if key not in seen:
                    seen.add(key)
                    unique_results.append(r)
            
            print(f"\n{'='*70}")
            print(f"📊 ИТОГО: собрано {len(all_results)}, уникальных {len(unique_results)}")
            print(f"{'='*70}\n")
            
            return unique_results
            
        finally:
            try:
                driver.quit()
            except:
                pass
                
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
        return []


if __name__ == '__main__':
    print("="*70)
    print("ПОЛУЧЕНИЕ ВСЕХ БАНКОВ С РБК (ПО СТРАНИЦАМ)")
    print("="*70)
    
    results = get_all_rbc_banks()
    
    if results:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_file = f'rbc_all_banks_{timestamp}.json'
        csv_file = f'rbc_all_banks_{timestamp}.csv'
        
        # Сохраняем JSON
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"✅ JSON сохранён: {json_file}")
        
        # Сохраняем CSV
        import csv
        if results:
            with open(csv_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=results[0].keys())
                writer.writeheader()
                writer.writerows(results)
            print(f"✅ CSV сохранён: {csv_file}")
        
        print("\n" + "="*70)
        print("СТАТИСТИКА")
        print("="*70)
        print(f"Всего банков: {len(results)}")
        print(f"Уникальных названий банков: {len(set(r['bank'] for r in results))}")
        print(f"Банков с обоими курсами: {len([r for r in results if r.get('buy') and r.get('sell')])}")
        
        print("\nПервые 10 банков:")
        for i, bank in enumerate(results[:10], 1):
            print(f"  {i}. {bank['bank']}: buy={bank.get('buy')}, sell={bank.get('sell')}")
    else:
        print("❌ Не удалось получить данные")
