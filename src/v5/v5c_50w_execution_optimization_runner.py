from __future__ import annotations

import csv
import json
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.basket_daily_backtest_runner import (
    _affordable_amount,
    _build_equal_weight_benchmark,
    _build_report,
    _buy_block_reason,
    _commission,
    _compute_metrics,
    _execute_buys,
    _execute_sells,
    _fieldnames,
    _load_corporate_actions,
    _load_prices,
    _portfolio_value,
    _sell_block_reason,
    _target_amount,
    _trade_row,
)
from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.rebalance_order_health import build_rebalance_order_health
from v5.v5c_sleeve_weighting_rigorous_runner import CONFIG_PATH


OUT_DIR = Path("v5c_50w_execution_optimization_test") / "current"
RUN_OUT_DIR = Path("v5c_50w_execution_optimization_test") / "runs"
TOP7_50W_SIGNALS = Path("v5c_topx_capital_rigorous_test") / "current" / "top7_per_sleeve_cap5_rebalance_signals.csv"
INITIAL_CASH = 500_000.0


VARIANTS = [
    {
        "variant_id": "top7_50w_baseline_no_retry",
        "retry_days": 0,
        "min_trade_value": 0.0,
        "description": "Top7 50w baseline: no delayed retry and no small-difference trade filter.",
    },
    {
        "variant_id": "top7_50w_retry_3d",
        "retry_days": 3,
        "min_trade_value": 0.0,
        "description": "Retry skipped limit/paused orders for up to 3 trading days after a rebalance.",
    },
    {
        "variant_id": "top7_50w_min_trade_1000",
        "retry_days": 0,
        "min_trade_value": 1000.0,
        "description": "Skip target-difference trades below 1,000 CNY to reduce minimum-commission friction.",
    },
    {
        "variant_id": "top7_50w_min_trade_2000",
        "retry_days": 0,
        "min_trade_value": 2000.0,
        "description": "Skip target-difference trades below 2,000 CNY to reduce minimum-commission friction.",
    },
    {
        "variant_id": "top7_50w_retry_3d_min_trade_2000",
        "retry_days": 3,
        "min_trade_value": 2000.0,
        "description": "Combine 3-day retry for blocked orders with a 2,000 CNY small-trade filter.",
    },
]


