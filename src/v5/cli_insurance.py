from __future__ import annotations

import argparse
import json
from pathlib import Path

from v5.insurance_daily_backtest_runner import DEFAULT_BENCHMARK_ID, check_insurance_daily_backtest_ready, run_insurance_daily_joinquant_like_backtest
from v5.insurance_failure_attribution_runner import run_insurance_failure_year_attribution
from v5.local_backtest import DEFAULT_BACKTEST_END, DEFAULT_BACKTEST_START, BacktestOptions


def register_insurance_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    insurance_daily_parser = subparsers.add_parser("insurance-daily-backtest")
    insurance_daily_subparsers = insurance_daily_parser.add_subparsers(dest="insurance_daily_command", required=True)
    insurance_daily_ready = insurance_daily_subparsers.add_parser("ready")
    insurance_daily_ready.add_argument("--panel", type=Path, required=True)
    insurance_daily_ready.add_argument("--execution-price-csv", type=Path, required=True)
    insurance_daily_ready.add_argument("--dividend-cash-csv", type=Path)
    insurance_daily_ready.add_argument("--start-date", default=DEFAULT_BACKTEST_START)
    insurance_daily_ready.add_argument("--end-date", default=DEFAULT_BACKTEST_END)
    insurance_daily_ready.set_defaults(handler=_handle_insurance_daily_backtest)
    insurance_daily_run = insurance_daily_subparsers.add_parser("run")
    insurance_daily_run.add_argument("spec", type=Path)
    insurance_daily_run.add_argument("--panel", type=Path, required=True)
    insurance_daily_run.add_argument("--execution-price-csv", type=Path, required=True)
    insurance_daily_run.add_argument("--benchmark-csv", type=Path)
    insurance_daily_run.add_argument("--benchmark-id", default=DEFAULT_BENCHMARK_ID)
    insurance_daily_run.add_argument("--dividend-cash-csv", type=Path)
    insurance_daily_run.add_argument("--out", type=Path, default=Path("local_daily_backtests_insurance_v53c"))
    insurance_daily_run.add_argument("--start-date", default=DEFAULT_BACKTEST_START)
    insurance_daily_run.add_argument("--end-date", default=DEFAULT_BACKTEST_END)
    insurance_daily_run.add_argument("--initial-cash", type=float, default=2_000_000.0)
    insurance_daily_run.set_defaults(handler=_handle_insurance_daily_backtest)

    insurance_failure_parser = subparsers.add_parser("insurance-failure-attribution")
    insurance_failure_parser.add_argument("--daily-returns-csv", type=Path, required=True)
    insurance_failure_parser.add_argument("--rebalance-signals-csv", type=Path, required=True)
    insurance_failure_parser.add_argument("--trades-csv", type=Path, required=True)
    insurance_failure_parser.add_argument("--dividends-csv", type=Path, required=True)
    insurance_failure_parser.add_argument("--out", type=Path, default=Path("failure_attribution_insurance_v53c"))
    insurance_failure_parser.add_argument("--strategy-id", default="insurance_low_pb_only_v53c")
    insurance_failure_parser.add_argument("--years", nargs="+", default=["2021", "2026"])
    insurance_failure_parser.set_defaults(handler=_handle_insurance_failure_attribution)


def _handle_insurance_daily_backtest(args: argparse.Namespace) -> int:
    if args.insurance_daily_command == "ready":
        print(json.dumps(check_insurance_daily_backtest_ready(args.panel, args.execution_price_csv, args.start_date, args.end_date, args.dividend_cash_csv), ensure_ascii=False, indent=2))
        return 0
    print(
        run_insurance_daily_joinquant_like_backtest(
            args.spec,
            args.panel,
            args.execution_price_csv,
            args.out,
            args.benchmark_csv,
            args.benchmark_id,
            args.dividend_cash_csv,
            options=BacktestOptions(execution_mode="joinquant_like", start_date=args.start_date, end_date=args.end_date, initial_cash=args.initial_cash),
        )
    )
    return 0


def _handle_insurance_failure_attribution(args: argparse.Namespace) -> int:
    print(run_insurance_failure_year_attribution(args.daily_returns_csv, args.rebalance_signals_csv, args.trades_csv, args.dividends_csv, args.out, args.strategy_id, args.years))
    return 0
