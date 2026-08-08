from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

import pandas as pd

from v5.io_utils import read_csv_rows, write_csv_rows
from v5.math_utils import to_float
from v5.v57f_execution_robustness_runner import (
    _build_equal_weight_benchmark,
    _compute_metrics,
    _load_corporate_actions,
    _load_prices,
    _load_signals,
    _portfolio_value,
)
from v5.v5d_minute_execution_robustness_runner import load_minute_prices


OUT_DIR = Path("v5d_order_scheduling_engineering_test") / "current"
RUN_DIR = OUT_DIR / "runs"
BASELINE_DIR = Path("local_daily_backtests_v57f_etf") / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
CONFIG_PATH = Path("config") / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f.json"
DATA_GATE_DIR = Path("v5d_baostock_5min_data_gate") / "current"
ROBUSTNESS_DIR = Path("v5d_minute_execution_robustness") / "current"
SPEC_DIR = Path("v5d_order_scheduling_policy_spec") / "current"
STD_INDEX = DATA_GATE_DIR / "v5d_baostock_5min_standardized_index.csv"
V57F_SIGNALS = BASELINE_DIR / "rebalance_signals.csv"
ERC_SIGNALS = Path("v5c_risk_budget_overlay_engineering_comparison") / "current" / "v5c_erc_fixed_covariance_signals.csv"
ENGINEERING_WINDOW_START = "2021-05-01"
ENGINEERING_WINDOW_END = "2026-05-31"
TARGET_EXPOSURE = 0.995
INITIAL_CASH = 2_000_000.0
LOT_SIZE = 100
COMMISSION_RATE = 0.0003
MIN_COMMISSION = 5.0
SMALL_DIFF_VALUE_FLOOR = 2_000.0
LARGE_ORDER_VALUE_THRESHOLD = 50_000.0


@dataclass
class PlannedOrder:
    code: str
    side: str
    amount: int
    target_amount: int
    ref_price: float
    target_weight: float
    filtered: bool = False
    filter_reason: str = ""


SELL_WINDOWS = [("09:35:00", 0.50), ("09:40:00", 0.25), ("10:00:00", 0.25), ("13:30:00", 0.0), ("14:30:00", 0.0)]
BUY_WINDOWS = [("09:40:00", 0.40), ("10:00:00", 0.30), ("13:30:00", 0.20), ("14:30:00", 0.05), ("14:55:00", 0.05)]


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


def commission(value: float) -> float:
    return max(value * COMMISSION_RATE, MIN_COMMISSION) if value > 0 else 0.0


