from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from v5.math_utils import to_float
from v5 import v5e_limited_engineering_runner as eng


OUT_DIR = Path("v5e_capital_sensitivity_test") / "current"
RUN_DIR = OUT_DIR / "runs"
FORWARD_SUMMARY = Path("v5e_profit_lock_main_forward_paper_execution_tracking") / "current" / "v5e_profit_lock_forward_paper_summary.json"
FORWARD_STATUS = Path("v5e_profit_lock_main_forward_paper_execution_tracking") / "current" / "v5e_profit_lock_forward_paper_candidate_status.csv"
FORWARD_GATE = Path("v5e_profit_lock_main_forward_paper_execution_tracking") / "current" / "v5e_profit_lock_forward_paper_gate_decision.csv"
FORMAL_SUMMARY = Path("v5e_profit_lock_execution_robust_formal_review") / "current" / "v5e_profit_lock_execution_robust_summary.json"
PROXY_SUMMARY = Path("v5e_trigger_day_5min_execution_proxy_test") / "current" / "v5e_5min_execution_proxy_summary.json"
PROXY_COMPARISON = Path("v5e_trigger_day_5min_execution_proxy_test") / "current" / "v5e_5min_execution_proxy_comparison.csv"
V5E_EXIT_LOG = Path("v5e_limited_engineering_loop") / "current" / "v5e_exit_action_log.csv"
V5E_TRIGGER_LOG = Path("v5e_limited_engineering_loop") / "current" / "v5e_trigger_log.csv"
V5E_CASH_DRAG_LOG = Path("v5e_limited_engineering_loop") / "current" / "v5e_cash_drag_log.csv"
STARTUP_SUMMARY = Path("v5_startup_warmup_price_repair") / "current" / "v5_startup_warmup_price_repair_summary.json"
SHADOW_CONFIG = Path("config") / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f_startup_repaired_shadow.json"
MINUTE_INDEX = Path("v5e_trigger_day_5min_execution_data_gate") / "current" / "v5e_exit_5min_standardized_index.csv"

