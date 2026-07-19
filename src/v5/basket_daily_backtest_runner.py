from __future__ import annotations

import math
import shutil
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.math_utils import fmt_float, to_float


DEFAULT_CONFIG = Path("config/dividend_low_vol_fcf_basket_v56.json")
DEFAULT_SIGNALS = Path("validation_formal_v56_basket_constructor") / "basket_rebalance_signals.csv"
DEFAULT_OUT_DIR = Path("local_daily_backtests_v56_basket")


@dataclass(frozen=True)
class BasketDailyBacktestResult:
    output_dir: Path
    summary_path: Path
    daily_returns_path: Path
    holdings_path: Path
    trades_path: Path
    dividends_path: Path
    corporate_actions_path: Path
    benchmark_path: Path
    daily_count: int
    trade_count: int
    dividend_count: int
    corporate_action_count: int


def run_basket_daily_backtest(
    config_path: Path = DEFAULT_CONFIG,
    signals_csv: Path = DEFAULT_SIGNALS,
    out_dir: Path = DEFAULT_OUT_DIR,
    *,
    initial_cash: float = 2_000_000.0,
    target_exposure: float = 0.995,
    lot_size: int = 100,
    open_commission: float = 0.0003,
    close_commission: float = 0.0003,
    min_commission: float = 5.0,
) -> BasketDailyBacktestResult:
    config = _read_json(config_path)
    start_date = str(config.get("portfolio", {}).get("start_date") or "2021-05-01")
    end_date = str(config.get("portfolio", {}).get("end_date") or "2026-05-31")
    price_files = [Path(str(sector["price_csv"])) for sector in config.get("sectors", []) if sector.get("price_csv")]
    dividend_files = [Path(str(sector["dividend_csv"])) for sector in config.get("sectors", []) if sector.get("dividend_csv")]
    if not price_files:
        raise ValueError("basket config sectors must include price_csv paths")

    signals = _load_signals(signals_csv)
    if not signals:
        raise ValueError(f"no basket signals found: {signals_csv}")
    first_signal = min(signals)
    start_date = max(start_date, first_signal)
    prices_by_date = _load_prices(price_files, start_date, end_date)
    corporate_actions_by_date = _load_corporate_actions(dividend_files, start_date, end_date)
    benchmark_by_date = _build_equal_weight_benchmark(prices_by_date, corporate_actions_by_date, start_date, end_date)
    daily_rows, holding_rows, trade_rows, dividend_rows, corporate_action_rows = _simulate(
        prices_by_date,
        corporate_actions_by_date,
        benchmark_by_date,
        signals,
        initial_cash=initial_cash,
        target_exposure=target_exposure,
        lot_size=lot_size,
        open_commission=open_commission,
        close_commission=close_commission,
        min_commission=min_commission,
    )

    out = out_dir / str(config.get("project") or "v56_basket")
    out.mkdir(parents=True, exist_ok=True)
    daily_path = out / "daily_returns.csv"
    holdings_path = out / "holdings.csv"
    trades_path = out / "trades.csv"
    dividends_path = out / "dividends.csv"
    corporate_actions_path = out / "corporate_actions.csv"
    benchmark_path = out / "same_pool_equal_weight_benchmark.csv"
    signals_copy_path = out / "rebalance_signals.csv"
    summary_path = out / "summary.json"
    report_path = out / "basket_daily_backtest_report.md"

    write_csv_rows(daily_path, _fieldnames(daily_rows), daily_rows)
    write_csv_rows(holdings_path, _fieldnames(holding_rows), holding_rows)
    write_csv_rows(trades_path, _fieldnames(trade_rows), trade_rows)
    write_csv_rows(dividends_path, _fieldnames(dividend_rows), dividend_rows)
    write_csv_rows(corporate_actions_path, _fieldnames(corporate_action_rows), corporate_action_rows)
    write_csv_rows(
        benchmark_path,
        ["trade_date", "benchmark_return", "benchmark_nav", "constituent_count", "dividend_constituent_count"],
        benchmark_by_date,
    )
    shutil.copyfile(signals_csv, signals_copy_path)

    metrics = _compute_metrics(daily_rows)
    sector_ids = [str(sector.get("sector_id") or "") for sector in config.get("sectors", [])]
    dividend_file_counts = {str(path): len(read_csv_rows(path)) if path.exists() else 0 for path in dividend_files}
    summary = {
        "schema_version": 1,
        "strategy_id": str(config.get("project") or "v56_dividend_low_vol_fcf_shadow_basket"),
        "mode": "basket_daily_joinquant_like",
        "experiment_layer": "engineering_smoke_test",
        "config": str(config_path),
        "signals_csv": str(signals_csv),
        "price_files": [str(path) for path in price_files],
        "dividend_files": [str(path) for path in dividend_files],
        "window": {"start_date": start_date, "end_date": end_date},
        "execution": {
            "initial_cash": initial_cash,
            "target_exposure": target_exposure,
            "lot_size": lot_size,
            "open_commission": open_commission,
            "close_commission": close_commission,
            "min_commission": min_commission,
            "trade_price": "daily_open",
            "valuation_price": "daily_close",
            "cash_dividend_policy": "Tax-adjusted net_cash_per_share is added to cash on pay_date.",
            "share_action_policy": "Bonus/transfer shares adjust position amount on ex_date before same-day trading and close valuation.",
            "benchmark_policy": "Same-pool equal-weight total-return benchmark where net cash dividends are available; otherwise price return.",
        },
        "signal_count": len(signals),
        "daily_count": len(daily_rows),
        "trade_count": len(trade_rows),
        "dividend_count": len(dividend_rows),
        "corporate_action_count": len(corporate_action_rows),
        "metrics": metrics,
        "outputs": {
            "summary": "summary.json",
            "daily_returns": "daily_returns.csv",
            "holdings": "holdings.csv",
            "trades": "trades.csv",
            "dividends": "dividends.csv",
            "corporate_actions": "corporate_actions.csv",
            "rebalance_signals": "rebalance_signals.csv",
            "same_pool_equal_weight_benchmark": "same_pool_equal_weight_benchmark.csv",
            "report": "basket_daily_backtest_report.md",
        },
        "data_coverage": {
            "sector_ids": sector_ids,
            "dividend_file_event_counts": dividend_file_counts,
        },
        "notes": _build_notes(sector_ids, dividend_file_counts),
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    write_json_file(summary_path, summary)
    report_path.write_text(_build_report(summary), encoding="utf-8")

    return BasketDailyBacktestResult(
        output_dir=out,
        summary_path=summary_path,
        daily_returns_path=daily_path,
        holdings_path=holdings_path,
        trades_path=trades_path,
        dividends_path=dividends_path,
        corporate_actions_path=corporate_actions_path,
        benchmark_path=benchmark_path,
        daily_count=len(daily_rows),
        trade_count=len(trade_rows),
        dividend_count=len(dividend_rows),
        corporate_action_count=len(corporate_action_rows),
    )


def _build_notes(sector_ids: list[str], dividend_file_counts: dict[str, int]) -> list[str]:
    missing_dividend_files = [path for path, count in dividend_file_counts.items() if count <= 0]
    notes = [
        "This is a basket-level local daily simulation, not platform replication and not strategy acceptance.",
        f"Basket sectors included in this run: {', '.join(sector_ids)}.",
        "Benchmark is a same-pool equal-weight total-return proxy where net cash dividends are available; otherwise price return.",
    ]
    if missing_dividend_files:
        notes.append(
            "Dividend repair is still needed for files with zero events: "
            + "; ".join(missing_dividend_files)
            + "."
        )
    else:
        notes.append("All configured dividend files contain at least one cash-dividend event.")
    return notes


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


def _simulate(
    prices_by_date: dict[str, dict[str, dict[str, float]]],
    corporate_actions_by_date: dict[str, dict[str, dict[str, float]]],
    benchmark_rows: list[dict[str, Any]],
    signals: dict[str, dict[str, float]],
    *,
    initial_cash: float,
    target_exposure: float,
    lot_size: int,
    open_commission: float,
    close_commission: float,
    min_commission: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
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
    current_targets: dict[str, float] = {}

    for day, price_rows in sorted(prices_by_date.items()):
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

        open_prices = {code: item["open"] for code, item in price_rows.items()}
        close_prices = {code: item["close"] for code, item in price_rows.items()}
        trade_prices = dict(last_close)
        trade_prices.update(open_prices)
        buy_turnover = 0.0
        sell_turnover = 0.0
        commission_total = 0.0
        rebalance = day in signals
        if rebalance:
            current_targets = {code: weight * target_exposure for code, weight in signals[day].items()}
            cash, sell_commission, sell_turnover, sells = _execute_sells(
                day,
                cash,
                positions,
                trade_prices,
                price_rows,
                current_targets,
                lot_size,
                close_commission,
                min_commission,
            )
            total_after_sells = _portfolio_value(cash, positions, trade_prices)
            cash, buy_commission, buy_turnover, buys = _execute_buys(
                day,
                cash,
                positions,
                trade_prices,
                price_rows,
                current_targets,
                total_after_sells,
                lot_size,
                open_commission,
                min_commission,
            )
            commission_total = sell_commission + buy_commission
            trade_rows.extend(sells)
            trade_rows.extend(buys)

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
    return daily_rows, holding_rows, trade_rows, dividend_rows, corporate_action_rows


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
) -> tuple[float, float, float, list[dict[str, Any]]]:
    total_value = _portfolio_value(cash, positions, prices)
    commission_total = 0.0
    turnover = 0.0
    trades: list[dict[str, Any]] = []
    for code in list(positions):
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
        reason = _sell_block_reason(price_rows.get(code))
        if reason:
            trades.append(_trade_row(day, code, "sell_skipped", amount, price, 0.0, 0.0, target_amount, reason))
            continue
        value = amount * price
        commission = _commission(value, commission_rate, min_commission)
        cash += value - commission
        positions[code] = target_amount
        if positions[code] <= 0:
            positions.pop(code, None)
        commission_total += commission
        turnover += value
        trades.append(_trade_row(day, code, "sell", amount, price, value, commission, target_amount, ""))
    return cash, commission_total, turnover, trades


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
) -> tuple[float, float, float, list[dict[str, Any]]]:
    commission_total = 0.0
    turnover = 0.0
    trades: list[dict[str, Any]] = []
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
        reason = _buy_block_reason(price_rows.get(code))
        if reason:
            trades.append(_trade_row(day, code, "buy_skipped", amount, price, 0.0, 0.0, target_amount, reason))
            continue
        value = amount * price
        commission = _commission(value, commission_rate, min_commission)
        cash -= value + commission
        positions[code] = current + amount
        commission_total += commission
        turnover += value
        trades.append(_trade_row(day, code, "buy", amount, price, value, commission, target_amount, ""))
    return cash, commission_total, turnover, trades


