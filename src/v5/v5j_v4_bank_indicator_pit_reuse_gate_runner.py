from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.local_1min_clean_ingest_runner import find_v5_database


OUT_DIR = Path("v5j_v4_bank_indicator_pit_reuse_gate") / "current"
POOL_REL = Path("processed") / "pre2021_repaired_multisleeve_pit_pool_v5" / "repaired_multisleeve_pit_pool.csv"
V4_ROOT = Path(r"D:\hh\codex\v4\phase_1_fundamental")
RAW_BANK_DIR = V4_ROOT / "raw_downloads" / "all_banks"
BACKFILL_DIR = V4_ROOT / "backfill_2013_joinquant"
FIELDS = (
    "Nonperforming_loan_rate",
    "non_performing_loan_provision_coverage",
    "core_level_capital_adequacy_ratio",
)


def run_v5j_v4_bank_indicator_pit_reuse_gate(root: Path = Path(".")) -> dict[str, Any]:
    """Audit V4's original bank-indicator records before any V5 reuse.

    This deliberately emits a sidecar panel.  It never changes the V57f
    configuration or silently substitutes a reconstructed accounting field.
    """
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    db = find_v5_database(root)
    pool = [
        row
        for row in _read_csv(db / POOL_REL)
        if row.get("pool_eligibility") == "eligible_for_predecessor_pool"
        and row.get("sleeve_id") == "bank"
    ]
    records, source_audit = _load_v4_records()
    selected = _select_visible_records(pool, records)
    coverage = _coverage(selected)
    blockers = _blockers(pool, source_audit, coverage)
    decision = _decision(blockers, coverage)

    _write_csv(out / "v5j_v4_bank_indicator_raw_source_audit.csv", source_audit)
    _write_csv(out / "v5j_v4_bank_indicator_pit_sidecar_panel.csv", selected)
    _write_csv(out / "v5j_v4_bank_indicator_coverage.csv", coverage)
    _write_csv(out / "v5j_v4_bank_indicator_blockers.csv", blockers)
    _write_csv(out / "v5j_v4_bank_indicator_pm_gate.csv", [decision])
    _write_json(
        out / "v5j_v4_bank_indicator_pit_reuse_summary.json",
        {
            "created_at_utc": _now(),
            "task": "v5j_v4_bank_indicator_pit_reuse_gate",
            "pool_observation_count": len(pool),
            "raw_record_count": len(records),
            "pit_visible_observation_count": sum(row["pit_status"] == "pass" for row in selected),
            "pm_gate_decision": decision["pm_gate_decision"],
            "sidecar_only": True,
            "v57f_core_modified": False,
            "accepted": False,
            "network_fetch_started": False,
        },
    )
    (out / "v5j_v4_bank_indicator_pit_reuse_report.md").write_text(
        _report(pool, records, coverage, decision), encoding="utf-8"
    )
    return _read_json(out / "v5j_v4_bank_indicator_pit_reuse_summary.json")


def _load_v4_records() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    sources = [(RAW_BANK_DIR, "v4_original_bank_indicator"), (BACKFILL_DIR, "v4_2013_bank_indicator_backfill")]
    seen: set[tuple[str, str, str]] = set()
    for directory, source_type in sources:
        if not directory.exists():
            audit.append({"source": str(directory), "status": "missing", "record_count": 0})
            continue
        files = sorted(directory.rglob("*bank_indicator*.csv"))
        count = 0
        for path in files:
            for row in _read_csv(path):
                code = str(row.get("code") or "")
                pub_date = str(row.get("pubDate") or "")[:10]
                stat_date = str(row.get("statDate") or "")[:10]
                if not code or not pub_date or not stat_date:
                    continue
                key = (code, pub_date, stat_date)
                if key in seen:
                    continue
                seen.add(key)
                records.append(
                    {
                        "code": code,
                        "pub_date": pub_date,
                        "stat_date": stat_date,
                        "Nonperforming_loan_rate": row.get("Nonperforming_loan_rate", ""),
                        "non_performing_loan_provision_coverage": row.get("non_performing_loan_provision_coverage", ""),
                        "core_level_capital_adequacy_ratio": row.get("core_level_capital_adequacy_ratio", ""),
                        "source_type": source_type,
                        "source_path": str(path),
                    }
                )
                count += 1
        audit.append({"source": str(directory), "status": "pass", "record_count": count, "file_count": len(files)})
    return sorted(records, key=lambda row: (row["code"], row["pub_date"], row["stat_date"])), audit


