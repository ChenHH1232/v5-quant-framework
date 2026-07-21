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
from v5.sector_replication_batch_runner import (
    DEFAULT_OUT_DIR as DEFAULT_SECTOR_REPLICATION_BATCH_OUT,
    run_sector_replication_batch,
)
from v5.theory_gated_sector_prevalidation_runner import (
    DEFAULT_CONFIG as DEFAULT_THEORY_GATED_PREVALIDATION_CONFIG,
    DEFAULT_OUT_DIR as DEFAULT_THEORY_GATED_PREVALIDATION_OUT,
    DEFAULT_STATUS_REGISTRY as DEFAULT_THEORY_GATED_PREVALIDATION_STATUS,
    run_theory_gated_sector_prevalidation,
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
from v5.home_appliances_state_gate_runner import (
    DEFAULT_DIVIDENDS as DEFAULT_HOME_APPLIANCES_STATE_DIVIDENDS,
    DEFAULT_OUT_DIR as DEFAULT_HOME_APPLIANCES_STATE_OUT,
    DEFAULT_PANEL as DEFAULT_HOME_APPLIANCES_STATE_PANEL,
    build_home_appliances_state_gate,
    collect_home_appliances_external_proxy_state,
)
from v5.home_appliances_state_diagnostic_runner import (
    DEFAULT_OUT_DIR as DEFAULT_HOME_APPLIANCES_STATE_DIAGNOSTIC_OUT,
    DEFAULT_PANEL as DEFAULT_HOME_APPLIANCES_STATE_DIAGNOSTIC_PANEL,
    DEFAULT_SPEC as DEFAULT_HOME_APPLIANCES_STATE_DIAGNOSTIC_SPEC,
    DEFAULT_STRATEGY_ID as DEFAULT_HOME_APPLIANCES_STATE_DIAGNOSTIC_ID,
    run_home_appliances_state_diagnostic,
)
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
from v5.gas_water_2021_pit_coverage_repair_runner import (
    DEFAULT_CURRENT_PANEL as DEFAULT_GAS_WATER_2021_REPAIR_CURRENT_PANEL,
    DEFAULT_OUT_DIR as DEFAULT_GAS_WATER_2021_REPAIR_OUT,
    DEFAULT_SEGMENT_EVIDENCE as DEFAULT_GAS_WATER_2021_REPAIR_SEGMENT_EVIDENCE,
    DEFAULT_SOURCE_PANEL as DEFAULT_GAS_WATER_2021_REPAIR_SOURCE_PANEL,
    DEFAULT_TRUE_EVIDENCE as DEFAULT_GAS_WATER_2021_REPAIR_TRUE_EVIDENCE,
    repair_gas_water_2021_07_pit_coverage,
)
from v5.gas_water_external_state_runner import (
    DEFAULT_BENCHMARK as DEFAULT_GAS_WATER_STATE_BENCHMARK,
    DEFAULT_ENRICHED_OUT_DIR as DEFAULT_GAS_WATER_STATE_ENRICHED_OUT,
    DEFAULT_OUT_DIR as DEFAULT_GAS_WATER_STATE_OUT,
    DEFAULT_PANEL as DEFAULT_GAS_WATER_STATE_PANEL,
    DEFAULT_VALIDATION_OUT_DIR as DEFAULT_GAS_WATER_STATE_VALIDATION_OUT,
    build_gas_water_external_state_panel,
    build_gas_water_state_enriched_panel,
    run_gas_water_state_bucket_validation,
    validate_gas_water_external_state,
)
from v5.gas_water_true_operating_state_runner import (
    DEFAULT_DISCLOSURE_CSV as DEFAULT_GAS_WATER_TRUE_STATE_DISCLOSURE,
    DEFAULT_OUT_DIR as DEFAULT_GAS_WATER_TRUE_STATE_OUT,
    DEFAULT_PANEL_OUT_DIR as DEFAULT_GAS_WATER_TRUE_STATE_PANEL_OUT,
    DEFAULT_PANEL_CSV as DEFAULT_GAS_WATER_TRUE_STATE_PANEL,
    build_gas_water_true_operating_state_panel,
    collect_gas_water_true_operating_state_evidence,
)
from v5.gas_water_state_guard_validation_runner import (
    DEFAULT_OUT_DIR as DEFAULT_GAS_WATER_STATE_GUARD_OUT,
    DEFAULT_PANEL as DEFAULT_GAS_WATER_STATE_GUARD_PANEL,
    DEFAULT_SPEC as DEFAULT_GAS_WATER_STATE_GUARD_SPEC,
    DEFAULT_STRATEGY_ID as DEFAULT_GAS_WATER_STATE_GUARD_ID,
    run_gas_water_state_guard_validation,
)
from v5.gas_water_state_guard_daily_backtest_runner import (
    DEFAULT_BENCHMARK_CSV as DEFAULT_GAS_WATER_STATE_GUARD_DAILY_BENCHMARK,
    DEFAULT_BENCHMARK_ID as DEFAULT_GAS_WATER_STATE_GUARD_DAILY_BENCHMARK_ID,
    DEFAULT_DIVIDEND_CASH_CSV as DEFAULT_GAS_WATER_STATE_GUARD_DAILY_DIVIDENDS,
    DEFAULT_EXECUTION_PRICE_CSV as DEFAULT_GAS_WATER_STATE_GUARD_DAILY_PRICES,
    DEFAULT_OUT_DIR as DEFAULT_GAS_WATER_STATE_GUARD_DAILY_OUT,
    DEFAULT_PANEL as DEFAULT_GAS_WATER_STATE_GUARD_DAILY_PANEL,
    DEFAULT_SPEC as DEFAULT_GAS_WATER_STATE_GUARD_DAILY_SPEC,
    run_gas_water_state_guard_daily_backtest,
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
    import_oil_gas_nbs_price_release,
    import_oil_gas_tushare_futures_state,
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

    gas_water_2021_repair_parser = subparsers.add_parser("repair-gas-water-2021-07-pit-coverage")
    gas_water_2021_repair_parser.add_argument("--source-panel", type=Path, default=DEFAULT_GAS_WATER_2021_REPAIR_SOURCE_PANEL)
    gas_water_2021_repair_parser.add_argument("--current-panel", type=Path, default=DEFAULT_GAS_WATER_2021_REPAIR_CURRENT_PANEL)
    gas_water_2021_repair_parser.add_argument("--true-evidence-csv", type=Path, default=DEFAULT_GAS_WATER_2021_REPAIR_TRUE_EVIDENCE)
    gas_water_2021_repair_parser.add_argument("--segment-evidence-csv", type=Path, default=DEFAULT_GAS_WATER_2021_REPAIR_SEGMENT_EVIDENCE)
    gas_water_2021_repair_parser.add_argument("--out-dir", type=Path, default=DEFAULT_GAS_WATER_2021_REPAIR_OUT)
    gas_water_2021_repair_parser.set_defaults(handler=_handle_repair_gas_water_2021_07_pit_coverage)

    gas_water_state_parser = subparsers.add_parser("build-gas-water-external-state")
    gas_water_state_parser.add_argument("--panel", type=Path, default=DEFAULT_GAS_WATER_STATE_PANEL)
    gas_water_state_parser.add_argument("--benchmark-csv", type=Path, default=DEFAULT_GAS_WATER_STATE_BENCHMARK)
    gas_water_state_parser.add_argument("--out-dir", type=Path, default=DEFAULT_GAS_WATER_STATE_OUT)
    gas_water_state_parser.add_argument("--include-official-proxies", action="store_true")
    gas_water_state_parser.set_defaults(handler=_handle_build_gas_water_external_state)

    gas_water_state_validate_parser = subparsers.add_parser("validate-gas-water-external-state")
    gas_water_state_validate_parser.add_argument("csv_path", type=Path)
    gas_water_state_validate_parser.set_defaults(handler=_handle_validate_gas_water_external_state)

    gas_water_state_panel_parser = subparsers.add_parser("build-gas-water-state-enriched-panel")
    gas_water_state_panel_parser.add_argument("--panel", type=Path, default=DEFAULT_GAS_WATER_STATE_PANEL)
    gas_water_state_panel_parser.add_argument("--state-csv", type=Path, default=DEFAULT_GAS_WATER_STATE_OUT / "gas_water_external_state.csv")
    gas_water_state_panel_parser.add_argument("--out-dir", type=Path, default=DEFAULT_GAS_WATER_STATE_ENRICHED_OUT)
    gas_water_state_panel_parser.add_argument("--strategy-id", default="gas_water_value_serviceability_state_diagnostic_v59")
    gas_water_state_panel_parser.set_defaults(handler=_handle_build_gas_water_state_enriched_panel)

    gas_water_state_bucket_parser = subparsers.add_parser("validate-gas-water-state-bucket")
    gas_water_state_bucket_parser.add_argument("--panel", type=Path, default=DEFAULT_GAS_WATER_STATE_ENRICHED_OUT / "panel_with_external_state.csv")
    gas_water_state_bucket_parser.add_argument("--out", type=Path, default=DEFAULT_GAS_WATER_STATE_VALIDATION_OUT)
    gas_water_state_bucket_parser.add_argument("--strategy-id", default="gas_water_value_serviceability_state_diagnostic_v59")
    gas_water_state_bucket_parser.add_argument("--state-metric", default="sector_receivables_to_revenue_median")
    gas_water_state_bucket_parser.add_argument("--selection-count", type=int, default=10)
    gas_water_state_bucket_parser.add_argument("--min-history", type=int, default=4)
    gas_water_state_bucket_parser.set_defaults(handler=_handle_validate_gas_water_state_bucket)

    gas_water_true_state_parser = subparsers.add_parser("collect-gas-water-true-operating-state")
    gas_water_true_state_parser.add_argument("--disclosure-csv", type=Path, default=DEFAULT_GAS_WATER_TRUE_STATE_DISCLOSURE)
    gas_water_true_state_parser.add_argument("--panel-csv", type=Path, default=DEFAULT_GAS_WATER_TRUE_STATE_PANEL)
    gas_water_true_state_parser.add_argument("--out-dir", type=Path, default=DEFAULT_GAS_WATER_TRUE_STATE_OUT)
    gas_water_true_state_parser.add_argument("--sample-size", type=int)
    gas_water_true_state_parser.add_argument("--seed", type=int, default=59)
    gas_water_true_state_parser.add_argument("--start-period")
    gas_water_true_state_parser.add_argument("--end-period")
    gas_water_true_state_parser.add_argument("--no-pdf-text", action="store_true")
    gas_water_true_state_parser.add_argument("--cache-pdf", action="store_true")
    gas_water_true_state_parser.add_argument("--max-pages", type=int, default=120)
    gas_water_true_state_parser.add_argument("--request-timeout-seconds", type=float, default=30.0)
    gas_water_true_state_parser.add_argument("--sleep-seconds", type=float, default=0.2)
    gas_water_true_state_parser.set_defaults(handler=_handle_collect_gas_water_true_operating_state)

    gas_water_true_state_panel_parser = subparsers.add_parser("build-gas-water-true-operating-state-panel")
    gas_water_true_state_panel_parser.add_argument("panel_csv", type=Path)
    gas_water_true_state_panel_parser.add_argument("evidence_csv", type=Path)
    gas_water_true_state_panel_parser.add_argument("--out-dir", type=Path, default=DEFAULT_GAS_WATER_TRUE_STATE_PANEL_OUT)
    gas_water_true_state_panel_parser.set_defaults(handler=_handle_build_gas_water_true_operating_state_panel)

    gas_water_state_guard_parser = subparsers.add_parser("validate-gas-water-state-guard")
    gas_water_state_guard_parser.add_argument("--panel", type=Path, default=DEFAULT_GAS_WATER_STATE_GUARD_PANEL)
    gas_water_state_guard_parser.add_argument("--base-spec", type=Path, default=DEFAULT_GAS_WATER_STATE_GUARD_SPEC)
    gas_water_state_guard_parser.add_argument("--out-dir", type=Path, default=DEFAULT_GAS_WATER_STATE_GUARD_OUT)
    gas_water_state_guard_parser.add_argument("--strategy-id", default=DEFAULT_GAS_WATER_STATE_GUARD_ID)
    gas_water_state_guard_parser.add_argument("--guard-field", default="true_financing_debt_density_per_10k")
    gas_water_state_guard_parser.add_argument("--guard-quantile", type=float, default=0.75)
    gas_water_state_guard_parser.add_argument("--min-history", type=int, default=8)
    gas_water_state_guard_parser.set_defaults(handler=_handle_validate_gas_water_state_guard)

    gas_water_state_guard_daily_parser = subparsers.add_parser("daily-backtest-gas-water-state-guard")
    gas_water_state_guard_daily_parser.add_argument("--spec", type=Path, default=DEFAULT_GAS_WATER_STATE_GUARD_DAILY_SPEC)
    gas_water_state_guard_daily_parser.add_argument("--panel", type=Path, default=DEFAULT_GAS_WATER_STATE_GUARD_DAILY_PANEL)
    gas_water_state_guard_daily_parser.add_argument("--execution-price-csv", type=Path, default=DEFAULT_GAS_WATER_STATE_GUARD_DAILY_PRICES)
    gas_water_state_guard_daily_parser.add_argument("--benchmark-csv", type=Path, default=DEFAULT_GAS_WATER_STATE_GUARD_DAILY_BENCHMARK)
    gas_water_state_guard_daily_parser.add_argument("--benchmark-id", default=DEFAULT_GAS_WATER_STATE_GUARD_DAILY_BENCHMARK_ID)
    gas_water_state_guard_daily_parser.add_argument("--dividend-cash-csv", type=Path, default=DEFAULT_GAS_WATER_STATE_GUARD_DAILY_DIVIDENDS)
    gas_water_state_guard_daily_parser.add_argument("--out", type=Path, default=DEFAULT_GAS_WATER_STATE_GUARD_DAILY_OUT)
    gas_water_state_guard_daily_parser.add_argument("--start-date", default="2021-05-01")
    gas_water_state_guard_daily_parser.add_argument("--end-date", default="2026-05-31")
    gas_water_state_guard_daily_parser.add_argument("--initial-cash", type=float, default=2_000_000.0)
    gas_water_state_guard_daily_parser.add_argument("--target-exposure", type=float, default=0.995)
    gas_water_state_guard_daily_parser.add_argument("--lot-size", type=int, default=100)
    gas_water_state_guard_daily_parser.set_defaults(handler=_handle_daily_backtest_gas_water_state_guard)

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
    oil_gas_conditioned_panel_parser.add_argument("--state-source-csv", type=Path)
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

    oil_gas_nbs_import_parser = subparsers.add_parser("import-oil-gas-nbs-price-release")
    oil_gas_nbs_import_parser.add_argument("url")
    oil_gas_nbs_import_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OIL_GAS_SOURCE_GATE_OUT)
    oil_gas_nbs_import_parser.add_argument("--timeout-seconds", type=float, default=20.0)
    oil_gas_nbs_import_parser.set_defaults(handler=_handle_import_oil_gas_nbs_price_release)

    oil_gas_tushare_import_parser = subparsers.add_parser("import-oil-gas-tushare-futures-state")
    oil_gas_tushare_import_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OIL_GAS_SOURCE_GATE_OUT)
    oil_gas_tushare_import_parser.add_argument("--panel", type=Path, default=DEFAULT_OIL_GAS_SOURCE_GATE_PANEL)
    oil_gas_tushare_import_parser.add_argument("--token-env", default="TUSHARE_TOKEN")
    oil_gas_tushare_import_parser.add_argument("--credential-file", type=Path)
    oil_gas_tushare_import_parser.add_argument("--crude-barrel-per-ton", type=float, default=7.33)
    oil_gas_tushare_import_parser.set_defaults(handler=_handle_import_oil_gas_tushare_futures_state)

    screen_parser = subparsers.add_parser("screen-dividend-low-vol-fcf-sectors")
    screen_parser.add_argument("--config", type=Path, default=DEFAULT_V56_SCREEN_CONFIG)
    screen_parser.add_argument("--status-registry", type=Path, default=DEFAULT_V56_STATUS_REGISTRY)
    screen_parser.add_argument("--out", type=Path, default=DEFAULT_V56_SCREEN_OUT)
    screen_parser.set_defaults(handler=_handle_screen_dividend_low_vol_fcf_sectors)

    roadmap_parser = subparsers.add_parser("build-sector-replication-roadmap")
    roadmap_parser.add_argument("--config", type=Path, default=DEFAULT_V58_REPLICATION_ROADMAP_CONFIG)
    roadmap_parser.add_argument("--out", type=Path, default=DEFAULT_V58_REPLICATION_ROADMAP_OUT)
    roadmap_parser.set_defaults(handler=_handle_build_sector_replication_roadmap)

    batch_parser = subparsers.add_parser("run-sector-replication-batch")
    batch_parser.add_argument("--screen-config", type=Path, default=DEFAULT_V56_SCREEN_CONFIG)
    batch_parser.add_argument("--roadmap-config", type=Path, default=DEFAULT_V58_REPLICATION_ROADMAP_CONFIG)
    batch_parser.add_argument("--status-registry", type=Path, default=DEFAULT_V56_STATUS_REGISTRY)
    batch_parser.add_argument("--out", type=Path, default=DEFAULT_SECTOR_REPLICATION_BATCH_OUT)
    batch_parser.set_defaults(handler=_handle_run_sector_replication_batch)

    theory_prevalidation_parser = subparsers.add_parser("theory-gated-sector-prevalidation")
    theory_prevalidation_parser.add_argument("--config", type=Path, default=DEFAULT_THEORY_GATED_PREVALIDATION_CONFIG)
    theory_prevalidation_parser.add_argument("--status-registry", type=Path, default=DEFAULT_THEORY_GATED_PREVALIDATION_STATUS)
    theory_prevalidation_parser.add_argument("--out", type=Path, default=DEFAULT_THEORY_GATED_PREVALIDATION_OUT)
    theory_prevalidation_parser.set_defaults(handler=_handle_theory_gated_sector_prevalidation)

    low_vol_parser = subparsers.add_parser("add-low-volatility-factors")
    low_vol_parser.add_argument("panel", type=Path)
    low_vol_parser.add_argument("price_csv", type=Path)
    low_vol_parser.add_argument("--benchmark-csv", type=Path)
    low_vol_parser.add_argument("--strategy-id")
    low_vol_parser.add_argument("--out", type=Path, default=DEFAULT_LOW_VOL_OUT_DIR)
    low_vol_parser.add_argument("--min-observations", type=int, default=40)
    low_vol_parser.set_defaults(handler=_handle_add_low_volatility_factors)

    home_appliances_state_parser = subparsers.add_parser("build-home-appliances-state-gate")
    home_appliances_state_parser.add_argument("--panel", type=Path, default=DEFAULT_HOME_APPLIANCES_STATE_PANEL)
    home_appliances_state_parser.add_argument("--dividend-cash-csv", type=Path, default=DEFAULT_HOME_APPLIANCES_STATE_DIVIDENDS)
    home_appliances_state_parser.add_argument("--external-state-csv", type=Path)
    home_appliances_state_parser.add_argument("--out-dir", type=Path, default=DEFAULT_HOME_APPLIANCES_STATE_OUT)
    home_appliances_state_parser.add_argument("--strategy-id", default="home_appliances_ocf_quality_v5a5c")
    home_appliances_state_parser.set_defaults(handler=_handle_build_home_appliances_state_gate)

    home_appliances_proxy_parser = subparsers.add_parser("collect-home-appliances-external-proxy-state")
    home_appliances_proxy_parser.add_argument("--panel", type=Path, default=DEFAULT_HOME_APPLIANCES_STATE_PANEL)
    home_appliances_proxy_parser.add_argument("--out-dir", type=Path, default=DEFAULT_HOME_APPLIANCES_STATE_OUT)
    home_appliances_proxy_parser.set_defaults(handler=_handle_collect_home_appliances_external_proxy_state)

    home_appliances_state_diag_parser = subparsers.add_parser("diagnose-home-appliances-state")
    home_appliances_state_diag_parser.add_argument("--spec", type=Path, default=DEFAULT_HOME_APPLIANCES_STATE_DIAGNOSTIC_SPEC)
    home_appliances_state_diag_parser.add_argument("--panel", type=Path, default=DEFAULT_HOME_APPLIANCES_STATE_DIAGNOSTIC_PANEL)
    home_appliances_state_diag_parser.add_argument("--out-dir", type=Path, default=DEFAULT_HOME_APPLIANCES_STATE_DIAGNOSTIC_OUT)
    home_appliances_state_diag_parser.add_argument("--strategy-id", default=DEFAULT_HOME_APPLIANCES_STATE_DIAGNOSTIC_ID)
    home_appliances_state_diag_parser.add_argument("--selection-count", type=int)
    home_appliances_state_diag_parser.add_argument("--min-history", type=int, default=4)
    home_appliances_state_diag_parser.set_defaults(handler=_handle_diagnose_home_appliances_state)

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


