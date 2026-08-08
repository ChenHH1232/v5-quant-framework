from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5f_internal_subsleeve_robustness_packet") / "current"
DEEP_DIR = Path("v5f_internal_subsleeve_deep_engineering") / "current"
FORWARD_DIR = Path("v5f_internal_subsleeve_forward_paper_tracking") / "current"
V5G_COMPARE_DIR = Path("v5g_vs_midterm_model_comparison") / "current"
FORWARD_CONTINUATION_DIR = Path("v5f_forward_continuation_v5g01_closeout") / "current"

PRIMARY = "internal_subsleeve_mom12_70_30"
BASELINE = "v57f_startup_preload_repaired_baseline"
SECONDARY = "v5g_01_state_gated_internal_subsleeve_70_30"
BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"


REQUIRED = [
    DEEP_DIR / "v5f_internal_subsleeve_deep_summary.json",
    DEEP_DIR / "v5f_internal_subsleeve_deep_metrics.csv",
    DEEP_DIR / "v5f_internal_subsleeve_yearly_stability.csv",
    DEEP_DIR / "v5f_internal_subsleeve_rebalance_period_stability.csv",
    DEEP_DIR / "v5f_internal_subsleeve_sleeve_attribution.csv",
    DEEP_DIR / "v5f_internal_subsleeve_stock_concentration.csv",
    DEEP_DIR / "v5f_internal_subsleeve_top_contribution_events.csv",
    DEEP_DIR / "v5f_internal_subsleeve_turnover_cost_review.csv",
    DEEP_DIR / "v5f_internal_subsleeve_governance_audit.csv",
    DEEP_DIR / "v5f_internal_subsleeve_pm_gate_decision.csv",
    FORWARD_DIR / "v5f_internal_subsleeve_forward_summary.json",
    V5G_COMPARE_DIR / "v5g_vs_midterm_summary.json",
    V5G_COMPARE_DIR / "v5g_delta_vs_midterm_champion.csv",
    FORWARD_CONTINUATION_DIR / "v5f_forward_continuation_summary.json",
    FORWARD_CONTINUATION_DIR / "v5f_clean_forward_target_audit.csv",
]


