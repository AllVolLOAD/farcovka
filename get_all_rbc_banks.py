"""
Парсер РБК cash.rbc.ru: собирает все строки с банков/офисов по страницам.
Подходит для редкого запуска на сервере (headless по умолчанию).
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def _extract_num(text: str) -> Optional[float]:
    if not text:
        return None
    t = text.replace("\xa0", " ").replace(",", ".").strip()
    m = re.search(r"\d+(?:\.\d+)?", t)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


@dataclass(frozen=True)
class _RowKey:
    bank: str
    buy: Optional[float]
    sell: Optional[float]
    address: str


async def _parse_rbc_page(page: Any, url: str, *, toggle_pro: bool) -> List[Dict[str, Any]]:
    await page.goto(url, wait_until="load", timeout=60000)
    await page.wait_for_timeout(1200)

    if toggle_pro:
        try:
            toggle = page.locator(".js-toggle-versions-text")
            if await toggle.count() > 0:
                text = (await toggle.first.inner_text()).strip()
                if "Профессиональная" in text:
                    await toggle.first.click(timeout=5000)
                    await page.wait_for_timeout(1200)
        except Exception:
            pass

    try:
        await page.wait_for_selector(".quote__office__one", timeout=15000)
    except Exception:
        return []

    # Доскролливаем страницу (иногда подгружаются элементы)
    last_height = 0
    for _ in range(12):
        height = await page.evaluate("() => document.body.scrollHeight")
        if height == last_height:
            break
        last_height = height
        await page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(600)

    rows = await page.evaluate(
        """
        () => {
          const sels = ['.quote__office__one.js-one-office', '.quote__office__one'];
          const nodes = sels.flatMap(sel => Array.from(document.querySelectorAll(sel)));
          const uniq = [];
          const seen = new Set();
          for (const n of nodes) {
            const key = n.getAttribute('data-id') || n.innerText?.slice(0, 64) || Math.random().toString();
            if (!seen.has(key)) { seen.add(key); uniq.push(n); }
          }
          const getText = (root, sel) => {
            const el = root.querySelector(sel);
            return (el ? el.textContent : '').trim();
          };
          return uniq.map(r => ({
            bank: getText(r, '.quote__office__one__name'),
            buy_text: getText(r, '.quote__office__one__buy'),
            sell_text: getText(r, '.quote__office__one__sell'),
            address: getText(r, '.quote__office__one__address')
          }));
        }
        """
    )

    results: List[Dict[str, Any]] = []
    for r in rows:
        bank = (r.get("bank") or "").strip()
        if not bank:
            continue
        buy = _extract_num(r.get("buy_text") or "")
        sell = _extract_num(r.get("sell_text") or "")
        if buy is None and sell is None:
            continue
        results.append(
            {
                "source": "RBC",
                "bank": bank,
                "currency": "USD",
                "buy": buy,
                "sell": sell,
                "address": (r.get("address") or "").strip(),
            }
        )
    return results


async def get_all_rbc_banks(*, headless: bool = True, max_pages: int = 100) -> List[Dict[str, Any]]:
    try:
        from playwright.async_api import async_playwright
    except ImportError as e:
        logger.error("Playwright не установлен: pip install playwright && playwright install chromium")
        raise

    all_rows: List[Dict[str, Any]] = []
    seen: set[_RowKey] = set()
    no_new_pages = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="ru-RU",
            timezone_id="Europe/Moscow",
        )
        page = await context.new_page()

        try:
            for page_num in range(1, max_pages + 1):
                url = f"https://cash.rbc.ru/cash/?currency=3&city=1&diapason=3&page={page_num}"
                logger.info("RBC page %s: %s", page_num, url)

                page_rows = await _parse_rbc_page(page, url, toggle_pro=(page_num == 1))
                if not page_rows:
                    break

                new_count = 0
                for r in page_rows:
                    key = _RowKey(
                        bank=(r.get("bank") or "").strip(),
                        buy=r.get("buy"),
                        sell=r.get("sell"),
                        address=(r.get("address") or "").strip(),
                    )
                    if key not in seen:
                        seen.add(key)
                        all_rows.append(r)
                        new_count += 1

                logger.info("RBC page %s: rows=%s new=%s total_unique=%s", page_num, len(page_rows), new_count, len(all_rows))
                if new_count == 0:
                    no_new_pages += 1
                    if no_new_pages >= 2:
                        break
                else:
                    no_new_pages = 0

        finally:
            await context.close()
            await browser.close()

    return all_rows


def _save_json_csv(rows: List[Dict[str, Any]], *, prefix: str) -> Tuple[Path, Path]:
    json_path = Path(f"{prefix}.json")
    csv_path = Path(f"{prefix}.csv")

    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    if rows:
        fieldnames = ["source", "bank", "currency", "buy", "sell", "address"]
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k) for k in fieldnames})
    return json_path, csv_path


async def _amain() -> int:
    ap = argparse.ArgumentParser(description="RBC cash.rbc.ru parser (all pages).")
    ap.add_argument("--headed", action="store_true", help="Run with visible browser window.")
    ap.add_argument("--max-pages", type=int, default=100, help="Safety limit.")
    args = ap.parse_args()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = f"rbc_all_banks_{ts}"

    rows = await get_all_rbc_banks(headless=not args.headed, max_pages=args.max_pages)
    if not rows:
        logger.error("Не удалось получить данные РБК")
        return 2

    json_path, csv_path = _save_json_csv(rows, prefix=prefix)
    logger.info("Saved: %s", json_path)
    logger.info("Saved: %s", csv_path)
    logger.info("Total rows: %s", len(rows))
    return 0


if __name__ == "__main__":
    import asyncio

    raise SystemExit(asyncio.run(_amain()))
