from __future__ import annotations

import argparse
from pathlib import Path

from v5.dividend_low_vol_fcf_screener_runner import (
    DEFAULT_CONFIG as DEFAULT_V56_SCREEN_CONFIG,
    DEFAULT_OUT_DIR as DEFAULT_V56_SCREEN_OUT,
    DEFAULT_STATUS_REGISTRY as DEFAULT_V56_STATUS_REGISTRY,
    run_dividend_low_vol_fcf_batch_screening,
)
from v5.sector_replication_roadmap_runner import (
    DEFAULT_CONFIG as DEFAULT_V58_REPLICATION_ROADMAP_CONFIG,
    DEFAULT_OUT_DIR as DEFAULT_V58_REPLICATION_ROADMAP_OUT,
    build_sector_replication_roadmap,
)
from v5.basket_constructor_runner import (
    DEFAULT_CONFIG as DEFAULT_V56_BASKET_CONFIG,
    DEFAULT_OUT_DIR as DEFAULT_V56_BASKET_OUT,
    construct_dividend_low_vol_fcf_basket,
)
from v5.basket_ablation_runner import (
    DEFAULT_CONFIG as DEFAULT_V56_BASKET_ABLATION_CONFIG,
    DEFAULT_OUT_DIR as DEFAULT_V56_BASKET_ABLATION_OUT,
    run_basket_ablation,
)
from v5.basket_daily_backtest_runner import (
    DEFAULT_CONFIG as DEFAULT_V56_BASKET_DAILY_CONFIG,
    DEFAULT_OUT_DIR as DEFAULT_V56_BASKET_DAILY_OUT,
    DEFAULT_SIGNALS as DEFAULT_V56_BASKET_SIGNALS,
    run_basket_daily_backtest,
)
from v5.basket_failure_attribution_runner import (
    DEFAULT_CONFIG as DEFAULT_V56_BASKET_ATTRIBUTION_CONFIG,
    DEFAULT_DAILY_DIR as DEFAULT_V56_BASKET_ATTRIBUTION_DAILY_DIR,
    DEFAULT_OUT_DIR as DEFAULT_V56_BASKET_ATTRIBUTION_OUT,
    DEFAULT_SIGNALS as DEFAULT_V56_BASKET_ATTRIBUTION_SIGNALS,
    run_basket_failure_attribution,
)
from v5.basket_formal_validation_runner import (
    DEFAULT_CONFIG as DEFAULT_V56_BASKET_FORMAL_CONFIG,
    DEFAULT_DAILY_RETURNS as DEFAULT_V56_BASKET_FORMAL_DAILY_RETURNS,
    DEFAULT_OUT_DIR as DEFAULT_V56_BASKET_FORMAL_OUT,
    DEFAULT_SIGNALS as DEFAULT_V56_BASKET_FORMAL_SIGNALS,
    run_basket_formal_validation,
)
from v5.basket_joinquant_export_runner import (
    DEFAULT_OUT as DEFAULT_V56_BASKET_JQ_OUT,
    DEFAULT_SIGNALS as DEFAULT_V56_BASKET_JQ_SIGNALS,
    export_basket_frozen_signals_to_joinquant,
)
from v5.low_volatility_factor_runner import DEFAULT_OUT_DIR as DEFAULT_LOW_VOL_OUT_DIR, add_low_volatility_factors
from v5.similar_sector_pit_panel_runner import DEFAULT_OUT_ROOT, SECTOR_CONFIGS, collect_similar_sector_pit_panel
from v5.gas_water_operating_evidence_runner import (
    DEFAULT_OUT_DIR as DEFAULT_GAS_WATER_EVIDENCE_OUT,
    build_gas_water_business_purity_panel,
    collect_eastmoney_gas_water_segment_evidence,
    collect_gas_water_report_disclosure_dates,
)
from v5.gas_water_financial_evidence_runner import (
    DEFAULT_OUT_DIR as DEFAULT_GAS_WATER_FINANCIAL_OUT,
    enrich_gas_water_financial_evidence,
)
from v5.airport_transport_operating_evidence_runner import (
    DEFAULT_OUT_DIR as DEFAULT_AIRPORT_OPERATING_EVIDENCE_OUT,
    build_airport_business_purity_panel,
    cache_airport_operating_announcement_contents,
    collect_airport_report_disclosure_dates,
    collect_eastmoney_airport_operating_announcements,
    collect_eastmoney_airport_segment_evidence,
    extract_airport_operating_state_values,
)
from v5.oil_gas_state_runner import (
    DEFAULT_OUT_DIR as DEFAULT_OIL_GAS_STATE_OUT,
    DEFAULT_PANEL_OUT_DIR as DEFAULT_OIL_GAS_PANEL_OUT,
    build_oil_gas_research_panel,
    collect_oil_gas_external_state,
    validate_oil_gas_external_state,
)
from v5.oil_gas_cycle_state_validation_runner import (
    DEFAULT_OUT_DIR as DEFAULT_OIL_GAS_CYCLE_STATE_OUT,
    DEFAULT_PANEL as DEFAULT_OIL_GAS_CYCLE_STATE_PANEL,
    run_oil_gas_cycle_state_validation,
)
from v5.oil_gas_state_conditioned_panel_runner import (
    DEFAULT_OUT_DIR as DEFAULT_OIL_GAS_STATE_CONDITIONED_OUT,
    DEFAULT_PANEL as DEFAULT_OIL_GAS_STATE_CONDITIONED_PANEL,
    build_oil_gas_state_conditioned_panel,
)
from v5.oil_gas_source_gate_runner import (
    DEFAULT_OUT_DIR as DEFAULT_OIL_GAS_SOURCE_GATE_OUT,
    DEFAULT_PANEL as DEFAULT_OIL_GAS_SOURCE_GATE_PANEL,
    audit_oil_gas_source_gate,
    merge_oil_gas_state_sources,
    write_oil_gas_official_source_register,
    write_oil_gas_official_state_import_template,
)


