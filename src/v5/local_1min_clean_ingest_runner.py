from __future__ import annotations

import argparse
import csv
import json
import math
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


START_YEAR = 2013
END_YEAR = 2026
DATASET_ID = "local_1min_clean_2013_2026"
SOURCE = "local_1min_package_cleaned"
FREQUENCY = "1min"
ADJUST_FLAG = "unadjusted"
TRADING_MINUTE_WINDOWS = (("09:31:00", "11:30:00"), ("13:01:00", "15:00:00"))
EXPECTED_MINUTES_PER_FULL_DAY = 240

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
    "frequency",
    "adjustflag",
    "source",
    "source_year",
    "quality_status",
    "created_at_utc",
]

INDEX_COLUMNS = [
    "code",
    "local_code",
    "year",
    "path",
    "row_count",
    "stock_days",
    "full_240_days",
    "minute_count_modes",
    "source_rows",
    "dropped_parse_rows",
    "dropped_out_of_session_rows",
    "dropped_bad_ohlc_rows",
    "dropped_bad_vol_amount_rows",
    "duplicate_datetime_rows",
    "status",
    "notes",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_local_1min_clean_ingest(
    root: Path = Path("."),
    *,
    years: list[int] | None = None,
    force: bool = False,
    source_minute_dir: Path | None = None,
    max_codes: int | None = None,
) -> dict[str, Any]:
    years = years or list(range(START_YEAR, END_YEAR + 1))
    for year in years:
        ingest_year(root, year, force=force, source_minute_dir=source_minute_dir, max_codes=max_codes)
    return refresh_combined_outputs(root)


def ingest_year(
    root: Path,
    year: int,
    *,
    force: bool = False,
    source_minute_dir: Path | None = None,
    max_codes: int | None = None,
) -> list[dict[str, Any]]:
    db = find_v5_database(root)
    minute_dir = source_minute_dir or find_local_minute_package()
    processed = db / "processed" / DATASET_ID
    manifest_dir = db / "manifests" / DATASET_ID
    processed.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    universe = collect_universe(root, db)
    if max_codes is not None:
        universe = universe[:max_codes]
    write_dicts(processed / "v5_required_1min_universe.csv", universe, ["code", "local_code", "sleeves", "source_files"])

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
            output_path = year_dir / f"{jq_code.replace('.', '_')}_1min.csv"
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
                        "full_240_days": "",
                        "minute_count_modes": "",
                        "source_rows": "",
                        "dropped_parse_rows": "",
                        "dropped_out_of_session_rows": "",
                        "dropped_bad_ohlc_rows": "",
                        "dropped_bad_vol_amount_rows": "",
                        "duplicate_datetime_rows": "",
                        "status": "existing_reused",
                        "notes": "",
                    }
                )
                continue

            entry = f"{year}/{local_code}.csv"
            if entry not in entry_names:
                index_rows.append(_missing_index_row(jq_code, local_code, year))
                continue

            text = decode_bytes(zf.read(entry))
            reader = csv.reader(text.splitlines())
            header = next(reader, [])
            notes = "" if header[:7] == ["trade_time", "open", "high", "low", "close", "vol", "amount"] else "unexpected_source_header"
            cleaned_rows, audit = clean_1min_rows(reader, jq_code, local_code, year, created_at)
            if cleaned_rows:
                write_rows(output_path, cleaned_rows)
                status = "pass"
            else:
                status = "empty_after_cleaning"
            warning_notes = quality_notes(audit)
            notes = ";".join(part for part in [notes, warning_notes] if part)
            index_rows.append(
                {
                    "code": jq_code,
                    "local_code": local_code,
                    "year": year,
                    "path": rel_path if cleaned_rows else "",
                    "row_count": len(cleaned_rows),
                    "stock_days": audit["stock_days"],
                    "full_240_days": audit["full_240_days"],
                    "minute_count_modes": audit["minute_count_modes"],
                    "source_rows": audit["source_rows"],
                    "dropped_parse_rows": audit["dropped_parse_rows"],
                    "dropped_out_of_session_rows": audit["dropped_out_of_session_rows"],
                    "dropped_bad_ohlc_rows": audit["dropped_bad_ohlc_rows"],
                    "dropped_bad_vol_amount_rows": audit["dropped_bad_vol_amount_rows"],
                    "duplicate_datetime_rows": audit["duplicate_datetime_rows"],
                    "status": status,
                    "notes": notes,
                }
            )

    write_dicts(manifest_dir / f"v5_required_1min_index_{year}.csv", index_rows, INDEX_COLUMNS)
    refresh_combined_outputs(root)
    return index_rows


