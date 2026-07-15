from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from v5.engine import load_spec
from v5.experiment_governance import (
    build_run_manifest,
    freeze_snapshot,
    validate_daily_run_contract,
    write_run_manifest,
)
from v5.local_backtest import (
    BacktestOptions,
    _affordable_lot_amount,
    _commission,
    _compute_metrics,
    _parse_date,
    _portfolio_value,
    _target_lot_amount,
    _to_float,
    _write_csv,
    _write_json,
)
from v5.scoring import apply_value_trap_guard, merge_eastmoney_quality, score_rows


def run_daily_joinquant_like_backtest(
    spec_path: Path,
    panel_path: Path,
    v4_raw_dir: Path,
    benchmark_csv: Path,
    out_dir: Path,
    options: BacktestOptions | None = None,
    benchmark_id: str = "bank_etf_512800_qfq",
    execution_price_csv: Path | None = None,
    dividend_cash_csv: Path | None = None,
    eastmoney_quality_csv: Path | None = None,
    eastmoney_min_review_status: str = "needs_check",
    eastmoney_visibility_mode: str = "notice_date",
    experiment_layer: str = "engineering_smoke_test",
    snapshot_out: Path | None = None,
) -> Path:
    options = options or BacktestOptions(execution_mode="joinquant_like")
    spec = load_spec(spec_path)
    governance_warnings = validate_daily_run_contract(
        experiment_layer=experiment_layer,
        eastmoney_visibility_mode=eastmoney_visibility_mode,
        execution_price_csv=execution_price_csv,
        benchmark_csv=benchmark_csv,
        dividend_cash_csv=dividend_cash_csv,
    )
    signals, signal_rows = _build_rebalance_signals(
        panel_path,
        spec.raw,
        options,
        eastmoney_quality_csv,
        eastmoney_min_review_status,
        eastmoney_visibility_mode,
    )
    if execution_price_csv is not None:
        prices_by_date = _load_execution_prices(execution_price_csv, options.start_date, options.end_date)
        price_source = str(execution_price_csv)
    else:
        prices_by_date = _load_daily_prices(v4_raw_dir, options.start_date, options.end_date)
        price_source = str(v4_raw_dir)
    benchmarks = _load_benchmark_closes(benchmark_csv, benchmark_id, options.start_date, options.end_date)
    cash_dividends = _load_cash_dividends(dividend_cash_csv, options.start_date, options.end_date)
    out = out_dir / spec.strategy_id
    out.mkdir(parents=True, exist_ok=True)

    daily_rows, holding_rows, trade_rows, dividend_rows = _simulate_daily(prices_by_date, benchmarks, cash_dividends, signals, spec.raw, options)
    metrics = _compute_metrics(daily_rows)
    summary = {
        "strategy_id": spec.strategy_id,
        "mode": "daily_joinquant_like",
        "panel": str(panel_path),
        "price_source": price_source,
        "benchmark_csv": str(benchmark_csv),
        "dividend_cash_csv": str(dividend_cash_csv) if dividend_cash_csv else None,
        "eastmoney_quality_csv": str(eastmoney_quality_csv) if eastmoney_quality_csv else None,
        "eastmoney_min_review_status": eastmoney_min_review_status,
        "eastmoney_visibility_mode": eastmoney_visibility_mode,
        "experiment_layer": experiment_layer,
        "benchmark_id": benchmark_id,
        "window": {
            "start_date": options.start_date,
            "end_date": options.end_date,
            "policy": "default_v4_comparison_window",
        },
        "execution": {
            "initial_cash": options.initial_cash,
            "target_exposure": options.target_exposure,
            "lot_size": options.lot_size,
            "open_commission": options.open_commission,
            "close_commission": options.close_commission,
            "min_commission": options.min_commission,
            "trade_price": "daily_open",
            "valuation_price": "daily_close",
            "cash_dividend_policy": "Add net_cash_per_share * shares to cash on pay_date.",
            "tradability_policy": "Skip buy when paused or opening at high limit; skip sell when paused or opening at low limit.",
            "defensive_mode": options.defensive_mode,
            "defensive_ma_days": options.defensive_ma_days,
            "defensive_risk_exposure": options.defensive_risk_exposure,
        },
        "signal_count": len(signals),
        "daily_count": len(daily_rows),
        "metrics": metrics,
        "outputs": {
            "summary": "summary.json",
            "daily_returns": "daily_returns.csv",
            "holdings": "holdings.csv",
            "trades": "trades.csv",
            "dividends": "dividends.csv",
            "rebalance_signals": "rebalance_signals.csv",
        },
        "notes": [
            "This runner is for JoinQuant comparison. It simulates daily path, open-price rebalancing, close-price valuation, A-share lot rounding, cash, and commissions.",
            "Use JoinQuant fq=None real prices when execution_price_csv is supplied. Otherwise V4 raw daily prices are used as a fallback.",
            "Defensive overlay, when enabled, changes exposure only and does not change selected stocks or factor ranks.",
            "Execution is still daily-open approximation; JoinQuant scheduled intraday execution such as 09:40 can differ from daily open.",
        ],
    }
    _write_json(out / "summary.json", summary)
    _write_csv(out / "daily_returns.csv", list(daily_rows[0].keys()) if daily_rows else [], daily_rows)
    _write_csv(out / "holdings.csv", list(holding_rows[0].keys()) if holding_rows else [], holding_rows)
    _write_csv(out / "trades.csv", list(trade_rows[0].keys()) if trade_rows else [], trade_rows)
    _write_csv(out / "dividends.csv", list(dividend_rows[0].keys()) if dividend_rows else [], dividend_rows)
    _write_csv(out / "rebalance_signals.csv", list(signal_rows[0].keys()) if signal_rows else [], signal_rows)
    manifest = build_run_manifest(
        strategy_id=spec.strategy_id,
        experiment_layer=experiment_layer,
        command_profile={
            "spec": str(spec_path),
            "panel": str(panel_path),
            "v4_raw_dir": str(v4_raw_dir),
            "benchmark_csv": str(benchmark_csv),
            "benchmark_id": benchmark_id,
            "execution_price_csv": str(execution_price_csv) if execution_price_csv else None,
            "dividend_cash_csv": str(dividend_cash_csv) if dividend_cash_csv else None,
            "eastmoney_quality_csv": str(eastmoney_quality_csv) if eastmoney_quality_csv else None,
            "eastmoney_min_review_status": eastmoney_min_review_status,
            "eastmoney_visibility_mode": eastmoney_visibility_mode,
            "start_date": options.start_date,
            "end_date": options.end_date,
            "initial_cash": options.initial_cash,
            "target_exposure": options.target_exposure,
            "lot_size": options.lot_size,
            "open_commission": options.open_commission,
            "close_commission": options.close_commission,
            "min_commission": options.min_commission,
            "defensive_mode": options.defensive_mode,
            "defensive_ma_days": options.defensive_ma_days,
            "defensive_risk_exposure": options.defensive_risk_exposure,
        },
        outputs=summary["outputs"] | {"run_manifest": "RUN_MANIFEST.json"},
        warnings=governance_warnings,
    )
    write_run_manifest(out / "RUN_MANIFEST.json", manifest)
    if snapshot_out is not None:
        freeze_snapshot(out, snapshot_out, manifest)
    return out / "summary.json"


