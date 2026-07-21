from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from typing import Any

from v5.io_utils import read_csv_rows, read_csv_rows_if_exists, write_csv_rows, write_json_file
from v5.math_utils import fmt_float, to_float
from v5.paths import DEFAULT_PROCESSED_DIR


DEFAULT_PANEL = (
    DEFAULT_PROCESSED_DIR
    / "low_volatility_factors_v5a5"
    / "home_appliances"
    / "home_appliances_v5a5"
    / "panel_with_low_vol.csv"
)
DEFAULT_DIVIDENDS = DEFAULT_PROCESSED_DIR / "home_appliances_v5a5_joinquant_cash_dividends.csv"
DEFAULT_OUT_DIR = DEFAULT_PROCESSED_DIR / "home_appliances_state_gate_v5a5c"

STATE_FIELDS = [
    "trade_date",
    "visible_date",
    "scope",
    "sub_industry",
    "metric",
    "value",
    "unit",
    "source_name",
    "pit_usable",
    "review_status",
    "notes",
]

EXTERNAL_TEMPLATE_FIELDS = [
    "state_date",
    "visible_date",
    "metric",
    "value",
    "unit",
    "source_name",
    "source_url",
    "source_publication_date",
    "pit_usable",
    "review_status",
    "notes",
]

ENRICHED_FIELDS = [
    "home_appliances_state_visible_date",
    "sector_ocf_yield_median",
    "sector_ocf_to_net_profit_median",
    "sector_cash_collection_quality_median",
    "sector_capex_burden_median",
    "sector_asset_liability_ratio_median",
    "sector_low_vol_score_median",
    "sector_dividend_yield_median",
    "sector_inventory_to_revenue_median",
    "sector_receivables_to_revenue_median",
    "sector_working_capital_pressure_to_revenue_median",
    "sector_current_ratio_median",
    "sector_overseas_revenue_share_median",
    "sector_negative_ocf_yield_ratio",
    "sector_high_capex_burden_ratio",
    "sector_high_export_exposure_ratio",
    "sector_high_inventory_pressure_ratio",
    "sector_high_receivables_pressure_ratio",
    "sector_high_working_capital_pressure_ratio",
    "subindustry_ocf_yield_median",
    "subindustry_ocf_to_net_profit_median",
    "subindustry_cash_collection_quality_median",
    "subindustry_capex_burden_median",
    "subindustry_low_vol_score_median",
    "subindustry_inventory_to_revenue_median",
    "subindustry_receivables_to_revenue_median",
    "subindustry_working_capital_pressure_to_revenue_median",
    "subindustry_overseas_revenue_share_median",
    "code_net_cash_per_share_trailing_365d",
    "code_dividend_event_count_trailing_365d",
    "home_appliances_capex_policy_flag",
    "home_appliances_dividend_support_flag",
    "home_appliances_external_state_gate",
    "external_real_estate_climate_index",
    "external_china_exports_yoy",
    "external_commodity_price_index",
    "external_producer_goods_total_yoy",
    "external_mineral_goods_yoy",
    "external_energy_goods_yoy",
    "external_state_visible_date",
    "external_state_source",
]

FINANCIAL_METRICS = [
    ("ocf_yield_median", "operating_cash_flow_yield", "ratio", "Higher OCF yield supports the cash-flow value hypothesis."),
    (
        "ocf_to_net_profit_median",
        "operating_cash_flow_to_net_profit",
        "ratio",
        "Higher OCF to profit supports earnings cash-conversion quality.",
    ),
    ("cash_collection_quality_median", "cash_collection_quality", "ratio", "Higher cash collection quality lowers channel / receivable risk."),
    ("capex_burden_median", "capex_burden", "ratio", "Capex burden is diagnostic until sector capex policy is reviewed."),
    ("asset_liability_ratio_median", "asset_liability_ratio", "ratio", "Balance-sheet leverage pressure proxy."),
    ("low_vol_score_median", "low_vol_score", "score", "Low-volatility score is diagnostic, not a V5a.5c scoring factor."),
    ("dividend_yield_median", "dividend_yield", "percent", "Dividend yield is diagnostic until real dividend support is audited."),
    ("inventory_to_revenue_median", "inventory_to_revenue", "ratio", "Higher inventory to revenue can indicate demand or channel pressure."),
    ("receivables_to_revenue_median", "receivables_to_revenue", "ratio", "Higher receivables to revenue can indicate cash-collection pressure."),
    (
        "working_capital_pressure_to_revenue_median",
        "working_capital_pressure_to_revenue",
        "ratio",
        "Inventory plus receivables plus contract assets minus contract liabilities relative to revenue.",
    ),
    ("current_ratio_median", "current_ratio", "ratio", "Liquidity support proxy."),
    (
        "overseas_revenue_share_median",
        "overseas_revenue_share",
        "ratio",
        "Higher overseas revenue share indicates export-cycle sensitivity.",
    ),
]

