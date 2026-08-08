from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5d_order_scheduling_policy_spec") / "current"
ENGINEERING_WINDOW_START = "2021-05-01"
ENGINEERING_WINDOW_END = "2026-05-31"

REQUIRED = [
    Path("v5d_baostock_5min_data_gate/current/v5d_baostock_5min_data_gate_summary.json"),
    Path("v5d_minute_execution_robustness/current/v5d_minute_execution_robustness_summary.json"),
    Path("v5d_minute_execution_robustness/current/v5d_execution_proxy_comparison.csv"),
    Path("v5d_minute_execution_robustness/current/v5d_execution_order_health.csv"),
    Path("local_daily_backtests_v57f_etf/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f/trades.csv"),
    Path("local_daily_backtests_v57f_etf/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f/rebalance_order_health.csv"),
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_specs() -> list[dict[str, Any]]:
    return [
        {
            "rule_id": "V5D_OS_001",
            "rule_name": "sell_first_then_buy",
            "allowed_for_engineering": True,
            "objective": "Release cash and reduce buy failures caused by insufficient cash.",
            "order_scope": "rebalance_day_delta_orders",
            "schedule": "sells in early window before buys",
            "allowed_windows": "09:35;09:40;10:00",
            "blocked_behavior": "Do not delay sells based on intraday price view.",
            "order_health_fields": "sell_attempted;sell_filled;sell_blocked;cash_released;buy_cash_shortfall",
        },
        {
            "rule_id": "V5D_OS_002",
            "rule_name": "multi_window_buy_schedule",
            "allowed_for_engineering": True,
            "objective": "Give buy orders multiple non-predictive fill opportunities.",
            "order_scope": "new_or_increased_target_positions",
            "schedule": "default 40% 09:40, 30% 10:00, 20% 13:30, 10% 14:30/14:55",
            "allowed_windows": "09:40;10:00;13:30;14:30;14:55",
            "blocked_behavior": "Do not change buy list or weights based on intraday return.",
            "order_health_fields": "buy_slice_id;buy_attempted;buy_filled;buy_unfilled;cash_available",
        },
        {
            "rule_id": "V5D_OS_003",
            "rule_name": "multi_window_sell_schedule",
            "allowed_for_engineering": True,
            "objective": "Give sell orders multiple fill opportunities without creating intraday T.",
            "order_scope": "reduced_or_exit_positions",
            "schedule": "default 50% 09:35, 25% 09:40, 25% 10:00; retry blocked at 13:30/14:30",
            "allowed_windows": "09:35;09:40;10:00;13:30;14:30",
            "blocked_behavior": "Do not sell later because price looks better; later windows are only for unfilled or scheduled slices.",
            "order_health_fields": "sell_slice_id;sell_attempted;sell_filled;sell_unfilled;block_reason",
        },
        {
            "rule_id": "V5D_OS_004",
            "rule_name": "large_order_twap",
            "allowed_for_engineering": True,
            "objective": "Reduce single-price assumption for large target value changes.",
            "order_scope": "orders_above_value_or_position_threshold",
            "schedule": "equal slices across available fixed windows",
            "allowed_windows": "09:40;10:00;13:30;14:30;14:55",
            "blocked_behavior": "Do not optimize TWAP windows by historical return.",
            "order_health_fields": "slice_count;slice_target_value;slice_fill_value;avg_fill_proxy",
        },
        {
            "rule_id": "V5D_OS_005",
            "rule_name": "small_existing_position_diff_filter",
            "allowed_for_engineering": True,
            "objective": "Avoid churn and minimum-commission drag from tiny target deltas.",
            "order_scope": "existing_positions_only",
            "schedule": "filter before order slicing",
            "allowed_windows": "not_applicable",
            "blocked_behavior": "Do not filter new buys, full exits, risk-off sells, or blocked retry cleanup.",
            "order_health_fields": "filtered_reason;estimated_commission_saving;target_delta_value",
        },
        {
            "rule_id": "V5D_OS_006",
            "rule_name": "same_day_retry_for_unfilled_orders",
            "allowed_for_engineering": True,
            "objective": "Retry only mechanical non-fills caused by停牌/涨跌停/no bar/cash availability.",
            "order_scope": "unfilled_rebalance_orders",
            "schedule": "next scheduled retry window on same day",
            "allowed_windows": "10:00;13:30;14:30;14:55",
            "blocked_behavior": "Do not retry because price moved favorably or unfavorably.",
            "order_health_fields": "retry_count;retry_reason;final_unfilled_status",
        },
        {
            "rule_id": "V5D_OS_007",
            "rule_name": "stop_at_close_and_log_unfilled",
            "allowed_for_engineering": True,
            "objective": "Prevent hidden fills and preserve auditability.",
            "order_scope": "all_unfilled_orders_after_last_window",
            "schedule": "stop after 14:55/last available bar",
            "allowed_windows": "14:55;last_bar",
            "blocked_behavior": "Do not fabricate fills after close.",
            "order_health_fields": "unfilled_amount;unfilled_value;final_block_reason;carry_policy",
        },
        {
            "rule_id": "V5D_OS_008",
            "rule_name": "no_intraday_T_policy",
            "allowed_for_engineering": True,
            "objective": "Keep V5d as execution scheduling, not intraday alpha.",
            "order_scope": "all_orders",
            "schedule": "governance rule",
            "allowed_windows": "not_applicable",
            "blocked_behavior": "No same-day reversal, no bottom-fishing, no high-sell-low-buy based on intraday price.",
            "order_health_fields": "t_trade_violation_flag",
        },
    ]


def build_window_plan() -> list[dict[str, Any]]:
    return [
        {"window_id": "W1", "time": "09:35", "primary_use": "early sell slice and urgent exit retry check", "buy_allowed": False, "sell_allowed": True, "retry_allowed": False, "notes": "Avoid opening auction noise; first 5min executable proxy."},
        {"window_id": "W2", "time": "09:40", "primary_use": "first buy slice after initial sells", "buy_allowed": True, "sell_allowed": True, "retry_allowed": True, "notes": "Main early execution window."},
        {"window_id": "W3", "time": "10:00", "primary_use": "second scheduled slice and retry", "buy_allowed": True, "sell_allowed": True, "retry_allowed": True, "notes": "Reduces dependence on open price."},
        {"window_id": "W4", "time": "13:30", "primary_use": "post-lunch retry and remaining TWAP slice", "buy_allowed": True, "sell_allowed": True, "retry_allowed": True, "notes": "No price prediction; scheduled/retry only."},
        {"window_id": "W5", "time": "14:30", "primary_use": "late remaining slice", "buy_allowed": True, "sell_allowed": True, "retry_allowed": True, "notes": "Avoid last-minute concentration."},
        {"window_id": "W6", "time": "14:55", "primary_use": "final attempt and unfilled logging", "buy_allowed": True, "sell_allowed": False, "retry_allowed": True, "notes": "Final audit window, not optimization target."},
    ]


def build_priority_rules() -> list[dict[str, Any]]:
    return [
        {"priority": 1, "rule": "compute_net_delta_first", "description": "Calculate target amount minus current amount once per rebalance; no repeated buy/sell in same code."},
        {"priority": 2, "rule": "sell_reductions_before_buys", "description": "Execute reductions/exits first to release cash before new/increased buys."},
        {"priority": 3, "rule": "protect_full_exit", "description": "Full exits are never blocked by small-diff filter."},
        {"priority": 4, "rule": "cash_available_buy_queue", "description": "Buy slices use released cash plus existing cash; cash shortfall is logged, not hidden."},
        {"priority": 5, "rule": "same_sleeve_no_cross_trade_loop", "description": "Within a sleeve, execute net deltas only; do not churn names already near target."},
    ]


def build_retry_policy() -> list[dict[str, Any]]:
    return [
        {"trigger": "paused", "same_day_retry": False, "carry_after_close": "log_unfilled_pm_review", "notes": "停牌 cannot be forced."},
        {"trigger": "buy_at_high_limit", "same_day_retry": True, "carry_after_close": "do_not_fill_log_unfilled", "notes": "Retry only if later bar becomes tradeable."},
        {"trigger": "sell_at_low_limit", "same_day_retry": True, "carry_after_close": "do_not_fill_log_unfilled", "notes": "Retry only if later bar becomes tradeable."},
        {"trigger": "missing_5min_bar", "same_day_retry": True, "carry_after_close": "fallback_for_diagnostic_only_log_data_issue", "notes": "No synthetic fill."},
        {"trigger": "cash_shortfall_after_sells", "same_day_retry": True, "carry_after_close": "partial_fill_log_cash_shortfall", "notes": "Retry after sell proceeds are available."},
    ]


def build_small_filter() -> list[dict[str, Any]]:
    return [
        {"filter_id": "small_diff_value_floor", "scope": "existing_positions_only", "candidate_threshold": "max(1 lot value, estimated_min_commission_drag band)", "allowed_engineering": True, "blocked_scope": "new_position;full_exit;position_zero;blocked_retry"},
        {"filter_id": "small_diff_weight_floor", "scope": "existing_positions_only", "candidate_threshold": "pre_registered small weight delta; not optimized by return", "allowed_engineering": True, "blocked_scope": "do_not_scan_thresholds"},
    ]


def build_allowed_blocked() -> list[dict[str, Any]]:
    return [
        {"action": "sell_first_then_buy_engineering", "status": "allowed", "reason": "cash/order-health improvement"},
        {"action": "multi_window_order_scheduling_engineering", "status": "allowed", "reason": "execution robustness, no alpha timing"},
        {"action": "large_order_twap_engineering", "status": "allowed", "reason": "reduce single point execution assumption"},
        {"action": "small_existing_diff_filter_spec", "status": "allowed", "reason": "reduce churn; thresholds must be pre-registered"},
        {"action": "modify_v57f", "status": "blocked", "reason": "frozen mainline"},
        {"action": "modify_erc_candidate_logic", "status": "blocked", "reason": "ERC is not accepted or replacement"},
        {"action": "intraday_T", "status": "blocked", "reason": "outside V5d mainline"},
        {"action": "choose_best_window_by_historical_return", "status": "blocked", "reason": "would be minute timing optimization"},
        {"action": "start_joinquant", "status": "blocked", "reason": "not needed for spec"},
    ]


def run() -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    blockers = [{"path": str(p), "reason": "missing_required_input"} for p in REQUIRED if not p.exists()]
    if blockers:
        write_csv(OUT_DIR / "v5d_allowed_blocked_actions.csv", build_allowed_blocked())
        summary = {"schema_version": 1, "project": "v5d_order_scheduling_policy_spec", "status": "blocked_missing_inputs", "blockers": blockers, "created_at_utc": now_utc()}
        (OUT_DIR / "v5d_order_scheduling_policy_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        return summary

    data_gate = read_json(REQUIRED[0])
    robustness = read_json(REQUIRED[1])
    comp = pd.read_csv(REQUIRED[2])
    max_same_day_delta = float(
        comp[(comp["execution_proxy"] != "daily_open") & (comp["execution_proxy"] != "next_day_open")]["delta_return_vs_daily_open"].abs().max()
    )
    max_next_day_delta = float(comp[comp["execution_proxy"] == "next_day_open"]["delta_return_vs_daily_open"].abs().max())

    specs = build_specs()
    write_csv(OUT_DIR / "v5d_order_scheduling_rule_specs.csv", specs)
    write_csv(OUT_DIR / "v5d_order_window_plan.csv", build_window_plan())
    write_csv(OUT_DIR / "v5d_buy_sell_priority_rules.csv", build_priority_rules())
    write_csv(OUT_DIR / "v5d_retry_and_unfilled_policy.csv", build_retry_policy())
    write_csv(OUT_DIR / "v5d_small_diff_trade_filter_spec.csv", build_small_filter())
    write_csv(OUT_DIR / "v5d_allowed_blocked_actions.csv", build_allowed_blocked())
    next_queue = [
        {
            "priority": 1,
            "agent": "V5d Engineering Agent",
            "task": "order_scheduling_engineering_test",
            "allowed_to_start": True,
            "input_data": "BaoStock 5min standardized bars; V57f and ERC fixed rebalance signals",
            "must_not_do": "no return-based window selection; no intraday T; no V57f/ERC modification",
        }
    ]
    write_csv(OUT_DIR / "v5d_next_engineering_queue.csv", next_queue)

    summary = {
        "schema_version": 1,
        "project": "v5d_order_scheduling_policy_spec",
        "status": "spec_completed_ready_for_engineering",
        "created_at_utc": now_utc(),
        "local_engineering_window": {"start_date": ENGINEERING_WINDOW_START, "end_date": ENGINEERING_WINDOW_END},
        "v57f_core_modified": False,
        "erc_modified": False,
        "joinquant_started": False,
        "intraday_T_allowed": False,
        "data_gate_status": data_gate.get("status"),
        "robustness_status": robustness.get("status"),
        "same_day_execution_sensitivity_abs_max": max_same_day_delta,
        "next_day_open_sensitivity_abs_max": max_next_day_delta,
        "paid_1m_data_still_useful": True,
        "rule_count": len(specs),
        "engineering_allowed_rules": [row["rule_name"] for row in specs if row["allowed_for_engineering"]],
        "outputs": {
            "summary": str(OUT_DIR / "v5d_order_scheduling_policy_summary.json"),
            "report": str(OUT_DIR / "v5d_order_scheduling_policy_report.md"),
            "rule_specs": str(OUT_DIR / "v5d_order_scheduling_rule_specs.csv"),
            "window_plan": str(OUT_DIR / "v5d_order_window_plan.csv"),
            "priority_rules": str(OUT_DIR / "v5d_buy_sell_priority_rules.csv"),
            "retry_policy": str(OUT_DIR / "v5d_retry_and_unfilled_policy.csv"),
            "small_filter": str(OUT_DIR / "v5d_small_diff_trade_filter_spec.csv"),
            "allowed_blocked": str(OUT_DIR / "v5d_allowed_blocked_actions.csv"),
            "next_queue": str(OUT_DIR / "v5d_next_engineering_queue.csv"),
        },
    }
    (OUT_DIR / "v5d_order_scheduling_policy_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "v5d_order_scheduling_policy_report.md").write_text(build_report(summary, specs), encoding="utf-8")
    return summary


def build_report(summary: dict[str, Any], specs: list[dict[str, Any]]) -> str:
    lines = [
        "# V5d Order Scheduling Execution Policy Spec",
        "",
        f"- Status: `{summary['status']}`",
        f"- Local engineering window: {ENGINEERING_WINDOW_START} to {ENGINEERING_WINDOW_END}",
        "- Scope: L2 order scheduling, not L1 fixed minute proxy and not L3 intraday T.",
        "- V57f and ERC are unchanged.",
        "",
        "## Why This Spec",
        "",
        f"- Same-day 5min proxy sensitivity max abs delta: {summary['same_day_execution_sensitivity_abs_max']:.2%}",
        f"- Next-day-open sensitivity max abs delta: {summary['next_day_open_sensitivity_abs_max']:.2%}",
        "- The goal is order health and execution robustness, not choosing the highest-return historical window.",
        "",
        "## Rules",
    ]
    for row in specs:
        lines.append(f"- `{row['rule_name']}`: {row['objective']}")
    lines.extend(
        [
            "",
            "## Engineering Gate",
            "",
            "`order_scheduling_engineering_test` may start with fixed windows and pre-registered rules.",
            "",
            "## Blocked",
            "",
            "- No V57f modification.",
            "- No ERC replacement/accepted conclusion.",
            "- No intraday T.",
            "- No selecting best minute window by historical return.",
            "- No JoinQuant in this spec task.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
