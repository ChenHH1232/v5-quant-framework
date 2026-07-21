from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from v5.engine import load_spec
from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.math_utils import compound, fmt_float, quantile, to_float
from v5.paths import DEFAULT_PROCESSED_DIR
from v5.scoring import apply_value_trap_guard, score_rows


DEFAULT_PANEL = DEFAULT_PROCESSED_DIR / "home_appliances_state_gate_v5a5c" / "panel_with_home_appliances_state_gate.csv"
DEFAULT_SPEC = Path("examples/home_appliances_ocf_quality_v5a5c_strategy.json")
DEFAULT_OUT_DIR = Path("validation_state_v5a5c_home_appliances")
DEFAULT_STRATEGY_ID = "home_appliances_ocf_quality_v5a5c"

STATE_METRICS = [
    "external_real_estate_climate_index",
    "external_china_exports_yoy",
    "external_commodity_price_index",
    "external_producer_goods_total_yoy",
    "external_mineral_goods_yoy",
    "external_energy_goods_yoy",
    "sector_capex_burden_median",
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
]


@dataclass(frozen=True)
class HomeAppliancesStateDiagnosticResult:
    summary_json: Path
    bucket_csv: Path
    report_md: Path
    status: str


def run_home_appliances_state_diagnostic(
    spec_path: Path = DEFAULT_SPEC,
    panel_csv: Path = DEFAULT_PANEL,
    out_dir: Path = DEFAULT_OUT_DIR,
    strategy_id: str = DEFAULT_STRATEGY_ID,
    selection_count: int | None = None,
    min_history: int = 4,
) -> HomeAppliancesStateDiagnosticResult:
    spec = load_spec(spec_path)
    raw = spec.raw
    count = selection_count or int(raw.get("portfolio", {}).get("selection_count", 10))
    rows = read_csv_rows(panel_csv)
    by_date = _group_by_date(rows)
    selected_by_date = _selected_returns_by_date(by_date, raw, count)
    state_by_date = _state_values_by_date(by_date)
    bucket_rows = _bucket_rows(state_by_date, selected_by_date, by_date, min_history)

    out = out_dir / strategy_id
    out.mkdir(parents=True, exist_ok=True)
    bucket_csv = out / "state_bucket_diagnostic.csv"
    summary_json = out / "state_diagnostic_summary.json"
    report_md = out / "state_diagnostic_report.md"
    write_csv_rows(bucket_csv, list(bucket_rows[0].keys()) if bucket_rows else ["metric"], bucket_rows)
    summary = {
        "strategy_id": strategy_id,
        "experiment_layer": "research_state_diagnostic",
        "spec": str(spec_path),
        "panel": str(panel_csv),
        "selection_count": count,
        "min_history": min_history,
        "status": _diagnostic_status(bucket_rows),
        "bucket_rows": bucket_rows,
        "governance": "State diagnostics explain or block a research hypothesis; they do not approve Engineering handoff.",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    write_json_file(summary_json, summary)
    _write_report(report_md, summary)
    return HomeAppliancesStateDiagnosticResult(summary_json, bucket_csv, report_md, str(summary["status"]))


def _group_by_date(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        trade_date = str(row.get("trade_date") or "")[:10]
        if trade_date:
            grouped[trade_date].append(row)
    return dict(grouped)


def _selected_returns_by_date(by_date: dict[str, list[dict[str, str]]], raw: dict[str, Any], count: int) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for trade_date, date_rows in sorted(by_date.items()):
        scored, used = score_rows(raw, list(date_rows))
        guarded = apply_value_trap_guard(raw, scored)
        selected = sorted(guarded, key=lambda row: to_float(row.get("final_score")) or 0.0, reverse=True)[:count]
        selected_returns = [value for value in (to_float(row.get("future_return")) for row in selected) if value is not None]
        universe_returns = [value for value in (to_float(row.get("future_return")) for row in date_rows) if value is not None]
        result[trade_date] = {
            "selected_count": len(selected),
            "selected_return": mean(selected_returns) if selected_returns else None,
            "universe_return": mean(universe_returns) if universe_returns else None,
            "used_factors": ";".join(used),
            "selected_codes": ";".join(str(row.get("code") or "") for row in selected),
        }
    return result


def _state_values_by_date(by_date: dict[str, list[dict[str, str]]]) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}
    for trade_date, rows in by_date.items():
        values: dict[str, float] = {}
        first = rows[0] if rows else {}
        for metric in STATE_METRICS:
            value = to_float(first.get(metric))
            if value is not None:
                values[metric] = value
        result[trade_date] = values
    return result


def _bucket_rows(
    state_by_date: dict[str, dict[str, float]],
    selected_by_date: dict[str, dict[str, Any]],
    by_date: dict[str, list[dict[str, str]]],
    min_history: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    dates = sorted(state_by_date)
    for metric in STATE_METRICS:
        history: list[float] = []
        dated: list[dict[str, Any]] = []
        for trade_date in dates:
            value = state_by_date.get(trade_date, {}).get(metric)
            selected = selected_by_date.get(trade_date, {})
            if value is None:
                continue
            bucket = "warmup"
            if len(history) >= min_history:
                low = quantile(history, 0.33)
                high = quantile(history, 0.67)
                if low is not None and high is not None:
                    if value <= low:
                        bucket = "low"
                    elif value >= high:
                        bucket = "high"
                    else:
                        bucket = "mid"
            dated.append(
                {
                    "metric": metric,
                    "bucket": bucket,
                    "trade_date": trade_date,
                    "state_value": value,
                    "selected_return": selected.get("selected_return"),
                    "universe_return": selected.get("universe_return"),
                    "selected_count": selected.get("selected_count"),
                    "selected_codes": selected.get("selected_codes"),
                    "date_row_count": len(by_date.get(trade_date, [])),
                }
            )
            history.append(value)
        rows.extend(_summarize_metric_bucket(metric, dated))
    return rows


def _summarize_metric_bucket(metric: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for bucket in ["low", "mid", "high", "warmup"]:
        bucket_rows = [row for row in rows if row["bucket"] == bucket]
        selected_returns = [value for value in (row.get("selected_return") for row in bucket_rows) if value is not None]
        universe_returns = [value for value in (row.get("universe_return") for row in bucket_rows) if value is not None]
        if not bucket_rows:
            continue
        result.append(
            {
                "metric": metric,
                "bucket": bucket,
                "periods": len(bucket_rows),
                "selected_cum_return": fmt_float(compound(selected_returns)),
                "selected_mean_return": fmt_float(mean(selected_returns) if selected_returns else None),
                "universe_mean_return": fmt_float(mean(universe_returns) if universe_returns else None),
                "mean_excess_return": fmt_float(
                    (mean(selected_returns) - mean(universe_returns)) if selected_returns and universe_returns else None
                ),
                "positive_ratio": fmt_float(_positive_ratio(selected_returns)),
                "sample_dates": ";".join(row["trade_date"] for row in bucket_rows),
            }
        )
    return result


def _positive_ratio(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(1 for value in values if value > 0) / len(values)


def _diagnostic_status(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "state_diagnostic_failed_no_rows"
    non_warmup = [row for row in rows if row.get("bucket") != "warmup"]
    if not non_warmup:
        return "state_diagnostic_needs_longer_history"
    return "state_diagnostic_completed_not_engineering_handoff"


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        f"# {summary['strategy_id']} State Diagnostic",
        "",
        f"Status: `{summary['status']}`",
        "",
        "This packet is a research-state diagnostic. It does not approve Engineering handoff.",
        "",
        "| Metric | Bucket | Periods | Selected cum return | Mean excess return | Positive ratio |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["bucket_rows"]:
        lines.append(
            f"| `{row['metric']}` | `{row['bucket']}` | {row['periods']} | {row['selected_cum_return']} | {row['mean_excess_return']} | {row['positive_ratio']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
