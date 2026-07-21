from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.math_utils import compound, pearson, ranks, safe_median, to_float
from v5.paths import DEFAULT_PROCESSED_DIR
from v5.scoring import apply_value_trap_guard, score_rows


DEFAULT_PANEL = DEFAULT_PROCESSED_DIR / "gas_water_financial_evidence_v57" / "panel_with_direct_financial_evidence.csv"
DEFAULT_BENCHMARK = DEFAULT_PROCESSED_DIR / "gas_water_v57b_same_pool_equal_weight_benchmark.csv"
DEFAULT_OUT_DIR = DEFAULT_PROCESSED_DIR / "gas_water_external_state_v59"
DEFAULT_ENRICHED_OUT_DIR = DEFAULT_PROCESSED_DIR / "gas_water_state_enriched_panel_v59"
DEFAULT_VALIDATION_OUT_DIR = Path("validation_state_v59_gas_water")
DEFAULT_STRATEGY_ID = "gas_water_value_serviceability_state_diagnostic_v59"

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

REQUIRED_STATE_METRICS = [
    "sector_receivables_to_revenue_median",
    "sector_collection_cash_to_revenue_median",
    "sector_net_debt_to_assets_median",
    "same_pool_trailing_60d_return",
    "same_pool_trailing_60d_volatility",
    "same_pool_trailing_60d_drawdown",
]

FINANCIAL_STATE_SPECS = [
    (
        "sector_receivables_to_revenue_median",
        "direct_receivables_to_revenue",
        "ratio",
        "Higher values indicate collection pressure and local-fiscal payment risk.",
    ),
    (
        "sector_receivables_to_assets_median",
        "direct_receivables_to_assets",
        "ratio",
        "Balance-sheet receivables pressure proxy.",
    ),
    (
        "sector_collection_cash_to_revenue_median",
        "direct_collection_cash_to_revenue",
        "ratio",
        "Higher values indicate better cash collection.",
    ),
    (
        "sector_interest_bearing_debt_to_assets_median",
        "direct_interest_bearing_debt_to_assets",
        "ratio",
        "Interest-bearing debt pressure proxy.",
    ),
    (
        "sector_net_debt_to_assets_median",
        "direct_net_debt_to_assets",
        "ratio",
        "Net debt pressure proxy.",
    ),
    (
        "sector_dividend_yield_median",
        "dividend_yield",
        "percent",
        "Sector dividend support / high-dividend crowding proxy.",
    ),
]

MARKET_STATE_SPECS = [
    ("same_pool_trailing_60d_return", "return", "trailing same-pool benchmark return; uses dates strictly before rebalance"),
    ("same_pool_trailing_120d_return", "return", "trailing same-pool benchmark return; uses dates strictly before rebalance"),
    ("same_pool_trailing_60d_volatility", "daily_return_volatility", "trailing same-pool benchmark daily return volatility"),
    ("same_pool_trailing_60d_drawdown", "drawdown", "trailing same-pool benchmark max drawdown"),
]

STATE_FACTOR_CASES = {
    "v57b_value_serviceability_top10": ("composite", "", "higher_is_better"),
    "equal_weight_gas_water": ("equal_all", "", "higher_is_better"),
    "low_pb_safe_top10": ("single_factor", "low_price_to_book_safe", "lower_is_better"),
    "high_dividend_top10": ("single_factor", "dividend_yield", "higher_is_better"),
    "serviceability_top10": ("single_factor", "interest_coverage_safe", "higher_is_better"),
}


@dataclass(frozen=True)
class GasWaterExternalStateResult:
    panel_path: Path
    manifest_path: Path
    row_count: int
    status: str
    pit_usable_count: int


@dataclass(frozen=True)
class GasWaterStateEnrichedPanelResult:
    panel_path: Path
    manifest_path: Path
    row_count: int
    state_enriched_count: int
    status: str


@dataclass(frozen=True)
class GasWaterStateValidationResult:
    summary_path: Path
    report_path: Path
    status: str