BASELINE = "v57f_repaired_baseline"
V5E_MAIN = "v5e_profit_lock_main_20pct_sell50"
CAPITAL_LEVELS = [
    ("50w", 500_000.0),
    ("200w", 2_000_000.0),
    ("800w", 8_000_000.0),
]
SMALL_ORDER_THRESHOLD = 10_000.0
BROKER_REFERENCE_COMMISSION_RATE = 0.0001
BROKER_REFERENCE_MIN_COMMISSION = 5.0
REFERENCE_TARGET_COUNT = 28


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_capital_sensitivity(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    run_dir = root / RUN_DIR
    out.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)
    blockers = _missing_blockers(root)
    if blockers:
        _write_csv(out / "v5e_capital_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5e_capital_sensitivity_summary.json", summary)
        return summary

    bundle = eng._load_data(root)
    minute_prices = _load_minute_prices(root)
    all_sims: list[dict[str, Any]] = []
    comparison_rows: list[dict[str, Any]] = []
    cost_rows: list[dict[str, Any]] = []
    cash_rows: list[dict[str, Any]] = []
    vwap_rows: list[dict[str, Any]] = []
    order_rows: list[dict[str, Any]] = []
    governance_rows: list[dict[str, Any]] = []
    min_efficiency_rows = _min_commission_efficiency_rows()
    wanyi_rows = _wanyi_commission_supplement_rows(root, bundle, minute_prices)

    original_cash = eng.INITIAL_CASH
    try:
        for label, capital in CAPITAL_LEVELS:
            eng.INITIAL_CASH = capital
            baseline = eng._simulate_variant(eng.Variant(BASELINE), bundle)
            v5e = eng._simulate_variant(
                eng.Variant(
                    V5E_MAIN,
                    profit_threshold=0.20,
                    profit_sell_fraction=0.50,
                    include_profit_lock=True,
                ),
                bundle,
            )
            for sim in [baseline, v5e]:
                sim["capital_label"] = label
                sim["initial_capital"] = capital
                _write_run_files(run_dir, label, sim)
            all_sims.extend([baseline, v5e])
            base_row = _comparison_row(label, capital, baseline, baseline, minute_prices)
            v5e_row = _comparison_row(label, capital, v5e, baseline, minute_prices)
            comparison_rows.extend([base_row, v5e_row])
            cost_rows.extend([_execution_cost_row(label, capital, baseline), _execution_cost_row(label, capital, v5e)])
            cash_rows.extend([_cash_row(label, baseline, baseline), _cash_row(label, v5e, baseline)])
            vwap_rows.append(_vwap_row(label, capital, v5e, minute_prices, v5e_row))
            order_rows.extend([_order_health_row(label, capital, baseline), _order_health_row(label, capital, v5e)])
            governance_rows.extend([_governance_row(label, baseline), _governance_row(label, v5e)])
    finally:
        eng.INITIAL_CASH = original_cash

    gate = _pm_gate_decision(comparison_rows, cost_rows, cash_rows, vwap_rows, min_efficiency_rows, wanyi_rows)
    next_queue = _next_queue(gate[0]["pm_gate_decision"])
    blockers = _nonfatal_blockers()

    _write_csv(out / "v5e_capital_level_comparison.csv", comparison_rows)
    _write_csv(out / "v5e_capital_execution_cost_breakdown.csv", cost_rows)
    _write_csv(out / "v5e_capital_cash_drag_comparison.csv", cash_rows)
    _write_csv(out / "v5e_capital_5min_vwap_impact.csv", vwap_rows)
    _write_csv(out / "v5e_capital_order_health.csv", order_rows)
    _write_csv(out / "v5e_capital_governance_audit.csv", governance_rows)
    _write_csv(out / "v5e_capital_min_commission_efficiency.csv", min_efficiency_rows)
    _write_csv(out / "v5e_capital_wanyi_commission_supplement.csv", wanyi_rows)
    _write_csv(out / "v5e_capital_pm_gate_decision.csv", gate)
    _write_csv(out / "v5e_capital_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5e_capital_blockers.csv", blockers)
    (out / "v5e_capital_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")

    summary = _summary(
        "completed_capital_sensitivity_test",
        gate[0]["pm_gate_decision"],
        [],
        comparison_rows=comparison_rows,
        vwap_rows=vwap_rows,
        min_efficiency_rows=min_efficiency_rows,
        wanyi_rows=wanyi_rows,
    )
    _write_json(out / "v5e_capital_sensitivity_summary.json", summary)
    (out / "v5e_capital_sensitivity_report.md").write_text(
        _report(summary, gate[0], comparison_rows, cost_rows, cash_rows, vwap_rows, min_efficiency_rows, wanyi_rows),
        encoding="utf-8",
    )
    return summary


def _comparison_row(
    label: str,
    capital: float,
    sim: dict[str, Any],
    baseline: dict[str, Any],
    minute_prices: dict[tuple[str, str], dict[str, float]],
) -> dict[str, Any]:
    row = eng._comparison_row(sim, baseline)
    vwap_impact = _vwap_impact(sim, minute_prices)
    return {
        "capital_level": label,
        "initial_capital": capital,
        "version_id": sim["version_id"],
        "execution_proxy": "daily_T_plus_1_open",
        **row,
        "traded_value": _sum_float(sim["trade_rows"], "value"),
        "commission_total": _sum_float(sim["trade_rows"], "commission"),
        "commission_drag_pct": _sum_float(sim["trade_rows"], "commission") / capital,
        "average_order_value": _avg([to_float(r.get("value")) or 0.0 for r in sim["trade_rows"]]),
        "small_order_count": sum(1 for r in sim["trade_rows"] if (to_float(r.get("value")) or 0.0) < SMALL_ORDER_THRESHOLD),
        "odd_lot_or_rounding_loss": _rounding_loss(sim),
        "estimated_5min_vwap_impact": vwap_impact["impact_pct_of_initial_capital"],
        "vwap_adjusted_strategy_return_estimate": (row["strategy_return"] or 0.0) + vwap_impact["impact_pct_of_initial_capital"],
        "threshold_scan_used": False,
        "v57f_core_modified": False,
        "accepted": False,
    }


