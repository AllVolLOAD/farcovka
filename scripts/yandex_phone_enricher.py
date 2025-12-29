"""
Enrich Yandex.Maps results with phone numbers and mark entries missing in ads.

Usage:
  python scripts/yandex_phone_enricher.py --yandex yandex_maps_results_filtered.json \
    --ads rbc_all_banks_*.json banki_rates_*.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import aiohttp


_RE_MULTI_SPACE = re.compile(r"\s+")
_RE_PARENS = re.compile(r"\([^)]*\)")
_RE_OFFICE_TAIL = re.compile(r"\s+\b(до|оо)\b.*$", flags=re.IGNORECASE)
_RE_NON_WORDS = re.compile(r"[^0-9a-zа-я]+", flags=re.IGNORECASE)
_RE_PHONE = re.compile(r"(?:(?:\+7)|(?:8))\s*\(?\d{3}\)?\s*\d{3}\s*-?\s*\d{2}\s*-?\s*\d{2}")


_LEGAL_TOKENS = {
    "ао",
    "пао",
    "оао",
    "зао",
    "ооо",
    "акб",
    "кб",
    "нкб",
    "мкб",
    "банк",
}


def _compact(text: str) -> str:
    return _RE_MULTI_SPACE.sub(" ", text).strip()


def _extract_base_bank_name(raw: str) -> str:
    s = _compact(raw)
    s = _RE_OFFICE_TAIL.sub("", s)
    return _compact(s)


def _norm_name(name: str) -> str:
    s = name.lower().replace("ё", "е")
    s = s.replace("«", '"').replace("»", '"')
    s = _RE_PARENS.sub(" ", s)
    s = _RE_NON_WORDS.sub(" ", s)
    parts = [p for p in _compact(s).split(" ") if p and p not in _LEGAL_TOKENS]
    return " ".join(parts)


def _load_json_list(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
        return [d for d in data["data"] if isinstance(d, dict)]
    return []


def _expand_inputs(patterns: Iterable[str]) -> List[Path]:
    out: List[Path] = []
    for p in patterns:
        matches = sorted(Path().glob(p))
        if matches:
            out.extend(matches)
        else:
            direct = Path(p)
            if direct.exists():
                out.append(direct)
    seen: Set[Path] = set()
    uniq: List[Path] = []
    for p in out:
        rp = p.resolve()
        if rp not in seen:
            seen.add(rp)
            uniq.append(p)
    return uniq


def _normalize_phone(raw: str) -> Optional[str]:
    digits = re.sub(r"\D+", "", raw)
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    if len(digits) == 11 and digits.startswith("7"):
        return "+{}".format(digits)
    return None


def _extract_phones(html: str) -> List[str]:
    phones: List[str] = []
    for m in _RE_PHONE.finditer(html):
        norm = _normalize_phone(m.group(0))
        if norm:
            phones.append(norm)
    # de-dupe preserving order
    seen = set()
    uniq = []
    for p in phones:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq


@dataclass
class _FetchStats:
    ok: int = 0
    failed: int = 0
    skipped: int = 0


async def _fetch_phone(session: aiohttp.ClientSession, url: str, delay: Tuple[float, float]) -> List[str]:
    await asyncio.sleep(random.uniform(*delay))
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
        if resp.status != 200:
            return []
        html = await resp.text()
        return _extract_phones(html)


def _build_ads_set(files: List[Path]) -> Set[str]:
    out: Set[str] = set()
    for p in files:
        for item in _load_json_list(p):
            name = (item.get("bank") or "").strip()
            if not name:
                continue
            base = _extract_base_bank_name(name)
            norm = _norm_name(base)
            if norm:
                out.add(norm)
    return out


def _match_ads(name_norm: str, ads_set: Set[str]) -> Tuple[bool, str]:
    if name_norm in ads_set:
        return True, "exact"
    # мягкая проверка включения, чтобы не пропускать очевидные совпадения
    for a in ads_set:
        if len(a) >= 4 and (a in name_norm or name_norm in a):
            return True, "contains"
    return False, ""


async def enrich(
    yandex_file: Path,
    ads_files: List[Path],
    *,
    limit: Optional[int],
    concurrency: int,
    delay: Tuple[float, float],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], _FetchStats]:
    data = _load_json_list(yandex_file)
    ads_set = _build_ads_set(ads_files)

    stats = _FetchStats()
    sem = asyncio.Semaphore(concurrency)

    async with aiohttp.ClientSession(
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ru-RU,ru;q=0.9",
        }
    ) as session:
        async def handle(item: Dict[str, Any]) -> Dict[str, Any]:
            url = (item.get("url") or "").strip()
            name = (item.get("name") or "").strip()
            name_norm = _norm_name(name)
            in_ads, matched_by = _match_ads(name_norm, ads_set)

            out = dict(item)
            out["name_norm"] = name_norm
            out["in_ads"] = in_ads
            out["matched_by"] = matched_by

            if not url:
                stats.skipped += 1
                out["phones"] = []
                return out

            async with sem:
                try:
                    phones = await _fetch_phone(session, url, delay)
                    if phones:
                        stats.ok += 1
                    else:
                        stats.failed += 1
                    out["phones"] = phones
                except Exception:
                    stats.failed += 1
                    out["phones"] = []
            return out

        tasks = []
        for i, item in enumerate(data):
            if limit is not None and i >= limit:
                break
            tasks.append(handle(item))

        enriched = await asyncio.gather(*tasks)

    missing_ads = [r for r in enriched if not r.get("in_ads")]
    return enriched, missing_ads, stats


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch phones for Yandex.Maps exchange points.")
    ap.add_argument("--yandex", required=True, help="Yandex maps JSON file")
    ap.add_argument("--ads", nargs="*", default=[], help="RBC/Banki JSON files or globs")
    ap.add_argument("--limit", type=int, default=None, help="Optional limit for testing")
    ap.add_argument("--concurrency", type=int, default=5, help="Parallel HTTP requests")
    ap.add_argument("--delay-min", type=float, default=0.2, help="Min delay between requests (sec)")
    ap.add_argument("--delay-max", type=float, default=0.6, help="Max delay between requests (sec)")
    ap.add_argument("--out", default="", help="Output JSON (enriched)")
    ap.add_argument("--missing-out", default="", help="Output JSON for missing-in-ads only")
    args = ap.parse_args()

    yandex_path = Path(args.yandex)
    if not yandex_path.exists():
        raise SystemExit(f"Yandex file not found: {yandex_path}")

    ads_files = _expand_inputs(args.ads)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = Path(args.out) if args.out else Path(f"yandex_with_phones_{ts}.json")
    missing_path = Path(args.missing_out) if args.missing_out else Path(f"yandex_missing_ads_{ts}.json")

    enriched, missing_ads, stats = asyncio.run(
        enrich(
            yandex_path,
            ads_files,
            limit=args.limit,
            concurrency=args.concurrency,
            delay=(args.delay_min, args.delay_max),
        )
    )

    out_path.write_text(json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8")
    missing_path.write_text(json.dumps(missing_ads, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ Enriched: {len(enriched)}")
    print(f"✅ Missing in ads: {len(missing_ads)}")
    print(f"✅ Phones ok: {stats.ok}, failed: {stats.failed}, skipped(no url): {stats.skipped}")
    print(f"✅ Output: {out_path}")
    print(f"✅ Missing: {missing_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

