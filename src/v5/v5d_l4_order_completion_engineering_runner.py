from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

import pandas as pd

from v5.io_utils import write_csv_rows
from v5.math_utils import to_float
from v5.v57f_execution_robustness_runner import _compute_metrics, _load_signals, _portfolio_value
from v5.v5d_order_scheduling_engineering_runner import (
    CONFIG_PATH,
    ENGINEERING_WINDOW_END,
    ENGINEERING_WINDOW_START,
    ERC_SIGNALS,
    INITIAL_CASH,
    TARGET_EXPOSURE,
    V57F_SIGNALS,
    PlannedOrder,
    build_planned_orders,
    first_ref_price,
    load_inputs,
)
from v5.v5d_l3_intraday_execution_engineering_runner import execute_l3_schedule, load_minute_ohlc


OUT_DIR = Path("v5d_l4_rebalance_neighborhood_order_completion") / "current"
RUN_DIR = OUT_DIR / "runs"
L4_PACKET_SUMMARY = OUT_DIR / "v5d_l4_order_completion_summary.json"
L2_COMPARISON = Path("v5d_order_scheduling_engineering_test") / "current" / "v5d_l2_engineering_comparison.csv"

L4_POLICIES = [
    "baseline_l2_size_aware",
    "l4_d0_sell_first_buy_after_cash",
    "l4_d0_d1_completion",
    "l4_d0_d1_d2_final_cleanup",
    "l4_exception_governed_completion",
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


def pct(value: Any) -> str:
    v = to_float(value)
    return "" if v is None else f"{v:.2%}"


def next_day_map(trading_days: list[str]) -> dict[str, tuple[str, str]]:
    result: dict[str, tuple[str, str]] = {}
    for i, day in enumerate(trading_days):
        d1 = trading_days[i + 1] if i + 1 < len(trading_days) else ""
        d2 = trading_days[i + 2] if i + 2 < len(trading_days) else ""
        result[day] = (d1, d2)
    return result


def unfilled_to_orders(
    *,
    unfilled_rows: list[dict[str, Any]],
    day: str,
    price_rows: dict[str, dict[str, float]],
    minute_prices: dict[tuple[str, str], dict[str, Any]],
) -> list[PlannedOrder]:
    orders: list[PlannedOrder] = []
    for row in unfilled_rows:
        code = str(row["code"])
        side = str(row["side"])
        amount = int(float(row["unfilled_amount"]))
        target_amount = int(float(row.get("target_amount") or 0))
        if amount <= 0:
            continue
        ref = first_ref_price(minute_prices, price_rows, code, day, side)
        if not ref:
            ref = 0.0
        orders.append(PlannedOrder(code=code, side=side, amount=amount, target_amount=target_amount, ref_price=ref, target_weight=0.0))
    return orders


def execute_and_tag(
    *,
    relative_day: str,
    day: str,
    strategy_id: str,
    l4_policy_id: str,
    orders: list[PlannedOrder],
    positions: dict[str, int],
    cash: float,
    price_rows: dict[str, dict[str, float]],
    minute_prices: dict[tuple[str, str], dict[str, Any]],
    minute_ohlc: dict[tuple[str, str], dict[str, Any]],
    last_close: dict[str, float],
) -> tuple[float, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    cash, trades, unfilled, cash_rows, exceptions = execute_l3_schedule(
        day=day,
        strategy_id=strategy_id,
        l3_policy_id="l3_default_exception",
        orders=orders,
        positions=positions,
        cash=cash,
        price_rows=price_rows,
        minute_prices=minute_prices,
        minute_ohlc=minute_ohlc,
        last_close=last_close,
    )
    for rows in [trades, unfilled, cash_rows, exceptions]:
        for row in rows:
            row["l4_policy_id"] = l4_policy_id
            row["relative_day"] = relative_day
            row.pop("l3_policy_id", None)
    return cash, trades, unfilled, cash_rows, exceptions


def simulate_l4(
    *,
    strategy_id: str,
    l4_policy_id: str,
    signals: dict[str, dict[str, float]],
    prices_by_date: dict[str, dict[str, dict[str, float]]],
    corporate_actions_by_date: dict[str, dict[str, dict[str, float]]],
    benchmark_rows: list[dict[str, Any]],
    minute_prices: dict[tuple[str, str], dict[str, Any]],
    minute_ohlc: dict[tuple[str, str], dict[str, Any]],
    trading_days: list[str],
) -> dict[str, Any]:
    benchmark_by_date = {row["trade_date"]: row for row in benchmark_rows}
    next_days = next_day_map(trading_days)
    max_carry_days = 0
    if l4_policy_id in {"l4_d0_d1_completion"}:
        max_carry_days = 1
    if l4_policy_id in {"l4_d0_d1_d2_final_cleanup", "l4_exception_governed_completion"}:
        max_carry_days = 2

    cash = INITIAL_CASH
    positions: dict[str, int] = {}
    last_close: dict[str, float] = {}
    previous_value = cash
    strategy_nav = 1.0
    excess_nav = 1.0
    current_targets: dict[str, float] = {}
    carry_by_day: dict[str, list[dict[str, Any]]] = {}

    daily_rows: list[dict[str, Any]] = []
    holdings: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []
    unfilled_rows: list[dict[str, Any]] = []
    exceptions: list[dict[str, Any]] = []
    cash_rows: list[dict[str, Any]] = []
    filters: list[dict[str, Any]] = []
    t_violations: list[dict[str, Any]] = []
    signal_days = set(signals)

    for day in trading_days:
        price_rows = prices_by_date.get(day, {})
        for code, action in corporate_actions_by_date.get(day, {}).items():
            current_amount = positions.get(code, 0)
            share_ratio = action.get("stock_dividend_ratio", 0.0) or 0.0
            if current_amount > 0 and share_ratio > 0:
                positions[code] = int(round(current_amount * (1.0 + share_ratio)))

        day_trades: list[dict[str, Any]] = []
        day_unfilled: list[dict[str, Any]] = []
        rebalance = day in signal_days
        if rebalance:
            current_targets = {code: weight * TARGET_EXPOSURE for code, weight in signals[day].items()}
            planned_orders, filter_rows = build_planned_orders(day=day, targets=current_targets, positions=positions, cash=cash, price_rows=price_rows, minute_prices=minute_prices)
            for row in filter_rows:
                row["strategy_id"] = strategy_id
                row["l4_policy_id"] = l4_policy_id
                row["relative_day"] = "D0"
            filters.extend(filter_rows)
            cash, d0_trades, d0_unfilled, d0_cash, d0_exceptions = execute_and_tag(
                relative_day="D0",
                day=day,
                strategy_id=strategy_id,
                l4_policy_id=l4_policy_id,
                orders=planned_orders,
                positions=positions,
                cash=cash,
                price_rows=price_rows,
                minute_prices=minute_prices,
                minute_ohlc=minute_ohlc,
                last_close=last_close,
            )
            day_trades.extend(d0_trades)
            trades.extend(d0_trades)
            cash_rows.extend(d0_cash)
            exceptions.extend(d0_exceptions)
            if max_carry_days > 0 and d0_unfilled:
                d1, d2 = next_days.get(day, ("", ""))
                if d1:
                    for row in d0_unfilled:
                        row["origin_rebalance_date"] = day
                        row["remaining_carry_days"] = max_carry_days
                    carry_by_day.setdefault(d1, []).extend(d0_unfilled)
            else:
                day_unfilled.extend(d0_unfilled)

        if day in carry_by_day:
            incoming = carry_by_day.pop(day)
            if incoming:
                origin = str(incoming[0].get("origin_rebalance_date", ""))
                remaining_carry_days = int(incoming[0].get("remaining_carry_days", 0))
                relative_day = "D_plus_1" if remaining_carry_days == max_carry_days else "D_plus_2"
                carry_orders = unfilled_to_orders(unfilled_rows=incoming, day=day, price_rows=price_rows, minute_prices=minute_prices)
                cash, carry_trades, carry_unfilled, carry_cash, carry_exceptions = execute_and_tag(
                    relative_day=relative_day,
                    day=day,
                    strategy_id=strategy_id,
                    l4_policy_id=l4_policy_id,
                    orders=carry_orders,
                    positions=positions,
                    cash=cash,
                    price_rows=price_rows,
                    minute_prices=minute_prices,
                    minute_ohlc=minute_ohlc,
                    last_close=last_close,
                )
                day_trades.extend(carry_trades)
                trades.extend(carry_trades)
                cash_rows.extend(carry_cash)
                exceptions.extend(carry_exceptions)
                if remaining_carry_days > 1:
                    d1, d2 = next_days.get(day, ("", ""))
                    if d1:
                        for row in carry_unfilled:
                            row["origin_rebalance_date"] = origin
                            row["remaining_carry_days"] = remaining_carry_days - 1
                        carry_by_day.setdefault(d1, []).extend(carry_unfilled)
                    else:
                        day_unfilled.extend(carry_unfilled)
                else:
                    day_unfilled.extend(carry_unfilled)

        by_code_sides: dict[str, set[str]] = {}
        for row in day_trades:
            by_code_sides.setdefault(row["code"], set()).add(row["side"])
        for code, sides in by_code_sides.items():
            if {"buy", "sell"}.issubset(sides):
                t_violations.append({"strategy_id": strategy_id, "l4_policy_id": l4_policy_id, "trade_date": day, "code": code, "violation": "same_day_buy_and_sell"})
        unfilled_rows.extend(day_unfilled)

        dividend_cash = 0.0
        for code, action in corporate_actions_by_date.get(day, {}).items():
            cash_per_share = action.get("net_cash_per_share", 0.0) or 0.0
            amount = positions.get(code, 0)
            if amount > 0 and cash_per_share > 0:
                cash_amount = amount * cash_per_share
                cash += cash_amount
                dividend_cash += cash_amount

        close_prices = {code: item["close"] for code, item in price_rows.items()}
        valuation_prices = dict(last_close)
        valuation_prices.update(close_prices)
        portfolio_value = _portfolio_value(cash, positions, valuation_prices)
        strategy_return = portfolio_value / previous_value - 1.0 if previous_value > 0 else 0.0
        previous_value = portfolio_value
        strategy_nav *= 1.0 + strategy_return
        benchmark = benchmark_by_date.get(day, {})
        benchmark_return = to_float(benchmark.get("benchmark_return")) or 0.0
        benchmark_nav = to_float(benchmark.get("benchmark_nav")) or 1.0
        excess_return = strategy_return - benchmark_return
        excess_nav *= 1.0 + excess_return
        invested_value = sum(amount * valuation_prices.get(code, 0.0) for code, amount in positions.items())
        daily_rows.append(
            {
                "trade_date": day,
                "strategy_return": strategy_return,
                "benchmark_return": benchmark_return,
                "excess_return": excess_return,
                "strategy_nav": strategy_nav,
                "benchmark_nav": benchmark_nav,
                "excess_nav": excess_nav,
                "portfolio_value": portfolio_value,
                "cash": cash,
                "invested_value": invested_value,
                "cash_weight": cash / portfolio_value if portfolio_value > 0 else 1.0,
                "selected_count": len(current_targets) if rebalance else 0,
                "holding_count": len(positions),
                "buy_turnover": sum(to_float(r.get("value")) or 0.0 for r in day_trades if r.get("side") == "buy"),
                "sell_turnover": sum(to_float(r.get("value")) or 0.0 for r in day_trades if r.get("side") == "sell"),
                "commission": sum(to_float(r.get("commission")) or 0.0 for r in day_trades),
                "dividend_cash": dividend_cash,
                "rebalance": "1" if rebalance else "0",
                "strategy_id": strategy_id,
                "l4_policy_id": l4_policy_id,
            }
        )
        if rebalance:
            for code, target_weight in current_targets.items():
                amount = positions.get(code, 0)
                close = valuation_prices.get(code, 0.0)
                holdings.append({"trade_date": day, "code": code, "target_weight": target_weight, "actual_weight": amount * close / portfolio_value if portfolio_value > 0 else 0.0, "amount": amount, "close": close, "strategy_id": strategy_id, "l4_policy_id": l4_policy_id})
        last_close.update(close_prices)
    return {
        "strategy_id": strategy_id,
        "l4_policy_id": l4_policy_id,
        "daily": daily_rows,
        "holdings": holdings,
        "trades": trades,
        "unfilled": unfilled_rows,
        "exceptions": exceptions,
        "cash_rows": cash_rows,
        "filters": filters,
        "t_violations": t_violations,
    }


def comparison_row(sim: dict[str, Any], baseline_rows: pd.DataFrame) -> dict[str, Any]:
    metrics = _compute_metrics(sim["daily"])
    base = baseline_rows[(baseline_rows["strategy_id"] == sim["strategy_id"]) & (baseline_rows["execution_policy"] == "l2_size_aware")]
    base_ret = float(base["strategy_return"].iloc[0]) if not base.empty else float("nan")
    base_mdd = float(base["max_drawdown"].iloc[0]) if not base.empty else float("nan")
    unfilled_value = sum((to_float(row.get("unfilled_amount")) or 0.0) for row in sim["unfilled"])
    return {
        "strategy_id": sim["strategy_id"],
        "version_id": sim["l4_policy_id"],
        "strategy_return": metrics.get("strategy_return"),
        "annualized_return": metrics.get("annualized_return"),
        "max_drawdown": metrics.get("max_drawdown"),
        "volatility": metrics.get("strategy_volatility"),
        "sharpe": metrics.get("sharpe"),
        "information_ratio": metrics.get("information_ratio"),
        "trade_count": len(sim["trades"]),
        "unfilled_order_count": len(sim["unfilled"]),
        "unfilled_amount_sum": unfilled_value,
        "cash_shortfall_count": len([r for r in sim["cash_rows"] if r.get("event") == "buy_cash_shortfall"]),
        "cash_event_count": len(sim["cash_rows"]),
        "exception_count": len(sim["exceptions"]),
        "t_violation_count": len(sim["t_violations"]),
        "avg_cash_weight": mean([to_float(row.get("cash_weight")) or 0.0 for row in sim["daily"]]) if sim["daily"] else 0.0,
        "delta_return_vs_l2_size_aware": (metrics.get("strategy_return") or 0.0) - base_ret,
        "delta_max_drawdown_vs_l2_size_aware": (metrics.get("max_drawdown") or 0.0) - base_mdd,
        "selection_basis": "order_completion_diagnostic_not_return_selection",
    }


def build_report(summary: dict[str, Any], comparison_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# V5d L4 Rebalance-Neighborhood Order Completion Engineering",
        "",
        f"- Status: `{summary['status']}`",
        f"- Local engineering window: {ENGINEERING_WINDOW_START} to {ENGINEERING_WINDOW_END}",
        "- Scope: D0/D1/D2 residual order completion only; no V57f/ERC modification, no T, no return selection.",
        "",
        "| Strategy | Version | Return | Max DD | Trades | Unfilled | T Violations | Delta vs L2 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in comparison_rows:
        lines.append(f"| `{row['strategy_id']}` | `{row['version_id']}` | {pct(row['strategy_return'])} | {pct(row['max_drawdown'])} | {row['trade_count']} | {row['unfilled_order_count']} | {row['t_violation_count']} | {pct(row['delta_return_vs_l2_size_aware'])} |")
    lines.extend(["", "## PM Read", "", "L4 D0/D1/D2 completion can be reviewed as an execution policy candidate only where unfilled governance improves without T violations. Results are not a basis for choosing by historical return."])
    return "\n".join(lines) + "\n"


def run() -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    required = [L4_PACKET_SUMMARY, L2_COMPARISON, V57F_SIGNALS, ERC_SIGNALS, CONFIG_PATH]
    blockers = [{"blocker_id": "missing_required_input", "severity": "fatal", "path": str(path)} for path in required if not path.exists()]
    if blockers:
        write_csv(OUT_DIR / "v5d_l4_blockers.csv", blockers, ["blocker_id", "severity", "path"])
        summary = {"schema_version": 1, "project": "v5d_l4_rebalance_neighborhood_order_completion", "status": "blocked", "blocker_count": len(blockers), "created_at_utc": now_utc()}
        (OUT_DIR / "v5d_l4_order_completion_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        return summary
    packet = read_json(L4_PACKET_SUMMARY)
    d0 = packet.get("data_coverage", {}).get("d0_coverage_ratio", 0)
    d1 = packet.get("data_coverage", {}).get("d1_coverage_ratio", 0)
    d2 = packet.get("data_coverage", {}).get("d2_coverage_ratio", 0)
    if min(d0, d1, d2) < 1.0:
        blockers = [{"blocker_id": "l4_data_gate_not_full_pass", "severity": "fatal", "description": "D0/D1/D2 data coverage is not complete."}]
        write_csv(OUT_DIR / "v5d_l4_blockers.csv", blockers, ["blocker_id", "severity", "description"])
        summary = {"schema_version": 1, "project": "v5d_l4_rebalance_neighborhood_order_completion", "status": "blocked_data_gate_not_full_pass", "blocker_count": 1, "created_at_utc": now_utc(), "data_coverage": packet.get("data_coverage", {})}
        (OUT_DIR / "v5d_l4_order_completion_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        return summary

    _, prices_by_date, corporate_actions_by_date, benchmark_rows, trading_days, minute_prices = load_inputs()
    minute_ohlc = load_minute_ohlc()
    baseline = pd.read_csv(L2_COMPARISON)
    signal_sets = {"v57f_frozen": _load_signals(V57F_SIGNALS), "erc_fixed_covariance_candidate": _load_signals(ERC_SIGNALS)}
    policy_map = {
        "baseline_l2_size_aware": 0,
        "l4_d0_sell_first_buy_after_cash": 0,
        "l4_d0_d1_completion": 1,
        "l4_d0_d1_d2_final_cleanup": 2,
        "l4_exception_governed_completion": 2,
    }
    comparison_rows: list[dict[str, Any]] = []
    health_rows: list[dict[str, Any]] = []
    unfilled_rows: list[dict[str, Any]] = []
    cash_rows: list[dict[str, Any]] = []
    violation_rows: list[dict[str, Any]] = []
    exception_rows: list[dict[str, Any]] = []
    output_rows: list[dict[str, Any]] = []

    for strategy_id, signals in signal_sets.items():
        for policy_id in L4_POLICIES:
            sim = simulate_l4(strategy_id=strategy_id, l4_policy_id=policy_id, signals=signals, prices_by_date=prices_by_date, corporate_actions_by_date=corporate_actions_by_date, benchmark_rows=benchmark_rows, minute_prices=minute_prices, minute_ohlc=minute_ohlc, trading_days=trading_days)
            run_dir = RUN_DIR / strategy_id / policy_id
            run_dir.mkdir(parents=True, exist_ok=True)
            write_csv_rows(run_dir / "daily_returns.csv", list(sim["daily"][0].keys()) if sim["daily"] else [], sim["daily"])
            write_csv_rows(run_dir / "trades.csv", list(sim["trades"][0].keys()) if sim["trades"] else [], sim["trades"])
            write_csv_rows(run_dir / "holdings.csv", list(sim["holdings"][0].keys()) if sim["holdings"] else [], sim["holdings"])
            comp = comparison_row(sim, baseline)
            comparison_rows.append(comp)
            health_rows.append(
                {
                    "strategy_id": strategy_id,
                    "version_id": policy_id,
                    "rebalance_count": len(signals),
                    "normal_rebalance_count": len({r["trade_date"] for r in sim["trades"]}),
                    "unfilled_order_count": len(sim["unfilled"]),
                    "cash_event_count": len(sim["cash_rows"]),
                    "cash_shortfall_count": comp["cash_shortfall_count"],
                    "t_violation_count": len(sim["t_violations"]),
                    "pm_read": "pass" if not sim["t_violations"] else "needs_review_t_violation",
                }
            )
            unfilled_rows.extend(sim["unfilled"])
            cash_rows.extend(sim["cash_rows"])
            violation_rows.extend(sim["t_violations"])
            exception_rows.extend(sim["exceptions"])
            output_rows.append({"strategy_id": strategy_id, "version_id": policy_id, "daily_returns": str(run_dir / "daily_returns.csv"), "trades": str(run_dir / "trades.csv"), "holdings": str(run_dir / "holdings.csv")})

    reason_summary: list[dict[str, Any]] = []
    if unfilled_rows:
        df_unfilled = pd.DataFrame(unfilled_rows)
        for (strategy_id, version_id, reason), group in df_unfilled.groupby(["strategy_id", "l4_policy_id", "final_block_reason"]):
            reason_summary.append({"strategy_id": strategy_id, "version_id": version_id, "unfilled_reason": reason, "count": int(len(group)), "amount_sum": float(pd.to_numeric(group["unfilled_amount"], errors="coerce").fillna(0).sum())})
    gate_rows: list[dict[str, Any]] = []
    for strategy_id in signal_sets:
        base = next(r for r in comparison_rows if r["strategy_id"] == strategy_id and r["version_id"] == "baseline_l2_size_aware")
        for row in [r for r in comparison_rows if r["strategy_id"] == strategy_id]:
            if row["version_id"] == "baseline_l2_size_aware":
                decision = "reference_only"
                reason = "existing L2 size-aware baseline"
            elif row["t_violation_count"] != 0:
                decision = "blocked_t_violation"
                reason = "T violation count must be zero"
            elif row["unfilled_order_count"] < base["unfilled_order_count"]:
                decision = "promote_to_l4_execution_policy_candidate_not_accepted"
                reason = "unfilled count improves versus L2 baseline and T violations are zero; not selected by return"
            elif row["unfilled_order_count"] == base["unfilled_order_count"]:
                decision = "diagnostic_only_no_unfilled_improvement"
                reason = "unfilled count is unchanged versus L2 baseline"
            else:
                decision = "diagnostic_only_unfilled_not_improved"
                reason = "unfilled count is higher than baseline"
            gate_rows.append({"strategy_id": strategy_id, "candidate": row["version_id"], "decision": decision, "reason": reason})

    write_csv(OUT_DIR / "v5d_l4_engineering_comparison.csv", comparison_rows)
    write_csv(OUT_DIR / "v5d_l4_order_health.csv", health_rows)
    write_csv(OUT_DIR / "v5d_l4_unfilled_order_log.csv", unfilled_rows, ["strategy_id", "l4_policy_id", "trade_date", "code", "side", "unfilled_amount", "target_amount", "last_window", "final_block_reason", "carry_policy", "relative_day", "origin_rebalance_date", "remaining_carry_days"])
    write_csv(OUT_DIR / "v5d_l4_unfilled_reason_summary.csv", reason_summary)
    write_csv(
        OUT_DIR / "v5d_l4_cash_release_audit.csv",
        cash_rows,
        ["strategy_id", "l4_policy_id", "trade_date", "code", "window", "event", "pending_amount", "filled_amount", "cash", "price", "visible_bar_cutoff_time", "relative_day"],
    )
    write_csv(OUT_DIR / "v5d_l4_t_violation_audit.csv", violation_rows, ["strategy_id", "l4_policy_id", "trade_date", "code", "violation"])
    write_csv(
        OUT_DIR / "v5d_l4_exception_log.csv",
        exception_rows,
        ["strategy_id", "l4_policy_id", "trade_date", "code", "side", "window", "exception_type", "reason", "pending_amount", "visible_bar_cutoff_time", "relative_day"],
    )
    write_csv(OUT_DIR / "v5d_l4_output_index.csv", output_rows)
    write_csv(OUT_DIR / "v5d_l4_candidate_gate_decision.csv", gate_rows)
    blockers = []
    if violation_rows:
        blockers.append({"blocker_id": "t_violation", "severity": "fatal", "description": "T violation appeared in L4 engineering."})
    write_csv(OUT_DIR / "v5d_l4_blockers.csv", blockers, ["blocker_id", "severity", "description"])
    summary = {
        "schema_version": 1,
        "project": "v5d_l4_rebalance_neighborhood_order_completion",
        "status": "completed_l4_engineering_ready_for_pm_review" if not blockers else "completed_with_blockers",
        "created_at_utc": now_utc(),
        "local_engineering_window": {"start_date": ENGINEERING_WINDOW_START, "end_date": ENGINEERING_WINDOW_END},
        "v57f_core_modified": False,
        "erc_modified": False,
        "joinquant_started": False,
        "intraday_T_allowed": False,
        "return_selection_used": False,
        "data_coverage": packet.get("data_coverage", {}),
        "tested_strategies": sorted(signal_sets),
        "tested_versions": L4_POLICIES,
        "blocker_count": len(blockers),
        "next_gate": "l4_pm_quant_review" if not blockers else "resolve_l4_blockers",
        "outputs": {
            "summary": str(OUT_DIR / "v5d_l4_order_completion_summary.json"),
            "report": str(OUT_DIR / "v5d_l4_order_completion_report.md"),
            "engineering_comparison": str(OUT_DIR / "v5d_l4_engineering_comparison.csv"),
            "order_health": str(OUT_DIR / "v5d_l4_order_health.csv"),
            "unfilled_log": str(OUT_DIR / "v5d_l4_unfilled_order_log.csv"),
            "candidate_gate": str(OUT_DIR / "v5d_l4_candidate_gate_decision.csv"),
        },
    }
    (OUT_DIR / "v5d_l4_order_completion_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "v5d_l4_order_completion_report.md").write_text(build_report(summary, comparison_rows), encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
