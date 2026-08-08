from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5j_pre2019_pit_rebuild_data_gate") / "current"
DB = Path("数据库")
MINUTE_INDEX = DB / "processed" / "local_1min_clean_2013_2026" / "v5_required_1min_standardized_index.csv"
PRICE_DIR = DB / "processed" / "startup_preload_repaired_prices_v5"
PANEL_DIR = DB / "processed" / "startup_preload_repaired_panels_v5"
PRE_FACTOR_DIR = DB / "processed" / "pre2021_repaired_factor_panels_v5"
BANK_PDF_DIR = Path("v5c_bank_special_mention_pre2021_train_test") / "current" / "pdf"
INFRA_PDF_DIR = Path("v5c_infra_capex_original_statement_extraction") / "current" / "pdf"
YEARS = range(2013, 2019)
SLEEVES = {
    "bank": "bank_v3_startup_repaired_daily_prices.csv",
    "utilities_electricity": "utilities_v51f_startup_repaired_daily_prices.csv",
    "highway_infrastructure": "highway_v54h_startup_repaired_daily_prices.csv",
    "port_rail_infrastructure": "port_rail_v55j_startup_repaired_daily_prices.csv",
}


def run_v5j_pre2019_pit_rebuild_data_gate(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    minute = _minute_coverage(root)
    sleeve_rows = [_sleeve_row(root, sleeve, filename, minute) for sleeve, filename in SLEEVES.items()]
    gates = _gates(sleeve_rows, minute)
    queue = _queue(sleeve_rows)
    blockers = [row for row in sleeve_rows if row["p0_status"] != "ready"]
    summary = {
        "created_at_utc": _now(),
        "task": "v5j_pre2019_pit_rebuild_data_gate",
        "status": "completed_p0_inventory_blocked_for_rebuild",
        "target_validation_window": "2013-01-01_to_2021-04-30",
        "minute_data_available": bool(minute),
        "pre2019_repaired_daily_price_panel_available": False,
        "pre2019_full_multisleeve_pit_pool_available": False,
        "ready_sleeve_count": sum(row["p0_status"] == "ready" for row in sleeve_rows),
        "blocked_sleeve_count": sum(row["p0_status"] != "ready" for row in sleeve_rows),
        "accepted": False,
        "joinquant_started": False,
        "network_fetch_started": False,
    }
    _write_csv(out / "v5j_pre2019_minute_coverage.csv", minute)
    _write_csv(out / "v5j_pre2019_multisleeve_pit_inventory.csv", sleeve_rows)
    _write_csv(out / "v5j_pre2019_pit_rebuild_gates.csv", gates)
    _write_csv(out / "v5j_pre2019_pit_rebuild_blockers.csv", blockers)
    _write_csv(out / "v5j_pre2019_pit_rebuild_queue.csv", queue)
    _write_json(out / "v5j_pre2019_pit_rebuild_summary.json", summary)
    (out / "v5j_pre2019_pit_rebuild_report.md").write_text(_report(summary, sleeve_rows, minute), encoding="utf-8")
    return summary


def _minute_coverage(root: Path) -> list[dict[str, Any]]:
    if not (root / MINUTE_INDEX).exists():
        return []
    rows = _read_csv(root / MINUTE_INDEX)
    out = []
    for year in YEARS:
        group = [row for row in rows if row.get("year") == str(year)]
        out.append({
            "year": year,
            "indexed_code_count": len(group),
            "pass_code_count": sum(row.get("status") == "pass" for row in group),
            "total_rows": sum(int(row.get("row_count") or 0) for row in group),
            "full_240_days": sum(int(row.get("full_240_days") or 0) for row in group),
            "status": "pass" if group and any(row.get("status") == "pass" for row in group) else "fail",
            "note": "Execution-path source only; not a factor or universe source.",
        })
    return out


def _sleeve_row(root: Path, sleeve: str, price_file: str, minute: list[dict[str, Any]]) -> dict[str, Any]:
    price_path = root / PRICE_DIR / price_file
    price_min = _csv_min_date(price_path)
    panel_paths = list((root / PANEL_DIR).rglob("panel_with_low_vol.csv")) if (root / PANEL_DIR).exists() else []
    panel_for_sleeve = next((path for path in panel_paths if sleeve.split("_")[0] in str(path).lower() or (sleeve == "bank" and "bank" in str(path).lower())), None)
    panel_min = _csv_min_date(panel_for_sleeve) if panel_for_sleeve else ""
    bank_pdf_count = len(list((root / BANK_PDF_DIR).glob("*.pdf"))) if sleeve == "bank" and (root / BANK_PDF_DIR).exists() else 0
    infra_pdf_count = len(list((root / INFRA_PDF_DIR).glob("*.pdf"))) if sleeve in {"highway_infrastructure", "port_rail_infrastructure"} and (root / INFRA_PDF_DIR).exists() else 0
    evidence = "bank_multi_year_annual_reports_local" if bank_pdf_count else "infra_2018_focused_reports_local" if infra_pdf_count else "no_local_multi_year_statement_batch"
    missing = ["repaired_daily_price_2013_2018", "PIT_universe_membership_2013_2018", "factor_visible_dates_2013_2018"]
    if sleeve != "bank":
        missing.append("multi_year_financial_statement_evidence_2013_2018")
    return {
        "sleeve_id": sleeve,
        "minute_execution_source_2013_2018": all(row["status"] == "pass" for row in minute),
        "repaired_daily_price_source": str(price_path),
        "repaired_daily_price_first_date": price_min,
        "factor_panel_first_date": panel_min,
        "local_statement_evidence": evidence,
        "local_statement_pdf_count": bank_pdf_count or infra_pdf_count,
        "missing_required_components": ";".join(missing),
        "p0_status": "blocked",
        "reason": "A full V57f-equivalent historical sleeve requires PIT price, universe, factor and statement evidence; current repaired panel starts in 2019.",
    }


def _gates(rows: list[dict[str, Any]], minute: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"gate_id": "P0_MINUTE", "status": "pass" if minute and all(row["status"] == "pass" for row in minute) else "fail", "detail": "2013-2018 local 1-minute coverage exists for the stored V5 universe."},
        {"gate_id": "P0_DAILY_PRICE", "status": "blocked", "detail": "Startup repaired daily price panels start in 2019, not 2013."},
        {"gate_id": "P0_PIT_UNIVERSE", "status": "blocked", "detail": "No historical 2013-2018 multi-sleeve membership snapshot is currently stored."},
        {"gate_id": "P0_PIT_FACTORS", "status": "blocked", "detail": "No factor-visible-date panels cover all four sleeves for 2013-2018."},
        {"gate_id": "P0_STATEMENTS", "status": "partial", "detail": "Bank has local multi-year reports; infrastructure evidence is focused on 2018 and utilities lacks a comparable local batch."},
    ]


