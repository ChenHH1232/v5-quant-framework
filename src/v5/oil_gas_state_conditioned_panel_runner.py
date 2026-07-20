from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.paths import DEFAULT_PROCESSED_DIR


DEFAULT_PANEL = DEFAULT_PROCESSED_DIR / "oil_gas_low_vol_panel_v58a" / "oil_gas_ocf_dividend_cycle_probe_v58a" / "panel_with_low_vol.csv"
DEFAULT_OUT_DIR = DEFAULT_PROCESSED_DIR / "oil_gas_state_conditioned_panel_v58d"
STATE_METRICS = [
    "crude_oil_price_state",
    "bitumen_price_state",
    "refining_spread_proxy_state",
    "gas_liquid_price_state",
]


@dataclass(frozen=True)
class OilGasStateConditionedPanelResult:
    panel_path: Path
    manifest_path: Path
    row_count: int
    date_count: int
    status: str


def build_oil_gas_state_conditioned_panel(
    panel_path: Path = DEFAULT_PANEL,
    out_dir: Path = DEFAULT_OUT_DIR,
    strategy_id: str = "oil_gas_state_conditioned_ocf_v58d",
    min_history: int = 4,
    state_source_csv: Path | None = None,
) -> OilGasStateConditionedPanelResult:
    rows = read_csv_rows(panel_path)
    if state_source_csv is not None:
        rows = _attach_state_source(rows, read_csv_rows(state_source_csv))
    by_date = _group_by_date(rows)
    state_buckets = _state_buckets_by_date(by_date, min_history)
    enriched = []
    policy_counts: dict[str, int] = {}
    for trade_date in sorted(by_date):
        bucket = state_buckets.get(trade_date, {})
        policy = _cycle_policy(bucket)
        policy_counts[policy] = policy_counts.get(policy, 0) + len(by_date[trade_date])
        for row in by_date[trade_date]:
            item = dict(row)
            for metric in STATE_METRICS:
                item[f"{metric}_bucket"] = bucket.get(metric, "missing")
            item["oil_gas_cycle_policy"] = policy
            _attach_conditioned_scores(item, policy)
            enriched.append(item)

    out = out_dir / strategy_id
    panel_out = out / "panel.csv"
    manifest_out = out / "collection_manifest.json"
    fieldnames = _fieldnames(rows, enriched)
    write_csv_rows(panel_out, fieldnames, enriched)
    manifest = {
        "schema_version": 1,
        "strategy_id": strategy_id,
        "source_panel": str(panel_path),
        "state_source_csv": str(state_source_csv) if state_source_csv else "",
        "panel_path": str(panel_out),
        "row_count": len(enriched),
        "date_count": len({row.get("trade_date") for row in enriched}),
        "state_metrics": STATE_METRICS,
        "min_history": min_history,
        "policy_counts": policy_counts,
        "status": "research_pit_validation_ready",
        "pit_policy": "State buckets use expanding history strictly before each trade_date.",
        "limitations": [
            "State metrics are sourced from the supplied PIT state source when state_source_csv is set; otherwise they remain V5.8a futures proxies.",
            "This panel is for research validation only and cannot approve Engineering handoff.",
            "Low-PE remains diagnostic because cyclical earnings can create false cheapness.",
        ],
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    write_json_file(manifest_out, manifest)
    return OilGasStateConditionedPanelResult(
        panel_path=panel_out,
        manifest_path=manifest_out,
        row_count=len(enriched),
        date_count=int(manifest["date_count"]),
        status=str(manifest["status"]),
    )


def _attach_state_source(rows: list[dict[str, str]], source_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_metric = {
        metric: sorted(
            [
                row
                for row in source_rows
                if row.get("metric") == metric
                and str(row.get("pit_usable", "")).lower() == "true"
                and row.get("visible_date")
                and row.get("value") not in {None, ""}
            ],
            key=lambda row: str(row.get("visible_date"))[:10],
        )
        for metric in STATE_METRICS
    }
    enriched = []
    for row in rows:
        item = dict(row)
        trade_date = str(row.get("trade_date") or "")[:10]
        if trade_date:
            for metric, metric_rows in by_metric.items():
                visible = [source for source in metric_rows if str(source.get("visible_date"))[:10] <= trade_date]
                if visible:
                    latest = visible[-1]
                    item[metric] = str(latest.get("value") or "")
                    item[f"{metric}_source_visible_date"] = str(latest.get("visible_date") or "")[:10]
                    item[f"{metric}_source_state_date"] = str(latest.get("state_date") or "")[:10]
                    item[f"{metric}_source_review_status"] = str(latest.get("review_status") or "")
        enriched.append(item)
    return enriched


def _attach_conditioned_scores(row: dict[str, Any], policy: str) -> None:
    row["state_conditioned_ocf_score"] = ""
    row["cycle_defensive_low_vol_score"] = ""
    row["cycle_low_pe_diagnostic_score"] = ""
    if policy in {"ocf_supported_weak_commodity", "ocf_supported_refining_spread"}:
        row["state_conditioned_ocf_score"] = row.get("operating_cash_flow_yield", "")
    elif policy in {"defensive_strong_commodity", "warmup_defensive"}:
        row["cycle_defensive_low_vol_score"] = row.get("low_vol_score", "")
    else:
        row["state_conditioned_ocf_score"] = row.get("operating_cash_flow_yield", "")
        row["cycle_defensive_low_vol_score"] = row.get("low_vol_score", "")
    if policy == "ocf_supported_refining_spread":
        row["cycle_low_pe_diagnostic_score"] = row.get("pe_ratio", "")


def _cycle_policy(bucket: dict[str, str]) -> str:
    buckets = set(bucket.values())
    if not buckets or "missing" in buckets:
        return "missing_state"
    if "warmup" in buckets:
        return "warmup_defensive"
    crude = bucket.get("crude_oil_price_state")
    bitumen = bucket.get("bitumen_price_state")
    refining = bucket.get("refining_spread_proxy_state")
    gas = bucket.get("gas_liquid_price_state")
    if crude == "strong" or bitumen == "strong":
        return "defensive_strong_commodity"
    if crude == "weak" or bitumen == "weak" or gas == "weak":
        return "ocf_supported_weak_commodity"
    if refining in {"mid", "strong"}:
        return "ocf_supported_refining_spread"
    return "balanced_ocf_low_vol"


def _state_buckets_by_date(by_date: dict[str, list[dict[str, str]]], min_history: int) -> dict[str, dict[str, str]]:
    values_by_metric = {metric: _state_by_date(by_date, metric) for metric in STATE_METRICS}
    history_by_metric: dict[str, list[float]] = {metric: [] for metric in STATE_METRICS}
    result: dict[str, dict[str, str]] = {}
    for trade_date in sorted(by_date):
        result[trade_date] = {}
        for metric in STATE_METRICS:
            value = values_by_metric[metric].get(trade_date)
            if value is None:
                result[trade_date][metric] = "missing"
                continue
            result[trade_date][metric] = _expanding_bucket(history_by_metric[metric], value, min_history)
            history_by_metric[metric].append(value)
    return result


def _state_by_date(by_date: dict[str, list[dict[str, str]]], metric: str) -> dict[str, float]:
    result = {}
    for trade_date, rows in by_date.items():
        values = [_to_float(row.get(metric)) for row in rows]
        usable = [value for value in values if value is not None]
        if usable:
            result[trade_date] = usable[0]
    return result


def _group_by_date(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        trade_date = row.get("trade_date")
        if not trade_date:
            continue
        if _to_float(row.get("future_return") or row.get("total_return")) is None:
            continue
        result.setdefault(trade_date, []).append(row)
    return result


def _expanding_bucket(history: list[float], value: float, min_history: int) -> str:
    if len(history) < min_history:
        return "warmup"
    sorted_history = sorted(history)
    q33 = sorted_history[len(sorted_history) // 3]
    q67 = sorted_history[(2 * len(sorted_history)) // 3]
    if value <= q33:
        return "weak"
    if value >= q67:
        return "strong"
    return "mid"


def _fieldnames(source_rows: list[dict[str, str]], enriched_rows: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for row in source_rows + enriched_rows:
        for key in row:
            if key not in names:
                names.append(key)
    return names


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-oil-gas-state-conditioned-panel")
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--strategy-id", default="oil_gas_state_conditioned_ocf_v58d")
    parser.add_argument("--min-history", type=int, default=4)
    parser.add_argument("--state-source-csv", type=Path)
    args = parser.parse_args(argv)
    print(build_oil_gas_state_conditioned_panel(args.panel, args.out_dir, args.strategy_id, args.min_history, args.state_source_csv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
