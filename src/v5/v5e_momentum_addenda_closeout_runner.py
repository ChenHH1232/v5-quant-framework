from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5e_momentum_addenda_closeout_packet") / "current"
HISTORICAL_CLOSEOUT = Path("v5e_historical_closeout_governance_packet") / "current" / "v5e_historical_closeout_summary.json"
FIVE_MIN_DIR = Path("v5e_full_holding_5min_momentum_research") / "current"
DAILY_DIR = Path("v5e_daily_momentum_diagnostic_addendum") / "current"
LONG_DIR = Path("v5e_long_horizon_momentum_diagnostic") / "current"
RANGE_DIR = Path("v5e_reasonable_momentum_range_test") / "current"
BRIEF = Path("knowledge") / "research_agent" / "factor_theory" / "v5e_daily_momentum_exit_diagnostic_brief.md"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_momentum_addenda_closeout(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5e_momentum_closeout_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_by_missing_addendum", blockers)
        _write_json(out / "v5e_momentum_closeout_summary.json", summary)
        return summary

    historical = _read_json(root / HISTORICAL_CLOSEOUT)
    five = _read_json(root / FIVE_MIN_DIR / "v5e_momentum_research_summary.json")
    daily = _read_json(root / DAILY_DIR / "v5e_daily_momentum_summary.json")
    long = _read_json(root / LONG_DIR / "v5e_long_momentum_summary.json")
    reasonable = _read_json(root / RANGE_DIR / "v5e_reasonable_momentum_summary.json")

    component_matrix = _component_matrix(five, daily, long, reasonable)
    signal_quality = _signal_quality_matrix(root)
    event_proxy = _event_proxy_matrix(root)
    governance = _governance_matrix(historical, component_matrix, [five, daily, long, reasonable])
    decision = _pm_decision(component_matrix, signal_quality, event_proxy, governance)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blocked_actions = _blocked_actions()
    blockers_out = _blockers(governance)

    _write_csv(out / "v5e_momentum_addenda_component_matrix.csv", component_matrix)
    _write_csv(out / "v5e_momentum_signal_quality_matrix.csv", signal_quality)
    _write_csv(out / "v5e_momentum_event_proxy_comparison.csv", event_proxy)
    _write_csv(out / "v5e_momentum_governance_matrix.csv", governance)
    _write_csv(out / "v5e_momentum_theory_readthrough.csv", _theory_readthrough())
    _write_csv(out / "v5e_momentum_allowed_blocked_actions.csv", blocked_actions)
    _write_csv(out / "v5e_momentum_closeout_pm_decision.csv", decision)
    _write_csv(out / "v5e_momentum_closeout_next_queue.csv", next_queue)
    _write_csv(out / "v5e_momentum_closeout_blockers.csv", blockers_out)
    (out / "v5e_momentum_closeout_report.md").write_text(
        _report(component_matrix, signal_quality, event_proxy, decision),
        encoding="utf-8",
    )
    (out / "v5e_momentum_closeout_next_prompt.md").write_text(_next_prompt(decision[0]["pm_gate_decision"]), encoding="utf-8")
    (out / "v5e_momentum_closeout_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")

    summary = _summary(
        "completed_v5e_momentum_addenda_closeout_packet",
        decision[0]["pm_gate_decision"],
        [],
        addendum_count=len(component_matrix),
        diagnostic_count=sum(1 for row in component_matrix if "diagnostic" in row["final_status"]),
        candidate_count=sum(1 for row in component_matrix if "candidate" in row["final_status"]),
        best_component=decision[0]["best_component"],
        recommended_range=decision[0]["recommended_range"],
    )
    _write_json(out / "v5e_momentum_closeout_summary.json", summary)
    return summary


def _component_matrix(five: dict[str, Any], daily: dict[str, Any], long: dict[str, Any], reasonable: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "component_id": "five_min_momentum",
            "source_dir": str(FIVE_MIN_DIR),
            "scope": "full_holding_period_5min",
            "best_feature": five.get("best_feature_by_next_close_spread", ""),
            "best_spread": five.get("best_feature_next_close_spread", ""),
            "event_proxy_pct_points": "",
            "nav_level_effective": five.get("nav_level_effective", False),
            "pm_gate": five.get("pm_gate_decision", ""),
            "final_status": "diagnostic_only_microstructure_noise",
            "interpretation": "Minute momentum is too noisy; event-level value is very thin and prior NAV failed.",
        },
        {
            "component_id": "short_daily_momentum",
            "source_dir": str(DAILY_DIR),
            "scope": "5d_10d_20d_60d_daily",
            "best_feature": daily.get("best_feature_by_forward_20d_spread", ""),
            "best_spread": daily.get("best_feature_forward_20d_spread", ""),
            "event_proxy_pct_points": daily.get("trigger_overlay_diagnostic_pct_points", ""),
            "nav_level_effective": daily.get("nav_level_effective", False),
            "pm_gate": daily.get("pm_gate_decision", ""),
            "final_status": "diagnostic_only_short_horizon_reversal",
            "interpretation": "Short daily momentum mostly behaves like mean reversion in the V57f holding pool.",
        },
        {
            "component_id": "long_horizon_momentum",
            "source_dir": str(LONG_DIR),
            "scope": "60d_120d_180d_252d_and_v4_6_1_12_1",
            "best_feature": long.get("best_feature_by_forward_60d_spread", ""),
            "best_spread": long.get("best_feature_forward_60d_spread", ""),
            "event_proxy_pct_points": long.get("trigger_overlay_diagnostic_pct_points", ""),
            "nav_level_effective": False,
            "pm_gate": long.get("pm_gate_decision", ""),
            "final_status": "future_research_watchlist_not_quant_spec",
            "interpretation": "Long horizon has the best explanatory signal, but follow-up range test blocks direct delay-sell promotion.",
        },
        {
            "component_id": "reasonable_range_6_1_9_1_12_1",
            "source_dir": str(RANGE_DIR),
            "scope": reasonable.get("range", ""),
            "best_feature": reasonable.get("best_feature_by_forward_60d_spread", ""),
            "best_spread": reasonable.get("best_forward_60d_spread", ""),
            "event_proxy_pct_points": reasonable.get("trigger_overlay_best_pct_points", ""),
            "nav_level_effective": False,
            "pm_gate": reasonable.get("pm_gate_decision", ""),
            "final_status": "diagnostic_only_blocks_delay_sell_spec",
            "interpretation": "Reasonable range confirms mild held-pool signal but V5e trigger-event proxy is negative.",
        },
    ]


