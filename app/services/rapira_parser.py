import re
from datetime import datetime

def parse_rapira_complete(card_text):
    """Исправленный парсинг данных RAPIRA"""
    import re

    print("🔧 Начинаем полный парсинг данных...")

    data = {
        'exchange': 'RAPIRA',
        'symbol': 'USDT/RUB',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # ← Теперь правильно
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
                if 'Bid:' in current_line and 'Ask:' not in current_line and 'VWAP' not in current_line:
                    # Основной Bid (не VWAP)
                    match = re.search(r'Bid:\s*([\d.]+)', current_line)
                    if match and 'Bid' not in data:
                        data['Bid'] = float(match.group(1))
                        print(f"✅ Основной Bid: {data['Bid']}")

                elif 'Ask:' in current_line and 'Bid:' not in current_line and 'VWAP' not in current_line:
                    # Основной Ask (не VWAP)
                    match = re.search(r'Ask:\s*([\d.]+)', current_line)
                    if match and 'Ask' not in data:
                        data['Ask'] = float(match.group(1))
                        print(f"✅ Основной Ask: {data['Ask']}")

                elif 'Bid:' in current_line and 'Ask:' in current_line and 'VWAP' not in current_line:
                    # Bid и Ask в одной строке (основные)
                    bid_match = re.search(r'Bid:\s*([\d.]+)', current_line)
                    ask_match = re.search(r'Ask:\s*([\d.]+)', current_line)
                    if bid_match and 'Bid' not in data:
                        data['Bid'] = float(bid_match.group(1))
                        print(f"✅ Основной Bid: {data['Bid']}")
                    if ask_match and 'Ask' not in data:
                        data['Ask'] = float(ask_match.group(1))
                        print(f"✅ Основной Ask: {data['Ask']}")

                # Обрабатываем VWAP значения
                elif 'VWAP' in current_line:
                    # VWAP 50k Bid
                    if '50k Bid' in current_line:
                        match = re.search(r'VWAP 50k Bid:\s*([\d.]+)', current_line)
                        if match:
                            data['VWAP_50k_Bid'] = float(match.group(1))
                            print(f"✅ VWAP 50k Bid: {data['VWAP_50k_Bid']}")

                    # VWAP 50k Ask
                    elif '50k Ask' in current_line:
                        match = re.search(r'VWAP 50k Ask:\s*([\d.]+)', current_line)
                        if match:
                            data['VWAP_50k_Ask'] = float(match.group(1))
                            print(f"✅ VWAP 50k Ask: {data['VWAP_50k_Ask']}")

                    # VWAP 250k Bid
                    elif '250k Bid' in current_line:
                        match = re.search(r'VWAP 250k Bid:\s*([\d.]+)', current_line)
                        if match:
                            data['VWAP_250k_Bid'] = float(match.group(1))
                            print(f"✅ VWAP 250k Bid: {data['VWAP_250k_Bid']}")

                    # VWAP 250k Ask
                    elif '250k Ask' in current_line:
                        match = re.search(r'VWAP 250k Ask:\s*([\d.]+)', current_line)
                        if match:
                            data['VWAP_250k_Ask'] = float(match.group(1))
                            print(f"✅ VWAP 250k Ask: {data['VWAP_250k_Ask']}")

                # Дата и время
                elif re.match(r'\d{2}\.\d{2}\.\d{4}', current_line):
                    data['data_timestamp'] = current_line
                    print(f"✅ Время данных: {current_line}")

                i += 1
            break
        i += 1

    # Рассчитываем спред на основе основных Bid/Ask
    if 'Bid' in data and 'Ask' in data:
        data['Spread'] = round(data['Ask'] - data['Bid'], 4)
        data['Spread_Percent'] = round((data['Spread'] / data['Bid']) * 100, 4)
        print(f"✅ Спред: {data['Spread']:.4f} ({data['Spread_Percent']:.4f}%)")

    # Считаем только пользовательские поля (исключая служебные)
    user_fields = [k for k in data.keys() if k not in ['exchange', 'symbol', 'timestamp', 'source']]
    print(f"📊 Всего извлечено полей: {len(user_fields)}")

    return data