def _handle_repair_gas_water_2021_07_pit_coverage(args: argparse.Namespace) -> int:
    print(
        repair_gas_water_2021_07_pit_coverage(
            source_panel=args.source_panel,
            current_panel=args.current_panel,
            true_evidence_csv=args.true_evidence_csv,
            segment_evidence_csv=args.segment_evidence_csv,
            out_dir=args.out_dir,
        )
    )
    return 0


def _handle_build_gas_water_external_state(args: argparse.Namespace) -> int:
    print(build_gas_water_external_state_panel(args.panel, args.benchmark_csv, args.out_dir, args.include_official_proxies))
    return 0


def _handle_validate_gas_water_external_state(args: argparse.Namespace) -> int:
    print(validate_gas_water_external_state(args.csv_path))
    return 0


def _handle_build_gas_water_state_enriched_panel(args: argparse.Namespace) -> int:
    print(build_gas_water_state_enriched_panel(args.panel, args.state_csv, args.out_dir, args.strategy_id))
    return 0


def _handle_validate_gas_water_state_bucket(args: argparse.Namespace) -> int:
    print(
        run_gas_water_state_bucket_validation(
            args.panel,
            args.out,
            args.strategy_id,
            args.state_metric,
            args.selection_count,
            args.min_history,
        )
    )
    return 0


