from __future__ import annotations

import csv
import json
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.local_1min_clean_ingest_runner import (
    INDEX_COLUMNS,
    clean_1min_rows,
    decode_bytes,
    find_local_minute_package,
    find_v5_database,
    jq_to_local,
)


OUT_DIR = Path("v5j_missing_1min_source_repair") / "current"
POOL_REL = Path("processed") / "pre2021_repaired_multisleeve_pit_pool_v5" / "repaired_multisleeve_pit_pool.csv"
INDEX_REL = Path("processed") / "local_1min_clean_2013_2026" / "v5_required_1min_standardized_index.csv"
DATASET_REL = Path("processed") / "local_1min_clean_2013_2026"
START_YEAR, END_YEAR = 2013, 2021


def run_v5j_missing_1min_source_repair(root: Path = Path("."), *, sleeves: set[str] | None = None) -> dict[str, Any]:
    """Repair only annual one-minute files required by dated PIT pool members."""
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    db = find_v5_database(root)
    pool = _read_csv(db / POOL_REL)
    old_index = _read_csv(db / INDEX_REL)
    requested = _required_code_years(pool, sleeves)
    old_map = {(r["code"], int(r["year"])): r for r in old_index if str(r.get("year", "")).isdigit()}
    needed = [r for r in requested if not _usable(old_map.get((r["code"], r["year"])))]
    source_root = find_local_minute_package()
    fresh, extraction_audit = _extract(root, db, source_root, needed)
    merged = _merge_index(old_index, fresh)
    _write_csv(db / INDEX_REL, merged)
    _write_csv(out / "v5j_missing_1min_requested_code_years.csv", requested)
    _write_csv(out / "v5j_missing_1min_extraction_audit.csv", extraction_audit)
    _write_csv(out / "v5j_missing_1min_repaired_index_rows.csv", fresh)
    remaining = [r for r in requested if not _usable({(x["code"], int(x["year"])): x for x in merged}.get((r["code"], r["year"])))]
    _write_csv(out / "v5j_missing_1min_remaining_gap_queue.csv", remaining)
    summary = {
        "created_at_utc": _now(), "task": "v5j_missing_1min_source_repair",
        "requested_code_year_count": len(requested), "repair_attempt_count": len(needed),
        "new_cleaned_file_count": sum(r.get("status") == "pass" for r in fresh),
        "remaining_source_gap_count": len(remaining),
        "scope": "dated PIT pool only; no bar substitution, no feature calculation, no technical validation",
        "technical_rule_validation_started": False, "accepted": False,
        "status": "pass" if not remaining else "partial_source_repair",
    }
    _write_json(out / "v5j_missing_1min_source_repair_summary.json", summary)
    (out / "v5j_missing_1min_source_repair_report.md").write_text(_report(summary), encoding="utf-8")
    return summary


def _required_code_years(pool: list[dict[str, str]], sleeves: set[str] | None) -> list[dict[str, Any]]:
    rows: dict[tuple[str, int], dict[str, Any]] = {}
    dates = sorted({r["rebalance_date"] for r in pool})
    next_date = {day: dates[index + 1] if index + 1 < len(dates) else "2021-04-30" for index, day in enumerate(dates)}
    for r in pool:
        if r.get("pool_eligibility") != "eligible_for_predecessor_pool" or (sleeves and r.get("sleeve_id") not in sleeves):
            continue
        for year in range(int(r["rebalance_date"][:4]), int(next_date[r["rebalance_date"]][:4]) + 1):
            key = (r["code"], year)
            entry = rows.setdefault(key, {"code": r["code"], "year": year, "sleeves": set(), "rebalance_dates": set()})
            entry["sleeves"].add(r["sleeve_id"]); entry["rebalance_dates"].add(r["rebalance_date"])
    return [{"code": v["code"], "local_code": jq_to_local(v["code"]), "year": v["year"], "sleeves": ";".join(sorted(v["sleeves"])), "rebalance_dates": ";".join(sorted(v["rebalance_dates"]))} for v in rows.values()]


