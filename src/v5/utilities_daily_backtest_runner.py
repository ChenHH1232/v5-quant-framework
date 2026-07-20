from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.daily_backtest import (
    _load_benchmark_closes,
    _load_cash_dividends,
    _load_execution_prices,
    _simulate_daily,
)
from v5.local_backtest import BacktestOptions, _compute_metrics, _parse_date, _to_float, _write_csv, _write_json
from v5.rebalance_order_health import build_rebalance_order_health
from v5.utilities_demand_state_validation_runner import _expanding_bucket, _latest_visible_state_by_date


DEFAULT_PANEL = Path("数据库") / "processed" / "utilities_cashflow_value_v51b_panel" / "panel.csv"
DEFAULT_STATE_PANEL = Path("数据库") / "processed" / "utilities_external_state" / "utilities_external_state.csv"
DEFAULT_OUT_DIR = Path("local_daily_backtests_utilities_v51f")

CASE_FACTORS = {
    "raw_high_dividend_utilities_top10": ("dividend_yield", "higher_is_better"),
    "raw_cashflow_yield_utilities_top10": ("operating_cash_flow_yield", "higher_is_better"),
    "raw_low_pb_utilities_top10": ("low_price_to_book", "lower_is_better"),
}

DAILY_RETURN_FIELDS = [
    "trade_date",
    "next_trade_date",
    "strategy_return",
    "benchmark_return",
    "excess_return",
    "strategy_nav",
    "benchmark_nav",
    "excess_nav",
    "selected_count",
    "date_security_count",
    "cash_weight",
    "benchmark_source",
    "selected_codes",
    "portfolio_value",
    "cash",
    "invested_value",
    "buy_turnover",
    "sell_turnover",
    "commission",
    "dividend_cash",
    "defensive_state",
    "effective_target_exposure",
]
HOLDING_FIELDS = ["trade_date", "code", "target_weight", "effective_target_weight", "actual_weight", "amount", "close"]
TRADE_FIELDS = ["trade_date", "code", "side", "amount", "price", "value", "commission", "target_amount", "reason"]
DIVIDEND_FIELDS = ["trade_date", "code", "amount", "net_cash_per_share", "dividend_cash"]
ORDER_HEALTH_FIELDS = [
    "trade_date",
    "order_health_status",
    "selected_count",
    "selected_codes",
    "executed_order_count",
    "buy_order_count",
    "sell_order_count",
    "skipped_order_count",
    "buy_skipped_count",
    "sell_skipped_count",
    "buy_turnover",
    "sell_turnover",
    "holding_count_after_rebalance",
    "cash_weight_after_rebalance",
    "portfolio_value_after_rebalance",
    "diagnosis",
]
SIGNAL_FIELDS = [
    "trade_date",
    "state_visible_date",
    "state_date",
    "state_value",
    "state_bucket",
    "case",
    "factor",
    "candidate_count",
    "selected_count",
    "selected_codes",
]


def check_utilities_daily_backtest_ready(
    panel_path: Path,
    state_panel_path: Path,
    execution_price_csv: Path,
    benchmark_csv: Path,
    dividend_cash_csv: Path | None = None,
    start_date: str = "2021-05-01",
    end_date: str = "2026-05-31",
) -> dict[str, Any]:
    required = {
        "panel_path": panel_path,
        "state_panel_path": state_panel_path,
        "execution_price_csv": execution_price_csv,
        "benchmark_csv": benchmark_csv,
    }
    missing = [name for name, path in required.items() if not path.exists()]
    panel_dates = _panel_dates(panel_path, start_date, end_date) if panel_path.exists() else []
    state_covered_dates = _state_covered_dates(panel_path, state_panel_path, start_date, end_date) if panel_path.exists() and state_panel_path.exists() else []
    price_dates = _csv_dates(execution_price_csv, start_date, end_date) if execution_price_csv.exists() else []
    benchmark_dates = _csv_dates(benchmark_csv, start_date, end_date) if benchmark_csv.exists() else []
    dividend_exists = dividend_cash_csv.exists() if dividend_cash_csv else False
    blockers = list(missing)
    if panel_dates and len(state_covered_dates) < len(panel_dates):
        blockers.append("state_panel_missing_visible_rebalance_dates")
    if execution_price_csv.exists() and len(price_dates) == 0:
        blockers.append("execution_price_csv_has_no_window_rows")
    if benchmark_csv.exists() and len(benchmark_dates) == 0:
        blockers.append("benchmark_csv_has_no_window_rows")
    return {
        "status": "ready" if not blockers else "blocked",
        "blockers": blockers,
        "window": {"start_date": start_date, "end_date": end_date},
        "panel_rebalance_dates": len(panel_dates),
        "state_covered_rebalance_dates": len(state_covered_dates),
        "execution_price_dates": len(price_dates),
        "benchmark_dates": len(benchmark_dates),
        "dividend_cash_csv": str(dividend_cash_csv) if dividend_cash_csv else None,
        "dividend_cash_csv_exists": dividend_exists,
        "notes": [
            "Use separate utilities execution price and benchmark CSVs; do not overwrite bank platform-replication data.",
            "Dividend cash CSV is optional for a first smoke run, but required before platform replication.",
        ],
    }