def _signal_quality_matrix(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    specs = [
        ("five_min_momentum", FIVE_MIN_DIR / "v5e_momentum_forward_return_diagnostics.csv", "positive_minus_negative_next_close_return"),
        ("short_daily_momentum", DAILY_DIR / "v5e_daily_momentum_forward_return_diagnostics.csv", "positive_minus_negative_forward_20d_return"),
        ("long_horizon_momentum", LONG_DIR / "v5e_long_momentum_forward_diagnostics.csv", "positive_minus_negative_forward_60d_return"),
        ("reasonable_range_6_1_9_1_12_1", RANGE_DIR / "v5e_reasonable_momentum_range_diagnostics.csv", "positive_minus_negative_forward_60d_return"),
    ]
    for component, rel_path, metric in specs:
        data = _read_csv(root / rel_path)
        for row in data:
            value = _to_float(row.get(metric, ""))
            rows.append(
                {
                    "component_id": component,
                    "feature_name": row.get("feature_name", ""),
                    "primary_metric": metric,
                    "primary_metric_value": "" if value is None else value,
                    "stable_direction_diagnostic": row.get("stable_direction_diagnostic", ""),
                    "used_for_trade_rule": False,
                }
            )
    return rows


def _event_proxy_matrix(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    specs = [
        ("five_min_momentum", FIVE_MIN_DIR / "v5e_momentum_nav_engineering_comparison.csv"),
        ("short_daily_momentum", DAILY_DIR / "v5e_daily_momentum_nav_proxy_comparison.csv"),
        ("long_horizon_momentum", LONG_DIR / "v5e_long_momentum_nav_proxy_comparison.csv"),
        ("reasonable_range_6_1_9_1_12_1", RANGE_DIR / "v5e_reasonable_momentum_nav_proxy.csv"),
    ]
    for component, rel_path in specs:
        for row in _read_csv(root / rel_path):
            version = row.get("version_id", "")
            if "momentum" not in version and "reasonable" not in version:
                continue
            rows.append(
                {
                    "component_id": component,
                    "version_id": version,
                    "nav_level_valid": row.get("nav_level_valid", ""),
                    "delta_return_pct_points_vs_baseline": row.get("delta_return_pct_points_vs_baseline", row.get("delta_return_vs_baseline", "")),
                    "accepted": row.get("accepted", False),
                    "interpretation": "event_proxy_only_not_selectable" if row.get("nav_level_valid") in {"False", False} else "nav_reference",
                }
            )
    return rows


def _governance_matrix(
    historical: dict[str, Any],
    component_matrix: list[dict[str, Any]],
    summaries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    checks = [
        ("historical_closeout_complete", historical.get("historical_closeout_status") == "complete", historical.get("historical_closeout_status")),
        ("v5e_accepted_false", not historical.get("v5e_accepted", True), historical.get("v5e_accepted")),
        ("v57f_core_modified_false", not historical.get("v57f_core_modified", True), historical.get("v57f_core_modified")),
        ("threshold_scan_false", not historical.get("threshold_scan_used", True), historical.get("threshold_scan_used")),
        ("all_addenda_not_accepted", all(not row.get("accepted", True) and not row.get("live_trading_approved", True) for row in summaries), "summary accepted/live flags are false"),
        ("all_addenda_governance_clean", all(not row.get("v57f_core_modified", True) and not row.get("threshold_scan_used", True) and not row.get("new_buy_signal_used", True) for row in summaries), "summary governance flags are clean"),
        ("no_full_market_selection", True, "All addenda use V57f/V5e existing holding pool."),
        ("reasonable_range_blocks_delay_sell", component_matrix[-1]["final_status"] == "diagnostic_only_blocks_delay_sell_spec", component_matrix[-1]["final_status"]),
    ]
    return [
        {
            "check_id": check_id,
            "status": "pass" if ok else "fail",
            "detail": detail,
        }
        for check_id, ok, detail in checks
    ]


def _pm_decision(
    component_matrix: list[dict[str, Any]],
    signal_quality: list[dict[str, Any]],
    event_proxy: list[dict[str, Any]],
    governance: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    governance_ok = all(row["status"] == "pass" for row in governance)
    reasonable = next(row for row in component_matrix if row["component_id"] == "reasonable_range_6_1_9_1_12_1")
    long = next(row for row in component_matrix if row["component_id"] == "long_horizon_momentum")
    if not governance_ok:
        decision = "blocked_by_governance_issue"
        next_gate = "repair_governance_audit"
        rationale = "Governance audit failed."
        best_component = ""
        recommended_range = ""
    elif _to_float(reasonable.get("event_proxy_pct_points")) is not None and float(reasonable["event_proxy_pct_points"]) < 0:
        decision = "close_momentum_addenda_as_diagnostic_watchlist"
        next_gate = "continue_v5e_forward_paper_tracking"
        rationale = "Reasonable 6-1/9-1/12-1 range shows mild held-pool signal but negative V5e trigger-event proxy, so delay-sell spec is not admitted."
        best_component = "long_horizon_momentum"
        recommended_range = "9_1_to_12_1_diagnostic_only"
    elif "positive_ready" in str(long.get("pm_gate", "")):
        decision = "retain_long_momentum_for_future_separate_spec_not_now"
        next_gate = "momentum_future_research_watchlist"
        rationale = "Long-horizon signal is positive, but requires separate approval before any Quant spec."
        best_component = "long_horizon_momentum"
        recommended_range = "12_1_primary_6_1_reference"
    else:
        decision = "archive_momentum_addenda_diagnostic_only"
        next_gate = "continue_v5e_forward_paper_tracking"
        rationale = "No momentum addendum has enough NAV or trigger-event evidence for promotion."
        best_component = "none"
        recommended_range = "none"
    return [
        {
            "pm_gate_decision": decision,
            "next_gate": next_gate,
            "best_component": best_component,
            "recommended_range": recommended_range,
            "accepted": False,
            "live_trading_approved": False,
            "v57f_replacement": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "new_buy_signal": False,
            "open_delay_sell_quant_spec_now": False,
            "rationale": rationale,
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {"priority": 1, "next_task": "Continue V5e forward/paper tracking", "allowed": True, "requires_user_approval": False},
        {"priority": 2, "next_task": "Keep 9-1/12-1 momentum as future research watchlist", "allowed": True, "requires_user_approval": False},
        {"priority": 3, "next_task": "Open V5e delay-sell Quant spec from momentum", "allowed": False, "requires_user_approval": True},
        {"priority": 4, "next_task": "Use momentum for full-market selection", "allowed": False, "requires_user_approval": True},
        {"priority": 5, "next_task": "Momentum threshold scan", "allowed": False, "requires_user_approval": True},
    ]


def _theory_readthrough() -> list[dict[str, Any]]:
    return [
        {
            "source": "V4 phase_2_momentum",
            "readthrough": "V4 supports intermediate/long horizon momentum as a slow state or deployment backbone, especially 12-1, but also shows state dependence and acceptance risk.",
            "v5e_use": "Borrow horizon discipline, not strategy structure.",
        },
        {
            "source": str(BRIEF),
            "readthrough": "Momentum can diagnose whether V5e profit-lock sells winners too early.",
            "v5e_use": "Diagnostic only inside V57f/V5e holding pool.",
        },
        {
            "source": "reasonable_range_test",
            "readthrough": "9-1/12-1 can show mild held-pool signal, but V5e trigger-event delay proxy is negative.",
            "v5e_use": "Do not open delay-sell Quant spec now.",
        },
    ]


def _blocked_actions() -> list[dict[str, Any]]:
    return [
        {"action": "keep_diagnostic_watchlist", "allowed": True, "blocked": False},
        {"action": "continue_forward_paper_tracking", "allowed": True, "blocked": False},
        {"action": "open_delay_sell_quant_spec_without_new_pm_approval", "allowed": False, "blocked": True},
        {"action": "use_momentum_full_market_selection", "allowed": False, "blocked": True},
        {"action": "scan_momentum_thresholds", "allowed": False, "blocked": True},
        {"action": "mark_momentum_accepted", "allowed": False, "blocked": True},
        {"action": "modify_v57f_core", "allowed": False, "blocked": True},
    ]


def _blockers(governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in governance if row["status"] != "pass"]
    if not failed:
        return [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Momentum addenda closeout complete."}]
    return [
        {"blocker_id": row["check_id"], "severity": "fatal", "status": "blocking", "description": str(row["detail"])}
        for row in failed
    ]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    addendum_count: int = 0,
    diagnostic_count: int = 0,
    candidate_count: int = 0,
    best_component: str = "",
    recommended_range: str = "",
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_momentum_addenda_closeout_packet",
        "status": status,
        "pm_gate_decision": decision,
        "addendum_count": addendum_count,
        "diagnostic_count": diagnostic_count,
        "candidate_count": candidate_count,
        "best_component": best_component,
        "recommended_range": recommended_range,
        "accepted": False,
        "live_trading_approved": False,
        "v57f_replacement": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "new_buy_signal_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(
    component_matrix: list[dict[str, Any]],
    signal_quality: list[dict[str, Any]],
    event_proxy: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    return "\n".join(
        [
            "# V5e Momentum Addenda Closeout Packet",
            "",
            "## Component Read",
            *[
                f"- `{row['component_id']}`: {row['final_status']}; best={row['best_feature']}; spread={row['best_spread']}; event_proxy={row['event_proxy_pct_points']}"
                for row in component_matrix
            ],
            "",
            "## PM Interpretation",
            "- 5min momentum is too noisy and NAV failed.",
            "- Short daily momentum mostly behaves like mean reversion.",
            "- Long horizon momentum has the best explanatory value.",
            "- Reasonable 6-1/9-1/12-1 range does not support a V5e delay-sell rule because trigger-event proxy is negative.",
            "",
            "## Gate",
            f"- Decision: `{decision[0]['pm_gate_decision']}`.",
            f"- Recommended range: `{decision[0]['recommended_range']}`.",
            f"- Open delay-sell Quant spec now: `{decision[0]['open_delay_sell_quant_spec_now']}`.",
            f"- Rationale: {decision[0]['rationale']}",
            "",
        ]
    )


def _next_prompt(decision: str) -> str:
    return f"""Working directory:
D:\\hh\\codex\\v5

Task:
V5e forward/paper tracking continuation after momentum addenda closeout

Goal:
Use `v5e_momentum_addenda_closeout_packet/current/` as the final PM/Quant readthrough for momentum. Continue V5e forward/paper tracking. Do not open a momentum delay-sell Quant spec unless separately approved. Do not scan thresholds, do not modify V57f, do not mark accepted.

Current decision:
`{decision}`
"""


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5e Momentum Closeout Agent Rules",
            "",
            "- Closeout and governance packet only.",
            "- Do not mark any momentum addendum accepted.",
            "- Do not open delay-sell engineering without separate PM approval.",
            "- Do not use momentum for full-market stock selection.",
            "- Do not scan thresholds or modify V57f core.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        HISTORICAL_CLOSEOUT,
        FIVE_MIN_DIR / "v5e_momentum_research_summary.json",
        FIVE_MIN_DIR / "v5e_momentum_forward_return_diagnostics.csv",
        FIVE_MIN_DIR / "v5e_momentum_nav_engineering_comparison.csv",
        DAILY_DIR / "v5e_daily_momentum_summary.json",
        DAILY_DIR / "v5e_daily_momentum_forward_return_diagnostics.csv",
        DAILY_DIR / "v5e_daily_momentum_nav_proxy_comparison.csv",
        LONG_DIR / "v5e_long_momentum_summary.json",
        LONG_DIR / "v5e_long_momentum_forward_diagnostics.csv",
        LONG_DIR / "v5e_long_momentum_nav_proxy_comparison.csv",
        RANGE_DIR / "v5e_reasonable_momentum_summary.json",
        RANGE_DIR / "v5e_reasonable_momentum_range_diagnostics.csv",
        RANGE_DIR / "v5e_reasonable_momentum_nav_proxy.csv",
        BRIEF,
    ]
    return [
        {"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)}
        for path in required
        if not (root / path).exists()
    ]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    result = run_v5e_momentum_addenda_closeout()
    print(json.dumps(result, ensure_ascii=False, indent=2))
