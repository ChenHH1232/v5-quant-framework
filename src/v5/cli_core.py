from __future__ import annotations

import argparse
import json
from pathlib import Path

from v5.benchmark_runner import DEFAULT_BENCHMARK_ID, DEFAULT_BENCHMARK_PROCESSED
from v5.config_validation_runner import validate_config_file
from v5.data_runner import collect_panel_from_v4_raw, write_collection_manifest
from v5.daily_backtest import run_daily_joinquant_like_backtest
from v5.dividend_runner import DEFAULT_DIVIDEND_PROCESSED
from v5.engine import run_strategy
from v5.formal_validation_runner import run_formal_validation
from v5.joinquant_capability_probe import run_joinquant_capability_probe
from v5.joinquant_real_data_runner import collect_joinquant_real_data
from v5.local_backtest import DEFAULT_BACKTEST_END, DEFAULT_BACKTEST_START, BacktestOptions, run_local_backtest
from v5.paths import DEFAULT_DATABASE_DIR
from v5.v5_startup_preload_repair_runner import run_v5_startup_preload_repair
from v5.v5_startup_warmup_data_repair_runner import run_v5_startup_warmup_price_repair
from v5.validation_runner import validate_panel
from v5.workspace_contract_audit_runner import DEFAULT_OUT_DIR as DEFAULT_WORKSPACE_CONTRACT_AUDIT_OUT, run_workspace_contract_audit


