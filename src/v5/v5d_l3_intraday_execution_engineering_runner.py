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
    BUY_WINDOWS,
    COMMISSION_RATE,
    CONFIG_PATH,
    ENGINEERING_WINDOW_END,
    ENGINEERING_WINDOW_START,
    ERC_SIGNALS,
    INITIAL_CASH,
    LOT_SIZE,
    OUT_DIR as L2_OUT_DIR,
    RUN_DIR as L2_RUN_DIR,
    SELL_WINDOWS,
    SPEC_DIR,
    STD_INDEX,
    TARGET_EXPOSURE,
    V57F_SIGNALS,
    PlannedOrder,
    affordable_amount,
    block_reason,
    build_planned_orders,
    commission,
    load_inputs,
    price_at,
    slice_plan,
)


OUT_DIR = Path("v5d_l3_intraday_execution_engineering") / "current"
RUN_DIR = OUT_DIR / "runs"
L3_SPEC_DIR = Path("v5d_l3_intraday_execution_policy_spec") / "current"
STD_DATA_DIR = Path("v5d_baostock_5min_data_gate") / "data_standardized"

OPEN_VOL_RANGE_THRESHOLD = 0.03
OPEN_VOL_BODY_THRESHOLD = 0.02
PRICE_BAND_PCT = 0.05


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


def load_minute_ohlc() -> dict[tuple[str, str], dict[str, Any]]:
    paths = sorted(STD_DATA_DIR.rglob("*_5min_standardized.csv"))
    if not paths and STD_INDEX.exists():
        index = pd.read_csv(STD_INDEX)
        paths = [Path(str(p)) for p in index["path"].dropna().unique()]
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for path in paths:
        if not path.exists():
            continue
        df = pd.read_csv(path)
        if df.empty:
            continue
        for trade_date, day in df.groupby("trade_date"):
            code = str(day["code"].iloc[0])
            bars: dict[str, dict[str, float]] = {}
            for _, row in day.iterrows():
                try:
                    bars[str(row["time"])] = {
                        "open": float(row["open"]),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "close": float(row["close"]),
                        "volume": float(row["volume"]),
                        "amount": float(row["amount"]),
                    }
                except (TypeError, ValueError):
                    continue
            result[(code, str(trade_date))] = {
                "bars": bars,
                "by_time": {k: v["close"] for k, v in bars.items() if v["close"] > 0},
            }
    return result


def visible_times_before_or_at(window: str, include_current: bool) -> list[str]:
    times = ["09:35:00", "09:40:00", "09:45:00", "09:50:00", "09:55:00", "10:00:00", "13:30:00", "14:30:00", "14:55:00"]
    if include_current:
        return [t for t in times if t <= window]
    return [t for t in times if t < window]


def open_volatility_trigger(
    minute_ohlc: dict[tuple[str, str], dict[str, Any]],
    code: str,
    day: str,
    window: str,
    prev_close: float | None,
) -> tuple[bool, str]:
    if window not in {"09:40:00", "10:00:00"} or not prev_close or prev_close <= 0:
        return False, ""
    item = minute_ohlc.get((code, day), {})
    bars = item.get("bars", {})
    visible = ["09:35:00"] if window == "09:40:00" else ["09:35:00", "09:40:00", "09:45:00", "09:50:00", "09:55:00"]
    ranges = []
    bodies = []
    for t in visible:
        bar = bars.get(t)
        if not bar:
            continue
        ranges.append((bar["high"] - bar["low"]) / prev_close)
        if bar["open"] > 0:
            bodies.append(abs(bar["close"] / bar["open"] - 1.0))
    if not ranges:
        return False, ""
    max_range = max(ranges)
    max_body = max(bodies) if bodies else 0.0
    if max_range > OPEN_VOL_RANGE_THRESHOLD or max_body > OPEN_VOL_BODY_THRESHOLD:
        return True, f"open_volatility_delay|max_range={max_range:.4f}|max_body={max_body:.4f}|visible_cutoff_before_{window}"
    return False, ""


def price_band_reason(price: float, side: str, prev_close: float | None, day_open: float | None) -> str:
    anchors = [x for x in [prev_close, day_open] if x and x > 0]
    if not anchors:
        return ""
    if side == "buy":
        ceiling = min(anchor * (1.0 + PRICE_BAND_PCT) for anchor in anchors)
        if price > ceiling:
            return f"price_band_not_triggered_buy|price={price:.4f}|ceiling={ceiling:.4f}"
    else:
        floor = max(anchor * (1.0 - PRICE_BAND_PCT) for anchor in anchors)
        if price < floor:
            return f"price_band_not_triggered_sell|price={price:.4f}|floor={floor:.4f}"
    return ""


