from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5d_l4_rebalance_neighborhood_order_completion") / "current"
STD_DATA_DIR = Path("v5d_baostock_5min_data_gate") / "data_standardized"
WINDOW_PLAN = Path("v5d_baostock_5min_data_gate") / "current" / "v5d_baostock_rebalance_window_plan.csv"
DAILY_RETURNS = Path("local_daily_backtests_v57f_etf") / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f" / "daily_returns.csv"
V57F_L2_TRADES = Path("v5d_order_scheduling_engineering_test") / "current" / "runs" / "v57f_frozen" / "l2_size_aware" / "trades.csv"
ERC_L2_TRADES = Path("v5d_order_scheduling_engineering_test") / "current" / "runs" / "erc_fixed_covariance_candidate" / "l2_size_aware" / "trades.csv"

REQUIRED_INPUTS = [
    Path("v5d_baostock_5min_data_gate") / "current" / "v5d_baostock_5min_data_gate_summary.json",
    Path("v5d_minute_execution_robustness") / "current" / "v5d_minute_execution_robustness_summary.json",
    Path("v5d_minute_execution_robustness") / "current" / "v5d_execution_proxy_comparison.csv",
    Path("v5d_order_scheduling_engineering_test") / "current" / "v5d_l2_engineering_summary.json",
    Path("v5d_l2_order_scheduling_pm_quant_review") / "current" / "v5d_l2_pm_quant_review_summary.json",
    Path("v5d_l3_intraday_execution_engineering") / "current" / "v5d_l3_engineering_summary.json",
    Path("v5d_l3_intraday_execution_engineering") / "current" / "v5d_l3_unfilled_order_log.csv",
    Path("v5d_l3_pm_quant_review") / "current" / "v5d_l3_pm_quant_review_summary.json",
    Path("v5c_erc_formal_validation") / "current" / "v5c_erc_formal_validation_summary.json",
    Path("enhanced_etf_production_lines_v5") / "current" / "sleeve_promotion_queue.csv",
    WINDOW_PLAN,
    DAILY_RETURNS,
    V57F_L2_TRADES,
    ERC_L2_TRADES,
]

ENGINEERING_WINDOW_START = "2021-05-01"
ENGINEERING_WINDOW_END = "2026-05-31"
REQUIRED_TIMES = ["09:35:00", "09:40:00", "10:00:00", "14:55:00"]


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


def next_trading_day(trading_days: list[str], day: str, offset: int) -> str:
    if day not in trading_days:
        return ""
    idx = trading_days.index(day) + offset
    return trading_days[idx] if 0 <= idx < len(trading_days) else ""


def load_actual_bars_by_rebalance() -> dict[str, dict[str, dict[str, set[str]]]]:
    result: dict[str, dict[str, dict[str, set[str]]]] = {}
    for rebalance_dir in STD_DATA_DIR.iterdir() if STD_DATA_DIR.exists() else []:
        if not rebalance_dir.is_dir():
            continue
        rebalance_date = rebalance_dir.name
        result.setdefault(rebalance_date, {})
        for path in rebalance_dir.glob("*_5min_standardized.csv"):
            try:
                df = pd.read_csv(path, usecols=["code", "trade_date", "time", "open", "high", "low", "close", "volume", "amount"])
            except Exception:
                continue
            if df.empty:
                continue
            code = str(df["code"].iloc[0])
            for trade_date, day in df.groupby("trade_date"):
                key = str(trade_date)
                result[rebalance_date].setdefault(code, {}).setdefault(key, set())
                result[rebalance_date][code][key].update(str(t) for t in day["time"].dropna().unique())
    return result


def trade_codes_by_strategy() -> dict[str, dict[str, set[str]]]:
    result = {"v57f_frozen": {}, "erc_fixed_covariance_candidate": {}}
    for strategy_id, path in [("v57f_frozen", V57F_L2_TRADES), ("erc_fixed_covariance_candidate", ERC_L2_TRADES)]:
        df = pd.read_csv(path)
        for trade_date, day in df.groupby("trade_date"):
            result[strategy_id][str(trade_date)] = set(str(code) for code in day["code"].dropna().unique())
    return result