def register_sector_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("collect-similar-sector-pit-panel")
    parser.add_argument("sector", choices=sorted(SECTOR_CONFIGS))
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    parser.add_argument("--start-date", default="2021-05-01")
    parser.add_argument("--end-date", default="2026-05-31")
    parser.add_argument("--listing-age-days", type=int, default=180)
    parser.set_defaults(handler=_handle_collect_similar_sector_pit_panel)

    gas_water_disclosure_parser = subparsers.add_parser("collect-gas-water-report-disclosure-dates")
    gas_water_disclosure_parser.add_argument("panel", type=Path)
    gas_water_disclosure_parser.add_argument("--out-dir", type=Path, default=DEFAULT_GAS_WATER_EVIDENCE_OUT)
    gas_water_disclosure_parser.set_defaults(handler=_handle_collect_gas_water_report_disclosure_dates)

    gas_water_eastmoney_parser = subparsers.add_parser("collect-eastmoney-gas-water-segments")
    gas_water_eastmoney_parser.add_argument("panel", type=Path)
    gas_water_eastmoney_parser.add_argument("disclosure_csv", type=Path)
    gas_water_eastmoney_parser.add_argument("--out-dir", type=Path, default=DEFAULT_GAS_WATER_EVIDENCE_OUT)
    gas_water_eastmoney_parser.add_argument("--request-timeout-seconds", type=float, default=15.0)
    gas_water_eastmoney_parser.add_argument("--sleep-seconds", type=float, default=0.25)
    gas_water_eastmoney_parser.add_argument("--limit", type=int)
    gas_water_eastmoney_parser.set_defaults(handler=_handle_collect_eastmoney_gas_water_segments)

    gas_water_purity_parser = subparsers.add_parser("build-gas-water-business-purity-panel")
    gas_water_purity_parser.add_argument("panel", type=Path)
    gas_water_purity_parser.add_argument("evidence_csv", type=Path)
    gas_water_purity_parser.add_argument("--out-dir", type=Path, default=DEFAULT_GAS_WATER_EVIDENCE_OUT / "business_purity_panel")
    gas_water_purity_parser.add_argument("--min-operator-share", type=float, default=0.5)
    gas_water_purity_parser.set_defaults(handler=_handle_build_gas_water_business_purity_panel)

    gas_water_financial_parser = subparsers.add_parser("enrich-gas-water-financial-evidence")
    gas_water_financial_parser.add_argument("panel", type=Path)
    gas_water_financial_parser.add_argument("--out-dir", type=Path, default=DEFAULT_GAS_WATER_FINANCIAL_OUT)
    gas_water_financial_parser.set_defaults(handler=_handle_enrich_gas_water_financial_evidence)

    airport_disclosure_parser = subparsers.add_parser("collect-airport-report-disclosure-dates")
    airport_disclosure_parser.add_argument("panel", type=Path)
    airport_disclosure_parser.add_argument("--out-dir", type=Path, default=DEFAULT_AIRPORT_OPERATING_EVIDENCE_OUT)
    airport_disclosure_parser.set_defaults(handler=_handle_collect_airport_report_disclosure_dates)

    airport_eastmoney_parser = subparsers.add_parser("collect-eastmoney-airport-segments")
    airport_eastmoney_parser.add_argument("panel", type=Path)
    airport_eastmoney_parser.add_argument("disclosure_csv", type=Path)
    airport_eastmoney_parser.add_argument("--out-dir", type=Path, default=DEFAULT_AIRPORT_OPERATING_EVIDENCE_OUT)
    airport_eastmoney_parser.add_argument("--request-timeout-seconds", type=float, default=15.0)
    airport_eastmoney_parser.add_argument("--sleep-seconds", type=float, default=0.25)
    airport_eastmoney_parser.add_argument("--limit", type=int)
    airport_eastmoney_parser.set_defaults(handler=_handle_collect_eastmoney_airport_segments)

    airport_purity_parser = subparsers.add_parser("build-airport-business-purity-panel")
    airport_purity_parser.add_argument("panel", type=Path)
    airport_purity_parser.add_argument("evidence_csv", type=Path)
    airport_purity_parser.add_argument("--out-dir", type=Path, default=DEFAULT_AIRPORT_OPERATING_EVIDENCE_OUT / "business_purity_panel")
    airport_purity_parser.add_argument("--min-operator-share", type=float, default=0.5)
    airport_purity_parser.set_defaults(handler=_handle_build_airport_business_purity_panel)

    airport_ann_parser = subparsers.add_parser("collect-eastmoney-airport-operating-announcements")
    airport_ann_parser.add_argument("panel", type=Path)
    airport_ann_parser.add_argument("--out-dir", type=Path, default=DEFAULT_AIRPORT_OPERATING_EVIDENCE_OUT)
    airport_ann_parser.add_argument("--begin-date", default="2021-01-01")
    airport_ann_parser.add_argument("--end-date", default="2026-05-31")
    airport_ann_parser.add_argument("--request-timeout-seconds", type=float, default=15.0)
    airport_ann_parser.add_argument("--sleep-seconds", type=float, default=0.25)
    airport_ann_parser.add_argument("--limit", type=int)
    airport_ann_parser.set_defaults(handler=_handle_collect_eastmoney_airport_operating_announcements)

    airport_values_parser = subparsers.add_parser("extract-airport-operating-state-values")
    airport_values_parser.add_argument("announcement_index", type=Path)
    airport_values_parser.add_argument("--out-dir", type=Path, default=DEFAULT_AIRPORT_OPERATING_EVIDENCE_OUT / "operating_state_values")
    airport_values_parser.add_argument("--request-timeout-seconds", type=float, default=12.0)
    airport_values_parser.add_argument("--sleep-seconds", type=float, default=0.15)
    airport_values_parser.add_argument("--max-workers", type=int, default=1)
    airport_values_parser.add_argument("--content-cache-dir", type=Path)
    airport_values_parser.add_argument("--cache-only", action="store_true")
    airport_values_parser.add_argument("--limit", type=int)
    airport_values_parser.set_defaults(handler=_handle_extract_airport_operating_state_values)

    airport_content_cache_parser = subparsers.add_parser("cache-airport-operating-announcement-contents")
    airport_content_cache_parser.add_argument("announcement_index", type=Path)
    airport_content_cache_parser.add_argument("--out-dir", type=Path, default=DEFAULT_AIRPORT_OPERATING_EVIDENCE_OUT / "operating_content_cache")
    airport_content_cache_parser.add_argument("--request-timeout-seconds", type=float, default=12.0)
    airport_content_cache_parser.add_argument("--sleep-seconds", type=float, default=0.15)
    airport_content_cache_parser.add_argument("--max-workers", type=int, default=1)
    airport_content_cache_parser.add_argument("--limit", type=int)
    airport_content_cache_parser.add_argument("--code")
    airport_content_cache_parser.add_argument("--start-month")
    airport_content_cache_parser.add_argument("--end-month")
    airport_content_cache_parser.add_argument("--retry-failed", action="store_true")
    airport_content_cache_parser.set_defaults(handler=_handle_cache_airport_operating_announcement_contents)

    oil_gas_state_parser = subparsers.add_parser("collect-oil-gas-external-state")
    oil_gas_state_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OIL_GAS_STATE_OUT)
    oil_gas_state_parser.add_argument("--start-date", default="2021-01-01")
    oil_gas_state_parser.add_argument("--end-date", default="2026-05-31")
    oil_gas_state_parser.set_defaults(handler=_handle_collect_oil_gas_external_state)

    oil_gas_state_validate_parser = subparsers.add_parser("validate-oil-gas-external-state")
    oil_gas_state_validate_parser.add_argument("csv_path", type=Path)
    oil_gas_state_validate_parser.set_defaults(handler=_handle_validate_oil_gas_external_state)

    oil_gas_panel_parser = subparsers.add_parser("build-oil-gas-research-panel")
    oil_gas_panel_parser.add_argument("panel", type=Path)
    oil_gas_panel_parser.add_argument("external_state", type=Path)
    oil_gas_panel_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OIL_GAS_PANEL_OUT)
    oil_gas_panel_parser.add_argument("--strategy-id", default="oil_gas_ocf_dividend_cycle_probe_v58a")
    oil_gas_panel_parser.set_defaults(handler=_handle_build_oil_gas_research_panel)

    oil_gas_cycle_parser = subparsers.add_parser("validate-oil-gas-cycle-state")
    oil_gas_cycle_parser.add_argument("--panel", type=Path, default=DEFAULT_OIL_GAS_CYCLE_STATE_PANEL)
    oil_gas_cycle_parser.add_argument("--out", type=Path, default=DEFAULT_OIL_GAS_CYCLE_STATE_OUT)
    oil_gas_cycle_parser.add_argument("--metric", default="crude_oil_price_state")
    oil_gas_cycle_parser.add_argument("--selection-count", type=int, default=8)
    oil_gas_cycle_parser.add_argument("--min-history", type=int, default=4)
    oil_gas_cycle_parser.add_argument("--strategy-id", default="oil_gas_ocf_state_diagnostic_v58c")
    oil_gas_cycle_parser.set_defaults(handler=_handle_validate_oil_gas_cycle_state)

    oil_gas_conditioned_panel_parser = subparsers.add_parser("build-oil-gas-state-conditioned-panel")
    oil_gas_conditioned_panel_parser.add_argument("--panel", type=Path, default=DEFAULT_OIL_GAS_STATE_CONDITIONED_PANEL)
    oil_gas_conditioned_panel_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OIL_GAS_STATE_CONDITIONED_OUT)
    oil_gas_conditioned_panel_parser.add_argument("--strategy-id", default="oil_gas_state_conditioned_ocf_v58d")
    oil_gas_conditioned_panel_parser.add_argument("--min-history", type=int, default=4)
    oil_gas_conditioned_panel_parser.set_defaults(handler=_handle_build_oil_gas_state_conditioned_panel)

    oil_gas_source_register_parser = subparsers.add_parser("oil-gas-source-register")
    oil_gas_source_register_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OIL_GAS_SOURCE_GATE_OUT)
    oil_gas_source_register_parser.set_defaults(handler=_handle_oil_gas_source_register)

    oil_gas_state_template_parser = subparsers.add_parser("oil-gas-official-state-template")
    oil_gas_state_template_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OIL_GAS_SOURCE_GATE_OUT)
    oil_gas_state_template_parser.add_argument("--start-year", type=int, default=2021)
    oil_gas_state_template_parser.add_argument("--end-year", type=int, default=2026)
    oil_gas_state_template_parser.set_defaults(handler=_handle_oil_gas_official_state_template)

    oil_gas_source_audit_parser = subparsers.add_parser("audit-oil-gas-source-gate")
    oil_gas_source_audit_parser.add_argument("state_csv", type=Path)
    oil_gas_source_audit_parser.add_argument("--panel", type=Path, default=DEFAULT_OIL_GAS_SOURCE_GATE_PANEL)
    oil_gas_source_audit_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OIL_GAS_SOURCE_GATE_OUT)
    oil_gas_source_audit_parser.set_defaults(handler=_handle_audit_oil_gas_source_gate)

    oil_gas_source_merge_parser = subparsers.add_parser("merge-oil-gas-state-sources")
    oil_gas_source_merge_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OIL_GAS_SOURCE_GATE_OUT)
    oil_gas_source_merge_parser.add_argument("--panel", type=Path, default=DEFAULT_OIL_GAS_SOURCE_GATE_PANEL)
    oil_gas_source_merge_parser.add_argument("state_csvs", nargs="+", type=Path)
    oil_gas_source_merge_parser.set_defaults(handler=_handle_merge_oil_gas_state_sources)

    screen_parser = subparsers.add_parser("screen-dividend-low-vol-fcf-sectors")
    screen_parser.add_argument("--config", type=Path, default=DEFAULT_V56_SCREEN_CONFIG)
    screen_parser.add_argument("--status-registry", type=Path, default=DEFAULT_V56_STATUS_REGISTRY)
    screen_parser.add_argument("--out", type=Path, default=DEFAULT_V56_SCREEN_OUT)
    screen_parser.set_defaults(handler=_handle_screen_dividend_low_vol_fcf_sectors)

    roadmap_parser = subparsers.add_parser("build-sector-replication-roadmap")
    roadmap_parser.add_argument("--config", type=Path, default=DEFAULT_V58_REPLICATION_ROADMAP_CONFIG)
    roadmap_parser.add_argument("--out", type=Path, default=DEFAULT_V58_REPLICATION_ROADMAP_OUT)
    roadmap_parser.set_defaults(handler=_handle_build_sector_replication_roadmap)

    low_vol_parser = subparsers.add_parser("add-low-volatility-factors")
    low_vol_parser.add_argument("panel", type=Path)
    low_vol_parser.add_argument("price_csv", type=Path)
    low_vol_parser.add_argument("--benchmark-csv", type=Path)
    low_vol_parser.add_argument("--strategy-id")
    low_vol_parser.add_argument("--out", type=Path, default=DEFAULT_LOW_VOL_OUT_DIR)
    low_vol_parser.add_argument("--min-observations", type=int, default=40)
    low_vol_parser.set_defaults(handler=_handle_add_low_volatility_factors)

    basket_parser = subparsers.add_parser("construct-dividend-low-vol-fcf-basket")
    basket_parser.add_argument("--config", type=Path, default=DEFAULT_V56_BASKET_CONFIG)
    basket_parser.add_argument("--out", type=Path, default=DEFAULT_V56_BASKET_OUT)
    basket_parser.set_defaults(handler=_handle_construct_dividend_low_vol_fcf_basket)

    basket_daily_parser = subparsers.add_parser("daily-backtest-dividend-low-vol-fcf-basket")
    basket_daily_parser.add_argument("--config", type=Path, default=DEFAULT_V56_BASKET_DAILY_CONFIG)
    basket_daily_parser.add_argument("--signals", type=Path, default=DEFAULT_V56_BASKET_SIGNALS)
    basket_daily_parser.add_argument("--out", type=Path, default=DEFAULT_V56_BASKET_DAILY_OUT)
    basket_daily_parser.add_argument("--initial-cash", type=float, default=2_000_000.0)
    basket_daily_parser.add_argument("--target-exposure", type=float, default=0.995)
    basket_daily_parser.add_argument("--lot-size", type=int, default=100)
    basket_daily_parser.add_argument("--open-commission", type=float, default=0.0003)
    basket_daily_parser.add_argument("--close-commission", type=float, default=0.0003)
    basket_daily_parser.add_argument("--min-commission", type=float, default=5.0)
    basket_daily_parser.set_defaults(handler=_handle_daily_backtest_dividend_low_vol_fcf_basket)

    basket_formal_parser = subparsers.add_parser("validate-dividend-low-vol-fcf-basket")
    basket_formal_parser.add_argument("--config", type=Path, default=DEFAULT_V56_BASKET_FORMAL_CONFIG)
    basket_formal_parser.add_argument("--signals", type=Path, default=DEFAULT_V56_BASKET_FORMAL_SIGNALS)
    basket_formal_parser.add_argument("--daily-returns-csv", type=Path, default=DEFAULT_V56_BASKET_FORMAL_DAILY_RETURNS)
    basket_formal_parser.add_argument("--out", type=Path, default=DEFAULT_V56_BASKET_FORMAL_OUT)
    basket_formal_parser.set_defaults(handler=_handle_validate_dividend_low_vol_fcf_basket)

    basket_ablation_parser = subparsers.add_parser("ablate-dividend-low-vol-fcf-basket")
    basket_ablation_parser.add_argument("--config", type=Path, default=DEFAULT_V56_BASKET_ABLATION_CONFIG)
    basket_ablation_parser.add_argument("--out", type=Path, default=DEFAULT_V56_BASKET_ABLATION_OUT)
    basket_ablation_parser.set_defaults(handler=_handle_ablate_dividend_low_vol_fcf_basket)

    basket_attribution_parser = subparsers.add_parser("attribute-dividend-low-vol-fcf-basket-failures")
    basket_attribution_parser.add_argument("--config", type=Path, default=DEFAULT_V56_BASKET_ATTRIBUTION_CONFIG)
    basket_attribution_parser.add_argument("--daily-dir", type=Path, default=DEFAULT_V56_BASKET_ATTRIBUTION_DAILY_DIR)
    basket_attribution_parser.add_argument("--signals", type=Path, default=DEFAULT_V56_BASKET_ATTRIBUTION_SIGNALS)
    basket_attribution_parser.add_argument("--out", type=Path, default=DEFAULT_V56_BASKET_ATTRIBUTION_OUT)
    basket_attribution_parser.set_defaults(handler=_handle_attribute_dividend_low_vol_fcf_basket_failures)

    basket_jq_parser = subparsers.add_parser("export-basket-frozen-signals-joinquant")
    basket_jq_parser.add_argument("--signals", type=Path, default=DEFAULT_V56_BASKET_JQ_SIGNALS)
    basket_jq_parser.add_argument("--out-file", type=Path, default=DEFAULT_V56_BASKET_JQ_OUT)
    basket_jq_parser.add_argument("--strategy-id", default="v56_dividend_low_vol_fcf_shadow_basket")
    basket_jq_parser.add_argument("--script-version")
    basket_jq_parser.add_argument("--benchmark", default="000300.XSHG")
    basket_jq_parser.add_argument("--target-exposure", type=float, default=0.995)
    basket_jq_parser.add_argument("--lot-size", type=int, default=100)
    basket_jq_parser.set_defaults(handler=_handle_export_basket_frozen_signals_joinquant)