def build_gas_water_external_state_panel(
    panel_csv: Path = DEFAULT_PANEL,
    benchmark_csv: Path = DEFAULT_BENCHMARK,
    out_dir: Path = DEFAULT_OUT_DIR,
    include_official_proxies: bool = False,
) -> GasWaterExternalStateResult:
    panel_rows = read_csv_rows(panel_csv)
    benchmark_rows = read_csv_rows(benchmark_csv)
    by_date = _group_by_date(panel_rows)
    benchmark_series = _benchmark_series(benchmark_rows)

    rows: list[dict[str, Any]] = []
    for trade_date in sorted(by_date):
        date_rows = by_date[trade_date]
        rows.extend(_financial_state_rows(trade_date, date_rows))
        rows.extend(_market_state_rows(trade_date, benchmark_series))
    official_warnings: list[str] = []
    if include_official_proxies:
        rows.extend(_official_proxy_state_rows(sorted(by_date), official_warnings))

    rows = sorted(rows, key=lambda item: (item["visible_date"], item["metric"]))
    out_dir.mkdir(parents=True, exist_ok=True)
    panel_path = out_dir / "gas_water_external_state.csv"
    manifest_path = out_dir / "collection_manifest.json"
    write_csv_rows(panel_path, STATE_FIELDS, rows)
    validation = validate_gas_water_external_state(panel_path, sorted(by_date))
    write_json_file(
        manifest_path,
        {
            "dataset": "gas_water_external_state_v59",
            "panel": str(panel_path),
            "source_panel": str(panel_csv),
            "benchmark_csv": str(benchmark_csv),
            "row_count": len(rows),
            "validation": validation,
            "pit_policy": "Financial state rows are cross-sectional aggregates from the already PIT-audited gas/water panel. Market state rows use benchmark prices strictly before the rebalance date.",
            "limitations": [
                "This is a minimum viable ex-ante state proxy panel, not a final official operating-state dataset.",
                "Gas procurement cost and water tariff/pass-through variables still require external source collection before strategy promotion.",
                "Research reports remain hypothesis evidence only; no report-only text is used as a scored factor.",
            ],
            "official_proxy_status": "included" if include_official_proxies else "not_requested",
            "official_proxy_warnings": official_warnings,
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return GasWaterExternalStateResult(
        panel_path=panel_path,
        manifest_path=manifest_path,
        row_count=len(rows),
        status=str(validation["status"]),
        pit_usable_count=int(validation["pit_usable_count"]),
    )


def validate_gas_water_external_state(path: Path, expected_trade_dates: list[str] | None = None) -> dict[str, Any]:
    rows = read_csv_rows(path)
    missing_required = []
    future_or_invalid = 0
    pit_usable = 0
    usable_by_date: dict[str, set[str]] = defaultdict(set)
    for index, row in enumerate(rows, start=2):
        for field in ["visible_date", "state_date", "metric", "source_publication_date"]:
            if not row.get(field):
                missing_required.append(f"line {index}: missing {field}")
        visible_date = str(row.get("visible_date") or "")[:10]
        publication_date = str(row.get("source_publication_date") or "")[:10]
        if visible_date and publication_date and visible_date < publication_date:
            future_or_invalid += 1
        if str(row.get("pit_usable", "")).lower() == "true":
            pit_usable += 1
            usable_by_date[visible_date].add(str(row.get("metric") or ""))
    expected = expected_trade_dates or sorted(usable_by_date)
    required_by_date = {
        trade_date: [metric for metric in REQUIRED_STATE_METRICS if metric not in usable_by_date.get(trade_date, set())]
        for trade_date in expected
    }
    missing_required_metric_dates = {date: missing for date, missing in required_by_date.items() if missing}
    covered_dates = len([date for date in expected if not required_by_date.get(date)])
    coverage_ratio = covered_dates / len(expected) if expected else 0.0
    dates_2026 = [date for date in expected if date.startswith("2026-")]
    missing_2026 = {date: missing_required_metric_dates[date] for date in dates_2026 if date in missing_required_metric_dates}
    status = (
        "state_validation_ready"
        if not missing_required
        and future_or_invalid == 0
        and coverage_ratio >= 0.8
        and not missing_2026
        else "needs_review"
    )
    return {
        "row_count": len(rows),
        "pit_usable_count": pit_usable,
        "required_state_metrics": REQUIRED_STATE_METRICS,
        "expected_trade_date_count": len(expected),
        "fully_covered_trade_dates": covered_dates,
        "coverage_ratio": coverage_ratio,
        "missing_required": missing_required,
        "future_or_invalid_visible_dates": future_or_invalid,
        "missing_required_metric_dates": missing_required_metric_dates,
        "missing_2026_required_metric_dates": missing_2026,
        "status": status,
        "promotion_policy": "May start Quant state-bucket validation when status is state_validation_ready. Engineering handoff still requires stable validation evidence.",
    }


def build_gas_water_state_enriched_panel(
    panel_csv: Path = DEFAULT_PANEL,
    state_csv: Path = DEFAULT_OUT_DIR / "gas_water_external_state.csv",
    out_dir: Path = DEFAULT_ENRICHED_OUT_DIR,
    strategy_id: str = DEFAULT_STRATEGY_ID,
) -> GasWaterStateEnrichedPanelResult:
    panel_rows = read_csv_rows(panel_csv)
    state_by_date = _state_values_by_visible_date(read_csv_rows(state_csv))
    enriched_rows: list[dict[str, Any]] = []
    state_enriched_count = 0
    for row in panel_rows:
        item = dict(row)
        trade_date = str(row.get("trade_date") or "")[:10]
        state_values = state_by_date.get(trade_date, {})
        if _has_required_state_values(state_values):
            state_enriched_count += 1
        item.update(state_values)
        enriched_rows.append(item)

    out_dir.mkdir(parents=True, exist_ok=True)
    panel_path = out_dir / "panel_with_external_state.csv"
    manifest_path = out_dir / "collection_manifest.json"
    fieldnames = _merge_fieldnames(panel_rows, state_by_date)
    write_csv_rows(panel_path, fieldnames, enriched_rows)
    coverage_ratio = state_enriched_count / len(enriched_rows) if enriched_rows else 0.0
    status = "state_validation_ready" if coverage_ratio >= 0.8 else "needs_review"
    write_json_file(
        manifest_path,
        {
            "dataset": "gas_water_state_enriched_panel_v59",
            "strategy_id": strategy_id,
            "source_panel": str(panel_csv),
            "state_csv": str(state_csv),
            "panel": str(panel_path),
            "row_count": len(enriched_rows),
            "state_enriched_count": state_enriched_count,
            "state_coverage_ratio": coverage_ratio,
            "status": status,
            "next_gate": "run_gas_water_state_bucket_validation" if status == "state_validation_ready" else "repair_state_coverage",
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return GasWaterStateEnrichedPanelResult(
        panel_path=panel_path,
        manifest_path=manifest_path,
        row_count=len(enriched_rows),
        state_enriched_count=state_enriched_count,
        status=status,
    )


def run_gas_water_state_bucket_validation(
    panel_path: Path = DEFAULT_ENRICHED_OUT_DIR / "panel_with_external_state.csv",
    out_dir: Path = DEFAULT_VALIDATION_OUT_DIR,
    strategy_id: str = DEFAULT_STRATEGY_ID,
    state_metric: str = "sector_receivables_to_revenue_median",
    selection_count: int = 10,
    min_history: int = 4,
) -> GasWaterStateValidationResult:
    rows = read_csv_rows(panel_path)
    by_date = _group_by_date(rows)
    state_by_date = _state_by_date(by_date, state_metric)
    if not state_by_date:
        raise RuntimeError(f"no usable state values found for metric={state_metric}")

    out = out_dir / strategy_id / f"state_bucket_{state_metric}"
    out.mkdir(parents=True, exist_ok=True)
    coverage_rows = _coverage_rows(by_date, state_by_date, state_metric)
    bucket_rows = _rolling_bucket_by_date(state_by_date, min_history)
    bucket_tests = _state_bucket_tests(by_date, bucket_rows, selection_count)
    conditioned_ic = _state_conditioned_factor_ic(by_date, bucket_rows)
    yearly_rows = _yearly_state_summary(by_date, bucket_rows, selection_count)
    summary = _state_validation_summary(
        panel_path=panel_path,
        state_metric=state_metric,
        coverage_rows=coverage_rows,
        bucket_rows=bucket_rows,
        bucket_tests=bucket_tests,
        conditioned_ic=conditioned_ic,
        yearly_rows=yearly_rows,
        strategy_id=strategy_id,
    )
    write_csv_rows(out / "state_coverage.csv", coverage_rows[0].keys(), coverage_rows)
    write_csv_rows(out / "rolling_state_buckets.csv", bucket_rows[0].keys(), bucket_rows)
    write_csv_rows(out / "state_bucket_tests.csv", bucket_tests[0].keys(), bucket_tests)
    write_csv_rows(out / "state_conditioned_factor_ic.csv", conditioned_ic[0].keys(), conditioned_ic)
    write_csv_rows(out / "yearly_state_summary.csv", yearly_rows[0].keys(), yearly_rows)
    summary_path = out / "state_bucket_validation_summary.json"
    report_path = out / "state_bucket_validation_report.md"
    write_json_file(summary_path, summary)
    _write_state_validation_report(report_path, summary)
    return GasWaterStateValidationResult(
        summary_path=summary_path,
        report_path=report_path,
        status=str(summary["status"]),
    )


def _financial_state_rows(trade_date: str, rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    source_publication_date = _latest_visible_date(rows, trade_date)
    if source_publication_date is None:
        return result
    for metric, source_field, unit, notes in FINANCIAL_STATE_SPECS:
        values = [value for value in (to_float(row.get(source_field)) for row in rows) if value is not None]
        value = safe_median(values)
        if value is None:
            continue
        result.append(
            _state_row(
                visible_date=trade_date,
                state_date=trade_date,
                metric=metric,
                value=value,
                unit=unit,
                source_name="derived_from_pit_gas_water_financial_panel",
                source_publication_date=source_publication_date,
                review_status="derived_pit_proxy",
                notes=notes,
            )
        )
    return result


def _market_state_rows(trade_date: str, benchmark_series: list[dict[str, Any]]) -> list[dict[str, Any]]:
    history = [row for row in benchmark_series if row["date"] < trade_date]
    if len(history) < 2:
        return []
    result: list[dict[str, Any]] = []
    metrics = {
        "same_pool_trailing_60d_return": _trailing_return(history, 60),
        "same_pool_trailing_120d_return": _trailing_return(history, 120),
        "same_pool_trailing_60d_volatility": _trailing_volatility(history, 60),
        "same_pool_trailing_60d_drawdown": _trailing_drawdown(history, 60),
    }
    state_date = str(history[-1]["date"])
    for metric, unit, notes in MARKET_STATE_SPECS:
        value = metrics.get(metric)
        if value is None:
            continue
        result.append(
            _state_row(
                visible_date=trade_date,
                state_date=state_date,
                metric=metric,
                value=value,
                unit=unit,
                source_name="derived_from_same_pool_equal_weight_benchmark",
                source_publication_date=trade_date,
                review_status="market_price_pit_proxy",
                notes=notes,
            )
        )
    return result


def _official_proxy_state_rows(trade_dates: list[str], warnings: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    qyspjg = _try_collect_qyspjg(warnings)
    shibor = _try_collect_shibor(warnings)
    lpr = _try_collect_lpr(warnings)
    for trade_date in trade_dates:
        rows.extend(_latest_qyspjg_rows(trade_date, qyspjg))
        rows.extend(_latest_shibor_rows(trade_date, shibor))
        rows.extend(_latest_lpr_rows(trade_date, lpr))
    return rows


def _try_collect_qyspjg(warnings: list[str]) -> list[dict[str, Any]]:
    try:
        import akshare as ak

        df = ak.macro_china_qyspjg()
    except Exception as exc:  # pragma: no cover - optional network dependency.
        warnings.append(f"macro_china_qyspjg failed: {type(exc).__name__}")
        return []
    rows: list[dict[str, Any]] = []
    for item in df.to_dict(orient="records"):
        month = _parse_chinese_month(str(item.get("月份") or ""))
        if month is None:
            continue
        visible = _next_month_day(month, 25)
        rows.append(
            {
                "visible_date": visible.isoformat(),
                "state_date": month.isoformat(),
                "nbs_total_price_index": to_float(item.get("总指数-指数值")),
                "nbs_total_price_yoy": to_float(item.get("总指数-同比增长")),
                "nbs_mineral_price_index": to_float(item.get("矿产品-指数值")),
                "nbs_mineral_price_yoy": to_float(item.get("矿产品-同比增长")),
                "nbs_coal_oil_power_index": to_float(item.get("煤油电-指数值")),
                "nbs_coal_oil_power_yoy": to_float(item.get("煤油电-同比增长")),
                "source": "akshare.macro_china_qyspjg",
            }
        )
    return rows


def _try_collect_shibor(warnings: list[str]) -> list[dict[str, Any]]:
    try:
        import akshare as ak

        df = ak.macro_china_shibor_all()
    except Exception as exc:  # pragma: no cover - optional network dependency.
        warnings.append(f"macro_china_shibor_all failed: {type(exc).__name__}")
        return []
    rows: list[dict[str, Any]] = []
    for item in df.to_dict(orient="records"):
        day = str(item.get("日期") or "")[:10]
        if not day:
            continue
        rows.append(
            {
                "visible_date": day,
                "state_date": day,
                "shibor_3m": to_float(item.get("3M-定价")),
                "shibor_1y": to_float(item.get("1Y-定价")),
                "source": "akshare.macro_china_shibor_all",
            }
        )
    return sorted(rows, key=lambda item: item["visible_date"])


def _try_collect_lpr(warnings: list[str]) -> list[dict[str, Any]]:
    try:
        import akshare as ak

        df = ak.macro_china_lpr()
    except Exception as exc:  # pragma: no cover - optional network dependency.
        warnings.append(f"macro_china_lpr failed: {type(exc).__name__}")
        return []
    rows: list[dict[str, Any]] = []
    for item in df.to_dict(orient="records"):
        day = str(item.get("TRADE_DATE") or "")[:10]
        if not day:
            continue
        rows.append(
            {
                "visible_date": day,
                "state_date": day,
                "lpr_1y": to_float(item.get("LPR1Y")),
                "lpr_5y": to_float(item.get("LPR5Y")),
                "source": "akshare.macro_china_lpr",
            }
        )
    return sorted(rows, key=lambda item: item["visible_date"])


def _latest_qyspjg_rows(trade_date: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest = _latest_visible_record(trade_date, rows)
    if not latest:
        return []
    result = []
    specs = [
        ("nbs_total_price_yoy", "percent", "NBS production-material total price YoY; broad cost/inflation proxy."),
        ("nbs_mineral_price_yoy", "percent", "NBS mineral product price YoY; upstream material cost proxy."),
        ("nbs_coal_oil_power_yoy", "percent", "NBS coal/oil/power price YoY; fuel and energy cost pressure proxy."),
    ]
    for metric, unit, notes in specs:
        value = latest.get(metric)
        if value is None:
            continue
        result.append(
            _state_row(
                visible_date=trade_date,
                state_date=str(latest["state_date"]),
                metric=metric,
                value=float(value),
                unit=unit,
                source_name=str(latest["source"]),
                source_publication_date=str(latest["visible_date"]),
                review_status="official_proxy_conservative_visible_date",
                notes=notes,
            )
        )
    return result


def _latest_shibor_rows(trade_date: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest = _latest_visible_record(trade_date, rows, strictly_before=True)
    if not latest:
        return []
    history = [row for row in rows if str(row.get("visible_date")) < trade_date and row.get("shibor_3m") is not None]
    result = []
    for metric, unit, notes in [
        ("shibor_3m", "percent", "3M Shibor level; financing pressure proxy."),
        ("shibor_1y", "percent", "1Y Shibor level; financing pressure proxy."),
    ]:
        value = latest.get(metric)
        if value is not None:
            result.append(
                _state_row(
                    visible_date=trade_date,
                    state_date=str(latest["state_date"]),
                    metric=metric,
                    value=float(value),
                    unit=unit,
                    source_name=str(latest["source"]),
                    source_publication_date=str(latest["visible_date"]),
                    review_status="official_market_rate",
                    notes=notes,
                )
            )
    if len(history) >= 60:
        current = to_float(history[-1].get("shibor_3m"))
        prior = to_float(history[-60].get("shibor_3m"))
        if current is not None and prior is not None:
            result.append(
                _state_row(
                    visible_date=trade_date,
                    state_date=str(history[-1]["state_date"]),
                    metric="shibor_3m_60d_change",
                    value=current - prior,
                    unit="percentage_point",
                    source_name=str(history[-1]["source"]),
                    source_publication_date=str(history[-1]["visible_date"]),
                    review_status="official_market_rate",
                    notes="3M Shibor 60-observation change; financing-pressure change proxy.",
                )
            )
    return result


def _latest_lpr_rows(trade_date: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest = _latest_visible_record(trade_date, rows)
    if not latest:
        return []
    result = []
    for metric, unit, notes in [
        ("lpr_1y", "percent", "1Y LPR level; broad credit-cost proxy."),
        ("lpr_5y", "percent", "5Y LPR level; long-duration financing proxy."),
    ]:
        value = latest.get(metric)
        if value is not None:
            result.append(
                _state_row(
                    visible_date=trade_date,
                    state_date=str(latest["state_date"]),
                    metric=metric,
                    value=float(value),
                    unit=unit,
                    source_name=str(latest["source"]),
                    source_publication_date=str(latest["visible_date"]),
                    review_status="official_market_rate",
                    notes=notes,
                )
            )
    return result


def _latest_visible_record(trade_date: str, rows: list[dict[str, Any]], strictly_before: bool = False) -> dict[str, Any] | None:
    if strictly_before:
        candidates = [row for row in rows if str(row.get("visible_date") or "") < trade_date]
    else:
        candidates = [row for row in rows if str(row.get("visible_date") or "") <= trade_date]
    return candidates[-1] if candidates else None


def _parse_chinese_month(value: str) -> date | None:
    import re

    match = re.search(r"(\d{4})年(\d{1,2})月", value)
    if not match:
        return None
    return date(int(match.group(1)), int(match.group(2)), 1)


def _next_month_day(month: date, day: int) -> date:
    year = month.year + (1 if month.month == 12 else 0)
    next_month = 1 if month.month == 12 else month.month + 1
    return date(year, next_month, day)


def _state_row(
    *,
    visible_date: str,
    state_date: str,
    metric: str,
    value: float,
    unit: str,
    source_name: str,
    source_publication_date: str,
    review_status: str,
    notes: str,
) -> dict[str, Any]:
    pit_usable = bool(source_publication_date <= visible_date)
    return {
        "visible_date": visible_date,
        "state_date": state_date,
        "state_scope": "sector",
        "sub_industry": "gas_water_operators",
        "metric": metric,
        "value": value,
        "unit": unit,
        "source_name": source_name,
        "source_url": "",
        "source_publication_date": source_publication_date,
        "pit_usable": str(pit_usable).lower(),
        "review_status": review_status,
        "notes": notes,
    }


def _group_by_date(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    by_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        trade_date = str(row.get("trade_date") or "")[:10]
        if trade_date:
            by_date[trade_date].append(row)
    return dict(by_date)


def _latest_visible_date(rows: list[dict[str, str]], trade_date: str) -> str | None:
    candidates = []
    for row in rows:
        for field in ["gas_water_financial_evidence_visible_date", "gas_water_visible_date", "factor_visible_date", "notice_date", "announce_date"]:
            value = str(row.get(field) or "")[:10]
            if value and value <= trade_date:
                candidates.append(value)
    return max(candidates) if candidates else None


def _benchmark_series(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    series = []
    previous_close = None
    for row in sorted(rows, key=lambda item: str(item.get("date") or "")):
        date_value = str(row.get("date") or "")[:10]
        close = to_float(row.get("close"))
        if not date_value or close is None:
            continue
        ret = None if previous_close in (None, 0) else close / previous_close - 1.0
        series.append({"date": date_value, "close": close, "return": ret})
        previous_close = close
    return series


def _trailing_return(history: list[dict[str, Any]], window: int) -> float | None:
    current = history[-1]["close"] if history else None
    if current is None or len(history) < 2:
        return None
    lookback = history[-min(window, len(history))]["close"]
    if not lookback:
        return None
    return float(current) / float(lookback) - 1.0


def _trailing_volatility(history: list[dict[str, Any]], window: int) -> float | None:
    returns = [row["return"] for row in history[-window:] if row.get("return") is not None]
    if len(returns) < 20:
        return None
    avg = mean(returns)
    variance = sum((ret - avg) ** 2 for ret in returns) / max(1, len(returns) - 1)
    return math.sqrt(variance)


def _trailing_drawdown(history: list[dict[str, Any]], window: int) -> float | None:
    closes = [float(row["close"]) for row in history[-window:] if row.get("close") is not None]
    if len(closes) < 20:
        return None
    peak = closes[0]
    worst = 0.0
    for close in closes:
        peak = max(peak, close)
        if peak:
            worst = min(worst, close / peak - 1.0)
    return worst


def _state_values_by_visible_date(rows: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    by_date: dict[str, dict[str, Any]] = defaultdict(dict)
    for row in rows:
        if str(row.get("pit_usable", "")).lower() != "true":
            continue
        date_value = str(row.get("visible_date") or "")[:10]
        metric = str(row.get("metric") or "")
        value = to_float(row.get("value"))
        if not date_value or not metric or value is None:
            continue
        by_date[date_value][metric] = value
        by_date[date_value][f"{metric}_visible_date"] = date_value
    return dict(by_date)


def _has_required_state_values(values: dict[str, Any]) -> bool:
    return all(metric in values for metric in REQUIRED_STATE_METRICS)


def _merge_fieldnames(rows: list[dict[str, str]], state_by_date: dict[str, dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for row in rows:
        for key in row:
            if key not in names:
                names.append(key)
    for values in state_by_date.values():
        for key in values:
            if key not in names:
                names.append(key)
    return names


def _state_by_date(by_date: dict[str, list[dict[str, str]]], metric: str) -> dict[str, float]:
    result = {}
    for trade_date, rows in by_date.items():
        values = [value for value in (to_float(row.get(metric)) for row in rows) if value is not None]
        if values:
            result[trade_date] = values[0]
    return result


def _coverage_rows(by_date: dict[str, list[dict[str, str]]], state_by_date: dict[str, float], metric: str) -> list[dict[str, Any]]:
    return [
        {
            "trade_date": trade_date,
            "panel_rows": len(rows),
            "metric": metric,
            "has_state": str(trade_date in state_by_date).lower(),
            "state_value": state_by_date.get(trade_date),
        }
        for trade_date, rows in sorted(by_date.items())
    ]


def _rolling_bucket_by_date(state_by_date: dict[str, float], min_history: int) -> list[dict[str, Any]]:
    history: list[float] = []
    rows: list[dict[str, Any]] = []
    for trade_date, value in sorted(state_by_date.items()):
        bucket = _expanding_bucket(history, value, min_history)
        rows.append(
            {
                "trade_date": trade_date,
                "state_value": value,
                "expanding_bucket": bucket,
                "history_count": len(history),
            }
        )
        history.append(value)
    return rows


def _state_bucket_tests(
    by_date: dict[str, list[dict[str, str]]],
    bucket_rows: list[dict[str, Any]],
    selection_count: int,
) -> list[dict[str, Any]]:
    bucket_by_date = {row["trade_date"]: row["expanding_bucket"] for row in bucket_rows}
    result: list[dict[str, Any]] = []
    for bucket in ["warmup", "low", "mid", "high", "all"]:
        dates = [trade_date for trade_date in sorted(by_date) if bucket == "all" or bucket_by_date.get(trade_date) == bucket]
        for case_name in STATE_FACTOR_CASES:
            returns = [_case_return(by_date[trade_date], case_name, selection_count) for trade_date in dates]
            usable = [value for value in returns if value is not None]
            result.append(
                {
                    "bucket": bucket,
                    "case": case_name,
                    "periods": len(usable),
                    "cum_return": compound(usable),
                    "mean_return": mean(usable) if usable else None,
                    "positive_ratio": _positive_ratio(usable),
                }
            )
    return result


def _state_conditioned_factor_ic(by_date: dict[str, list[dict[str, str]]], bucket_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bucket_by_date = {row["trade_date"]: row["expanding_bucket"] for row in bucket_rows}
    factor_specs = {
        "low_price_to_book_safe": "lower_is_better",
        "dividend_yield": "higher_is_better",
        "interest_coverage_safe": "higher_is_better",
        "debt_pressure_safe": "lower_is_better",
        "capex_burden_safe": "lower_is_better",
    }
    result: list[dict[str, Any]] = []
    for bucket in ["warmup", "low", "mid", "high", "all"]:
        dates = [trade_date for trade_date in sorted(by_date) if bucket == "all" or bucket_by_date.get(trade_date) == bucket]
        for factor, direction in factor_specs.items():
            ic_values: list[float] = []
            rank_ic_values: list[float] = []
            observations = 0
            for trade_date in dates:
                pairs = []
                for row in by_date[trade_date]:
                    factor_value = to_float(row.get(factor))
                    ret = to_float(row.get("future_return") or row.get("total_return"))
                    if factor_value is None or ret is None:
                        continue
                    adjusted = -factor_value if direction == "lower_is_better" else factor_value
                    pairs.append((adjusted, ret))
                    observations += 1
                if len(pairs) < 3:
                    continue
                x = [item[0] for item in pairs]
                y = [item[1] for item in pairs]
                ic = pearson(x, y)
                rank_ic = pearson(ranks(x), ranks(y))
                if ic is not None:
                    ic_values.append(ic)
                if rank_ic is not None:
                    rank_ic_values.append(rank_ic)
            result.append(
                {
                    "bucket": bucket,
                    "factor": factor,
                    "observations": observations,
                    "dates": len(ic_values),
                    "mean_ic": mean(ic_values) if ic_values else None,
                    "mean_rankic": mean(rank_ic_values) if rank_ic_values else None,
                    "positive_ic_ratio": _positive_ratio(ic_values),
                }
            )
    return result


def _yearly_state_summary(
    by_date: dict[str, list[dict[str, str]]],
    bucket_rows: list[dict[str, Any]],
    selection_count: int,
) -> list[dict[str, Any]]:
    bucket_by_date = {row["trade_date"]: row["expanding_bucket"] for row in bucket_rows}
    by_year: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    bucket_notes: dict[str, list[str]] = defaultdict(list)
    for trade_date, rows in by_date.items():
        year = trade_date[:4]
        bucket_notes[year].append(bucket_by_date.get(trade_date, "missing"))
        for case_name in STATE_FACTOR_CASES:
            ret = _case_return(rows, case_name, selection_count)
            if ret is not None:
                by_year[year][case_name].append(ret)
    result = []
    for year, cases in sorted(by_year.items()):
        result.append(
            {
                "year": year,
                "buckets": ";".join(bucket_notes[year]),
                "v57b_cum_return": compound(cases.get("v57b_value_serviceability_top10", [])),
                "equal_weight_cum_return": compound(cases.get("equal_weight_gas_water", [])),
                "low_pb_cum_return": compound(cases.get("low_pb_safe_top10", [])),
                "high_dividend_cum_return": compound(cases.get("high_dividend_top10", [])),
                "serviceability_cum_return": compound(cases.get("serviceability_top10", [])),
            }
        )
    return result


def _case_return(rows: list[dict[str, str]], case_name: str, selection_count: int) -> float | None:
    mode, factor, direction = STATE_FACTOR_CASES[case_name]
    if mode == "equal_all":
        selected = rows
    elif mode == "single_factor":
        ranked = [row for row in rows if to_float(row.get(factor)) is not None]
        ranked = sorted(ranked, key=lambda row: to_float(row.get(factor)) or 0.0, reverse=direction == "higher_is_better")
        selected = ranked[:selection_count]
    else:
        raw = _v57b_scoring_raw(selection_count)
        scored, _used = score_rows(raw, rows)
        selected = sorted(apply_value_trap_guard(raw, scored), key=lambda item: item["score"], reverse=True)[:selection_count]
    returns = [to_float(row.get("future_return") or row.get("total_return")) for row in selected]
    usable = [value for value in returns if value is not None]
    return mean(usable) if usable else None


def _v57b_scoring_raw(selection_count: int) -> dict[str, Any]:
    factors = [
        ("low_price_to_book_safe", "lower_is_better"),
        ("dividend_yield", "higher_is_better"),
        ("interest_coverage_safe", "higher_is_better"),
        ("debt_pressure_safe", "lower_is_better"),
        ("capex_burden_safe", "lower_is_better"),
    ]
    return {
        "signals": {
            "factors": [{"name": name, "direction": direction} for name, direction in factors],
            "scoring": {
                "method": "weighted_composite",
                "weights": {
                    "low_price_to_book_safe": 0.35,
                    "dividend_yield": 0.2,
                    "interest_coverage_safe": 0.2,
                    "debt_pressure_safe": 0.15,
                    "capex_burden_safe": 0.1,
                },
                "min_factor_count": 4,
            },
        },
        "portfolio": {"selection_count": selection_count},
    }


def _state_validation_summary(
    *,
    panel_path: Path,
    state_metric: str,
    coverage_rows: list[dict[str, Any]],
    bucket_rows: list[dict[str, Any]],
    bucket_tests: list[dict[str, Any]],
    conditioned_ic: list[dict[str, Any]],
    yearly_rows: list[dict[str, Any]],
    strategy_id: str,
) -> dict[str, Any]:
    covered = sum(1 for row in coverage_rows if row["has_state"] == "true")
    total = len(coverage_rows)
    all_cases = [row for row in bucket_tests if row["bucket"] == "all"]
    year_2026 = [row for row in yearly_rows if row["year"] == "2026"]
    status = "state_bucket_validation_completed_not_acceptance" if total and covered / total >= 0.8 else "needs_review"
    return {
        "strategy_id": strategy_id,
        "panel": str(panel_path),
        "state_metric": state_metric,
        "status": status,
        "coverage": {
            "state_covered_dates": covered,
            "panel_dates": total,
            "coverage_ratio": covered / total if total else 0.0,
        },
        "all_bucket_cases": all_cases,
        "year_2026": year_2026,
        "bucket_rows": bucket_rows,
        "governance": "State bucket validation is diagnostic evidence only. It does not promote gas/water to Engineering without PM approval.",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }


def _write_state_validation_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        f"# Gas / Water State Bucket Validation: {summary['state_metric']}",
        "",
        f"Status: `{summary['status']}`",
        "",
        "## Coverage",
        "",
        f"- Covered dates: `{summary['coverage']['state_covered_dates']}` / `{summary['coverage']['panel_dates']}`",
        f"- Coverage ratio: `{summary['coverage']['coverage_ratio']:.2%}`",
        "",
        "## All-Bucket Cases",
        "",
        "| Case | Periods | Cumulative Return | Positive Ratio |",
        "|---|---:|---:|---:|",
    ]
    for row in summary["all_bucket_cases"]:
        lines.append(
            f"| `{row['case']}` | {row['periods']} | {_fmt_pct(row['cum_return'])} | {_fmt_pct(row['positive_ratio'])} |"
        )
    lines.extend(["", "## 2026", ""])
    for row in summary["year_2026"]:
        lines.append(
            f"- Buckets `{row['buckets']}`; V57b {_fmt_pct(row['v57b_cum_return'])}; "
            f"equal-weight {_fmt_pct(row['equal_weight_cum_return'])}; low-PB {_fmt_pct(row['low_pb_cum_return'])}."
        )
    lines.extend(
        [
            "",
            "## PM Note",
            "",
            "This opens Quant state validation. It is not an Engineering handoff and not strategy acceptance.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _expanding_bucket(history: list[float], value: float, min_history: int) -> str:
    if len(history) < min_history:
        return "warmup"
    ordered = sorted(history)
    low_cut = ordered[int((len(ordered) - 1) * 0.33)]
    high_cut = ordered[int((len(ordered) - 1) * 0.67)]
    if value <= low_cut:
        return "low"
    if value >= high_cut:
        return "high"
    return "mid"


def _positive_ratio(values: list[float]) -> float | None:
    return sum(1 for value in values if value > 0) / len(values) if values else None


def _fmt_pct(value: Any) -> str:
    parsed = to_float(value)
    return "" if parsed is None else f"{parsed:.2%}"