def clean_1min_rows(
    rows: Any,
    jq_code: str,
    local_code: str,
    year: int,
    created_at: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_datetime: dict[str, dict[str, Any]] = {}
    source_rows = 0
    dropped_parse = 0
    dropped_out_of_session = 0
    dropped_bad_ohlc = 0
    dropped_bad_vol_amount = 0
    duplicate_datetime = 0

    for source_row in rows:
        source_rows += 1
        if len(source_row) < 7:
            dropped_parse += 1
            continue
        trade_time = str(source_row[0]).strip()
        parsed = parse_trade_time(trade_time)
        if parsed is None:
            dropped_parse += 1
            continue
        trade_date, time_value = parsed
        if not is_trading_minute(time_value):
            dropped_out_of_session += 1
            continue
        values = [safe_float(source_row[index]) for index in range(1, 7)]
        if any(value is None for value in values):
            dropped_parse += 1
            continue
        open_, high, low, close, volume, amount = values
        if high + 1e-12 < max(open_, low, close) or low - 1e-12 > min(open_, high, close):
            dropped_bad_ohlc += 1
            continue
        if volume < -1e-12 or amount < -1e-12:
            dropped_bad_vol_amount += 1
            continue
        if trade_time in by_datetime:
            duplicate_datetime += 1
        by_datetime[trade_time] = {
            "code": jq_code,
            "local_code": local_code,
            "trade_date": trade_date,
            "datetime": trade_time,
            "time": time_value,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "amount": amount,
            "frequency": FREQUENCY,
            "adjustflag": ADJUST_FLAG,
            "source": SOURCE,
            "source_year": year,
            "quality_status": "pass",
            "created_at_utc": created_at,
        }

    cleaned = [by_datetime[key] for key in sorted(by_datetime)]
    day_counts = Counter(row["trade_date"] for row in cleaned)
    minute_count_modes = Counter(day_counts.values())
    audit = {
        "source_rows": source_rows,
        "dropped_parse_rows": dropped_parse,
        "dropped_out_of_session_rows": dropped_out_of_session,
        "dropped_bad_ohlc_rows": dropped_bad_ohlc,
        "dropped_bad_vol_amount_rows": dropped_bad_vol_amount,
        "duplicate_datetime_rows": duplicate_datetime,
        "stock_days": len(day_counts),
        "full_240_days": sum(1 for count in day_counts.values() if count == EXPECTED_MINUTES_PER_FULL_DAY),
        "minute_count_modes": json.dumps(dict(minute_count_modes.most_common(5)), ensure_ascii=False),
    }
    return cleaned, audit


def parse_trade_time(value: str) -> tuple[str, str] | None:
    if len(value) < 19 or " " not in value:
        return None
    date_part, time_part = value[:10], value[11:19]
    try:
        datetime.strptime(f"{date_part} {time_part}", "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
    return date_part, time_part


def is_trading_minute(time_value: str) -> bool:
    return any(start <= time_value <= end for start, end in TRADING_MINUTE_WINDOWS)


def safe_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def quality_notes(audit: dict[str, Any]) -> str:
    notes = []
    for key in [
        "dropped_parse_rows",
        "dropped_out_of_session_rows",
        "dropped_bad_ohlc_rows",
        "dropped_bad_vol_amount_rows",
        "duplicate_datetime_rows",
    ]:
        if int(audit.get(key) or 0) > 0:
            notes.append(key)
    stock_days = int(audit.get("stock_days") or 0)
    full_days = int(audit.get("full_240_days") or 0)
    if stock_days and full_days / stock_days < 0.98:
        notes.append("non_240_minute_day_count_present")
    return ";".join(notes)


def refresh_combined_outputs(root: Path) -> dict[str, Any]:
    db = find_v5_database(root)
    processed = db / "processed" / DATASET_ID
    manifest_dir = db / "manifests" / DATASET_ID
    universe = collect_universe(root, db)
    write_dicts(processed / "v5_required_1min_universe.csv", universe, ["code", "local_code", "sleeves", "source_files"])

    rows: list[dict[str, Any]] = []
    for path in sorted(manifest_dir.glob("v5_required_1min_index_*.csv")):
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows.extend(csv.DictReader(handle))
    write_dicts(processed / "v5_required_1min_standardized_index.csv", rows, INDEX_COLUMNS)
    write_dicts(manifest_dir / "v5_required_1min_coverage_audit.csv", rows, INDEX_COLUMNS)
    warning_rows = [row for row in rows if str(row.get("notes") or "").strip()]
    write_dicts(manifest_dir / "v5_required_1min_quality_warnings.csv", warning_rows, INDEX_COLUMNS)

    status_counts = Counter(row.get("status", "") for row in rows)
    years = sorted({int(row["year"]) for row in rows if str(row.get("year", "")).isdigit()})
    file_rows = [row for row in rows if row.get("path")]
    total_rows = sum(int(row.get("row_count") or 0) for row in rows)
    total_stock_days = sum(int(row.get("stock_days") or 0) for row in rows if str(row.get("stock_days", "")).isdigit())
    full_240_days = sum(int(row.get("full_240_days") or 0) for row in rows if str(row.get("full_240_days", "")).isdigit())
    dropped_counts = {
        key: sum(int(row.get(key) or 0) for row in rows if str(row.get(key, "")).lstrip("-").isdigit())
        for key in [
            "dropped_parse_rows",
            "dropped_out_of_session_rows",
            "dropped_bad_ohlc_rows",
            "dropped_bad_vol_amount_rows",
            "duplicate_datetime_rows",
        ]
    }
    summary = {
        "created_at_utc": now_utc(),
        "dataset_id": DATASET_ID,
        "status": "completed" if years and min(years) <= START_YEAR and max(years) >= END_YEAR else "partial",
        "years_loaded": years,
        "target_year_start": START_YEAR,
        "target_year_end": END_YEAR,
        "universe_code_count": len(universe),
        "index_rows": len(rows),
        "stored_file_count": len(file_rows),
        "missing_entry_count": sum(1 for row in rows if row.get("status") == "missing_entry"),
        "warning_count": len(warning_rows),
        "total_1min_rows": total_rows,
        "total_stock_days": total_stock_days,
        "full_240_stock_days": full_240_days,
        "full_240_stock_day_rate_pct": round(full_240_days / total_stock_days * 100, 6) if total_stock_days else 0.0,
        "status_counts": dict(status_counts),
        "dropped_counts": dropped_counts,
        "processed_dir": "<v5_database>/processed/local_1min_clean_2013_2026",
        "manifest_dir": "<v5_database>/manifests/local_1min_clean_2013_2026",
        "processed_relative_dir": "processed/local_1min_clean_2013_2026",
        "manifest_relative_dir": "manifests/local_1min_clean_2013_2026",
        "source": SOURCE,
        "frequency": FREQUENCY,
        "adjustflag": ADJUST_FLAG,
        "cleaning_policy": "drop invalid parse/out-of-session/bad OHLC/negative volume or amount; de-duplicate exact datetimes; no filling; no adjustment",
        "research_boundary": "Use 2013-01-01 to 2021-04-30 only for prebacktest learning/validation; 2021-05-01 to 2026-05-31 remains formal backtest; post-2026-05-31 must be forward/paper only.",
    }
    write_json(manifest_dir / "collection_manifest.json", summary)
    (manifest_dir / "collection_report.md").write_text(collection_report(summary), encoding="utf-8")
    return summary


def collection_report(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Local 1-Minute Clean Data Ingestion",
            "",
            f"- Dataset: `{summary['dataset_id']}`",
            f"- Status: `{summary['status']}`",
            f"- Years loaded: `{summary['years_loaded']}`",
            f"- Universe codes: `{summary['universe_code_count']}`",
            f"- Stored files: `{summary['stored_file_count']}`",
            f"- Total 1-minute rows: `{summary['total_1min_rows']}`",
            f"- Full 240-minute stock-day rate: `{summary['full_240_stock_day_rate_pct']}%`",
            f"- Missing entries: `{summary['missing_entry_count']}`",
            f"- Warnings: `{summary['warning_count']}`",
            "",
            "Daily OHLC remains canonical for daily-return work. This 1-minute dataset is intended for execution audit, microstructure learning, VWAP/path quality, and 5-minute signal-quality validation.",
            "",
            "Cleaning policy: drop invalid rows, out-of-session rows, OHLC-inconsistent rows, and rows with negative volume/amount; de-duplicate exact timestamps; do not fill missing minutes; do not apply price adjustment.",
            "",
            "Boundary: 2013-01-01 to 2021-04-30 is prebacktest learning/validation; 2021-05-01 to 2026-05-31 is formal backtest; after 2026-05-31 is forward/paper only.",
            "",
        ]
    )


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
    preferred = package_root / "股票全周期K线包" / "历史数据" / "A股一分钟"
    if preferred.exists():
        return preferred
    for path in package_root.rglob("*.zip"):
        if path.name == f"{START_YEAR}.zip":
            return path.parent
    raise FileNotFoundError(f"Could not locate annual 1-minute zip directory under {package_root}.")


def decode_bytes(raw: bytes) -> str:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
        try:
            return raw.decode(encoding)
        except Exception as exc:
            last_error = exc
    if last_error:
        raise last_error
    raise UnicodeDecodeError("unknown", b"", 0, 1, "empty decoder list")


def collect_universe(root: Path, db: Path) -> list[dict[str, str]]:
    existing = db / "processed" / "local_5min_2013_2026" / "v5_required_5min_universe.csv"
    if existing.exists():
        with existing.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

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
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                code = str(row.get("code", "")).strip()
                if code:
                    sources[code].add(path.name)
                    sleeve_by_code[code].add(sleeve)
    return [
        {
            "code": code,
            "local_code": jq_to_local(code),
            "sleeves": ";".join(sorted(sleeve_by_code[code])),
            "source_files": ";".join(sorted(sources[code])),
        }
        for code in sorted(sources)
    ]


def jq_to_local(code: str) -> str:
    plain = code.split(".")[0]
    if code.endswith(".XSHE"):
        return f"{plain}.SZ"
    if code.endswith(".XSHG"):
        return f"{plain}.SH"
    raise ValueError(f"Unsupported V5 code: {code}")


def _missing_index_row(jq_code: str, local_code: str, year: int) -> dict[str, Any]:
    return {
        "code": jq_code,
        "local_code": local_code,
        "year": year,
        "path": "",
        "row_count": 0,
        "stock_days": 0,
        "full_240_days": 0,
        "minute_count_modes": "",
        "source_rows": 0,
        "dropped_parse_rows": 0,
        "dropped_out_of_session_rows": 0,
        "dropped_bad_ohlc_rows": 0,
        "dropped_bad_vol_amount_rows": 0,
        "duplicate_datetime_rows": 0,
        "status": "missing_entry",
        "notes": "entry_missing_in_annual_zip_probably_not_listed_or_no_data",
    }


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def write_dicts(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames or ["empty"], extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def count_existing_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig") as handle:
        return max(sum(1 for _ in handle) - 1, 0)


def rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def parse_years(value: str) -> list[int]:
    if "-" in value:
        start, end = value.split("-", 1)
        return list(range(int(start), int(end) + 1))
    return [int(part.strip()) for part in value.split(",") if part.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean local 1-minute V5 universe data into the V5 database.")
    parser.add_argument("--years", default=f"{START_YEAR}-{END_YEAR}")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--max-codes", type=int, default=None)
    args = parser.parse_args()
    summary = run_local_1min_clean_ingest(
        Path.cwd(),
        years=parse_years(args.years),
        force=args.force,
        max_codes=args.max_codes,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