def _extract(root: Path, db: Path, source_root: Path, needed: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = {}
    for item in needed: grouped.setdefault(item["year"], []).append(item)
    index_rows: list[dict[str, Any]] = []; audit: list[dict[str, Any]] = []
    created = _now(); destination = db / DATASET_REL / "by_year"
    for year, rows in sorted(grouped.items()):
        archive = source_root / f"{year}.zip"
        if not archive.exists():
            for item in rows: index_rows.append(_missing(item, "annual_zip_missing"))
            continue
        with zipfile.ZipFile(archive) as zf:
            names = set(zf.namelist())
            for item in rows:
                entry = f"{year}/{item['local_code']}.csv"; output = destination / str(year) / f"{item['code'].replace('.', '_')}_1min.csv"
                if entry not in names:
                    index_rows.append(_missing(item, "entry_missing_in_annual_zip")); continue
                raw = csv.reader(decode_bytes(zf.read(entry)).splitlines()); header = next(raw, [])
                clean, quality = clean_1min_rows(raw, item["code"], item["local_code"], year, created)
                if clean:
                    output.parent.mkdir(parents=True, exist_ok=True)
                    _write_csv(output, clean)
                row = {"code": item["code"], "local_code": item["local_code"], "year": year,
                       "path": str(output.relative_to(root)) if clean else "", "row_count": len(clean),
                       "stock_days": quality["stock_days"], "full_240_days": quality["full_240_days"],
                       "minute_count_modes": quality["minute_count_modes"], "source_rows": quality["source_rows"],
                       "dropped_parse_rows": quality["dropped_parse_rows"], "dropped_out_of_session_rows": quality["dropped_out_of_session_rows"],
                       "dropped_bad_ohlc_rows": quality["dropped_bad_ohlc_rows"], "dropped_bad_vol_amount_rows": quality["dropped_bad_vol_amount_rows"],
                       "duplicate_datetime_rows": quality["duplicate_datetime_rows"], "status": "pass" if clean else "empty_after_cleaning",
                       "notes": "v5j_dynamic_pit_pool_targeted_extract;header=" + ",".join(header[:7])}
                index_rows.append(row); audit.append({"code": item["code"], "year": year, "source_entry": entry, "status": row["status"], "cleaned_row_count": len(clean)})
    return index_rows, audit


def _merge_index(old: list[dict[str, str]], fresh: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged = {(r.get("code", ""), str(r.get("year", ""))): dict(r) for r in old}
    for r in fresh: merged[(r["code"], str(r["year"]))] = r
    return [merged[key] for key in sorted(merged)]


def _usable(row: dict[str, Any] | None) -> bool:
    return bool(row and row.get("path") and row.get("status") in {"pass", "existing_reused"})


def _missing(item: dict[str, Any], note: str) -> dict[str, Any]:
    return {**{k: "" for k in INDEX_COLUMNS}, "code": item["code"], "local_code": item["local_code"], "year": item["year"], "status": "missing_entry", "notes": note}


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists(): return []
    with path.open(encoding="utf-8-sig", newline="") as h: return list(csv.DictReader(h))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(k for row in rows for k in row)) or ["empty"]
    with path.open("w", encoding="utf-8-sig", newline="") as h:
        writer = csv.DictWriter(h, fields, extrasaction="ignore"); writer.writeheader(); writer.writerows(rows)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _now() -> str: return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _report(summary: dict[str, Any]) -> str:
    return "\n".join(["# V5j targeted one-minute source repair", "", f"- Requested code-years: `{summary['requested_code_year_count']}`.", f"- New cleaned files: `{summary['new_cleaned_file_count']}`.", f"- Remaining source gaps: `{summary['remaining_source_gap_count']}`.", "- No bars were substituted, no technical features were calculated, and no technical rule was evaluated.", ""])


if __name__ == "__main__": print(json.dumps(run_v5j_missing_1min_source_repair(), ensure_ascii=False, indent=2))