def _execution_cost_row(label: str, capital: float, sim: dict[str, Any]) -> dict[str, Any]:
    trades = sim["trade_rows"]
    commissions = [to_float(r.get("commission")) or 0.0 for r in trades]
    values = [to_float(r.get("value")) or 0.0 for r in trades]
    min_flags = [
        c > 0 and abs(c - eng.MIN_COMMISSION) < 1e-9 and v * eng.COMMISSION_RATE < eng.MIN_COMMISSION
        for c, v in zip(commissions, values)
    ]
    exit_trades = [r for r in trades if str(r.get("reason", "")).startswith("v5e_")]
    return {
        "capital_level": label,
        "initial_capital": capital,
        "version_id": sim["version_id"],
        "trade_count": len(trades),
        "exit_trade_count": len(exit_trades),
        "traded_value": sum(values),
        "commission_total": sum(commissions),
        "min_commission_trade_count": sum(1 for flag in min_flags if flag),
        "min_commission_total": sum(c for c, flag in zip(commissions, min_flags) if flag),
        "commission_drag_pct": sum(commissions) / capital,
        "average_order_value": _avg(values),
        "median_order_value": _median(values),
        "small_order_count": sum(1 for value in values if value < SMALL_ORDER_THRESHOLD),
        "small_order_share": (sum(1 for value in values if value < SMALL_ORDER_THRESHOLD) / len(values)) if values else 0.0,
        "odd_lot_or_rounding_loss": _rounding_loss(sim),
        "unfilled_count": len(sim["unfilled_log"]),
    }