def run_utilities_daily_joinquant_like_backtest(
    spec_path: Path,
    panel_path: Path,
    state_panel_path: Path,
    execution_price_csv: Path,
    benchmark_csv: Path,
    out_dir: Path = DEFAULT_OUT_DIR,
    dividend_cash_csv: Path | None = None,
    benchmark_id: str = "utilities_benchmark",
    metric: str = "electricity_consumption_yoy",
    options: BacktestOptions | None = None,
    min_history: int = 8,
) -> Path:
    options = options or BacktestOptions(execution_mode="joinquant_like")
    readiness = check_utilities_daily_backtest_ready(
        panel_path,
        state_panel_path,
        execution_price_csv,
        benchmark_csv,
        dividend_cash_csv,
        options.start_date,
        options.end_date,
    )
    if readiness["status"] != "ready":
        raise RuntimeError("utilities daily backtest is not ready: " + ";".join(readiness["blockers"]))
    raw_spec = _read_json(spec_path)
    signals, signal_rows = build_utilities_v51f_signals(panel_path, state_panel_path, raw_spec, options, metric, min_history)
    prices_by_date = _load_execution_prices(execution_price_csv, options.start_date, options.end_date)
    benchmarks = _load_benchmark_closes(benchmark_csv, benchmark_id, options.start_date, options.end_date)
    cash_dividends = _load_cash_dividends(dividend_cash_csv, options.start_date, options.end_date)
    daily_rows, holding_rows, trade_rows, dividend_rows = _simulate_daily(prices_by_date, benchmarks, cash_dividends, signals, raw_spec, options)
    for row in daily_rows:
        row["benchmark_source"] = benchmark_id
    order_health_rows, order_health_summary = build_rebalance_order_health(signals, daily_rows, trade_rows, holding_rows)
    metrics = _compute_metrics(daily_rows)
    out = out_dir / raw_spec["meta"]["strategy_id"]
    out.mkdir(parents=True, exist_ok=True)
    summary = {
        "strategy_id": raw_spec["meta"]["strategy_id"],
        "mode": "utilities_daily_joinquant_like",
        "experiment_layer": "engineering_smoke_test",
        "panel": str(panel_path),
        "state_panel": str(state_panel_path),
        "execution_price_csv": str(execution_price_csv),
        "benchmark_csv": str(benchmark_csv),
        "benchmark_id": benchmark_id,
        "dividend_cash_csv": str(dividend_cash_csv) if dividend_cash_csv else None,
        "readiness": readiness,
        "signal_count": len(signals),
        "daily_count": len(daily_rows),
        "rebalance_order_health": order_health_summary,
        "metrics": metrics,
        "execution": {
            "initial_cash": options.initial_cash,
            "target_exposure": options.target_exposure,
            "lot_size": options.lot_size,
            "open_commission": options.open_commission,
            "close_commission": options.close_commission,
            "min_commission": options.min_commission,
            "trade_price": "daily_open",
            "valuation_price": "daily_close",
        },
        "outputs": {
            "summary": "summary.json",
            "daily_returns": "daily_returns.csv",
            "holdings": "holdings.csv",
            "trades": "trades.csv",
            "dividends": "dividends.csv",
            "rebalance_order_health": "rebalance_order_health.csv",
            "rebalance_signals": "rebalance_signals.csv",
        },
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "notes": [
            "This is a local JoinQuant-like daily simulation, not platform replication.",
            "Execution uses daily-open approximation; JoinQuant scheduled intraday execution can differ.",
        ],
    }
    _write_json(out / "summary.json", summary)
    _write_csv(out / "daily_returns.csv", DAILY_RETURN_FIELDS, daily_rows)
    _write_csv(out / "holdings.csv", HOLDING_FIELDS, holding_rows)
    _write_csv(out / "trades.csv", TRADE_FIELDS, trade_rows)
    _write_csv(out / "dividends.csv", DIVIDEND_FIELDS, dividend_rows)
    _write_csv(out / "rebalance_order_health.csv", ORDER_HEALTH_FIELDS, order_health_rows)
    _write_csv(out / "rebalance_signals.csv", SIGNAL_FIELDS, signal_rows)
    return out / "summary.json"


