from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


BACKTEST_END = "2026-05-31"
FORWARD_START = "2026-06-01"
ONE_MIN_DATASET = "local_1min_clean_2013_2026"
MICRO_GATE_DIR = Path("v5f_1min_microstructure_signal_quality_gate") / "current"
MICRO_SUMMARY = MICRO_GATE_DIR / "v5f_1min_microstructure_summary.json"
EVENT_DIAGNOSTICS = MICRO_GATE_DIR / "v5f_1min_event_path_diagnostics.csv"
EVENT_SUMMARY = MICRO_GATE_DIR / "v5f_1min_event_type_quality_summary.csv"
VWAP_DIAGNOSTICS = MICRO_GATE_DIR / "v5f_1min_vwap_precision_diagnostics.csv"
QUALITY_RECOMMENDATION = MICRO_GATE_DIR / "v5f_1min_quality_filter_recommendation.csv"

VWAP_OUT = Path("v5f_1min_vwap_execution_precision_audit") / "current"
FILTER_SPEC_OUT = Path("v5f_spike_mr_signal_quality_filter_spec") / "current"
FORWARD_OUT = Path("v5f_1min_forward_observation_append") / "current"
COMBINED_OUT = Path("v5f_1min_queue_123_execution") / "current"

LATE_VWAP_EVENTS = {"late_day_vwap_dislocation", "late_day_vwap_premium"}
EARLY_SPIKE_EVENTS = {"morning_30m_micro_crash", "morning_60m_micro_crash", "morning_30m_micro_spike"}
CRASH_EVENTS = {"morning_30m_micro_crash", "morning_60m_micro_crash", "late_day_vwap_dislocation"}
SPIKE_EVENTS = {"morning_30m_micro_spike", "late_day_vwap_premium"}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5f_1min_queue_123(root: Path = Path(".")) -> dict[str, Any]:
    blockers = _missing_inputs(root)
    if blockers:
        return _write_blocked(root, blockers)

    db = _find_v5_database(root)
    micro_summary = _read_json(root / MICRO_SUMMARY)
    event_rows = _read_csv(root / EVENT_DIAGNOSTICS)
    event_summary = _read_csv(root / EVENT_SUMMARY)
    vwap_diag = _read_csv(root / VWAP_DIAGNOSTICS)
    quality_recommendations = _read_csv(root / QUALITY_RECOMMENDATION)

    vwap_summary = _run_vwap_audit(root, micro_summary, event_rows, vwap_diag)
    filter_summary = _run_filter_spec(root, event_summary, quality_recommendations)
    forward_summary = _run_forward_append(root, db)
    combined_summary = _combined_summary(vwap_summary, filter_summary, forward_summary)
    _write_combined(root, combined_summary, [vwap_summary, filter_summary, forward_summary])
    return combined_summary


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    missing = []
    try:
        db = _find_v5_database(root)
    except FileNotFoundError as exc:
        missing.append(_blocker("v5_database_missing", str(exc)))
        db = None
    for path in [MICRO_SUMMARY, EVENT_DIAGNOSTICS, EVENT_SUMMARY, VWAP_DIAGNOSTICS, QUALITY_RECOMMENDATION]:
        if not (root / path).exists():
            missing.append(_blocker(f"missing_{path.name}", str(path)))
    if db is not None:
        one_min_dir = db / "processed" / ONE_MIN_DATASET / "by_year" / "2026"
        if not one_min_dir.exists():
            missing.append(_blocker("missing_2026_1min_clean_dir", str(one_min_dir)))
    return missing


