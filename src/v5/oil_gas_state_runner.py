from __future__ import annotations

import argparse
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.paths import DEFAULT_DATABASE_DIR


DEFAULT_OUT_DIR = DEFAULT_DATABASE_DIR / "processed" / "oil_gas_external_state_v58a"
DEFAULT_PANEL_OUT_DIR = DEFAULT_DATABASE_DIR / "processed" / "oil_gas_formal_panel_v58a"

STATE_FIELDS = [
    "visible_date",
    "state_date",
    "state_scope",
    "sub_industry",
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

REQUIRED_RESEARCH_METRICS = [
    "crude_oil_price_state",
    "fuel_oil_price_state",
    "bitumen_price_state",
    "low_sulfur_fuel_oil_price_state",
    "gas_liquid_price_state",
    "refining_spread_proxy_state",
]

FUTURES_SPECS = [
    ("SC0", "crude_oil_price_state", "upstream_integrated", "domestic crude-oil main-continuous futures proxy"),
    ("FU0", "fuel_oil_price_state", "refining", "fuel-oil main-continuous futures proxy"),
    ("BU0", "bitumen_price_state", "refining", "bitumen main-continuous futures proxy"),
    ("LU0", "low_sulfur_fuel_oil_price_state", "refining", "low-sulfur fuel-oil main-continuous futures proxy"),
    ("PG0", "gas_liquid_price_state", "natural_gas_lpg", "LPG main-continuous futures proxy for gas/liquid-fuel state"),
]

EXPOSURE_FIELDS = [
    "upstream_exposure_share",
    "pipeline_storage_lng_exposure_share",
    "refining_chemical_exposure_share",
    "retail_trade_exposure_share",
    "oilfield_service_exposure_share",
    "oil_gas_business_exposure_score",
    "business_exposure_visible_date",
    "business_exposure_source",
    "business_exposure_review_status",
]


@dataclass(frozen=True)
class OilGasExternalStateResult:
    panel_path: Path
    manifest_path: Path
    row_count: int
    pit_usable_count: int
    status: str
    warning_count: int


@dataclass(frozen=True)
class OilGasResearchPanelResult:
    panel_path: Path
    manifest_path: Path
    row_count: int
    state_enriched_count: int
    exposure_enriched_count: int
    status: str


def collect_oil_gas_external_state(
    out_dir: Path = DEFAULT_OUT_DIR,
    start_date: str = "2021-01-01",
    end_date: str = "2026-05-31",
) -> OilGasExternalStateResult:
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    rows.extend(_collect_futures_state_rows(start_date, end_date, warnings))
    rows.extend(_derived_refining_spread_rows(rows))
    rows = sorted(rows, key=lambda item: (item["visible_date"], item["metric"], item["sub_industry"]))

    out_dir.mkdir(parents=True, exist_ok=True)
    panel_path = out_dir / "oil_gas_external_state.csv"
    manifest_path = out_dir / "collection_manifest.json"
    write_csv_rows(panel_path, STATE_FIELDS, rows)
    validation = validate_oil_gas_external_state(panel_path)
    write_json_file(
        manifest_path,
        {
            "dataset": "oil_gas_external_state_v58a",
            "panel": str(panel_path),
            "row_count": len(rows),
            "validation": validation,
            "sources": [f"akshare.futures_main_sina {symbol}" for symbol, *_rest in FUTURES_SPECS],
            "warnings": warnings,
            "pit_policy": "Daily futures rows are reduced to month-end state rows and assigned visible_date = next calendar day. This is preliminary research validation evidence only.",
            "limitations": [
                "Futures proxies are not official domestic spot prices, long-contract gas prices, product crack spreads or regulated pipeline tariff evidence.",
                "Refining spread is a normalized product-basket minus crude proxy, not a refinery-accounting margin.",
                "Pipeline tariff / policy state remains required before any pipeline-heavy formal candidate promotion.",
                "This state panel may open V5.8a Test-1 research validation, but it cannot support accepted-strategy or platform-replication promotion.",
            ],
            "required_research_metrics": REQUIRED_RESEARCH_METRICS,
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return OilGasExternalStateResult(
        panel_path=panel_path,
        manifest_path=manifest_path,
        row_count=len(rows),
        pit_usable_count=int(validation["pit_usable_count"]),
        status=str(validation["status"]),
        warning_count=len(warnings),
    )


def validate_oil_gas_external_state(path: Path) -> dict[str, Any]:
    rows = read_csv_rows(path)
    missing_required = []
    future_or_invalid = 0
    metric_counts: dict[str, int] = defaultdict(int)
    usable_metric_counts: dict[str, int] = defaultdict(int)
    pit_usable = 0
    for index, row in enumerate(rows, start=2):
        metric = str(row.get("metric") or "")
        if metric:
            metric_counts[metric] += 1
        for field in ["visible_date", "state_date", "metric", "source_publication_date"]:
            if not row.get(field):
                missing_required.append(f"line {index}: missing {field}")
        if row.get("visible_date") and row.get("source_publication_date"):
            if str(row["visible_date"])[:10] < str(row["source_publication_date"])[:10]:
                future_or_invalid += 1
        if str(row.get("pit_usable", "")).lower() == "true":
            pit_usable += 1
            if metric:
                usable_metric_counts[metric] += 1
    missing_usable_required_metrics = [metric for metric in REQUIRED_RESEARCH_METRICS if usable_metric_counts.get(metric, 0) == 0]
    status = "preliminary_research_validation_ready" if not missing_required and future_or_invalid == 0 and not missing_usable_required_metrics else "needs_review"
    return {
        "row_count": len(rows),
        "pit_usable_count": pit_usable,
        "metric_counts": dict(metric_counts),
        "usable_metric_counts": dict(usable_metric_counts),
        "missing_required": missing_required,
        "future_or_invalid_visible_dates": future_or_invalid,
        "missing_usable_required_metrics": missing_usable_required_metrics,
        "status": status,
        "formal_promotion_status": "blocked_until_official_spot_spread_tariff_and_business_exposure_sources_are_reviewed",
    }


def build_oil_gas_research_panel(
    panel_csv: Path,
    external_state_csv: Path,
    out_dir: Path = DEFAULT_PANEL_OUT_DIR,
    strategy_id: str = "oil_gas_ocf_dividend_cycle_probe_v58a",
) -> OilGasResearchPanelResult:
    panel_rows = read_csv_rows(panel_csv)
    state_by_trade_date = latest_visible_state_values(external_state_csv, [row.get("trade_date", "") for row in panel_rows])
    enriched_rows: list[dict[str, Any]] = []
    state_enriched_count = 0
    exposure_enriched_count = 0
    for row in panel_rows:
        enriched = dict(row)
        trade_date = str(row.get("trade_date") or "")[:10]
        state_values = state_by_trade_date.get(trade_date, {})
        if state_values:
            state_enriched_count += 1
        enriched.update(state_values)
        exposure = _business_exposure_proxy(row)
        if exposure:
            exposure_enriched_count += 1
        enriched.update(exposure)
        enriched_rows.append(enriched)

    out_dir.mkdir(parents=True, exist_ok=True)
    panel_path = out_dir / "panel.csv"
    manifest_path = out_dir / "collection_manifest.json"
    fieldnames = _merge_fieldnames(panel_rows, [*state_by_trade_date_fieldnames(state_by_trade_date), *EXPOSURE_FIELDS])
    write_csv_rows(panel_path, fieldnames, enriched_rows)
    state_coverage = state_enriched_count / len(enriched_rows) if enriched_rows else 0.0
    exposure_coverage = exposure_enriched_count / len(enriched_rows) if enriched_rows else 0.0
    status = "research_validation_ready" if state_coverage >= 0.8 and exposure_coverage >= 0.8 else "needs_review"
    write_json_file(
        manifest_path,
        {
            "dataset": "oil_gas_research_panel_v58a",
            "strategy_id": strategy_id,
            "source_panel": str(panel_csv),
            "external_state_csv": str(external_state_csv),
            "panel": str(panel_path),
            "row_count": len(enriched_rows),
            "date_count": len({row.get("trade_date") for row in enriched_rows if row.get("trade_date")}),
            "code_count": len({row.get("code") for row in enriched_rows if row.get("code")}),
            "state_enriched_count": state_enriched_count,
            "state_coverage": state_coverage,
            "exposure_enriched_count": exposure_enriched_count,
            "exposure_coverage": exposure_coverage,
            "status": status,
            "research_validation_permission": "Quant Agent may run Test-1 formal validation if status is research_validation_ready. Promotion remains blocked before official / reviewed source repair.",
            "limitations": [
                "Business exposure is a PIT JoinQuant industry-membership proxy, not reviewed annual-report segment evidence.",
                "External state uses preliminary futures proxies.",
                "Dividend attribution and real daily execution simulation are not part of this research panel.",
            ],
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return OilGasResearchPanelResult(
        panel_path=panel_path,
        manifest_path=manifest_path,
        row_count=len(enriched_rows),
        state_enriched_count=state_enriched_count,
        exposure_enriched_count=exposure_enriched_count,
        status=status,
    )


def latest_visible_state_values(panel_path: Path, trade_dates: Iterable[str]) -> dict[str, dict[str, str]]:
    rows = [row for row in read_csv_rows(panel_path) if str(row.get("pit_usable", "")).lower() == "true"]
    by_metric: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("metric") and row.get("visible_date") and row.get("value"):
            by_metric[str(row["metric"])].append(row)
    for metric_rows in by_metric.values():
        metric_rows.sort(key=lambda row: str(row["visible_date"])[:10])
    result: dict[str, dict[str, str]] = {}
    for trade_date in sorted({str(day)[:10] for day in trade_dates if day}):
        values: dict[str, str] = {}
        for metric, metric_rows in by_metric.items():
            visible = [row for row in metric_rows if str(row["visible_date"])[:10] <= trade_date]
            if visible:
                row = visible[-1]
                values[metric] = row["value"]
                values[f"{metric}_visible_date"] = str(row.get("visible_date", ""))[:10]
                values[f"{metric}_state_date"] = str(row.get("state_date", ""))[:10]
                values[f"{metric}_source"] = row.get("source_name", "")
        result[trade_date] = values
    return result


def state_by_trade_date_fieldnames(state_by_trade_date: dict[str, dict[str, str]]) -> list[str]:
    fields: list[str] = []
    for values in state_by_trade_date.values():
        for key in values:
            if key not in fields:
                fields.append(key)
    return fields


def _collect_futures_state_rows(start_date: str, end_date: str, warnings: list[str]) -> list[dict[str, Any]]:
    try:
        import akshare as ak
    except Exception as exc:  # pragma: no cover - optional dependency.
        raise RuntimeError("collecting oil/gas external state requires akshare") from exc

    rows: list[dict[str, Any]] = []
    for symbol, metric, sub_industry, notes in FUTURES_SPECS:
        try:
            df = ak.futures_main_sina(symbol=symbol, start_date=start_date.replace("-", ""), end_date=end_date.replace("-", ""))
        except Exception as exc:
            warnings.append(f"{symbol}: futures collection failed: {repr(exc)}")
            continue
        rows.extend(_month_end_futures_rows(df, symbol, metric, sub_industry, notes))
    return rows


def _month_end_futures_rows(df: Any, symbol: str, metric: str, sub_industry: str, notes: str) -> list[dict[str, Any]]:
    if df is None or getattr(df, "empty", True):
        return []
    latest_by_month: dict[str, dict[str, Any]] = {}
    for record in df.to_dict("records"):
        state_day = _parse_date(record.get("日期"))
        value = _to_float(record.get("收盘价"))
        if state_day is None or value is None or value <= 0:
            continue
        key = state_day.strftime("%Y-%m")
        if key not in latest_by_month or state_day > latest_by_month[key]["state_day"]:
            latest_by_month[key] = {"state_day": state_day, "value": value}
    rows = []
    for item in latest_by_month.values():
        state_day = item["state_day"]
        visible = state_day + timedelta(days=1)
        rows.append(
            _state_row(
                visible,
                state_day,
                "china_futures_market",
                sub_industry,
                metric,
                item["value"],
                "cny_per_ton_proxy",
                f"AkShare futures_main_sina {symbol}",
                "https://vip.stock.finance.sina.com.cn/quotes_service/view/qihuohangqing.html",
                visible,
                "preliminary_proxy",
                notes,
                pit_usable=True,
            )
        )
    return rows


def _derived_refining_spread_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_date = _rows_by_state_date(rows)
    result = []
    for state_day, values in sorted(by_date.items()):
        crude = values.get("crude_oil_price_state")
        products = [
            values.get("fuel_oil_price_state"),
            values.get("bitumen_price_state"),
            values.get("low_sulfur_fuel_oil_price_state"),
        ]
        product_values = [item for item in products if item is not None]
        if crude is None or len(product_values) < 2:
            continue
        product_basket = mean(product_values)
        spread_proxy = product_basket / crude - 1.0 if crude > 0 else None
        if spread_proxy is None:
            continue
        visible = state_day + timedelta(days=1)
        result.append(
            _state_row(
                visible,
                state_day,
                "china_futures_market",
                "refining",
                "refining_spread_proxy_state",
                spread_proxy,
                "product_basket_divided_by_crude_minus_1",
                "Derived from AkShare futures_main_sina FU0/BU0/LU0/SC0",
                "https://vip.stock.finance.sina.com.cn/quotes_service/view/qihuohangqing.html",
                visible,
                "preliminary_proxy",
                "Normalized proxy only; not a physical refining margin or crack spread.",
                pit_usable=True,
            )
        )
    return result


def _rows_by_state_date(rows: list[dict[str, Any]]) -> dict[date, dict[str, float]]:
    result: dict[date, dict[str, float]] = defaultdict(dict)
    for row in rows:
        state_day = _parse_date(row.get("state_date"))
        metric = str(row.get("metric") or "")
        value = _to_float(row.get("value"))
        if state_day is not None and metric and value is not None:
            result[state_day][metric] = value
    return result


def _business_exposure_proxy(row: dict[str, Any]) -> dict[str, str]:
    label = str(row.get("sub_industry") or "")
    mapping = {
        "integrated_oil_gas": (0.45, 0.10, 0.25, 0.15, 0.00),
        "fuel_refining": (0.05, 0.00, 0.80, 0.10, 0.00),
        "natural_gas_processing": (0.10, 0.70, 0.05, 0.10, 0.00),
        "oil_gas_distribution_other": (0.05, 0.35, 0.05, 0.45, 0.00),
    }
    if label not in mapping:
        return {}
    upstream, pipeline, refining, retail, oilfield_service = mapping[label]
    score = pipeline + 0.7 * retail + 0.5 * upstream - 0.4 * refining - 0.8 * oilfield_service
    trade_date = str(row.get("trade_date") or "")[:10]
    return {
        "upstream_exposure_share": _fmt(upstream),
        "pipeline_storage_lng_exposure_share": _fmt(pipeline),
        "refining_chemical_exposure_share": _fmt(refining),
        "retail_trade_exposure_share": _fmt(retail),
        "oilfield_service_exposure_share": _fmt(oilfield_service),
        "oil_gas_business_exposure_score": _fmt(score),
        "business_exposure_visible_date": trade_date,
        "business_exposure_source": "jqdatasdk.get_industry_stocks sub_industry proxy",
        "business_exposure_review_status": "jq_industry_proxy_needs_annual_report_review",
    }


def _state_row(
    visible_date: date,
    state_date: date,
    state_scope: str,
    sub_industry: str,
    metric: str,
    value: Any,
    unit: str,
    source_name: str,
    source_url: str,
    source_publication_date: date,
    review_status: str,
    notes: str,
    pit_usable: bool,
) -> dict[str, str]:
    return {
        "visible_date": visible_date.isoformat(),
        "state_date": state_date.isoformat(),
        "state_scope": state_scope,
        "sub_industry": sub_industry,
        "metric": metric,
        "value": _fmt(value),
        "unit": unit,
        "source_name": source_name,
        "source_url": source_url,
        "source_publication_date": source_publication_date.isoformat(),
        "pit_usable": str(pit_usable).lower(),
        "review_status": review_status,
        "notes": notes,
    }


def _merge_fieldnames(rows: list[dict[str, Any]], extra_fields: list[str]) -> list[str]:
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    for key in extra_fields:
        if key not in fieldnames:
            fieldnames.append(key)
    return fieldnames


def _parse_date(value: Any) -> date | None:
    if value in {None, ""}:
        return None
    if isinstance(value, date):
        return value
    if hasattr(value, "date"):
        return value.date()
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()


def _to_float(value: Any) -> float | None:
    if value in {None, "", "nan", "NaN", "None"}:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric) or math.isinf(numeric):
        return None
    return numeric


def _fmt(value: Any) -> str:
    numeric = _to_float(value)
    if numeric is None:
        return "" if value in {None, ""} else str(value)
    return f"{numeric:.10g}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-oil-gas-state")
    subparsers = parser.add_subparsers(dest="command", required=True)
    collect_parser = subparsers.add_parser("collect")
    collect_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    collect_parser.add_argument("--start-date", default="2021-01-01")
    collect_parser.add_argument("--end-date", default="2026-05-31")
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("csv_path", type=Path)
    build_parser = subparsers.add_parser("build-research-panel")
    build_parser.add_argument("panel", type=Path)
    build_parser.add_argument("external_state", type=Path)
    build_parser.add_argument("--out-dir", type=Path, default=DEFAULT_PANEL_OUT_DIR)
    build_parser.add_argument("--strategy-id", default="oil_gas_ocf_dividend_cycle_probe_v58a")
    args = parser.parse_args(argv)
    if args.command == "collect":
        print(collect_oil_gas_external_state(args.out_dir, args.start_date, args.end_date))
        return 0
    if args.command == "validate":
        print(validate_oil_gas_external_state(args.csv_path))
        return 0
    if args.command == "build-research-panel":
        print(build_oil_gas_research_panel(args.panel, args.external_state, args.out_dir, strategy_id=args.strategy_id))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
