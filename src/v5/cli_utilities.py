from __future__ import annotations

import argparse
import json
from pathlib import Path

from v5.local_backtest import DEFAULT_BACKTEST_END, DEFAULT_BACKTEST_START, BacktestOptions
from v5.paths import DEFAULT_PROCESSED_DIR
from v5.sector_rank_panel_runner import build_sector_rank_panel
from v5.utilities_daily_backtest_runner import check_utilities_daily_backtest_ready, run_utilities_daily_joinquant_like_backtest
from v5.utilities_demand_state_validation_runner import run_utilities_demand_state_validation
from v5.utilities_external_state_runner import collect_utilities_external_state, validate_utilities_external_state, write_utilities_external_state_template
from v5.utilities_golden_workflow_runner import run_utilities_golden_workflow_audit
from v5.utilities_model_panel_runner import build_utilities_cashflow_value_panel
from v5.utilities_pit_panel_runner import collect_utilities_pit_panel


def register_utilities_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    utilities_pit_parser = subparsers.add_parser("collect-utilities-pit-panel")
    utilities_pit_parser.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "utilities_pit_panel")
    utilities_pit_parser.add_argument("--start-date", default="2017-01-01")
    utilities_pit_parser.add_argument("--end-date", default="2026-05-31")
    utilities_pit_parser.add_argument("--listing-age-days", type=int, default=180)
    utilities_pit_parser.set_defaults(handler=_handle_collect_utilities_pit_panel)

    utilities_model_panel_parser = subparsers.add_parser("build-utilities-cashflow-value-panel")
    utilities_model_panel_parser.add_argument("source_panel", type=Path, nargs="?", default=DEFAULT_PROCESSED_DIR / "utilities_pit_panel" / "panel.csv")
    utilities_model_panel_parser.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "utilities_cashflow_value_v51b_panel")
    utilities_model_panel_parser.set_defaults(handler=_handle_build_utilities_cashflow_value_panel)

    sector_rank_parser = subparsers.add_parser("build-sector-rank-panel")
    sector_rank_parser.add_argument("source_panel", type=Path)
    sector_rank_parser.add_argument("factor_config", type=Path)
    sector_rank_parser.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "sector_rank_panel")
    sector_rank_parser.add_argument("--date-field", default="trade_date")
    sector_rank_parser.add_argument("--group-field", default="sub_industry")
    sector_rank_parser.add_argument("--min-group-size", type=int, default=8)
    sector_rank_parser.set_defaults(handler=_handle_build_sector_rank_panel)

    utilities_state_parser = subparsers.add_parser("utilities-external-state")
    utilities_state_subparsers = utilities_state_parser.add_subparsers(dest="state_command", required=True)
    utilities_state_template = utilities_state_subparsers.add_parser("template")
    utilities_state_template.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "utilities_external_state")
    utilities_state_template.set_defaults(handler=_handle_utilities_external_state)
    utilities_state_collect = utilities_state_subparsers.add_parser("collect")
    utilities_state_collect.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "utilities_external_state")
    utilities_state_collect.set_defaults(handler=_handle_utilities_external_state)
    utilities_state_validate = utilities_state_subparsers.add_parser("validate")
    utilities_state_validate.add_argument("csv_path", type=Path)
    utilities_state_validate.set_defaults(handler=_handle_utilities_external_state)

    utilities_demand_state_parser = subparsers.add_parser("validate-utilities-demand-state")
    utilities_demand_state_parser.add_argument("--panel", type=Path, default=DEFAULT_PROCESSED_DIR / "utilities_cashflow_value_v51b_panel" / "panel.csv")
    utilities_demand_state_parser.add_argument("--state-panel", type=Path, default=DEFAULT_PROCESSED_DIR / "utilities_external_state" / "utilities_external_state.csv")
    utilities_demand_state_parser.add_argument("--out", type=Path, default=Path("validation_formal_v51e"))
    utilities_demand_state_parser.add_argument("--metric", default="electricity_consumption_yoy")
    utilities_demand_state_parser.add_argument("--selection-count", type=int, default=10)
    utilities_demand_state_parser.add_argument("--min-history", type=int, default=8)
    utilities_demand_state_parser.set_defaults(handler=_handle_validate_utilities_demand_state)

    utilities_daily_parser = subparsers.add_parser("utilities-daily-backtest")
    utilities_daily_subparsers = utilities_daily_parser.add_subparsers(dest="utilities_daily_command", required=True)
    utilities_daily_ready = utilities_daily_subparsers.add_parser("ready")
    utilities_daily_ready.add_argument("--panel", type=Path, default=DEFAULT_PROCESSED_DIR / "utilities_cashflow_value_v51b_panel" / "panel.csv")
    utilities_daily_ready.add_argument("--state-panel", type=Path, default=DEFAULT_PROCESSED_DIR / "utilities_external_state" / "utilities_external_state.csv")
    utilities_daily_ready.add_argument("--execution-price-csv", type=Path, required=True)
    utilities_daily_ready.add_argument("--benchmark-csv", type=Path, required=True)
    utilities_daily_ready.add_argument("--dividend-cash-csv", type=Path)
    utilities_daily_ready.add_argument("--start-date", default=DEFAULT_BACKTEST_START)
    utilities_daily_ready.add_argument("--end-date", default=DEFAULT_BACKTEST_END)
    utilities_daily_ready.set_defaults(handler=_handle_utilities_daily_backtest)
    utilities_daily_run = utilities_daily_subparsers.add_parser("run")
    utilities_daily_run.add_argument("spec", type=Path)
    utilities_daily_run.add_argument("--panel", type=Path, default=DEFAULT_PROCESSED_DIR / "utilities_cashflow_value_v51b_panel" / "panel.csv")
    utilities_daily_run.add_argument("--state-panel", type=Path, default=DEFAULT_PROCESSED_DIR / "utilities_external_state" / "utilities_external_state.csv")
    utilities_daily_run.add_argument("--execution-price-csv", type=Path, required=True)
    utilities_daily_run.add_argument("--benchmark-csv", type=Path, required=True)
    utilities_daily_run.add_argument("--benchmark-id", default="utilities_benchmark")
    utilities_daily_run.add_argument("--dividend-cash-csv", type=Path)
    utilities_daily_run.add_argument("--out", type=Path, default=Path("local_daily_backtests_utilities_v51f"))
    utilities_daily_run.add_argument("--start-date", default=DEFAULT_BACKTEST_START)
    utilities_daily_run.add_argument("--end-date", default=DEFAULT_BACKTEST_END)
    utilities_daily_run.add_argument("--initial-cash", type=float, default=2_000_000.0)
    utilities_daily_run.set_defaults(handler=_handle_utilities_daily_backtest)

    utilities_golden_parser = subparsers.add_parser("utilities-golden-workflow-audit")
    utilities_golden_parser.add_argument("--out-dir", type=Path, default=Path("docs") / "governance")
    utilities_golden_parser.set_defaults(handler=_handle_utilities_golden_workflow_audit)


