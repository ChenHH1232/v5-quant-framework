from __future__ import annotations

import argparse
import csv
import json
import math
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


START_YEAR = 2013
END_YEAR = 2026
FREQUENCY = "5min"
ADJUST_FLAG = "unadjusted"
SOURCE = "local_1min_package_aggregated"
AGGREGATION_RULE = "1min_end_labeled_5bar_groups_0931_to_0935"

OUTPUT_COLUMNS = [
    "code",
    "local_code",
    "trade_date",
    "datetime",
    "time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
    "bar_count",
    "frequency",
    "adjustflag",
    "source",
    "aggregation_rule",
    "source_year",
    "created_at_utc",
]

INDEX_COLUMNS = [
    "code",
    "local_code",
    "year",
    "path",
    "row_count",
    "stock_days",
    "full_48_days",
    "bar_count_modes",
    "source_1min_rows",
    "source_stock_days",
    "source_full_240_days",
    "source_bad_ohlc_rows",
    "source_bad_vol_amount_rows",
    "status",
    "notes",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def find_v5_database(root: Path) -> Path:
    for child in root.iterdir():
        if child.is_dir() and (child / "processed").exists() and (child / "raw").exists() and (child / "manifests").exists():
            return child
    raise FileNotFoundError("Could not locate V5 database directory with processed/raw/manifests children.")


def find_local_minute_package() -> Path:
    base = Path("D:/hh")
    candidates = [p for p in base.iterdir() if p.is_dir() and "2000" in p.name and "2026" in p.name]
    if not candidates:
        raise FileNotFoundError("Could not locate local 1-minute package under D:/hh.")
    package_root = candidates[0]
    kline_pack = next((p for p in package_root.iterdir() if p.is_dir()), None)
    if kline_pack is None:
        raise FileNotFoundError(f"Could not locate K-line package directory under {package_root}.")
    history_dir = next((p for p in kline_pack.iterdir() if p.is_dir() and any((p / f"{y}.zip").exists() for y in (START_YEAR, END_YEAR))), None)
    if history_dir is None:
        history_dirs = [p for p in kline_pack.iterdir() if p.is_dir()]
        for directory in history_dirs:
            minute_dir = next((p for p in directory.iterdir() if p.is_dir() and (p / f"{START_YEAR}.zip").exists()), None)
            if minute_dir is not None:
                return minute_dir
        raise FileNotFoundError(f"Could not locate annual 1-minute zip directory under {kline_pack}.")
    minute_dir = next((p for p in history_dir.iterdir() if p.is_dir() and (p / f"{START_YEAR}.zip").exists()), None)
    if minute_dir is None:
        raise FileNotFoundError(f"Could not locate annual 1-minute zip directory under {history_dir}.")
    return minute_dir


def decode_bytes(raw: bytes) -> str:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
        try:
            return raw.decode(encoding)
        except Exception as exc:  # pragma: no cover - diagnostic fallback
            last_error = exc
    if last_error:
        raise last_error
    raise UnicodeDecodeError("unknown", b"", 0, 1, "empty decoder list")


def jq_to_local(code: str) -> str:
    plain = code.split(".")[0]
    if code.endswith(".XSHE"):
        return f"{plain}.SZ"
    if code.endswith(".XSHG"):
        return f"{plain}.SH"
    raise ValueError(f"Unsupported V5 code: {code}")


def local_to_jq(code: str) -> str:
    plain = code.split(".")[0]
    if code.endswith(".SZ"):
        return f"{plain}.XSHE"
    if code.endswith(".SH"):
        return f"{plain}.XSHG"
    raise ValueError(f"Unsupported local code: {code}")


def safe_float(value: str) -> float:
    try:
        return float(value)
    except Exception:
        return math.nan


def valid_number(value: float) -> bool:
    return math.isfinite(value)


def rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def collect_universe(root: Path, db: Path) -> list[dict[str, str]]:
    sources: dict[str, set[str]] = defaultdict(set)
    sleeve_by_code: dict[str, set[str]] = defaultdict(set)
    price_dir = db / "processed" / "startup_preload_repaired_prices_v5"
    sleeve_map = {
        "bank_v3_startup_repaired_daily_prices.csv": "bank",
        "highway_v54h_startup_repaired_daily_prices.csv": "highway_infrastructure",
        "port_rail_v55j_startup_repaired_daily_prices.csv": "port_rail_infrastructure",
        "utilities_v51f_startup_repaired_daily_prices.csv": "utilities_electricity",
    }
    for path in sorted(price_dir.glob("*.csv")):
        sleeve = sleeve_map.get(path.name, path.stem)
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = str(row.get("code", "")).strip()
                if not code:
                    continue
                sources[code].add(path.name)
                sleeve_by_code[code].add(sleeve)
    req = root / "v5e_full_holding_5min_data_gate" / "current" / "v5e_full_holding_5min_requirement.csv"
    if req.exists():
        with req.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = str(row.get("code", "")).strip()
                if not code:
                    continue
                sources[code].add("v5e_full_holding_5min_requirement.csv")
                sleeve = str(row.get("sleeve", "")).strip()
                if sleeve:
                    sleeve_by_code[code].add(sleeve)
    rows = []
    for code in sorted(sources):
        rows.append(
            {
                "code": code,
                "local_code": jq_to_local(code),
                "sleeves": ";".join(sorted(sleeve_by_code[code])),
                "source_files": ";".join(sorted(sources[code])),
            }
        )
    return rows


def grouped_5min_rows(
    rows: Iterable[list[str]],
    jq_code: str,
    local_code: str,
    year: int,
    created_at: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_day: dict[str, list[tuple[str, float, float, float, float, float, float]]] = defaultdict(list)
    source_rows = 0
    bad_ohlc = 0
    bad_vol_amount = 0
    for row in rows:
        if len(row) < 7:
            continue
        trade_time = row[0]
        values = [safe_float(row[index]) for index in range(1, 7)]
        if any(not valid_number(value) for value in values):
            continue
        open_, high, low, close, volume, amount = values
        if high + 1e-12 < max(open_, low, close) or low - 1e-12 > min(open_, high, close):
            bad_ohlc += 1
        if volume < -1e-12 or amount < -1e-12:
            bad_vol_amount += 1
        trade_date = trade_time[:10]
        by_day[trade_date].append((trade_time, open_, high, low, close, volume, amount))
        source_rows += 1

    output: list[dict[str, Any]] = []
    bar_counts_by_day: Counter[int] = Counter()
    source_counts_by_day: Counter[int] = Counter()
    for trade_date in sorted(by_day):
        day_rows = sorted(by_day[trade_date], key=lambda item: item[0])
        source_counts_by_day[len(day_rows)] += 1
        day_bar_count = 0
        for start in range(0, len(day_rows), 5):
            chunk = day_rows[start : start + 5]
            if len(chunk) < 5:
                continue
            end_time = chunk[-1][0]
            output.append(
                {
                    "code": jq_code,
                    "local_code": local_code,
                    "trade_date": trade_date,
                    "datetime": end_time,
                    "time": end_time.split(" ")[1] if " " in end_time else "",
                    "open": chunk[0][1],
                    "high": max(item[2] for item in chunk),
                    "low": min(item[3] for item in chunk),
                    "close": chunk[-1][4],
                    "volume": sum(item[5] for item in chunk),
                    "amount": sum(item[6] for item in chunk),
                    "bar_count": len(chunk),
                    "frequency": FREQUENCY,
                    "adjustflag": ADJUST_FLAG,
                    "source": SOURCE,
                    "aggregation_rule": AGGREGATION_RULE,
                    "source_year": year,
                    "created_at_utc": created_at,
                }
            )
            day_bar_count += 1
        bar_counts_by_day[day_bar_count] += 1
    audit = {
        "source_1min_rows": source_rows,
        "source_stock_days": len(by_day),
        "source_full_240_days": source_counts_by_day.get(240, 0),
        "source_bad_ohlc_rows": bad_ohlc,
        "source_bad_vol_amount_rows": bad_vol_amount,
        "stock_days": sum(bar_counts_by_day.values()),
        "full_48_days": bar_counts_by_day.get(48, 0),
        "bar_count_modes": json.dumps(dict(bar_counts_by_day.most_common(4)), ensure_ascii=False),
    }
    return output, audit


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def count_existing_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig") as f:
        return max(sum(1 for _ in f) - 1, 0)


def ingest_year(root: Path, year: int, force: bool = False) -> list[dict[str, Any]]:
    db = find_v5_database(root)
    minute_dir = find_local_minute_package()
    processed = db / "processed" / "local_5min_2013_2026"
    manifest_dir = db / "manifests" / "local_5min_2013_2026"
    processed.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    universe = collect_universe(root, db)
    write_dicts(processed / "v5_required_5min_universe.csv", universe, ["code", "local_code", "sleeves", "source_files"])
    zip_path = minute_dir / f"{year}.zip"
    if not zip_path.exists():
        raise FileNotFoundError(f"Missing local 1-minute annual zip: {zip_path}")

    created_at = now_utc()
    year_dir = processed / "by_year" / str(year)
    index_rows: list[dict[str, Any]] = []
    with zipfile.ZipFile(zip_path) as zf:
        entry_names = {info.filename for info in zf.infolist() if not info.is_dir() and info.filename.lower().endswith(".csv")}
        for item in universe:
            jq_code = item["code"]
            local_code = item["local_code"]
            output_path = year_dir / f"{jq_code.replace('.', '_')}_5min.csv"
            rel_path = rel(root, output_path)
            if output_path.exists() and not force:
                row_count = count_existing_rows(output_path)
                index_rows.append(
                    {
                        "code": jq_code,
                        "local_code": local_code,
                        "year": year,
                        "path": rel_path,
                        "row_count": row_count,
                        "stock_days": "",
                        "full_48_days": "",
                        "bar_count_modes": "",
                        "source_1min_rows": "",
                        "source_stock_days": "",
                        "source_full_240_days": "",
                        "source_bad_ohlc_rows": "",
                        "source_bad_vol_amount_rows": "",
                        "status": "existing_reused",
                        "notes": "",
                    }
                )
                continue
            entry = f"{year}/{local_code}.csv"
            if entry not in entry_names:
                index_rows.append(
                    {
                        "code": jq_code,
                        "local_code": local_code,
                        "year": year,
                        "path": "",
                        "row_count": 0,
                        "stock_days": 0,
                        "full_48_days": 0,
                        "bar_count_modes": "",
                        "source_1min_rows": 0,
                        "source_stock_days": 0,
                        "source_full_240_days": 0,
                        "source_bad_ohlc_rows": 0,
                        "source_bad_vol_amount_rows": 0,
                        "status": "missing_entry",
                        "notes": "entry_missing_in_annual_zip_probably_not_listed_or_no_data",
                    }
                )
                continue
            raw = zf.read(entry)
            text = decode_bytes(raw)
            reader = csv.reader(text.splitlines())
            header = next(reader, [])
            if header[:7] != ["trade_time", "open", "high", "low", "close", "vol", "amount"]:
                notes = "unexpected_source_header"
            else:
                notes = ""
            rows, audit = grouped_5min_rows(reader, jq_code, local_code, year, created_at)
            if rows:
                write_rows(output_path, rows)
                status = "pass"
            else:
                status = "empty_after_aggregation"
            if audit["source_bad_ohlc_rows"] or audit["source_bad_vol_amount_rows"]:
                notes = ";".join(filter(None, [notes, "source_minute_quality_warning"]))
            if audit["stock_days"] and audit["full_48_days"] / audit["stock_days"] < 0.98:
                notes = ";".join(filter(None, [notes, "non_48_5min_day_count_present"]))
            index_rows.append(
                {
                    "code": jq_code,
                    "local_code": local_code,
                    "year": year,
                    "path": rel_path if rows else "",
                    "row_count": len(rows),
                    "stock_days": audit["stock_days"],
                    "full_48_days": audit["full_48_days"],
                    "bar_count_modes": audit["bar_count_modes"],
                    "source_1min_rows": audit["source_1min_rows"],
                    "source_stock_days": audit["source_stock_days"],
                    "source_full_240_days": audit["source_full_240_days"],
                    "source_bad_ohlc_rows": audit["source_bad_ohlc_rows"],
                    "source_bad_vol_amount_rows": audit["source_bad_vol_amount_rows"],
                    "status": status,
                    "notes": notes,
                }
            )
    year_index = manifest_dir / f"v5_required_5min_index_{year}.csv"
    write_dicts(year_index, index_rows, INDEX_COLUMNS)
    refresh_combined_outputs(root)
    return index_rows


def refresh_combined_outputs(root: Path) -> dict[str, Any]:
    db = find_v5_database(root)
    processed = db / "processed" / "local_5min_2013_2026"
    manifest_dir = db / "manifests" / "local_5min_2013_2026"
    universe = collect_universe(root, db)
    write_dicts(processed / "v5_required_5min_universe.csv", universe, ["code", "local_code", "sleeves", "source_files"])
    rows: list[dict[str, Any]] = []
    for path in sorted(manifest_dir.glob("v5_required_5min_index_*.csv")):
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            rows.extend(csv.DictReader(f))
    write_dicts(processed / "v5_required_5min_standardized_index.csv", rows, INDEX_COLUMNS)
    write_dicts(manifest_dir / "v5_required_5min_coverage_audit.csv", rows, INDEX_COLUMNS)

    status_counts = Counter(row.get("status", "") for row in rows)
    years = sorted({int(row["year"]) for row in rows if str(row.get("year", "")).isdigit()})
    file_rows = [row for row in rows if row.get("path")]
    missing_rows = [row for row in rows if row.get("status") == "missing_entry"]
    warning_rows = [row for row in rows if row.get("notes")]
    total_5min_rows = sum(int(row.get("row_count") or 0) for row in rows)
    total_stock_days = sum(int(row.get("stock_days") or 0) for row in rows if str(row.get("stock_days", "")).isdigit())
    total_full_48_days = sum(int(row.get("full_48_days") or 0) for row in rows if str(row.get("full_48_days", "")).isdigit())
    summary = {
        "created_at_utc": now_utc(),
        "dataset_id": "local_5min_2013_2026",
        "status": "completed" if years and min(years) <= START_YEAR and max(years) >= END_YEAR else "partial",
        "years_loaded": years,
        "target_year_start": START_YEAR,
        "target_year_end": END_YEAR,
        "universe_code_count": len(universe),
        "index_rows": len(rows),
        "stored_file_count": len(file_rows),
        "missing_entry_count": len(missing_rows),
        "warning_count": len(warning_rows),
        "total_5min_rows": total_5min_rows,
        "total_stock_days": total_stock_days,
        "full_48_stock_days": total_full_48_days,
        "full_48_stock_day_rate_pct": round(total_full_48_days / total_stock_days * 100, 6) if total_stock_days else 0.0,
        "status_counts": dict(status_counts),
        "processed_dir": "<v5_database>/processed/local_5min_2013_2026",
        "manifest_dir": "<v5_database>/manifests/local_5min_2013_2026",
        "processed_relative_dir": "processed/local_5min_2013_2026",
        "manifest_relative_dir": "manifests/local_5min_2013_2026",
        "source": SOURCE,
        "frequency": FREQUENCY,
        "adjustflag": ADJUST_FLAG,
        "aggregation_rule": AGGREGATION_RULE,
        "research_boundary": "Use pre-2021 only for training/independent validation; 2021-05-01 to 2026-05-31 remains formal backtest; post-2026-05-31 must be forward/paper only.",
    }
    write_json(manifest_dir / "collection_manifest.json", summary)
    report = (
        "# Local 5-Minute Data Ingestion\n\n"
        f"- Dataset: `{summary['dataset_id']}`\n"
        f"- Years loaded: `{years[0] if years else ''}` to `{years[-1] if years else ''}`\n"
        f"- Universe codes: `{summary['universe_code_count']}`\n"
        f"- Stored files: `{summary['stored_file_count']}`\n"
        f"- Total 5-minute rows: `{summary['total_5min_rows']}`\n"
        f"- Full 48-bar stock-day rate: `{summary['full_48_stock_day_rate_pct']}%`\n"
        f"- Missing entries: `{summary['missing_entry_count']}`; mostly pre-IPO/not listed/no data years.\n"
        f"- Warnings: `{summary['warning_count']}`\n\n"
        "This dataset is generated from the local 1-minute package. Daily OHLC remains canonical for daily-return work; this dataset is for intraday path, VWAP, spike/reversion, and 5-minute diagnostics.\n\n"
        "Boundary: pre-2021 data may be used for training or independent validation. The 2021-05-01 to 2026-05-31 window remains the formal backtest window. Data after 2026-05-31 is forward/paper only.\n"
    )
    (manifest_dir / "collection_report.md").write_text(report, encoding="utf-8")
    return summary


def write_dicts(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_years(value: str) -> list[int]:
    if "-" in value:
        start, end = value.split("-", 1)
        return list(range(int(start), int(end) + 1))
    return [int(part.strip()) for part in value.split(",") if part.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate local 1-minute A-share package into V5 5-minute database files.")
    parser.add_argument("--years", default=f"{START_YEAR}-{END_YEAR}")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    root = Path.cwd()
    summaries = []
    for year in parse_years(args.years):
        rows = ingest_year(root, year, force=args.force)
        status_counts = Counter(row.get("status", "") for row in rows)
        stored_rows = sum(int(row.get("row_count") or 0) for row in rows)
        print(json.dumps({"year": year, "status_counts": dict(status_counts), "stored_5min_rows": stored_rows}, ensure_ascii=False))
        summaries.append({"year": year, "status_counts": dict(status_counts), "stored_5min_rows": stored_rows})
    combined = refresh_combined_outputs(root)
    print(json.dumps({"year_runs": summaries, "combined": combined}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
