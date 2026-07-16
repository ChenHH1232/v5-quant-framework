from __future__ import annotations

import argparse
from pathlib import Path

from v5.bank_quality_date_alignment_runner import DEFAULT_DATABASE_DIR as DATE_ALIGNMENT_DATABASE_DIR
from v5.bank_quality_date_alignment_runner import align_bank_quality_dates
from v5.benchmark_runner import collect_bank_benchmarks
from v5.dividend_runner import DEFAULT_DATABASE_DIR, collect_bank_dividends, collect_joinquant_cash_dividends
from v5.eastmoney_bank_indicator_runner import DEFAULT_V4_EXTRACTED_VALUES, collect_eastmoney_bank_indicators
from v5.joinquant_availability_runner import build_joinquant_availability_proxy, collect_joinquant_bank_indicator_pubdates
from v5.joinquant_pit_panel_runner import collect_joinquant_basic_pit_panel
from v5.tushare_disclosure_runner import collect_tushare_disclosure_dates
from v5.v4_legacy_bank_quality_runner import DEFAULT_V4_PHASE1_PANEL, collect_v4_legacy_bank_quality
from v5.v4_quality_source_date_audit_runner import audit_v4_quality_source_dates


def register_bank_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    dividend_parser = subparsers.add_parser("collect-dividends")
    dividend_parser.add_argument("panel", type=Path)
    dividend_parser.add_argument("--database-dir", type=Path, default=DEFAULT_DATABASE_DIR)
    dividend_parser.add_argument("--start-date")
    dividend_parser.add_argument("--end-date")
    dividend_parser.add_argument("--output-prefix", default="")
    dividend_parser.add_argument("--source", choices=["akshare", "joinquant"], default="akshare")
    dividend_parser.add_argument("--dividend-tax-rate", type=float, default=0.2)
    dividend_parser.set_defaults(handler=_handle_collect_dividends)

    benchmark_parser = subparsers.add_parser("collect-benchmarks")
    benchmark_parser.add_argument("--database-dir", type=Path, default=DEFAULT_DATABASE_DIR)
    benchmark_parser.add_argument("--start-date", default="2011-01-01")
    benchmark_parser.add_argument("--end-date", default="2026-07-14")
    benchmark_parser.set_defaults(handler=_handle_collect_benchmarks)

    eastmoney_parser = subparsers.add_parser("collect-eastmoney-bank-indicators")
    eastmoney_parser.add_argument("--source-csv", type=Path, default=DEFAULT_V4_EXTRACTED_VALUES)
    eastmoney_parser.add_argument("--out-dir", type=Path, default=DEFAULT_DATABASE_DIR / "processed")
    eastmoney_parser.add_argument("--min-review-status", choices=["reviewed", "needs_check", "unreviewed"], default="needs_check")
    eastmoney_parser.set_defaults(handler=_handle_collect_eastmoney_bank_indicators)

    v4_quality_parser = subparsers.add_parser("collect-v4-legacy-bank-quality")
    v4_quality_parser.add_argument("--source-panel", type=Path, default=DEFAULT_V4_PHASE1_PANEL)
    v4_quality_parser.add_argument("--out-dir", type=Path, default=DEFAULT_DATABASE_DIR / "processed")
    v4_quality_parser.set_defaults(handler=_handle_collect_v4_quality)

    jq_availability_parser = subparsers.add_parser("build-joinquant-availability-proxy")
    jq_availability_parser.add_argument("--v4-quality-csv", type=Path, default=DATE_ALIGNMENT_DATABASE_DIR / "processed" / "v4_legacy_bank_quality.csv")
    jq_availability_parser.add_argument("--out-dir", type=Path, default=DATE_ALIGNMENT_DATABASE_DIR / "processed" / "joinquant_availability")
    jq_availability_parser.set_defaults(handler=_handle_build_jq_availability)

    jq_bank_indicator_parser = subparsers.add_parser("collect-joinquant-bank-indicator-pubdates")
    jq_bank_indicator_parser.add_argument("--v4-quality-csv", type=Path, default=DATE_ALIGNMENT_DATABASE_DIR / "processed" / "v4_legacy_bank_quality.csv")
    jq_bank_indicator_parser.add_argument("--out-dir", type=Path, default=DATE_ALIGNMENT_DATABASE_DIR / "processed" / "joinquant_availability")
    jq_bank_indicator_parser.set_defaults(handler=_handle_collect_jq_bank_pubdates)

    tushare_parser = subparsers.add_parser("collect-tushare-disclosure-dates")
    tushare_parser.add_argument("--quality-csv", type=Path, default=DATE_ALIGNMENT_DATABASE_DIR / "processed" / "v4_legacy_bank_quality.csv")
    tushare_parser.add_argument("--out-dir", type=Path, default=DATE_ALIGNMENT_DATABASE_DIR / "processed" / "tushare_disclosure_dates")
    tushare_parser.add_argument("--credential-file", type=Path)
    tushare_parser.add_argument("--token-env", default="TUSHARE_TOKEN")
    tushare_parser.set_defaults(handler=_handle_collect_tushare_disclosure_dates)

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
    jq_pit_parser.add_argument("--bank-quality-min-review-status", choices=["reviewed", "needs_check", "unreviewed"], default="needs_check")
    jq_pit_parser.set_defaults(handler=_handle_collect_jq_basic_pit_panel)

    source_date_audit_parser = subparsers.add_parser("audit-v4-quality-source-dates")
    source_date_audit_parser.add_argument("quality_csv", type=Path)
    source_date_audit_parser.add_argument("--out", type=Path, default=Path("validation_formal"))
    source_date_audit_parser.add_argument("--strategy-id", default="bank_high_dividend_sustainability_v3")
    source_date_audit_parser.set_defaults(handler=_handle_audit_v4_quality_source_dates)

    date_alignment_parser = subparsers.add_parser("align-bank-quality-dates")
    date_alignment_parser.add_argument("--out-dir", type=Path, default=DATE_ALIGNMENT_DATABASE_DIR / "processed" / "bank_quality_date_alignment")
    date_alignment_parser.add_argument("--v4-quality-csv", type=Path, default=DATE_ALIGNMENT_DATABASE_DIR / "processed" / "v4_legacy_bank_quality.csv")
    date_alignment_parser.add_argument("--eastmoney-quality-csv", type=Path, default=DATE_ALIGNMENT_DATABASE_DIR / "processed" / "eastmoney_bank_quality_manual_csv.csv")
    date_alignment_parser.add_argument("--joinquant-availability-csv", type=Path)
    date_alignment_parser.add_argument("--external-notice-csv", type=Path)
    date_alignment_parser.set_defaults(handler=_handle_align_bank_quality_dates)