def execute_l3_schedule(
    *,
    day: str,
    strategy_id: str,
    l3_policy_id: str,
    orders: list[PlannedOrder],
    positions: dict[str, int],
    cash: float,
    price_rows: dict[str, dict[str, float]],
    minute_prices: dict[tuple[str, str], dict[str, Any]],
    minute_ohlc: dict[tuple[str, str], dict[str, Any]],
    last_close: dict[str, float],
) -> tuple[float, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    trades: list[dict[str, Any]] = []
    unfilled: list[dict[str, Any]] = []
    cash_rows: list[dict[str, Any]] = []
    exception_rows: list[dict[str, Any]] = []
    order_map = {(o.code, o.side): o for o in orders}
    pending = {(o.code, o.side): o.amount for o in orders}
    slice_maps = {(o.code, o.side): slice_plan(o, "l2_size_aware") for o in orders}

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

                prev_close = last_close.get(code)
                day_open = price_rows.get(code, {}).get("open")
                if l3_policy_id in {"l3_open_delay_price_band", "l3_open_delay_price_band_fallback"} and side == "buy":
                    should_delay, delay_reason = open_volatility_trigger(minute_ohlc, code, day, window, prev_close)
                    delay_windows = {"09:40:00", "10:00:00"} if l3_policy_id == "l3_open_delay_price_band" else {"09:40:00"}
                    if should_delay and window in delay_windows:
                        exception_rows.append(
                            {
                                "strategy_id": strategy_id,
                                "l3_policy_id": l3_policy_id,
                                "trade_date": day,
                                "code": code,
                                "side": side,
                                "window": window,
                                "exception_type": "open_volatility_delay",
                                "reason": delay_reason,
                                "pending_amount": pending[key],
                                "visible_bar_cutoff_time": "09:35:00" if window == "09:40:00" else "09:55:00",
                            }
                        )
                        continue

                price = price_at(minute_prices, code, day, window)
                reason = block_reason(price_rows.get(code, {}), price, side)
                if not reason and price is not None and l3_policy_id in {"l3_open_delay_price_band", "l3_open_delay_price_band_fallback"}:
                    if l3_policy_id == "l3_open_delay_price_band_fallback" and window in {"14:30:00", "14:55:00"}:
                        pass
                    else:
                        reason = price_band_reason(price, side, prev_close, day_open)
                if reason:
                    exception_rows.append(
                        {
                            "strategy_id": strategy_id,
                            "l3_policy_id": l3_policy_id,
                            "trade_date": day,
                            "code": code,
                            "side": side,
                            "window": window,
                            "exception_type": reason.split("|")[0],
                            "reason": reason,
                            "pending_amount": pending[key],
                            "visible_bar_cutoff_time": window,
                        }
                    )
                    if window == "14:55:00":
                        unfilled.append(
                            {
                                "strategy_id": strategy_id,
                                "l3_policy_id": l3_policy_id,
                                "trade_date": day,
                                "code": code,
                                "side": side,
                                "unfilled_amount": pending[key],
                                "target_amount": order.target_amount,
                                "last_window": window,
                                "final_block_reason": reason.split("|")[0],
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
                                "l3_policy_id": l3_policy_id,
                                "trade_date": day,
                                "code": code,
                                "window": window,
                                "event": "buy_cash_shortfall",
                                "pending_amount": pending[key],
                                "cash": cash,
                                "price": price,
                                "visible_bar_cutoff_time": window,
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
                            "l3_policy_id": l3_policy_id,
                            "trade_date": day,
                            "code": code,
                            "window": window,
                            "event": "sell_cash_released",
                            "filled_amount": fill,
                            "cash": cash,
                            "price": price,
                            "visible_bar_cutoff_time": window,
                        }
                    )
                pending[key] -= fill
                trades.append(
                    {
                        "strategy_id": strategy_id,
                        "l3_policy_id": l3_policy_id,
                        "trade_date": day,
                        "window": window,
                        "visible_bar_cutoff_time": window,
                        "code": code,
                        "side": side,
                        "amount": fill,
                        "price": price,
                        "value": value,
                        "commission": fee,
                        "target_amount": order.target_amount,
                        "remaining_amount": pending.get(key, 0),
                        "execution_policy": "l2_size_aware",
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
                "l3_policy_id": l3_policy_id,
                "trade_date": day,
                "code": code,
                "side": side,
                "unfilled_amount": amount,
                "target_amount": order.target_amount,
                "last_window": "14:55:00",
                "final_block_reason": "end_of_l3_schedule",
                "carry_policy": "stop_at_close_and_log_unfilled",
            }
        )
    return cash, trades, unfilled, cash_rows, exception_rows


def simulate_l3(
    *,
    strategy_id: str,
    l3_policy_id: str,
    signals: dict[str, dict[str, float]],
    prices_by_date: dict[str, dict[str, dict[str, float]]],
    corporate_actions_by_date: dict[str, dict[str, dict[str, float]]],
    benchmark_rows: list[dict[str, Any]],
    minute_prices: dict[tuple[str, str], dict[str, Any]],
    minute_ohlc: dict[tuple[str, str], dict[str, Any]],
    trading_days: list[str],
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
    unfilled: list[dict[str, Any]] = []
    filters: list[dict[str, Any]] = []
    cash_rows: list[dict[str, Any]] = []
    exception_rows: list[dict[str, Any]] = []
    t_violations: list[dict[str, Any]] = []
    signal_days = set(signals)

    for day in trading_days:
        price_rows = prices_by_date.get(day, {})
        for code, action in corporate_actions_by_date.get(day, {}).items():
            current_amount = positions.get(code, 0)
            share_ratio = action.get("stock_dividend_ratio", 0.0) or 0.0
            if current_amount > 0 and share_ratio > 0:
                positions[code] = int(round(current_amount * (1.0 + share_ratio)))

        rebalance = day in signal_days
        day_trades: list[dict[str, Any]] = []
        if rebalance:
            current_targets = {code: weight * TARGET_EXPOSURE for code, weight in signals[day].items()}
            planned_orders, filter_rows = build_planned_orders(
                day=day,
                targets=current_targets,
                positions=positions,
                cash=cash,
                price_rows=price_rows,
                minute_prices=minute_prices,
            )
            for row in filter_rows:
                row["strategy_id"] = strategy_id
                row["l3_policy_id"] = l3_policy_id
            filters.extend(filter_rows)
            cash, day_trades, day_unfilled, day_cash_rows, day_exception_rows = execute_l3_schedule(
                day=day,
                strategy_id=strategy_id,
                l3_policy_id=l3_policy_id,
                orders=planned_orders,
                positions=positions,
                cash=cash,
                price_rows=price_rows,
                minute_prices=minute_prices,
                minute_ohlc=minute_ohlc,
                last_close=last_close,
            )
            trades.extend(day_trades)
            unfilled.extend(day_unfilled)
            cash_rows.extend(day_cash_rows)
            exception_rows.extend(day_exception_rows)
            by_code_sides: dict[str, set[str]] = {}
            for row in day_trades:
                by_code_sides.setdefault(row["code"], set()).add(row["side"])
            for code, sides in by_code_sides.items():
                if {"buy", "sell"}.issubset(sides):
                    t_violations.append({"strategy_id": strategy_id, "l3_policy_id": l3_policy_id, "trade_date": day, "code": code, "violation": "same_day_buy_and_sell"})

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
                "l3_policy_id": l3_policy_id,
            }
        )
        if rebalance:
            for code, target_weight in current_targets.items():
                amount = positions.get(code, 0)
                close = valuation_prices.get(code, 0.0)
                holding_rows.append({"trade_date": day, "code": code, "target_weight": target_weight, "actual_weight": amount * close / portfolio_value if portfolio_value > 0 else 0.0, "amount": amount, "close": close, "strategy_id": strategy_id, "l3_policy_id": l3_policy_id})
        last_close.update(close_prices)
    return {
        "strategy_id": strategy_id,
        "l3_policy_id": l3_policy_id,
        "daily": daily_rows,
        "holdings": holding_rows,
        "trades": trades,
        "unfilled": unfilled,
        "filters": filters,
        "cash_rows": cash_rows,
        "exception_rows": exception_rows,
        "t_violations": t_violations,
    }