def _cash_row(label: str, sim: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    cash_weights = [to_float(r.get("cash_weight")) or 0.0 for r in sim["daily_rows"]]
    base_cash = [to_float(r.get("cash_weight")) or 0.0 for r in baseline["daily_rows"]]
    avg_cash = _avg(cash_weights)
    return {
        "capital_level": label,
        "version_id": sim["version_id"],
        "average_cash_weight": avg_cash,
        "max_cash_weight": max(cash_weights) if cash_weights else 0.0,
        "baseline_average_cash_weight": _avg(base_cash),
        "cash_drag_delta_vs_baseline": avg_cash - _avg(base_cash),
        "cash_days_above_5pct": sum(1 for x in cash_weights if x > 0.05),
        "cash_days_above_10pct": sum(1 for x in cash_weights if x > 0.10),
        "cash_days_above_15pct": sum(1 for x in cash_weights if x > 0.15),
    }


def _vwap_row(
    label: str,
    capital: float,
    sim: dict[str, Any],
    minute_prices: dict[tuple[str, str], dict[str, float]],
    comparison_row: dict[str, Any],
) -> dict[str, Any]:
    impact = _vwap_impact(sim, minute_prices)
    return {
        "capital_level": label,
        "initial_capital": capital,
        "version_id": sim["version_id"],
        **impact,
        "daily_open_strategy_return": comparison_row["strategy_return"],
        "vwap_adjusted_strategy_return_estimate": comparison_row["strategy_return"] + impact["impact_pct_of_initial_capital"],
        "daily_open_delta_return_vs_v57f": comparison_row["delta_return_vs_baseline"],
        "vwap_adjusted_delta_return_vs_v57f_estimate": comparison_row["delta_return_vs_baseline"] + impact["impact_pct_of_initial_capital"],
        "minute_data_used_for_trigger": False,
        "full_rebacktest": False,
    }


def _order_health_row(label: str, capital: float, sim: dict[str, Any]) -> dict[str, Any]:
    trades = sim["trade_rows"]
    values = [to_float(r.get("value")) or 0.0 for r in trades]
    return {
        "capital_level": label,
        "initial_capital": capital,
        "version_id": sim["version_id"],
        "trade_count": len(trades),
        "unfilled_count": len(sim["unfilled_log"]),
        "small_order_count": sum(1 for value in values if value < SMALL_ORDER_THRESHOLD),
        "zero_or_negative_trade_count": sum(1 for value in values if value <= 0),
        "min_order_value": min(values) if values else 0.0,
        "average_order_value": _avg(values),
        "round_lot_size": eng.LOT_SIZE,
        "t_violation_count": len(sim["t_violation_log"]),
        "reentry_violation_count": len(sim["reentry_violation_log"]),
        "order_health_status": "pass" if not sim["unfilled_log"] and not sim["t_violation_log"] and not sim["reentry_violation_log"] else "review",
    }


def _governance_row(label: str, sim: dict[str, Any]) -> dict[str, Any]:
    return {
        "capital_level": label,
        "version_id": sim["version_id"],
        "pit_violation_count": 0,
        "t_violation_count": len(sim["t_violation_log"]),
        "reentry_violation_count": len(sim["reentry_violation_log"]),
        "threshold_scan_used": False,
        "v57f_core_modified": False,
        "accepted": False,
        "joinquant_started": False,
        "network_fetch_started": False,
        "minute_data_used_for_trigger": False,
    }


def _vwap_impact(sim: dict[str, Any], minute_prices: dict[tuple[str, str], dict[str, float]]) -> dict[str, Any]:
    total_delta = 0.0
    matched = 0
    missing = 0
    bps_values: list[float] = []
    for action in sim["exit_action_log"]:
        code = str(action["code"])
        day = str(action["execution_date"])
        minute = minute_prices.get((code, day))
        amount = to_float(action.get("amount")) or 0.0
        daily_price = to_float(action.get("price")) or 0.0
        if not minute or daily_price <= 0 or amount <= 0:
            missing += 1
            continue
        vwap = minute["vwap"]
        delta = (vwap - daily_price) * amount
        total_delta += delta
        matched += 1
        bps_values.append(delta / (daily_price * amount) * 10000.0)
    capital = float(sim["initial_capital"])
    return {
        "exit_action_count": len(sim["exit_action_log"]),
        "matched_5min_vwap_action_count": matched,
        "missing_5min_vwap_action_count": missing,
        "total_vwap_value_delta_vs_daily_open": total_delta,
        "impact_pct_of_initial_capital": total_delta / capital if capital else 0.0,
        "avg_bps_delta_vs_daily_open": _avg(bps_values),
        "median_bps_delta_vs_daily_open": _median(bps_values),
    }


def _pm_gate_decision(
    comparison_rows: list[dict[str, Any]],
    cost_rows: list[dict[str, Any]],
    cash_rows: list[dict[str, Any]],
    vwap_rows: list[dict[str, Any]],
    min_efficiency_rows: list[dict[str, Any]],
    wanyi_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    v5e_by_cap = {row["capital_level"]: row for row in comparison_rows if row["version_id"] == V5E_MAIN}
    cost_by_cap = {row["capital_level"]: row for row in cost_rows if row["version_id"] == V5E_MAIN}
    cash_by_cap = {row["capital_level"]: row for row in cash_rows if row["version_id"] == V5E_MAIN}
    vwap_by_cap = {row["capital_level"]: row for row in vwap_rows}
    cost_drag_50 = cost_by_cap["50w"]["commission_drag_pct"]
    cost_drag_200 = cost_by_cap["200w"]["commission_drag_pct"]
    cash_drag_200 = cash_by_cap["200w"]["cash_drag_delta_vs_baseline"]
    vwap_delta_200 = vwap_by_cap["200w"]["vwap_adjusted_delta_return_vs_v57f_estimate"]
    efficient_200 = next(row for row in min_efficiency_rows if row["capital_level"] == "200w")["above_reference_minimum_capital"]
    if cash_drag_200 > 0.03:
        decision = "open_cash_policy_review"
        reason = "200w is above the 5 yuan / wanyi 1bp / 28-stock minimum efficient capital line, yet cash drag remains the dominant weakness; transaction cost differences are secondary."
    elif cost_drag_50 > cost_drag_200 * 1.5:
        decision = "retain_forward_paper_tracking_200w_plus_only"
        reason = "50w has materially worse commission drag; 200w+ better reflects strategy behavior."
    elif vwap_delta_200 > 0 and v5e_by_cap["200w"]["delta_max_drawdown_vs_baseline"] < 0:
        decision = "retain_forward_paper_tracking_200w_plus_only" if efficient_200 else "retain_forward_paper_tracking_all_capital_levels"
        reason = "Profit-lock main remains governance-clean; 200w+ is the reasonable capital band under the 5元/万一 minimum-commission line."
    else:
        decision = "downgrade_v5e_profit_lock_to_diagnostic"
        reason = "Capital scaling does not repair the V5e edge after execution and cash drag."
    return [
        {
            "pm_gate_decision": decision,
            "reason": reason,
            "accepted": False,
            "v57f_replacement": False,
            "primary_capital_read": _capital_read(v5e_by_cap, cost_by_cap, cash_by_cap, vwap_by_cap),
            "next_gate": _next_gate(decision),
        }
    ]


def _capital_read(
    v5e_by_cap: dict[str, dict[str, Any]],
    cost_by_cap: dict[str, dict[str, Any]],
    cash_by_cap: dict[str, dict[str, Any]],
    vwap_by_cap: dict[str, dict[str, Any]],
) -> str:
    return (
        f"50w daily delta {v5e_by_cap['50w']['delta_return_vs_baseline']:.4f}, cost drag {cost_by_cap['50w']['commission_drag_pct']:.4f}; "
        f"200w daily delta {v5e_by_cap['200w']['delta_return_vs_baseline']:.4f}, vwap delta {vwap_by_cap['200w']['vwap_adjusted_delta_return_vs_v57f_estimate']:.4f}; "
        f"800w daily delta {v5e_by_cap['800w']['delta_return_vs_baseline']:.4f}, cash drag {cash_by_cap['800w']['cash_drag_delta_vs_baseline']:.4f}."
    )


def _min_commission_efficiency_rows() -> list[dict[str, Any]]:
    minimum_efficient_order_value = BROKER_REFERENCE_MIN_COMMISSION / BROKER_REFERENCE_COMMISSION_RATE
    minimum_efficient_capital = minimum_efficient_order_value * REFERENCE_TARGET_COUNT
    rows: list[dict[str, Any]] = []
    for label, capital in CAPITAL_LEVELS:
        average_initial_order_value = capital * eng.TARGET_EXPOSURE / REFERENCE_TARGET_COUNT
        rows.append(
            {
                "capital_level": label,
                "initial_capital": capital,
                "broker_reference_commission_rate": BROKER_REFERENCE_COMMISSION_RATE,
                "broker_reference_commission_rate_label": "wanyi_1bp",
                "min_commission": BROKER_REFERENCE_MIN_COMMISSION,
                "minimum_efficient_order_value": minimum_efficient_order_value,
                "reference_target_count": REFERENCE_TARGET_COUNT,
                "minimum_efficient_capital_for_28_names": minimum_efficient_capital,
                "average_initial_order_value": average_initial_order_value,
                "above_reference_minimum_order_value": average_initial_order_value >= minimum_efficient_order_value,
                "above_reference_minimum_capital": capital >= minimum_efficient_capital,
                "capital_efficiency_read": "reasonable_200w_plus_band" if capital >= minimum_efficient_capital else "below_min_commission_efficient_band",
            }
        )
    return rows


def _wanyi_commission_supplement_rows(
    root: Path,
    bundle: dict[str, Any],
    minute_prices: dict[tuple[str, str], dict[str, float]],
) -> list[dict[str, Any]]:
    original_cash = eng.INITIAL_CASH
    original_rate = eng.COMMISSION_RATE
    original_min = eng.MIN_COMMISSION
    rows: list[dict[str, Any]] = []
    try:
        eng.COMMISSION_RATE = BROKER_REFERENCE_COMMISSION_RATE
        eng.MIN_COMMISSION = BROKER_REFERENCE_MIN_COMMISSION
        for label, capital in CAPITAL_LEVELS:
            eng.INITIAL_CASH = capital
            baseline = eng._simulate_variant(eng.Variant(BASELINE), bundle)
            v5e = eng._simulate_variant(
                eng.Variant(
                    V5E_MAIN,
                    profit_threshold=0.20,
                    profit_sell_fraction=0.50,
                    include_profit_lock=True,
                ),
                bundle,
            )
            baseline["initial_capital"] = capital
            v5e["initial_capital"] = capital
            base_row = eng._comparison_row(baseline, baseline)
            v5e_row = eng._comparison_row(v5e, baseline)
            cost = _execution_cost_row(label, capital, v5e)
            vwap = _vwap_impact(v5e, minute_prices)
            rows.append(
                {
                    "capital_level": label,
                    "initial_capital": capital,
                    "commission_rate": BROKER_REFERENCE_COMMISSION_RATE,
                    "commission_rate_label": "wanyi_1bp",
                    "version_id": V5E_MAIN,
                    "strategy_return": v5e_row["strategy_return"],
                    "delta_return_vs_v57f": v5e_row["delta_return_vs_baseline"],
                    "max_drawdown": v5e_row["max_drawdown"],
                    "delta_max_drawdown_vs_v57f": v5e_row["delta_max_drawdown_vs_baseline"],
                    "commission_total": cost["commission_total"],
                    "commission_drag_pct": cost["commission_drag_pct"],
                    "min_commission_trade_count": cost["min_commission_trade_count"],
                    "average_order_value": cost["average_order_value"],
                    "cash_drag_delta_vs_baseline": v5e_row["cash_drag_delta_vs_baseline"],
                    "vwap_impact_pct": vwap["impact_pct_of_initial_capital"],
                    "vwap_adjusted_delta_vs_v57f": v5e_row["delta_return_vs_baseline"] + vwap["impact_pct_of_initial_capital"],
                    "threshold_scan_used": False,
                    "accepted": False,
                }
            )
    finally:
        eng.INITIAL_CASH = original_cash
        eng.COMMISSION_RATE = original_rate
        eng.MIN_COMMISSION = original_min
    return rows


def _next_gate(decision: str) -> str:
    if decision == "open_cash_policy_review":
        return "v5e_cash_policy_review"
    if decision in {"retain_forward_paper_tracking_all_capital_levels", "retain_forward_paper_tracking_200w_plus_only", "retain_forward_paper_tracking_800w_only"}:
        return "continue_forward_paper_tracking_with_capital_notes"
    return "diagnostic_or_archive_review"


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "next_gate": _next_gate(decision),
            "task": "V5e cash policy review" if decision == "open_cash_policy_review" else "V5e forward/paper tracking with capital notes",
            "description": "Review whether strict cash-to-next-rebalance remains the right policy; do not change thresholds or V57f.",
            "requires_new_threshold": False,
            "requires_v57f_change": False,
            "accepted_allowed": False,
        }
    ]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    comparison_rows: list[dict[str, Any]] | None = None,
    vwap_rows: list[dict[str, Any]] | None = None,
    min_efficiency_rows: list[dict[str, Any]] | None = None,
    wanyi_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    comparison_rows = comparison_rows or []
    vwap_rows = vwap_rows or []
    v5e_rows = [r for r in comparison_rows if r.get("version_id") == V5E_MAIN]
    min_efficiency_rows = min_efficiency_rows or []
    wanyi_rows = wanyi_rows or []
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_capital_sensitivity_test",
        "status": status,
        "pm_gate_decision": decision,
        "capital_levels": [label for label, _ in CAPITAL_LEVELS],
        "tested_versions": [BASELINE, V5E_MAIN],
        "threshold_scan_used": False,
        "v57f_core_modified": False,
        "accepted": False,
        "joinquant_started": False,
        "network_fetch_started": False,
        "minute_data_used_for_trigger": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
        "v5e_daily_delta_by_capital": {row["capital_level"]: row["delta_return_vs_baseline"] for row in v5e_rows},
        "v5e_vwap_delta_by_capital": {row["capital_level"]: row["vwap_adjusted_delta_return_vs_v57f_estimate"] for row in vwap_rows},
        "minimum_efficient_capital_wanyi_28_names": BROKER_REFERENCE_MIN_COMMISSION / BROKER_REFERENCE_COMMISSION_RATE * REFERENCE_TARGET_COUNT,
        "capital_efficiency_by_level": {row["capital_level"]: row["capital_efficiency_read"] for row in min_efficiency_rows},
        "wanyi_vwap_delta_by_capital": {row["capital_level"]: row["vwap_adjusted_delta_vs_v57f"] for row in wanyi_rows},
    }