def _handle_collect_similar_sector_pit_panel(args: argparse.Namespace) -> int:
    print(
        collect_similar_sector_pit_panel(
            args.sector,
            out_root=args.out_root,
            start_date=args.start_date,
            end_date=args.end_date,
            listing_age_days=args.listing_age_days,
        )
    )
    return 0


def _handle_collect_gas_water_report_disclosure_dates(args: argparse.Namespace) -> int:
    print(collect_gas_water_report_disclosure_dates(args.panel, args.out_dir))
    return 0


def _handle_collect_eastmoney_gas_water_segments(args: argparse.Namespace) -> int:
    print(
        collect_eastmoney_gas_water_segment_evidence(
            args.panel,
            args.disclosure_csv,
            args.out_dir,
            request_timeout_seconds=args.request_timeout_seconds,
            sleep_seconds=args.sleep_seconds,
            limit=args.limit,
        )
    )
    return 0


def _handle_build_gas_water_business_purity_panel(args: argparse.Namespace) -> int:
    print(
        build_gas_water_business_purity_panel(
            args.panel,
            args.evidence_csv,
            args.out_dir,
            min_operator_share=args.min_operator_share,
        )
    )
    return 0


def _handle_enrich_gas_water_financial_evidence(args: argparse.Namespace) -> int:
    print(enrich_gas_water_financial_evidence(args.panel, out_dir=args.out_dir))
    return 0


