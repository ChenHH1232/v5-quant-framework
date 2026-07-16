from __future__ import annotations

import argparse
from pathlib import Path

from v5.overfit_audit_runner import run_overfit_audit
from v5.platform_attribution_runner import run_platform_attribution, run_position_attribution, run_transaction_attribution
from v5.platform_replication_runner import run_platform_replication_packet
from v5.universe_runner import build_point_in_time_universe


def register_platform_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    universe_parser = subparsers.add_parser("build-universe")
    universe_parser.add_argument("panel", type=Path)
    universe_parser.add_argument("execution_price_csv", type=Path)
    universe_parser.add_argument("--out", type=Path, default=Path("universes"))
    universe_parser.add_argument("--strategy-id", default="bank_value_15y")
    universe_parser.set_defaults(handler=_handle_build_universe)

    overfit_parser = subparsers.add_parser("overfit-audit")
    overfit_parser.add_argument("spec", type=Path)
    overfit_parser.add_argument("--panel", type=Path)
    overfit_parser.add_argument("--daily-returns-csv", type=Path)
    overfit_parser.add_argument("--rebalance-signals-csv", type=Path)
    overfit_parser.add_argument("--out", type=Path, default=Path("validation_overfit"))
    overfit_parser.add_argument("--strategy-id")
    overfit_parser.add_argument("--random-seed", type=int, default=20260716)
    overfit_parser.add_argument("--random-windows", type=int, default=100)
    overfit_parser.add_argument("--min-window-days", type=int, default=252)
    overfit_parser.set_defaults(handler=_handle_overfit_audit)

    attribution_parser = subparsers.add_parser("platform-attribution")
    attribution_parser.add_argument("local_daily_csv", type=Path)
    attribution_parser.add_argument("joinquant_daily_csv", type=Path)
    attribution_parser.add_argument("--out", type=Path, default=Path("platform_attribution"))
    attribution_parser.add_argument("--strategy-id", default="bank_value_15y")
    attribution_parser.add_argument("--local-rebalance-signals-csv", type=Path)
    attribution_parser.add_argument("--local-trades-csv", type=Path)
    attribution_parser.add_argument("--local-dividends-csv", type=Path)
    attribution_parser.set_defaults(handler=_handle_platform_attribution)

    position_parser = subparsers.add_parser("platform-position-attribution")
    position_parser.add_argument("joinquant_position_csv", type=Path)
    position_parser.add_argument("local_holdings_csv", type=Path)
    position_parser.add_argument("--out", type=Path, default=Path("platform_attribution"))
    position_parser.add_argument("--strategy-id", default="bank_value_15y")
    position_parser.set_defaults(handler=_handle_position_attribution)

    transaction_parser = subparsers.add_parser("platform-transaction-attribution")
    transaction_parser.add_argument("joinquant_transaction_csv", type=Path)
    transaction_parser.add_argument("local_trades_csv", type=Path)
    transaction_parser.add_argument("--out", type=Path, default=Path("platform_attribution"))
    transaction_parser.add_argument("--strategy-id", default="bank_value_15y")
    transaction_parser.set_defaults(handler=_handle_transaction_attribution)

    packet_parser = subparsers.add_parser("platform-replication-packet")
    packet_parser.add_argument("local_run_dir", type=Path)
    packet_parser.add_argument("--out", type=Path, default=Path("platform_replication_packets"))
    packet_parser.add_argument("--strategy-id", default="bank_value_15y")
    packet_parser.add_argument("--panel-csv", type=Path)
    packet_parser.add_argument("--joinquant-daily-csv", type=Path)
    packet_parser.add_argument("--joinquant-transaction-csv", type=Path)
    packet_parser.add_argument("--joinquant-position-csv", type=Path)
    packet_parser.add_argument("--expected-rebalance-date", action="append", default=[])
    packet_parser.add_argument("--final-strategy-diff-threshold", type=float, default=0.01)
    packet_parser.add_argument("--max-strategy-diff-threshold", type=float, default=0.03)
    packet_parser.set_defaults(handler=_handle_platform_replication_packet)


def _handle_build_universe(args: argparse.Namespace) -> int:
    print(build_point_in_time_universe(args.panel, args.execution_price_csv, args.out, args.strategy_id))
    return 0


def _handle_overfit_audit(args: argparse.Namespace) -> int:
    result = run_overfit_audit(
        args.spec,
        args.out,
        panel_path=args.panel,
        daily_returns_csv=args.daily_returns_csv,
        rebalance_signals_csv=args.rebalance_signals_csv,
        strategy_id=args.strategy_id,
        random_seed=args.random_seed,
        random_windows=args.random_windows,
        min_window_days=args.min_window_days,
    )
    print(result.report_path)
    return 0 if result.blocker_count == 0 else 2


def _handle_platform_attribution(args: argparse.Namespace) -> int:
    print(run_platform_attribution(args.local_daily_csv, args.joinquant_daily_csv, args.out, args.strategy_id, local_rebalance_signals_csv=args.local_rebalance_signals_csv, local_trades_csv=args.local_trades_csv, local_dividends_csv=args.local_dividends_csv))
    return 0


def _handle_position_attribution(args: argparse.Namespace) -> int:
    print(run_position_attribution(args.joinquant_position_csv, args.local_holdings_csv, args.out, args.strategy_id))
    return 0


def _handle_transaction_attribution(args: argparse.Namespace) -> int:
    print(run_transaction_attribution(args.joinquant_transaction_csv, args.local_trades_csv, args.out, args.strategy_id))
    return 0


def _handle_platform_replication_packet(args: argparse.Namespace) -> int:
    print(
        run_platform_replication_packet(
            args.local_run_dir,
            args.joinquant_daily_csv,
            args.out,
            args.strategy_id,
            panel_csv=args.panel_csv,
            joinquant_transaction_csv=args.joinquant_transaction_csv,
            joinquant_position_csv=args.joinquant_position_csv,
            expected_rebalance_dates=args.expected_rebalance_date,
            final_strategy_diff_threshold=args.final_strategy_diff_threshold,
            max_strategy_diff_threshold=args.max_strategy_diff_threshold,
        )
    )
    return 0
