from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_SOURCE_PANEL = Path("数据库") / "processed" / "utilities_pit_panel" / "panel.csv"
DEFAULT_OUT_DIR = Path("数据库") / "processed" / "utilities_cashflow_value_v51b_panel"

ADDED_FIELDS = [
    "cashflow_yield_subindustry_score",
    "low_pb_subindustry_score",
    "dividend_cashflow_support_score",
    "capex_control_score",
    "leverage_control_score",
]


def build_utilities_cashflow_value_panel(
    source_panel: Path = DEFAULT_SOURCE_PANEL,
    out_dir: Path = DEFAULT_OUT_DIR,
) -> Path:
    rows = _read_csv(source_panel)
    enhanced = _enhance_rows(rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    panel_path = out_dir / "panel.csv"
    fieldnames = list(rows[0].keys()) + [field for field in ADDED_FIELDS if field not in rows[0]]
    _write_csv(panel_path, fieldnames, enhanced)
    manifest = {
        "dataset": "utilities_cashflow_value_v51b_panel",
        "source_panel": str(source_panel),
        "panel": str(panel_path),
        "row_count": len(enhanced),
        "date_count": len({row["trade_date"] for row in enhanced}),
        "code_count": len({row["code"] for row in enhanced}),
        "added_fields": ADDED_FIELDS,
        "method": "Build sub-industry-aware percentile scores by trade_date and sub_industry. Scores are research factors only and require formal validation.",
        "limitations": [
            "The scores use within-date and within-sub-industry cross-sectional ranks; small sub-industries fall back to same-date full-universe ranks.",
            "This panel is still research_pit_validation input, not platform replication input.",
            "External variables such as coal prices, tariff policy and utilization hours are not yet directly joined.",
        ],
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    _write_json(out_dir / "collection_manifest.json", manifest)
    return panel_path


def _enhance_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    by_date_industry: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_date[row["trade_date"]].append(row)
        by_date_industry[(row["trade_date"], row.get("sub_industry", ""))].append(row)

    enhanced = []
    for row in rows:
        date_rows = by_date[row["trade_date"]]
        industry_rows = by_date_industry[(row["trade_date"], row.get("sub_industry", ""))]
        peer_rows = industry_rows if len(industry_rows) >= 8 else date_rows

        cashflow = _percentile(row, peer_rows, "operating_cash_flow_yield", higher_is_better=True)
        low_pb = _percentile(row, peer_rows, "low_price_to_book", higher_is_better=False)
        dividend = _percentile(row, peer_rows, "dividend_yield", higher_is_better=True)
        ocf_profit = _percentile(row, peer_rows, "operating_cash_flow_to_net_profit", higher_is_better=True)
        capex = _percentile(row, peer_rows, "capex_burden", higher_is_better=False)
        leverage = _percentile(row, peer_rows, "asset_liability_ratio", higher_is_better=False)

        item = dict(row)
        item["cashflow_yield_subindustry_score"] = _fmt(cashflow)
        item["low_pb_subindustry_score"] = _fmt(low_pb)
        item["dividend_cashflow_support_score"] = _fmt(_average([dividend, cashflow, ocf_profit]))
        item["capex_control_score"] = _fmt(capex)
        item["leverage_control_score"] = _fmt(leverage)
        enhanced.append(item)
    return enhanced


def _percentile(row: dict[str, str], peers: list[dict[str, str]], field: str, higher_is_better: bool) -> float | None:
    current = _to_float(row.get(field))
    if current is None:
        return None
    values = [_to_float(peer.get(field)) for peer in peers]
    values = sorted(value for value in values if value is not None)
    if len(values) < 3:
        return None
    below_or_equal = sum(1 for value in values if value <= current)
    percentile = below_or_equal / len(values)
    if not higher_is_better:
        percentile = 1.0 - percentile
    return percentile


def _average(values: list[float | None]) -> float | None:
    usable = [value for value in values if value is not None]
    if not usable:
        return None
    return sum(usable) / len(usable)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _to_float(value: Any) -> float | None:
    if value in {None, "", "nan", "NaN", "None"}:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric != numeric or numeric in {float("inf"), float("-inf")}:
        return None
    return numeric


def _fmt(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.10g}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-utilities-cashflow-value-panel")
    parser.add_argument("source_panel", type=Path, nargs="?", default=DEFAULT_SOURCE_PANEL)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)
    print(build_utilities_cashflow_value_panel(args.source_panel, args.out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
