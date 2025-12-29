"""
Merge and dedupe currency-rate parser outputs (RBC / Banki / etc.).

Inputs are JSON files containing a list of dicts with (at least) these fields:
  - bank: str
  - currency: str (e.g. "USD")
  - buy: float | null
  - sell: float | null
  - address: str (optional)
  - source: str (optional; inferred from filename when missing)

Output is a bank-level union (one record per bank+currency) with aggregated offers.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


_RE_MULTI_SPACE = re.compile(r"\s+")
_RE_PARENS = re.compile(r"\([^)]*\)")
_RE_OFFICE_TAIL = re.compile(r"\s+\b(до|оо)\b.*$", flags=re.IGNORECASE)
_RE_NON_WORDS = re.compile(r"[^0-9a-zа-я]+", flags=re.IGNORECASE)


def _compact_spaces(text: str) -> str:
    return _RE_MULTI_SPACE.sub(" ", text).strip()


def _extract_base_bank_name(raw: str) -> str:
    """
    RBC sometimes returns office-level names like:
      'АО КБ "ЮНИСТРИМ" ОО № 263' or '... ДО "Внуково"'
    We strip the office tail to merge at bank level.
    """
    s = _compact_spaces(raw)
    s = _RE_OFFICE_TAIL.sub("", s)
    return _compact_spaces(s)


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
    "кбк",
}


def _bank_key(bank_base: str) -> str:
    s = bank_base.lower().replace("ё", "е")
    s = s.replace("«", '"').replace("»", '"')
    s = _RE_PARENS.sub(" ", s)
    s = _RE_NON_WORDS.sub(" ", s)
    parts = [p for p in _compact_spaces(s).split(" ") if p and p not in _LEGAL_TOKENS]
    return " ".join(parts)


def _infer_source(file_path: Path) -> str:
    name = file_path.name.lower()
    if "rbc" in name:
        return "RBC"
    if "banki" in name:
        return "Banki"
    return "unknown"


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        v = value.replace("\xa0", " ").replace(",", ".").strip()
        m = re.search(r"\d+(?:\.\d+)?", v)
        if not m:
            return None
        try:
            return float(m.group(0))
        except ValueError:
            return None
    return None


def _load_json_list(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        out: List[Dict[str, Any]] = []
        for item in data:
            if isinstance(item, dict):
                out.append(item)
        return out
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
    # de-dupe while preserving order
    seen: set[Path] = set()
    uniq: List[Path] = []
    for p in out:
        rp = p.resolve()
        if rp not in seen:
            seen.add(rp)
            uniq.append(p)
    return uniq


@dataclass
class Offer:
    source: str
    bank_raw: str
    buy: Optional[float]
    sell: Optional[float]
    address: str
    input_files: List[str] = field(default_factory=list)

    def key(self) -> Tuple[Any, ...]:
        return (
            self.source,
            _compact_spaces(self.bank_raw).lower(),
            self.buy,
            self.sell,
            _compact_spaces(self.address).lower(),
        )


def merge_rates(files: List[Path]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    total_records = 0
    bad_records = 0

    grouped: Dict[Tuple[str, str], Dict[str, Any]] = {}

    for file_path in files:
        items = _load_json_list(file_path)
        for item in items:
            total_records += 1
            bank_raw = (item.get("bank") or "").strip()
            currency = (item.get("currency") or "").strip().upper()
            if not bank_raw or not currency:
                bad_records += 1
                continue

            bank_base = _extract_base_bank_name(bank_raw)
            bank_norm = _bank_key(bank_base)
            if not bank_norm:
                bad_records += 1
                continue

            source = (item.get("source") or "").strip() or _infer_source(file_path)
            buy = _safe_float(item.get("buy"))
            sell = _safe_float(item.get("sell"))
            address = (item.get("address") or "").strip()

            group_key = (bank_norm, currency)
            group = grouped.get(group_key)
            if not group:
                group = {
                    "bank": bank_base,
                    "bank_norm": bank_norm,
                    "currency": currency,
                    "offers": {},  # offer_key -> Offer
                }
                grouped[group_key] = group

            offer = Offer(
                source=source,
                bank_raw=bank_raw,
                buy=buy,
                sell=sell,
                address=address,
                input_files=[file_path.name],
            )
            offer_key = offer.key()
            existing: Offer | None = group["offers"].get(offer_key)
            if existing is None:
                group["offers"][offer_key] = offer
            else:
                if file_path.name not in existing.input_files:
                    existing.input_files.append(file_path.name)

    merged: List[Dict[str, Any]] = []
    for (_bank_norm, _currency), group in grouped.items():
        offers: List[Offer] = list(group["offers"].values())
        sources = sorted({o.source for o in offers})

        best_buy_offer = None
        best_sell_offer = None
        for o in offers:
            if o.buy is not None:
                if best_buy_offer is None or o.buy < best_buy_offer.buy:  # type: ignore[operator]
                    best_buy_offer = o
            if o.sell is not None:
                if best_sell_offer is None or o.sell > best_sell_offer.sell:  # type: ignore[operator]
                    best_sell_offer = o

        merged.append(
            {
                "bank": group["bank"],
                "bank_norm": group["bank_norm"],
                "currency": group["currency"],
                "sources": sources,
                "offers_count": len(offers),
                "best_buy": None
                if best_buy_offer is None
                else {
                    "value": best_buy_offer.buy,
                    "source": best_buy_offer.source,
                    "bank_raw": best_buy_offer.bank_raw,
                },
                "best_sell": None
                if best_sell_offer is None
                else {
                    "value": best_sell_offer.sell,
                    "source": best_sell_offer.source,
                    "bank_raw": best_sell_offer.bank_raw,
                },
                "offers": [
                    {
                        "source": o.source,
                        "bank_raw": o.bank_raw,
                        "buy": o.buy,
                        "sell": o.sell,
                        "address": o.address,
                        "input_files": sorted(o.input_files),
                    }
                    for o in sorted(
                        offers,
                        key=lambda x: (x.source, x.buy if x.buy is not None else 10**9, x.sell or -10**9),
                    )
                ],
            }
        )

    merged.sort(key=lambda r: (r["currency"], r["bank_norm"]))
    stats = {
        "input_files": [p.name for p in files],
        "input_records_total": total_records,
        "input_records_bad": bad_records,
        "output_banks": len(merged),
        "output_offers_total": sum(r["offers_count"] for r in merged),
    }
    return merged, stats


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv_summary(path: Path, merged: List[Dict[str, Any]]) -> None:
    fields = [
        "bank",
        "bank_norm",
        "currency",
        "offers_count",
        "sources",
        "best_buy",
        "best_buy_source",
        "best_sell",
        "best_sell_source",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in merged:
            best_buy = r["best_buy"]["value"] if r.get("best_buy") else None
            best_buy_source = r["best_buy"]["source"] if r.get("best_buy") else None
            best_sell = r["best_sell"]["value"] if r.get("best_sell") else None
            best_sell_source = r["best_sell"]["source"] if r.get("best_sell") else None
            w.writerow(
                {
                    "bank": r["bank"],
                    "bank_norm": r["bank_norm"],
                    "currency": r["currency"],
                    "offers_count": r["offers_count"],
                    "sources": ",".join(r["sources"]),
                    "best_buy": best_buy,
                    "best_buy_source": best_buy_source,
                    "best_sell": best_sell,
                    "best_sell_source": best_sell_source,
                }
            )


def main() -> int:
    ap = argparse.ArgumentParser(description="Merge & dedupe currency rate JSON lists.")
    ap.add_argument(
        "--inputs",
        nargs="+",
        required=True,
        help='Input files/globs, e.g. "rbc_all_banks_*.json" "banki_rates_*.json"',
    )
    ap.add_argument("--out", default="", help="Output JSON path (default: merged_rates_<ts>.json)")
    ap.add_argument(
        "--csv",
        default="",
        help="Optional CSV summary path (default: alongside JSON with _summary.csv)",
    )
    args = ap.parse_args()

    files = _expand_inputs(args.inputs)
    if not files:
        raise SystemExit("No input files matched.")

    merged, stats = merge_rates(files)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_json = Path(args.out) if args.out else Path(f"merged_rates_{ts}.json")
    out_csv = Path(args.csv) if args.csv else out_json.with_name(out_json.stem + "_summary.csv")

    payload = {"stats": stats, "data": merged}
    _write_json(out_json, payload)
    _write_csv_summary(out_csv, merged)

    # Short console stats
    src_counts = Counter()
    for r in merged:
        for s in r["sources"]:
            src_counts[s] += 1
    print(f"✅ Input files: {len(files)}")
    print(f"✅ Input records: {stats['input_records_total']} (bad: {stats['input_records_bad']})")
    print(f"✅ Unique banks: {stats['output_banks']} (offers total: {stats['output_offers_total']})")
    print(f"✅ Output: {out_json}")
    print(f"✅ CSV: {out_csv}")
    if src_counts:
        print("Sources (banks with offers): " + ", ".join(f"{k}={v}" for k, v in src_counts.most_common()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