def _handle_collect_airport_report_disclosure_dates(args: argparse.Namespace) -> int:
    print(collect_airport_report_disclosure_dates(args.panel, args.out_dir))
    return 0


def _handle_collect_eastmoney_airport_segments(args: argparse.Namespace) -> int:
    print(
        collect_eastmoney_airport_segment_evidence(
            args.panel,
            args.disclosure_csv,
            args.out_dir,
            request_timeout_seconds=args.request_timeout_seconds,
            sleep_seconds=args.sleep_seconds,
            limit=args.limit,
        )
    )
    return 0


def _handle_build_airport_business_purity_panel(args: argparse.Namespace) -> int:
    print(build_airport_business_purity_panel(args.panel, args.evidence_csv, args.out_dir, min_operator_share=args.min_operator_share))
    return 0


def _handle_collect_eastmoney_airport_operating_announcements(args: argparse.Namespace) -> int:
    print(
        collect_eastmoney_airport_operating_announcements(
            args.panel,
            args.out_dir,
            begin_date=args.begin_date,
            end_date=args.end_date,
            request_timeout_seconds=args.request_timeout_seconds,
            sleep_seconds=args.sleep_seconds,
            max_workers=args.max_workers,
            content_cache_dir=args.content_cache_dir,
            cache_only=args.cache_only,
            limit=args.limit,
        )
    )
    return 0


