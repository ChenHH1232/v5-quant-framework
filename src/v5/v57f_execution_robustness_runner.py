from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.math_utils import to_float
from v5.rebalance_order_health import build_rebalance_order_health
from v5.startup_preload import startup_gap_days


DEFAULT_CONFIG = Path("config/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f.json")
DEFAULT_SIGNALS = Path("validation_formal_v57f_etf_constructor") / "basket_rebalance_signals.csv"
DEFAULT_BASELINE_SUMMARY = (
    Path("local_daily_backtests_v57f_etf") / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f" / "summary.json"
)
DEFAULT_PRODUCTION_SUMMARY = Path("enhanced_etf_production_lines_v5") / "current" / "production_line_summary.json"
DEFAULT_OUT_DIR = Path("execution_robustness_v57f") / "current"

VARIANT_FIELDS = [
    "execution_variant",
    "execution_policy",
    "strategy_return",
    "annualized_return",
    "benchmark_return",
    "excess_return",
    "max_drawdown",
    "sharpe",
    "turnover",
    "trade_count",
    "skipped_buy_count",
    "skipped_sell_count",
    "delayed_fill_count",
    "cash_drag",
    "rebalance_order_health",
    "conclusion",
]

RISK_FIELDS = [
    "execution_variant",
    "trade_date",
    "risk_event",
    "code",
    "action",
    "detail",
    "cash_weight",
    "holding_count",
]


@dataclass(frozen=True)
class ExecutionVariant:
    name: str
    policy: str
    price_alpha: float
    delay_days: int = 0
    slice_days: int = 1
    carry_blocked_orders: bool = False


@dataclass(frozen=True)
class V57fExecutionRobustnessResult:
    output_dir: Path
    freeze_manifest: Path
    variant_matrix_csv: Path
    risk_control_log_csv: Path
    summary_json: Path
    report_path: Path
    variant_count: int


DEFAULT_VARIANTS = [
    ExecutionVariant("rebalance_day_open", "baseline same-day open execution", 0.0),
    ExecutionVariant("rebalance_day_0940_proxy", "same-day 09:40 proxy using open-close interpolation", 10.0 / 240.0),
    ExecutionVariant("rebalance_day_1000_proxy", "same-day 10:00 proxy using open-close interpolation", 30.0 / 240.0),
    ExecutionVariant("rebalance_day_close_proxy", "same-day close proxy stress test", 1.0),
    ExecutionVariant("t_plus_1_open", "next trading day open execution", 0.0, delay_days=1),
    ExecutionVariant("sliced_2d_open", "two trading-day sliced open execution", 0.0, slice_days=2),
    ExecutionVariant("sliced_3d_open", "three trading-day sliced open execution", 0.0, slice_days=3),
    ExecutionVariant("delayed_limit_fill_3d", "same-day open with blocked orders retried for three trading days", 0.0, carry_blocked_orders=True),
]


