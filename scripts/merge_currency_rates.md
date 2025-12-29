# merge_currency_rates.py

Сливает результаты парсеров курсов в одно множество (банк+валюта), убирает дубли и сохраняет:
- `merged_rates_<ts>.json` (с офферами по источникам)
- `merged_rates_<ts>_summary.csv` (краткая сводка)

Примеры:
- `python scripts/merge_currency_rates.py --inputs "rbc_all_banks_*.json" "banki_rates_*.json"`
- `python scripts/merge_currency_rates.py --inputs "rbc_all_banks_*.json" --out merged_rbc.json --csv merged_rbc.csv`