def comparison_row(sim: dict[str, Any], l2_baseline: pd.DataFrame) -> dict[str, Any]:
    metrics = _compute_metrics(sim["daily"])
    base = l2_baseline[
        (l2_baseline["strategy_id"] == sim["strategy_id"])
        & (l2_baseline["execution_policy"] == "l2_size_aware")
    ]
    base_ret = float(base["strategy_return"].iloc[0]) if not base.empty else float("nan")
    base_mdd = float(base["max_drawdown"].iloc[0]) if not base.empty else float("nan")
    return {
        "strategy_id": sim["strategy_id"],
        "l3_policy_id": sim["l3_policy_id"],
        "strategy_return": metrics.get("strategy_return"),
        "annualized_return": metrics.get("annualized_return"),
        "max_drawdown": metrics.get("max_drawdown"),
        "strategy_volatility": metrics.get("strategy_volatility"),
        "sharpe": metrics.get("sharpe"),
        "information_ratio": metrics.get("information_ratio"),
        "trade_count": len(sim["trades"]),
        "unfilled_order_count": len(sim["unfilled"]),
        "exception_count": len(sim["exception_rows"]),
        "filtered_small_diff_count": len(sim["filters"]),
        "cash_event_count": len(sim["cash_rows"]),
        "t_trade_violation_count": len(sim["t_violations"]),
        "avg_cash_weight": mean([to_float(row.get("cash_weight")) or 0.0 for row in sim["daily"]]) if sim["daily"] else 0.0,
        "delta_return_vs_l2_size_aware": (metrics.get("strategy_return") or 0.0) - base_ret,
        "delta_max_drawdown_vs_l2_size_aware": (metrics.get("max_drawdown") or 0.0) - base_mdd,
        "selection_basis": "execution_health_diagnostic_not_return_selection",
    }