def build_utilities_v51f_signals(
    panel_path: Path,
    state_panel_path: Path,
    raw_spec: dict[str, Any],
    options: BacktestOptions,
    metric: str = "electricity_consumption_yoy",
    min_history: int = 8,
) -> tuple[dict[str, list[str]], list[dict[str, Any]]]:
    rows = _read_csv(panel_path)
    states = _read_csv(state_panel_path)
    start = _parse_date(options.start_date)
    end = _parse_date(options.end_date)
    panel_rows = []
    for row in rows:
        if not row.get("trade_date") or not row.get("code"):
            continue
        day = _parse_date(row["trade_date"])
        if start <= day <= end:
            panel_rows.append(row)
    by_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in panel_rows:
        by_date[row["trade_date"]].append(row)
    state_by_date = _latest_visible_state_by_date(dict(by_date), states, metric)
    selection_count = int(raw_spec["portfolio"]["selection_count"])
    history: list[float] = []
    signals: dict[str, list[str]] = {}
    signal_rows: list[dict[str, Any]] = []
    for trade_date in sorted(by_date):
        state = state_by_date.get(trade_date)
        if state is None:
            continue
        state_value = float(state["value"])
        bucket = _expanding_bucket(history, state_value, min_history)
        case_name = _case_for_bucket(bucket)
        selected, factor_name = _select_case(by_date[trade_date], case_name, selection_count)
        signals[trade_date] = [row["code"] for row in selected]
        signal_rows.append(
            {
                "trade_date": trade_date,
                "state_visible_date": state["visible_date"],
                "state_date": state["state_date"],
                "state_value": state_value,
                "state_bucket": bucket,
                "case": case_name,
                "factor": factor_name,
                "candidate_count": len(by_date[trade_date]),
                "selected_count": len(selected),
                "selected_codes": ";".join(signals[trade_date]),
            }
        )
        history.append(state_value)
    return signals, signal_rows


def _case_for_bucket(bucket: str) -> str:
    if bucket == "strong":
        return "raw_low_pb_utilities_top10"
    if bucket == "weak":
        return "raw_high_dividend_utilities_top10"
    return "raw_cashflow_yield_utilities_top10"


def _select_case(rows: list[dict[str, str]], case_name: str, selection_count: int) -> tuple[list[dict[str, str]], str]:
    factor, direction = CASE_FACTORS[case_name]
    usable = [row for row in rows if _to_float(row.get(factor)) is not None]
    selected = sorted(usable, key=lambda row: _to_float(row.get(factor)) or 0.0, reverse=direction == "higher_is_better")[:selection_count]
    return selected, factor


def _panel_dates(path: Path, start_date: str, end_date: str) -> list[str]:
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    return sorted({row["trade_date"] for row in _read_csv(path) if row.get("trade_date") and start <= _parse_date(row["trade_date"]) <= end})


def _state_covered_dates(panel_path: Path, state_panel_path: Path, start_date: str, end_date: str) -> list[str]:
    rows = [row for row in _read_csv(panel_path) if row.get("trade_date")]
    by_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    for row in rows:
        day = _parse_date(row["trade_date"])
        if start <= day <= end:
            by_date[row["trade_date"]].append(row)
    state_by_date = _latest_visible_state_by_date(dict(by_date), _read_csv(state_panel_path), "electricity_consumption_yoy")
    return sorted(state_by_date)


def _csv_dates(path: Path, start_date: str, end_date: str) -> list[str]:
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    dates = set()
    for row in _read_csv(path):
        day_text = row.get("date") or row.get("day") or row.get("trade_date")
        if not day_text:
            continue
        day = _parse_date(day_text)
        if start <= day <= end:
            dates.add(day.isoformat())
    return sorted(dates)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-utilities-daily-backtest")
    subparsers = parser.add_subparsers(dest="command", required=True)
    ready = subparsers.add_parser("ready")
    ready.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    ready.add_argument("--state-panel", type=Path, default=Path("数据库") / "processed" / "utilities_external_state" / "utilities_external_state.csv")
    ready.add_argument("--execution-price-csv", type=Path, required=True)
    ready.add_argument("--benchmark-csv", type=Path, required=True)
    ready.add_argument("--dividend-cash-csv", type=Path)
    ready.add_argument("--start-date", default="2021-05-01")
    ready.add_argument("--end-date", default="2026-05-31")
    run = subparsers.add_parser("run")
    run.add_argument("spec", type=Path)
    run.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    run.add_argument("--state-panel", type=Path, default=Path("数据库") / "processed" / "utilities_external_state" / "utilities_external_state.csv")
    run.add_argument("--execution-price-csv", type=Path, required=True)
    run.add_argument("--benchmark-csv", type=Path, required=True)
    run.add_argument("--benchmark-id", default="utilities_benchmark")
    run.add_argument("--dividend-cash-csv", type=Path)
    run.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR)
    run.add_argument("--start-date", default="2021-05-01")
    run.add_argument("--end-date", default="2026-05-31")
    run.add_argument("--initial-cash", type=float, default=2_000_000.0)
    args = parser.parse_args(argv)
    if args.command == "ready":
        print(
            json.dumps(
                check_utilities_daily_backtest_ready(
                    args.panel,
                    args.state_panel,
                    args.execution_price_csv,
                    args.benchmark_csv,
                    args.dividend_cash_csv,
                    args.start_date,
                    args.end_date,
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    options = BacktestOptions(
        execution_mode="joinquant_like",
        start_date=args.start_date,
        end_date=args.end_date,
        initial_cash=args.initial_cash,
    )
    print(
        run_utilities_daily_joinquant_like_backtest(
            args.spec,
            args.panel,
            args.state_panel,
            args.execution_price_csv,
            args.benchmark_csv,
            args.out,
            args.dividend_cash_csv,
            args.benchmark_id,
            options=options,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