def run_v57f_execution_robustness(
    config_path: Path = DEFAULT_CONFIG,
    signals_csv: Path = DEFAULT_SIGNALS,
    baseline_summary_path: Path = DEFAULT_BASELINE_SUMMARY,
    production_summary_path: Path = DEFAULT_PRODUCTION_SUMMARY,
    out_dir: Path = DEFAULT_OUT_DIR,
    *,
    initial_cash: float = 2_000_000.0,
    target_exposure: float = 0.995,
    lot_size: int = 100,
    open_commission: float = 0.0003,
    close_commission: float = 0.0003,
    min_commission: float = 5.0,
) -> V57fExecutionRobustnessResult:
    config = _read_json(config_path)
    project = str(config.get("project") or "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f")
    start_date = str(config.get("portfolio", {}).get("start_date") or "2021-05-01")
    configured_start_date = start_date
    end_date = str(config.get("portfolio", {}).get("end_date") or "2026-05-31")
    signals = _load_signals(signals_csv)
    if not signals:
        raise ValueError(f"no frozen V57f signals found: {signals_csv}")
    first_signal = min(signals)

    price_files = [Path(str(sector["price_csv"])) for sector in config.get("sectors", []) if sector.get("price_csv")]
    dividend_files = [Path(str(sector["dividend_csv"])) for sector in config.get("sectors", []) if sector.get("dividend_csv")]
    prices_by_date = _load_prices(price_files, start_date, end_date)
    corporate_actions_by_date = _load_corporate_actions(dividend_files, start_date, end_date)
    benchmark_by_date = _build_equal_weight_benchmark(prices_by_date, corporate_actions_by_date, start_date, end_date)
    trading_days = sorted(prices_by_date)

    out_dir.mkdir(parents=True, exist_ok=True)
    variant_rows: list[dict[str, Any]] = []
    risk_rows: list[dict[str, Any]] = []
    variant_outputs: dict[str, dict[str, str]] = {}

    for variant in DEFAULT_VARIANTS:
        daily_rows, holding_rows, trade_rows, dividend_rows, corporate_action_rows, variant_risk_rows = _simulate_variant(
            prices_by_date=prices_by_date,
            corporate_actions_by_date=corporate_actions_by_date,
            benchmark_rows=benchmark_by_date,
            signals=signals,
            trading_days=trading_days,
            variant=variant,
            initial_cash=initial_cash,
            target_exposure=target_exposure,
            lot_size=lot_size,
            open_commission=open_commission,
            close_commission=close_commission,
            min_commission=min_commission,
        )
        health_schedule = _schedule_signals(signals, trading_days, variant.delay_days)
        variant_dir = out_dir / variant.name
        variant_dir.mkdir(parents=True, exist_ok=True)
        daily_path = variant_dir / "daily_returns.csv"
        holdings_path = variant_dir / "holdings.csv"
        trades_path = variant_dir / "trades.csv"
        dividends_path = variant_dir / "dividends.csv"
        corporate_actions_path = variant_dir / "corporate_actions.csv"
        order_health_path = variant_dir / "rebalance_order_health.csv"
        summary_path = variant_dir / "summary.json"
        order_health_rows, order_health_summary = build_rebalance_order_health(health_schedule, daily_rows, trade_rows, holding_rows)
        metrics = _compute_metrics(daily_rows)
        turnover = sum((to_float(row.get("value")) or 0.0) for row in trade_rows if str(row.get("side") or "") in {"buy", "sell"})
        average_nav = mean([to_float(row.get("portfolio_value")) or initial_cash for row in daily_rows]) if daily_rows else initial_cash
        skipped_buy_count = sum(1 for row in trade_rows if row.get("side") == "buy_skipped")
        skipped_sell_count = sum(1 for row in trade_rows if row.get("side") == "sell_skipped")
        delayed_fill_count = sum(1 for row in trade_rows if str(row.get("reason") or "").startswith("delayed_fill"))
        cash_drag = mean([to_float(row.get("cash_weight")) or 0.0 for row in daily_rows]) if daily_rows else 0.0

        summary = {
            "schema_version": 1,
            "strategy_id": project,
            "execution_variant": variant.name,
            "experiment_layer": "engineering_execution_robustness_not_tuning",
            "config": str(config_path),
            "signals_csv": str(signals_csv),
            "window": {"start_date": start_date, "end_date": end_date},
            "startup_preload": {
                "configured_start_date": configured_start_date,
                "effective_first_signal_date": first_signal,
                "first_daily_row_date": daily_rows[0]["trade_date"] if daily_rows else None,
                "startup_gap_days": startup_gap_days(configured_start_date, first_signal),
                "start_date_was_silently_lifted_to_first_signal": False,
            },
            "execution_policy": variant.policy,
            "frozen_logic": {
                "signals_are_reused": True,
                "factors_are_not_recomputed": True,
                "weights_are_not_tuned": True,
                "sleeves_are_not_changed": True,
            },
            "metrics": metrics,
            "turnover": turnover / average_nav if average_nav > 0 else None,
            "trade_count": len([row for row in trade_rows if row.get("side") in {"buy", "sell"}]),
            "skipped_buy_count": skipped_buy_count,
            "skipped_sell_count": skipped_sell_count,
            "delayed_fill_count": delayed_fill_count,
            "cash_drag": cash_drag,
            "rebalance_order_health": order_health_summary,
            "created_at_utc": _now(),
        }
        write_csv_rows(daily_path, _fieldnames(daily_rows), daily_rows)
        write_csv_rows(holdings_path, _fieldnames(holding_rows), holding_rows)
        write_csv_rows(trades_path, _fieldnames(trade_rows), trade_rows)
        write_csv_rows(dividends_path, _fieldnames(dividend_rows), dividend_rows)
        write_csv_rows(corporate_actions_path, _fieldnames(corporate_action_rows), corporate_action_rows)
        write_csv_rows(order_health_path, _fieldnames(order_health_rows), order_health_rows)
        write_json_file(summary_path, summary)
        variant_outputs[variant.name] = {
            "summary": str(summary_path),
            "daily_returns": str(daily_path),
            "holdings": str(holdings_path),
            "trades": str(trades_path),
            "rebalance_order_health": str(order_health_path),
        }
        risk_rows.extend(variant_risk_rows)
        variant_rows.append(
            {
                "execution_variant": variant.name,
                "execution_policy": variant.policy,
                "strategy_return": _num(metrics.get("strategy_return")),
                "annualized_return": _num(metrics.get("annualized_return")),
                "benchmark_return": _num(metrics.get("benchmark_return")),
                "excess_return": _num(metrics.get("excess_return")),
                "max_drawdown": _num(metrics.get("max_drawdown")),
                "sharpe": _num(metrics.get("sharpe")),
                "turnover": _num(summary["turnover"]),
                "trade_count": summary["trade_count"],
                "skipped_buy_count": skipped_buy_count,
                "skipped_sell_count": skipped_sell_count,
                "delayed_fill_count": delayed_fill_count,
                "cash_drag": _num(cash_drag),
                "rebalance_order_health": "needs_review" if order_health_summary.get("needs_review") else "pass",
                "conclusion": _variant_conclusion(metrics, order_health_summary),
            }
        )

    freeze_manifest_path = out_dir / "v57f_freeze_manifest.json"
    variant_matrix_csv = out_dir / "execution_variant_matrix.csv"
    risk_control_log_csv = out_dir / "non_rebalance_risk_control_log.csv"
    summary_json = out_dir / "execution_robustness_summary.json"
    report_path = out_dir / "execution_robustness_report.md"
    frozen_copy = out_dir / "frozen_basket_rebalance_signals.csv"
    shutil.copyfile(signals_csv, frozen_copy)

    freeze_manifest = _build_freeze_manifest(
        config_path=config_path,
        signals_csv=signals_csv,
        baseline_summary_path=baseline_summary_path,
        production_summary_path=production_summary_path,
        config=config,
        signals=signals,
        baseline_summary=_read_json_if_exists(baseline_summary_path),
        production_summary=_read_json_if_exists(production_summary_path),
        configured_start_date=configured_start_date,
        first_signal_date=first_signal,
    )
    write_json_file(freeze_manifest_path, freeze_manifest)
    write_csv_rows(variant_matrix_csv, VARIANT_FIELDS, variant_rows)
    write_csv_rows(risk_control_log_csv, RISK_FIELDS, risk_rows)

    summary = _build_summary(freeze_manifest, variant_rows, risk_rows, variant_outputs, report_path)
    write_json_file(summary_json, summary)
    report_path.write_text(_build_report(summary, variant_rows, risk_rows), encoding="utf-8")

    return V57fExecutionRobustnessResult(
        output_dir=out_dir,
        freeze_manifest=freeze_manifest_path,
        variant_matrix_csv=variant_matrix_csv,
        risk_control_log_csv=risk_control_log_csv,
        summary_json=summary_json,
        report_path=report_path,
        variant_count=len(variant_rows),
    )