def _handle_collect_utilities_pit_panel(args: argparse.Namespace) -> int:
    result = collect_utilities_pit_panel(out_dir=args.out_dir, start_date=args.start_date, end_date=args.end_date, listing_age_days=args.listing_age_days)
    print(result.panel_path)
    return 0


def _handle_build_utilities_cashflow_value_panel(args: argparse.Namespace) -> int:
    print(build_utilities_cashflow_value_panel(args.source_panel, args.out_dir))
    return 0


def _handle_build_sector_rank_panel(args: argparse.Namespace) -> int:
    print(build_sector_rank_panel(args.source_panel, args.out_dir, args.factor_config, date_field=args.date_field, group_field=args.group_field, min_group_size=args.min_group_size))
    return 0


def _handle_utilities_external_state(args: argparse.Namespace) -> int:
    if args.state_command == "template":
        print(write_utilities_external_state_template(args.out_dir))
    elif args.state_command == "collect":
        print(collect_utilities_external_state(args.out_dir))
    else:
        print(json.dumps(validate_utilities_external_state(args.csv_path), ensure_ascii=False, indent=2))
    return 0


def _handle_validate_utilities_demand_state(args: argparse.Namespace) -> int:
    print(run_utilities_demand_state_validation(args.panel, args.state_panel, args.out, args.metric, args.selection_count, args.min_history))
    return 0


def _handle_utilities_daily_backtest(args: argparse.Namespace) -> int:
    if args.utilities_daily_command == "ready":
        print(json.dumps(check_utilities_daily_backtest_ready(args.panel, args.state_panel, args.execution_price_csv, args.benchmark_csv, args.dividend_cash_csv, args.start_date, args.end_date), ensure_ascii=False, indent=2))
        return 0
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
            options=BacktestOptions(execution_mode="joinquant_like", start_date=args.start_date, end_date=args.end_date, initial_cash=args.initial_cash),
        )
    )
    return 0


def _handle_utilities_golden_workflow_audit(args: argparse.Namespace) -> int:
    print(run_utilities_golden_workflow_audit(args.out_dir))
    return 0
