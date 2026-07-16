from __future__ import annotations

import argparse
import json
from pathlib import Path

from v5.coal_cycle_state_validation_runner import run_coal_cycle_state_validation
from v5.coal_data_audit_runner import (
    audit_coal_business_tags,
    audit_coal_capex_fcf,
    audit_coal_segment_evidence,
    build_coal_capex_policy_panel,
    build_coal_reviewed_business_tag_panel,
    collect_coal_report_disclosure_dates,
    collect_eastmoney_coal_segment_evidence,
    collect_tushare_coal_segment_evidence,
    merge_coal_manual_state,
    merge_coal_segment_evidence_sources,
    merge_coal_state_sources,
    write_coal_business_tag_visible_date_template,
    write_coal_manual_state_template,
    write_coal_official_state_seed,
    write_coal_segment_evidence_template,
    write_nbs_historical_state_template,
)
from v5.coal_external_state_runner import collect_coal_external_state, validate_coal_external_state, write_coal_external_state_template
from v5.coal_pit_panel_runner import collect_coal_pit_panel
from v5.paths import DEFAULT_MANIFEST_DIR, DEFAULT_PROCESSED_DIR


def register_coal_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    coal_pit_parser = subparsers.add_parser("collect-coal-pit-panel")
    coal_pit_parser.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_pit_panel")
    coal_pit_parser.add_argument("--state-panel", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_external_state" / "coal_external_state.csv")
    coal_pit_parser.add_argument("--start-date", default="2015-07-01")
    coal_pit_parser.add_argument("--end-date", default="2026-05-31")
    coal_pit_parser.add_argument("--listing-age-days", type=int, default=180)
    coal_pit_parser.set_defaults(handler=_handle_collect_coal_pit_panel)

    coal_state_parser = subparsers.add_parser("coal-external-state")
    coal_state_subparsers = coal_state_parser.add_subparsers(dest="state_command", required=True)
    coal_state_template = coal_state_subparsers.add_parser("template")
    coal_state_template.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_external_state")
    coal_state_template.set_defaults(handler=_handle_coal_external_state)
    coal_state_collect = coal_state_subparsers.add_parser("collect")
    coal_state_collect.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_external_state")
    coal_state_collect.add_argument("--start-date", default="2013-01-01")
    coal_state_collect.add_argument("--end-date", default="2026-05-31")
    coal_state_collect.set_defaults(handler=_handle_coal_external_state)
    coal_state_validate = coal_state_subparsers.add_parser("validate")
    coal_state_validate.add_argument("csv_path", type=Path)
    coal_state_validate.set_defaults(handler=_handle_coal_external_state)

    coal_cycle_state_parser = subparsers.add_parser("validate-coal-cycle-state")
    coal_cycle_state_parser.add_argument("--panel", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_pit_panel" / "panel.csv")
    coal_cycle_state_parser.add_argument("--out", type=Path, default=Path("validation_formal_v52"))
    coal_cycle_state_parser.add_argument("--metric", default="coking_coal_price_state")
    coal_cycle_state_parser.add_argument("--selection-count", type=int, default=8)
    coal_cycle_state_parser.add_argument("--min-history", type=int, default=8)
    coal_cycle_state_parser.add_argument("--strategy-id", default="coal_high_dividend_cycle_value_v52")
    coal_cycle_state_parser.set_defaults(handler=_handle_validate_coal_cycle_state)

    coal_data_audit_parser = subparsers.add_parser("coal-data-audit")
    audit_subparsers = coal_data_audit_parser.add_subparsers(dest="coal_data_audit_command", required=True)
    _register_coal_data_audit_subcommands(audit_subparsers)


def _register_coal_data_audit_subcommands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    template = subparsers.add_parser("manual-state-template")
    template.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_external_state")
    template.set_defaults(handler=_handle_coal_data_audit)

    nbs_template = subparsers.add_parser("nbs-historical-template")
    nbs_template.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_external_state")
    nbs_template.add_argument("--start-year", type=int, default=2015)
    nbs_template.add_argument("--end-year", type=int, default=2026)
    nbs_template.set_defaults(handler=_handle_coal_data_audit)

    seed = subparsers.add_parser("official-state-seed")
    seed.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_external_state")
    seed.set_defaults(handler=_handle_coal_data_audit)

    merge_sources = subparsers.add_parser("merge-state-sources")
    merge_sources.add_argument("state_csvs", type=Path, nargs="+")
    merge_sources.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_external_state")
    merge_sources.set_defaults(handler=_handle_coal_data_audit)

    merge = subparsers.add_parser("merge-manual-state")
    merge.add_argument("base_state_csv", type=Path)
    merge.add_argument("manual_state_csv", type=Path)
    merge.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_external_state")
    merge.set_defaults(handler=_handle_coal_data_audit)

    tags = subparsers.add_parser("audit-business-tags")
    tags.add_argument("panel", type=Path, nargs="?", default=DEFAULT_PROCESSED_DIR / "coal_pit_panel" / "panel.csv")
    tags.add_argument("--out-dir", type=Path, default=DEFAULT_MANIFEST_DIR / "coal_business_tag_audit")
    tags.set_defaults(handler=_handle_coal_data_audit)

    tag_template = subparsers.add_parser("business-tag-template")
    tag_template.add_argument("panel", type=Path, nargs="?", default=DEFAULT_PROCESSED_DIR / "coal_pit_panel" / "panel.csv")
    tag_template.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_business_tags")
    tag_template.set_defaults(handler=_handle_coal_data_audit)

    disclosures = subparsers.add_parser("collect-report-disclosures")
    disclosures.add_argument("panel", type=Path, nargs="?", default=DEFAULT_PROCESSED_DIR / "coal_pit_panel" / "panel.csv")
    disclosures.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_business_tags")
    disclosures.add_argument("--credential-file", type=Path)
    disclosures.add_argument("--token-env", default="TUSHARE_TOKEN")
    disclosures.set_defaults(handler=_handle_coal_data_audit)

    segment_template = subparsers.add_parser("segment-evidence-template")
    segment_template.add_argument("disclosure_csv", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_business_tags" / "coal_report_disclosure_dates.csv", nargs="?")
    segment_template.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_business_tags")
    segment_template.set_defaults(handler=_handle_coal_data_audit)

    segment_audit = subparsers.add_parser("audit-segment-evidence")
    segment_audit.add_argument("evidence_csv", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_business_tags" / "coal_segment_business_evidence_template.csv", nargs="?")
    segment_audit.add_argument("--out-dir", type=Path, default=DEFAULT_MANIFEST_DIR / "coal_segment_evidence_audit")
    segment_audit.set_defaults(handler=_handle_coal_data_audit)

    eastmoney = subparsers.add_parser("collect-eastmoney-segments")
    eastmoney.add_argument("panel", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_pit_panel" / "panel.csv", nargs="?")
    eastmoney.add_argument("disclosure_csv", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_business_tags" / "coal_report_disclosure_dates.csv", nargs="?")
    eastmoney.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_business_tags")
    eastmoney.add_argument("--request-timeout-seconds", type=float, default=15.0)
    eastmoney.add_argument("--sleep-seconds", type=float, default=0.25)
    eastmoney.add_argument("--limit", type=int)
    eastmoney.set_defaults(handler=_handle_coal_data_audit)

    tushare = subparsers.add_parser("collect-tushare-segments")
    tushare.add_argument("panel", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_pit_panel" / "panel.csv", nargs="?")
    tushare.add_argument("disclosure_csv", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_business_tags" / "coal_report_disclosure_dates.csv", nargs="?")
    tushare.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_business_tags")
    tushare.add_argument("--codes", nargs="*", default=None)
    tushare.add_argument("--sleep-seconds", type=float, default=0.25)
    tushare.set_defaults(handler=_handle_coal_data_audit)

    merge_segments = subparsers.add_parser("merge-segment-evidence")
    merge_segments.add_argument("eastmoney_csv", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_business_tags" / "coal_segment_business_evidence_eastmoney.csv", nargs="?")
    merge_segments.add_argument("fallback_csv", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_business_tags" / "coal_segment_business_evidence_tushare.csv", nargs="?")
    merge_segments.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_business_tags")
    merge_segments.set_defaults(handler=_handle_coal_data_audit)

    reviewed_panel = subparsers.add_parser("build-reviewed-business-tag-panel")
    reviewed_panel.add_argument("panel", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_pit_panel" / "panel.csv", nargs="?")
    reviewed_panel.add_argument("evidence_csv", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_business_tags" / "coal_segment_business_evidence_reviewed.csv", nargs="?")
    reviewed_panel.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_business_tags")
    reviewed_panel.set_defaults(handler=_handle_coal_data_audit)

    capex = subparsers.add_parser("audit-capex-fcf")
    capex.add_argument("panel", type=Path, nargs="?", default=DEFAULT_PROCESSED_DIR / "coal_pit_panel" / "panel.csv")
    capex.add_argument("--out-dir", type=Path, default=DEFAULT_MANIFEST_DIR / "coal_capex_fcf_audit")
    capex.set_defaults(handler=_handle_coal_data_audit)

    capex_policy = subparsers.add_parser("capex-policy-panel")
    capex_policy.add_argument("panel", type=Path, nargs="?", default=DEFAULT_PROCESSED_DIR / "coal_pit_panel" / "panel.csv")
    capex_policy.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_pit_panel_capex_policy")
    capex_policy.set_defaults(handler=_handle_coal_data_audit)


def _handle_collect_coal_pit_panel(args: argparse.Namespace) -> int:
    result = collect_coal_pit_panel(out_dir=args.out_dir, state_panel=args.state_panel, start_date=args.start_date, end_date=args.end_date, listing_age_days=args.listing_age_days)
    print(result.panel_path)
    return 0


def _handle_coal_external_state(args: argparse.Namespace) -> int:
    if args.state_command == "template":
        print(write_coal_external_state_template(args.out_dir))
    elif args.state_command == "collect":
        print(collect_coal_external_state(args.out_dir, args.start_date, args.end_date))
    else:
        print(json.dumps(validate_coal_external_state(args.csv_path), ensure_ascii=False, indent=2))
    return 0


def _handle_validate_coal_cycle_state(args: argparse.Namespace) -> int:
    print(run_coal_cycle_state_validation(args.panel, args.out, args.metric, args.selection_count, args.min_history, args.strategy_id))
    return 0


def _handle_coal_data_audit(args: argparse.Namespace) -> int:
    command = args.coal_data_audit_command
    if command == "manual-state-template":
        print(write_coal_manual_state_template(args.out_dir))
    elif command == "nbs-historical-template":
        print(write_nbs_historical_state_template(args.out_dir, args.start_year, args.end_year))
    elif command == "official-state-seed":
        print(write_coal_official_state_seed(args.out_dir))
    elif command == "merge-state-sources":
        print(merge_coal_state_sources(args.out_dir, *args.state_csvs))
    elif command == "merge-manual-state":
        print(merge_coal_manual_state(args.base_state_csv, args.manual_state_csv, args.out_dir))
    elif command == "audit-business-tags":
        print(audit_coal_business_tags(args.panel, args.out_dir))
    elif command == "business-tag-template":
        print(write_coal_business_tag_visible_date_template(args.panel, args.out_dir))
    elif command == "collect-report-disclosures":
        print(collect_coal_report_disclosure_dates(args.panel, args.out_dir, args.credential_file, args.token_env))
    elif command == "segment-evidence-template":
        print(write_coal_segment_evidence_template(args.disclosure_csv, args.out_dir))
    elif command == "audit-segment-evidence":
        print(audit_coal_segment_evidence(args.evidence_csv, args.out_dir))
    elif command == "collect-eastmoney-segments":
        print(collect_eastmoney_coal_segment_evidence(args.panel, args.disclosure_csv, args.out_dir, args.request_timeout_seconds, args.sleep_seconds, args.limit))
    elif command == "collect-tushare-segments":
        print(collect_tushare_coal_segment_evidence(args.panel, args.disclosure_csv, args.out_dir, args.codes, args.sleep_seconds))
    elif command == "merge-segment-evidence":
        print(merge_coal_segment_evidence_sources(args.eastmoney_csv, args.fallback_csv, args.out_dir))
    elif command == "build-reviewed-business-tag-panel":
        print(build_coal_reviewed_business_tag_panel(args.panel, args.evidence_csv, args.out_dir))
    elif command == "audit-capex-fcf":
        print(audit_coal_capex_fcf(args.panel, args.out_dir))
    elif command == "capex-policy-panel":
        print(build_coal_capex_policy_panel(args.panel, args.out_dir))
    else:
        return 1
    return 0
