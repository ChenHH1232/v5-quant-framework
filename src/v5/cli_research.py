from __future__ import annotations

import argparse
from pathlib import Path

from v5.fxbaogao_report_runner import (
    collect_fxbaogao_report_search,
    fetch_fxbaogao_paragraphs,
    filter_fxbaogao_report_candidates,
)
from v5.v5c_fxbaogao_seed_retrieval_runner import run_v5c_fxbaogao_seed_retrieval
from v5.v5c_profit_taking_overheat_runner import run_v5c_profit_taking_overheat
from v5.v5c_sleeve_weighting_rigorous_runner import run_v5c_sleeve_weighting_rigorous
from v5.v5c_sleeve_weighting_diagnostic_runner import run_v5c_sleeve_weighting_diagnostic
from v5.v5c_topx_capital_rigorous_runner import run_v5c_topx_capital_rigorous
from v5.v5c_50w_execution_micro_audit_runner import run_v5c_50w_execution_micro_audit
from v5.v5c_50w_execution_optimization_runner import run_v5c_50w_execution_optimization


def register_research_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    search_parser = subparsers.add_parser("research-report-search")
    search_parser.add_argument("keywords", nargs="?")
    search_parser.add_argument("--keywords-file", type=Path)
    search_parser.add_argument("--out", type=Path, default=Path("research_reports/fxbaogao_search"))
    search_parser.add_argument("--org", action="append", default=[])
    search_parser.add_argument("--start-time")
    search_parser.add_argument("--end-time", default="last1year")
    search_parser.set_defaults(handler=_handle_research_report_search)

    paragraph_parser = subparsers.add_parser("research-report-paragraphs")
    paragraph_parser.add_argument("report_id", type=int)
    paragraph_parser.add_argument("--keyword", required=True)
    paragraph_parser.add_argument("--out", type=Path, default=Path("research_reports/fxbaogao_paragraphs"))
    paragraph_parser.set_defaults(handler=_handle_research_report_paragraphs)

    filter_parser = subparsers.add_parser("research-report-filter")
    filter_parser.add_argument("candidate_csvs", nargs="+", type=Path)
    filter_parser.add_argument("--out", type=Path, default=Path("research_reports/fxbaogao_filtered"))
    filter_parser.add_argument("--include-any", action="append", default=[])
    filter_parser.add_argument("--include-all", action="append", default=[])
    filter_parser.add_argument("--exclude", action="append", default=[])
    filter_parser.add_argument("--preferred", action="append", default=[])
    filter_parser.add_argument("--top-k", type=int)
    filter_parser.set_defaults(handler=_handle_research_report_filter)

    seed_parser = subparsers.add_parser("v5c-fxbaogao-seed-retrieval")
    seed_parser.add_argument("--root", type=Path, default=Path("."))
    seed_parser.add_argument("--end-time", default="last1year")
    seed_parser.set_defaults(handler=_handle_v5c_fxbaogao_seed_retrieval)

    overheat_parser = subparsers.add_parser("v5c-profit-taking-overheat")
    overheat_parser.add_argument("--root", type=Path, default=Path("."))
    overheat_parser.set_defaults(handler=_handle_v5c_profit_taking_overheat)

    sleeve_weight_parser = subparsers.add_parser("v5c-sleeve-weighting-diagnostic")
    sleeve_weight_parser.add_argument("--root", type=Path, default=Path("."))
    sleeve_weight_parser.set_defaults(handler=_handle_v5c_sleeve_weighting_diagnostic)

    sleeve_weight_rigorous_parser = subparsers.add_parser("v5c-sleeve-weighting-rigorous")
    sleeve_weight_rigorous_parser.add_argument("--root", type=Path, default=Path("."))
    sleeve_weight_rigorous_parser.set_defaults(handler=_handle_v5c_sleeve_weighting_rigorous)

    topx_capital_parser = subparsers.add_parser("v5c-topx-capital-rigorous")
    topx_capital_parser.add_argument("--root", type=Path, default=Path("."))
    topx_capital_parser.set_defaults(handler=_handle_v5c_topx_capital_rigorous)

    execution_micro_parser = subparsers.add_parser("v5c-50w-execution-micro-audit")
    execution_micro_parser.add_argument("--root", type=Path, default=Path("."))
    execution_micro_parser.set_defaults(handler=_handle_v5c_50w_execution_micro_audit)

    execution_optimization_parser = subparsers.add_parser("v5c-50w-execution-optimization")
    execution_optimization_parser.add_argument("--root", type=Path, default=Path("."))
    execution_optimization_parser.set_defaults(handler=_handle_v5c_50w_execution_optimization)


def _handle_research_report_search(args: argparse.Namespace) -> int:
    keywords = args.keywords
    if args.keywords_file:
        keywords = args.keywords_file.read_text(encoding="utf-8").strip()
    if not keywords:
        raise RuntimeError("research-report-search requires keywords or --keywords-file")
    print(
        collect_fxbaogao_report_search(
            keywords,
            args.out,
            org_names=args.org,
            start_time=args.start_time,
            end_time=args.end_time,
        )
    )
    return 0


def _handle_research_report_paragraphs(args: argparse.Namespace) -> int:
    print(fetch_fxbaogao_paragraphs(args.report_id, args.keyword, args.out))
    return 0


def _handle_research_report_filter(args: argparse.Namespace) -> int:
    print(
        filter_fxbaogao_report_candidates(
            args.candidate_csvs,
            args.out,
            include_any=args.include_any,
            include_all=args.include_all,
            exclude_keywords=args.exclude or None,
            preferred_keywords=args.preferred or None,
            top_k=args.top_k,
        )
    )
    return 0


def _handle_v5c_fxbaogao_seed_retrieval(args: argparse.Namespace) -> int:
    print(run_v5c_fxbaogao_seed_retrieval(args.root, end_time=args.end_time))
    return 0


def _handle_v5c_profit_taking_overheat(args: argparse.Namespace) -> int:
    print(run_v5c_profit_taking_overheat(args.root))
    return 0


def _handle_v5c_sleeve_weighting_diagnostic(args: argparse.Namespace) -> int:
    print(run_v5c_sleeve_weighting_diagnostic(args.root))
    return 0


def _handle_v5c_sleeve_weighting_rigorous(args: argparse.Namespace) -> int:
    print(run_v5c_sleeve_weighting_rigorous(args.root))
    return 0


def _handle_v5c_topx_capital_rigorous(args: argparse.Namespace) -> int:
    print(run_v5c_topx_capital_rigorous(args.root))
    return 0


def _handle_v5c_50w_execution_micro_audit(args: argparse.Namespace) -> int:
    print(run_v5c_50w_execution_micro_audit(args.root))
    return 0


def _handle_v5c_50w_execution_optimization(args: argparse.Namespace) -> int:
    print(run_v5c_50w_execution_optimization(args.root))
    return 0