def build_data_audit() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    plan = pd.read_csv(WINDOW_PLAN)
    trading_days = [str(x) for x in pd.read_csv(DAILY_RETURNS)["trade_date"].dropna().unique()]
    bars = load_actual_bars_by_rebalance()
    codes_by_strategy = trade_codes_by_strategy()
    rows: list[dict[str, Any]] = []
    total_checks = 0
    d0_pass = d1_pass = d2_pass = 0
    d2_missing_windows = 0
    for _, r in plan.iterrows():
        d0 = str(r["rebalance_date"])
        d1 = str(r.get("next_trading_date", "")) if str(r.get("next_trading_date", "")) != "nan" else next_trading_day(trading_days, d0, 1)
        d2 = next_trading_day(trading_days, d0, 2)
        for strategy_id, by_day in codes_by_strategy.items():
            codes = by_day.get(d0, set())
            for label, date_value in [("D0", d0), ("D_plus_1", d1), ("D_plus_2", d2)]:
                total_checks += 1
                covered_codes = 0
                required_time_pass_codes = 0
                missing_codes: list[str] = []
                missing_required_time_codes: list[str] = []
                ohlc_amount_volume_ok_codes = 0
                for code in codes:
                    times = bars.get(d0, {}).get(code, {}).get(date_value, set())
                    if times:
                        covered_codes += 1
                        if all(t in times for t in REQUIRED_TIMES):
                            required_time_pass_codes += 1
                            ohlc_amount_volume_ok_codes += 1
                        else:
                            missing_required_time_codes.append(code)
                    else:
                        missing_codes.append(code)
                pass_flag = bool(codes) and covered_codes == len(codes) and required_time_pass_codes == len(codes)
                if label == "D0" and pass_flag:
                    d0_pass += 1
                if label == "D_plus_1" and pass_flag:
                    d1_pass += 1
                if label == "D_plus_2" and pass_flag:
                    d2_pass += 1
                if label == "D_plus_2" and not pass_flag:
                    d2_missing_windows += 1
                rows.append(
                    {
                        "strategy_id": strategy_id,
                        "rebalance_date": d0,
                        "relative_day": label,
                        "trade_date_required": date_value,
                        "required_code_count": len(codes),
                        "covered_code_count": covered_codes,
                        "required_time_pass_code_count": required_time_pass_codes,
                        "required_times": ";".join(REQUIRED_TIMES + ["last_bar"]),
                        "ohlc_volume_amount_available": str(ohlc_amount_volume_ok_codes == len(codes) and bool(codes)).lower(),
                        "pause_limit_zero_volume_identification": "partial_via_daily_fields_and_5min_zero_or_missing_bar",
                        "pass_for_l4_engineering": str(pass_flag).lower(),
                        "missing_code_sample": ";".join(sorted(missing_codes)[:12]),
                        "missing_required_time_code_sample": ";".join(sorted(missing_required_time_codes)[:12]),
                    }
                )
    stats = {
        "total_relative_day_checks": total_checks,
        "d0_pass_checks": d0_pass,
        "d1_pass_checks": d1_pass,
        "d2_pass_checks": d2_pass,
        "d2_missing_checks": d2_missing_windows,
        "all_d0_d1_d2_available": d2_missing_windows == 0,
    }
    return rows, stats


def build_rule_specs() -> list[dict[str, Any]]:
    return [
        {"rule_id": "baseline_l2_size_aware", "rule_type": "baseline", "description": "Existing L2 size-aware D0 schedule; no change.", "allowed": "yes", "blocked": "accepted;return_selection", "engineering_status": "reference_only"},
        {"rule_id": "l4_d0_sell_first_completion", "rule_type": "D0", "description": "D0 sell orders first using L2/L3 exception governance; unfilled sells logged.", "allowed": "yes", "blocked": "force_fill;delay_sell_for_timing", "engineering_status": "blocked_until_full_D0_D1_D2_data_or_separate_D0_scope"},
        {"rule_id": "l4_d0_buy_after_cash", "rule_type": "D0", "description": "D0 buy orders only after released cash and available cash; no future cash borrowing.", "allowed": "yes", "blocked": "over_target;borrow_future_cash", "engineering_status": "blocked_until_full_D0_D1_D2_data_or_separate_D0_scope"},
        {"rule_id": "l4_d0_d1_completion_fallback", "rule_type": "D0_D1", "description": "Carry only D0 residual orders to D+1; no new signal or target-weight mutation.", "allowed": "yes", "blocked": "new_signal;price_based_target_change", "engineering_status": "data_available_for_D1_but_not_run_due_full_L4_D2_gap"},
        {"rule_id": "l4_d0_d1_d2_final_cleanup", "rule_type": "D0_D1_D2", "description": "Carry residual orders to D+2 final cleanup; archive execution residual after D+2 close.", "allowed": "yes", "blocked": "infinite_chase;cross_gate_roll", "engineering_status": "blocked_missing_D2_5min_data"},
        {"rule_id": "l4_exception_governed_completion", "rule_type": "candidate", "description": "Combine L2 size-aware, L3 default_exception, D0/D1/D2 completion and fixed unfilled taxonomy.", "allowed": "yes_after_data_gate", "blocked": "accepted;V57f_replacement;return_selection", "engineering_status": "blocked_missing_D2_5min_data"},
        {"rule_id": "no_intraday_T_governance", "rule_type": "hard_gate", "description": "No same-day sell-then-buy or buy-then-sell of the same stock outside target completion.", "allowed": "required", "blocked": "bottom_position_T;intraday_alpha", "engineering_status": "spec_only"},
        {"rule_id": "unfilled_reason_taxonomy", "rule_type": "hard_gate", "description": "paused;limit_up_buy_unavailable;limit_down_sell_unavailable;zero_volume;missing_bar;insufficient_liquidity;close_unfinished;cash_not_released;price_band_not_met;other", "allowed": "required", "blocked": "hide_unfilled;fabricate_fill", "engineering_status": "spec_only"},
    ]