def _select_visible_records(pool: list[dict[str, str]], records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_code: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        by_code[row["code"]].append(row)
    for rows in by_code.values():
        rows.sort(key=lambda row: (row["pub_date"], row["stat_date"]))
    result: list[dict[str, Any]] = []
    for item in pool:
        visible = [row for row in by_code.get(item["code"], []) if row["pub_date"] <= item["rebalance_date"]]
        record = visible[-1] if visible else None
        required_present = bool(record) and all(str(record.get(field) or "") != "" for field in FIELDS)
        result.append(
            {
                "rebalance_date": item["rebalance_date"],
                "code": item["code"],
                "sleeve_id": "bank",
                "statement_pub_date": record["pub_date"] if record else "",
                "statement_period": record["stat_date"] if record else "",
                **{field: record.get(field, "") if record else "" for field in FIELDS},
                "future_record_used": False,
                "source_type": record["source_type"] if record else "",
                "pit_status": "pass" if required_present else "missing_visible_required_bank_fields",
                "sidecar_only": True,
                "accepted": False,
            }
        )
    return result


def _coverage(selected: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in selected:
        by_date[row["rebalance_date"]].append(row)
    rows = []
    for date, group in sorted(by_date.items()):
        passed = sum(row["pit_status"] == "pass" for row in group)
        rows.append(
            {
                "rebalance_date": date,
                "bank_pool_observation_count": len(group),
                "pit_visible_required_field_count": passed,
                "coverage_pct": round(100 * passed / len(group), 4) if group else 0.0,
                "status": "pass" if passed == len(group) else "partial",
            }
        )
    return rows


def _blockers(pool: list[dict[str, str]], audit: list[dict[str, Any]], coverage: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blockers = []
    if not pool:
        blockers.append({"blocker_id": "bank_pool_missing", "severity": "fatal", "detail": "No eligible historical bank observations."})
    if not any(row.get("status") == "pass" for row in audit):
        blockers.append({"blocker_id": "v4_raw_bank_source_missing", "severity": "fatal", "detail": "No readable V4 bank indicator source."})
    partial = [row for row in coverage if row["status"] != "pass"]
    if partial:
        blockers.append({"blocker_id": "bank_indicator_visible_coverage_partial", "severity": "review", "detail": f"{len(partial)} rebalance dates have a missing bank field."})
    return blockers


def _decision(blockers: list[dict[str, Any]], coverage: list[dict[str, Any]]) -> dict[str, Any]:
    fatal = any(row["severity"] == "fatal" for row in blockers)
    complete = bool(coverage) and all(row["status"] == "pass" for row in coverage)
    return {
        "pm_gate_decision": "v4_bank_pit_sidecar_pass_ready_for_v5j_target_reconstruction" if complete and not fatal else "v4_bank_pit_sidecar_partial_keep_data_gate",
        "sidecar_only": True,
        "admit_target_reconstruction_dependency": complete and not fatal,
        "admit_strategy_backtest": False,
        "accepted": False,
        "v57f_core_modified": False,
    }


def _report(pool: list[dict[str, str]], records: list[dict[str, Any]], coverage: list[dict[str, Any]], decision: dict[str, Any]) -> str:
    passed = sum(row["pit_visible_required_field_count"] for row in coverage)
    total = sum(row["bank_pool_observation_count"] for row in coverage)
    return "\n".join(
        [
            "# V4 Bank Indicator PIT Reuse Gate",
            "",
            f"- Historical bank pool observations: `{len(pool)}`.",
            f"- Original V4 records audited: `{len(records)}`.",
            f"- PIT-visible required-field coverage: `{passed}/{total}`.",
            f"- PM gate: `{decision['pm_gate_decision']}`.",
            "- The output is a sidecar with original `pubDate` provenance only; it does not modify V57f or run a strategy backtest.",
            "",
        ]
    )


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row)) or ["empty"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    print(json.dumps(run_v5j_v4_bank_indicator_pit_reuse_gate(), ensure_ascii=False, indent=2))