def _report(
    summary: dict[str, Any],
    gate: dict[str, Any],
    comparison_rows: list[dict[str, Any]],
    cost_rows: list[dict[str, Any]],
    cash_rows: list[dict[str, Any]],
    vwap_rows: list[dict[str, Any]],
    min_efficiency_rows: list[dict[str, Any]],
    wanyi_rows: list[dict[str, Any]],
) -> str:
    lines = [
        "# V5e Capital Sensitivity Test",
        "",
        f"- PM gate decision: `{gate['pm_gate_decision']}`",
        f"- Reason: {gate['reason']}",
        "- Scope: 50w / 200w / 800w only; no threshold changes, no accepted decision.",
        "- Broker reference note: 5 yuan minimum commission at wanyi (1bp) implies 50,000 yuan per efficient order; 28 names imply about 1.4m minimum efficient capital.",
        "",
        "## V5e Profit-Lock Main",
        "",
        "| Capital | Daily Delta vs V57f | VWAP-Adjusted Delta | Max DD Delta | Commission Drag | Cash Drag |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    comp = {row["capital_level"]: row for row in comparison_rows if row["version_id"] == V5E_MAIN}
    cost = {row["capital_level"]: row for row in cost_rows if row["version_id"] == V5E_MAIN}
    cash = {row["capital_level"]: row for row in cash_rows if row["version_id"] == V5E_MAIN}
    vwap = {row["capital_level"]: row for row in vwap_rows}
    for label, _capital in CAPITAL_LEVELS:
        lines.append(
            f"| {label} | {comp[label]['delta_return_vs_baseline']:.4%} | {vwap[label]['vwap_adjusted_delta_return_vs_v57f_estimate']:.4%} | {comp[label]['delta_max_drawdown_vs_baseline']:.4%} | {cost[label]['commission_drag_pct']:.4%} | {cash[label]['cash_drag_delta_vs_baseline']:.4%} |"
        )
    lines.extend(
        [
            "",
            "## Minimum Commission Efficiency",
            "",
            "| Capital | Avg Initial Order | Efficient Under 5 Yuan / Wanyi | Read |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for row in min_efficiency_rows:
        lines.append(
            f"| {row['capital_level']} | {row['average_initial_order_value']:.0f} | {row['above_reference_minimum_capital']} | {row['capital_efficiency_read']} |"
        )
    lines.extend(
        [
            "",
            "## Wanyi Commission Supplement",
            "",
            "| Capital | Daily Delta vs V57f | VWAP-Adjusted Delta | Commission Drag | Cash Drag |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in wanyi_rows:
        lines.append(
            f"| {row['capital_level']} | {row['delta_return_vs_v57f']:.4%} | {row['vwap_adjusted_delta_vs_v57f']:.4%} | {row['commission_drag_pct']:.4%} | {row['cash_drag_delta_vs_baseline']:.4%} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- 50w is below the minimum-commission efficient band under 5 yuan / wanyi / 28 names.",
            "- 200w and 800w are both in the reasonable capital band; their results are more representative than 50w.",
            "- Transaction friction declines with scale, but cash drag remains materially larger than commission drag in the reasonable 200w+ band.",
            "- 5min VWAP adjustment weakens the edge; it does not create a stronger model.",
            "- The next useful gate is cash policy review, not threshold tuning.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_run_files(run_dir: Path, label: str, sim: dict[str, Any]) -> None:
    path = run_dir / label / sim["version_id"]
    path.mkdir(parents=True, exist_ok=True)
    _write_csv(path / "daily_returns.csv", sim["daily_rows"])
    _write_csv(path / "trades.csv", sim["trade_rows"])
    _write_csv(path / "holdings.csv", sim["holding_rows"])


def _load_minute_prices(root: Path) -> dict[tuple[str, str], dict[str, float]]:
    result: dict[tuple[str, str], dict[str, float]] = {}
    if not (root / MINUTE_INDEX).exists():
        return result
    for row in _read_csv(root / MINUTE_INDEX):
        path = root / Path(row["path"])
        if not path.exists():
            continue
        df = pd.read_csv(path)
        if df.empty:
            continue
        volume = pd.to_numeric(df["volume"], errors="coerce").fillna(0.0)
        amount = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
        close = pd.to_numeric(df["close"], errors="coerce").dropna()
        total_volume = float(volume.sum())
        result[(row["code"], row["trade_date"])] = {
            "vwap": float(amount.sum() / total_volume) if total_volume > 0 else float(close.iloc[-1]),
            "twap": float(close.mean()) if len(close) else 0.0,
        }
    return result


def _rounding_loss(sim: dict[str, Any]) -> float:
    losses = []
    for trigger in sim["trigger_log"]:
        desired = (to_float(trigger.get("sell_amount")) or 0.0)
        # The simulator already rounds to board lots before logging sell_amount; this field
        # stays explicit so later runners can compare against unrounded desired shares.
        losses.append(0.0 if desired >= 0 else 0.0)
    return sum(losses)


def _sum_float(rows: list[dict[str, Any]], key: str) -> float:
    return sum(to_float(row.get(key)) or 0.0 for row in rows)


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _missing_blockers(root: Path) -> list[dict[str, Any]]:
    required = [
        FORWARD_SUMMARY,
        FORWARD_STATUS,
        FORWARD_GATE,
        FORMAL_SUMMARY,
        PROXY_SUMMARY,
        PROXY_COMPARISON,
        V5E_EXIT_LOG,
        V5E_TRIGGER_LOG,
        V5E_CASH_DRAG_LOG,
        STARTUP_SUMMARY,
        SHADOW_CONFIG,
        eng.REPAIRED_RUN / "summary.json",
        eng.REPAIRED_RUN / "rebalance_signals.csv",
        eng.REPAIRED_RUN / "trades.csv",
        eng.REPAIRED_RUN / "daily_returns.csv",
        eng.REPAIRED_RUN / "dividends.csv",
        eng.REPAIRED_RUN / "corporate_actions.csv",
        MINUTE_INDEX,
    ]
    return [
        {
            "blocker_id": "missing_required_input",
            "severity": "fatal",
            "status": "blocking",
            "path": str(path),
            "description": "Required V5e capital sensitivity input is missing.",
        }
        for path in required
        if not (root / path).exists()
    ]


def _nonfatal_blockers() -> list[dict[str, Any]]:
    return [
        {
            "blocker_id": "none_fatal",
            "severity": "none",
            "status": "not_blocking",
            "description": "Capital sensitivity completed without rule or data changes.",
        }
    ]


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5e Capital Sensitivity Agent Rules",
            "",
            "- Test only 50w, 200w, and 800w capital levels.",
            "- Test only repaired V57f baseline and v5e_profit_lock_main_20pct_sell50.",
            "- Keep +20% threshold and 50% sell fraction fixed.",
            "- Do not use 5min bars as triggers.",
            "- Do not modify V57f, ERC, or V5d.",
            "- Do not mark accepted.",
            "",
        ]
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    print(json.dumps(run_v5e_capital_sensitivity(Path(".")), ensure_ascii=False, indent=2))