def run_v5c_50w_execution_optimization(root: Path) -> dict[str, Any]:
    out_dir = root / OUT_DIR
    run_out_dir = root / RUN_OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    run_out_dir.mkdir(parents=True, exist_ok=True)

    config = _read_json(root / CONFIG_PATH)
    signals = _load_signals(root / TOP7_50W_SIGNALS)
    start_date = max(str(config.get("portfolio", {}).get("start_date") or "2021-05-01"), min(signals))
    end_date = str(config.get("portfolio", {}).get("end_date") or "2026-05-31")
    price_files = [root / Path(str(sector["price_csv"])) for sector in config.get("sectors", []) if sector.get("price_csv")]
    dividend_files = [root / Path(str(sector["dividend_csv"])) for sector in config.get("sectors", []) if sector.get("dividend_csv")]
    prices_by_date = _load_prices(price_files, start_date, end_date)
    corporate_actions_by_date = _load_corporate_actions(dividend_files, start_date, end_date)
    benchmark_rows = _build_equal_weight_benchmark(prices_by_date, corporate_actions_by_date, start_date, end_date)

    _write_prompt(out_dir)
    _write_csv(out_dir / "v5c_50w_execution_optimization_flow_table.csv", _flow_rows())
    _write_csv(out_dir / "v5c_50w_execution_optimization_variant_spec.csv", VARIANTS)

    comparison_rows: list[dict[str, Any]] = []
    health_rows: list[dict[str, Any]] = []
    output_index_rows: list[dict[str, str]] = []

    for variant in VARIANTS:
        run_dir = run_out_dir / variant["variant_id"]
        run_dir.mkdir(parents=True, exist_ok=True)
        result = _simulate_variant(
            config=config,
            signals=signals,
            prices_by_date=prices_by_date,
            corporate_actions_by_date=corporate_actions_by_date,
            benchmark_rows=benchmark_rows,
            variant=variant,
        )
        _write_run_outputs(root, run_dir, variant, result, config, start_date, end_date)
        summary = result["summary"]
        comparison_rows.append(_comparison_row(variant, summary, result))
        health = dict(summary["rebalance_order_health"])
        health["variant_id"] = variant["variant_id"]
        health_rows.append(health)
        output_index_rows.append(
            {
                "variant_id": variant["variant_id"],
                "summary": str(run_dir / "summary.json"),
                "daily_returns": str(run_dir / "daily_returns.csv"),
                "holdings": str(run_dir / "holdings.csv"),
                "trades": str(run_dir / "trades.csv"),
                "dividends": str(run_dir / "dividends.csv"),
                "retry_log": str(run_dir / "retry_log.csv"),
                "small_trade_skip_log": str(run_dir / "small_trade_skip_log.csv"),
                "rebalance_order_health": str(run_dir / "rebalance_order_health.csv"),
            }
        )

    comparison_rows = _add_deltas(comparison_rows)
    blockers = _blocker_rows()
    _write_csv(out_dir / "v5c_50w_execution_optimization_comparison.csv", comparison_rows)
    _write_csv(out_dir / "v5c_50w_execution_optimization_order_health.csv", health_rows)
    _write_csv(out_dir / "v5c_50w_execution_optimization_output_index.csv", output_index_rows)
    _write_csv(out_dir / "v5c_50w_execution_optimization_blockers.csv", blockers)
    _write_report(out_dir, comparison_rows, blockers)

    summary = {
        "schema_version": 1,
        "project": "v5c_50w_execution_optimization_test",
        "status": "completed_no_v57f_core_change",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "v57f_core_modified": False,
        "joinquant_started": False,
        "initial_cash": INITIAL_CASH,
        "tested_variants": [variant["variant_id"] for variant in VARIANTS],
        "pm_decision": _pm_decision(comparison_rows),
        "outputs": {
            "prompt": str(out_dir / "00_v5c_50w_execution_optimization_prompt.md"),
            "variant_spec": str(out_dir / "v5c_50w_execution_optimization_variant_spec.csv"),
            "comparison": str(out_dir / "v5c_50w_execution_optimization_comparison.csv"),
            "order_health": str(out_dir / "v5c_50w_execution_optimization_order_health.csv"),
            "output_index": str(out_dir / "v5c_50w_execution_optimization_output_index.csv"),
            "report": str(out_dir / "v5c_50w_execution_optimization_report.md"),
            "summary": str(out_dir / "v5c_50w_execution_optimization_summary.json"),
            "blockers": str(out_dir / "v5c_50w_execution_optimization_blockers.csv"),
        },
    }
    _write_json(out_dir / "v5c_50w_execution_optimization_summary.json", summary)
    return summary