def _buy_block_reason(price_row: dict[str, float] | None) -> str:
    if not price_row:
        return ""
    if (price_row.get("paused") or 0.0) >= 1.0:
        return "paused"
    open_price = price_row.get("open")
    high_limit = price_row.get("high_limit")
    if open_price is not None and high_limit is not None and high_limit > 0 and open_price >= high_limit * 0.999999:
        return "high_limit"
    return ""


def _sell_block_reason(price_row: dict[str, float] | None) -> str:
    if not price_row:
        return ""
    if (price_row.get("paused") or 0.0) >= 1.0:
        return "paused"
    open_price = price_row.get("open")
    low_limit = price_row.get("low_limit")
    if open_price is not None and low_limit is not None and low_limit > 0 and open_price <= low_limit * 1.000001:
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
    alpha = annualized - beta * benchmark_annualized if alpha_inputs_ok(annualized, beta, benchmark_annualized) else None
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


def alpha_inputs_ok(annualized: float | None, beta: float | None, benchmark_annualized: float | None) -> bool:
    return annualized is not None and beta is not None and benchmark_annualized is not None


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


def _fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    return fields


def _build_report(summary: dict[str, Any]) -> str:
    metrics = summary.get("metrics", {})
    lines = [
        "# Basket Daily Backtest Report",
        "",
        f"Created at UTC: `{summary['created_at_utc']}`",
        "",
        "## PM Decision",
        "",
        "The basket has completed a local daily engineering smoke test. This is not platform replication, paper trading approval, or strategy acceptance.",
        "",
        "## Metrics",
        "",
    ]
    for key in [
        "strategy_return",
        "annualized_return",
        "benchmark_return",
        "excess_return",
        "max_drawdown",
        "sharpe",
        "information_ratio",
        "strategy_volatility",
        "benchmark_volatility",
        "max_drawdown_interval",
    ]:
        lines.append(f"- `{key}`: `{fmt_float(metrics.get(key)) if key != 'max_drawdown_interval' else metrics.get(key)}`")
    lines.extend(
        [
            "",
            "## Known Gaps",
            "",
        ]
    )
    for note in summary.get("notes", []):
        lines.append(f"- {note}")
    lines.extend(
        [
            "",
            "## Next Gate",
            "",
            "`basket_formal_validation_and_overfit_audit`",
            "",
        ]
    )
    return "\n".join(lines)


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        import json

        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload
