from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

from v5.math_utils import compound


DERIVED_FIELDS = [
    "operating_state_score",
    "sector_demand_state",
    "sector_revenue_growth_mean",
    "sector_cash_collection_mean",
    "operating_state_factor_count",
]

OPERATING_STATE_FACTORS = [
    ("revenue_growth_yoy", "higher"),
    ("ocf_to_revenue", "higher"),
    ("cash_collection_quality", "higher"),
    ("interest_coverage", "higher"),
    ("asset_liability_ratio", "lower"),
    ("capex_burden", "lower"),
]


def build_port_rail_operating_state_panel(panel: Path, out_dir: Path) -> Path:
    rows = _read_csv(panel)
    if not rows:
        raise RuntimeError(f"empty panel: {panel}")
    out_dir.mkdir(parents=True, exist_ok=True)
    enriched = _enrich_rows(rows)
    fieldnames = list(rows[0].keys())
    for field in DERIVED_FIELDS:
        if field not in fieldnames:
            fieldnames.append(field)
    panel_path = out_dir / "panel_operating_state.csv"
    _write_csv(panel_path, fieldnames, enriched)
    _write_csv(out_dir / "panel_port_only.csv", fieldnames, [row for row in enriched if row.get("sub_industry") == "port"])
    _write_csv(out_dir / "panel_rail_only.csv", fieldnames, [row for row in enriched if row.get("sub_industry") == "railway_transport"])
    state_rows = _state_bucket_summary(enriched)
    _write_csv(
        out_dir / "state_bucket_validation.csv",
        [
            "sector_demand_state",
            "periods",
            "mean_return",
            "cum_return",
            "positive_ratio",
            "mean_sector_revenue_growth",
            "mean_sector_cash_collection",
        ],
        state_rows,
    )
    manifest = {
        "dataset": "port_rail_operating_state_panel_v55b",
        "source_panel": str(panel),
        "panel": str(panel_path),
        "port_only_panel": str(out_dir / "panel_port_only.csv"),
        "rail_only_panel": str(out_dir / "panel_rail_only.csv"),
        "state_bucket_validation": str(out_dir / "state_bucket_validation.csv"),
        "row_count": len(enriched),
        "date_count": len({row["trade_date"] for row in enriched}),
        "code_count": len({row["code"] for row in enriched}),
        "operating_state_factors": [{"field": field, "direction": direction} for field, direction in OPERATING_STATE_FACTORS],
        "pit_policy": "Derived only from fields already visible in the source PIT panel. No future rows are used for cross-sectional operating_state_score. sector_demand_state uses expanding prior/current date history.",
        "limitations": [
            "This is still a financial-statement operating proxy layer, not original cargo throughput / rail freight data.",
            "Before Engineering handoff, Research Agent should review company reports and official operating statistics where available.",
        ],
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    (out_dir / "collection_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return panel_path


def _enrich_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_date[row["trade_date"]].append(row)
    state_history: list[tuple[str, float]] = []
    enriched: list[dict[str, Any]] = []
    for trade_date in sorted(by_date):
        date_rows = [dict(row) for row in by_date[trade_date]]
        factor_scores = _date_factor_scores(date_rows)
        sector_revenue_growth = _mean_field(date_rows, "revenue_growth_yoy")
        sector_cash_collection = _mean_field(date_rows, "cash_collection_quality")
        if sector_revenue_growth is not None:
            state_history.append((trade_date, sector_revenue_growth))
        state = _expanding_state_bucket([value for _date, value in state_history], sector_revenue_growth)
        for row in date_rows:
            code = row["code"]
            parts = [scores[code] for scores in factor_scores if code in scores]
            row["operating_state_score"] = _fmt_float(mean(parts) if parts else None)
            row["operating_state_factor_count"] = str(len(parts))
            row["sector_demand_state"] = state
            row["sector_revenue_growth_mean"] = _fmt_float(sector_revenue_growth)
            row["sector_cash_collection_mean"] = _fmt_float(sector_cash_collection)
            enriched.append(row)
    return enriched


def _date_factor_scores(rows: list[dict[str, Any]]) -> list[dict[str, float]]:
    result: list[dict[str, float]] = []
    for field, direction in OPERATING_STATE_FACTORS:
        keyed = []
        for row in rows:
            value = _to_float(row.get(field))
            if value is None:
                continue
            if direction == "lower":
                value = -value
            keyed.append((row["code"], value))
        scores = _zscores(keyed)
        if len(scores) >= 3:
            result.append(scores)
    return result


def _zscores(keyed: list[tuple[str, float]]) -> dict[str, float]:
    if not keyed:
        return {}
    values = [value for _code, value in keyed]
    avg = mean(values)
    variance = mean((value - avg) ** 2 for value in values)
    std = math.sqrt(variance)
    if std == 0:
        return {code: 0.0 for code, _value in keyed}
    return {code: (value - avg) / std for code, value in keyed}


def _expanding_state_bucket(history: list[float], current: float | None) -> str:
    if current is None:
        return "unknown"
    if len(history) < 6:
        return "warmup"
    ordered = sorted(history)
    low = ordered[max(0, int(len(ordered) * 0.33) - 1)]
    high = ordered[max(0, int(len(ordered) * 0.67) - 1)]
    if current <= low:
        return "weak"
    if current >= high:
        return "strong"
    return "mid"


def _state_bucket_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    returns_by_state: dict[str, list[float]] = defaultdict(list)
    revenue_by_state: dict[str, list[float]] = defaultdict(list)
    collection_by_state: dict[str, list[float]] = defaultdict(list)
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_date[row["trade_date"]].append(row)
    for _date, date_rows in sorted(by_date.items()):
        state = date_rows[0].get("sector_demand_state") or "unknown"
        rets = [_to_float(row.get("future_return")) for row in date_rows]
        rets = [value for value in rets if value is not None]
        if rets:
            returns_by_state[state].append(mean(rets))
        rev = _to_float(date_rows[0].get("sector_revenue_growth_mean"))
        col = _to_float(date_rows[0].get("sector_cash_collection_mean"))
        if rev is not None:
            revenue_by_state[state].append(rev)
        if col is not None:
            collection_by_state[state].append(col)
    result = []
    for state in sorted(returns_by_state):
        values = returns_by_state[state]
        result.append(
            {
                "sector_demand_state": state,
                "periods": len(values),
                "mean_return": _fmt_float(mean(values) if values else None),
                "cum_return": _fmt_float(compound(values) if values else None),
                "positive_ratio": _fmt_float(sum(1 for value in values if value > 0) / len(values) if values else None),
                "mean_sector_revenue_growth": _fmt_float(mean(revenue_by_state[state]) if revenue_by_state[state] else None),
                "mean_sector_cash_collection": _fmt_float(mean(collection_by_state[state]) if collection_by_state[state] else None),
            }
        )
    return result


def _mean_field(rows: list[dict[str, Any]], field: str) -> float | None:
    values = [_to_float(row.get(field)) for row in rows]
    values = [value for value in values if value is not None]
    return mean(values) if values else None


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


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


def _fmt_float(value: Any) -> str:
    numeric = _to_float(value)
    if numeric is None:
        return ""
    return f"{numeric:.10g}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("panel", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("数据库") / "processed" / "port_rail_operating_state_v55b")
    args = parser.parse_args(argv)
    print(build_port_rail_operating_state_panel(args.panel, args.out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