EXTERNAL_METRICS = [
    ("property_sales_yoy", "percent", "NBS commercial residential sales or reviewed official real-estate demand proxy."),
    ("residential_completion_area_yoy", "percent", "NBS residential completion area proxy for appliance installation demand."),
    ("home_appliance_export_value_yoy", "percent", "Customs / industry association appliance export value growth."),
    ("home_appliance_inventory_pressure", "index", "Reviewed inventory or channel inventory pressure proxy."),
    ("raw_material_cost_pressure", "index", "Copper / steel / plastics cost pressure proxy."),
]


@dataclass(frozen=True)
class HomeAppliancesStateGateResult:
    state_csv: Path
    enriched_panel_csv: Path
    external_template_csv: Path
    summary_json: Path
    status: str
    row_count: int
    dividend_event_count: int


@dataclass(frozen=True)
class HomeAppliancesExternalProxyResult:
    proxy_csv: Path
    manifest_json: Path
    row_count: int
    metric_count: int
    status: str


def build_home_appliances_state_gate(
    panel_csv: Path = DEFAULT_PANEL,
    dividend_cash_csv: Path | None = DEFAULT_DIVIDENDS,
    external_state_csv: Path | None = None,
    out_dir: Path = DEFAULT_OUT_DIR,
    strategy_id: str = "home_appliances_ocf_quality_v5a5c",
) -> HomeAppliancesStateGateResult:
    panel_rows = read_csv_rows(panel_csv)
    dividend_rows = read_csv_rows_if_exists(dividend_cash_csv)
    if external_state_csv is None:
        candidate = out_dir / "home_appliances_external_state_official_proxy.csv"
        external_state_csv = candidate if candidate.exists() else None
    external_rows = read_csv_rows_if_exists(external_state_csv)
    dividend_index = _build_dividend_index(dividend_rows)
    grouped = _group_panel_rows(panel_rows)
    external_by_date = _external_state_by_trade_date(external_rows)

    state_rows: list[dict[str, Any]] = []
    enriched_rows: list[dict[str, Any]] = []
    for trade_date in sorted(grouped):
        date_rows = grouped[trade_date]
        sector_state = _financial_state_rows(trade_date, "sector", "", date_rows)
        state_rows.extend(sector_state)
        sector_lookup = _state_lookup(sector_state)

        by_sub: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in date_rows:
            by_sub[str(row.get("sub_industry") or "unknown")].append(row)
        sub_lookup: dict[str, dict[str, str]] = {}
        for sub_industry, sub_rows in sorted(by_sub.items()):
            sub_state = _financial_state_rows(trade_date, "sub_industry", sub_industry, sub_rows)
            state_rows.extend(sub_state)
            sub_lookup[sub_industry] = _state_lookup(sub_state)

        sector_capex_median = to_float(sector_lookup.get("capex_burden_median"))
        external_lookup = external_by_date.get(trade_date, {})
        for row in date_rows:
            code = str(row.get("code") or "")
            sub_industry = str(row.get("sub_industry") or "unknown")
            dividends = _trailing_dividends(dividend_index.get(code, []), trade_date, days=365)
            enriched = dict(row)
            enriched.update(
                _enriched_state_fields(
                    row,
                    sector_lookup,
                    sub_lookup.get(sub_industry, {}),
                    sector_capex_median,
                    dividends,
                    external_lookup,
                )
            )
            enriched_rows.append(enriched)

    external_template_rows = _external_template_rows(sorted(grouped))
    validation = _validate_state_gate(panel_rows, enriched_rows, dividend_rows, external_template_rows, external_rows)

    out_dir.mkdir(parents=True, exist_ok=True)
    state_csv = out_dir / "home_appliances_state_gate.csv"
    enriched_csv = out_dir / "panel_with_home_appliances_state_gate.csv"
    template_csv = out_dir / "home_appliances_external_state_import_template.csv"
    summary_json = out_dir / "home_appliances_state_gate_summary.json"

    write_csv_rows(state_csv, STATE_FIELDS, state_rows)
    write_csv_rows(enriched_csv, _merge_fieldnames(panel_rows, ENRICHED_FIELDS), enriched_rows)
    write_csv_rows(template_csv, EXTERNAL_TEMPLATE_FIELDS, external_template_rows)
    write_json_file(
        summary_json,
        {
            "dataset": "home_appliances_state_gate_v5a5c",
            "strategy_id": strategy_id,
            "panel_csv": str(panel_csv),
            "dividend_cash_csv": str(dividend_cash_csv) if dividend_cash_csv else None,
            "external_state_csv": str(external_state_csv) if external_state_csv else None,
            "state_csv": str(state_csv),
            "enriched_panel_csv": str(enriched_csv),
            "external_template_csv": str(template_csv),
            "row_count": len(panel_rows),
            "trade_date_count": len(grouped),
            "dividend_event_count": len(dividend_rows),
            "status": validation["status"],
            "checks": validation["checks"],
            "pm_rule": "Home appliances cannot move to Engineering until true external state or a documented no-state policy is reviewed.",
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return HomeAppliancesStateGateResult(
        state_csv=state_csv,
        enriched_panel_csv=enriched_csv,
        external_template_csv=template_csv,
        summary_json=summary_json,
        status=str(validation["status"]),
        row_count=len(panel_rows),
        dividend_event_count=len(dividend_rows),
    )


def collect_home_appliances_external_proxy_state(
    panel_csv: Path = DEFAULT_PANEL,
    out_dir: Path = DEFAULT_OUT_DIR,
) -> HomeAppliancesExternalProxyResult:
    try:
        import akshare as ak
    except Exception as exc:  # pragma: no cover - optional dependency.
        raise RuntimeError("collect-home-appliances-external-proxy-state requires akshare") from exc

    trade_dates = sorted(_group_panel_rows(read_csv_rows(panel_csv)))
    raw_sources: list[dict[str, Any]] = []
    warnings: list[str] = []

    raw_sources.extend(
        _collect_ak_series(
            lambda: ak.macro_china_real_estate(),
            source_name="akshare.macro_china_real_estate",
            date_column="日期",
            value_column="最新值",
            metric="real_estate_climate_index",
            unit="index",
            visible_lag_days=45,
            warnings=warnings,
        )
    )
    raw_sources.extend(
        _collect_ak_series(
            lambda: ak.macro_china_exports_yoy(),
            source_name="akshare.macro_china_exports_yoy",
            date_column="日期",
            value_column="今值",
            metric="china_exports_yoy",
            unit="percent",
            visible_lag_days=0,
            warnings=warnings,
        )
    )
    raw_sources.extend(
        _collect_ak_series(
            lambda: ak.macro_china_commodity_price_index(),
            source_name="akshare.macro_china_commodity_price_index",
            date_column="日期",
            value_column="最新值",
            metric="commodity_price_index",
            unit="index",
            visible_lag_days=0,
            warnings=warnings,
        )
    )
    raw_sources.extend(_collect_qyspjg_proxy_rows(ak, warnings))

    rows: list[dict[str, Any]] = []
    by_metric: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in raw_sources:
        by_metric[str(item["metric"])].append(item)
    for values in by_metric.values():
        values.sort(key=lambda item: str(item["visible_date"]))

    for trade_date in trade_dates:
        for metric, values in sorted(by_metric.items()):
            visible = [item for item in values if str(item["visible_date"])[:10] <= trade_date]
            if not visible:
                continue
            item = visible[-1]
            rows.append(
                {
                    "trade_date": trade_date,
                    "visible_date": item["visible_date"],
                    "scope": "official_proxy",
                    "sub_industry": "",
                    "metric": metric,
                    "value": fmt_float(item["value"]),
                    "unit": item["unit"],
                    "source_name": item["source_name"],
                    "pit_usable": "true",
                    "review_status": "official_proxy_conservative_visible_date",
                    "notes": item["notes"],
                }
            )

    out_dir.mkdir(parents=True, exist_ok=True)
    proxy_csv = out_dir / "home_appliances_external_state_official_proxy.csv"
    manifest_json = out_dir / "home_appliances_external_state_official_proxy_manifest.json"
    write_csv_rows(proxy_csv, STATE_FIELDS, rows)
    metrics = sorted({row["metric"] for row in rows})
    status = "proxy_state_collected_needs_review" if rows else "proxy_state_collection_failed"
    write_json_file(
        manifest_json,
        {
            "dataset": "home_appliances_external_state_official_proxy_v5a5c",
            "panel_csv": str(panel_csv),
            "proxy_csv": str(proxy_csv),
            "row_count": len(rows),
            "metric_count": len(metrics),
            "metrics": metrics,
            "warnings": warnings,
            "status": status,
            "pit_policy": "For each rebalance date, use the latest proxy observation with conservative visible_date <= trade_date.",
            "limitations": [
                "These are official/public proxies, not company-level appliance inventory or export exposure.",
                "Proxy state can support diagnostics, but does not by itself approve Engineering handoff.",
            ],
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return HomeAppliancesExternalProxyResult(proxy_csv, manifest_json, len(rows), len(metrics), status)


def _group_panel_rows(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        trade_date = str(row.get("trade_date") or "")[:10]
        if trade_date:
            grouped[trade_date].append(row)
    return dict(grouped)


def _financial_state_rows(trade_date: str, scope: str, sub_industry: str, rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    visible_date = _max_visible_date(rows, trade_date)
    result: list[dict[str, Any]] = []
    for metric, source_field, unit, notes in FINANCIAL_METRICS:
        values = [value for value in (to_float(row.get(source_field)) for row in rows) if value is not None]
        result.append(
            {
                "trade_date": trade_date,
                "visible_date": visible_date,
                "scope": scope,
                "sub_industry": sub_industry,
                "metric": metric,
                "value": fmt_float(median(values) if values else None),
                "unit": unit,
                "source_name": f"panel.{source_field}",
                "pit_usable": "true" if visible_date <= trade_date and values else "false",
                "review_status": "derived_from_pit_panel" if values else "missing",
                "notes": notes,
            }
        )
    result.extend(_ratio_state_rows(trade_date, visible_date, scope, sub_industry, rows))
    return result


def _ratio_state_rows(trade_date: str, visible_date: str, scope: str, sub_industry: str, rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    ocf_values = [to_float(row.get("operating_cash_flow_yield")) for row in rows]
    capex_values = [to_float(row.get("capex_burden")) for row in rows]
    inventory_values = [to_float(row.get("inventory_to_revenue")) for row in rows]
    receivables_values = [to_float(row.get("receivables_to_revenue")) for row in rows]
    working_values = [to_float(row.get("working_capital_pressure_to_revenue")) for row in rows]
    export_values = [to_float(row.get("overseas_revenue_share")) for row in rows]
    ocf_valid = [value for value in ocf_values if value is not None]
    capex_valid = [value for value in capex_values if value is not None]
    inventory_valid = [value for value in inventory_values if value is not None]
    receivables_valid = [value for value in receivables_values if value is not None]
    working_valid = [value for value in working_values if value is not None]
    export_valid = [value for value in export_values if value is not None]
    return [
        {
            "trade_date": trade_date,
            "visible_date": visible_date,
            "scope": scope,
            "sub_industry": sub_industry,
            "metric": "negative_ocf_yield_ratio",
            "value": fmt_float(_share(ocf_valid, lambda value: value < 0)),
            "unit": "ratio",
            "source_name": "panel.operating_cash_flow_yield",
            "pit_usable": "true" if visible_date <= trade_date and ocf_valid else "false",
            "review_status": "derived_from_pit_panel" if ocf_valid else "missing",
            "notes": "Higher ratio indicates more companies with negative OCF yield.",
        },
        {
            "trade_date": trade_date,
            "visible_date": visible_date,
            "scope": scope,
            "sub_industry": sub_industry,
            "metric": "high_capex_burden_ratio",
            "value": fmt_float(_share(capex_valid, lambda value: value > 1.0)),
            "unit": "ratio",
            "source_name": "panel.capex_burden",
            "pit_usable": "true" if visible_date <= trade_date and capex_valid else "false",
            "review_status": "derived_from_pit_panel" if capex_valid else "missing",
            "notes": "Uses capex_burden > 1.0 as a conservative pressure flag; sector policy still needs review.",
        },
        {
            "trade_date": trade_date,
            "visible_date": visible_date,
            "scope": scope,
            "sub_industry": sub_industry,
            "metric": "high_export_exposure_ratio",
            "value": fmt_float(_share(export_valid, lambda value: value > 0.3)),
            "unit": "ratio",
            "source_name": "panel.overseas_revenue_share",
            "pit_usable": "true" if visible_date <= trade_date and export_valid else "false",
            "review_status": "derived_from_pit_segment_panel" if export_valid else "missing",
            "notes": "Uses overseas_revenue_share > 0.3 as a first-pass export-cycle exposure flag.",
        },
        {
            "trade_date": trade_date,
            "visible_date": visible_date,
            "scope": scope,
            "sub_industry": sub_industry,
            "metric": "high_inventory_pressure_ratio",
            "value": fmt_float(_share(inventory_valid, lambda value: value > 0.5)),
            "unit": "ratio",
            "source_name": "panel.inventory_to_revenue",
            "pit_usable": "true" if visible_date <= trade_date and inventory_valid else "false",
            "review_status": "derived_from_pit_panel" if inventory_valid else "missing",
            "notes": "Uses inventory_to_revenue > 0.5 as a first-pass appliance inventory pressure flag.",
        },
        {
            "trade_date": trade_date,
            "visible_date": visible_date,
            "scope": scope,
            "sub_industry": sub_industry,
            "metric": "high_receivables_pressure_ratio",
            "value": fmt_float(_share(receivables_valid, lambda value: value > 0.5)),
            "unit": "ratio",
            "source_name": "panel.receivables_to_revenue",
            "pit_usable": "true" if visible_date <= trade_date and receivables_valid else "false",
            "review_status": "derived_from_pit_panel" if receivables_valid else "missing",
            "notes": "Uses receivables_to_revenue > 0.5 as a first-pass collection pressure flag.",
        },
        {
            "trade_date": trade_date,
            "visible_date": visible_date,
            "scope": scope,
            "sub_industry": sub_industry,
            "metric": "high_working_capital_pressure_ratio",
            "value": fmt_float(_share(working_valid, lambda value: value > 1.0)),
            "unit": "ratio",
            "source_name": "panel.working_capital_pressure_to_revenue",
            "pit_usable": "true" if visible_date <= trade_date and working_valid else "false",
            "review_status": "derived_from_pit_panel" if working_valid else "missing",
            "notes": "Uses working_capital_pressure_to_revenue > 1.0 as a conservative balance-sheet pressure flag.",
        },
    ]


def _enriched_state_fields(
    row: dict[str, str],
    sector: dict[str, str],
    sub: dict[str, str],
    sector_capex_median: float | None,
    dividends: list[dict[str, str]],
    external: dict[str, str],
) -> dict[str, str]:
    capex = to_float(row.get("capex_burden"))
    net_cash = sum(to_float(item.get("net_cash_per_share")) or 0.0 for item in dividends)
    capex_flag = "needs_review"
    if capex is not None and sector_capex_median is not None:
        capex_flag = "above_sector_median" if capex > sector_capex_median else "at_or_below_sector_median"
    dividend_flag = "has_trailing_cash_dividend" if net_cash > 0 else "no_trailing_cash_dividend"
    return {
        "home_appliances_state_visible_date": sector.get("_visible_date", ""),
        "sector_ocf_yield_median": sector.get("ocf_yield_median", ""),
        "sector_ocf_to_net_profit_median": sector.get("ocf_to_net_profit_median", ""),
        "sector_cash_collection_quality_median": sector.get("cash_collection_quality_median", ""),
        "sector_capex_burden_median": sector.get("capex_burden_median", ""),
        "sector_asset_liability_ratio_median": sector.get("asset_liability_ratio_median", ""),
        "sector_low_vol_score_median": sector.get("low_vol_score_median", ""),
        "sector_dividend_yield_median": sector.get("dividend_yield_median", ""),
        "sector_inventory_to_revenue_median": sector.get("inventory_to_revenue_median", ""),
        "sector_receivables_to_revenue_median": sector.get("receivables_to_revenue_median", ""),
        "sector_working_capital_pressure_to_revenue_median": sector.get("working_capital_pressure_to_revenue_median", ""),
        "sector_current_ratio_median": sector.get("current_ratio_median", ""),
        "sector_overseas_revenue_share_median": sector.get("overseas_revenue_share_median", ""),
        "sector_negative_ocf_yield_ratio": sector.get("negative_ocf_yield_ratio", ""),
        "sector_high_capex_burden_ratio": sector.get("high_capex_burden_ratio", ""),
        "sector_high_export_exposure_ratio": sector.get("high_export_exposure_ratio", ""),
        "sector_high_inventory_pressure_ratio": sector.get("high_inventory_pressure_ratio", ""),
        "sector_high_receivables_pressure_ratio": sector.get("high_receivables_pressure_ratio", ""),
        "sector_high_working_capital_pressure_ratio": sector.get("high_working_capital_pressure_ratio", ""),
        "subindustry_ocf_yield_median": sub.get("ocf_yield_median", ""),
        "subindustry_ocf_to_net_profit_median": sub.get("ocf_to_net_profit_median", ""),
        "subindustry_cash_collection_quality_median": sub.get("cash_collection_quality_median", ""),
        "subindustry_capex_burden_median": sub.get("capex_burden_median", ""),
        "subindustry_low_vol_score_median": sub.get("low_vol_score_median", ""),
        "subindustry_inventory_to_revenue_median": sub.get("inventory_to_revenue_median", ""),
        "subindustry_receivables_to_revenue_median": sub.get("receivables_to_revenue_median", ""),
        "subindustry_working_capital_pressure_to_revenue_median": sub.get("working_capital_pressure_to_revenue_median", ""),
        "subindustry_overseas_revenue_share_median": sub.get("overseas_revenue_share_median", ""),
        "code_net_cash_per_share_trailing_365d": fmt_float(net_cash),
        "code_dividend_event_count_trailing_365d": str(len(dividends)),
        "home_appliances_capex_policy_flag": capex_flag,
        "home_appliances_dividend_support_flag": dividend_flag,
        "home_appliances_external_state_gate": "official_proxy_needs_review" if external else "missing_true_property_export_inventory_state",
        "external_real_estate_climate_index": external.get("real_estate_climate_index", ""),
        "external_china_exports_yoy": external.get("china_exports_yoy", ""),
        "external_commodity_price_index": external.get("commodity_price_index", ""),
        "external_producer_goods_total_yoy": external.get("producer_goods_total_yoy", ""),
        "external_mineral_goods_yoy": external.get("mineral_goods_yoy", ""),
        "external_energy_goods_yoy": external.get("energy_goods_yoy", ""),
        "external_state_visible_date": external.get("_visible_date", ""),
        "external_state_source": external.get("_source", ""),
    }


def _state_lookup(rows: list[dict[str, Any]]) -> dict[str, str]:
    result: dict[str, str] = {}
    visible_dates = []
    for row in rows:
        metric = str(row.get("metric") or "")
        result[metric] = str(row.get("value") or "")
        visible = str(row.get("visible_date") or "")
        if visible:
            visible_dates.append(visible)
    result["_visible_date"] = max(visible_dates) if visible_dates else ""
    return result


def _external_state_by_trade_date(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    grouped: dict[str, dict[str, str]] = defaultdict(dict)
    visible_dates: dict[str, list[str]] = defaultdict(list)
    sources: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        trade_date = str(row.get("trade_date") or "")[:10]
        metric = str(row.get("metric") or "")
        if not trade_date or not metric:
            continue
        grouped[trade_date][metric] = str(row.get("value") or "")
        visible = str(row.get("visible_date") or "")[:10]
        source = str(row.get("source_name") or "")
        if visible:
            visible_dates[trade_date].append(visible)
        if source and source not in sources[trade_date]:
            sources[trade_date].append(source)
    for trade_date, values in grouped.items():
        values["_visible_date"] = max(visible_dates[trade_date]) if visible_dates[trade_date] else ""
        values["_source"] = ";".join(sources[trade_date])
    return dict(grouped)


def _external_template_rows(trade_dates: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for trade_date in trade_dates:
        state_date = _previous_month_end(trade_date)
        for metric, unit, notes in EXTERNAL_METRICS:
            rows.append(
                {
                    "state_date": state_date,
                    "visible_date": "",
                    "metric": metric,
                    "value": "",
                    "unit": unit,
                    "source_name": "",
                    "source_url": "",
                    "source_publication_date": "",
                    "pit_usable": "false",
                    "review_status": "manual_or_vendor_import_required",
                    "notes": notes,
                }
            )
    return rows


def _validate_state_gate(
    panel_rows: list[dict[str, str]],
    enriched_rows: list[dict[str, str]],
    dividend_rows: list[dict[str, str]],
    external_template_rows: list[dict[str, str]],
    external_rows: list[dict[str, str]],
) -> dict[str, Any]:
    row_count = len(panel_rows)
    checks = [
        _check("panel_rows", "pass" if row_count > 0 else "blocker", f"panel rows={row_count}"),
        _check(
            "dividend_events",
            "pass" if dividend_rows else "needs_review",
            f"JoinQuant cash dividend events={len(dividend_rows)}",
        ),
        _check(
            "state_enrichment",
            "pass" if len(enriched_rows) == row_count and row_count > 0 else "blocker",
            f"enriched rows={len(enriched_rows)}",
        ),
        _check(
            "true_inventory_receivable_working_capital_state",
            "pass" if _field_coverage(enriched_rows, "inventory_to_revenue") >= 0.8
            and _field_coverage(enriched_rows, "receivables_to_revenue") >= 0.8
            and _field_coverage(enriched_rows, "working_capital_pressure_to_revenue") >= 0.8
            else "needs_review",
            (
                "coverage inventory_to_revenue="
                f"{fmt_float(_field_coverage(enriched_rows, 'inventory_to_revenue'))}; "
                "receivables_to_revenue="
                f"{fmt_float(_field_coverage(enriched_rows, 'receivables_to_revenue'))}; "
                "working_capital_pressure_to_revenue="
                f"{fmt_float(_field_coverage(enriched_rows, 'working_capital_pressure_to_revenue'))}"
            ),
        ),
        _check(
            "true_export_exposure_state",
            "pass" if _field_coverage(enriched_rows, "overseas_revenue_share") >= 0.8 else "needs_review",
            f"coverage overseas_revenue_share={fmt_float(_field_coverage(enriched_rows, 'overseas_revenue_share'))}",
        ),
        _check(
            "official_proxy_external_state",
            "needs_review" if external_rows else "blocker",
            f"proxy rows={len(external_rows)}; template rows={len(external_template_rows)}; property/export demand and raw-material state still require reviewed PIT import or a documented no-state policy",
        ),
    ]
    if any(item["status"] == "blocker" for item in checks):
        status = "research_state_gate_blocked_by_external_state"
    elif any(item["status"] == "needs_review" for item in checks):
        status = "research_state_gate_proxy_repaired_needs_review"
    else:
        status = "research_state_gate_passed"
    return {"status": status, "checks": checks}


def _check(name: str, status: str, detail: str) -> dict[str, str]:
    return {"check": name, "status": status, "detail": detail}


def _field_coverage(rows: list[dict[str, str]], field: str) -> float:
    if not rows:
        return 0.0
    return sum(1 for row in rows if row.get(field) not in ("", None)) / len(rows)


def _collect_ak_series(
    loader: Any,
    *,
    source_name: str,
    date_column: str,
    value_column: str,
    metric: str,
    unit: str,
    visible_lag_days: int,
    warnings: list[str],
) -> list[dict[str, Any]]:
    try:
        df = loader()
    except Exception as exc:
        warnings.append(f"{source_name}: {repr(exc)}")
        return []
    result: list[dict[str, Any]] = []
    if df is None or getattr(df, "empty", True):
        warnings.append(f"{source_name}: no rows")
        return result
    for row in df.to_dict(orient="records"):
        state_date = _parse_date(str(row.get(date_column) or "")[:10])
        value = to_float(row.get(value_column))
        if state_date is None or value is None:
            continue
        visible_date = state_date + timedelta(days=visible_lag_days)
        result.append(
            {
                "metric": metric,
                "state_date": state_date.isoformat(),
                "visible_date": visible_date.isoformat(),
                "value": value,
                "unit": unit,
                "source_name": source_name,
                "notes": f"{metric} official/public proxy; visible lag={visible_lag_days} days.",
            }
        )
    return result


def _collect_qyspjg_proxy_rows(ak: Any, warnings: list[str]) -> list[dict[str, Any]]:
    try:
        df = ak.macro_china_qyspjg()
    except Exception as exc:
        warnings.append(f"akshare.macro_china_qyspjg: {repr(exc)}")
        return []
    if df is None or getattr(df, "empty", True):
        warnings.append("akshare.macro_china_qyspjg: no rows")
        return []
    specs = [
        ("producer_goods_total_yoy", "总指数-同比增长"),
        ("mineral_goods_yoy", "矿产品-同比增长"),
        ("energy_goods_yoy", "煤油电-同比增长"),
    ]
    rows: list[dict[str, Any]] = []
    for raw in df.to_dict(orient="records"):
        state_date = _parse_chinese_month(str(raw.get("月份") or ""))
        if state_date is None:
            continue
        visible_date = state_date + timedelta(days=25)
        for metric, column in specs:
            value = to_float(raw.get(column))
            if value is None:
                continue
            rows.append(
                {
                    "metric": metric,
                    "state_date": state_date.isoformat(),
                    "visible_date": visible_date.isoformat(),
                    "value": value,
                    "unit": "percent",
                    "source_name": "akshare.macro_china_qyspjg",
                    "notes": f"{metric} production-material price proxy; conservative month-end plus 25 day visibility.",
                }
            )
    return rows


def _parse_chinese_month(text: str) -> date | None:
    if "年" not in text or "月" not in text:
        return None
    try:
        year = int(text.split("年", 1)[0])
        month_text = text.split("年", 1)[1].split("月", 1)[0]
        month = int(month_text)
    except ValueError:
        return None
    first_next_month = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return first_next_month - timedelta(days=1)


def _build_dividend_index(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    by_code: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        code = str(row.get("code") or "")
        pay_date = str(row.get("pay_date") or row.get("ex_date") or "")[:10]
        if code and pay_date:
            by_code[code].append(row)
    for values in by_code.values():
        values.sort(key=lambda item: str(item.get("pay_date") or item.get("ex_date") or ""))
    return dict(by_code)


def _trailing_dividends(rows: list[dict[str, str]], trade_date: str, days: int) -> list[dict[str, str]]:
    end = _parse_date(trade_date)
    if end is None:
        return []
    start = end - timedelta(days=days)
    result = []
    for row in rows:
        day = _parse_date(str(row.get("pay_date") or row.get("ex_date") or "")[:10])
        if day is not None and start <= day < end:
            result.append(row)
    return result


def _max_visible_date(rows: list[dict[str, str]], trade_date: str) -> str:
    visible = [
        str(row.get("factor_visible_date") or row.get("notice_date") or row.get("announce_date") or "")[:10]
        for row in rows
    ]
    visible = [item for item in visible if item]
    if not visible:
        return trade_date
    return min(max(visible), trade_date)


def _share(values: list[float], predicate: Any) -> float | None:
    if not values:
        return None
    return sum(1 for value in values if predicate(value)) / len(values)


def _previous_month_end(text: str) -> str:
    parsed = _parse_date(text)
    if parsed is None:
        return text[:10]
    first = parsed.replace(day=1)
    previous = first - timedelta(days=1)
    return previous.isoformat()


def _parse_date(text: str) -> date | None:
    try:
        return date.fromisoformat(str(text)[:10])
    except ValueError:
        return None


def _merge_fieldnames(rows: list[dict[str, str]], extra: list[str]) -> list[str]:
    names: list[str] = []
    for row in rows:
        for key in row:
            if key not in names:
                names.append(key)
    for key in extra:
        if key not in names:
            names.append(key)
    return names
