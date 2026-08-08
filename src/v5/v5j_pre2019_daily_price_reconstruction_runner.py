from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DB = Path("数据库")
INDEX = DB / "processed" / "local_1min_clean_2013_2026" / "v5_required_1min_standardized_index.csv"
OUT_DIR = DB / "processed" / "pre2019_reconstructed_daily_prices_v5"
MANIFEST_DIR = DB / "manifests" / "pre2019_reconstructed_daily_prices_v5"
YEARS = range(2013, 2019)
FIELDS = ["date", "code", "open", "high", "low", "close", "volume", "amount", "minute_bar_count", "price_adjustment", "source", "quality_status"]


def run_v5j_pre2019_daily_price_reconstruction(root: Path = Path(".")) -> dict[str, Any]:
    index_path = root / INDEX
    if not index_path.exists():
        raise FileNotFoundError(index_path)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    index_rows = _read_csv(index_path)
    out_path = root / OUT_DIR / "v5_pre2019_daily_prices_from_1min.csv"
    audits: list[dict[str, Any]] = []
    total_days = 0
    with out_path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=FIELDS)
        writer.writeheader()
        for year in YEARS:
            year_rows = [row for row in index_rows if row.get("year") == str(year) and row.get("status") == "pass" and row.get("path")]
            year_days = year_bars = missing = 0
            for item in year_rows:
                source = root / item["path"]
                if not source.exists():
                    missing += 1
                    continue
                daily = _aggregate_file(source)
                for row in daily:
                    writer.writerow(row)
                year_days += len(daily)
                year_bars += sum(int(row["minute_bar_count"]) for row in daily)
            total_days += year_days
            audits.append({"year": year, "indexed_pass_files": len(year_rows), "missing_source_files": missing, "daily_rows": year_days, "minute_rows_aggregated": year_bars, "status": "pass" if year_rows and not missing else "partial"})
    summary = {"created_at_utc": _now(), "task": "v5j_pre2019_daily_price_reconstruction", "status": "completed_local_unadjusted_daily_price_layer", "year_start": 2013, "year_end": 2018, "daily_row_count": total_days, "price_adjustment": "raw_unadjusted_from_clean_1min", "factor_or_dividend_panel_created": False, "pit_universe_created": False, "accepted": False}
    _write_csv(root / MANIFEST_DIR / "v5_pre2019_daily_price_reconstruction_audit.csv", audits)
    (root / MANIFEST_DIR / "v5_pre2019_daily_price_reconstruction_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def _aggregate_file(path: Path) -> list[dict[str, Any]]:
    daily: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            date = row["trade_date"]
            current = daily.get(date)
            if current is None:
                current = {"date": date, "code": row["code"], "open": float(row["open"]), "high": float(row["high"]), "low": float(row["low"]), "close": float(row["close"]), "volume": float(row["volume"]), "amount": float(row["amount"]), "minute_bar_count": 1, "price_adjustment": "raw_unadjusted_from_clean_1min", "source": "local_1min_clean_2013_2026", "quality_status": "pass"}
                daily[date] = current
            else:
                current["high"] = max(current["high"], float(row["high"]))
                current["low"] = min(current["low"], float(row["low"]))
                current["close"] = float(row["close"])
                current["volume"] += float(row["volume"])
                current["amount"] += float(row["amount"])
                current["minute_bar_count"] += 1
    return [daily[key] for key in sorted(daily)]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["empty"])
        writer.writeheader()
        writer.writerows(rows)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    print(json.dumps(run_v5j_pre2019_daily_price_reconstruction(), ensure_ascii=False, indent=2))