def _handle_cache_airport_operating_announcement_contents(args: argparse.Namespace) -> int:
    print(
        cache_airport_operating_announcement_contents(
            args.announcement_index,
            args.out_dir,
            request_timeout_seconds=args.request_timeout_seconds,
            sleep_seconds=args.sleep_seconds,
            max_workers=args.max_workers,
            limit=args.limit,
            code=args.code,
            start_month=args.start_month,
            end_month=args.end_month,
            retry_failed=args.retry_failed,
        )
    )
    return 0


def _handle_extract_airport_operating_state_values(args: argparse.Namespace) -> int:
    print(
        extract_airport_operating_state_values(
            args.announcement_index,
            args.out_dir,
            request_timeout_seconds=args.request_timeout_seconds,
            sleep_seconds=args.sleep_seconds,
            limit=args.limit,
        )
    )
    return 0


def _handle_collect_oil_gas_external_state(args: argparse.Namespace) -> int:
    print(collect_oil_gas_external_state(args.out_dir, start_date=args.start_date, end_date=args.end_date))
    return 0


def _handle_validate_oil_gas_external_state(args: argparse.Namespace) -> int:
    print(validate_oil_gas_external_state(args.csv_path))
    return 0


def _handle_build_oil_gas_research_panel(args: argparse.Namespace) -> int:
    print(build_oil_gas_research_panel(args.panel, args.external_state, args.out_dir, strategy_id=args.strategy_id))
    return 0