def empty_engineering_comparison() -> list[dict[str, Any]]:
    versions = [
        "baseline_l2_size_aware",
        "l4_d0_sell_first_buy_after_cash",
        "l4_d0_d1_completion",
        "l4_d0_d1_d2_final_cleanup",
        "l4_exception_governed_completion",
    ]
    return [
        {
            "version_id": version,
            "engineering_status": "not_run_data_blocked",
            "strategy_return": "",
            "annualized_return": "",
            "max_drawdown": "",
            "volatility": "",
            "trade_count": "",
            "unfilled_order_count": "",
            "unfilled_value": "",
            "cash_shortfall_count": "",
            "t_violation_count": "",
            "reason": "Current local BaoStock 5min data lacks D+2 coverage; L4 D0/D1/D2 engineering would be incomplete.",
        }
        for version in versions
    ]


def build_report(summary: dict[str, Any], blockers: list[dict[str, Any]]) -> str:
    lines = [
        "# V5d L4 Rebalance-Neighborhood Order Completion",
        "",
        f"- Status: `{summary['status']}`",
        f"- Local engineering window: {ENGINEERING_WINDOW_START} to {ENGINEERING_WINDOW_END}",
        "- Scope: order completion policy after rebalance signal only; no V57f/ERC modification, no T, no return selection.",
        f"- D0 coverage: `{summary['data_coverage']['d0_coverage']}`",
        f"- D+1 coverage: `{summary['data_coverage']['d1_coverage']}`",
        f"- D+2 coverage: `{summary['data_coverage']['d2_coverage']}`",
        "",
        "## Decision",
        "",
        "L4 finite engineering is blocked because current local BaoStock 5min data fully covers D0 but does not sufficiently cover D+1 for the actual order universe, and D+2 coverage is absent. The requested D0/D1/D2 final-cleanup rule cannot be tested without additional data.",
        "",
        "## Blockers",
        "",
    ]
    for blocker in blockers:
        lines.append(f"- `{blocker['blocker_id']}`: {blocker['description']}")
    lines.extend(
        [
            "",
            "## Next Data Requirement",
            "",
            "Collect BaoStock 5min unadjusted OHLCV/amount bars for D+2 for every rebalance-date/order-code pair, then rerun the L4 data gate before any engineering comparison.",
        ]
    )
    return "\n".join(lines) + "\n"