def _simulate_variant(
    *,
    config: dict[str, Any],
    signals: dict[str, dict[str, float]],
    prices_by_date: dict[str, dict[str, dict[str, float]]],
    corporate_actions_by_date: dict[str, dict[str, dict[str, float]]],
    benchmark_rows: list[dict[str, Any]],
    variant: dict[str, Any],
) -> dict[str, Any]:
    benchmark_by_date = {row["trade_date"]: row for row in benchmark_rows}
    cash = INITIAL_CASH
    positions: dict[str, int] = {}
    last_close: dict[str, float] = {}
    previous_value = cash
    strategy_nav = 1.0
    excess_nav = 1.0
    daily_rows: list[dict[str, Any]] = []
    holding_rows: list[dict[str, Any]] = []
    trade_rows: list[dict[str, Any]] = []
    dividend_rows: list[dict[str, Any]] = []
    corporate_action_rows: list[dict[str, Any]] = []
    retry_rows: list[dict[str, Any]] = []
    small_skip_rows: list[dict[str, Any]] = []
    current_targets: dict[str, float] = {}
    pending_targets: dict[str, dict[str, Any]] = {}
    retry_days = int(variant["retry_days"])
    min_trade_value = float(variant["min_trade_value"])

    all_dates = sorted(prices_by_date)
    date_index = {day: idx for idx, day in enumerate(all_dates)}

    for day in all_dates:
        price_rows = prices_by_date[day]
        action_share_value = _apply_share_actions(day, price_rows, corporate_actions_by_date, positions, last_close, corporate_action_rows)
        open_prices = {code: item["open"] for code, item in price_rows.items()}
        close_prices = {code: item["close"] for code, item in price_rows.items()}
        trade_prices = dict(last_close)
        trade_prices.update(open_prices)
        buy_turnover = 0.0
        sell_turnover = 0.0
        commission_total = 0.0
        rebalance = day in signals

        if rebalance:
            current_targets = {code: weight * 0.995 for code, weight in signals[day].items()}
            cash, sell_commission, sell_turnover, sells, small_sells = _execute_sells_with_threshold(
                day, cash, positions, trade_prices, price_rows, current_targets, 100, 0.0003, 5.0, min_trade_value
            )
            total_after_sells = _portfolio_value(cash, positions, trade_prices)
            cash, buy_commission, buy_turnover, buys, small_buys = _execute_buys_with_threshold(
                day, cash, positions, trade_prices, price_rows, current_targets, total_after_sells, 100, 0.0003, 5.0, min_trade_value
            )
            commission_total += sell_commission + buy_commission
            trade_rows.extend(sells)
            trade_rows.extend(buys)
            small_skip_rows.extend(small_sells)
            small_skip_rows.extend(small_buys)
            if retry_days > 0:
                _update_pending_from_skips(day, date_index[day], retry_days, current_targets, sells + buys, pending_targets, retry_rows)

        if retry_days > 0 and pending_targets:
            retry_targets = {code: item for code, item in pending_targets.items() if item["expires_idx"] >= date_index[day] and code in current_targets}
            retry_sell_targets = {
                code: item["target_weight"]
                for code, item in retry_targets.items()
                if item.get("source_side") == "sell_skipped"
            }
            retry_buy_targets = {
                code: item["target_weight"]
                for code, item in retry_targets.items()
                if item.get("source_side") == "buy_skipped"
            }
            if retry_targets:
                before_trade_count = len(trade_rows)
                cash, retry_sell_commission, retry_sell_turnover, retry_sells, retry_small_sells = _execute_sells_with_threshold(
                    day,
                    cash,
                    positions,
                    trade_prices,
                    price_rows,
                    retry_sell_targets,
                    100,
                    0.0003,
                    5.0,
                    min_trade_value,
                    True,
                )
                total_after_retry_sells = _portfolio_value(cash, positions, trade_prices)
                cash, retry_buy_commission, retry_buy_turnover, retry_buys, retry_small_buys = _execute_buys_with_threshold(
                    day, cash, positions, trade_prices, price_rows, retry_buy_targets, total_after_retry_sells, 100, 0.0003, 5.0, min_trade_value
                )
                retry_trades = retry_sells + retry_buys
                trade_rows.extend(retry_trades)
                small_skip_rows.extend(retry_small_sells)
                small_skip_rows.extend(retry_small_buys)
                commission_total += retry_sell_commission + retry_buy_commission
                buy_turnover += retry_buy_turnover
                sell_turnover += retry_sell_turnover
                _record_retry_attempts(day, {code: item["target_weight"] for code, item in retry_targets.items()}, retry_trades, retry_rows, pending_targets, before_trade_count)
            expired = [code for code, item in pending_targets.items() if item["expires_idx"] < date_index[day]]
            for code in expired:
                retry_rows.append(
                    {
                        "trade_date": day,
                        "code": code,
                        "event": "retry_expired",
                        "target_weight": pending_targets[code]["target_weight"],
                        "source_rebalance_date": pending_targets[code]["source_rebalance_date"],
                    }
                )
                pending_targets.pop(code, None)

        dividend_cash = _apply_cash_dividends(day, corporate_actions_by_date, positions, dividend_rows)
        cash += dividend_cash

        valuation_prices = dict(last_close)
        valuation_prices.update(close_prices)
        portfolio_value = _portfolio_value(cash, positions, valuation_prices)
        strategy_return = portfolio_value / previous_value - 1.0 if previous_value > 0 else 0.0
        previous_value = portfolio_value
        strategy_nav *= 1.0 + strategy_return
        benchmark = benchmark_by_date.get(day, {})
        benchmark_return = _to_float(benchmark.get("benchmark_return"))
        benchmark_nav = _to_float(benchmark.get("benchmark_nav")) or 1.0
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
                "buy_turnover": buy_turnover,
                "sell_turnover": sell_turnover,
                "commission": commission_total,
                "dividend_cash": dividend_cash,
                "corporate_action_share_value": action_share_value,
                "benchmark_constituent_count": benchmark.get("constituent_count", ""),
                "rebalance": "1" if rebalance else "0",
            }
        )
        if rebalance:
            for code, target_weight in current_targets.items():
                amount = positions.get(code, 0)
                close = valuation_prices.get(code, 0.0)
                holding_rows.append(
                    {
                        "trade_date": day,
                        "code": code,
                        "target_weight": target_weight,
                        "actual_weight": amount * close / portfolio_value if portfolio_value > 0 else 0.0,
                        "amount": amount,
                        "close": close,
                    }
                )
        last_close.update(close_prices)

    order_health_rows, order_health_summary = build_rebalance_order_health(signals, daily_rows, trade_rows, holding_rows)
    metrics = _compute_metrics(daily_rows)
    summary = _summary(config, variant, metrics, order_health_summary, daily_rows, trade_rows, dividend_rows, corporate_action_rows)
    return {
        "summary": summary,
        "daily_rows": daily_rows,
        "holding_rows": holding_rows,
        "trade_rows": trade_rows,
        "dividend_rows": dividend_rows,
        "corporate_action_rows": corporate_action_rows,
        "order_health_rows": order_health_rows,
        "retry_rows": retry_rows,
        "small_skip_rows": small_skip_rows,
    }