def _handle_validate_oil_gas_cycle_state(args: argparse.Namespace) -> int:
    print(run_oil_gas_cycle_state_validation(args.panel, args.out, args.metric, args.selection_count, args.min_history, args.strategy_id))
    return 0


def _handle_build_oil_gas_state_conditioned_panel(args: argparse.Namespace) -> int:
    print(build_oil_gas_state_conditioned_panel(args.panel, args.out_dir, args.strategy_id, args.min_history))
    return 0


def _handle_oil_gas_source_register(args: argparse.Namespace) -> int:
    print(write_oil_gas_official_source_register(args.out_dir))
    return 0


def _handle_oil_gas_official_state_template(args: argparse.Namespace) -> int:
    print(write_oil_gas_official_state_import_template(args.out_dir, args.start_year, args.end_year))
    return 0


def _handle_audit_oil_gas_source_gate(args: argparse.Namespace) -> int:
    print(audit_oil_gas_source_gate(args.state_csv, args.panel, args.out_dir))
    return 0


def _handle_merge_oil_gas_state_sources(args: argparse.Namespace) -> int:
    print(merge_oil_gas_state_sources(args.out_dir, *args.state_csvs, panel_path=args.panel))
    return 0


def _handle_screen_dividend_low_vol_fcf_sectors(args: argparse.Namespace) -> int:
    print(
        run_dividend_low_vol_fcf_batch_screening(
            config_path=args.config,
            status_registry_path=args.status_registry,
            out_dir=args.out,
        )
    )
    return 0