def _handle_collect_dividends(args: argparse.Namespace) -> int:
    if args.source == "joinquant":
        result = collect_joinquant_cash_dividends(args.panel, args.database_dir, args.start_date, args.end_date, args.output_prefix, args.dividend_tax_rate)
    else:
        result = collect_bank_dividends(args.panel, args.database_dir, args.start_date, args.end_date, args.output_prefix)
    print(result.processed_path)
    return 0


def _handle_collect_benchmarks(args: argparse.Namespace) -> int:
    print(collect_bank_benchmarks(args.database_dir, args.start_date, args.end_date).processed_path)
    return 0


def _handle_collect_eastmoney_bank_indicators(args: argparse.Namespace) -> int:
    print(collect_eastmoney_bank_indicators(args.source_csv, args.out_dir, args.min_review_status).quality_path)
    return 0


def _handle_collect_v4_quality(args: argparse.Namespace) -> int:
    print(collect_v4_legacy_bank_quality(args.source_panel, args.out_dir).quality_path)
    return 0


def _handle_build_jq_availability(args: argparse.Namespace) -> int:
    print(build_joinquant_availability_proxy(args.v4_quality_csv, args.out_dir).availability_path)
    return 0


def _handle_collect_jq_bank_pubdates(args: argparse.Namespace) -> int:
    print(collect_joinquant_bank_indicator_pubdates(args.v4_quality_csv, args.out_dir).availability_path)
    return 0


def _handle_collect_tushare_disclosure_dates(args: argparse.Namespace) -> int:
    kwargs = {"credential_file": args.credential_file} if args.credential_file else {}
    print(collect_tushare_disclosure_dates(args.quality_csv, args.out_dir, token_env=args.token_env, **kwargs).disclosure_path)
    return 0


def _handle_collect_jq_basic_pit_panel(args: argparse.Namespace) -> int:
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


def _handle_audit_v4_quality_source_dates(args: argparse.Namespace) -> int:
    print(audit_v4_quality_source_dates(args.quality_csv, args.out, args.strategy_id))
    return 0


def _handle_align_bank_quality_dates(args: argparse.Namespace) -> int:
    result = align_bank_quality_dates(
        args.out_dir,
        v4_quality_csv=args.v4_quality_csv,
        eastmoney_quality_csv=args.eastmoney_quality_csv,
        joinquant_availability_csv=args.joinquant_availability_csv,
        external_notice_csv=args.external_notice_csv,
    )
    print(result.alignment_path)
    return 0