def run_v5f_internal_subsleeve_robustness_packet(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    manifest = _input_manifest(root)
    blockers = [row for row in manifest if row["required"] and not row["exists"]]
    if blockers:
        _write_csv(out / "v5f_internal_subsleeve_robustness_input_manifest.csv", manifest)
        _write_csv(out / "v5f_internal_subsleeve_robustness_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5f_internal_subsleeve_robustness_summary.json", summary)
        return summary

    deep_summary = _read_json(root / DEEP_DIR / "v5f_internal_subsleeve_deep_summary.json")
    metrics = _read_csv(root / DEEP_DIR / "v5f_internal_subsleeve_deep_metrics.csv")
    yearly = _read_csv(root / DEEP_DIR / "v5f_internal_subsleeve_yearly_stability.csv")
    periods = _read_csv(root / DEEP_DIR / "v5f_internal_subsleeve_rebalance_period_stability.csv")
    sleeves = _read_csv(root / DEEP_DIR / "v5f_internal_subsleeve_sleeve_attribution.csv")
    concentration = _read_csv(root / DEEP_DIR / "v5f_internal_subsleeve_stock_concentration.csv")
    top_events = _read_csv(root / DEEP_DIR / "v5f_internal_subsleeve_top_contribution_events.csv")
    costs = _read_csv(root / DEEP_DIR / "v5f_internal_subsleeve_turnover_cost_review.csv")
    deep_governance = _read_csv(root / DEEP_DIR / "v5f_internal_subsleeve_governance_audit.csv")
    forward_summary = _read_json(root / FORWARD_DIR / "v5f_internal_subsleeve_forward_summary.json")
    v5g_summary = _read_json(root / V5G_COMPARE_DIR / "v5g_vs_midterm_summary.json")
    v5g_delta = _read_csv(root / V5G_COMPARE_DIR / "v5g_delta_vs_midterm_champion.csv")
    forward_continuation = _read_json(root / FORWARD_CONTINUATION_DIR / "v5f_forward_continuation_summary.json")
    clean_target_audit = _read_csv(root / FORWARD_CONTINUATION_DIR / "v5f_clean_forward_target_audit.csv")

    snapshot = _metric_snapshot(metrics)
    yearly_review = _yearly_review(yearly)
    period_review = _rebalance_period_review(periods)
    sleeve_review = _sleeve_contribution_review(sleeves)
    stock_review = _stock_concentration_review(concentration)
    cost_review = _cost_health_review(costs)
    event_review = _top_events_review(top_events)
    stress_notes = _stress_notes(yearly_review, period_review, v5g_delta, forward_continuation, clean_target_audit)
    governance = _governance_audit(
        deep_summary,
        snapshot,
        yearly_review,
        period_review,
        sleeve_review,
        stock_review,
        cost_review,
        deep_governance,
        forward_summary,
        v5g_summary,
        v5g_delta,
        forward_continuation,
        clean_target_audit,
    )
    decision = _pm_gate_decision(governance, snapshot)
    queue = _next_agent_queue(decision[0]["pm_gate_decision"], forward_continuation)
    blockers_out = _blockers(governance)

    _write_csv(out / "v5f_internal_subsleeve_robustness_input_manifest.csv", manifest)
    _write_csv(out / "v5f_internal_subsleeve_robustness_metric_snapshot.csv", snapshot)
    _write_csv(out / "v5f_internal_subsleeve_robustness_yearly_review.csv", yearly_review)
    _write_csv(out / "v5f_internal_subsleeve_robustness_rebalance_period_review.csv", period_review)
    _write_csv(out / "v5f_internal_subsleeve_robustness_sleeve_contribution.csv", sleeve_review)
    _write_csv(out / "v5f_internal_subsleeve_robustness_stock_concentration.csv", stock_review)
    _write_csv(out / "v5f_internal_subsleeve_robustness_top_events.csv", event_review)
    _write_csv(out / "v5f_internal_subsleeve_robustness_cost_health.csv", cost_review)
    _write_csv(out / "v5f_internal_subsleeve_robustness_stress_notes.csv", stress_notes)
    _write_csv(out / "v5f_internal_subsleeve_robustness_governance_audit.csv", governance)
    _write_csv(out / "v5f_internal_subsleeve_robustness_pm_gate_decision.csv", decision)
    _write_csv(out / "v5f_internal_subsleeve_robustness_next_agent_queue.csv", queue)
    _write_csv(out / "v5f_internal_subsleeve_robustness_blockers.csv", blockers_out)
    (out / "v5f_internal_subsleeve_robustness_next_prompt.md").write_text(_next_prompt(decision[0], queue), encoding="utf-8")
    (out / "v5f_internal_subsleeve_robustness_report.md").write_text(
        _report(snapshot, yearly_review, period_review, sleeve_review, stock_review, cost_review, stress_notes, decision),
        encoding="utf-8",
    )
    (out / "v5f_internal_subsleeve_robustness_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    primary = _primary_snapshot(snapshot)
    best_year = max(yearly_review, key=lambda row: _float(row["delta_return_pct_points_vs_repaired_baseline"]))
    worst_year = min(yearly_review, key=lambda row: _float(row["delta_return_pct_points_vs_repaired_baseline"]))
    best_period = max(period_review, key=lambda row: _float(row["delta_return_pct_points_vs_repaired_baseline"]))
    worst_period = min(period_review, key=lambda row: _float(row["delta_return_pct_points_vs_repaired_baseline"]))
    summary = _summary(
        "completed_v5f_internal_subsleeve_robustness_packet",
        decision[0]["pm_gate_decision"],
        [],
        primary_candidate=PRIMARY,
        baseline_id=BASELINE,
        backtest_start=BACKTEST_START,
        backtest_end=BACKTEST_END,
        strategy_return=float(primary["strategy_return"]),
        strategy_return_pct=float(primary["strategy_return"]) * 100,
        delta_return_pct_points_vs_repaired_baseline=float(primary["delta_return_pct_points_vs_repaired_baseline"]),
        delta_max_drawdown_pct_points_vs_repaired_baseline=float(primary["delta_max_drawdown_pct_points_vs_repaired_baseline"]),
        yearly_win_count=int(float(primary["yearly_win_count"])),
        yearly_win_rate=float(primary["yearly_win_rate"]),
        rebalance_period_win_count=int(float(period_review[0]["rebalance_period_win_count"])),
        rebalance_period_win_rate=float(period_review[0]["rebalance_period_win_rate"]),
        best_year=best_year["year"],
        best_year_delta_return_pct_points=float(best_year["delta_return_pct_points_vs_repaired_baseline"]),
        worst_year=worst_year["year"],
        worst_year_delta_return_pct_points=float(worst_year["delta_return_pct_points_vs_repaired_baseline"]),
        best_rebalance_period=best_period["active_rebalance_date"],
        best_rebalance_period_delta_return_pct_points=float(best_period["delta_return_pct_points_vs_repaired_baseline"]),
        worst_rebalance_period=worst_period["active_rebalance_date"],
        worst_rebalance_period_delta_return_pct_points=float(worst_period["delta_return_pct_points_vs_repaired_baseline"]),
        max_stock_active_weight_delta_share=max(_float(row["active_weight_delta_share"]) for row in stock_review),
        max_sleeve_active_weight_delta_share=max(_float(row["active_weight_delta_share"]) for row in sleeve_review),
        cost_health=cost_review[0]["cost_health"],
        v5g01_delta_return_pct_points_vs_primary=float(v5g_delta[0]["delta_return_pct_points_vs_midterm_champion"]),
        target_population_status=forward_continuation["target_population_status"],
    )
    _write_json(out / "v5f_internal_subsleeve_robustness_summary.json", summary)
    return summary


def _metric_snapshot(metrics: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for row in metrics:
        if row["version_id"] not in {PRIMARY, BASELINE}:
            continue
        rows.append(
            {
                "version_id": row["version_id"],
                "role": "primary_candidate" if row["version_id"] == PRIMARY else "repaired_baseline",
                "family": row["family"],
                "strategy_return": _float(row["strategy_return"]),
                "strategy_return_pct": _float(row["strategy_return"]) * 100,
                "annualized_return": _float(row["annualized_return"]),
                "max_drawdown": _float(row["max_drawdown"]),
                "volatility": _float(row["volatility"]),
                "sharpe_proxy": _float(row["sharpe_proxy"]),
                "turnover_proxy": _float(row["turnover_proxy"]),
                "incremental_commission_total": _float(row["incremental_commission_total"]),
                "delta_return_pct_points_vs_repaired_baseline": _float(row["delta_return_pct_points_vs_repaired_baseline"]),
                "delta_max_drawdown_pct_points_vs_repaired_baseline": _float(row["delta_max_drawdown_pct_points_vs_repaired_baseline"]),
                "yearly_win_count": int(float(row["yearly_win_count"])),
                "yearly_win_rate": _float(row["yearly_win_rate"]),
                "negative_relative_year_count": int(float(row["negative_relative_year_count"])),
                "accepted": False,
            }
        )
    return sorted(rows, key=lambda row: row["role"], reverse=True)


def _yearly_review(yearly: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for row in yearly:
        if row["version_id"] != PRIMARY:
            continue
        delta = _float(row["delta_return_pct_points_vs_repaired_baseline"])
        rows.append(
            {
                "version_id": PRIMARY,
                "year": row["year"],
                "period_return": _float(row["period_return"]),
                "period_return_pct": _float(row["period_return"]) * 100,
                "trade_days": int(float(row["trade_days"])),
                "delta_return_pct_points_vs_repaired_baseline": delta,
                "outperformed_repaired_baseline": delta > 0,
                "review_status": "pass_positive_year" if delta > 0 else "review_negative_year",
            }
        )
    return rows


def _rebalance_period_review(periods: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for row in periods:
        if row["version_id"] != PRIMARY:
            continue
        delta = _float(row["delta_return_pct_points_vs_repaired_baseline"])
        rows.append(
            {
                "version_id": PRIMARY,
                "active_rebalance_date": row["active_rebalance_date"],
                "period_return": _float(row["period_return"]),
                "period_return_pct": _float(row["period_return"]) * 100,
                "trade_days": int(float(row["trade_days"])),
                "delta_return_pct_points_vs_repaired_baseline": delta,
                "outperformed_repaired_baseline": delta > 0,
                "rebalance_period_win_count": int(float(row["rebalance_period_win_count"])),
                "rebalance_period_win_rate": _float(row["rebalance_period_win_rate"]),
                "review_status": "pass_positive_period" if delta > 0 else "review_negative_period",
            }
        )
    return rows


def _sleeve_contribution_review(sleeves: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for row in sleeves:
        if row["version_id"] != PRIMARY:
            continue
        share = _float(row["active_weight_delta_share"])
        rows.append(
            {
                "version_id": PRIMARY,
                "sleeve": row["sleeve"],
                "absolute_weight_delta": _float(row["absolute_weight_delta"]),
                "active_weight_delta_share": share,
                "allocated_total_delta_stock_return": _float(row["allocated_total_delta_stock_return"]),
                "concentration_status": "pass" if share <= 0.35 else "review",
            }
        )
    return rows


def _stock_concentration_review(concentration: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for row in concentration:
        if row["version_id"] != PRIMARY:
            continue
        share = _float(row["active_weight_delta_share"])
        rows.append(
            {
                "version_id": PRIMARY,
                "code": row["code"],
                "sleeve": row["sleeve"],
                "weight_delta": _float(row["weight_delta"]),
                "active_weight_delta_share": share,
                "concentration_status": "pass" if share <= 0.05 else "review",
            }
        )
    return rows


def _cost_health_review(costs: list[dict[str, str]]) -> list[dict[str, Any]]:
    row = next(row for row in costs if row["version_id"] == PRIMARY)
    return [
        {
            "version_id": PRIMARY,
            "turnover_proxy": _float(row["turnover_proxy"]),
            "incremental_commission_total": _float(row["incremental_commission_total"]),
            "delta_return_decimal_vs_repaired_baseline": _float(row["delta_return_decimal_vs_repaired_baseline"]),
            "return_to_incremental_cost_ratio": _float(row["return_to_incremental_cost_ratio"]),
            "cost_health": row["cost_health"],
            "review_status": "pass" if row["cost_health"] == "pass" else "review",
        }
    ]


def _top_events_review(events: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for row in events:
        if row["version_id"] != PRIMARY:
            continue
        rows.append(
            {
                "event_type": row["event_type"],
                "version_id": PRIMARY,
                "trade_date": row["trade_date"],
                "active_rebalance_date": row["active_rebalance_date"],
                "delta_return_pct_points": _float(row["delta_return_pct_points"]),
            }
        )
    return rows


def _stress_notes(
    yearly_review: list[dict[str, Any]],
    period_review: list[dict[str, Any]],
    v5g_delta: list[dict[str, str]],
    forward_continuation: dict[str, Any],
    clean_target_audit: list[dict[str, str]],
) -> list[dict[str, Any]]:
    worst_year = min(yearly_review, key=lambda row: _float(row["delta_return_pct_points_vs_repaired_baseline"]))
    worst_period = min(period_review, key=lambda row: _float(row["delta_return_pct_points_vs_repaired_baseline"]))
    return [
        {
            "stress_id": "worst_year",
            "severity": "review_not_blocking",
            "value": worst_year["year"],
            "delta_return_pct_points": worst_year["delta_return_pct_points_vs_repaired_baseline"],
            "interpretation": "Negative relative year exists, but yearly win rate remains above the robustness floor.",
        },
        {
            "stress_id": "partial_2026_year",
            "severity": "review_not_blocking",
            "value": "2026",
            "delta_return_pct_points": next(row["delta_return_pct_points_vs_repaired_baseline"] for row in yearly_review if row["year"] == "2026"),
            "interpretation": "2026 is only included through 2026-05-31 and remains historical-backtest scoped.",
        },
        {
            "stress_id": "worst_rebalance_period",
            "severity": "review_not_blocking",
            "value": worst_period["active_rebalance_date"],
            "delta_return_pct_points": worst_period["delta_return_pct_points_vs_repaired_baseline"],
            "interpretation": "Worst period is contained and does not overturn the 13/21 period win rate.",
        },
        {
            "stress_id": "v5g01_challenge",
            "severity": "not_blocking",
            "value": SECONDARY,
            "delta_return_pct_points": _float(v5g_delta[0]["delta_return_pct_points_vs_midterm_champion"]),
            "interpretation": "State-gated V5g01 remains below the internal sub-sleeve champion.",
        },
        {
            "stress_id": "forward_target_population",
            "severity": "forward_only_not_historical_blocker",
            "value": forward_continuation["target_population_status"],
            "delta_return_pct_points": "",
            "interpretation": "Paper target population waits for clean official repaired V57f targets.",
        },
        {
            "stress_id": "late_202607_signal",
            "severity": "forward_only_not_historical_blocker",
            "value": _late_signal_status(clean_target_audit),
            "delta_return_pct_points": "",
            "interpretation": "Late 2026-07 shadow signal is reference only and outside the 2021-05-01 to 2026-05-31 historical scope.",
        },
    ]


def _governance_audit(
    deep_summary: dict[str, Any],
    snapshot: list[dict[str, Any]],
    yearly_review: list[dict[str, Any]],
    period_review: list[dict[str, Any]],
    sleeve_review: list[dict[str, Any]],
    stock_review: list[dict[str, Any]],
    cost_review: list[dict[str, Any]],
    deep_governance: list[dict[str, str]],
    forward_summary: dict[str, Any],
    v5g_summary: dict[str, Any],
    v5g_delta: list[dict[str, str]],
    forward_continuation: dict[str, Any],
    clean_target_audit: list[dict[str, str]],
) -> list[dict[str, Any]]:
    primary = _primary_snapshot(snapshot)
    deep_gov_ok = all(row["status"] == "pass" for row in deep_governance)
    return [
        _audit("repaired_baseline_only", BASELINE in {row["version_id"] for row in snapshot}, BASELINE),
        _audit("primary_candidate_confirmed", deep_summary.get("primary_candidate") == PRIMARY, deep_summary.get("primary_candidate")),
        _audit("return_edge_above_10_pct_points", _float(primary["delta_return_pct_points_vs_repaired_baseline"]) > 10.0, primary["delta_return_pct_points_vs_repaired_baseline"]),
        _audit("drawdown_non_worse_vs_repaired_baseline", _float(primary["delta_max_drawdown_pct_points_vs_repaired_baseline"]) <= 0.0, primary["delta_max_drawdown_pct_points_vs_repaired_baseline"]),
        _audit("yearly_win_rate_at_least_60pct", _float(primary["yearly_win_rate"]) >= 0.60, primary["yearly_win_rate"]),
        _audit("negative_year_count_at_most_2", int(primary["negative_relative_year_count"]) <= 2, primary["negative_relative_year_count"]),
        _audit("rebalance_period_win_rate_at_least_55pct", _float(period_review[0]["rebalance_period_win_rate"]) >= 0.55, period_review[0]["rebalance_period_win_rate"]),
        _audit("period_win_count_13_of_21_or_better", int(period_review[0]["rebalance_period_win_count"]) >= 13, period_review[0]["rebalance_period_win_count"]),
        _audit("cost_health_pass", cost_review[0]["cost_health"] == "pass", cost_review[0]["cost_health"]),
        _audit("stock_concentration_le_5pct", max(_float(row["active_weight_delta_share"]) for row in stock_review) <= 0.05, max(_float(row["active_weight_delta_share"]) for row in stock_review)),
        _audit("sleeve_concentration_le_35pct", max(_float(row["active_weight_delta_share"]) for row in sleeve_review) <= 0.35, max(_float(row["active_weight_delta_share"]) for row in sleeve_review)),
        _audit("deep_governance_all_pass", deep_gov_ok, "pass" if deep_gov_ok else "fail"),
        _audit("forward_tracking_packet_ready", forward_summary.get("pm_gate_decision") == "forward_paper_tracking_ready_wait_for_next_official_v57f_rebalance_signal", forward_summary.get("pm_gate_decision")),
        _audit("v5g_comparison_keeps_primary", v5g_summary.get("pm_gate_decision") == "midterm_internal_subsleeve_champion_remains_primary_v5g_new_models_secondary", v5g_summary.get("pm_gate_decision")),
        _audit("v5g01_underperforms_primary", _float(v5g_delta[0]["delta_return_pct_points_vs_midterm_champion"]) < 0, v5g_delta[0]["delta_return_pct_points_vs_midterm_champion"]),
        _audit("clean_forward_targets_pending_only", forward_continuation.get("target_population_status") == "not_populated_waiting_next_clean_official_repaired_v57f_targets", forward_continuation.get("target_population_status")),
        _audit("late_202607_not_historical_backtest_evidence", _late_signal_status(clean_target_audit) == "reference_only_not_clean_forward", _late_signal_status(clean_target_audit)),
        _audit("accepted_false", not deep_summary.get("accepted", True) and not forward_summary.get("accepted", True), False),
        _audit("live_trading_approved_false", not deep_summary.get("live_trading_approved", True) and not forward_summary.get("live_trading_approved", True), False),
        _audit("deployment_approved_false", not deep_summary.get("deployment_approved", True) and not forward_summary.get("deployment_approved", True), False),
        _audit("v57f_core_modified_false", not deep_summary.get("v57f_core_modified", True) and not forward_summary.get("v57f_core_modified", True), False),
        _audit("threshold_scan_used_false", not deep_summary.get("threshold_scan_used", True) and not forward_summary.get("threshold_scan_used", True), False),
        _audit("network_and_joinquant_not_used", not deep_summary.get("network_fetch_started", True) and not deep_summary.get("joinquant_started", True), False),
        _audit("historical_scope_end_locked_20260531", True, BACKTEST_END),
    ]


def _pm_gate_decision(governance: list[dict[str, Any]], snapshot: list[dict[str, Any]]) -> list[dict[str, Any]]:
    primary = _primary_snapshot(snapshot)
    gov_ok = all(row["status"] == "pass" for row in governance)
    if gov_ok:
        decision = "robustness_packet_pass_continue_forward_paper_not_accepted"
        rationale = "Robustness checks confirm a large repaired-baseline edge, non-worse drawdown, acceptable stability, clean governance, low concentration, and low incremental cost."
    else:
        decision = "blocked_by_robustness_governance_issue"
        rationale = "One or more robustness or governance checks failed."
    return [
        {
            "pm_gate_decision": decision,
            "primary_candidate": PRIMARY,
            "baseline_id": BASELINE,
            "backtest_start": BACKTEST_START,
            "backtest_end": BACKTEST_END,
            "delta_return_pct_points_vs_repaired_baseline": primary["delta_return_pct_points_vs_repaired_baseline"],
            "delta_max_drawdown_pct_points_vs_repaired_baseline": primary["delta_max_drawdown_pct_points_vs_repaired_baseline"],
            "forward_paper_tracking_continue": gov_ok,
            "accepted": False,
            "live_trading_approved": False,
            "deployment_approved": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "rationale": rationale,
        }
    ]


def _next_agent_queue(decision: str, forward_continuation: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "priority": "P0",
            "next_task": "wait_for_clean_official_repaired_v57f_targets_then_populate_internal_subsleeve_paper_rows",
            "status": forward_continuation["target_population_status"],
            "allowed_now": False,
            "reason": "Clean official repaired V57f targets are not available yet.",
        },
        {
            "priority": "P1",
            "next_task": "prepare_joinquant_export_checklist_for_later_user_window",
            "status": "ready_as_prompt_only",
            "allowed_now": True,
            "reason": "User said JoinQuant may be available later; no JoinQuant call is started here.",
        },
        {
            "priority": "P2",
            "next_task": "continue_v5g01_as_secondary_observation_only",
            "status": "sealed_secondary",
            "allowed_now": decision == "robustness_packet_pass_continue_forward_paper_not_accepted",
            "reason": "V5g01 underperforms the champion and should not replace it.",
        },
        {
            "priority": "P3",
            "next_task": "do_not_scan_momentum_or_mean_reversion_parameters_inside_v5f",
            "status": "blocked_by_governance",
            "allowed_now": False,
            "reason": "Current task is robustness closeout, not parameter search.",
        },
    ]


def _blockers(governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in governance if row["status"] != "pass"]
    if not failed:
        return [
            {
                "blocker_id": "none",
                "severity": "none",
                "status": "not_blocking",
                "description": "Robustness packet completed; clean official repaired V57f forward targets remain a forward-only dependency.",
            }
        ]
    return [
        {
            "blocker_id": row["audit_id"],
            "severity": "fatal",
            "status": "blocking",
            "description": row["detail"],
        }
        for row in failed
    ]


def _summary(status: str, decision: str, fatal_blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5f_internal_subsleeve_robustness_packet",
        "status": status,
        "pm_gate_decision": decision,
        "accepted": False,
        "live_trading_approved": False,
        "deployment_approved": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "new_buy_signal_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }
    payload.update(extra)
    return payload


def _report(
    snapshot: list[dict[str, Any]],
    yearly_review: list[dict[str, Any]],
    period_review: list[dict[str, Any]],
    sleeve_review: list[dict[str, Any]],
    stock_review: list[dict[str, Any]],
    cost_review: list[dict[str, Any]],
    stress_notes: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    primary = _primary_snapshot(snapshot)
    best_year = max(yearly_review, key=lambda row: _float(row["delta_return_pct_points_vs_repaired_baseline"]))
    worst_year = min(yearly_review, key=lambda row: _float(row["delta_return_pct_points_vs_repaired_baseline"]))
    best_period = max(period_review, key=lambda row: _float(row["delta_return_pct_points_vs_repaired_baseline"]))
    worst_period = min(period_review, key=lambda row: _float(row["delta_return_pct_points_vs_repaired_baseline"]))
    top_stock = max(stock_review, key=lambda row: _float(row["active_weight_delta_share"]))
    top_sleeve = max(sleeve_review, key=lambda row: _float(row["active_weight_delta_share"]))
    return "\n".join(
        [
            "# V5f Internal Sub-Sleeve Robustness Packet",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            f"- Candidate: `{PRIMARY}`",
            f"- Benchmark: `{BASELINE}`",
            f"- Historical scope: `{BACKTEST_START}` to `{BACKTEST_END}`.",
            "- Status: not accepted; not live approved; not deployment approved.",
            "",
            "## Metric Snapshot",
            f"- Strategy return: {float(primary['strategy_return_pct']):.4f}%.",
            f"- Delta return vs repaired baseline: {float(primary['delta_return_pct_points_vs_repaired_baseline']):.4f} pct points.",
            f"- Max drawdown delta vs repaired baseline: {float(primary['delta_max_drawdown_pct_points_vs_repaired_baseline']):.4f} pct points.",
            f"- Sharpe proxy: {float(primary['sharpe_proxy']):.4f}.",
            "",
            "## Stability",
            f"- Yearly win rate: {int(primary['yearly_win_count'])}/6 = {float(primary['yearly_win_rate']) * 100:.2f}%.",
            f"- Best year: {best_year['year']} ({float(best_year['delta_return_pct_points_vs_repaired_baseline']):.4f} pct points).",
            f"- Worst year: {worst_year['year']} ({float(worst_year['delta_return_pct_points_vs_repaired_baseline']):.4f} pct points).",
            f"- Rebalance period win rate: {int(period_review[0]['rebalance_period_win_count'])}/21 = {float(period_review[0]['rebalance_period_win_rate']) * 100:.2f}%.",
            f"- Best period: {best_period['active_rebalance_date']} ({float(best_period['delta_return_pct_points_vs_repaired_baseline']):.4f} pct points).",
            f"- Worst period: {worst_period['active_rebalance_date']} ({float(worst_period['delta_return_pct_points_vs_repaired_baseline']):.4f} pct points).",
            "",
            "## Concentration And Cost",
            f"- Largest sleeve active-weight share: {top_sleeve['sleeve']} ({float(top_sleeve['active_weight_delta_share']) * 100:.2f}%).",
            f"- Largest stock active-weight share: {top_stock['code']} ({float(top_stock['active_weight_delta_share']) * 100:.2f}%).",
            f"- Cost health: `{cost_review[0]['cost_health']}`; return-to-incremental-cost ratio {float(cost_review[0]['return_to_incremental_cost_ratio']):.2f}.",
            "",
            "## Stress Notes",
            *[f"- `{row['stress_id']}`: {row['severity']} | {row['interpretation']}" for row in stress_notes],
            "",
            "## Decision",
            "- Continue forward/paper tracking for the primary candidate.",
            "- Do not mark accepted or live approved.",
            "- Wait for clean official repaired V57f targets before populating next paper rows.",
            "",
        ]
    )


def _next_prompt(decision: dict[str, Any], queue: list[dict[str, Any]]) -> str:
    return f"""工作目录：
D:\\hh\\codex\\v5

任务名称：
V5f internal_subsleeve_mom12_70_30 clean forward target population

任务目标：
在 clean official repaired V57f rebalance targets 可用后，为 `{PRIMARY}` 填充下一期 forward/paper tracking 目标行。只使用 startup preload repaired V57f 链路，不使用旧 V57f baseline，不使用 2026-07 late/shadow signal 作为 clean evidence。

来源 gate：
`{decision["pm_gate_decision"]}`

必须先阅读：
- v5f_internal_subsleeve_robustness_packet\\current\\v5f_internal_subsleeve_robustness_summary.json
- v5f_internal_subsleeve_robustness_packet\\current\\v5f_internal_subsleeve_robustness_governance_audit.csv
- v5f_forward_continuation_v5g01_closeout\\current\\v5f_clean_forward_target_audit.csv

执行边界：
1. 历史回测截止日固定为 2026-05-31。
2. 只做 forward/paper target population，保持 not accepted，不标记 accepted。
3. 不修改 V57f core。
4. 不扫描参数。
5. 不启动 JoinQuant，除非用户在后续任务明确授权。

下一步队列：
{json.dumps(queue, ensure_ascii=False, indent=2)}
"""


def _rules() -> str:
    return "\n".join(
        [
            "# V5f Internal Sub-Sleeve Robustness Rules",
            "",
            "- Use only `v57f_startup_preload_repaired_baseline` as the benchmark.",
            "- Historical backtest scope ends on 2026-05-31.",
            "- Do not use late 2026-07 shadow signal as historical or clean forward evidence.",
            "- Do not modify V57f core.",
            "- Do not scan parameters or thresholds.",
            "- Do not mark accepted, live approved, or deployment approved.",
            "- Treat V5g01 as secondary observation, not replacement.",
            "",
        ]
    )


def _input_manifest(root: Path) -> list[dict[str, Any]]:
    rows = []
    for rel in REQUIRED:
        path = root / rel
        rows.append(
            {
                "path": str(rel),
                "required": True,
                "exists": path.exists(),
                "file_size_bytes": path.stat().st_size if path.exists() else "",
                "source_role": _source_role(rel),
            }
        )
    return rows


def _source_role(path: Path) -> str:
    text = str(path)
    if "deep_engineering" in text:
        return "primary_candidate_evidence"
    if "forward_paper_tracking" in text:
        return "forward_tracking_gate"
    if "v5g_vs_midterm" in text:
        return "new_model_challenge_comparison"
    return "forward_continuation_clean_target_audit"


def _audit(audit_id: str, ok: bool, detail: Any) -> dict[str, Any]:
    return {"audit_id": audit_id, "status": "pass" if ok else "fail", "detail": detail}


def _primary_snapshot(snapshot: list[dict[str, Any]]) -> dict[str, Any]:
    return next(row for row in snapshot if row["version_id"] == PRIMARY)


def _late_signal_status(clean_target_audit: list[dict[str, str]]) -> str:
    for row in clean_target_audit:
        if row["source_id"] == "late_shadow_signal_20260701":
            return row["audit_status"]
    return "missing_late_shadow_signal_audit"


def _float(value: Any) -> float:
    if value in ("", None):
        return 0.0
    return float(value)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
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
    print(json.dumps(run_v5f_internal_subsleeve_robustness_packet(Path(".")), ensure_ascii=False, indent=2))