def _run_vwap_audit(
    root: Path,
    micro_summary: dict[str, Any],
    event_rows: list[dict[str, Any]],
    vwap_diag: list[dict[str, Any]],
) -> dict[str, Any]:
    out = root / VWAP_OUT
    out.mkdir(parents=True, exist_ok=True)
    vwap_events = [row for row in event_rows if row.get("event_type") in LATE_VWAP_EVENTS]
    flip_cases = [
        row
        for row in vwap_events
        if str(row.get("confirmed_by_1min", "")).lower() != "true"
        or abs(_float(row.get("vwap_deviation_abs_diff"))) >= 0.002
    ]
    by_year = _group_vwap_precision(vwap_events, "year")
    by_sleeve = _group_vwap_precision(vwap_events, "sleeve")
    execution = _group_execution_path(vwap_events)
    governance = _shared_governance(extra=[
        ("vwap_used_for_precision_only", "pass", "VWAP is audited with 1min observation-time bars only; no trade rule changed."),
        ("late_day_only", "pass", "Only late-day VWAP dislocation/premium events are included in this audit."),
    ])
    decision = [
        {
            "pm_gate_decision": "vwap_execution_precision_audit_pass_use_1min_for_audit_not_trading",
            "status": "pass",
            "accepted": False,
            "live_trading_approved": False,
            "trading_frequency_increased": False,
            "v57f_core_modified": False,
            "v5f_mainline_modified": False,
            "notes": "Future VWAP diagnostics should prefer 1min observation-time VWAP. This does not approve trading changes.",
        }
    ]
    next_queue = [
        {
            "queue_id": "v5f_forward_vwap_observation_time_metric",
            "status": "ready",
            "scope": "Use 1min observation-time VWAP in future forward/paper diagnostics.",
        },
        {
            "queue_id": "v5f_vwap_flip_case_manual_review",
            "status": "ready_if_needed",
            "scope": "Review flip cases where 5min VWAP and 1min VWAP classification differ.",
        },
    ]
    blockers = [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": ""}]
    summary = {
        "created_at_utc": now_utc(),
        "task": "v5f_1min_vwap_execution_precision_audit",
        "status": "completed_vwap_execution_precision_audit",
        "pm_gate_decision": decision[0]["pm_gate_decision"],
        "source_micro_gate_status": micro_summary.get("status", ""),
        "vwap_event_count": len(vwap_events),
        "vwap_flip_or_review_case_count": len(flip_cases),
        "avg_abs_vwap_deviation_diff": _mean([row.get("vwap_deviation_abs_diff") for row in vwap_events]),
        "max_abs_vwap_deviation_diff": _max([abs(_float(row.get("vwap_deviation_abs_diff"))) for row in vwap_events]),
        "confirmed_by_1min_rate_pct": _pct(
            sum(1 for row in vwap_events if str(row.get("confirmed_by_1min", "")).lower() == "true"),
            len(vwap_events),
        ),
        "accepted": False,
        "live_trading_approved": False,
        "trading_frequency_increased": False,
        "v57f_core_modified": False,
        "v5f_mainline_modified": False,
        "threshold_scan_used": False,
        "new_buy_signal_used": False,
        "fatal_blocker_count": 0,
    }
    _write_json(out / "v5f_1min_vwap_precision_summary.json", summary)
    _write_csv(out / "v5f_1min_vwap_event_precision_audit.csv", vwap_events)
    _write_csv(out / "v5f_1min_vwap_flip_cases.csv", flip_cases)
    _write_csv(out / "v5f_1min_vwap_precision_by_year.csv", by_year)
    _write_csv(out / "v5f_1min_vwap_precision_by_sleeve.csv", by_sleeve)
    _write_csv(out / "v5f_1min_vwap_execution_path_audit.csv", execution)
    _write_csv(out / "v5f_1min_vwap_source_diagnostics.csv", vwap_diag)
    _write_csv(out / "v5f_1min_vwap_governance_audit.csv", governance)
    _write_csv(out / "v5f_1min_vwap_pm_gate_decision.csv", decision)
    _write_csv(out / "v5f_1min_vwap_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5f_1min_vwap_blockers.csv", blockers)
    (out / "v5f_1min_vwap_execution_precision_report.md").write_text(
        _vwap_report(summary, vwap_diag, by_sleeve, decision),
        encoding="utf-8",
    )
    (out / "v5f_1min_vwap_agent_execution_rules.md").write_text(_rules("VWAP precision audit"), encoding="utf-8")
    return summary


def _run_filter_spec(
    root: Path,
    event_summary: list[dict[str, Any]],
    quality_recommendations: list[dict[str, Any]],
) -> dict[str, Any]:
    out = root / FILTER_SPEC_OUT
    out.mkdir(parents=True, exist_ok=True)
    quality_matrix = []
    for row in event_summary:
        event_type = row.get("event_type", "")
        confirmation = _float(row.get("confirmed_by_1min_rate_pct"))
        dominated = _float(row.get("single_minute_dominated_rate_pct"))
        if event_type in LATE_VWAP_EVENTS and confirmation >= 95.0 and dominated < 10.0:
            status = "quality_pass_audit_only"
        elif event_type in EARLY_SPIKE_EVENTS:
            status = "diagnostic_noise_filter_required"
        else:
            status = "diagnostic_only"
        quality_matrix.append({**row, "quality_gate_status": status, "allowed_use": "diagnostic_or_forward_observation_only"})

    noise_schema = [
        {
            "flag_id": "one_min_confirmation_fail",
            "definition": "Registered 5min event is not confirmed when recomputed from cleaned 1min bars.",
            "default_action": "exclude_from_promotion_evidence; keep for diagnostics",
            "trading_rule_allowed": False,
        },
        {
            "flag_id": "single_minute_dominated",
            "definition": "Largest single 1min return explains at least 60% of the event-window move.",
            "default_action": "flag as microstructure/noise sensitive; no automatic trade change",
            "trading_rule_allowed": False,
        },
        {
            "flag_id": "low_direction_consistency",
            "definition": "Only a weak majority of 1min bars move in the event direction.",
            "default_action": "downweight evidence in PM review; no optimized threshold",
            "trading_rule_allowed": False,
        },
        {
            "flag_id": "vwap_confirmation_flip",
            "definition": "Late-day VWAP event changes classification under 1min observation-time VWAP.",
            "default_action": "manual audit / forward observation only",
            "trading_rule_allowed": False,
        },
    ]
    spec = [
        {
            "spec_id": "allowed_scope",
            "rule": "Use quality flags to judge whether historical short-window events are reliable evidence.",
            "allowed": True,
        },
        {
            "spec_id": "blocked_scope",
            "rule": "Do not use quality flags as new buy/sell triggers, optimized thresholds, or higher-frequency rebalancing.",
            "allowed": False,
        },
        {
            "spec_id": "promotion_boundary",
            "rule": "Early spike/crash mechanisms cannot be promoted unless pre-2021 or future forward samples pass the same fixed quality flags.",
            "allowed": True,
        },
    ]
    action_boundary = [
        {"action": "audit_evidence_quality", "status": "allowed"},
        {"action": "forward_observation_tagging", "status": "allowed"},
        {"action": "change_position_size_from_1min_flag", "status": "blocked"},
        {"action": "increase_trading_frequency", "status": "blocked"},
        {"action": "optimize_1min_noise_threshold", "status": "blocked"},
        {"action": "mark_accepted_or_live_approved", "status": "blocked"},
    ]
    governance = _shared_governance(extra=[
        ("spec_only", "pass", "This task produces rule boundaries only and does not run portfolio backtest."),
        ("no_parameter_scan", "pass", "Noise flags are fixed diagnostic labels, not optimized model parameters."),
    ])
    decision = [
        {
            "pm_gate_decision": "signal_quality_filter_spec_ready_for_forward_observation_not_trading",
            "status": "spec_only",
            "accepted": False,
            "live_trading_approved": False,
            "trading_frequency_increased": False,
            "v57f_core_modified": False,
            "v5f_mainline_modified": False,
            "notes": "Use 1min quality flags to separate robust evidence from noisy events. No direct trading rule is admitted.",
        }
    ]
    next_queue = [
        {
            "queue_id": "v5f_spike_mr_quality_filtered_forward_observation",
            "status": "ready",
            "scope": "Apply fixed quality flags to forward observation events only.",
        },
        {
            "queue_id": "pre2021_1min_quality_filter_independent_check",
            "status": "ready_after_pre2021_event_panel",
            "scope": "Apply same flags to pre-2021 independent event samples without retuning.",
        },
    ]
    blockers = [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": ""}]
    summary = {
        "created_at_utc": now_utc(),
        "task": "v5f_spike_mr_signal_quality_filter_spec",
        "status": "completed_signal_quality_filter_spec_only",
        "pm_gate_decision": decision[0]["pm_gate_decision"],
        "event_type_count": len(quality_matrix),
        "diagnostic_noise_filter_required_count": sum(1 for row in quality_matrix if row["quality_gate_status"] == "diagnostic_noise_filter_required"),
        "quality_pass_audit_only_count": sum(1 for row in quality_matrix if row["quality_gate_status"] == "quality_pass_audit_only"),
        "accepted": False,
        "live_trading_approved": False,
        "trading_frequency_increased": False,
        "v57f_core_modified": False,
        "v5f_mainline_modified": False,
        "threshold_scan_used": False,
        "new_buy_signal_used": False,
        "portfolio_backtest_run": False,
        "fatal_blocker_count": 0,
    }
    _write_json(out / "v5f_spike_mr_signal_quality_filter_summary.json", summary)
    _write_csv(out / "v5f_spike_mr_signal_quality_filter_spec.csv", spec)
    _write_csv(out / "v5f_spike_mr_event_type_quality_matrix.csv", quality_matrix)
    _write_csv(out / "v5f_spike_mr_noise_flag_schema.csv", noise_schema)
    _write_csv(out / "v5f_spike_mr_quality_recommendation_source.csv", quality_recommendations)
    _write_csv(out / "v5f_spike_mr_action_boundary.csv", action_boundary)
    _write_csv(out / "v5f_spike_mr_governance_audit.csv", governance)
    _write_csv(out / "v5f_spike_mr_pm_gate_decision.csv", decision)
    _write_csv(out / "v5f_spike_mr_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5f_spike_mr_blockers.csv", blockers)
    (out / "v5f_spike_mr_signal_quality_filter_report.md").write_text(
        _filter_report(summary, quality_matrix, action_boundary, decision),
        encoding="utf-8",
    )
    (out / "v5f_spike_mr_agent_execution_rules.md").write_text(_rules("signal quality filter spec"), encoding="utf-8")
    return summary


def _run_forward_append(root: Path, db: Path) -> dict[str, Any]:
    out = root / FORWARD_OUT
    out.mkdir(parents=True, exist_ok=True)
    universe = _read_universe(db)
    feature_rows, read_rows = _forward_feature_panel(db, universe)
    event_rows = _forward_events(feature_rows)
    by_type = _forward_breakdown(event_rows, ["event_type"])
    by_sleeve = _forward_breakdown(event_rows, ["event_type", "sleeve"])
    availability = _forward_availability(feature_rows, read_rows)
    governance = _shared_governance(extra=[
        ("forward_only_after_backtest_end", "pass", f"All observations are dated >= {FORWARD_START}; no backtest window is extended."),
        ("unofficial_target_status", "pass", "No official V57f rebalance signal is assumed; rows are observation-only over the V5 relevant universe."),
    ])
    decision = [
        {
            "pm_gate_decision": "forward_observation_append_completed_observation_only",
            "status": "observation_only",
            "accepted": False,
            "live_trading_approved": False,
            "trading_frequency_increased": False,
            "v57f_core_modified": False,
            "v5f_mainline_modified": False,
            "notes": "Forward rows after 2026-05-31 are appended only for observation; they are not model validation or trading instructions.",
        }
    ]
    next_queue = [
        {
            "queue_id": "append_next_local_1min_forward_batch",
            "status": "ready_when_new_local_data_arrives",
            "scope": "Append only post-2026-05-31 observations with same fixed event definitions.",
        },
        {
            "queue_id": "official_v57f_forward_target_join",
            "status": "pending_official_signal",
            "scope": "When official V57f target file exists, join observations to actual forward/paper holdings.",
        },
    ]
    blockers = [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": ""}]
    first_date = min((row["trade_date"] for row in feature_rows), default="")
    last_date = max((row["trade_date"] for row in feature_rows), default="")
    summary = {
        "created_at_utc": now_utc(),
        "task": "v5f_1min_forward_observation_append",
        "status": "completed_forward_observation_append",
        "pm_gate_decision": decision[0]["pm_gate_decision"],
        "forward_start": FORWARD_START,
        "forward_first_available_date": first_date,
        "forward_last_available_date": last_date,
        "forward_stock_day_count": len(feature_rows),
        "forward_event_count": len(event_rows),
        "forward_event_type_count": len(by_type),
        "universe_code_count": len(universe),
        "official_v57f_forward_targets_available": False,
        "observation_only": True,
        "accepted": False,
        "live_trading_approved": False,
        "trading_frequency_increased": False,
        "v57f_core_modified": False,
        "v5f_mainline_modified": False,
        "threshold_scan_used": False,
        "new_buy_signal_used": False,
        "fatal_blocker_count": 0,
    }
    _write_json(out / "v5f_1min_forward_observation_summary.json", summary)
    _write_csv(out / "v5f_1min_forward_data_availability.csv", availability)
    _write_csv(out / "v5f_1min_forward_file_read_audit.csv", read_rows)
    _write_csv(out / "v5f_1min_forward_observation_feature_panel.csv", feature_rows)
    _write_csv(out / "v5f_1min_forward_observation_event_log.csv", event_rows)
    _write_csv(out / "v5f_1min_forward_event_by_type.csv", by_type)
    _write_csv(out / "v5f_1min_forward_event_by_sleeve.csv", by_sleeve)
    _write_csv(out / "v5f_1min_forward_governance_audit.csv", governance)
    _write_csv(out / "v5f_1min_forward_pm_gate_decision.csv", decision)
    _write_csv(out / "v5f_1min_forward_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5f_1min_forward_blockers.csv", blockers)
    (out / "v5f_1min_forward_observation_report.md").write_text(
        _forward_report(summary, by_type, by_sleeve, decision),
        encoding="utf-8",
    )
    (out / "v5f_1min_forward_agent_execution_rules.md").write_text(_rules("forward observation append"), encoding="utf-8")
    return summary


def _read_universe(db: Path) -> list[dict[str, Any]]:
    path = db / "processed" / ONE_MIN_DATASET / "v5_required_1min_universe.csv"
    return _read_csv(path)


def _forward_feature_panel(db: Path, universe: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    read_rows: list[dict[str, Any]] = []
    for item in universe:
        code = str(item["code"])
        path = db / "processed" / ONE_MIN_DATASET / "by_year" / "2026" / f"{code.replace('.', '_')}_1min.csv"
        if not path.exists():
            read_rows.append({"code": code, "status": "missing", "path": str(path), "loaded_row_count": 0})
            continue
        day_rows = _load_forward_days(path)
        read_rows.append(
            {
                "code": code,
                "status": "pass",
                "path": str(path),
                "loaded_row_count": sum(len(group) for group in day_rows.values()),
                "loaded_trade_date_count": len(day_rows),
            }
        )
        prev_close: float | None = None
        for trade_date in sorted(day_rows):
            group = day_rows[trade_date]
            feature = _day_feature(group)
            if trade_date >= FORWARD_START:
                feature.update(
                    {
                        "code": code,
                        "local_code": item.get("local_code", ""),
                        "trade_date": trade_date,
                        "year": trade_date[:4],
                        "sleeve": item.get("sleeves", ""),
                        "sample_scope": "forward_observation_only",
                        "official_v57f_target": False,
                        "prev_day_close": prev_close,
                        "r_prevclose_1455": _ret(feature.get("close_1455"), prev_close),
                        "r_prevclose_close": _ret(feature.get("day_close"), prev_close),
                        "accepted": False,
                        "new_buy_signal_allowed": False,
                    }
                )
                rows.append(feature)
            prev_close = feature.get("day_close")
    return rows, read_rows


def _load_forward_days(path: Path) -> dict[str, list[dict[str, Any]]]:
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            trade_date = str(row.get("trade_date", ""))
            if trade_date < "2026-05-28":
                continue
            slim = {
                "trade_date": trade_date,
                "time": str(row.get("time", "")),
                "open": _float(row.get("open")),
                "high": _float(row.get("high")),
                "low": _float(row.get("low")),
                "close": _float(row.get("close")),
                "volume": _float(row.get("volume")),
                "amount": _float(row.get("amount")),
            }
            by_date[trade_date].append(slim)
    for trade_date in list(by_date):
        by_date[trade_date].sort(key=lambda row: row["time"])
    return by_date


def _day_feature(group: list[dict[str, Any]]) -> dict[str, Any]:
    by_time = {row["time"]: row for row in group}
    close_0935 = _time_close(by_time, "09:35:00")
    close_1000 = _time_close(by_time, "10:00:00")
    close_1030 = _time_close(by_time, "10:30:00")
    close_1455 = _time_close(by_time, "14:55:00")
    day_close = group[-1]["close"] if group else None
    day_low = min((row["low"] for row in group), default=None)
    day_high = max((row["high"] for row in group), default=None)
    upto_1455 = [row for row in group if row["time"] <= "14:55:00"]
    vwap_1455 = _vwap_from_rows(upto_1455)
    return {
        "one_min_bar_count": len(group),
        "first_bar_time": group[0]["time"] if group else "",
        "last_bar_time": group[-1]["time"] if group else "",
        "close_0935": close_0935,
        "close_1000": close_1000,
        "close_1030": close_1030,
        "close_1455": close_1455,
        "day_close": day_close,
        "day_low": day_low,
        "day_high": day_high,
        "vwap_1455_observation_1min": vwap_1455,
        "r_0935_1000": _ret(close_1000, close_0935),
        "r_0935_1030": _ret(close_1030, close_0935),
        "r_1455_vwap": _ret(close_1455, vwap_1455),
        "r_1000_close": _ret(day_close, close_1000),
        "r_1030_close": _ret(day_close, close_1030),
        "r_1455_close": _ret(day_close, close_1455),
    }


def _forward_events(feature_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events = []
    for row in feature_rows:
        event_defs = [
            ("morning_30m_micro_crash", row.get("r_0935_1000"), -0.01, "<=", "10:00:00"),
            ("morning_30m_micro_spike", row.get("r_0935_1000"), 0.01, ">=", "10:00:00"),
            ("morning_60m_micro_crash", row.get("r_0935_1030"), -0.015, "<=", "10:30:00"),
            ("late_day_vwap_dislocation", row.get("r_1455_vwap"), -0.005, "<=", "14:55:00"),
            ("late_day_vwap_premium", row.get("r_1455_vwap"), 0.005, ">=", "14:55:00"),
        ]
        for event_type, value, cutoff, op, obs_time in event_defs:
            if value is None:
                continue
            triggered = value <= cutoff if op == "<=" else value >= cutoff
            if not triggered:
                continue
            events.append(
                {
                    "event_id": f"forward|{event_type}|{row['code']}|{row['trade_date']}",
                    "event_type": event_type,
                    "code": row["code"],
                    "local_code": row.get("local_code", ""),
                    "trade_date": row["trade_date"],
                    "year": row["year"],
                    "sleeve": row.get("sleeve", ""),
                    "observation_time": obs_time,
                    "trigger_value": value,
                    "fixed_absolute_rule": f"{op} {cutoff}",
                    "sample_scope": "forward_observation_only",
                    "official_v57f_target": False,
                    "new_buy_signal_allowed": False,
                    "trading_frequency_increased": False,
                    "accepted": False,
                }
            )
    return events


def _forward_availability(feature_rows: list[dict[str, Any]], read_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dates = sorted({row["trade_date"] for row in feature_rows})
    return [
        {
            "availability_id": "forward_date_range",
            "status": "pass" if dates else "empty",
            "value": f"{dates[0]}..{dates[-1]}" if dates else "",
        },
        {
            "availability_id": "forward_stock_days",
            "status": "pass" if feature_rows else "empty",
            "value": len(feature_rows),
        },
        {
            "availability_id": "readable_2026_files",
            "status": "pass",
            "value": f"{sum(1 for row in read_rows if row['status'] == 'pass')}/{len(read_rows)}",
        },
        {
            "availability_id": "official_v57f_forward_target_join",
            "status": "pending",
            "value": "not_available_in_this_task",
        },
    ]


def _group_vwap_precision(rows: list[dict[str, Any]], column: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get(column, ""))].append(row)
    out = []
    for key, group in sorted(groups.items()):
        out.append(
            {
                column: key,
                "event_count": len(group),
                "confirmed_by_1min_rate_pct": _pct(sum(1 for row in group if str(row.get("confirmed_by_1min", "")).lower() == "true"), len(group)),
                "avg_abs_vwap_deviation_diff": _mean([row.get("vwap_deviation_abs_diff") for row in group]),
                "max_abs_vwap_deviation_diff": _max([abs(_float(row.get("vwap_deviation_abs_diff"))) for row in group]),
                "flip_or_review_case_count": sum(
                    1
                    for row in group
                    if str(row.get("confirmed_by_1min", "")).lower() != "true"
                    or abs(_float(row.get("vwap_deviation_abs_diff"))) >= 0.002
                ),
            }
        )
    return out


def _group_execution_path(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get("event_type", ""))].append(row)
    out = []
    for event_type, group in sorted(groups.items()):
        after = [_float(row.get("same_day_return_after_observation_1min")) for row in group]
        out.append(
            {
                "event_type": event_type,
                "event_count": len(group),
                "avg_same_day_return_after_observation": _mean(after),
                "median_same_day_return_after_observation": _median(after),
                "avg_mae_after_observation": _mean([row.get("mae_after_observation") for row in group]),
                "avg_mfe_after_observation": _mean([row.get("mfe_after_observation") for row in group]),
                "diagnostic_use_only": True,
            }
        )
    return out


def _forward_breakdown(rows: list[dict[str, Any]], cols: list[str]) -> list[dict[str, Any]]:
    groups: Counter[tuple[Any, ...]] = Counter(tuple(row.get(col, "") for col in cols) for row in rows)
    out = []
    for key, count in sorted(groups.items()):
        row = {col: key[index] for index, col in enumerate(cols)}
        row["event_count"] = count
        row["observation_only"] = True
        out.append(row)
    return out


def _shared_governance(*, extra: list[tuple[str, str, str]] | None = None) -> list[dict[str, Any]]:
    rows = [
        ("no_v57f_core_modified", "pass", "V57f core is not modified."),
        ("no_v5f_mainline_modified", "pass", "V5f mainline remains internal_subsleeve_mom12_70_30."),
        ("no_trading_frequency_increase", "pass", "1min data is not used to trade more frequently."),
        ("no_new_buy_signal", "pass", "No new stock buy signal is introduced."),
        ("no_accepted_or_live_approved", "pass", "No component is marked accepted or live approved."),
        ("backtest_end_preserved", "pass", f"Formal backtest still ends at {BACKTEST_END}."),
    ]
    rows.extend(extra or [])
    return [{"audit_id": key, "status": status, "detail": detail} for key, status, detail in rows]


def _combined_summary(vwap: dict[str, Any], filter_spec: dict[str, Any], forward: dict[str, Any]) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5f_1min_queue_123_execution",
        "status": "completed_v5f_1min_queue_123_execution",
        "queue_1_vwap_pm_gate_decision": vwap.get("pm_gate_decision"),
        "queue_2_filter_spec_pm_gate_decision": filter_spec.get("pm_gate_decision"),
        "queue_3_forward_append_pm_gate_decision": forward.get("pm_gate_decision"),
        "vwap_event_count": vwap.get("vwap_event_count", 0),
        "vwap_confirmed_by_1min_rate_pct": vwap.get("confirmed_by_1min_rate_pct", 0.0),
        "early_event_noise_filter_required_count": filter_spec.get("diagnostic_noise_filter_required_count", 0),
        "forward_stock_day_count": forward.get("forward_stock_day_count", 0),
        "forward_event_count": forward.get("forward_event_count", 0),
        "accepted": False,
        "live_trading_approved": False,
        "trading_frequency_increased": False,
        "v57f_core_modified": False,
        "v5f_mainline_modified": False,
        "threshold_scan_used": False,
        "new_buy_signal_used": False,
        "fatal_blocker_count": 0,
    }


def _write_combined(root: Path, summary: dict[str, Any], child_summaries: list[dict[str, Any]]) -> None:
    out = root / COMBINED_OUT
    out.mkdir(parents=True, exist_ok=True)
    _write_json(out / "v5f_1min_queue_123_summary.json", summary)
    _write_csv(
        out / "v5f_1min_queue_123_child_summary.csv",
        [
            {
                "task": child.get("task"),
                "status": child.get("status"),
                "pm_gate_decision": child.get("pm_gate_decision"),
                "accepted": child.get("accepted"),
                "trading_frequency_increased": child.get("trading_frequency_increased"),
            }
            for child in child_summaries
        ],
    )
    _write_csv(
        out / "v5f_1min_queue_123_pm_gate_decision.csv",
        [
            {
                "pm_gate_decision": "queue_123_completed_no_trading_frequency_change",
                "status": "completed",
                "accepted": False,
                "live_trading_approved": False,
                "trading_frequency_increased": False,
                "v57f_core_modified": False,
                "v5f_mainline_modified": False,
            }
        ],
    )
    (out / "v5f_1min_queue_123_report.md").write_text(
        "\n".join(
            [
                "# V5f 1min Queue 123 Execution",
                "",
                f"- VWAP event count: `{summary['vwap_event_count']}`",
                f"- VWAP 1min confirmation rate: `{summary['vwap_confirmed_by_1min_rate_pct']}%`",
                f"- Early event types needing noise filter: `{summary['early_event_noise_filter_required_count']}`",
                f"- Forward stock-days appended: `{summary['forward_stock_day_count']}`",
                f"- Forward observation events: `{summary['forward_event_count']}`",
                "",
                "All three queues are diagnostic/governance work only. No trading frequency, V57f core, or V5f mainline change is admitted.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_blocked(root: Path, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    out = root / COMBINED_OUT
    out.mkdir(parents=True, exist_ok=True)
    summary = {
        "created_at_utc": now_utc(),
        "task": "v5f_1min_queue_123_execution",
        "status": "blocked_missing_required_input",
        "pm_gate_decision": "blocked_by_missing_required_input",
        "fatal_blocker_count": len(blockers),
        "fatal_blockers": blockers,
        "accepted": False,
        "trading_frequency_increased": False,
    }
    _write_json(out / "v5f_1min_queue_123_summary.json", summary)
    _write_csv(out / "v5f_1min_queue_123_blockers.csv", blockers)
    return summary


def _vwap_report(summary: dict[str, Any], vwap_diag: list[dict[str, Any]], by_sleeve: list[dict[str, Any]], decision: list[dict[str, Any]]) -> str:
    lines = [
        "# V5f 1min VWAP Execution Precision Audit",
        "",
        f"- VWAP events: `{summary['vwap_event_count']}`",
        f"- 1min confirmed rate: `{summary['confirmed_by_1min_rate_pct']}%`",
        f"- Review cases: `{summary['vwap_flip_or_review_case_count']}`",
        f"- Avg abs VWAP deviation diff: `{summary['avg_abs_vwap_deviation_diff']}`",
        f"- Max abs VWAP deviation diff: `{summary['max_abs_vwap_deviation_diff']}`",
        "",
        "## Source Diagnostics",
    ]
    for row in vwap_diag:
        lines.append(
            f"- `{row.get('event_type')}`: confirmed `{row.get('confirmed_by_1min_rate_pct')}%`, flips `{row.get('confirmation_flip_count')}`, avg abs diff `{row.get('avg_abs_vwap_deviation_diff')}`."
        )
    lines.extend(["", "## By Sleeve"])
    for row in by_sleeve[:12]:
        lines.append(f"- `{row.get('sleeve')}`: events `{row.get('event_count')}`, confirmed `{row.get('confirmed_by_1min_rate_pct')}%`.")
    lines.extend(["", f"PM decision: `{decision[0]['pm_gate_decision']}`", ""])
    return "\n".join(lines)


def _filter_report(summary: dict[str, Any], matrix: list[dict[str, Any]], actions: list[dict[str, Any]], decision: list[dict[str, Any]]) -> str:
    lines = [
        "# V5f Spike/MR Signal Quality Filter Spec",
        "",
        f"- Event types reviewed: `{summary['event_type_count']}`",
        f"- Noise-filter-required event types: `{summary['diagnostic_noise_filter_required_count']}`",
        f"- Quality-pass audit-only event types: `{summary['quality_pass_audit_only_count']}`",
        "",
        "## Event Type Matrix",
    ]
    for row in matrix:
        lines.append(
            f"- `{row.get('event_type')}`: `{row.get('quality_gate_status')}`, confirmed `{row.get('confirmed_by_1min_rate_pct')}%`, dominated `{row.get('single_minute_dominated_rate_pct')}%`."
        )
    lines.extend(["", "## Action Boundary"])
    for row in actions:
        lines.append(f"- `{row['action']}`: `{row['status']}`")
    lines.extend(["", f"PM decision: `{decision[0]['pm_gate_decision']}`", ""])
    return "\n".join(lines)


def _forward_report(summary: dict[str, Any], by_type: list[dict[str, Any]], by_sleeve: list[dict[str, Any]], decision: list[dict[str, Any]]) -> str:
    lines = [
        "# V5f 1min Forward Observation Append",
        "",
        f"- Date range: `{summary['forward_first_available_date']}` to `{summary['forward_last_available_date']}`",
        f"- Stock-days: `{summary['forward_stock_day_count']}`",
        f"- Observation events: `{summary['forward_event_count']}`",
        "- Scope: observation-only after formal backtest end; no official V57f target assumed.",
        "",
        "## By Event Type",
    ]
    for row in by_type:
        lines.append(f"- `{row.get('event_type')}`: `{row.get('event_count')}`")
    lines.extend(["", "## By Sleeve"])
    for row in by_sleeve[:20]:
        lines.append(f"- `{row.get('event_type')}` / `{row.get('sleeve')}`: `{row.get('event_count')}`")
    lines.extend(["", f"PM decision: `{decision[0]['pm_gate_decision']}`", ""])
    return "\n".join(lines)


def _rules(title: str) -> str:
    return "\n".join(
        [
            f"# V5f 1min {title} Rules",
            "",
            "- Do not modify V57f core.",
            "- Do not modify V5f mainline.",
            "- Do not increase trading frequency.",
            "- Do not add buy signals, reentry, or cross-sleeve transfer.",
            "- Do not scan thresholds.",
            "- Do not mark accepted or live approved.",
            f"- Formal backtest still ends at {BACKTEST_END}.",
            "",
        ]
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def _find_v5_database(root: Path) -> Path:
    for child in root.iterdir():
        if child.is_dir() and (child / "processed").exists() and (child / "raw").exists() and (child / "manifests").exists():
            return child
    raise FileNotFoundError("Could not locate V5 database directory with processed/raw/manifests children.")


def _blocker(blocker_id: str, description: str) -> dict[str, Any]:
    return {"blocker_id": blocker_id, "severity": "fatal", "status": "blocking", "description": description}


def _float(value: Any) -> float:
    try:
        out = float(value)
        return out if math.isfinite(out) else 0.0
    except Exception:
        return 0.0


def _ret(end: float | None, start: float | None) -> float | None:
    if end is None or start in (None, 0.0):
        return None
    return end / start - 1.0


def _time_close(by_time: dict[str, dict[str, Any]], time_value: str) -> float | None:
    row = by_time.get(time_value)
    return None if row is None else row.get("close")


def _vwap_from_rows(rows: list[dict[str, Any]]) -> float | None:
    total_volume = sum(_float(row.get("volume")) for row in rows)
    if total_volume <= 0:
        return rows[-1].get("close") if rows else None
    return sum(_float(row.get("amount")) for row in rows) / total_volume


def _mean(values: list[Any]) -> float | None:
    clean = [_float(value) for value in values if value not in (None, "")]
    return sum(clean) / len(clean) if clean else None


def _median(values: list[Any]) -> float | None:
    clean = sorted(_float(value) for value in values if value not in (None, ""))
    if not clean:
        return None
    mid = len(clean) // 2
    if len(clean) % 2:
        return clean[mid]
    return (clean[mid - 1] + clean[mid]) / 2.0


def _max(values: list[Any]) -> float | None:
    clean = [_float(value) for value in values if value not in (None, "")]
    return max(clean) if clean else None


def _pct(numerator: int, denominator: int) -> float:
    return round(numerator / denominator * 100.0, 6) if denominator else 0.0


def main() -> None:
    summary = run_v5f_1min_queue_123(Path("."))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