def _execute_sells_with_threshold(
    day: str,
    cash: float,
    positions: dict[str, int],
    prices: dict[str, float],
    price_rows: dict[str, dict[str, float]],
    targets: dict[str, float],
    lot_size: int,
    commission_rate: float,
    min_commission: float,
    min_trade_value: float,
    restrict_to_target_codes: bool = False,
) -> tuple[float, float, float, list[dict[str, Any]], list[dict[str, Any]]]:
    total_value = _portfolio_value(cash, positions, prices)
    commission_total = 0.0
    turnover = 0.0
    trades: list[dict[str, Any]] = []
    small_skips: list[dict[str, Any]] = []
    codes_to_check = list(targets) if restrict_to_target_codes else list(positions)
    for code in codes_to_check:
        price = prices.get(code)
        if price is None or price <= 0:
            continue
        target_amount = _target_amount(total_value * targets.get(code, 0.0), price, lot_size)
        current = positions.get(code, 0)
        if current <= target_amount:
            continue
        amount = current - target_amount
        if target_amount > 0 and amount < lot_size:
            continue
        value = amount * price
        if 0 < value < min_trade_value:
            small_skips.append(_small_skip_row(day, code, "sell", amount, price, value, target_amount, min_trade_value))
            continue
        reason = _sell_block_reason(price_rows.get(code))
        if reason:
            trades.append(_trade_row(day, code, "sell_skipped", amount, price, 0.0, 0.0, target_amount, reason))
            continue
        commission = _commission(value, commission_rate, min_commission)
        cash += value - commission
        positions[code] = target_amount
        if positions[code] <= 0:
            positions.pop(code, None)
        commission_total += commission
        turnover += value
        trades.append(_trade_row(day, code, "sell", amount, price, value, commission, target_amount, ""))
    return cash, commission_total, turnover, trades, small_skips