def _simulate_variant(
    *,
    prices_by_date: dict[str, dict[str, dict[str, float]]],
    corporate_actions_by_date: dict[str, dict[str, dict[str, float]]],
    benchmark_rows: list[dict[str, Any]],
    signals: dict[str, dict[str, float]],
    trading_days: list[str],
    variant: ExecutionVariant,
    initial_cash: float,
    target_exposure: float,
    lot_size: int,
    open_commission: float,
    close_commission: float,
    min_commission: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    signal_schedule = _schedule_signals(signals, trading_days, variant.delay_days)
    benchmark_by_date = {row["trade_date"]: row for row in benchmark_rows}
    cash = float(initial_cash)
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
    risk_rows: list[dict[str, Any]] = []
    current_targets: dict[str, float] = {}
    pending_targets: dict[str, int] = {}
    slice_state: dict[str, Any] = {}

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

        close_prices = {code: item["close"] for code, item in price_rows.items()}
        trade_prices = dict(last_close)
        trade_prices.update({code: _execution_price(item, variant.price_alpha) for code, item in price_rows.items()})
        buy_turnover = 0.0
        sell_turnover = 0.0
        commission_total = 0.0
        scheduled_targets = signal_schedule.get(day)
        is_signal_day = scheduled_targets is not None
        is_slice_followup = bool(slice_state) and day in slice_state.get("days", [])[1:]
        rebalance_like_day = is_signal_day or is_slice_followup or bool(pending_targets)

        if is_signal_day:
            current_targets = {code: weight * target_exposure for code, weight in scheduled_targets.items()}
            if variant.slice_days > 1:
                slice_days = _slice_days(day, trading_days, variant.slice_days)
                slice_state = {"targets": current_targets, "days": slice_days}
            else:
                slice_state = {}

        targets_for_day = current_targets
        slice_progress = 1.0
        if slice_state:
            days = slice_state.get("days", [])
            if day in days:
                slice_progress = (days.index(day) + 1) / len(days)
                targets_for_day = {
                    code: _interpolate_weight(positions, trade_prices, cash, code, target, slice_progress)
                    for code, target in slice_state["targets"].items()
                }

        if rebalance_like_day:
            cash, sell_commission, sell_turnover, sells, new_pending_sells = _execute_sells(
                day,
                cash,
                positions,
                trade_prices,
                price_rows,
                targets_for_day,
                lot_size,
                close_commission,
                min_commission,
                carry_blocked_orders=variant.carry_blocked_orders,
                pending_targets=pending_targets,
            )
            total_after_sells = _portfolio_value(cash, positions, trade_prices)
            cash, buy_commission, buy_turnover, buys, new_pending_buys = _execute_buys(
                day,
                cash,
                positions,
                trade_prices,
                price_rows,
                targets_for_day,
                total_after_sells,
                lot_size,
                open_commission,
                min_commission,
                carry_blocked_orders=variant.carry_blocked_orders,
                pending_targets=pending_targets,
            )
            if variant.carry_blocked_orders:
                pending_targets = _merge_pending(new_pending_sells, new_pending_buys)
            else:
                pending_targets = {}
            commission_total = sell_commission + buy_commission
            trade_rows.extend(sells)
            trade_rows.extend(buys)
            for row in sells + buys:
                if str(row.get("side") or "").endswith("_skipped"):
                    risk_rows.append(_risk_row(variant.name, day, "blocked_or_unfilled_order", row.get("code", ""), "retry" if variant.carry_blocked_orders else "record", row.get("reason", ""), "", ""))

        dividend_cash = 0.0
        for code, action in corporate_actions_by_date.get(day, {}).items():
            cash_per_share = action.get("net_cash_per_share", 0.0) or 0.0
            amount = positions.get(code, 0)
            if amount <= 0 or cash_per_share <= 0:
                continue
            cash_amount = amount * cash_per_share
            cash += cash_amount
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
        cash_weight = cash / portfolio_value if portfolio_value > 0 else 1.0
        if cash_weight > 0.15:
            risk_rows.append(_risk_row(variant.name, day, "cash_drag_high", "", "record", "cash weight above 15%", cash_weight, len(positions)))
        if not rebalance_like_day:
            risk_rows.append(_risk_row(variant.name, day, "non_rebalance_no_action", "", "no_trade", "no risk trigger; no active timing trade", cash_weight, len(positions)))

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
                "cash_weight": cash_weight,
                "selected_count": len(current_targets) if rebalance_like_day else 0,
                "holding_count": len(positions),
                "buy_turnover": buy_turnover,
                "sell_turnover": sell_turnover,
                "commission": commission_total,
                "dividend_cash": dividend_cash,
                "corporate_action_share_value": action_share_value,
                "benchmark_constituent_count": benchmark.get("constituent_count", ""),
                "rebalance": "1" if rebalance_like_day else "0",
            }
        )
        if rebalance_like_day:
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
    return daily_rows, holding_rows, trade_rows, dividend_rows, corporate_action_rows, risk_rows