def _build_rebalance_signals(
    panel_path: Path,
    raw_spec: dict[str, Any],
    options: BacktestOptions,
    eastmoney_quality_csv: Path | None = None,
    eastmoney_min_review_status: str = "needs_check",
    eastmoney_visibility_mode: str = "notice_date",
) -> tuple[dict[str, list[str]], list[dict[str, Any]]]:
    with panel_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    start = _parse_date(options.start_date)
    end = _parse_date(options.end_date)
    panel_rows: list[dict[str, Any]] = []
    for row in rows:
        if not row.get("trade_date") or not row.get("code"):
            continue
        day = _parse_date(row["trade_date"])
        if start <= day <= end:
            ret = _to_float(row.get("total_return")) or _to_float(row.get("future_return")) or 0.0
            item = dict(row)
            item["future_return"] = ret
            panel_rows.append(item)

    panel_rows = merge_eastmoney_quality(panel_rows, eastmoney_quality_csv, eastmoney_min_review_status, eastmoney_visibility_mode)
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in panel_rows:
        by_date[item["trade_date"]].append(item)

    max_date_coverage = max((len(date_rows) for date_rows in by_date.values()), default=0)
    min_required_coverage = math.ceil(max_date_coverage * options.min_coverage_ratio) if max_date_coverage else 0
    selection_count = int(raw_spec["portfolio"]["selection_count"])
    signals: dict[str, list[str]] = {}
    signal_rows: list[dict[str, Any]] = []
    rebalance_months = set(raw_spec.get("schedule", {}).get("rebalance_months", [1, 4, 7, 10]))
    executed_keys: set[str] = set()
    for trade_date, date_rows in sorted(by_date.items()):
        day = _parse_date(trade_date)
        if day.month not in rebalance_months:
            continue
        key = f"{day.year:04d}-{day.month:02d}"
        if key in executed_keys:
            continue
        if len(date_rows) < min_required_coverage:
            continue
        scored, used_factors = score_rows(raw_spec, date_rows)
        eligible = apply_value_trap_guard(raw_spec, scored)
        selected = sorted(eligible, key=lambda item: item["score"], reverse=True)[:selection_count]
        signals[trade_date] = [row["code"] for row in selected]
        executed_keys.add(key)
        signal_rows.append(
            {
                "trade_date": trade_date,
                "candidate_count": len(scored),
                "guarded_count": len(eligible),
                "selected_count": len(selected),
                "used_factors": ";".join(used_factors),
                "selected_codes": ";".join(signals[trade_date]),
            }
        )
    return signals, signal_rows