def _execute_buys_with_threshold(
    day: str,
    cash: float,
    positions: dict[str, int],
    prices: dict[str, float],
    price_rows: dict[str, dict[str, float]],
    targets: dict[str, float],
    total_value: float,
    lot_size: int,
    commission_rate: float,
    min_commission: float,
    min_trade_value: float,
) -> tuple[float, float, float, list[dict[str, Any]], list[dict[str, Any]]]:
    commission_total = 0.0
    turnover = 0.0
    trades: list[dict[str, Any]] = []
    small_skips: list[dict[str, Any]] = []
    for code, target_weight in targets.items():
        price = prices.get(code)
        if price is None or price <= 0:
            continue
        target_amount = _target_amount(total_value * target_weight, price, lot_size)
        current = positions.get(code, 0)
        if target_amount <= current:
            continue
        amount = target_amount - current
        amount = min(amount, _affordable_amount(cash, price, lot_size, commission_rate, min_commission))
        if amount < lot_size:
            continue
        value = amount * price
        if current > 0 and 0 < value < min_trade_value:
            small_skips.append(_small_skip_row(day, code, "buy", amount, price, value, target_amount, min_trade_value))
            continue
        reason = _buy_block_reason(price_rows.get(code))
        if reason:
            trades.append(_trade_row(day, code, "buy_skipped", amount, price, 0.0, 0.0, target_amount, reason))
            continue
        commission = _commission(value, commission_rate, min_commission)
        cash -= value + commission
        positions[code] = current + amount
        commission_total += commission
        turnover += value
        trades.append(_trade_row(day, code, "buy", amount, price, value, commission, target_amount, ""))
    return cash, commission_total, turnover, trades, small_skips


def _update_pending_from_skips(
    day: str,
    idx: int,
    retry_days: int,
    targets: dict[str, float],
    trades: list[dict[str, Any]],
    pending_targets: dict[str, dict[str, Any]],
    retry_rows: list[dict[str, Any]],
) -> None:
    for row in trades:
        side = str(row.get("side") or "")
        if side not in {"buy_skipped", "sell_skipped"}:
            continue
        code = str(row.get("code") or "")
        if code not in targets:
            continue
        pending_targets[code] = {
            "target_weight": targets[code],
            "expires_idx": idx + retry_days,
            "source_rebalance_date": day,
            "source_reason": row.get("reason"),
            "source_side": side,
        }
        retry_rows.append(
            {
                "trade_date": day,
                "code": code,
                "event": "retry_scheduled",
                "target_weight": targets[code],
                "expires_after_trading_days": retry_days,
                "reason": row.get("reason"),
            }
        )


def _record_retry_attempts(
    day: str,
    retry_targets: dict[str, float],
    retry_trades: list[dict[str, Any]],
    retry_rows: list[dict[str, Any]],
    pending_targets: dict[str, dict[str, Any]],
    before_trade_count: int,
) -> None:
    successful = {str(row.get("code")) for row in retry_trades if str(row.get("side")) in {"buy", "sell"}}
    skipped = {str(row.get("code")): row.get("reason") for row in retry_trades if "skipped" in str(row.get("side"))}
    for code in retry_targets:
        if code in successful:
            retry_rows.append({"trade_date": day, "code": code, "event": "retry_filled", "target_weight": retry_targets[code]})
            pending_targets.pop(code, None)
        elif code in skipped:
            retry_rows.append({"trade_date": day, "code": code, "event": "retry_still_blocked", "target_weight": retry_targets[code], "reason": skipped[code]})
        else:
            retry_rows.append({"trade_date": day, "code": code, "event": "retry_no_order_needed_or_below_lot", "target_weight": retry_targets[code]})


def _apply_share_actions(
    day: str,
    price_rows: dict[str, dict[str, float]],
    corporate_actions_by_date: dict[str, dict[str, dict[str, float]]],
    positions: dict[str, int],
    last_close: dict[str, float],
    corporate_action_rows: list[dict[str, Any]],
) -> float:
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
        corporate_action_rows.append(
            {
                "trade_date": day,
                "code": code,
                "action": "stock_dividend_or_transfer",
                "old_amount": current_amount,
                "added_amount": added_amount,
                "new_amount": new_amount,
                "stock_dividend_ratio": share_ratio,
                "valuation_price": close_for_value,
                "estimated_share_value": action_value,
            }
        )
    return action_share_value


