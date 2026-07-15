from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from v5.benchmark_runner import (
    DEFAULT_BENCHMARK_ID,
    DEFAULT_BENCHMARK_PROCESSED,
    collect_bank_benchmarks,
)
from v5.bank_quality_date_alignment_runner import DEFAULT_DATABASE_DIR as DATE_ALIGNMENT_DATABASE_DIR
from v5.bank_quality_date_alignment_runner import align_bank_quality_dates
from v5.data_runner import collect_panel_from_v4_raw, write_collection_manifest
from v5.daily_backtest import run_daily_joinquant_like_backtest
from v5.dividend_runner import DEFAULT_DATABASE_DIR, DEFAULT_DIVIDEND_PROCESSED, collect_bank_dividends
from v5.eastmoney_bank_indicator_runner import (
    DEFAULT_V4_EXTRACTED_VALUES,
    collect_eastmoney_bank_indicators,
)
from v5.engine import RunBlockedError, run_strategy, validate_spec_file
from v5.joinquant_real_data_runner import collect_joinquant_real_data
from v5.joinquant_capability_probe import run_joinquant_capability_probe
from v5.joinquant_pit_panel_runner import collect_joinquant_basic_pit_panel
from v5.joinquant_availability_runner import build_joinquant_availability_proxy, collect_joinquant_bank_indicator_pubdates
from v5.local_backtest import DEFAULT_BACKTEST_END, DEFAULT_BACKTEST_START, BacktestOptions, run_local_backtest
from v5.formal_validation_runner import run_formal_validation
from v5.platform_attribution_runner import run_platform_attribution, run_position_attribution, run_transaction_attribution
from v5.platform_replication_runner import run_platform_replication_packet
from v5.tushare_disclosure_runner import collect_tushare_disclosure_dates
from v5.universe_runner import build_point_in_time_universe
from v5.utilities_model_panel_runner import build_utilities_cashflow_value_panel
from v5.utilities_pit_panel_runner import collect_utilities_pit_panel
from v5.validation_runner import validate_panel
from v5.v4_quality_source_date_audit_runner import audit_v4_quality_source_dates
from v5.v4_legacy_bank_quality_runner import (
    DEFAULT_V4_PHASE1_PANEL,
    collect_v4_legacy_bank_quality,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("spec", type=Path)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("spec", type=Path)
    run_parser.add_argument("--out", type=Path, default=Path("experiments"))
    run_parser.add_argument("--allow-blockers", action="store_true")

    collect_parser = subparsers.add_parser("collect-data")
    collect_parser.add_argument("spec", type=Path)
    collect_parser.add_argument("--out", type=Path, default=Path("data/processed"))
    collect_parser.add_argument("--mode", choices=["plan", "v4-raw"], default="plan")
    collect_parser.add_argument(
        "--v4-raw-dir",
        type=Path,
        default=Path(r"D:\hh\codex\v4\phase_1_fundamental\raw_downloads\all_banks"),
    )
    collect_parser.add_argument("--price-adjustment", default="unconfirmed_v4_raw")
    collect_parser.add_argument("--dividend-csv", type=Path)
    collect_parser.add_argument("--benchmark-csv", type=Path)
    collect_parser.add_argument("--benchmark-id", default=DEFAULT_BENCHMARK_ID)
    collect_parser.add_argument(
        "--total-return-mode",
        choices=["adjusted_total_return", "price_plus_net_cash_dividend", "price_plus_gross_cash_dividend"],
        default="adjusted_total_return",
    )
    collect_parser.add_argument("--dividend-tax-rate", type=float, default=0.2)

    dividend_parser = subparsers.add_parser("collect-dividends")
    dividend_parser.add_argument("panel", type=Path)
    dividend_parser.add_argument("--database-dir", type=Path, default=DEFAULT_DATABASE_DIR)
    dividend_parser.add_argument("--start-date")
    dividend_parser.add_argument("--end-date")

    benchmark_parser = subparsers.add_parser("collect-benchmarks")
    benchmark_parser.add_argument("--database-dir", type=Path, default=DEFAULT_DATABASE_DIR)
    benchmark_parser.add_argument("--start-date", default="2011-01-01")
    benchmark_parser.add_argument("--end-date", default="2026-07-14")

    eastmoney_parser = subparsers.add_parser("collect-eastmoney-bank-indicators")
    eastmoney_parser.add_argument("--source-csv", type=Path, default=DEFAULT_V4_EXTRACTED_VALUES)
    eastmoney_parser.add_argument("--out-dir", type=Path, default=DEFAULT_DATABASE_DIR / "processed")
    eastmoney_parser.add_argument(
        "--min-review-status",
        choices=["reviewed", "needs_check", "unreviewed"],
        default="needs_check",
    )

    v4_quality_parser = subparsers.add_parser("collect-v4-legacy-bank-quality")
    v4_quality_parser.add_argument("--source-panel", type=Path, default=DEFAULT_V4_PHASE1_PANEL)
    v4_quality_parser.add_argument("--out-dir", type=Path, default=DEFAULT_DATABASE_DIR / "processed")

    research_validate_parser = subparsers.add_parser("validate-research")
    research_validate_parser.add_argument("spec", type=Path)
    research_validate_parser.add_argument("panel", type=Path)
    research_validate_parser.add_argument("--out", type=Path, default=Path("validation"))

    formal_validate_parser = subparsers.add_parser("validate-formal")
    formal_validate_parser.add_argument("spec", type=Path)
    formal_validate_parser.add_argument("panel", type=Path)
    formal_validate_parser.add_argument("--out", type=Path, default=Path("validation_formal"))
    formal_validate_parser.add_argument("--experiment-layer", default="research_pit_validation")

    local_backtest_parser = subparsers.add_parser("local-backtest")
    local_backtest_parser.add_argument("spec", type=Path)
    local_backtest_parser.add_argument("panel", type=Path)
    local_backtest_parser.add_argument("--out", type=Path, default=Path("local_backtests"))
    local_backtest_parser.add_argument("--start-date", default=DEFAULT_BACKTEST_START)
    local_backtest_parser.add_argument("--end-date", default=DEFAULT_BACKTEST_END)
    local_backtest_parser.add_argument("--min-coverage-ratio", type=float, default=0.8)
    local_backtest_parser.add_argument(
        "--execution-mode",
        choices=["ideal_equal_weight", "joinquant_like"],
        default="ideal_equal_weight",
    )
    local_backtest_parser.add_argument("--initial-cash", type=float, default=2_000_000.0)
    local_backtest_parser.add_argument("--target-exposure", type=float, default=0.995)
    local_backtest_parser.add_argument("--lot-size", type=int, default=100)
    local_backtest_parser.add_argument("--open-commission", type=float, default=0.0003)
    local_backtest_parser.add_argument("--close-commission", type=float, default=0.0003)
    local_backtest_parser.add_argument("--min-commission", type=float, default=5.0)
    local_backtest_parser.add_argument("--save-periods", action="store_true")
    local_backtest_parser.add_argument("--save-holdings", action="store_true")

    daily_backtest_parser = subparsers.add_parser("daily-backtest")
    daily_backtest_parser.add_argument("spec", type=Path)
    daily_backtest_parser.add_argument("panel", type=Path)
    daily_backtest_parser.add_argument(
        "--v4-raw-dir",
        type=Path,
        default=Path(r"D:\hh\codex\v4\phase_1_fundamental\raw_downloads\all_banks"),
    )
    daily_backtest_parser.add_argument("--benchmark-csv", type=Path, default=DEFAULT_BENCHMARK_PROCESSED)
    daily_backtest_parser.add_argument("--benchmark-id", default=DEFAULT_BENCHMARK_ID)
    daily_backtest_parser.add_argument("--execution-price-csv", type=Path)
    daily_backtest_parser.add_argument("--dividend-cash-csv", type=Path)
    daily_backtest_parser.add_argument("--eastmoney-quality-csv", type=Path)
    daily_backtest_parser.add_argument(
        "--eastmoney-min-review-status",
        choices=["reviewed", "needs_check", "unreviewed"],
        default="needs_check",
    )
    daily_backtest_parser.add_argument(
        "--eastmoney-visibility-mode",
        choices=["notice_date", "joinquant_source_year"],
        default="notice_date",
    )
    daily_backtest_parser.add_argument(
        "--experiment-layer",
        choices=["research_pit_validation", "platform_replication", "engineering_smoke_test", "paper_trading"],
        default="engineering_smoke_test",
    )
    daily_backtest_parser.add_argument("--snapshot-out", type=Path)
    daily_backtest_parser.add_argument("--out", type=Path, default=Path("local_daily_backtests"))
    daily_backtest_parser.add_argument("--start-date", default=DEFAULT_BACKTEST_START)
    daily_backtest_parser.add_argument("--end-date", default=DEFAULT_BACKTEST_END)
    daily_backtest_parser.add_argument("--initial-cash", type=float, default=2_000_000.0)
    daily_backtest_parser.add_argument("--target-exposure", type=float, default=0.995)
    daily_backtest_parser.add_argument("--defensive-mode", choices=["none", "benchmark_ma"], default="none")
    daily_backtest_parser.add_argument("--defensive-ma-days", type=int, default=252)
    daily_backtest_parser.add_argument("--defensive-risk-exposure", type=float, default=0.5)
    daily_backtest_parser.add_argument("--value-trap-guard-mode", choices=["apply", "disabled"], default="apply")
    daily_backtest_parser.add_argument(
        "--signal-dividend-yield-mode",
        choices=["panel", "cash_dividend_trailing"],
        default="panel",
    )

    jq_real_parser = subparsers.add_parser("collect-joinquant-real-data")
    jq_real_parser.add_argument("panel", type=Path)
    jq_real_parser.add_argument("--database-dir", type=Path, default=DEFAULT_DATABASE_DIR)
    jq_real_parser.add_argument("--start-date", default=DEFAULT_BACKTEST_START)
    jq_real_parser.add_argument("--end-date", default=DEFAULT_BACKTEST_END)
    jq_real_parser.add_argument("--benchmark", default="512800.XSHG")
    jq_real_parser.add_argument("--benchmark-fq", default="pre", choices=["pre", "post", "none"])
    jq_real_parser.add_argument("--dividend-csv", type=Path)
    jq_real_parser.add_argument("--dividend-tax-rate", type=float, default=0.2)

    jq_probe_parser = subparsers.add_parser("probe-joinquant-capabilities")
    jq_probe_parser.add_argument("--out-dir", type=Path, default=DEFAULT_DATABASE_DIR / "manifests")

    jq_availability_parser = subparsers.add_parser("build-joinquant-availability-proxy")
    jq_availability_parser.add_argument("--v4-quality-csv", type=Path, default=DATE_ALIGNMENT_DATABASE_DIR / "processed" / "v4_legacy_bank_quality.csv")
    jq_availability_parser.add_argument("--out-dir", type=Path, default=DATE_ALIGNMENT_DATABASE_DIR / "processed" / "joinquant_availability")

    jq_bank_indicator_parser = subparsers.add_parser("collect-joinquant-bank-indicator-pubdates")
    jq_bank_indicator_parser.add_argument("--v4-quality-csv", type=Path, default=DATE_ALIGNMENT_DATABASE_DIR / "processed" / "v4_legacy_bank_quality.csv")
    jq_bank_indicator_parser.add_argument("--out-dir", type=Path, default=DATE_ALIGNMENT_DATABASE_DIR / "processed" / "joinquant_availability")

    tushare_parser = subparsers.add_parser("collect-tushare-disclosure-dates")
    tushare_parser.add_argument("--quality-csv", type=Path, default=DATE_ALIGNMENT_DATABASE_DIR / "processed" / "v4_legacy_bank_quality.csv")
    tushare_parser.add_argument("--out-dir", type=Path, default=DATE_ALIGNMENT_DATABASE_DIR / "processed" / "tushare_disclosure_dates")
    tushare_parser.add_argument("--credential-file", type=Path)
    tushare_parser.add_argument("--token-env", default="TUSHARE_TOKEN")

    jq_pit_parser = subparsers.add_parser("collect-joinquant-basic-pit-panel")
    jq_pit_parser.add_argument("scaffold_panel", type=Path)
    jq_pit_parser.add_argument("--out-dir", type=Path, default=DEFAULT_DATABASE_DIR / "processed" / "joinquant_basic_pit_panel")
    jq_pit_parser.add_argument("--database-dir", type=Path, default=DEFAULT_DATABASE_DIR)
    jq_pit_parser.add_argument("--start-date", default="2014-01-01")
    jq_pit_parser.add_argument("--end-date", default="2026-05-31")
    jq_pit_parser.add_argument("--benchmark", default="512800.XSHG")
    jq_pit_parser.add_argument("--benchmark-fq", default="pre", choices=["pre", "post", "none"])
    jq_pit_parser.add_argument("--dividend-csv", type=Path)
    jq_pit_parser.add_argument("--dividend-tax-rate", type=float, default=0.2)
    jq_pit_parser.add_argument("--bank-quality-csv", type=Path)
    jq_pit_parser.add_argument(
        "--bank-quality-min-review-status",
        choices=["reviewed", "needs_check", "unreviewed"],
        default="needs_check",
    )

    utilities_pit_parser = subparsers.add_parser("collect-utilities-pit-panel")
    utilities_pit_parser.add_argument("--out-dir", type=Path, default=Path("数据库") / "processed" / "utilities_pit_panel")
    utilities_pit_parser.add_argument("--start-date", default="2017-01-01")
    utilities_pit_parser.add_argument("--end-date", default="2026-05-31")
    utilities_pit_parser.add_argument("--listing-age-days", type=int, default=180)

    utilities_model_panel_parser = subparsers.add_parser("build-utilities-cashflow-value-panel")
    utilities_model_panel_parser.add_argument("source_panel", type=Path, nargs="?", default=Path("数据库") / "processed" / "utilities_pit_panel" / "panel.csv")
    utilities_model_panel_parser.add_argument("--out-dir", type=Path, default=Path("数据库") / "processed" / "utilities_cashflow_value_v51b_panel")

    universe_parser = subparsers.add_parser("build-universe")
    universe_parser.add_argument("panel", type=Path)
    universe_parser.add_argument("execution_price_csv", type=Path)
    universe_parser.add_argument("--out", type=Path, default=Path("universes"))
    universe_parser.add_argument("--strategy-id", default="bank_value_15y")

    attribution_parser = subparsers.add_parser("platform-attribution")
    attribution_parser.add_argument("local_daily_csv", type=Path)
    attribution_parser.add_argument("joinquant_daily_csv", type=Path)
    attribution_parser.add_argument("--out", type=Path, default=Path("platform_attribution"))
    attribution_parser.add_argument("--strategy-id", default="bank_value_15y")
    attribution_parser.add_argument("--local-rebalance-signals-csv", type=Path)
    attribution_parser.add_argument("--local-trades-csv", type=Path)
    attribution_parser.add_argument("--local-dividends-csv", type=Path)

    source_date_audit_parser = subparsers.add_parser("audit-v4-quality-source-dates")
    source_date_audit_parser.add_argument("quality_csv", type=Path)
    source_date_audit_parser.add_argument("--out", type=Path, default=Path("validation_formal"))
    source_date_audit_parser.add_argument("--strategy-id", default="bank_high_dividend_sustainability_v3")

    date_alignment_parser = subparsers.add_parser("align-bank-quality-dates")
    date_alignment_parser.add_argument("--out-dir", type=Path, default=DATE_ALIGNMENT_DATABASE_DIR / "processed" / "bank_quality_date_alignment")
    date_alignment_parser.add_argument("--v4-quality-csv", type=Path, default=DATE_ALIGNMENT_DATABASE_DIR / "processed" / "v4_legacy_bank_quality.csv")
    date_alignment_parser.add_argument("--eastmoney-quality-csv", type=Path, default=DATE_ALIGNMENT_DATABASE_DIR / "processed" / "eastmoney_bank_quality_manual_csv.csv")
    date_alignment_parser.add_argument("--joinquant-availability-csv", type=Path)
    date_alignment_parser.add_argument("--external-notice-csv", type=Path)

    position_attribution_parser = subparsers.add_parser("platform-position-attribution")
    position_attribution_parser.add_argument("joinquant_position_csv", type=Path)
    position_attribution_parser.add_argument("local_holdings_csv", type=Path)
    position_attribution_parser.add_argument("--out", type=Path, default=Path("platform_attribution"))
    position_attribution_parser.add_argument("--strategy-id", default="bank_value_15y")

    transaction_attribution_parser = subparsers.add_parser("platform-transaction-attribution")
    transaction_attribution_parser.add_argument("joinquant_transaction_csv", type=Path)
    transaction_attribution_parser.add_argument("local_trades_csv", type=Path)
    transaction_attribution_parser.add_argument("--out", type=Path, default=Path("platform_attribution"))
    transaction_attribution_parser.add_argument("--strategy-id", default="bank_value_15y")

    platform_replication_parser = subparsers.add_parser("platform-replication-packet")
    platform_replication_parser.add_argument("local_run_dir", type=Path)
    platform_replication_parser.add_argument("--out", type=Path, default=Path("platform_replication_packets"))
    platform_replication_parser.add_argument("--strategy-id", default="bank_value_15y")
    platform_replication_parser.add_argument("--panel-csv", type=Path)
    platform_replication_parser.add_argument("--joinquant-daily-csv", type=Path)
    platform_replication_parser.add_argument("--joinquant-transaction-csv", type=Path)
    platform_replication_parser.add_argument("--joinquant-position-csv", type=Path)
    platform_replication_parser.add_argument("--expected-rebalance-date", action="append", default=[])
    platform_replication_parser.add_argument("--final-strategy-diff-threshold", type=float, default=0.01)
    platform_replication_parser.add_argument("--max-strategy-diff-threshold", type=float, default=0.03)

    args = parser.parse_args(argv)

    try:
        if args.command == "validate":
            result = validate_spec_file(args.spec)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result["audit"]["passed"] else 2
        if args.command == "run":
            run_dir = run_strategy(args.spec, args.out, allow_blockers=args.allow_blockers)
            print(str(run_dir))
            return 0
        if args.command == "collect-data":
            if args.mode == "plan":
                print(write_collection_manifest(args.spec, args.out))
            else:
                dividend_csv = args.dividend_csv
                if dividend_csv is None and DEFAULT_DIVIDEND_PROCESSED.exists():
                    dividend_csv = DEFAULT_DIVIDEND_PROCESSED
                benchmark_csv = args.benchmark_csv
                if benchmark_csv is None and DEFAULT_BENCHMARK_PROCESSED.exists():
                    benchmark_csv = DEFAULT_BENCHMARK_PROCESSED
                print(
                    collect_panel_from_v4_raw(
                        args.spec,
                        args.v4_raw_dir,
                        args.out,
                        price_adjustment=args.price_adjustment,
                        dividend_csv=dividend_csv,
                        benchmark_csv=benchmark_csv,
                        benchmark_id=args.benchmark_id,
                        total_return_mode=args.total_return_mode,
                        dividend_tax_rate=args.dividend_tax_rate,
                    )
                )
            return 0
        if args.command == "collect-dividends":
            result = collect_bank_dividends(args.panel, args.database_dir, args.start_date, args.end_date)
            print(result.processed_path)
            return 0
        if args.command == "collect-benchmarks":
            result = collect_bank_benchmarks(args.database_dir, args.start_date, args.end_date)
            print(result.processed_path)
            return 0
        if args.command == "collect-eastmoney-bank-indicators":
            result = collect_eastmoney_bank_indicators(
                args.source_csv,
                args.out_dir,
                args.min_review_status,
            )
            print(result.quality_path)
            return 0
        if args.command == "collect-v4-legacy-bank-quality":
            result = collect_v4_legacy_bank_quality(args.source_panel, args.out_dir)
            print(result.quality_path)
            return 0
        if args.command == "validate-research":
            print(validate_panel(args.spec, args.panel, args.out))
            return 0
        if args.command == "validate-formal":
            print(run_formal_validation(args.spec, args.panel, args.out, args.experiment_layer))
            return 0
        if args.command == "local-backtest":
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
        if args.command == "daily-backtest":
            report = run_daily_joinquant_like_backtest(
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
                    value_trap_guard_mode=args.value_trap_guard_mode,
                ),
                benchmark_id=args.benchmark_id,
                execution_price_csv=args.execution_price_csv,
                dividend_cash_csv=args.dividend_cash_csv,
                eastmoney_quality_csv=args.eastmoney_quality_csv,
                eastmoney_min_review_status=args.eastmoney_min_review_status,
                eastmoney_visibility_mode=args.eastmoney_visibility_mode,
                signal_dividend_yield_mode=args.signal_dividend_yield_mode,
                experiment_layer=args.experiment_layer,
                snapshot_out=args.snapshot_out,
            )
            print(report)
            return 0
        if args.command == "collect-joinquant-real-data":
            result = collect_joinquant_real_data(
                args.panel,
                database_dir=args.database_dir,
                start_date=args.start_date,
                end_date=args.end_date,
                benchmark=args.benchmark,
                benchmark_fq=None if args.benchmark_fq == "none" else args.benchmark_fq,
                dividend_csv=args.dividend_csv,
                dividend_tax_rate=args.dividend_tax_rate,
            )
            print(result.price_path)
            return 0
        if args.command == "probe-joinquant-capabilities":
            print(run_joinquant_capability_probe(args.out_dir))
            return 0
        if args.command == "build-joinquant-availability-proxy":
            result = build_joinquant_availability_proxy(args.v4_quality_csv, args.out_dir)
            print(result.availability_path)
            return 0
        if args.command == "collect-joinquant-bank-indicator-pubdates":
            result = collect_joinquant_bank_indicator_pubdates(args.v4_quality_csv, args.out_dir)
            print(result.availability_path)
            return 0
        if args.command == "collect-tushare-disclosure-dates":
            kwargs = {}
            if args.credential_file:
                kwargs["credential_file"] = args.credential_file
            result = collect_tushare_disclosure_dates(args.quality_csv, args.out_dir, token_env=args.token_env, **kwargs)
            print(result.disclosure_path)
            return 0
        if args.command == "collect-joinquant-basic-pit-panel":
            result = collect_joinquant_basic_pit_panel(
                args.scaffold_panel,
                args.out_dir,
                database_dir=args.database_dir,
                start_date=args.start_date,
                end_date=args.end_date,
                benchmark=args.benchmark,
                benchmark_fq=None if args.benchmark_fq == "none" else args.benchmark_fq,
                dividend_csv=args.dividend_csv,
                dividend_tax_rate=args.dividend_tax_rate,
                bank_quality_csv=args.bank_quality_csv,
                bank_quality_min_review_status=args.bank_quality_min_review_status,
            )
            print(result.panel_path)
            return 0
        if args.command == "collect-utilities-pit-panel":
            result = collect_utilities_pit_panel(
                out_dir=args.out_dir,
                start_date=args.start_date,
                end_date=args.end_date,
                listing_age_days=args.listing_age_days,
            )
            print(result.panel_path)
            return 0
        if args.command == "build-utilities-cashflow-value-panel":
            print(build_utilities_cashflow_value_panel(args.source_panel, args.out_dir))
            return 0
        if args.command == "build-universe":
            print(build_point_in_time_universe(args.panel, args.execution_price_csv, args.out, args.strategy_id))
            return 0
        if args.command == "platform-attribution":
            print(
                run_platform_attribution(
                    args.local_daily_csv,
                    args.joinquant_daily_csv,
                    args.out,
                    args.strategy_id,
                    local_rebalance_signals_csv=args.local_rebalance_signals_csv,
                    local_trades_csv=args.local_trades_csv,
                    local_dividends_csv=args.local_dividends_csv,
                )
            )
            return 0
        if args.command == "audit-v4-quality-source-dates":
            print(audit_v4_quality_source_dates(args.quality_csv, args.out, args.strategy_id))
            return 0
        if args.command == "align-bank-quality-dates":
            result = align_bank_quality_dates(
                args.out_dir,
                v4_quality_csv=args.v4_quality_csv,
                eastmoney_quality_csv=args.eastmoney_quality_csv,
                joinquant_availability_csv=args.joinquant_availability_csv,
                external_notice_csv=args.external_notice_csv,
            )
            print(result.alignment_path)
            return 0
        if args.command == "platform-position-attribution":
            print(
                run_position_attribution(
                    args.joinquant_position_csv,
                    args.local_holdings_csv,
                    args.out,
                    args.strategy_id,
                )
            )
            return 0
        if args.command == "platform-transaction-attribution":
            print(
                run_transaction_attribution(
                    args.joinquant_transaction_csv,
                    args.local_trades_csv,
                    args.out,
                    args.strategy_id,
                )
            )
            return 0
        if args.command == "platform-replication-packet":
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
    except (RunBlockedError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