def _handle_collect_gas_water_true_operating_state(args: argparse.Namespace) -> int:
    print(
        collect_gas_water_true_operating_state_evidence(
            disclosure_csv=args.disclosure_csv,
            panel_csv=args.panel_csv,
            out_dir=args.out_dir,
            sample_size=args.sample_size,
            seed=args.seed,
            start_period=args.start_period,
            end_period=args.end_period,
            include_pdf_text=not args.no_pdf_text,
            cache_pdf=args.cache_pdf,
            max_pages=args.max_pages,
            request_timeout_seconds=args.request_timeout_seconds,
            sleep_seconds=args.sleep_seconds,
        )
    )
    return 0


def _handle_build_gas_water_true_operating_state_panel(args: argparse.Namespace) -> int:
    print(build_gas_water_true_operating_state_panel(args.panel_csv, args.evidence_csv, args.out_dir))
    return 0


def _handle_validate_gas_water_state_guard(args: argparse.Namespace) -> int:
    print(
        run_gas_water_state_guard_validation(
            panel_csv=args.panel,
            base_spec=args.base_spec,
            out_dir=args.out_dir,
            strategy_id=args.strategy_id,
            guard_field=args.guard_field,
            guard_quantile=args.guard_quantile,
            min_history=args.min_history,
        )
    )
    return 0


