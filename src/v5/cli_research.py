from __future__ import annotations

import argparse
from pathlib import Path

from v5.fxbaogao_report_runner import collect_fxbaogao_report_search, fetch_fxbaogao_paragraphs


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