def _execute_sells(
    day: str,
    cash: float,
    positions: dict[str, int],
    prices: dict[str, float],
    price_rows: dict[str, dict[str, float]],
    targets: dict[str, float],
    lot_size: int,
    commission_rate: float,
    min_commission: float,
    *,
    carry_blocked_orders: bool,
    pending_targets: dict[str, int],
) -> tuple[float, float, float, list[dict[str, Any]], dict[str, int]]:
    total_value = _portfolio_value(cash, positions, prices)
    commission_total = 0.0
    turnover = 0.0
    trades: list[dict[str, Any]] = []
    pending: dict[str, int] = {}
    codes = set(positions) | {code for code, target in pending_targets.items() if target < positions.get(code, 0)}
    for code in list(codes):
        price = prices.get(code)
        if price is None or price <= 0:
            continue
        target_amount = pending_targets.get(code)
        if target_amount is None:
            target_amount = _target_amount(total_value * targets.get(code, 0.0), price, lot_size)
        current = positions.get(code, 0)
        if current <= target_amount:
            continue
        amount = current - target_amount
        if target_amount > 0 and amount < lot_size:
            continue
        reason = _sell_block_reason(price_rows.get(code))
        if reason:
            trades.append(_trade_row(day, code, "sell_skipped", amount, price, 0.0, 0.0, target_amount, reason))
            if carry_blocked_orders:
                pending[code] = target_amount
            continue
        value = amount * price
        commission = _commission(value, commission_rate, min_commission)
        cash += value - commission
        positions[code] = target_amount
        if positions[code] <= 0:
            positions.pop(code, None)
        commission_total += commission
        turnover += value
        fill_reason = "delayed_fill_sell" if code in pending_targets else ""
        trades.append(_trade_row(day, code, "sell", amount, price, value, commission, target_amount, fill_reason))
    return cash, commission_total, turnover, trades, pending


def _execute_buys(
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
    *,
    carry_blocked_orders: bool,
    pending_targets: dict[str, int],
) -> tuple[float, float, float, list[dict[str, Any]], dict[str, int]]:
    commission_total = 0.0
    turnover = 0.0
    trades: list[dict[str, Any]] = []
    pending: dict[str, int] = {}
    codes = set(targets) | {code for code, target in pending_targets.items() if target > positions.get(code, 0)}
    for code in sorted(codes):
        price = prices.get(code)
        if price is None or price <= 0:
            continue
        target_amount = pending_targets.get(code)
        if target_amount is None:
            target_amount = _target_amount(total_value * targets.get(code, 0.0), price, lot_size)
        current = positions.get(code, 0)
        if target_amount <= current:
            continue
        amount = target_amount - current
        amount = min(amount, _affordable_amount(cash, price, lot_size, commission_rate, min_commission))
        if amount < lot_size:
            continue
        reason = _buy_block_reason(price_rows.get(code))
        if reason:
            trades.append(_trade_row(day, code, "buy_skipped", amount, price, 0.0, 0.0, target_amount, reason))
            if carry_blocked_orders:
                pending[code] = target_amount
            continue
        value = amount * price
        commission = _commission(value, commission_rate, min_commission)
        cash -= value + commission
        positions[code] = current + amount
        commission_total += commission
        turnover += value
        fill_reason = "delayed_fill_buy" if code in pending_targets else ""
        trades.append(_trade_row(day, code, "buy", amount, price, value, commission, target_amount, fill_reason))
    return cash, commission_total, turnover, trades, pending