def _queue(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"priority": 1, "task_id": "pre2019_daily_price_reconstruction", "status": "ready_local", "scope": "Aggregate only local 1-minute OHLCV to daily bars; retain raw, unadjusted provenance."},
        {"priority": 2, "task_id": "pre2019_pit_universe_reconstruction", "status": "blocked_by_source", "scope": "Build dated sector membership from archived official classification/evidence; no current-membership backfill."},
        {"priority": 3, "task_id": "pre2019_bank_pit_factor_extraction", "status": "ready_local_partial", "scope": "Extract visible-date financial fields from the local 2013-2018 bank annual reports."},
        {"priority": 4, "task_id": "pre2019_power_infra_pit_statement_collection", "status": "blocked_by_source", "scope": "Obtain annual/interim reports with publication dates for utilities, highway and port-rail before factor reconstruction."},
        {"priority": 5, "task_id": "pre2013_2021_v5f_technical_validation", "status": "blocked_until_p0", "scope": "Reconstruct targets and evaluate frozen V5h rule without parameter changes."},
    ]


def _csv_min_date(path: Path | None) -> str:
    if not path or not path.exists():
        return ""
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        dates = [str(row.get("date") or row.get("trade_date") or "")[:10] for _, row in zip(range(2000), reader)]
    return min((date for date in dates if date), default="")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    keys = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _report(summary: dict[str, Any], sleeves: list[dict[str, Any]], minute: list[dict[str, Any]]) -> str:
    return "\n".join([
        "# V5j Pre-2019 PIT Rebuild Data Gate",
        "",
        "- Target: a 2013-01-01 to 2021-04-30 independent V5f pool, before any technical execution validation.",
        f"- Minute data years passed: `{sum(row['status'] == 'pass' for row in minute)}/{len(minute)}`. This does not establish a valid stock pool.",
        f"- Repaired daily price panels currently begin in 2019; all `{len(sleeves)}` sleeves remain P0 blocked.",
        "- Bank has a local multi-year report batch; other sleeves need dated statement and historical-universe reconstruction.",
        "- No strategy, rule, weight, or JoinQuant test was changed or started.",
        "",
    ])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    print(json.dumps(run_v5j_pre2019_pit_rebuild_data_gate(), ensure_ascii=False, indent=2))