def build_order_health(sim: dict[str, Any], signal_count: int) -> dict[str, Any]:
    trade_days = {row["trade_date"] for row in sim["trades"]}
    unfilled_days = {row["trade_date"] for row in sim["unfilled"]}
    return {
        "strategy_id": sim["strategy_id"],
        "l3_policy_id": sim["l3_policy_id"],
        "rebalance_signal_count": signal_count,
        "normal_rebalance_count": len(trade_days),
        "rebalance_with_logged_unfilled_count": len(unfilled_days),
        "unfilled_order_count": len(sim["unfilled"]),
        "exception_count": len(sim["exception_rows"]),
        "filtered_small_diff_count": len(sim["filters"]),
        "cash_event_count": len(sim["cash_rows"]),
        "t_trade_violation_count": len(sim["t_violations"]),
        "pm_read": "pass_with_logged_exceptions" if not sim["t_violations"] else "needs_review_t_violation",
    }


def build_report(summary: dict[str, Any], comparison_rows: list[dict[str, Any]], health_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# V5d L3 Intraday Execution Engineering",
        "",
        f"- Status: `{summary['status']}`",
        f"- Local engineering window: {ENGINEERING_WINDOW_START} to {ENGINEERING_WINDOW_END}",
        "- Scope: fixed L3 execution diagnostics only; no V57f/ERC modification, no T, no return selection.",
        "",
        "## Comparison",
        "",
        "| Strategy | L3 Policy | Return | Max DD | Trades | Unfilled | Exceptions | T Violations | Delta vs L2 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in comparison_rows:
        lines.append(f"| `{row['strategy_id']}` | `{row['l3_policy_id']}` | {pct(row['strategy_return'])} | {pct(row['max_drawdown'])} | {row['trade_count']} | {row['unfilled_order_count']} | {row['exception_count']} | {row['t_trade_violation_count']} | {pct(row['delta_return_vs_l2_size_aware'])} |")
    lines.extend(["", "## Order Health", ""])
    for row in health_rows:
        lines.append(f"- `{row['strategy_id']}` / `{row['l3_policy_id']}`: `{row['pm_read']}`, unfilled `{row['unfilled_order_count']}`, exceptions `{row['exception_count']}`, T violations `{row['t_trade_violation_count']}`.")
    lines.extend(["", "## PM Read", "", "L3 default exception handling is the cleanest engineering candidate because it keeps L2 fills while adding explicit exception governance. The open-delay/price-band diagnostic is useful for understanding tail execution risk, but it should not be selected by return."])
    return "\n".join(lines) + "\n"


def run() -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    required = [
        L3_SPEC_DIR / "v5d_l3_intraday_execution_policy_summary.json",
        L2_OUT_DIR / "v5d_l2_engineering_comparison.csv",
        V57F_SIGNALS,
        ERC_SIGNALS,
        CONFIG_PATH,
    ]
    blockers = [{"blocker_id": "missing_required_input", "severity": "fatal", "path": str(path)} for path in required if not path.exists()]
    if blockers:
        write_csv(OUT_DIR / "v5d_l3_engineering_blockers.csv", blockers, ["blocker_id", "severity", "path"])
        summary = {"schema_version": 1, "project": "v5d_l3_intraday_execution_engineering", "status": "blocked", "blocker_count": len(blockers), "created_at_utc": now_utc()}
        (OUT_DIR / "v5d_l3_engineering_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        return summary

    _, prices_by_date, corporate_actions_by_date, benchmark_rows, trading_days, minute_prices = load_inputs()
    minute_ohlc = load_minute_ohlc()
    l2_baseline = pd.read_csv(L2_OUT_DIR / "v5d_l2_engineering_comparison.csv")
    signal_sets = {
        "v57f_frozen": _load_signals(V57F_SIGNALS),
        "erc_fixed_covariance_candidate": _load_signals(ERC_SIGNALS),
    }
    l3_policies = ["l3_default_exception", "l3_open_delay_price_band", "l3_open_delay_price_band_fallback"]
    comparison_rows: list[dict[str, Any]] = []
    health_rows: list[dict[str, Any]] = []
    unfilled_rows: list[dict[str, Any]] = []
    exception_rows: list[dict[str, Any]] = []
    cash_rows: list[dict[str, Any]] = []
    filter_rows: list[dict[str, Any]] = []
    violation_rows: list[dict[str, Any]] = []
    output_rows: list[dict[str, Any]] = []

    for strategy_id, signals in signal_sets.items():
        for l3_policy_id in l3_policies:
            sim = simulate_l3(
                strategy_id=strategy_id,
                l3_policy_id=l3_policy_id,
                signals=signals,
                prices_by_date=prices_by_date,
                corporate_actions_by_date=corporate_actions_by_date,
                benchmark_rows=benchmark_rows,
                minute_prices=minute_prices,
                minute_ohlc=minute_ohlc,
                trading_days=trading_days,
            )
            run_dir = RUN_DIR / strategy_id / l3_policy_id
            run_dir.mkdir(parents=True, exist_ok=True)
            write_csv_rows(run_dir / "daily_returns.csv", list(sim["daily"][0].keys()) if sim["daily"] else [], sim["daily"])
            write_csv_rows(run_dir / "trades.csv", list(sim["trades"][0].keys()) if sim["trades"] else [], sim["trades"])
            write_csv_rows(run_dir / "holdings.csv", list(sim["holdings"][0].keys()) if sim["holdings"] else [], sim["holdings"])
            comparison_rows.append(comparison_row(sim, l2_baseline))
            health_rows.append(build_order_health(sim, len(signals)))
            unfilled_rows.extend(sim["unfilled"])
            exception_rows.extend(sim["exception_rows"])
            cash_rows.extend(sim["cash_rows"])
            filter_rows.extend(sim["filters"])
            violation_rows.extend(sim["t_violations"])
            output_rows.append({"strategy_id": strategy_id, "l3_policy_id": l3_policy_id, "daily_returns": str(run_dir / "daily_returns.csv"), "trades": str(run_dir / "trades.csv"), "holdings": str(run_dir / "holdings.csv")})

    write_csv(OUT_DIR / "v5d_l3_engineering_comparison.csv", comparison_rows)
    write_csv(OUT_DIR / "v5d_l3_order_health.csv", health_rows)
    write_csv(OUT_DIR / "v5d_l3_unfilled_order_log.csv", unfilled_rows, ["strategy_id", "l3_policy_id", "trade_date", "code", "side", "unfilled_amount", "target_amount", "last_window", "final_block_reason", "carry_policy"])
    write_csv(
        OUT_DIR / "v5d_l3_exception_log.csv",
        exception_rows,
        ["strategy_id", "l3_policy_id", "trade_date", "code", "side", "window", "exception_type", "reason", "pending_amount", "visible_bar_cutoff_time"],
    )
    write_csv(
        OUT_DIR / "v5d_l3_cash_log.csv",
        cash_rows,
        ["strategy_id", "l3_policy_id", "trade_date", "code", "window", "event", "pending_amount", "filled_amount", "cash", "price", "visible_bar_cutoff_time"],
    )
    write_csv(
        OUT_DIR / "v5d_l3_small_diff_filter_log.csv",
        filter_rows,
        ["trade_date", "code", "side", "current_amount", "target_amount", "filtered_amount", "ref_price", "estimated_value", "filter_reason", "strategy_id", "l3_policy_id"],
    )
    write_csv(OUT_DIR / "v5d_l3_no_intraday_t_validation.csv", violation_rows, ["strategy_id", "l3_policy_id", "trade_date", "code", "violation"])
    write_csv(OUT_DIR / "v5d_l3_output_index.csv", output_rows)
    allowed_blocked = [
        {"action": "promote_l3_default_exception_to_pm_review", "status": "allowed", "reason": "keeps fixed L2 schedule and adds exception logs if no T violations"},
        {"action": "review_l3_open_delay_price_band_as_diagnostic", "status": "allowed", "reason": "fixed PIT-safe diagnostic; not selected by return"},
        {"action": "choose_l3_by_return", "status": "blocked", "reason": "L3 is execution governance, not alpha"},
        {"action": "intraday_T", "status": "blocked", "reason": "hard governance block"},
        {"action": "modify_v57f_or_erc", "status": "blocked", "reason": "frozen/candidate governance"},
    ]
    write_csv(OUT_DIR / "v5d_l3_allowed_blocked_actions.csv", allowed_blocked)
    blockers = []
    if violation_rows:
        blockers.append({"blocker_id": "intraday_t_violation", "severity": "fatal", "description": "Same-day buy and sell appeared."})
    write_csv(OUT_DIR / "v5d_l3_engineering_blockers.csv", blockers, ["blocker_id", "severity", "description"])
    next_gate = [
        {
            "gate": "l3_pm_quant_review",
            "allowed": str(not blockers).lower(),
            "reason": "L3 engineering produced auditable fixed-policy results and no T violations." if not blockers else "Resolve blockers first.",
            "not_allowed": "accepted_strategy;v57f_replacement;return_selected_l3",
        }
    ]
    write_csv(OUT_DIR / "v5d_l3_next_gate_decision.csv", next_gate)
    default_rows = [row for row in comparison_rows if row["l3_policy_id"] == "l3_default_exception"]
    diagnostic_rows = [row for row in comparison_rows if row["l3_policy_id"] == "l3_open_delay_price_band"]
    summary = {
        "schema_version": 1,
        "project": "v5d_l3_intraday_execution_engineering",
        "status": "completed_l3_engineering_ready_for_pm_review" if not blockers else "completed_with_blockers",
        "created_at_utc": now_utc(),
        "local_engineering_window": {"start_date": ENGINEERING_WINDOW_START, "end_date": ENGINEERING_WINDOW_END},
        "v57f_core_modified": False,
        "erc_modified": False,
        "joinquant_started": False,
        "intraday_T_allowed": False,
        "return_selection_used": False,
        "tested_strategies": sorted(signal_sets),
        "tested_l3_policies": l3_policies,
        "l3_default_exception_rows": default_rows,
        "l3_open_delay_price_band_rows": diagnostic_rows,
        "unfilled_order_count": len(unfilled_rows),
        "exception_count": len(exception_rows),
        "t_trade_violation_count": len(violation_rows),
        "blocker_count": len(blockers),
        "next_gate": next_gate[0]["gate"] if not blockers else "resolve_l3_engineering_blockers",
        "outputs": {
            "summary": str(OUT_DIR / "v5d_l3_engineering_summary.json"),
            "report": str(OUT_DIR / "v5d_l3_engineering_report.md"),
            "comparison": str(OUT_DIR / "v5d_l3_engineering_comparison.csv"),
            "order_health": str(OUT_DIR / "v5d_l3_order_health.csv"),
            "exception_log": str(OUT_DIR / "v5d_l3_exception_log.csv"),
            "unfilled_log": str(OUT_DIR / "v5d_l3_unfilled_order_log.csv"),
            "no_t_validation": str(OUT_DIR / "v5d_l3_no_intraday_t_validation.csv"),
            "next_gate": str(OUT_DIR / "v5d_l3_next_gate_decision.csv"),
        },
    }
    (OUT_DIR / "v5d_l3_engineering_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "v5d_l3_engineering_report.md").write_text(build_report(summary, comparison_rows, health_rows), encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