def _apply_cash_dividends(
    day: str,
    corporate_actions_by_date: dict[str, dict[str, dict[str, float]]],
    positions: dict[str, int],
    dividend_rows: list[dict[str, Any]],
) -> float:
    dividend_cash = 0.0
    for code, action in corporate_actions_by_date.get(day, {}).items():
        cash_per_share = action.get("net_cash_per_share", 0.0) or 0.0
        amount = positions.get(code, 0)
        if amount <= 0 or cash_per_share <= 0:
            continue
        cash_amount = amount * cash_per_share
        dividend_cash += cash_amount
        dividend_rows.append(
            {
                "trade_date": day,
                "code": code,
                "amount": amount,
                "net_cash_per_share": cash_per_share,
                "dividend_cash": cash_amount,
            }
        )
    return dividend_cash


def _summary(
    config: dict[str, Any],
    variant: dict[str, Any],
    metrics: dict[str, Any],
    order_health_summary: dict[str, Any],
    daily_rows: list[dict[str, Any]],
    trade_rows: list[dict[str, Any]],
    dividend_rows: list[dict[str, Any]],
    corporate_action_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "strategy_id": variant["variant_id"],
        "mode": "v5c_50w_execution_optimization",
        "experiment_layer": "engineering_smoke_test",
        "baseline_config": str(CONFIG_PATH),
        "signals_csv": str(TOP7_50W_SIGNALS),
        "variant": variant,
        "execution": {
            "initial_cash": INITIAL_CASH,
            "target_exposure": 0.995,
            "lot_size": 100,
            "open_commission": 0.0003,
            "close_commission": 0.0003,
            "min_commission": 5.0,
            "trade_price": "daily_open",
            "valuation_price": "daily_close",
            "cash_dividend_policy": "Tax-adjusted net_cash_per_share is added to cash on pay_date.",
        },
        "daily_count": len(daily_rows),
        "trade_count": len([row for row in trade_rows if str(row.get("side")) in {"buy", "sell"}]),
        "dividend_count": len(dividend_rows),
        "corporate_action_count": len(corporate_action_rows),
        "rebalance_order_health": order_health_summary,
        "metrics": metrics,
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }


def _write_run_outputs(root: Path, run_dir: Path, variant: dict[str, Any], result: dict[str, Any], config: dict[str, Any], start_date: str, end_date: str) -> None:
    write_csv_rows(run_dir / "daily_returns.csv", _fieldnames(result["daily_rows"]), result["daily_rows"])
    write_csv_rows(run_dir / "holdings.csv", _fieldnames(result["holding_rows"]), result["holding_rows"])
    write_csv_rows(run_dir / "trades.csv", _fieldnames(result["trade_rows"]), result["trade_rows"])
    write_csv_rows(run_dir / "dividends.csv", _fieldnames(result["dividend_rows"]), result["dividend_rows"])
    write_csv_rows(run_dir / "corporate_actions.csv", _fieldnames(result["corporate_action_rows"]), result["corporate_action_rows"])
    write_csv_rows(run_dir / "rebalance_order_health.csv", _fieldnames(result["order_health_rows"]), result["order_health_rows"])
    write_csv_rows(run_dir / "retry_log.csv", _fieldnames(result["retry_rows"]), result["retry_rows"])
    write_csv_rows(run_dir / "small_trade_skip_log.csv", _fieldnames(result["small_skip_rows"]), result["small_skip_rows"])
    shutil.copyfile(root / TOP7_50W_SIGNALS, run_dir / "rebalance_signals.csv")
    write_json_file(run_dir / "summary.json", result["summary"])
    (run_dir / "basket_daily_backtest_report.md").write_text(_build_report(result["summary"]), encoding="utf-8")