def register_core_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("spec", type=Path)
    validate_parser.set_defaults(handler=_handle_validate)

    workspace_audit_parser = subparsers.add_parser("audit-workspace-contract")
    workspace_audit_parser.add_argument("--root", type=Path, default=Path("."))
    workspace_audit_parser.add_argument("--out", type=Path, default=DEFAULT_WORKSPACE_CONTRACT_AUDIT_OUT)
    workspace_audit_parser.add_argument("--registry", type=Path, default=Path("docs/governance/status_registry.json"))
    workspace_audit_parser.set_defaults(handler=_handle_audit_workspace_contract)

    startup_parser = subparsers.add_parser("audit-startup-preload")
    startup_parser.add_argument("--root", type=Path, default=Path("."))
    startup_parser.set_defaults(handler=_handle_audit_startup_preload)

    startup_repair_parser = subparsers.add_parser("repair-startup-preload")
    startup_repair_parser.add_argument("--root", type=Path, default=Path("."))
    startup_repair_parser.set_defaults(handler=_handle_audit_startup_preload)

    startup_warmup_parser = subparsers.add_parser("repair-startup-warmup-prices")
    startup_warmup_parser.add_argument("--root", type=Path, default=Path("."))
    startup_warmup_parser.set_defaults(handler=_handle_startup_warmup_prices)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("spec", type=Path)
    run_parser.add_argument("--out", type=Path, default=Path("experiments"))
    run_parser.add_argument("--allow-blockers", action="store_true")
    run_parser.set_defaults(handler=_handle_run)

    collect_parser = subparsers.add_parser("collect-data")
    collect_parser.add_argument("spec", type=Path)
    collect_parser.add_argument("--out", type=Path, default=Path("data/processed"))
    collect_parser.add_argument("--mode", choices=["plan", "v4-raw"], default="plan")
    collect_parser.add_argument("--v4-raw-dir", type=Path, default=Path(r"D:\hh\codex\v4\phase_1_fundamental\raw_downloads\all_banks"))
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
    collect_parser.set_defaults(handler=_handle_collect_data)

    research_validate_parser = subparsers.add_parser("validate-research")
    research_validate_parser.add_argument("spec", type=Path)
    research_validate_parser.add_argument("panel", type=Path)
    research_validate_parser.add_argument("--out", type=Path, default=Path("validation"))
    research_validate_parser.set_defaults(handler=_handle_validate_research)

    formal_validate_parser = subparsers.add_parser("validate-formal")
    formal_validate_parser.add_argument("spec", type=Path)
    formal_validate_parser.add_argument("panel", type=Path)
    formal_validate_parser.add_argument("--out", type=Path, default=Path("validation_formal"))
    formal_validate_parser.add_argument("--experiment-layer", default="research_pit_validation")
    formal_validate_parser.set_defaults(handler=_handle_validate_formal)

    local_backtest_parser = subparsers.add_parser("local-backtest")
    local_backtest_parser.add_argument("spec", type=Path)
    local_backtest_parser.add_argument("panel", type=Path)
    local_backtest_parser.add_argument("--out", type=Path, default=Path("local_backtests"))
    local_backtest_parser.add_argument("--start-date", default=DEFAULT_BACKTEST_START)
    local_backtest_parser.add_argument("--end-date", default=DEFAULT_BACKTEST_END)
    local_backtest_parser.add_argument("--min-coverage-ratio", type=float, default=0.8)
    local_backtest_parser.add_argument("--execution-mode", choices=["ideal_equal_weight", "joinquant_like"], default="ideal_equal_weight")
    local_backtest_parser.add_argument("--initial-cash", type=float, default=2_000_000.0)
    local_backtest_parser.add_argument("--target-exposure", type=float, default=0.995)
    local_backtest_parser.add_argument("--lot-size", type=int, default=100)
    local_backtest_parser.add_argument("--open-commission", type=float, default=0.0003)
    local_backtest_parser.add_argument("--close-commission", type=float, default=0.0003)
    local_backtest_parser.add_argument("--min-commission", type=float, default=5.0)
    local_backtest_parser.add_argument("--save-periods", action="store_true")
    local_backtest_parser.add_argument("--save-holdings", action="store_true")
    local_backtest_parser.set_defaults(handler=_handle_local_backtest)

    daily_backtest_parser = subparsers.add_parser("daily-backtest")
    daily_backtest_parser.add_argument("spec", type=Path)
    daily_backtest_parser.add_argument("panel", type=Path)
    daily_backtest_parser.add_argument("--v4-raw-dir", type=Path, default=Path(r"D:\hh\codex\v4\phase_1_fundamental\raw_downloads\all_banks"))
    daily_backtest_parser.add_argument("--benchmark-csv", type=Path, default=DEFAULT_BENCHMARK_PROCESSED)
    daily_backtest_parser.add_argument("--benchmark-id", default=DEFAULT_BENCHMARK_ID)
    daily_backtest_parser.add_argument("--execution-price-csv", type=Path)
    daily_backtest_parser.add_argument("--dividend-cash-csv", type=Path)
    daily_backtest_parser.add_argument("--eastmoney-quality-csv", type=Path)
    daily_backtest_parser.add_argument("--eastmoney-min-review-status", choices=["reviewed", "needs_check", "unreviewed"], default="needs_check")
    daily_backtest_parser.add_argument("--eastmoney-visibility-mode", choices=["notice_date", "joinquant_source_year"], default="notice_date")
    daily_backtest_parser.add_argument(
        "--experiment-layer",
        choices=["research_pit_validation", "platform_replication", "engineering_smoke_test", "paper_trading"],
        default="engineering_smoke_test",
    )
    daily_backtest_parser.add_argument("--snapshot-out", type=Path)
    daily_backtest_parser.add_argument("--out", type=Path, default=Path("local_daily_backtests"))
    daily_backtest_parser.add_argument("--start-date", default=DEFAULT_BACKTEST_START)
    daily_backtest_parser.add_argument("--end-date", default=DEFAULT_BACKTEST_END)
    daily_backtest_parser.add_argument("--min-coverage-ratio", type=float, default=0.8)
    daily_backtest_parser.add_argument("--initial-cash", type=float, default=2_000_000.0)
    daily_backtest_parser.add_argument("--target-exposure", type=float, default=0.995)
    daily_backtest_parser.add_argument("--defensive-mode", choices=["none", "benchmark_ma"], default="none")
    daily_backtest_parser.add_argument("--defensive-ma-days", type=int, default=252)
    daily_backtest_parser.add_argument("--defensive-risk-exposure", type=float, default=0.5)
    daily_backtest_parser.add_argument("--value-trap-guard-mode", choices=["apply", "disabled"], default="apply")
    daily_backtest_parser.add_argument("--signal-dividend-yield-mode", choices=["panel", "cash_dividend_trailing"], default="panel")
    daily_backtest_parser.set_defaults(handler=_handle_daily_backtest)

    jq_real_parser = subparsers.add_parser("collect-joinquant-real-data")
    jq_real_parser.add_argument("panel", type=Path)
    jq_real_parser.add_argument("--database-dir", type=Path, default=DEFAULT_DATABASE_DIR)
    jq_real_parser.add_argument("--start-date", default=DEFAULT_BACKTEST_START)
    jq_real_parser.add_argument("--end-date", default=DEFAULT_BACKTEST_END)
    jq_real_parser.add_argument("--benchmark", default="512800.XSHG")
    jq_real_parser.add_argument("--benchmark-fq", default="pre", choices=["pre", "post", "none"])
    jq_real_parser.add_argument("--dividend-csv", type=Path)
    jq_real_parser.add_argument("--dividend-tax-rate", type=float, default=0.2)
    jq_real_parser.add_argument("--output-prefix", default="")
    jq_real_parser.set_defaults(handler=_handle_collect_joinquant_real_data)

    jq_probe_parser = subparsers.add_parser("probe-joinquant-capabilities")
    jq_probe_parser.add_argument("--out-dir", type=Path, default=DEFAULT_DATABASE_DIR / "manifests")
    jq_probe_parser.set_defaults(handler=_handle_probe_joinquant)