def _load_daily_prices(v4_raw_dir: Path, start_date: str, end_date: str) -> dict[str, dict[str, dict[str, float]]]:
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    prices: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)
    for bank_dir in sorted(path for path in v4_raw_dir.iterdir() if path.is_dir()):
        valuation_rows = _read_csv(bank_dir / "daily_valuation.csv")
        price_rows = _read_csv(bank_dir / "daily_price.csv")
        for valuation, price_row in zip(valuation_rows, price_rows):
            day_text = valuation.get("day")
            code = valuation.get("code") or bank_dir.name.replace("_", ".")
            if not day_text or not code:
                continue
            day = _parse_date(day_text)
            if day < start or day > end:
                continue
            open_price = _to_float(price_row.get("open"))
            close_price = _to_float(price_row.get("close"))
            if open_price is None or close_price is None or open_price <= 0 or close_price <= 0:
                continue
            prices[day.isoformat()][code] = {"open": open_price, "close": close_price}
    return dict(prices)


def _load_execution_prices(path: Path, start_date: str, end_date: str) -> dict[str, dict[str, dict[str, float]]]:
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    prices: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)
    for row in _read_csv(path):
        day_text = row.get("date") or row.get("day") or row.get("trade_date")
        code = row.get("code") or row.get("security")
        if not day_text or not code:
            continue
        day = _parse_date(day_text)
        if day < start or day > end:
            continue
        open_price = _to_float(row.get("open"))
        close_price = _to_float(row.get("close"))
        if open_price is None or close_price is None or open_price <= 0 or close_price <= 0:
            continue
        prices[day.isoformat()][code] = {
            "open": open_price,
            "close": close_price,
            "high_limit": _to_float(row.get("high_limit")),
            "low_limit": _to_float(row.get("low_limit")),
            "paused": _to_float(row.get("paused")) or 0.0,
        }
    return dict(prices)


def _load_benchmark_closes(path: Path, benchmark_id: str, start_date: str, end_date: str) -> dict[str, float]:
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    points: dict[str, float] = {}
    anchor_day = None
    anchor_close = None
    for row in _read_csv(path):
        row_id = row.get("benchmark_id") or row.get("code") or row.get("security")
        if row_id != benchmark_id:
            continue
        day_text = row.get("date") or row.get("day") or row.get("trade_date")
        close = _to_float(row.get("close"))
        if not day_text or close is None or close <= 0:
            continue
        day = _parse_date(day_text)
        if start <= day <= end:
            points[day.isoformat()] = close
        elif day < start and (anchor_day is None or day > anchor_day):
            anchor_day = day
            anchor_close = close
    if anchor_close is not None:
        points["__anchor_previous_close"] = anchor_close
    return points