def _build_freeze_manifest(
    *,
    config_path: Path,
    signals_csv: Path,
    baseline_summary_path: Path,
    production_summary_path: Path,
    config: dict[str, Any],
    signals: dict[str, dict[str, float]],
    baseline_summary: dict[str, Any],
    production_summary: dict[str, Any],
    configured_start_date: str,
    first_signal_date: str,
) -> dict[str, Any]:
    baseline_metrics = baseline_summary.get("metrics", {}) if isinstance(baseline_summary, dict) else {}
    health = baseline_summary.get("rebalance_order_health", {}) if isinstance(baseline_summary, dict) else {}
    return {
        "schema_version": 1,
        "created_at_utc": _now(),
        "strategy_id": str(config.get("project") or "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"),
        "freeze_status": "frozen_execution_robustness_candidate_not_tuned",
        "experiment_layer": "engineering_execution_robustness",
        "core_sleeves": [str(sector.get("sector_id") or "") for sector in config.get("sectors", [])],
        "config_path": str(config_path),
        "config_sha256": _sha256(config_path),
        "signals_csv": str(signals_csv),
        "signals_sha256": _sha256(signals_csv),
        "signal_count": len(signals),
        "startup_preload": {
            "configured_start_date": configured_start_date,
            "effective_first_signal_date": first_signal_date,
            "startup_gap_days": startup_gap_days(configured_start_date, first_signal_date),
            "start_date_was_silently_lifted_to_first_signal": False,
        },
        "baseline_summary_path": str(baseline_summary_path),
        "baseline_summary_sha256": _sha256(baseline_summary_path),
        "production_summary_path": str(production_summary_path),
        "production_line_status": production_summary.get("status", ""),
        "pm_gate_status": _safe_nested(production_summary, ["evidence", "pm_gate_summary", "status"]),
        "action_route_status": _safe_nested(production_summary, ["evidence", "action_route_summary", "status"]),
        "locked_metrics": {
            "strategy_return": baseline_metrics.get("strategy_return"),
            "annualized_return": baseline_metrics.get("annualized_return"),
            "benchmark_return": baseline_metrics.get("benchmark_return"),
            "excess_return": baseline_metrics.get("excess_return"),
            "max_drawdown": baseline_metrics.get("max_drawdown"),
            "sharpe": baseline_metrics.get("sharpe"),
            "trade_count": baseline_summary.get("trade_count"),
            "dividend_count": baseline_summary.get("dividend_count"),
            "rebalance_signal_count": health.get("rebalance_signal_count"),
            "first_executed_order_date": health.get("first_executed_order_date"),
            "first_position_date": health.get("first_position_date"),
        },
        "not_status": ["accepted_strategy", "platform_replication_passed", "live_trading_approved"],
        "pm_rules": [
            "This manifest freezes V57f inputs for execution robustness only.",
            "No factor recomputation, sleeve change, weight tuning or return-driven variant selection is allowed.",
            "2021-2026 remains platform-confirmation context, not clean acceptance evidence.",
        ],
    }


def _build_summary(
    freeze_manifest: dict[str, Any],
    variant_rows: list[dict[str, Any]],
    risk_rows: list[dict[str, Any]],
    variant_outputs: dict[str, dict[str, str]],
    report_path: Path,
) -> dict[str, Any]:
    baseline = next((row for row in variant_rows if row["execution_variant"] == "rebalance_day_open"), {})
    stable_rows = [
        row
        for row in variant_rows
        if row["rebalance_order_health"] == "pass"
        and _float(row.get("excess_return")) is not None
        and (_float(row.get("excess_return")) or 0.0) > 0
    ]
    return {
        "schema_version": 1,
        "created_at_utc": _now(),
        "strategy_id": freeze_manifest.get("strategy_id"),
        "status": "execution_robustness_completed_not_tuning",
        "experiment_layer": "engineering_execution_robustness",
        "baseline_variant": baseline.get("execution_variant", ""),
        "startup_preload": freeze_manifest.get("startup_preload", {}),
        "variant_count": len(variant_rows),
        "stable_positive_excess_variant_count": len(stable_rows),
        "risk_event_counts": _count_values(risk_rows, "risk_event"),
        "decision": _pm_decision(variant_rows),
        "next_gate": "prepare_clean_2026_10_08_paper_signal_or_joinquant_export_attribution",
        "not_status": ["accepted_strategy", "platform_replication_passed", "live_trading_approved"],
        "outputs": {
            "report": str(report_path),
            "variant_outputs": variant_outputs,
        },
        "pm_rules": freeze_manifest.get("pm_rules", []),
    }