def _handle_validate(args: argparse.Namespace) -> int:
    result = validate_config_file(args.spec)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["audit"]["passed"] else 2


def _handle_audit_workspace_contract(args: argparse.Namespace) -> int:
    result = run_workspace_contract_audit(root=args.root, out_dir=args.out, registry_path=args.registry)
    print(result.report_path)
    return 0 if result.status == "passed" else 2


def _handle_audit_startup_preload(args: argparse.Namespace) -> int:
    result = run_v5_startup_preload_repair(root=args.root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not result.get("blocker_count") else 2


def _handle_startup_warmup_prices(args: argparse.Namespace) -> int:
    result = run_v5_startup_warmup_price_repair(root=args.root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not result.get("blocker_count") else 2


def _handle_run(args: argparse.Namespace) -> int:
    print(run_strategy(args.spec, args.out, allow_blockers=args.allow_blockers))
    return 0


def _handle_collect_data(args: argparse.Namespace) -> int:
    if args.mode == "plan":
        print(write_collection_manifest(args.spec, args.out))
        return 0
    dividend_csv = args.dividend_csv or (DEFAULT_DIVIDEND_PROCESSED if DEFAULT_DIVIDEND_PROCESSED.exists() else None)
    benchmark_csv = args.benchmark_csv or (DEFAULT_BENCHMARK_PROCESSED if DEFAULT_BENCHMARK_PROCESSED.exists() else None)
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


def _handle_validate_research(args: argparse.Namespace) -> int:
    print(validate_panel(args.spec, args.panel, args.out))
    return 0


def _handle_validate_formal(args: argparse.Namespace) -> int:
    print(run_formal_validation(args.spec, args.panel, args.out, args.experiment_layer))
    return 0


def _handle_local_backtest(args: argparse.Namespace) -> int:
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


def _handle_daily_backtest(args: argparse.Namespace) -> int:
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
            min_coverage_ratio=args.min_coverage_ratio,
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


def _handle_collect_joinquant_real_data(args: argparse.Namespace) -> int:
    result = collect_joinquant_real_data(
        args.panel,
        database_dir=args.database_dir,
        start_date=args.start_date,
        end_date=args.end_date,
        benchmark=args.benchmark,
        benchmark_fq=None if args.benchmark_fq == "none" else args.benchmark_fq,
        dividend_csv=args.dividend_csv,
        dividend_tax_rate=args.dividend_tax_rate,
        output_prefix=args.output_prefix,
    )
    print(result.price_path)
    return 0


def _handle_probe_joinquant(args: argparse.Namespace) -> int:
    print(run_joinquant_capability_probe(args.out_dir))
    return 0
