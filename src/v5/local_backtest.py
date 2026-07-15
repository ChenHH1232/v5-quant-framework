from __future__ import annotations

import argparse
import csv
import html
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any

from v5.engine import load_spec
from v5.validation_runner import _apply_value_trap_guard, _score_date_rows


DEFAULT_BACKTEST_START = "2021-05-01"
DEFAULT_BACKTEST_END = "2026-05-31"

METRIC_ORDER = [
    ("strategy_return", "策略收益", "percent"),
    ("annualized_return", "策略年化收益", "percent"),
    ("excess_return", "超额收益", "percent"),
    ("benchmark_return", "基准收益", "percent"),
    ("alpha", "阿尔法", "decimal"),
    ("beta", "贝塔", "decimal"),
    ("sharpe", "夏普比率", "decimal"),
    ("win_rate", "胜率", "decimal"),
    ("profit_loss_ratio", "盈亏比", "decimal"),
    ("max_drawdown", "最大回撤", "percent"),
    ("sortino", "索提诺比率", "decimal"),
    ("mean_excess_return", "日均超额收益", "percent"),
    ("excess_max_drawdown", "超额收益最大回撤", "percent"),
    ("excess_sharpe", "超额收益夏普比率", "decimal"),
    ("daily_win_rate", "日胜率", "decimal"),
    ("profit_count", "盈利次数", "integer"),
    ("loss_count", "亏损次数", "integer"),
    ("information_ratio", "信息比率", "decimal"),
    ("strategy_volatility", "策略波动率", "decimal"),
    ("benchmark_volatility", "基准波动率", "decimal"),
    ("max_drawdown_interval", "最大回撤区间", "text"),
]


@dataclass(frozen=True)
class BacktestOptions:
    save_periods: bool = False
    save_holdings: bool = False
    start_date: str = DEFAULT_BACKTEST_START
    end_date: str = DEFAULT_BACKTEST_END
    min_coverage_ratio: float = 0.8
    execution_mode: str = "ideal_equal_weight"
    initial_cash: float = 2_000_000.0
    target_exposure: float = 0.995
    lot_size: int = 100
    open_commission: float = 0.0003
    close_commission: float = 0.0003
    min_commission: float = 5.0
    defensive_mode: str = "none"
    defensive_ma_days: int = 252
    defensive_risk_exposure: float = 0.5


def run_local_backtest(spec_path: Path, panel_path: Path, out_dir: Path, options: BacktestOptions | None = None) -> Path:
    options = options or BacktestOptions()
    spec = load_spec(spec_path)
    all_rows = _load_panel(panel_path)
    rows = _filter_rows_by_window(all_rows, options.start_date, options.end_date)
    out = out_dir / spec.strategy_id
    out.mkdir(parents=True, exist_ok=True)

    if options.execution_mode == "joinquant_like":
        period_rows, holding_rows, skipped_periods = _build_joinquant_like_period_returns(rows, spec.raw, options)
    else:
        period_rows, holding_rows, skipped_periods = _build_period_returns(rows, spec.raw, options.min_coverage_ratio)
    metrics = _compute_metrics(period_rows)
    benchmark_sources = sorted({str(row.get("benchmark_source")) for row in rows if row.get("benchmark_source")})
    summary = {
        "strategy_id": spec.strategy_id,
        "panel": str(panel_path),
        "window": {
            "start_date": options.start_date,
            "end_date": options.end_date,
            "policy": "default_v4_comparison_window",
        },
        "source_row_count": len(all_rows),
        "filtered_row_count": len(rows),
        "period_count": len(period_rows),
        "skipped_period_count": len(skipped_periods),
        "skipped_periods": skipped_periods,
        "coverage_filter": {
            "min_coverage_ratio": options.min_coverage_ratio,
            "policy": "skip_rebalance_periods_with_too_few_securities",
        },
        "security_count": len({row["code"] for row in rows}),
        "benchmark_sources": benchmark_sources or ["sample_equal_weight_fallback"],
        "execution": {
            "mode": options.execution_mode,
            "initial_cash": options.initial_cash if options.execution_mode == "joinquant_like" else None,
            "target_exposure": options.target_exposure if options.execution_mode == "joinquant_like" else None,
            "lot_size": options.lot_size if options.execution_mode == "joinquant_like" else None,
            "open_commission": options.open_commission if options.execution_mode == "joinquant_like" else None,
            "close_commission": options.close_commission if options.execution_mode == "joinquant_like" else None,
            "min_commission": options.min_commission if options.execution_mode == "joinquant_like" else None,
        },
        "metrics": metrics,
        "metric_order": [
            {"key": key, "label": label, "format": fmt}
            for key, label, fmt in METRIC_ORDER
        ],
        "outputs": {
            "html_report": "report.html",
            "summary": "summary.json",
            "period_returns": "period_returns.csv" if options.save_periods else None,
            "holdings": "holdings.csv" if options.save_holdings else None,
        },
        "notes": [
            f"Metrics are computed only for the configured window: {options.start_date} to {options.end_date}.",
            f"Rebalance periods below {options.min_coverage_ratio:.0%} of max date coverage are skipped.",
            f"Execution mode: {options.execution_mode}.",
            "If the panel is quarterly or monthly, labels such as daily win rate should be read as period win rate.",
            "JoinQuant-like metrics require daily panel data for closest platform matching.",
        ],
    }

    _write_json(out / "summary.json", summary)
    _write_html(
        out / "report.html",
        spec.raw["meta"]["name"],
        metrics,
        period_rows,
        summary["notes"],
        summary["window"],
        summary["benchmark_sources"],
    )
    if options.save_periods:
        _write_csv(out / "period_returns.csv", list(period_rows[0].keys()) if period_rows else [], period_rows)
    if options.save_holdings:
        _write_csv(out / "holdings.csv", list(holding_rows[0].keys()) if holding_rows else [], holding_rows)
    return out / "report.html"