def _handle_daily_backtest_gas_water_state_guard(args: argparse.Namespace) -> int:
    print(
        run_gas_water_state_guard_daily_backtest(
            spec_path=args.spec,
            panel_csv=args.panel,
            execution_price_csv=args.execution_price_csv,
            benchmark_csv=args.benchmark_csv,
            out_dir=args.out,
            dividend_cash_csv=args.dividend_cash_csv,
            benchmark_id=args.benchmark_id,
            start_date=args.start_date,
            end_date=args.end_date,
            initial_cash=args.initial_cash,
            target_exposure=args.target_exposure,
            lot_size=args.lot_size,
        )
    )
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
    print(build_oil_gas_state_conditioned_panel(args.panel, args.out_dir, args.strategy_id, args.min_history, args.state_source_csv))
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


def _handle_import_oil_gas_nbs_price_release(args: argparse.Namespace) -> int:
    print(import_oil_gas_nbs_price_release(args.url, args.out_dir, args.timeout_seconds))
    return 0


def _handle_import_oil_gas_tushare_futures_state(args: argparse.Namespace) -> int:
    import os

    token = os.environ.get(args.token_env, "")
    if not token and args.credential_file:
        token = _read_tushare_token(args.credential_file)
    print(import_oil_gas_tushare_futures_state(token, args.out_dir, args.panel, args.crude_barrel_per_ton))
    return 0