def target_amount(value: float, price: float) -> int:
    if price <= 0:
        return 0
    return int((value / price) // LOT_SIZE * LOT_SIZE)


def affordable_amount(cash: float, price: float) -> int:
    if price <= 0 or cash <= 0:
        return 0
    raw = int((cash / (price * (1.0 + COMMISSION_RATE))) // LOT_SIZE * LOT_SIZE)
    while raw >= LOT_SIZE and raw * price + commission(raw * price) > cash + 1e-8:
        raw -= LOT_SIZE
    return max(raw, 0)


def price_at(minute_prices: dict[tuple[str, str], dict[str, Any]], code: str, day: str, window: str) -> float | None:
    item = minute_prices.get((code, day))
    if not item:
        return None
    value = item.get("by_time", {}).get(window)
    if value and value > 0:
        return float(value)
    return None


def first_ref_price(
    minute_prices: dict[tuple[str, str], dict[str, Any]],
    price_rows: dict[str, dict[str, float]],
    code: str,
    day: str,
    side: str,
) -> float | None:
    windows = ["09:35:00", "09:40:00", "10:00:00"] if side == "sell" else ["09:40:00", "10:00:00", "13:30:00"]
    for window in windows:
        value = price_at(minute_prices, code, day, window)
        if value:
            return value
    row = price_rows.get(code, {})
    value = row.get("open")
    return value if value and value > 0 else None


def block_reason(row: dict[str, float], price: float | None, side: str) -> str:
    if not row:
        return "missing_daily_price"
    if (row.get("paused") or 0.0) >= 1.0:
        return "paused"
    if price is None or price <= 0:
        return "missing_5min_bar"
    high_limit = row.get("high_limit")
    low_limit = row.get("low_limit")
    if side == "buy" and high_limit and high_limit > 0 and price >= high_limit * 0.999999:
        return "buy_at_high_limit"
    if side == "sell" and low_limit and low_limit > 0 and price <= low_limit * 1.000001:
        return "sell_at_low_limit"
    return ""


def split_amount(total: int, windows: list[tuple[str, float]]) -> dict[str, int]:
    remaining = total
    result: dict[str, int] = {}
    positive_windows = [(w, p) for w, p in windows if p > 0]
    for i, (window, pct) in enumerate(positive_windows):
        if i == len(positive_windows) - 1:
            amount = remaining
        else:
            amount = int((total * pct) // LOT_SIZE * LOT_SIZE)
            amount = min(amount, remaining)
        result[window] = max(0, amount)
        remaining -= amount
    for window, pct in windows:
        result.setdefault(window, 0)
    return result


def build_planned_orders(
    *,
    day: str,
    targets: dict[str, float],
    positions: dict[str, int],
    cash: float,
    price_rows: dict[str, dict[str, float]],
    minute_prices: dict[tuple[str, str], dict[str, Any]],
) -> tuple[list[PlannedOrder], list[dict[str, Any]]]:
    codes = sorted(set(positions) | set(targets))
    ref_prices: dict[str, float] = {}
    for code in codes:
        side_hint = "sell" if positions.get(code, 0) > 0 and targets.get(code, 0.0) == 0 else "buy"
        ref = first_ref_price(minute_prices, price_rows, code, day, side_hint)
        if ref:
            ref_prices[code] = ref
    total_value = _portfolio_value(cash, positions, ref_prices)
    orders: list[PlannedOrder] = []
    filter_rows: list[dict[str, Any]] = []
    for code in codes:
        price = ref_prices.get(code)
        if not price or price <= 0:
            continue
        current = positions.get(code, 0)
        target_weight = targets.get(code, 0.0)
        tgt = target_amount(total_value * target_weight, price)
        delta = tgt - current
        if delta == 0:
            continue
        side = "buy" if delta > 0 else "sell"
        amount = abs(delta)
        filtered = False
        filter_reason = ""
        trade_value = amount * price
        if current > 0 and tgt > 0 and amount < LOT_SIZE:
            filtered = True
            filter_reason = "below_one_lot_existing_diff"
        elif current > 0 and tgt > 0 and trade_value < SMALL_DIFF_VALUE_FLOOR:
            filtered = True
            filter_reason = "below_2000_existing_diff_value_floor"
        if filtered:
            filter_rows.append(
                {
                    "trade_date": day,
                    "code": code,
                    "side": side,
                    "current_amount": current,
                    "target_amount": tgt,
                    "filtered_amount": amount,
                    "ref_price": price,
                    "estimated_value": trade_value,
                    "filter_reason": filter_reason,
                }
            )
            continue
        orders.append(PlannedOrder(code, side, amount, tgt, price, target_weight))
    return orders, filter_rows


def slice_plan(order: PlannedOrder, policy_id: str) -> dict[str, int]:
    if policy_id == "l2_size_aware":
        value = order.amount * order.ref_price
        if value < LARGE_ORDER_VALUE_THRESHOLD:
            if order.side == "sell":
                return {"09:35:00": order.amount, "09:40:00": 0, "10:00:00": 0, "13:30:00": 0, "14:30:00": 0}
            return {"09:40:00": 0, "10:00:00": order.amount, "13:30:00": 0, "14:30:00": 0, "14:55:00": 0}
    return split_amount(order.amount, SELL_WINDOWS if order.side == "sell" else BUY_WINDOWS)


def execute_schedule(
    *,
    day: str,
    strategy_id: str,
    orders: list[PlannedOrder],
    positions: dict[str, int],
    cash: float,
    price_rows: dict[str, dict[str, float]],
    minute_prices: dict[tuple[str, str], dict[str, Any]],
    policy_id: str,
) -> tuple[float, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    trades: list[dict[str, Any]] = []
    unfilled: list[dict[str, Any]] = []
    cash_rows: list[dict[str, Any]] = []
    order_map = {(o.code, o.side): o for o in orders}
    pending = {(o.code, o.side): o.amount for o in orders}
    slice_maps: dict[tuple[str, str], dict[str, int]] = {}
    for order in orders:
        slice_maps[(order.code, order.side)] = slice_plan(order, policy_id)

    for window in ["09:35:00", "09:40:00", "10:00:00", "13:30:00", "14:30:00", "14:55:00"]:
        for side in ["sell", "buy"]:
            if side == "buy" and window == "09:35:00":
                continue
            for key in sorted(list(pending)):
                code, order_side = key
                if order_side != side:
                    continue
                order = order_map[key]
                planned = slice_maps[key].get(window, 0)
                if planned <= 0 and window not in {"13:30:00", "14:30:00", "14:55:00"}:
                    continue
                amount_due = min(pending[key], planned if planned > 0 else pending[key])
                if amount_due <= 0:
                    continue
                price = price_at(minute_prices, code, day, window)
                reason = block_reason(price_rows.get(code, {}), price, side)
                if reason:
                    if window == "14:55:00" or (side == "sell" and window == "14:30:00"):
                        unfilled.append(
                            {
                                "strategy_id": strategy_id,
                                "execution_policy": policy_id,
                                "trade_date": day,
                                "code": code,
                                "side": side,
                                "unfilled_amount": pending[key],
                                "target_amount": order.target_amount,
                                "last_window": window,
                                "final_block_reason": reason,
                                "carry_policy": "stop_at_close_and_log_unfilled",
                            }
                        )
                        pending.pop(key, None)
                    continue
                assert price is not None
                if side == "buy":
                    affordable = affordable_amount(cash, price)
                    fill = min(amount_due, affordable)
                    fill = int(fill // LOT_SIZE * LOT_SIZE)
                    if fill < LOT_SIZE:
                        cash_rows.append(
                            {
                                "strategy_id": strategy_id,
                                "execution_policy": policy_id,
                                "trade_date": day,
                                "code": code,
                                "window": window,
                                "event": "buy_cash_shortfall",
                                "pending_amount": pending[key],
                                "cash": cash,
                                "price": price,
                            }
                        )
                        continue
                    value = fill * price
                    fee = commission(value)
                    cash -= value + fee
                    positions[code] = positions.get(code, 0) + fill
                else:
                    current = positions.get(code, 0)
                    fill = min(amount_due, current)
                    fill = int(fill // LOT_SIZE * LOT_SIZE)
                    if fill < LOT_SIZE:
                        pending.pop(key, None)
                        continue
                    value = fill * price
                    fee = commission(value)
                    cash += value - fee
                    positions[code] = current - fill
                    if positions[code] <= 0:
                        positions.pop(code, None)
                    cash_rows.append(
                        {
                            "strategy_id": strategy_id,
                            "execution_policy": policy_id,
                            "trade_date": day,
                            "code": code,
                            "window": window,
                            "event": "sell_cash_released",
                            "filled_amount": fill,
                            "cash": cash,
                            "price": price,
                        }
                    )
                pending[key] -= fill
                trades.append(
                    {
                        "strategy_id": strategy_id,
                        "trade_date": day,
                        "window": window,
                        "code": code,
                        "side": side,
                        "amount": fill,
                        "price": price,
                        "value": value,
                        "commission": fee,
                        "target_amount": order.target_amount,
                        "remaining_amount": pending.get(key, 0),
                        "execution_policy": policy_id,
                    }
                )
                if pending.get(key, 0) <= 0:
                    pending.pop(key, None)
    for key, amount in pending.items():
        code, side = key
        order = order_map[key]
        unfilled.append(
            {
                "strategy_id": strategy_id,
                "execution_policy": policy_id,
                "trade_date": day,
                "code": code,
                "side": side,
                "unfilled_amount": amount,
                "target_amount": order.target_amount,
                "last_window": "14:55:00",
                "final_block_reason": "end_of_schedule",
                "carry_policy": "stop_at_close_and_log_unfilled",
            }
        )
    return cash, trades, unfilled, cash_rows


def simulate_l2(
    *,
    strategy_id: str,
    signals: dict[str, dict[str, float]],
    prices_by_date: dict[str, dict[str, dict[str, float]]],
    corporate_actions_by_date: dict[str, dict[str, dict[str, float]]],
    benchmark_rows: list[dict[str, Any]],
    minute_prices: dict[tuple[str, str], dict[str, Any]],
    trading_days: list[str],
    policy_id: str,
) -> dict[str, Any]:
    benchmark_by_date = {row["trade_date"]: row for row in benchmark_rows}
    cash = INITIAL_CASH
    positions: dict[str, int] = {}
    last_close: dict[str, float] = {}
    previous_value = cash
    strategy_nav = 1.0
    excess_nav = 1.0
    current_targets: dict[str, float] = {}
    daily_rows: list[dict[str, Any]] = []
    holding_rows: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []
    dividends: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    unfilled: list[dict[str, Any]] = []
    filters: list[dict[str, Any]] = []
    cash_rows: list[dict[str, Any]] = []
    t_violations: list[dict[str, Any]] = []
    signal_days = set(signals)

    for day in trading_days:
        price_rows = prices_by_date.get(day, {})
        action_share_value = 0.0
        for code, action in corporate_actions_by_date.get(day, {}).items():
            current_amount = positions.get(code, 0)
            share_ratio = action.get("stock_dividend_ratio", 0.0) or 0.0
            if current_amount <= 0 or share_ratio <= 0:
                continue
            new_amount = int(round(current_amount * (1.0 + share_ratio)))
            added_amount = new_amount - current_amount
            if added_amount <= 0:
                continue
            positions[code] = new_amount
            close_for_value = price_rows.get(code, {}).get("close") or last_close.get(code, 0.0)
            action_value = added_amount * close_for_value
            action_share_value += action_value
            actions.append({"trade_date": day, "code": code, "action": "stock_dividend_or_transfer", "old_amount": current_amount, "added_amount": added_amount, "new_amount": new_amount})

        rebalance = day in signal_days
        day_trades: list[dict[str, Any]] = []
        day_unfilled: list[dict[str, Any]] = []
        if rebalance:
            current_targets = {code: weight * TARGET_EXPOSURE for code, weight in signals[day].items()}
            planned_orders, filter_rows = build_planned_orders(day=day, targets=current_targets, positions=positions, cash=cash, price_rows=price_rows, minute_prices=minute_prices)
            for row in filter_rows:
                row["strategy_id"] = strategy_id
                row["execution_policy"] = policy_id
            filters.extend(filter_rows)
            cash, day_trades, day_unfilled, day_cash_rows = execute_schedule(
                day=day,
                strategy_id=strategy_id,
                orders=planned_orders,
                positions=positions,
                cash=cash,
                price_rows=price_rows,
                minute_prices=minute_prices,
                policy_id=policy_id,
            )
            trades.extend(day_trades)
            unfilled.extend(day_unfilled)
            cash_rows.extend(day_cash_rows)
            by_code_sides: dict[str, set[str]] = {}
            for row in day_trades:
                by_code_sides.setdefault(row["code"], set()).add(row["side"])
            for code, sides in by_code_sides.items():
                if {"buy", "sell"}.issubset(sides):
                    t_violations.append({"strategy_id": strategy_id, "execution_policy": policy_id, "trade_date": day, "code": code, "violation": "same_day_buy_and_sell"})

        dividend_cash = 0.0
        for code, action in corporate_actions_by_date.get(day, {}).items():
            cash_per_share = action.get("net_cash_per_share", 0.0) or 0.0
            amount = positions.get(code, 0)
            if amount <= 0 or cash_per_share <= 0:
                continue
            cash_amount = amount * cash_per_share
            cash += cash_amount
            dividend_cash += cash_amount
            dividends.append({"trade_date": day, "code": code, "amount": amount, "net_cash_per_share": cash_per_share, "dividend_cash": cash_amount})

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
                "corporate_action_share_value": action_share_value,
                "benchmark_constituent_count": benchmark.get("constituent_count", ""),
                "rebalance": "1" if rebalance else "0",
                "strategy_id": strategy_id,
                "execution_policy": policy_id,
            }
        )
        if rebalance:
            for code, target_weight in current_targets.items():
                amount = positions.get(code, 0)
                close = valuation_prices.get(code, 0.0)
                holding_rows.append({"trade_date": day, "code": code, "target_weight": target_weight, "actual_weight": amount * close / portfolio_value if portfolio_value > 0 else 0.0, "amount": amount, "close": close, "strategy_id": strategy_id, "execution_policy": policy_id})
        last_close.update(close_prices)

    return {
        "policy_id": policy_id,
        "daily": daily_rows,
        "holdings": holding_rows,
        "trades": trades,
        "dividends": dividends,
        "actions": actions,
        "unfilled": unfilled,
        "filters": filters,
        "cash_rows": cash_rows,
        "t_violations": t_violations,
    }


def load_inputs() -> tuple[dict[str, Any], dict[str, dict[str, dict[str, float]]], dict[str, dict[str, dict[str, float]]], list[dict[str, Any]], list[str], dict[tuple[str, str], dict[str, Any]]]:
    config = read_json(CONFIG_PATH)
    price_files = [Path(str(sector["price_csv"])) for sector in config.get("sectors", []) if sector.get("price_csv")]
    dividend_files = [Path(str(sector["dividend_csv"])) for sector in config.get("sectors", []) if sector.get("dividend_csv")]
    deployment_start = str(config.get("portfolio", {}).get("start_date") or ENGINEERING_WINDOW_START)
    prices_by_date = _load_prices(price_files, deployment_start, ENGINEERING_WINDOW_END)
    corporate_actions_by_date = _load_corporate_actions(dividend_files, deployment_start, ENGINEERING_WINDOW_END)
    benchmark_rows = _build_equal_weight_benchmark(prices_by_date, corporate_actions_by_date, deployment_start, ENGINEERING_WINDOW_END)
    trading_days = sorted(prices_by_date)
    minute_prices = load_minute_prices(STD_INDEX)
    return config, prices_by_date, corporate_actions_by_date, benchmark_rows, trading_days, minute_prices


def build_order_health(strategy_id: str, sim: dict[str, Any], signal_count: int) -> dict[str, Any]:
    daily = [row for row in sim["daily"] if row.get("rebalance") == "1"]
    trade_days = {row["trade_date"] for row in sim["trades"]}
    unfilled_days = {row["trade_date"] for row in sim["unfilled"]}
    return {
        "strategy_id": strategy_id,
        "execution_policy": sim["policy_id"],
        "rebalance_signal_count": signal_count,
        "normal_rebalance_count": len([row for row in daily if row["trade_date"] in trade_days]),
        "rebalance_with_logged_unfilled_count": len(unfilled_days),
        "unfilled_order_count": len(sim["unfilled"]),
        "filtered_small_diff_count": len(sim["filters"]),
        "cash_event_count": len(sim["cash_rows"]),
        "t_trade_violation_count": len(sim["t_violations"]),
        "needs_review": bool(sim["t_violations"]),
        "pm_read": "pass_with_logged_unfilled" if not sim["t_violations"] else "needs_review_t_violation",
    }


def comparison_row(strategy_id: str, sim: dict[str, Any], baseline_rows: pd.DataFrame) -> dict[str, Any]:
    metrics = _compute_metrics(sim["daily"])
    base = baseline_rows[(baseline_rows["strategy_id"] == strategy_id) & (baseline_rows["execution_proxy"] == "daily_open")]
    base_ret = float(base["strategy_return"].iloc[0]) if not base.empty else float("nan")
    base_mdd = float(base["max_drawdown"].iloc[0]) if not base.empty else float("nan")
    return {
        "strategy_id": strategy_id,
        "execution_policy": sim["policy_id"],
        "strategy_return": metrics.get("strategy_return"),
        "annualized_return": metrics.get("annualized_return"),
        "max_drawdown": metrics.get("max_drawdown"),
        "strategy_volatility": metrics.get("strategy_volatility"),
        "sharpe": metrics.get("sharpe"),
        "information_ratio": metrics.get("information_ratio"),
        "trade_count": len(sim["trades"]),
        "slice_trade_count": len(sim["trades"]),
        "unfilled_order_count": len(sim["unfilled"]),
        "filtered_small_diff_count": len(sim["filters"]),
        "t_trade_violation_count": len(sim["t_violations"]),
        "avg_cash_weight": mean([to_float(row.get("cash_weight")) or 0.0 for row in sim["daily"]]) if sim["daily"] else 0.0,
        "delta_return_vs_daily_open": (metrics.get("strategy_return") or 0.0) - base_ret,
        "delta_max_drawdown_vs_daily_open": (metrics.get("max_drawdown") or 0.0) - base_mdd,
        "pm_read": "execution_health_test_not_return_selection",
    }


def run() -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    required = [
        SPEC_DIR / "v5d_order_scheduling_policy_summary.json",
        SPEC_DIR / "v5d_order_scheduling_rule_specs.csv",
        SPEC_DIR / "v5d_order_window_plan.csv",
        ROBUSTNESS_DIR / "v5d_execution_proxy_comparison.csv",
        DATA_GATE_DIR / "v5d_baostock_5min_data_gate_summary.json",
        V57F_SIGNALS,
        ERC_SIGNALS,
    ]
    blockers = [{"blocker_id": "missing_required_input", "path": str(path)} for path in required if not path.exists()]
    if blockers:
        write_csv(OUT_DIR / "v5d_l2_engineering_blockers.csv", blockers)
        summary = {"schema_version": 1, "project": "v5d_order_scheduling_engineering_test", "status": "blocked", "blocker_count": len(blockers), "created_at_utc": now_utc()}
        (OUT_DIR / "v5d_l2_engineering_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        return summary

    _, prices_by_date, corporate_actions_by_date, benchmark_rows, trading_days, minute_prices = load_inputs()
    baseline = pd.read_csv(ROBUSTNESS_DIR / "v5d_execution_proxy_comparison.csv")
    signal_sets = {
        "v57f_frozen": _load_signals(V57F_SIGNALS),
        "erc_fixed_covariance_candidate": _load_signals(ERC_SIGNALS),
    }
    comparison_rows: list[dict[str, Any]] = []
    health_rows: list[dict[str, Any]] = []
    unfilled_rows: list[dict[str, Any]] = []
    filter_rows: list[dict[str, Any]] = []
    cash_rows: list[dict[str, Any]] = []
    violation_rows: list[dict[str, Any]] = []
    output_rows: list[dict[str, Any]] = []

    policy_ids = ["l2_all_orders_sliced", "l2_size_aware"]
    for strategy_id, signals in signal_sets.items():
        for policy_id in policy_ids:
            sim = simulate_l2(strategy_id=strategy_id, signals=signals, prices_by_date=prices_by_date, corporate_actions_by_date=corporate_actions_by_date, benchmark_rows=benchmark_rows, minute_prices=minute_prices, trading_days=trading_days, policy_id=policy_id)
            run_dir = RUN_DIR / strategy_id / policy_id
            run_dir.mkdir(parents=True, exist_ok=True)
            write_csv_rows(run_dir / "daily_returns.csv", list(sim["daily"][0].keys()) if sim["daily"] else [], sim["daily"])
            write_csv_rows(run_dir / "trades.csv", list(sim["trades"][0].keys()) if sim["trades"] else [], sim["trades"])
            write_csv_rows(run_dir / "holdings.csv", list(sim["holdings"][0].keys()) if sim["holdings"] else [], sim["holdings"])
            comparison_rows.append(comparison_row(strategy_id, sim, baseline))
            health_rows.append(build_order_health(strategy_id, sim, len(signals)))
            unfilled_rows.extend(sim["unfilled"])
            filter_rows.extend(sim["filters"])
            cash_rows.extend(sim["cash_rows"])
            violation_rows.extend(sim["t_violations"])
            output_rows.append({"strategy_id": strategy_id, "execution_policy": policy_id, "daily_returns": str(run_dir / "daily_returns.csv"), "trades": str(run_dir / "trades.csv"), "holdings": str(run_dir / "holdings.csv")})

    write_csv(OUT_DIR / "v5d_l2_engineering_comparison.csv", comparison_rows)
    write_csv(OUT_DIR / "v5d_l2_order_health.csv", health_rows)
    write_csv(
        OUT_DIR / "v5d_l2_unfilled_order_log.csv",
        unfilled_rows,
        ["strategy_id", "execution_policy", "trade_date", "code", "side", "unfilled_amount", "target_amount", "last_window", "final_block_reason", "carry_policy"],
    )
    write_csv(
        OUT_DIR / "v5d_l2_small_diff_filter_log.csv",
        filter_rows,
        ["trade_date", "code", "side", "current_amount", "target_amount", "filtered_amount", "ref_price", "estimated_value", "filter_reason", "strategy_id", "execution_policy"],
    )
    write_csv(
        OUT_DIR / "v5d_l2_cash_release_and_shortfall_log.csv",
        cash_rows,
        ["strategy_id", "execution_policy", "trade_date", "code", "window", "event", "pending_amount", "filled_amount", "cash", "price"],
    )
    write_csv(
        OUT_DIR / "v5d_l2_no_intraday_t_validation.csv",
        violation_rows,
        ["strategy_id", "execution_policy", "trade_date", "code", "violation"],
    )
    write_csv(OUT_DIR / "v5d_l2_output_index.csv", output_rows)
    allowed_blocked = [
        {"action": "promote_l2_to_pm_review", "status": "allowed", "reason": "engineering completed if no T violations and order logs auditable"},
        {"action": "choose_by_return", "status": "blocked", "reason": "L2 is execution policy, not historical return optimization"},
        {"action": "modify_v57f_or_erc", "status": "blocked", "reason": "frozen/candidate governance"},
        {"action": "intraday_T", "status": "blocked", "reason": "explicitly out of V5d L2"},
    ]
    write_csv(OUT_DIR / "v5d_l2_allowed_blocked_actions.csv", allowed_blocked)
    blockers = []
    if violation_rows:
        blockers.append({"blocker_id": "intraday_t_violation", "severity": "fatal", "description": "Same-day buy and sell appeared for at least one code."})
    if any(row["pm_read"] != "pass_with_logged_unfilled" for row in health_rows):
        blockers.append({"blocker_id": "order_health_needs_review", "severity": "review", "description": "One or more L2 health rows needs review."})
    write_csv(OUT_DIR / "v5d_l2_engineering_blockers.csv", blockers, ["blocker_id", "severity", "description"])
    next_gate = [
        {
            "gate": "pm_quant_review_l2_order_scheduling",
            "allowed": str(not blockers).lower(),
            "reason": "L2 engineering produced auditable fills, unfilled logs, cash logs, and no intraday T violations." if not blockers else "Resolve blockers first.",
            "not_allowed": "accepted_strategy;v57f_replacement;return_selected_execution",
        }
    ]
    write_csv(OUT_DIR / "v5d_l2_next_gate_decision.csv", next_gate)
    summary = {
        "schema_version": 1,
        "project": "v5d_order_scheduling_engineering_test",
        "status": "completed_l2_engineering_ready_for_pm_review" if not blockers else "completed_with_blockers",
        "created_at_utc": now_utc(),
        "local_engineering_window": {"start_date": ENGINEERING_WINDOW_START, "end_date": ENGINEERING_WINDOW_END},
        "v57f_core_modified": False,
        "erc_modified": False,
        "joinquant_started": False,
        "intraday_T_allowed": False,
        "tested_strategies": sorted(signal_sets),
        "tested_execution_policies": policy_ids,
        "unfilled_order_count": len(unfilled_rows),
        "filtered_small_diff_count": len(filter_rows),
        "cash_event_count": len(cash_rows),
        "t_trade_violation_count": len(violation_rows),
        "blocker_count": len(blockers),
        "next_gate": next_gate[0]["gate"] if not blockers else "resolve_l2_engineering_blockers",
        "outputs": {
            "summary": str(OUT_DIR / "v5d_l2_engineering_summary.json"),
            "report": str(OUT_DIR / "v5d_l2_engineering_report.md"),
            "comparison": str(OUT_DIR / "v5d_l2_engineering_comparison.csv"),
            "order_health": str(OUT_DIR / "v5d_l2_order_health.csv"),
            "unfilled": str(OUT_DIR / "v5d_l2_unfilled_order_log.csv"),
            "small_diff_filter": str(OUT_DIR / "v5d_l2_small_diff_filter_log.csv"),
            "cash_log": str(OUT_DIR / "v5d_l2_cash_release_and_shortfall_log.csv"),
            "no_t_validation": str(OUT_DIR / "v5d_l2_no_intraday_t_validation.csv"),
            "next_gate": str(OUT_DIR / "v5d_l2_next_gate_decision.csv"),
        },
    }
    (OUT_DIR / "v5d_l2_engineering_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "v5d_l2_engineering_report.md").write_text(build_report(summary, comparison_rows, health_rows), encoding="utf-8")
    return summary


def pct(value: Any) -> str:
    v = to_float(value)
    return "" if v is None else f"{v:.2%}"


def build_report(summary: dict[str, Any], comparison_rows: list[dict[str, Any]], health_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# V5d L2 Order Scheduling Engineering Test",
        "",
        f"- Status: `{summary['status']}`",
        f"- Local engineering window: {ENGINEERING_WINDOW_START} to {ENGINEERING_WINDOW_END}",
        "- Scope: fixed L2 order scheduling only; no V57f/ERC modification and no intraday T.",
        "",
        "## Comparison",
        "",
        "| Strategy | Policy | Return | Max DD | IR | Trades | Unfilled | Filtered | Delta vs Daily Open |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in comparison_rows:
        lines.append(
            f"| `{row['strategy_id']}` | `{row['execution_policy']}` | {pct(row['strategy_return'])} | {pct(row['max_drawdown'])} | {row['information_ratio']:.4f} | {row['trade_count']} | {row['unfilled_order_count']} | {row['filtered_small_diff_count']} | {pct(row['delta_return_vs_daily_open'])} |"
        )
    lines.extend(["", "## Order Health", ""])
    for row in health_rows:
        lines.append(f"- `{row['strategy_id']}` / `{row['execution_policy']}`: `{row['pm_read']}`, unfilled `{row['unfilled_order_count']}`, filtered `{row['filtered_small_diff_count']}`, T violations `{row['t_trade_violation_count']}`.")
    lines.extend(["", "## PM Read", "", "L2 is complete for engineering and ready for PM/Quant review if blocker count is zero. Results are not a basis for choosing execution windows by return."])
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