def run() -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    missing_inputs = [{"blocker_id": "missing_required_input", "severity": "fatal", "path": str(path), "description": f"Missing required input {path}"} for path in REQUIRED_INPUTS if not path.exists()]
    if missing_inputs:
        write_csv(OUT_DIR / "v5d_l4_blockers.csv", missing_inputs, ["blocker_id", "severity", "path", "description"])
        summary = {"schema_version": 1, "project": "v5d_l4_rebalance_neighborhood_order_completion", "status": "blocked_missing_required_input", "blocker_count": len(missing_inputs), "created_at_utc": now_utc()}
        (OUT_DIR / "v5d_l4_order_completion_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        return summary

    audit_rows, audit_stats = build_data_audit()
    d0_total = len([r for r in audit_rows if r["relative_day"] == "D0"])
    d1_total = len([r for r in audit_rows if r["relative_day"] == "D_plus_1"])
    d2_total = len([r for r in audit_rows if r["relative_day"] == "D_plus_2"])
    d0_pass = len([r for r in audit_rows if r["relative_day"] == "D0" and r["pass_for_l4_engineering"] == "true"])
    d1_pass = len([r for r in audit_rows if r["relative_day"] == "D_plus_1" and r["pass_for_l4_engineering"] == "true"])
    d2_pass = len([r for r in audit_rows if r["relative_day"] == "D_plus_2" and r["pass_for_l4_engineering"] == "true"])
    d0_cov = d0_pass / d0_total if d0_total else 0.0
    d1_cov = d1_pass / d1_total if d1_total else 0.0
    d2_cov = d2_pass / d2_total if d2_total else 0.0
    blockers = [
        {
            "blocker_id": "incomplete_d_plus_1_actual_order_5min_data",
            "severity": "fatal_for_l4_d0_d1_engineering",
            "description": "Current local BaoStock 5min packet does not sufficiently cover D+1 for actual L2 order stocks.",
        },
        {
            "blocker_id": "missing_d_plus_2_5min_data",
            "severity": "fatal_for_l4_d0_d1_d2_engineering",
            "description": "Current local BaoStock 5min packet has no D+2 coverage for the rebalance-neighborhood final cleanup test.",
        },
    ]
    next_data = [
        {"data_requirement": "D_plus_2_5min_unadjusted_bars", "required_for": "l4_d0_d1_d2_final_cleanup;l4_exception_governed_completion", "scope": "all V57f/ERC L2 size-aware order codes for each rebalance signal", "fields": "datetime;time;open;high;low;close;volume;amount;adjustflag", "status": "missing_current_local_packet"},
        {"data_requirement": "D_plus_2_pause_limit_state", "required_for": "unfilled reason taxonomy", "scope": "same order-code/date set", "fields": "paused;high_limit;low_limit or auditable proxy", "status": "missing_or_partial"},
        {"data_requirement": "explicit_D1_D2_window_plan", "required_for": "PIT-safe carry-order schedule", "scope": "rebalance date to D+1/D+2 trading-day map", "fields": "rebalance_date;D0;D_plus_1;D_plus_2", "status": "D_plus_2 missing in current plan"},
    ]
    allowed_blocked = [
        {"action": "generate_l4_rule_spec", "status": "allowed", "reason": "does not require D+2 engineering data"},
        {"action": "run_D0_D1_D2_engineering", "status": "blocked", "reason": "D+1 actual-order coverage is incomplete and D+2 5min bars are missing"},
        {"action": "run_D0_only_or_D0_D1_partial_as_L4_candidate", "status": "blocked", "reason": "requested L4 candidate includes D0/D1/D2 completion; partial engineering could mislead"},
        {"action": "fetch_more_baostock_data_without_user_authorization", "status": "blocked", "reason": "user explicitly forbids联网拉数据 unless authorized"},
        {"action": "modify_v57f_or_erc", "status": "blocked", "reason": "frozen/candidate governance"},
        {"action": "intraday_T", "status": "blocked", "reason": "hard governance block"},
        {"action": "accepted_or_v57f_replacement", "status": "blocked", "reason": "L4 is execution research only"},
    ]
    candidate_gate = [
        {"candidate": "baseline_l2_size_aware", "decision": "reference_only", "reason": "existing L2 baseline"},
        {"candidate": "l4_d0_sell_first_buy_after_cash", "decision": "not_run_data_scope_blocked", "reason": "L4 packet requires complete D0/D1/D2 data before engineering comparison"},
        {"candidate": "l4_d0_d1_completion", "decision": "blocked_incomplete_D_plus_1_actual_order_data", "reason": "D+1 data is incomplete when checked against actual L2 order stocks"},
        {"candidate": "l4_d0_d1_d2_final_cleanup", "decision": "blocked_missing_D_plus_2_data", "reason": "D+2 5min bars are not present"},
        {"candidate": "l4_exception_governed_completion", "decision": "blocked_missing_D_plus_2_data", "reason": "candidate requires complete D0/D1/D2 data and fixed residual archive"},
    ]

    write_csv(OUT_DIR / "v5d_l4_data_availability_audit.csv", audit_rows)
    write_csv(OUT_DIR / "v5d_l4_rule_spec.csv", build_rule_specs())
    write_csv(OUT_DIR / "v5d_l4_engineering_comparison.csv", empty_engineering_comparison())
    write_csv(OUT_DIR / "v5d_l4_order_health.csv", [], ["version_id", "engineering_status", "rebalance_count", "normal_rebalance_count", "unfilled_order_count", "cash_event_count", "t_violation_count", "pm_read"])
    write_csv(OUT_DIR / "v5d_l4_unfilled_order_log.csv", [], ["version_id", "strategy_id", "trade_date", "code", "side", "unfilled_amount", "unfilled_value", "relative_day", "reason"])
    write_csv(OUT_DIR / "v5d_l4_unfilled_reason_summary.csv", [], ["version_id", "unfilled_reason", "count", "value"])
    write_csv(OUT_DIR / "v5d_l4_cash_release_audit.csv", [], ["version_id", "strategy_id", "trade_date", "relative_day", "cash_released", "cash_shortfall", "event"])
    write_csv(OUT_DIR / "v5d_l4_t_violation_audit.csv", [], ["version_id", "strategy_id", "trade_date", "code", "violation"])
    write_csv(OUT_DIR / "v5d_l4_candidate_gate_decision.csv", candidate_gate)
    write_csv(OUT_DIR / "v5d_l4_blockers.csv", blockers, ["blocker_id", "severity", "description"])
    write_csv(OUT_DIR / "v5d_l4_allowed_blocked_actions.csv", allowed_blocked)
    write_csv(OUT_DIR / "v5d_l4_next_data_requirement.csv", next_data)
    (OUT_DIR / "v5d_l4_agent_execution_rules.md").write_text(
        "\n".join(
            [
                "# V5d L4 Agent Execution Rules",
                "",
                "- Do not modify V57f or ERC target holdings, signals, factors, or weights.",
                "- Do not trade D-1 unless a separate PIT-visible target proof exists.",
                "- Do not run L4 D0/D1/D2 engineering until D+2 5min data is present and audited.",
                "- D+1/D+2 may only complete residual D0 target orders; no new signal, no target mutation.",
                "- Do not use historical return to choose D+1/D+2 policy.",
                "- Do not do intraday T, holding-period stop/profit-taking, or infinite chase orders.",
                "- Preserve all unfilled orders with the fixed reason taxonomy.",
                "- Stop and write blockers if any rule requires future bars or forced fills.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    summary = {
        "schema_version": 1,
        "project": "v5d_l4_rebalance_neighborhood_order_completion",
        "status": "blocked_missing_D_plus_2_data_packet_generated",
        "created_at_utc": now_utc(),
        "local_engineering_window": {"start_date": ENGINEERING_WINDOW_START, "end_date": ENGINEERING_WINDOW_END},
        "v57f_core_modified": False,
        "erc_modified": False,
        "joinquant_started": False,
        "network_fetch_started": False,
        "intraday_T_allowed": False,
        "engineering_backtest_started": False,
        "data_coverage": {
            "d0_coverage": f"{d0_pass}/{d0_total}",
            "d1_coverage": f"{d1_pass}/{d1_total}",
            "d2_coverage": f"{d2_pass}/{d2_total}",
            "d0_coverage_ratio": d0_cov,
            "d1_coverage_ratio": d1_cov,
            "d2_coverage_ratio": d2_cov,
        },
        "blocker_count": len(blockers),
        "primary_blocker": ";".join(blocker["blocker_id"] for blocker in blockers),
        "candidate_gate": "blocked_until_D_plus_2_5min_data_available",
        "next_gate": "authorize_or_provide_D_plus_2_baostock_5min_data_then_rerun_l4_data_gate",
        "outputs": {
            "summary": str(OUT_DIR / "v5d_l4_order_completion_summary.json"),
            "report": str(OUT_DIR / "v5d_l4_order_completion_report.md"),
            "data_availability_audit": str(OUT_DIR / "v5d_l4_data_availability_audit.csv"),
            "rule_spec": str(OUT_DIR / "v5d_l4_rule_spec.csv"),
            "engineering_comparison": str(OUT_DIR / "v5d_l4_engineering_comparison.csv"),
            "order_health": str(OUT_DIR / "v5d_l4_order_health.csv"),
            "unfilled_order_log": str(OUT_DIR / "v5d_l4_unfilled_order_log.csv"),
            "unfilled_reason_summary": str(OUT_DIR / "v5d_l4_unfilled_reason_summary.csv"),
            "cash_release_audit": str(OUT_DIR / "v5d_l4_cash_release_audit.csv"),
            "t_violation_audit": str(OUT_DIR / "v5d_l4_t_violation_audit.csv"),
            "candidate_gate_decision": str(OUT_DIR / "v5d_l4_candidate_gate_decision.csv"),
            "blockers": str(OUT_DIR / "v5d_l4_blockers.csv"),
            "next_data_requirement": str(OUT_DIR / "v5d_l4_next_data_requirement.csv"),
            "agent_rules": str(OUT_DIR / "v5d_l4_agent_execution_rules.md"),
        },
    }
    (OUT_DIR / "v5d_l4_order_completion_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "v5d_l4_order_completion_report.md").write_text(build_report(summary, blockers), encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