def _read_tushare_token(path: Path) -> str:
    import re

    text = path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"Tushare\s*Token\s*[:：]\s*([^\s]+)", text, flags=re.IGNORECASE)
    if not match:
        raise ValueError(f"Tushare token not found in credential file: {path}")
    return match.group(1).strip()


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


def _handle_run_sector_replication_batch(args: argparse.Namespace) -> int:
    print(
        run_sector_replication_batch(
            screen_config=args.screen_config,
            roadmap_config=args.roadmap_config,
            status_registry=args.status_registry,
            out_dir=args.out,
        )
    )
    return 0


def _handle_theory_gated_sector_prevalidation(args: argparse.Namespace) -> int:
    print(
        run_theory_gated_sector_prevalidation(
            config_path=args.config,
            status_registry_path=args.status_registry,
            out_dir=args.out,
        )
    )
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


def _handle_build_home_appliances_state_gate(args: argparse.Namespace) -> int:
    print(
        build_home_appliances_state_gate(
            args.panel,
            args.dividend_cash_csv,
            args.external_state_csv,
            args.out_dir,
            strategy_id=args.strategy_id,
        )
    )
    return 0


def _handle_collect_home_appliances_external_proxy_state(args: argparse.Namespace) -> int:
    print(collect_home_appliances_external_proxy_state(args.panel, args.out_dir))
    return 0


def _handle_diagnose_home_appliances_state(args: argparse.Namespace) -> int:
    print(
        run_home_appliances_state_diagnostic(
            args.spec,
            args.panel,
            args.out_dir,
            strategy_id=args.strategy_id,
            selection_count=args.selection_count,
            min_history=args.min_history,
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