def _pm_decision(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "needs_review_no_variants"
    health_ok = all(row.get("rebalance_order_health") == "pass" for row in rows)
    positive_excess = all((_float(row.get("excess_return")) or 0.0) > 0 for row in rows)
    if health_ok and positive_excess:
        return "execution_timing_not_fragile_no_strategy_change"
    return "needs_pm_review_execution_variant_fragility_or_order_health_issue"


def _build_report(summary: dict[str, Any], variant_rows: list[dict[str, Any]], risk_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# V57f Execution Robustness Packet",
        "",
        f"Created at UTC: `{summary['created_at_utc']}`",
        "",
        "## PM Decision",
        "",
        f"Decision: `{summary['decision']}`",
        "",
        "This packet changes execution assumptions only. It does not recompute factors, modify sleeves, tune weights, or approve live trading.",
        "",
        "## Execution Matrix",
        "",
        "| Variant | Return | Benchmark | Excess | Max drawdown | Sharpe | Order health | Skipped | Delayed fills |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |",
    ]
    for row in variant_rows:
        skipped = int(row.get("skipped_buy_count") or 0) + int(row.get("skipped_sell_count") or 0)
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row['execution_variant']}`",
                    _pct(row["strategy_return"]),
                    _pct(row["benchmark_return"]),
                    _pct(row["excess_return"]),
                    _pct(row["max_drawdown"]),
                    _fmt(row["sharpe"]),
                    f"`{row['rebalance_order_health']}`",
                    str(skipped),
                    str(row.get("delayed_fill_count") or 0),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Non-Rebalance Rule",
            "",
            "Non-rebalance days are no-action by default. The only allowed actions are delayed fills from blocked rebalance orders, sell-delay repair, drift/risk logging, and cash-drag measurement.",
            "",
            "## Risk Event Counts",
            "",
        ]
    )
    for event, count in sorted(_count_values(risk_rows, "risk_event").items()):
        lines.append(f"- `{event}`: `{count}`")
    lines.extend(
        [
            "",
            "## Next Gate",
            "",
            "`prepare_clean_2026_10_08_paper_signal_or_joinquant_export_attribution`",
            "",
        ]
    )
    return "\n".join(lines)


def _schedule_signals(signals: dict[str, dict[str, float]], trading_days: list[str], delay_days: int) -> dict[str, dict[str, float]]:
    if delay_days <= 0:
        return dict(signals)
    index = {day: i for i, day in enumerate(trading_days)}
    scheduled: dict[str, dict[str, float]] = {}
    for day, targets in signals.items():
        i = index.get(day)
        if i is None:
            continue
        target_i = min(i + delay_days, len(trading_days) - 1)
        scheduled[trading_days[target_i]] = targets
    return scheduled


def _slice_days(day: str, trading_days: list[str], slice_days: int) -> list[str]:
    index = {value: i for i, value in enumerate(trading_days)}
    start = index.get(day, 0)
    return trading_days[start : min(start + slice_days, len(trading_days))]


def _interpolate_weight(positions: dict[str, int], prices: dict[str, float], cash: float, code: str, target: float, progress: float) -> float:
    total = _portfolio_value(cash, positions, prices)
    current = positions.get(code, 0) * prices.get(code, 0.0) / total if total > 0 else 0.0
    return current + (target - current) * progress


def _load_signals(path: Path) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = defaultdict(dict)
    for row in read_csv_rows(path):
        day = str(row.get("trade_date") or "")[:10]
        code = str(row.get("code") or "")
        weight = to_float(row.get("target_weight"))
        if day and code and weight is not None and weight > 0:
            result[day][code] = result[day].get(code, 0.0) + weight
    return dict(sorted(result.items()))


def _load_prices(paths: list[Path], start_date: str, end_date: str) -> dict[str, dict[str, dict[str, float]]]:
    result: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)
    for path in paths:
        for row in read_csv_rows(path):
            day = str(row.get("date") or row.get("trade_date") or "")[:10]
            code = str(row.get("code") or "")
            if not day or not code or day < start_date or day > end_date:
                continue
            open_price = to_float(row.get("open"))
            close_price = to_float(row.get("close"))
            if open_price is None or close_price is None or open_price <= 0 or close_price <= 0:
                continue
            result[day][code] = {
                "open": open_price,
                "close": close_price,
                "high": to_float(row.get("high")),
                "low": to_float(row.get("low")),
                "high_limit": to_float(row.get("high_limit")),
                "low_limit": to_float(row.get("low_limit")),
                "paused": to_float(row.get("paused")) or 0.0,
            }
    return dict(sorted(result.items()))


def _load_corporate_actions(paths: list[Path], start_date: str, end_date: str) -> dict[str, dict[str, dict[str, float]]]:
    result: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)
    for path in paths:
        if not path.exists():
            continue
        for row in read_csv_rows(path):
            code = str(row.get("code") or "")
            day = str(row.get("ex_date") or row.get("pay_date") or "")[:10]
            cash = to_float(row.get("net_cash_per_share") or row.get("cash_per_share"))
            share_ratio = to_float(row.get("stock_dividend_ratio"))
            if share_ratio is None:
                bonus = to_float(row.get("bonus_share_per_10_shares")) or 0.0
                transfer = to_float(row.get("transfer_share_per_10_shares")) or 0.0
                share_ratio = (bonus + transfer) / 10.0
            if not code or not day or day < start_date or day > end_date:
                continue
            cash = cash or 0.0
            share_ratio = share_ratio or 0.0
            if cash <= 0 and share_ratio <= 0:
                continue
            bucket = result[day].setdefault(code, {"net_cash_per_share": 0.0, "stock_dividend_ratio": 0.0})
            bucket["net_cash_per_share"] += cash
            bucket["stock_dividend_ratio"] += share_ratio
    return dict(result)


def _build_equal_weight_benchmark(
    prices_by_date: dict[str, dict[str, dict[str, float]]],
    corporate_actions_by_date: dict[str, dict[str, dict[str, float]]],
    start_date: str,
    end_date: str,
) -> list[dict[str, Any]]:
    last_close: dict[str, float] = {}
    nav = 1.0
    rows: list[dict[str, Any]] = []
    for day, price_rows in sorted(prices_by_date.items()):
        if day < start_date or day > end_date:
            continue
        returns = []
        dividend_constituents = 0
        for code, price in price_rows.items():
            previous = last_close.get(code)
            close = price.get("close")
            if previous is not None and previous > 0 and close is not None and close > 0:
                action = corporate_actions_by_date.get(day, {}).get(code, {})
                dividend_return = (action.get("net_cash_per_share", 0.0) or 0.0) / previous
                stock_return = (action.get("stock_dividend_ratio", 0.0) or 0.0) * close / previous
                if dividend_return:
                    dividend_constituents += 1
                returns.append(close / previous - 1.0 + dividend_return + stock_return)
            if close is not None and close > 0:
                last_close[code] = close
        benchmark_return = mean(returns) if returns else 0.0
        nav *= 1.0 + benchmark_return
        rows.append(
            {
                "trade_date": day,
                "benchmark_return": benchmark_return,
                "benchmark_nav": nav,
                "constituent_count": len(returns),
                "dividend_constituent_count": dividend_constituents,
            }
        )
    return rows


def _execution_price(row: dict[str, float], alpha: float) -> float:
    open_price = row.get("open") or 0.0
    close_price = row.get("close") or open_price
    return open_price + (close_price - open_price) * alpha


def _buy_block_reason(price_row: dict[str, float] | None) -> str:
    if not price_row:
        return ""
    if (price_row.get("paused") or 0.0) >= 1.0:
        return "paused"
    price = _execution_price(price_row, 0.0)
    high_limit = price_row.get("high_limit")
    if high_limit is not None and high_limit > 0 and price >= high_limit * 0.999999:
        return "high_limit"
    return ""


def _sell_block_reason(price_row: dict[str, float] | None) -> str:
    if not price_row:
        return ""
    if (price_row.get("paused") or 0.0) >= 1.0:
        return "paused"
    price = _execution_price(price_row, 0.0)
    low_limit = price_row.get("low_limit")
    if low_limit is not None and low_limit > 0 and price <= low_limit * 1.000001:
        return "low_limit"
    return ""


def _trade_row(day: str, code: str, side: str, amount: int, price: float, value: float, commission: float, target_amount: int, reason: str) -> dict[str, Any]:
    return {
        "trade_date": day,
        "code": code,
        "side": side,
        "amount": amount,
        "price": price,
        "value": value,
        "commission": commission,
        "target_amount": target_amount,
        "reason": reason,
    }


def _risk_row(variant: str, day: str, event: str, code: Any, action: str, detail: Any, cash_weight: Any, holding_count: Any) -> dict[str, Any]:
    return {
        "execution_variant": variant,
        "trade_date": day,
        "risk_event": event,
        "code": code,
        "action": action,
        "detail": detail,
        "cash_weight": cash_weight,
        "holding_count": holding_count,
    }


def _merge_pending(*items: dict[str, int]) -> dict[str, int]:
    result: dict[str, int] = {}
    for item in items:
        result.update(item)
    return result


def _portfolio_value(cash: float, positions: dict[str, int], prices: dict[str, float]) -> float:
    return cash + sum(amount * prices.get(code, 0.0) for code, amount in positions.items())


def _target_amount(target_value: float, price: float, lot_size: int) -> int:
    if target_value <= 0 or price <= 0:
        return 0
    return int(target_value / price / lot_size) * lot_size


def _affordable_amount(cash: float, price: float, lot_size: int, commission_rate: float, min_commission: float) -> int:
    lots = int(cash / (price * lot_size))
    while lots > 0:
        amount = lots * lot_size
        value = amount * price
        if value + _commission(value, commission_rate, min_commission) <= cash:
            return amount
        lots -= 1
    return 0


def _commission(value: float, rate: float, minimum: float) -> float:
    if value <= 0:
        return 0.0
    return max(value * rate, minimum)


def _compute_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}
    strategy_returns = [float(row["strategy_return"]) for row in rows]
    benchmark_returns = [float(row["benchmark_return"]) for row in rows]
    excess_returns = [float(row["excess_return"]) for row in rows]
    dates = [str(row["trade_date"]) for row in rows]
    strategy_curve = _curve(strategy_returns)
    benchmark_curve = _curve(benchmark_returns)
    excess_curve = _curve(excess_returns)
    annual_factor = 252
    strategy_return = strategy_curve[-1] - 1.0
    benchmark_return = benchmark_curve[-1] - 1.0
    annualized = _annualize(strategy_return, len(strategy_returns), annual_factor)
    benchmark_annualized = _annualize(benchmark_return, len(benchmark_returns), annual_factor)
    beta = _beta(strategy_returns, benchmark_returns)
    alpha = annualized - beta * benchmark_annualized if annualized is not None and beta is not None and benchmark_annualized is not None else None
    max_dd, dd_start, dd_end = _max_drawdown(strategy_curve, dates)
    excess_max_dd, _ex_start, _ex_end = _max_drawdown(excess_curve, dates)
    profit_returns = [ret for ret in strategy_returns if ret > 0]
    loss_returns = [ret for ret in strategy_returns if ret < 0]
    return {
        "strategy_return": strategy_return,
        "annualized_return": annualized,
        "excess_return": strategy_return - benchmark_return,
        "benchmark_return": benchmark_return,
        "alpha": alpha,
        "beta": beta,
        "sharpe": _sharpe(strategy_returns, annual_factor),
        "win_rate": _positive_ratio(strategy_returns),
        "profit_loss_ratio": (mean(profit_returns) / abs(mean(loss_returns))) if profit_returns and loss_returns else None,
        "max_drawdown": max_dd,
        "sortino": _sortino(strategy_returns, annual_factor),
        "mean_excess_return": mean(excess_returns),
        "excess_max_drawdown": excess_max_dd,
        "excess_sharpe": _sharpe(excess_returns, annual_factor),
        "daily_win_rate": _positive_ratio(strategy_returns),
        "profit_count": len(profit_returns),
        "loss_count": len(loss_returns),
        "information_ratio": _information_ratio(excess_returns, annual_factor),
        "strategy_volatility": _volatility(strategy_returns, annual_factor),
        "benchmark_volatility": _volatility(benchmark_returns, annual_factor),
        "max_drawdown_interval": f"{dd_start},{dd_end}" if dd_start and dd_end else None,
        "annual_factor": annual_factor,
    }


def _curve(returns: list[float]) -> list[float]:
    nav = 1.0
    values = []
    for ret in returns:
        nav *= 1.0 + ret
        values.append(nav)
    return values


def _annualize(total_return: float, periods: int, annual_factor: int) -> float | None:
    if periods <= 0 or total_return <= -1:
        return None
    return (1.0 + total_return) ** (annual_factor / periods) - 1.0


def _volatility(returns: list[float], annual_factor: int) -> float | None:
    if len(returns) < 2:
        return None
    return pstdev(returns) * math.sqrt(annual_factor)


def _sharpe(returns: list[float], annual_factor: int) -> float | None:
    vol = pstdev(returns) if len(returns) >= 2 else 0.0
    return (mean(returns) / vol) * math.sqrt(annual_factor) if vol > 0 else None


def _sortino(returns: list[float], annual_factor: int) -> float | None:
    downside = [min(0.0, ret) for ret in returns]
    downside_dev = math.sqrt(mean([ret * ret for ret in downside])) if downside else 0.0
    return (mean(returns) / downside_dev) * math.sqrt(annual_factor) if downside_dev > 0 else None


def _information_ratio(excess_returns: list[float], annual_factor: int) -> float | None:
    tracking_error = pstdev(excess_returns) if len(excess_returns) >= 2 else 0.0
    return (mean(excess_returns) / tracking_error) * math.sqrt(annual_factor) if tracking_error > 0 else None


def _beta(strategy_returns: list[float], benchmark_returns: list[float]) -> float | None:
    if len(strategy_returns) != len(benchmark_returns) or len(strategy_returns) < 2:
        return None
    bm = mean(benchmark_returns)
    sm = mean(strategy_returns)
    variance = sum((ret - bm) ** 2 for ret in benchmark_returns)
    if variance == 0:
        return None
    covariance = sum((s - sm) * (b - bm) for s, b in zip(strategy_returns, benchmark_returns))
    return covariance / variance


def _max_drawdown(curve: list[float], dates: list[str]) -> tuple[float | None, str | None, str | None]:
    if not curve:
        return None, None, None
    peak = curve[0]
    peak_date = dates[0]
    max_dd = 0.0
    dd_start = dates[0]
    dd_end = dates[0]
    for value, day in zip(curve, dates):
        if value > peak:
            peak = value
            peak_date = day
        if peak > 0:
            drawdown = value / peak - 1.0
            if drawdown < max_dd:
                max_dd = drawdown
                dd_start = peak_date
                dd_end = day
    return abs(max_dd), dd_start, dd_end


def _positive_ratio(values: list[float]) -> float | None:
    return sum(1 for value in values if value > 0) / len(values) if values else None


def _variant_conclusion(metrics: dict[str, Any], order_health: dict[str, Any]) -> str:
    if order_health.get("needs_review"):
        return "needs_review_order_health"
    excess = metrics.get("excess_return")
    max_drawdown = metrics.get("max_drawdown")
    if excess is not None and excess > 0 and max_drawdown is not None and max_drawdown <= 0.2:
        return "pass_execution_not_fragile"
    if excess is not None and excess > 0:
        return "needs_review_drawdown"
    return "needs_review_excess_not_positive"


def _count_values(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(field) or "")
        counts[value] = counts.get(value, 0) + 1
    return counts


def _fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    return fields


def _num(value: Any) -> str:
    if value is None:
        return ""
    return f"{float(value):.12g}"


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pct(value: Any) -> str:
    parsed = _float(value)
    return "" if parsed is None else f"{parsed * 100:.2f}%"


def _fmt(value: Any) -> str:
    parsed = _float(value)
    return "" if parsed is None else f"{parsed:.3f}"


def _sha256(path: Path) -> str:
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return _read_json(path)


def _safe_nested(payload: dict[str, Any], keys: list[str]) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return ""
        current = current.get(key)
    return "" if current is None else current


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