def _load_panel(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    result = []
    for row in rows:
        ret = _to_float(row.get("total_return"))
        if ret is None:
            ret = _to_float(row.get("future_return"))
        if row.get("trade_date") and row.get("code") and ret is not None:
            item = dict(row)
            item["future_return"] = ret
            item["benchmark_return"] = _to_float(row.get("benchmark_return"))
            result.append(item)
    return result


def _filter_rows_by_window(rows: list[dict[str, Any]], start_date: str, end_date: str) -> list[dict[str, Any]]:
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    if end < start:
        raise ValueError(f"end_date must be on or after start_date: {start_date} > {end_date}")
    return [
        row
        for row in rows
        if start <= _parse_date(str(row["trade_date"])) <= end
    ]


def _build_period_returns(
    rows: list[dict[str, Any]],
    raw_spec: dict[str, Any],
    min_coverage_ratio: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_date[row["trade_date"]].append(row)

    max_date_coverage = max((len(date_rows) for date_rows in by_date.values()), default=0)
    min_required_coverage = math.ceil(max_date_coverage * min_coverage_ratio) if max_date_coverage else 0

    selection_count = int(raw_spec["portfolio"]["selection_count"])
    factors = raw_spec["signals"]["factors"]
    weights = raw_spec["signals"]["scoring"].get("weights", {})
    period_rows: list[dict[str, Any]] = []
    holding_rows: list[dict[str, Any]] = []
    strategy_nav = 1.0
    benchmark_nav = 1.0
    excess_nav = 1.0
    skipped_periods: list[dict[str, Any]] = []

    for trade_date, date_rows in sorted(by_date.items()):
        date_coverage = len(date_rows)
        if date_coverage < min_required_coverage:
            skipped_periods.append(
                {
                    "trade_date": trade_date,
                    "security_count": date_coverage,
                    "required_security_count": min_required_coverage,
                    "max_date_coverage": max_date_coverage,
                    "reason": "coverage_below_threshold",
                }
            )
            continue

        scored = _score_date_rows(date_rows, factors, weights)
        eligible = _apply_value_trap_guard(scored)
        selected = sorted(eligible, key=lambda item: item["score"], reverse=True)[:selection_count]
        selected_count = len(selected)
        cash_weight = max(0.0, 1.0 - (selected_count / selection_count))
        invested_weight = 1.0 - cash_weight

        if selected:
            selected_return = mean(float(row["future_return"]) for row in selected)
            strategy_return = selected_return * invested_weight
            selected_codes = [row["code"] for row in selected]
        else:
            strategy_return = 0.0
            selected_codes = []

        benchmark_values = [row["benchmark_return"] for row in date_rows if row.get("benchmark_return") is not None]
        if benchmark_values:
            benchmark_return = mean(benchmark_values)
        else:
            benchmark_return = mean(float(row["future_return"]) for row in date_rows)

        strategy_nav *= 1.0 + strategy_return
        benchmark_nav *= 1.0 + benchmark_return
        excess_return = strategy_return - benchmark_return
        excess_nav *= 1.0 + excess_return

        next_trade_date = selected[0].get("next_trade_date", "") if selected else date_rows[0].get("next_trade_date", "")
        period_rows.append(
            {
                "trade_date": trade_date,
                "next_trade_date": next_trade_date,
                "strategy_return": strategy_return,
                "benchmark_return": benchmark_return,
                "excess_return": excess_return,
                "strategy_nav": strategy_nav,
                "benchmark_nav": benchmark_nav,
                "excess_nav": excess_nav,
                "selected_count": selected_count,
                "date_security_count": date_coverage,
                "cash_weight": cash_weight,
                "benchmark_source": date_rows[0].get("benchmark_source", "sample_equal_weight_fallback"),
                "selected_codes": ";".join(selected_codes),
            }
        )
        for row in selected:
            holding_rows.append(
                {
                    "trade_date": trade_date,
                    "next_trade_date": next_trade_date,
                    "code": row["code"],
                    "target_weight": (invested_weight / selected_count) if selected_count else 0.0,
                    "future_return": row["future_return"],
                    "score": row.get("score", ""),
                }
            )

    return period_rows, holding_rows, skipped_periods


def _build_joinquant_like_period_returns(
    rows: list[dict[str, Any]],
    raw_spec: dict[str, Any],
    options: BacktestOptions,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_date[row["trade_date"]].append(row)

    max_date_coverage = max((len(date_rows) for date_rows in by_date.values()), default=0)
    min_required_coverage = math.ceil(max_date_coverage * options.min_coverage_ratio) if max_date_coverage else 0
    selection_count = int(raw_spec["portfolio"]["selection_count"])
    factors = raw_spec["signals"]["factors"]
    weights = raw_spec["signals"]["scoring"].get("weights", {})

    cash = float(options.initial_cash)
    positions: dict[str, int] = {}
    last_prices: dict[str, float] = {}
    prev_total_value = cash
    strategy_nav = 1.0
    benchmark_nav = 1.0
    excess_nav = 1.0
    period_rows: list[dict[str, Any]] = []
    holding_rows: list[dict[str, Any]] = []
    skipped_periods: list[dict[str, Any]] = []

    for trade_date, date_rows in sorted(by_date.items()):
        date_coverage = len(date_rows)
        if date_coverage < min_required_coverage:
            skipped_periods.append(
                {
                    "trade_date": trade_date,
                    "security_count": date_coverage,
                    "required_security_count": min_required_coverage,
                    "max_date_coverage": max_date_coverage,
                    "reason": "coverage_below_threshold",
                }
            )
            continue

        row_by_code = {row["code"]: row for row in date_rows}
        current_prices = {
            code: price
            for code, row in row_by_code.items()
            if (price := _to_float(row.get("close"))) is not None and price > 0
        }
        last_prices.update(current_prices)

        scored = _score_date_rows(date_rows, factors, weights)
        eligible = _apply_value_trap_guard(scored)
        selected = sorted(eligible, key=lambda item: item["score"], reverse=True)[:selection_count]
        selected_codes = [row["code"] for row in selected]
        selected_by_code = {row["code"]: row for row in selected}
        target_codes = set(selected_codes)

        total_before_trade = _portfolio_value(cash, positions, last_prices)
        cash, sell_commission, sell_turnover = _execute_joinquant_like_sells(
            cash,
            positions,
            last_prices,
            target_codes,
            selected_codes,
            selection_count,
            total_before_trade,
            options,
        )
        total_after_sells = _portfolio_value(cash, positions, last_prices)
        cash, buy_commission, buy_turnover = _execute_joinquant_like_buys(
            cash,
            positions,
            last_prices,
            selected_codes,
            selection_count,
            total_after_sells,
            options,
        )

        end_prices = dict(last_prices)
        for code, row in row_by_code.items():
            start_price = current_prices.get(code)
            if start_price is None:
                continue
            end_prices[code] = start_price * (1.0 + float(row["future_return"]))

        end_total_value = _portfolio_value(cash, positions, end_prices)
        strategy_return = (end_total_value / prev_total_value) - 1.0 if prev_total_value > 0 else 0.0
        prev_total_value = end_total_value
        last_prices.update(end_prices)

        benchmark_values = [row["benchmark_return"] for row in date_rows if row.get("benchmark_return") is not None]
        benchmark_return = mean(benchmark_values) if benchmark_values else mean(float(row["future_return"]) for row in date_rows)
        strategy_nav *= 1.0 + strategy_return
        benchmark_nav *= 1.0 + benchmark_return
        excess_return = strategy_return - benchmark_return
        excess_nav *= 1.0 + excess_return
        selected_count = len(selected)
        invested_value = sum(positions.get(code, 0) * end_prices.get(code, 0.0) for code in positions)
        cash_weight = cash / end_total_value if end_total_value > 0 else 1.0
        next_trade_date = selected[0].get("next_trade_date", "") if selected else date_rows[0].get("next_trade_date", "")

        period_rows.append(
            {
                "trade_date": trade_date,
                "next_trade_date": next_trade_date,
                "strategy_return": strategy_return,
                "benchmark_return": benchmark_return,
                "excess_return": excess_return,
                "strategy_nav": strategy_nav,
                "benchmark_nav": benchmark_nav,
                "excess_nav": excess_nav,
                "selected_count": selected_count,
                "date_security_count": date_coverage,
                "cash_weight": cash_weight,
                "benchmark_source": date_rows[0].get("benchmark_source", "sample_equal_weight_fallback"),
                "selected_codes": ";".join(selected_codes),
                "portfolio_value": end_total_value,
                "cash": cash,
                "invested_value": invested_value,
                "buy_turnover": buy_turnover,
                "sell_turnover": sell_turnover,
                "commission": buy_commission + sell_commission,
            }
        )
        for code in selected_codes:
            amount = positions.get(code, 0)
            value = amount * end_prices.get(code, 0.0)
            holding_rows.append(
                {
                    "trade_date": trade_date,
                    "next_trade_date": next_trade_date,
                    "code": code,
                    "target_weight": (options.target_exposure / selection_count) if selected_count else 0.0,
                    "actual_weight": value / end_total_value if end_total_value > 0 else 0.0,
                    "amount": amount,
                    "close": end_prices.get(code, ""),
                    "future_return": row_by_code.get(code, {}).get("future_return", ""),
                    "score": selected_by_code.get(code, {}).get("score", ""),
                }
            )

    return period_rows, holding_rows, skipped_periods


def _execute_joinquant_like_sells(
    cash: float,
    positions: dict[str, int],
    prices: dict[str, float],
    target_codes: set[str],
    selected_codes: list[str],
    selection_count: int,
    total_value: float,
    options: BacktestOptions,
) -> tuple[float, float, float]:
    commission_total = 0.0
    turnover = 0.0
    target_values = {
        code: total_value * options.target_exposure / selection_count
        for code in selected_codes
    } if selected_codes and selection_count > 0 else {}
    for code in list(positions.keys()):
        price = prices.get(code)
        if price is None or price <= 0:
            continue
        current_amount = positions.get(code, 0)
        target_amount = 0
        if code in target_codes:
            target_amount = _target_lot_amount(target_values.get(code, 0.0), price, options.lot_size)
        if current_amount <= target_amount:
            continue
        sell_amount = current_amount - target_amount
        if target_amount != 0 and sell_amount < options.lot_size:
            continue
        trade_value = sell_amount * price
        commission = _commission(trade_value, options.close_commission, options.min_commission)
        positions[code] = target_amount
        if positions[code] <= 0:
            positions.pop(code, None)
        cash += trade_value - commission
        commission_total += commission
        turnover += trade_value
    return cash, commission_total, turnover


def _execute_joinquant_like_buys(
    cash: float,
    positions: dict[str, int],
    prices: dict[str, float],
    selected_codes: list[str],
    selection_count: int,
    total_value: float,
    options: BacktestOptions,
) -> tuple[float, float, float]:
    commission_total = 0.0
    turnover = 0.0
    if not selected_codes or selection_count <= 0:
        return cash, commission_total, turnover
    for code in selected_codes:
        price = prices.get(code)
        if price is None or price <= 0:
            continue
        current_amount = positions.get(code, 0)
        target_value = total_value * options.target_exposure / selection_count
        target_amount = _target_lot_amount(target_value, price, options.lot_size)
        if target_amount <= current_amount:
            continue
        buy_amount = target_amount - current_amount
        if buy_amount < options.lot_size:
            continue
        affordable_amount = _affordable_lot_amount(cash, price, options)
        buy_amount = min(buy_amount, affordable_amount)
        if buy_amount < options.lot_size:
            continue
        trade_value = buy_amount * price
        commission = _commission(trade_value, options.open_commission, options.min_commission)
        cash -= trade_value + commission
        positions[code] = current_amount + buy_amount
        commission_total += commission
        turnover += trade_value
    return cash, commission_total, turnover


def _portfolio_value(cash: float, positions: dict[str, int], prices: dict[str, float]) -> float:
    return cash + sum(amount * prices.get(code, 0.0) for code, amount in positions.items())


def _target_lot_amount(target_value: float, price: float, lot_size: int) -> int:
    if target_value <= 0 or price <= 0:
        return 0
    return int(target_value / price / lot_size) * lot_size


def _affordable_lot_amount(cash: float, price: float, options: BacktestOptions) -> int:
    if cash <= 0 or price <= 0:
        return 0
    lots = int(cash / (price * options.lot_size))
    while lots > 0:
        amount = lots * options.lot_size
        value = amount * price
        if value + _commission(value, options.open_commission, options.min_commission) <= cash:
            return amount
        lots -= 1
    return 0


def _commission(value: float, rate: float, minimum: float) -> float:
    if value <= 0:
        return 0.0
    return max(value * rate, minimum)


def _compute_metrics(period_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not period_rows:
        return {key: None for key, _label, _fmt in METRIC_ORDER}

    strategy_returns = [float(row["strategy_return"]) for row in period_rows]
    benchmark_returns = [float(row["benchmark_return"]) for row in period_rows]
    excess_returns = [float(row["excess_return"]) for row in period_rows]
    dates = [row["trade_date"] for row in period_rows]
    annual_factor = _infer_annual_factor(dates)

    strategy_curve = _curve(strategy_returns)
    benchmark_curve = _curve(benchmark_returns)
    excess_curve = _curve(excess_returns)

    strategy_return = strategy_curve[-1] - 1.0
    benchmark_return = benchmark_curve[-1] - 1.0
    excess_return = strategy_return - benchmark_return
    annualized = _annualize(strategy_return, len(strategy_returns), annual_factor)
    benchmark_annualized = _annualize(benchmark_return, len(benchmark_returns), annual_factor)

    strategy_vol = _annualized_vol(strategy_returns, annual_factor)
    benchmark_vol = _annualized_vol(benchmark_returns, annual_factor)
    beta = _beta(strategy_returns, benchmark_returns)
    alpha = None
    if beta is not None and annualized is not None and benchmark_annualized is not None:
        alpha = annualized - beta * benchmark_annualized

    max_dd, dd_start, dd_end = _max_drawdown(strategy_curve, dates)
    excess_max_dd, _ex_start, _ex_end = _max_drawdown(excess_curve, dates)

    profit_returns = [ret for ret in strategy_returns if ret > 0]
    loss_returns = [ret for ret in strategy_returns if ret < 0]
    profit_loss_ratio = None
    if profit_returns and loss_returns:
        profit_loss_ratio = mean(profit_returns) / abs(mean(loss_returns))

    metrics = {
        "strategy_return": strategy_return,
        "annualized_return": annualized,
        "excess_return": excess_return,
        "benchmark_return": benchmark_return,
        "alpha": alpha,
        "beta": beta,
        "sharpe": _sharpe(strategy_returns, annual_factor),
        "win_rate": _positive_ratio(strategy_returns),
        "profit_loss_ratio": profit_loss_ratio,
        "max_drawdown": max_dd,
        "sortino": _sortino(strategy_returns, annual_factor),
        "mean_excess_return": mean(excess_returns) if excess_returns else None,
        "excess_max_drawdown": excess_max_dd,
        "excess_sharpe": _sharpe(excess_returns, annual_factor),
        "daily_win_rate": _positive_ratio(strategy_returns),
        "profit_count": len(profit_returns),
        "loss_count": len(loss_returns),
        "information_ratio": _information_ratio(excess_returns, annual_factor),
        "strategy_volatility": strategy_vol,
        "benchmark_volatility": benchmark_vol,
        "max_drawdown_interval": f"{dd_start},{dd_end}" if dd_start and dd_end else None,
        "annual_factor": annual_factor,
    }
    return metrics


def _infer_annual_factor(dates: list[str]) -> int:
    parsed = [_parse_date(value) for value in dates]
    deltas = [(right - left).days for left, right in zip(parsed, parsed[1:]) if (right - left).days > 0]
    if not deltas:
        return 252
    med = median(deltas)
    if med <= 3:
        return 252
    if med <= 10:
        return 52
    if med <= 45:
        return 12
    return 4


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


def _annualized_vol(returns: list[float], annual_factor: int) -> float | None:
    if len(returns) < 2:
        return None
    return pstdev(returns) * math.sqrt(annual_factor)


def _sharpe(returns: list[float], annual_factor: int) -> float | None:
    if len(returns) < 2:
        return None
    vol = pstdev(returns)
    if vol == 0:
        return None
    return (mean(returns) / vol) * math.sqrt(annual_factor)


def _sortino(returns: list[float], annual_factor: int) -> float | None:
    downside = [min(0.0, ret) for ret in returns]
    downside_dev = math.sqrt(mean([ret * ret for ret in downside])) if downside else 0.0
    if downside_dev == 0:
        return None
    return (mean(returns) / downside_dev) * math.sqrt(annual_factor)


def _information_ratio(excess_returns: list[float], annual_factor: int) -> float | None:
    if len(excess_returns) < 2:
        return None
    tracking_error = pstdev(excess_returns)
    if tracking_error == 0:
        return None
    return (mean(excess_returns) / tracking_error) * math.sqrt(annual_factor)


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
    for value, current_date in zip(curve, dates):
        if value > peak:
            peak = value
            peak_date = current_date
        if peak <= 0:
            continue
        drawdown = value / peak - 1.0
        if drawdown < max_dd:
            max_dd = drawdown
            dd_start = peak_date
            dd_end = current_date
    return abs(max_dd), dd_start, dd_end


def _positive_ratio(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(1 for value in values if value > 0) / len(values)


def _parse_date(value: str):
    return datetime.strptime(value[:10], "%Y-%m-%d").date()


def _to_float(value: Any) -> float | None:
    if value in {None, "", "nan", "NaN", "None"}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    if not fieldnames:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_html(
    path: Path,
    title: str,
    metrics: dict[str, Any],
    period_rows: list[dict[str, Any]],
    notes: list[str],
    window: dict[str, str],
    benchmark_sources: list[str],
) -> None:
    chart = _svg_chart(period_rows)
    metric_cards = "\n".join(_metric_card(key, label, fmt, metrics.get(key)) for key, label, fmt in METRIC_ORDER)
    note_items = "\n".join(f"<li>{html.escape(note)}</li>" for note in notes)
    window_text = f"{window['start_date']} 至 {window['end_date']}"
    benchmark_text = ", ".join(benchmark_sources)
    body = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} - Local Backtest</title>
  <style>
    body {{ margin: 0; font-family: Arial, "Microsoft YaHei", sans-serif; background: #f5f7fa; color: #1f2933; }}
    header {{ padding: 18px 26px; background: #ffffff; border-bottom: 1px solid #d8dee8; }}
    h1 {{ margin: 0; font-size: 18px; }}
    main {{ padding: 18px 26px 30px; }}
    .subtle {{ margin-top: 6px; color: #667085; font-size: 13px; }}
    .grid {{ display: grid; grid-template-columns: repeat(7, minmax(120px, 1fr)); gap: 18px 24px; background: #fff; padding: 18px 20px; border: 1px solid #d8dee8; }}
    .metric .label {{ color: #667085; font-size: 12px; margin-bottom: 7px; }}
    .metric .value {{ font-size: 18px; font-weight: 700; color: #111827; }}
    .metric .hot {{ color: #ff2a2a; }}
    .panel {{ margin-top: 18px; background: #fff; border: 1px solid #d8dee8; padding: 16px; }}
    .toolbar {{ display: flex; justify-content: space-between; align-items: center; color: #475467; font-size: 13px; margin-bottom: 12px; }}
    .legend span {{ display: inline-flex; align-items: center; margin-right: 14px; }}
    .swatch {{ width: 12px; height: 3px; margin-right: 5px; display: inline-block; }}
    .blue {{ background: #4e79a7; }}
    .red {{ background: #c44e52; }}
    .orange {{ background: #f28e2b; }}
    svg {{ width: 100%; height: auto; display: block; background: #fbfcfe; border: 1px solid #d8dee8; }}
    .notes {{ color: #475467; font-size: 13px; line-height: 1.6; }}
    @media (max-width: 1000px) {{ .grid {{ grid-template-columns: repeat(3, minmax(120px, 1fr)); }} }}
    @media (max-width: 640px) {{ main {{ padding: 12px; }} .grid {{ grid-template-columns: repeat(2, minmax(110px, 1fr)); gap: 14px; }} }}
  </style>
</head>
<body>
  <header>
    <h1>收益概览 - {html.escape(title)}</h1>
    <div class="subtle">回测窗口：{html.escape(window_text)}</div>
    <div class="subtle">基准来源：{html.escape(benchmark_text)}</div>
  </header>
  <main>
    <section class="grid">{metric_cards}</section>
    <section class="panel">
      <div class="toolbar">
        <div class="legend">
          <span><i class="swatch blue"></i>策略收益</span>
          <span><i class="swatch orange"></i>超额收益</span>
          <span><i class="swatch red"></i>基准收益</span>
        </div>
        <div>本地回测报告</div>
      </div>
      {chart}
    </section>
    <section class="panel notes"><strong>说明</strong><ul>{note_items}</ul></section>
  </main>
</body>
</html>
"""
    path.write_text(body, encoding="utf-8")


def _metric_card(key: str, label: str, fmt: str, value: Any) -> str:
    value_text = _format_value(value, fmt)
    hot = " hot" if key in {"strategy_return", "annualized_return", "excess_return", "benchmark_return", "max_drawdown"} else ""
    return f'<div class="metric"><div class="label">{html.escape(label)}</div><div class="value{hot}">{html.escape(value_text)}</div></div>'


def _format_value(value: Any, fmt: str) -> str:
    if value is None:
        return "--"
    if fmt == "percent":
        return f"{float(value) * 100:.2f}%"
    if fmt == "decimal":
        return f"{float(value):.3f}"
    if fmt == "integer":
        return str(int(value))
    return str(value).replace("-", "/")


def _svg_chart(period_rows: list[dict[str, Any]]) -> str:
    width = 1400
    height = 360
    pad_left = 54
    pad_right = 24
    pad_top = 24
    pad_bottom = 42
    if not period_rows:
        return f'<svg viewBox="0 0 {width} {height}" role="img"><text x="20" y="40">No data</text></svg>'

    dates = [row["trade_date"] for row in period_rows]
    strategy = [float(row["strategy_nav"]) - 1.0 for row in period_rows]
    benchmark = [float(row["benchmark_nav"]) - 1.0 for row in period_rows]
    excess = [float(row["excess_nav"]) - 1.0 for row in period_rows]
    all_values = strategy + benchmark + excess + [0.0]
    ymin = min(all_values)
    ymax = max(all_values)
    if abs(ymax - ymin) < 1e-12:
        ymax += 0.1
        ymin -= 0.1
    y_pad = (ymax - ymin) * 0.12
    ymin -= y_pad
    ymax += y_pad

    def x_at(index: int) -> float:
        if len(period_rows) == 1:
            return pad_left
        return pad_left + (width - pad_left - pad_right) * index / (len(period_rows) - 1)

    def y_at(value: float) -> float:
        return pad_top + (ymax - value) * (height - pad_top - pad_bottom) / (ymax - ymin)

    grid = []
    for i in range(6):
        y = pad_top + i * (height - pad_top - pad_bottom) / 5
        value = ymax - i * (ymax - ymin) / 5
        grid.append(f'<line x1="{pad_left}" y1="{y:.2f}" x2="{width-pad_right}" y2="{y:.2f}" stroke="#d0d5dd" stroke-width="1"/>')
        grid.append(f'<text x="{width-pad_right-4}" y="{y-4:.2f}" text-anchor="end" font-size="11" fill="#475467">{value*100:.0f}%</text>')
    zero_y = y_at(0.0)
    grid.append(f'<line x1="{pad_left}" y1="{zero_y:.2f}" x2="{width-pad_right}" y2="{zero_y:.2f}" stroke="#111827" stroke-width="1"/>')

    for i in range(0, len(period_rows), max(1, len(period_rows) // 8)):
        x = x_at(i)
        grid.append(f'<line x1="{x:.2f}" y1="{pad_top}" x2="{x:.2f}" y2="{height-pad_bottom}" stroke="#e5e7eb" stroke-width="1"/>')
        grid.append(f'<text x="{x:.2f}" y="{height-16}" text-anchor="middle" font-size="11" fill="#475467">{html.escape(dates[i][2:10])}</text>')

    strategy_path = _line_path(strategy, x_at, y_at)
    benchmark_path = _line_path(benchmark, x_at, y_at)
    excess_path = _line_path(excess, x_at, y_at)
    return f"""<svg viewBox="0 0 {width} {height}" role="img" aria-label="local backtest chart">
  {''.join(grid)}
  <path d="{strategy_path}" fill="none" stroke="#4e79a7" stroke-width="2"/>
  <path d="{benchmark_path}" fill="none" stroke="#c44e52" stroke-width="2"/>
  <path d="{excess_path}" fill="none" stroke="#f28e2b" stroke-width="1.6" opacity="0.9"/>
</svg>"""


def _line_path(values: list[float], x_at: Any, y_at: Any) -> str:
    parts = []
    for index, value in enumerate(values):
        cmd = "M" if index == 0 else "L"
        parts.append(f"{cmd}{x_at(index):.2f},{y_at(value):.2f}")
    return " ".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-local-backtest")
    parser.add_argument("spec", type=Path)
    parser.add_argument("panel", type=Path)
    parser.add_argument("--out", type=Path, default=Path("local_backtests"))
    parser.add_argument("--start-date", default=DEFAULT_BACKTEST_START)
    parser.add_argument("--end-date", default=DEFAULT_BACKTEST_END)
    parser.add_argument("--min-coverage-ratio", type=float, default=0.8)
    parser.add_argument("--execution-mode", choices=["ideal_equal_weight", "joinquant_like"], default="ideal_equal_weight")
    parser.add_argument("--initial-cash", type=float, default=2_000_000.0)
    parser.add_argument("--target-exposure", type=float, default=0.995)
    parser.add_argument("--lot-size", type=int, default=100)
    parser.add_argument("--open-commission", type=float, default=0.0003)
    parser.add_argument("--close-commission", type=float, default=0.0003)
    parser.add_argument("--min-commission", type=float, default=5.0)
    parser.add_argument("--save-periods", action="store_true")
    parser.add_argument("--save-holdings", action="store_true")
    args = parser.parse_args(argv)
    report = run_local_backtest(
        args.spec,
        args.panel,
        args.out,
        BacktestOptions(
            save_periods=args.save_periods,
            save_holdings=args.save_holdings,
            start_date=args.start_date,
            end_date=args.end_date,
            min_coverage_ratio=args.min_coverage_ratio,
            execution_mode=args.execution_mode,
            initial_cash=args.initial_cash,
            target_exposure=args.target_exposure,
            lot_size=args.lot_size,
            open_commission=args.open_commission,
            close_commission=args.close_commission,
            min_commission=args.min_commission,
        ),
    )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