def _handle_build_sector_replication_roadmap(args: argparse.Namespace) -> int:
    print(build_sector_replication_roadmap(config_path=args.config, out_dir=args.out))
    return 0


def _handle_add_low_volatility_factors(args: argparse.Namespace) -> int:
    print(
        add_low_volatility_factors(
            args.panel,
            args.price_csv,
            args.out,
            benchmark_csv=args.benchmark_csv,
            strategy_id=args.strategy_id,
            min_observations=args.min_observations,
        )
    )
    return 0


def _handle_construct_dividend_low_vol_fcf_basket(args: argparse.Namespace) -> int:
    print(construct_dividend_low_vol_fcf_basket(args.config, args.out))
    return 0


def _handle_daily_backtest_dividend_low_vol_fcf_basket(args: argparse.Namespace) -> int:
    print(
        run_basket_daily_backtest(
            args.config,
            args.signals,
            args.out,
            initial_cash=args.initial_cash,
            target_exposure=args.target_exposure,
            lot_size=args.lot_size,
            open_commission=args.open_commission,
            close_commission=args.close_commission,
            min_commission=args.min_commission,
        )
    )
    return 0


def _handle_validate_dividend_low_vol_fcf_basket(args: argparse.Namespace) -> int:
    print(
        run_basket_formal_validation(
            args.config,
            args.signals,
            args.daily_returns_csv,
            args.out,
        )
    )
    return 0


def _handle_ablate_dividend_low_vol_fcf_basket(args: argparse.Namespace) -> int:
    print(run_basket_ablation(args.config, args.out))
    return 0


def _handle_attribute_dividend_low_vol_fcf_basket_failures(args: argparse.Namespace) -> int:
    print(run_basket_failure_attribution(args.config, args.daily_dir, args.signals, args.out))
    return 0


def _handle_export_basket_frozen_signals_joinquant(args: argparse.Namespace) -> int:
    print(
        export_basket_frozen_signals_to_joinquant(
            args.signals,
            args.out_file,
            strategy_id=args.strategy_id,
            script_version=args.script_version,
            benchmark=args.benchmark,
            target_exposure=args.target_exposure,
            lot_size=args.lot_size,
        )
    )
    return 0