def _load_cash_dividends(path: Path | None, start_date: str, end_date: str) -> dict[str, dict[str, float]]:
    if path is None or not path.exists():
        return {}
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    events: dict[str, dict[str, float]] = defaultdict(dict)
    for row in _read_csv(path):
        code = row.get("code") or row.get("security")
        pay_date = row.get("pay_date") or row.get("ex_date") or row.get("date")
        if not code or not pay_date:
            continue
        day = _parse_date(pay_date)
        if day < start or day > end:
            continue
        cash = _to_float(row.get("net_cash_per_share") or row.get("cash_per_share"))
        if cash is None or cash <= 0:
            continue
        events[day.isoformat()][code] = events[day.isoformat()].get(code, 0.0) + cash
    return dict(events)


def _simulate_daily(
    prices_by_date: dict[str, dict[str, dict[str, float]]],
    benchmarks: dict[str, float],
    cash_dividends: dict[str, dict[str, float]],
    signals: dict[str, list[str]],
    raw_spec: dict[str, Any],
    options: BacktestOptions,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    cash = float(options.initial_cash)
    positions: dict[str, int] = {}
    last_close: dict[str, float] = {}
    previous_value = cash
    previous_benchmark_close: float | None = benchmarks.get("__anchor_previous_close")
    benchmark_history: list[float] = []
    strategy_nav = 1.0
    benchmark_nav = 1.0
    excess_nav = 1.0
    rows: list[dict[str, Any]] = []
    holdings: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []
    dividend_rows: list[dict[str, Any]] = []
    selection_count = int(raw_spec["portfolio"]["selection_count"])
    current_selected_codes: list[str] = []
    previous_effective_exposure = options.target_exposure
    previous_defensive_state = "risk_on"

    for day in sorted(prices_by_date):
        day_prices = prices_by_date[day]
        open_prices = {code: item["open"] for code, item in day_prices.items()}
        close_prices = {code: item["close"] for code, item in day_prices.items()}
        trade_prices = dict(last_close)
        trade_prices.update(open_prices)

        buy_turnover = 0.0
        sell_turnover = 0.0
        commission_total = 0.0
        signal_codes = signals.get(day)
        if signal_codes is not None:
            current_selected_codes = signal_codes
        defensive_state = _defensive_state(benchmark_history, options)
        effective_exposure = options.target_exposure
        if defensive_state == "risk_off":
            effective_exposure *= options.defensive_risk_exposure
        should_rebalance = signal_codes is not None or abs(effective_exposure - previous_effective_exposure) > 1e-12
        selected_codes = current_selected_codes if should_rebalance else None
        if selected_codes is not None:
            cash, sell_commission, sell_turnover, sell_trades = _daily_sells(
                day, cash, positions, trade_prices, day_prices, selected_codes, selection_count, effective_exposure, options
            )
            total_after_sells = _portfolio_value(cash, positions, trade_prices)
            cash, buy_commission, buy_turnover, buy_trades = _daily_buys(
                day, cash, positions, trade_prices, day_prices, selected_codes, selection_count, total_after_sells, effective_exposure, options
            )
            trades.extend(sell_trades)
            trades.extend(buy_trades)
            commission_total = sell_commission + buy_commission
            previous_effective_exposure = effective_exposure
            previous_defensive_state = defensive_state

        dividend_cash = 0.0
        for code, cash_per_share in cash_dividends.get(day, {}).items():
            amount = positions.get(code, 0)
            if amount > 0:
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
        cash += dividend_cash

        valuation_prices = dict(last_close)
        valuation_prices.update(close_prices)
        value = _portfolio_value(cash, positions, valuation_prices)
        strategy_return = (value / previous_value) - 1.0 if previous_value > 0 else 0.0
        previous_value = value
        strategy_nav *= 1.0 + strategy_return

        benchmark_close = benchmarks.get(day)
        if previous_benchmark_close is None or benchmark_close is None:
            benchmark_return = 0.0
        else:
            benchmark_return = (benchmark_close / previous_benchmark_close) - 1.0
        if benchmark_close is not None:
            previous_benchmark_close = benchmark_close
            benchmark_history.append(benchmark_close)
        benchmark_nav *= 1.0 + benchmark_return
        excess_return = strategy_return - benchmark_return
        excess_nav *= 1.0 + excess_return
        invested_value = sum(amount * valuation_prices.get(code, 0.0) for code, amount in positions.items())

        rows.append(
            {
                "trade_date": day,
                "next_trade_date": "",
                "strategy_return": strategy_return,
                "benchmark_return": benchmark_return,
                "excess_return": excess_return,
                "strategy_nav": strategy_nav,
                "benchmark_nav": benchmark_nav,
                "excess_nav": excess_nav,
                "selected_count": len(selected_codes or []),
                "date_security_count": len(day_prices),
                "cash_weight": cash / value if value > 0 else 1.0,
                "benchmark_source": "bank_etf_512800_qfq",
                "selected_codes": ";".join(selected_codes or []),
                "portfolio_value": value,
                "cash": cash,
                "invested_value": invested_value,
                "buy_turnover": buy_turnover,
                "sell_turnover": sell_turnover,
                "commission": commission_total,
                "dividend_cash": dividend_cash,
                "defensive_state": defensive_state,
                "effective_target_exposure": effective_exposure,
            }
        )
        if selected_codes is not None:
            for code in selected_codes:
                amount = positions.get(code, 0)
                price = valuation_prices.get(code, 0.0)
                holdings.append(
                    {
                        "trade_date": day,
                        "code": code,
                        "target_weight": options.target_exposure / selection_count,
                        "effective_target_weight": effective_exposure / selection_count,
                        "actual_weight": (amount * price / value) if value > 0 else 0.0,
                        "amount": amount,
                        "close": price,
                    }
                )
        last_close.update(close_prices)
    return rows, holdings, trades, dividend_rows


def _daily_sells(
    day: str,
    cash: float,
    positions: dict[str, int],
    prices: dict[str, float],
    day_price_rows: dict[str, dict[str, float]],
    selected_codes: list[str],
    selection_count: int,
    effective_exposure: float,
    options: BacktestOptions,
) -> tuple[float, float, float, list[dict[str, Any]]]:
    selected = set(selected_codes)
    total_value = _portfolio_value(cash, positions, prices)
    commission_total = 0.0
    turnover = 0.0
    trades: list[dict[str, Any]] = []
    for code in list(positions):
        price = prices.get(code)
        if price is None or price <= 0:
            continue
        current = positions[code]
        target = 0
        if code in selected:
            target_value = total_value * effective_exposure / selection_count
            target = _target_lot_amount(target_value, price, options.lot_size)
        if current <= target:
            continue
        amount = current - target
        if target != 0 and amount < options.lot_size:
            continue
        block_reason = _sell_block_reason(day_price_rows.get(code))
        if block_reason:
            trades.append({"trade_date": day, "code": code, "side": "sell_skipped", "amount": amount, "price": price, "value": 0.0, "commission": 0.0, "target_amount": target, "reason": block_reason})
            continue
        value = amount * price
        commission = _commission(value, options.close_commission, options.min_commission)
        cash += value - commission
        positions[code] = target
        if positions[code] <= 0:
            positions.pop(code, None)
        commission_total += commission
        turnover += value
        trades.append({"trade_date": day, "code": code, "side": "sell", "amount": amount, "price": price, "value": value, "commission": commission, "target_amount": target, "reason": ""})
    return cash, commission_total, turnover, trades


def _daily_buys(
    day: str,
    cash: float,
    positions: dict[str, int],
    prices: dict[str, float],
    day_price_rows: dict[str, dict[str, float]],
    selected_codes: list[str],
    selection_count: int,
    total_value: float,
    effective_exposure: float,
    options: BacktestOptions,
) -> tuple[float, float, float, list[dict[str, Any]]]:
    commission_total = 0.0
    turnover = 0.0
    trades: list[dict[str, Any]] = []
    for code in selected_codes:
        price = prices.get(code)
        if price is None or price <= 0:
            continue
        current = positions.get(code, 0)
        target_value = total_value * effective_exposure / selection_count
        target = _target_lot_amount(target_value, price, options.lot_size)
        if target <= current:
            continue
        amount = min(target - current, _affordable_lot_amount(cash, price, options))
        if amount < options.lot_size:
            continue
        block_reason = _buy_block_reason(day_price_rows.get(code))
        if block_reason:
            trades.append({"trade_date": day, "code": code, "side": "buy_skipped", "amount": target - current, "price": price, "value": 0.0, "commission": 0.0, "target_amount": target, "reason": block_reason})
            continue
        value = amount * price
        commission = _commission(value, options.open_commission, options.min_commission)
        cash -= value + commission
        positions[code] = current + amount
        commission_total += commission
        turnover += value
        trades.append({"trade_date": day, "code": code, "side": "buy", "amount": amount, "price": price, "value": value, "commission": commission, "target_amount": target, "reason": ""})
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


def _defensive_state(benchmark_history: list[float], options: BacktestOptions) -> str:
    if options.defensive_mode == "none":
        return "risk_on"
    if options.defensive_mode == "benchmark_ma":
        if len(benchmark_history) < options.defensive_ma_days:
            return "risk_on"
        ma = mean(benchmark_history[-options.defensive_ma_days :])
        if ma <= 0:
            return "risk_on"
        return "risk_off" if benchmark_history[-1] < ma else "risk_on"
    raise ValueError(f"unsupported defensive_mode: {options.defensive_mode}")


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-daily-backtest")
    parser.add_argument("spec", type=Path)
    parser.add_argument("panel", type=Path)
    parser.add_argument("--v4-raw-dir", type=Path, default=Path(r"D:\hh\codex\v4\phase_1_fundamental\raw_downloads\all_banks"))
    parser.add_argument("--benchmark-csv", type=Path, default=Path("数据库/processed/bank_benchmarks.csv"))
    parser.add_argument("--benchmark-id", default="bank_etf_512800_qfq")
    parser.add_argument("--execution-price-csv", type=Path)
    parser.add_argument("--dividend-cash-csv", type=Path)
    parser.add_argument("--eastmoney-quality-csv", type=Path)
    parser.add_argument("--eastmoney-min-review-status", choices=["reviewed", "needs_check", "unreviewed"], default="needs_check")
    parser.add_argument("--eastmoney-visibility-mode", choices=["notice_date", "joinquant_source_year"], default="notice_date")
    parser.add_argument("--experiment-layer", choices=["research_pit_validation", "platform_replication", "engineering_smoke_test", "paper_trading"], default="engineering_smoke_test")
    parser.add_argument("--snapshot-out", type=Path)
    parser.add_argument("--out", type=Path, default=Path("local_daily_backtests"))
    parser.add_argument("--start-date", default="2021-05-01")
    parser.add_argument("--end-date", default="2026-05-31")
    parser.add_argument("--initial-cash", type=float, default=2_000_000.0)
    parser.add_argument("--target-exposure", type=float, default=0.995)
    parser.add_argument("--defensive-mode", choices=["none", "benchmark_ma"], default="none")
    parser.add_argument("--defensive-ma-days", type=int, default=252)
    parser.add_argument("--defensive-risk-exposure", type=float, default=0.5)
    args = parser.parse_args(argv)
    path = run_daily_joinquant_like_backtest(
        args.spec,
        args.panel,
        args.v4_raw_dir,
        args.benchmark_csv,
        args.out,
        BacktestOptions(
            execution_mode="joinquant_like",
            start_date=args.start_date,
            end_date=args.end_date,
            initial_cash=args.initial_cash,
            target_exposure=args.target_exposure,
            defensive_mode=args.defensive_mode,
            defensive_ma_days=args.defensive_ma_days,
            defensive_risk_exposure=args.defensive_risk_exposure,
        ),
        benchmark_id=args.benchmark_id,
        execution_price_csv=args.execution_price_csv,
        dividend_cash_csv=args.dividend_cash_csv,
        eastmoney_quality_csv=args.eastmoney_quality_csv,
        eastmoney_min_review_status=args.eastmoney_min_review_status,
        eastmoney_visibility_mode=args.eastmoney_visibility_mode,
        experiment_layer=args.experiment_layer,
        snapshot_out=args.snapshot_out,
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