def _comparison_row(variant: dict[str, Any], summary: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    metrics = summary["metrics"]
    trades = [row for row in result["trade_rows"] if str(row.get("side")) in {"buy", "sell"}]
    min_fee_trades = [row for row in trades if abs(_to_float(row.get("commission")) - 5.0) < 1e-9]
    total_commission = sum(_to_float(row.get("commission")) for row in trades)
    total_turnover = sum(_to_float(row.get("value")) for row in trades)
    return {
        "variant_id": variant["variant_id"],
        "retry_days": variant["retry_days"],
        "min_trade_value": variant["min_trade_value"],
        "strategy_return": metrics.get("strategy_return"),
        "max_drawdown": metrics.get("max_drawdown"),
        "strategy_volatility": metrics.get("strategy_volatility"),
        "sharpe": metrics.get("sharpe"),
        "information_ratio": metrics.get("information_ratio"),
        "trade_count": summary.get("trade_count"),
        "dividend_count": summary.get("dividend_count"),
        "min_fee_trade_count": len(min_fee_trades),
        "min_fee_trade_ratio": len(min_fee_trades) / len(trades) if trades else 0.0,
        "total_commission": total_commission,
        "total_turnover": total_turnover,
        "commission_to_turnover": total_commission / total_turnover if total_turnover else 0.0,
        "retry_scheduled_count": sum(1 for row in result["retry_rows"] if row.get("event") == "retry_scheduled"),
        "retry_filled_count": sum(1 for row in result["retry_rows"] if row.get("event") == "retry_filled"),
        "retry_expired_count": sum(1 for row in result["retry_rows"] if row.get("event") == "retry_expired"),
        "small_trade_skip_count": len(result["small_skip_rows"]),
        "rebalance_needs_review": summary["rebalance_order_health"].get("needs_review"),
    }


def _add_deltas(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    baseline = next(row for row in rows if row["variant_id"] == "top7_50w_baseline_no_retry")
    output = []
    for row in rows:
        copied = dict(row)
        copied["delta_return_vs_baseline"] = _to_float(row["strategy_return"]) - _to_float(baseline["strategy_return"])
        copied["delta_max_drawdown_vs_baseline"] = _to_float(row["max_drawdown"]) - _to_float(baseline["max_drawdown"])
        copied["delta_trade_count_vs_baseline"] = int(row["trade_count"] or 0) - int(baseline["trade_count"] or 0)
        copied["pm_conclusion"] = _variant_conclusion(copied)
        output.append(copied)
    return output


def _variant_conclusion(row: dict[str, Any]) -> str:
    if row["variant_id"] == "top7_50w_baseline_no_retry":
        return "baseline_reference"
    if row.get("rebalance_needs_review") in {True, "True", "true"}:
        return "blocked_by_order_health_review"
    delta_return = _to_float(row["delta_return_vs_baseline"])
    delta_dd = _to_float(row["delta_max_drawdown_vs_baseline"])
    if delta_return >= 0 and delta_dd <= 0:
        return "execution_optimization_promising"
    if delta_return >= -0.005 and int(row["delta_trade_count_vs_baseline"]) < 0:
        return "cost_reduction_possible_small_return_cost"
    return "diagnostic_only_not_preferred"


def _pm_decision(rows: list[dict[str, Any]]) -> str:
    promising = [row for row in rows if row.get("pm_conclusion") == "execution_optimization_promising"]
    if promising:
        return "review_promising_execution_optimization_not_v57f_core_change"
    return "baseline_top7_50w_remains_preferred; small-trade filters and retry do not improve enough in local test"


def _small_skip_row(day: str, code: str, side: str, amount: int, price: float, value: float, target_amount: int, min_trade_value: float) -> dict[str, Any]:
    return {
        "trade_date": day,
        "code": code,
        "side": side,
        "amount": amount,
        "price": price,
        "value": value,
        "target_amount": target_amount,
        "min_trade_value": min_trade_value,
        "reason": "below_min_trade_value",
    }


def _load_signals(path: Path) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = defaultdict(dict)
    for row in read_csv_rows(path):
        day = str(row.get("trade_date") or "")[:10]
        code = str(row.get("code") or "")
        weight = _to_float(row.get("target_weight"))
        if day and code and weight > 0:
            result[day][code] = result[day].get(code, 0.0) + weight
    return dict(sorted(result.items()))


def _flow_rows() -> list[dict[str, str]]:
    return [
        {
            "step": "1",
            "stage": "scope",
            "action": "Lock 50w Top7 cap5 signals as the execution-optimization target.",
            "output": "prompt and variant spec",
        },
        {
            "step": "2",
            "stage": "delayed_retry",
            "action": "Retry skipped limit/paused orders for up to 3 trading days.",
            "output": "retry logs and comparison",
        },
        {
            "step": "3",
            "stage": "small_trade_filter",
            "action": "Skip existing-position trade differences below 1,000 or 2,000 CNY.",
            "output": "small trade skip logs and fee comparison",
        },
        {
            "step": "4",
            "stage": "pm_review",
            "action": "Compare return, drawdown, fee ratio, trade count and order health.",
            "output": "PM report",
        },
    ]


def _blocker_rows() -> list[dict[str, str]]:
    return [
        {
            "blocked_item": "actual_broker_fee_schedule",
            "reason": "The model assumes 0.03% commission and 5 CNY minimum. Actual broker rules may differ.",
            "allowed_next_action": "Run sensitivity after user confirms broker fee schedule.",
        },
        {
            "blocked_item": "live_order_book_slippage",
            "reason": "Local daily prices do not model order-book depth or partial fills.",
            "allowed_next_action": "Use platform/paper evidence only when user starts that scope.",
        },
    ]


def _write_prompt(out_dir: Path) -> None:
    text = """# V5c 50w Execution Optimization Prompt

Task: Test execution-only fixes for 500,000 CNY Top7 V57f.

Variants:
1. baseline no retry;
2. 3 trading-day retry for skipped limit/paused orders;
3. skip existing-position trade differences below 1,000 CNY;
4. skip existing-position trade differences below 2,000 CNY;
5. combine 3-day retry and 2,000 CNY small-trade filter.

Rules:
- Do not modify V57f selection, sleeve weights, factors or rebalance calendar.
- Use daily open execution, 100-share lots, 0.03% commission, 5 CNY minimum commission and true dividends.
- Keep full daily, trade, holding, dividend, retry, small-skip and order-health logs.
- Do not choose a variant by historical return alone.
"""
    (out_dir / "00_v5c_50w_execution_optimization_prompt.md").write_text(text, encoding="utf-8")


def _write_report(out_dir: Path, rows: list[dict[str, Any]], blockers: list[dict[str, str]]) -> None:
    lines = [
        "# V5c 50w Execution Optimization Test",
        "",
        "This packet tests delayed retry and small-trade filters for the 500,000 CNY Top7 execution problem.",
        "",
        "| Variant | Return | Max DD | Trades | Min-fee ratio | Comm/turnover | Retry filled | Small skips | Delta return | Delta DD | PM conclusion |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| {variant} | {ret:.2%} | {dd:.2%} | {trades} | {minfee:.2%} | {comm:.3%} | {retry} | {small} | {dret:.2%} | {ddd:.2%} | {conclusion} |".format(
                variant=row["variant_id"],
                ret=_to_float(row["strategy_return"]),
                dd=_to_float(row["max_drawdown"]),
                trades=row["trade_count"],
                minfee=_to_float(row["min_fee_trade_ratio"]),
                comm=_to_float(row["commission_to_turnover"]),
                retry=row["retry_filled_count"],
                small=row["small_trade_skip_count"],
                dret=_to_float(row["delta_return_vs_baseline"]),
                ddd=_to_float(row["delta_max_drawdown_vs_baseline"]),
                conclusion=row["pm_conclusion"],
            )
        )
    lines.extend(["", "## PM Notes", ""])
    lines.append("- Retry is useful only if the missed order fills soon enough and does not increase risk/turnover materially.")
    lines.append("- Small-trade filters should reduce minimum-fee noise, but they must not create meaningful drift or return loss.")
    lines.append("- This is an execution overlay only; V57f selection and weights remain frozen.")
    lines.extend(["", "## Blockers", ""])
    for row in blockers:
        lines.append(f"- `{row['blocked_item']}`: {row['reason']}")
    (out_dir / "v5c_50w_execution_optimization_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else ["empty"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    result = run_v5c_50w_execution_optimization(Path.cwd())
    print(json.dumps(result, ensure_ascii=False, indent=2))
