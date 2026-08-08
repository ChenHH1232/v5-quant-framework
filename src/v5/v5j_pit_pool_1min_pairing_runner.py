from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5j_pit_pool_1min_pairing") / "current"
POOL = Path("数据库") / "processed" / "pre2021_repaired_multisleeve_pit_pool_v5" / "repaired_multisleeve_pit_pool.csv"
CALENDAR = Path("数据库") / "processed" / "pre2021_repaired_multisleeve_pit_pool_v5" / "quarterly_rebalance_calendar.csv"
MINUTE_INDEX = Path("数据库") / "processed" / "local_1min_clean_2013_2026" / "v5_required_1min_standardized_index.csv"
WINDOW_END = "2021-04-30"
TERMINAL_EVENTS = Path("v5j_local_adjust_factor_corporate_action") / "current" / "v5j_corporate_action_terminal_events.csv"


def run_v5j_pit_pool_1min_pairing(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    pool = _read_csv(root / POOL)
    calendar = _read_csv(root / CALENDAR)
    minute = _read_csv(root / MINUTE_INDEX)
    terminal_events = _read_csv(root / TERMINAL_EVENTS)
    events, coverage, source_audit = _pair(pool, calendar, minute, terminal_events)
    gap_queue = _gap_queue(events)
    pit_audit = _pit_audit(events)
    blockers = _blockers(events)
    decision = _decision(events, blockers)
    _write_csv(out / "v5j_pit_pool_1min_event_manifest.csv", events)
    _write_csv(out / "v5j_pit_pool_1min_coverage_by_sleeve_period.csv", coverage)
    _write_csv(out / "v5j_pit_pool_1min_source_audit.csv", source_audit)
    _write_csv(out / "v5j_pit_pool_1min_missing_source_queue.csv", gap_queue)
    _write_csv(out / "v5j_pit_pool_1min_pit_governance_audit.csv", pit_audit)
    _write_csv(out / "v5j_pit_pool_1min_blockers.csv", blockers)
    _write_csv(out / "v5j_pit_pool_1min_pm_gate.csv", [decision])
    _write_csv(out / "v5j_pit_pool_1min_next_queue.csv", _queue(decision["pm_gate_decision"]))
    summary = {
        "created_at_utc": _now(),
        "task": "v5j_pit_pool_1min_pairing",
        "status": decision["status"],
        "event_count": len(events),
        "complete_1min_source_event_count": sum(_paired(row) for row in events),
        "incomplete_1min_source_event_count": sum(not _paired(row) for row in events),
        "raw_bars_copied": False,
        "technical_features_computed": False,
        "technical_rule_validation_started": False,
        "accepted": False,
        "pm_gate_decision": decision["pm_gate_decision"],
    }
    _write_json(out / "v5j_pit_pool_1min_summary.json", summary)
    (out / "v5j_pit_pool_1min_report.md").write_text(_report(summary, blockers), encoding="utf-8")
    (out / "v5j_pit_pool_1min_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")
    return summary


def _pair(pool: list[dict[str, str]], calendar: list[dict[str, str]], minute: list[dict[str, str]], terminal_events: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    dates = sorted(row["rebalance_date"] for row in calendar)
    next_date = {day: dates[index + 1] if index + 1 < len(dates) else WINDOW_END for index, day in enumerate(dates)}
    index = {(row["code"], int(row["year"])): row for row in minute if row.get("year", "").isdigit()}
    events: list[dict[str, Any]] = []
    used_sources: dict[tuple[str, int], dict[str, str]] = {}
    terminal_by_event = {row.get("event_id", ""): row for row in terminal_events}
    for row in pool:
        if row.get("pool_eligibility") != "eligible_for_predecessor_pool":
            continue
        start = row["rebalance_date"]
        end = next_date.get(start, WINDOW_END)
        yearly = []
        for year in _years_inclusive(start, end):
            source = index.get((row["code"], year))
            if source:
                used_sources[(row["code"], year)] = source
                yearly.append(source)
        requested_years = _years_inclusive(start, end)
        paired = len(yearly) == len(requested_years)
        # A dynamic PIT member can legitimately list part-way through a calendar year.
        # Annual 240-day completeness is therefore a later bar-quality audit, not a reason
        # to reject an otherwise cleaned annual source file at this source-pairing stage.
        clean = paired and all(source.get("status") in {"pass", "existing_reused"} and source.get("path") for source in yearly)
        missing_years = [year for year in requested_years if (row["code"], year) not in index]
        partial_years = [source["year"] for source in yearly if source.get("status") != "pass" or _int(source.get("stock_days")) != _int(source.get("full_240_days"))]
        event_id = f"{start}|{row['code']}|{row['sleeve_id']}"
        terminal = terminal_by_event.get(event_id)
        terminal_override = bool(terminal and not clean and str(terminal.get("last_observed_daily_trade_date", "")) >= start)
        events.append({
            "event_id": event_id,
            "rebalance_date": start,
            "period_end_exclusive": end,
            "code": row["code"],
            "sleeve_id": row["sleeve_id"],
            "pool_pit_status": row.get("industry_visibility_status"),
            "minute_source_years": ";".join(str(source["year"]) for source in yearly),
            "minute_source_paths": ";".join(str(source["path"]) for source in yearly),
            "minute_year_file_count": len(yearly),
            "minute_pairing_status": "pass" if clean else ("pass_terminal_corporate_action_no_postexit_bars_expected" if terminal_override else "missing_or_partial_annual_1min_source"),
            "minute_pairing_reason": "" if clean else ("terminal_nontradable_after:" + str(terminal.get("last_observed_daily_trade_date", "")) if terminal_override else ("missing_year_file:" + ";".join(map(str, missing_years)) if missing_years else "partial_year_file:" + ";".join(map(str, partial_years)))),
            "terminal_corporate_action_status": terminal.get("terminal_status", "") if terminal else "",
            "source_frequency": "1min",
            "source_adjustment": "unadjusted",
            "entry_bar_earliest": f"{start} 09:31:00",
            "signal_visibility_rule": "A signal at timestamp T may use completed bars with timestamp <= T only.",
            "future_bar_allowed": False,
            "technical_feature_precomputed": False,
            "raw_bar_copy_created": False,
        })
    coverage = []
    for sleeve in sorted({row["sleeve_id"] for row in events}):
        for day in dates:
            rows = [row for row in events if row["sleeve_id"] == sleeve and row["rebalance_date"] == day]
            coverage.append({
                "rebalance_date": day,
                "sleeve_id": sleeve,
                "pit_pool_event_count": len(rows),
                "paired_1min_event_count": sum(_paired(row) for row in rows),
                "coverage_ratio": round(sum(_paired(row) for row in rows) / len(rows), 6) if rows else 0.0,
                "status": "pass" if rows and all(_paired(row) for row in rows) else "partial_or_empty",
            })
    source_audit = [{
        "code": source["code"],
        "year": source["year"],
        "path": source["path"],
        "stock_days": source.get("stock_days"),
        "full_240_days": source.get("full_240_days"),
        "cleaning_status": source.get("status"),
        "source_used_by_event_count": sum(source["code"] == event["code"] and str(source["year"]) in event["minute_source_years"].split(";") for event in events),
    } for source in used_sources.values()]
    return events, coverage, source_audit


def _gap_queue(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], int] = {}
    for row in events:
        if _paired(row):
            continue
        key = (row["code"], row["sleeve_id"], row["minute_pairing_reason"])
        grouped[key] = grouped.get(key, 0) + 1
    return [{
        "code": code,
        "sleeve_id": sleeve,
        "minute_pairing_reason": reason,
        "affected_rebalance_event_count": count,
        "allowed_resolution": "ingest_same_raw_1min_source_then_run_cleaning_and_pairing; do_not_substitute_5min_or_drop_member",
        "status": "needs_1min_source",
    } for (code, sleeve, reason), count in sorted(grouped.items())]


def _pit_audit(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{
        "event_id": row["event_id"],
        "pool_pit_source_linked": row.get("pool_pit_status") == "pass_historical_snapshot",
        "uses_future_bar": row.get("future_bar_allowed") is False,
        "entry_before_first_visible_bar": row.get("entry_bar_earliest") == f"{row['rebalance_date']} 09:31:00",
        "technical_feature_precomputed": row.get("technical_feature_precomputed"),
        "status": "pass" if _paired(row) else "source_gap",
    } for row in events]


def _blockers(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    missing = sum(not _paired(row) for row in events)
    rows = [{
        "blocker_id": "pit_dividend_corporate_action_ledger_pending",
        "severity": "blocks_total_return_target_validation",
        "detail": "The paired minute data does not repair the raw-price total-return gate.",
    }, {
        "blocker_id": "statement_quality_factor_panel_pending",
        "severity": "blocks_full_v57f_equivalent_targets",
        "detail": "Minute pairing cannot replace report-visible-date OCF, payout and quality fields.",
    }]
    if missing:
        rows.append({"blocker_id": "partial_minute_source_coverage", "severity": "blocks_events_with_missing_source", "detail": f"{missing} PIT-pool events have no complete annual cleaned one-minute source."})
    return rows


def _decision(events: list[dict[str, Any]], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    missing = sum(not _paired(row) for row in events)
    return {
        "status": "pit_pool_1min_paired_no_technical_validation_started" if not missing else "pit_pool_1min_partially_paired",
        "pm_gate_decision": "admit_1min_event_index_to_frozen_rule_data_readiness_only" if not missing else "retain_partial_1min_data_gate",
        "technical_rule_validation_allowed": False,
        "reason": "One-minute source links are data readiness only; total return and statement factor gates remain open.",
    }


def _queue(decision: str) -> list[dict[str, Any]]:
    return [
        {"priority": 1, "task_id": "v5j_pit_dividend_corporate_action_ledger", "status": "ready", "reason": "Complete total-return input before target construction."},
        {"priority": 2, "task_id": "v5j_statement_visible_date_factor_panel", "status": "ready", "reason": "Complete financial quality fields before target construction."},
        {"priority": 3, "task_id": "v5j_frozen_technical_rule_independent_validation", "status": "blocked", "reason": "Do not read the paired bars for rule evaluation until P1/P2 pass."},
    ]


def _years_inclusive(start: str, end: str) -> list[int]:
    return list(range(int(start[:4]), int(end[:4]) + 1))


def _paired(row: dict[str, Any]) -> bool:
    return str(row.get("minute_pairing_status", "")) in {"pass", "pass_terminal_corporate_action_no_postexit_bars_expected"}


def _int(value: Any) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _report(summary: dict[str, Any], blockers: list[dict[str, Any]]) -> str:
    lines = [
        "# V5j PIT Pool One-minute Pairing",
        "",
        "- Each eligible historical PIT-pool member is linked to its cleaned, unadjusted one-minute source file by code and holding period.",
        "- Raw bars are not duplicated and no technical feature is precomputed.",
        "- The pairing is not a technical rule test.",
        f"- PM gate: `{summary['pm_gate_decision']}`.",
        "",
        "## Remaining blockers",
        "",
    ]
    lines.extend(f"- `{row['blocker_id']}`: {row['detail']}" for row in blockers)
    return "\n".join(lines) + "\n"


def _rules() -> str:
    return "\n".join([
        "# One-minute Pairing Rules",
        "",
        "1. A PIT pool event may only access the listed cleaned one-minute source path for its own code and holding period.",
        "2. A signal at time T may use only completed bars through T; forward bars are evaluation-only and cannot enter the signal.",
        "3. No feature, order, portfolio return, technical rule, or target weight is produced by this pairing task.",
        "4. Do not begin cross-period technical validation until PIT dividend/corporate-action and statement-factor gates pass.",
        "",
    ])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    print(json.dumps(run_v5j_pit_pool_1min_pairing(), ensure_ascii=False, indent=2))
