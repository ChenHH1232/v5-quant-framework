from __future__ import annotations

import argparse
import csv
import json
from calendar import monthrange
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_OUT_DIR = Path("数据库") / "processed" / "utilities_external_state"

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

DEFAULT_TEMPLATE_ROWS = [
    {
        "visible_date": "",
        "state_date": "",
        "state_scope": "national",
        "sub_industry": "thermal_power",
        "metric": "coal_price_index",
        "value": "",
        "unit": "index_or_cny_per_ton",
        "source_name": "",
        "source_url": "",
        "source_publication_date": "",
        "pit_usable": "false",
        "review_status": "template",
        "notes": "Fuel-cost proxy for thermal power. Fill only from a source with publication date.",
    },
    {
        "visible_date": "",
        "state_date": "",
        "state_scope": "national",
        "sub_industry": "thermal_power",
        "metric": "thermal_utilization_hours",
        "value": "",
        "unit": "hours",
        "source_name": "",
        "source_url": "",
        "source_publication_date": "",
        "pit_usable": "false",
        "review_status": "template",
        "notes": "Utilization proxy for thermal power operators.",
    },
    {
        "visible_date": "",
        "state_date": "",
        "state_scope": "national_or_region",
        "sub_industry": "hydropower",
        "metric": "hydro_utilization_or_inflow_proxy",
        "value": "",
        "unit": "hours_or_index",
        "source_name": "",
        "source_url": "",
        "source_publication_date": "",
        "pit_usable": "false",
        "review_status": "template",
        "notes": "Hydrology or utilization proxy for hydropower.",
    },
    {
        "visible_date": "",
        "state_date": "",
        "state_scope": "national_or_region",
        "sub_industry": "gas",
        "metric": "gas_tariff_or_margin_proxy",
        "value": "",
        "unit": "index_or_price",
        "source_name": "",
        "source_url": "",
        "source_publication_date": "",
        "pit_usable": "false",
        "review_status": "template",
        "notes": "Gas price/tariff proxy. Must be visible before rebalance date.",
    },
    {
        "visible_date": "",
        "state_date": "",
        "state_scope": "national",
        "sub_industry": "all_power",
        "metric": "marketized_power_price_or_tariff_proxy",
        "value": "",
        "unit": "index_or_price",
        "source_name": "",
        "source_url": "",
        "source_publication_date": "",
        "pit_usable": "false",
        "review_status": "template",
        "notes": "Electricity tariff / market transaction price proxy.",
    },
]


def write_utilities_external_state_template(out_dir: Path = DEFAULT_OUT_DIR) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    template_path = out_dir / "utilities_external_state_template.csv"
    _write_csv(template_path, STATE_FIELDS, DEFAULT_TEMPLATE_ROWS)
    _write_json(
        out_dir / "collection_manifest.json",
        {
            "dataset": "utilities_external_state_template",
            "template": str(template_path),
            "fields": STATE_FIELDS,
            "row_count": len(DEFAULT_TEMPLATE_ROWS),
            "required_pit_rule": "visible_date must be on or before the rebalance date. Rows without visible_date or source_publication_date are not PIT usable.",
            "intended_metrics": [
                "coal_price_index",
                "thermal_utilization_hours",
                "hydro_utilization_or_inflow_proxy",
                "gas_tariff_or_margin_proxy",
                "marketized_power_price_or_tariff_proxy",
            ],
            "governance": "This template is data-engineering preparation only. It must not be used for strategy scoring until populated and PIT audited.",
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return template_path


def collect_utilities_external_state(out_dir: Path = DEFAULT_OUT_DIR) -> Path:
    rows: list[dict[str, Any]] = []
    rows.extend(_collect_society_electricity_rows())
    rows.extend(_manual_nea_state_rows())
    rows = sorted(rows, key=lambda item: (item["visible_date"], item["metric"], item["sub_industry"]))

    out_dir.mkdir(parents=True, exist_ok=True)
    panel_path = out_dir / "utilities_external_state.csv"
    _write_csv(panel_path, STATE_FIELDS, rows)
    validation = validate_utilities_external_state(panel_path)
    _write_json(
        out_dir / "collection_manifest.json",
        {
            "dataset": "utilities_external_state",
            "panel": str(panel_path),
            "row_count": len(rows),
            "validation": validation,
            "sources": [
                "akshare.macro_china_society_electricity",
                "National Energy Administration public releases",
            ],
            "pit_policy": "AkShare monthly electricity rows use conservative visible_date = 25th day of the next month. NEA manual rows use the official publication date as visible_date.",
            "limitations": [
                "AkShare monthly electricity rows do not expose original publication URLs row-by-row, so review_status is conservative_proxy.",
                "NEA manual rows are source-anchored but currently sparse; they are suitable for data-pipeline validation before broad historical modeling.",
                "Coal-price, tariff and hydrology rows still need broader historical source collection before strategy scoring.",
            ],
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return panel_path


def validate_utilities_external_state(path: Path) -> dict[str, Any]:
    rows = _read_csv(path)
    missing_required = []
    future_or_invalid = 0
    pit_usable = 0
    for index, row in enumerate(rows, start=2):
        for field in ["visible_date", "state_date", "metric", "source_publication_date"]:
            if not row.get(field):
                missing_required.append(f"line {index}: missing {field}")
        if row.get("visible_date") and row.get("source_publication_date"):
            if str(row["visible_date"])[:10] < str(row["source_publication_date"])[:10]:
                future_or_invalid += 1
        if str(row.get("pit_usable", "")).lower() == "true":
            pit_usable += 1
    return {
        "row_count": len(rows),
        "pit_usable_count": pit_usable,
        "missing_required": missing_required,
        "future_or_invalid_visible_dates": future_or_invalid,
        "status": "pass" if not missing_required and future_or_invalid == 0 else "needs_review",
    }


def _collect_society_electricity_rows() -> list[dict[str, Any]]:
    try:
        import akshare as ak
    except Exception as exc:  # pragma: no cover - optional dependency.
        raise RuntimeError("collecting utilities external state requires akshare") from exc

    df = ak.macro_china_society_electricity()
    rows = []
    for record in df.to_dict(orient="records"):
        state_day = _parse_year_month(record.get("统计时间"))
        if state_day is None:
            continue
        visible = _next_month_25(state_day)
        rows.extend(
            [
                _state_row(
                    visible,
                    state_day,
                    "national",
                    "all_power",
                    "electricity_consumption_cumulative",
                    record.get("全社会用电量"),
                    "10k_kwh",
                    "AkShare macro_china_society_electricity",
                    "https://akshare.akfamily.xyz/",
                    visible,
                    "conservative_proxy",
                    "Cumulative total social electricity consumption. Visible date conservatively assigned to next month day 25.",
                ),
                _state_row(
                    visible,
                    state_day,
                    "national",
                    "all_power",
                    "electricity_consumption_yoy",
                    record.get("全社会用电量同比"),
                    "percent",
                    "AkShare macro_china_society_electricity",
                    "https://akshare.akfamily.xyz/",
                    visible,
                    "conservative_proxy",
                    "Demand-growth proxy for utilities. Publication date is approximated conservatively.",
                ),
                _state_row(
                    visible,
                    state_day,
                    "national",
                    "industrial_power",
                    "secondary_industry_electricity_yoy",
                    record.get("第二产业用电量同比"),
                    "percent",
                    "AkShare macro_china_society_electricity",
                    "https://akshare.akfamily.xyz/",
                    visible,
                    "conservative_proxy",
                    "Industrial electricity-demand proxy for power operators.",
                ),
            ]
        )
    return [row for row in rows if row["value"] not in {"", None}]


def _manual_nea_state_rows() -> list[dict[str, Any]]:
    seeds = [
        {
            "visible_date": "2024-01-26",
            "state_date": "2023-12-31",
            "source_url": "https://www.nea.gov.cn/2024-01/26/c_1310762246.htm",
            "metrics": [
                ("all_power", "generation_utilization_hours_total", 3592, "hours", "2023 NEA annual power statistics."),
                ("hydropower", "hydro_utilization_hours", 3133, "hours", "2023 NEA annual power statistics."),
                ("thermal_power", "thermal_utilization_hours", 4466, "hours", "2023 NEA annual power statistics."),
                ("hydropower", "hydro_capacity", 42154, "10k_kw", "2023 NEA annual power statistics."),
                ("thermal_power", "thermal_capacity", 139032, "10k_kw", "2023 NEA annual power statistics."),
                ("nuclear_power", "nuclear_capacity", 5691, "10k_kw", "2023 NEA annual power statistics."),
            ],
        },
        {
            "visible_date": "2025-01-21",
            "state_date": "2024-12-31",
            "source_url": "https://www.nea.gov.cn/20250121/097bfd7c1cd3498897639857d86d5dac/c.html",
            "metrics": [
                ("all_power", "generation_utilization_hours_total", 3442, "hours", "2024 NEA annual power statistics."),
                ("hydropower", "hydro_capacity", 43595, "10k_kw", "2024 NEA annual power statistics."),
                ("thermal_power", "thermal_capacity", 144445, "10k_kw", "2024 NEA annual power statistics."),
                ("nuclear_power", "nuclear_capacity", 6083, "10k_kw", "2024 NEA annual power statistics."),
            ],
        },
        {
            "visible_date": "2024-07-20",
            "state_date": "2024-06-30",
            "source_url": "https://www.nea.gov.cn/2024-07/20/c_1310782235.htm",
            "metrics": [
                ("all_power", "generation_utilization_hours_total", 1666, "hours", "2024 H1 NEA power statistics."),
                ("thermal_power", "power_supply_coal_consumption_rate", 302.4, "g_per_kwh", "2024 H1 NEA power statistics."),
                ("thermal_power", "heating_coal_consumption", 20454, "10k_ton", "2024 H1 NEA power statistics."),
            ],
        },
        {
            "visible_date": "2026-06-25",
            "state_date": "2026-05-31",
            "source_url": "https://www.nea.gov.cn/20260625/24f752fd199c4632b7dc7762462585de/c.html",
            "metrics": [
                ("all_power", "generation_utilization_hours_total", 1155, "hours", "2026 Jan-May NEA power statistics."),
            ],
        },
    ]
    rows = []
    for seed in seeds:
        visible = _parse_date(seed["visible_date"])
        state_day = _parse_date(seed["state_date"])
        for sub_industry, metric, value, unit, notes in seed["metrics"]:
            rows.append(
                _state_row(
                    visible,
                    state_day,
                    "national",
                    sub_industry,
                    metric,
                    value,
                    unit,
                    "National Energy Administration",
                    seed["source_url"],
                    visible,
                    "source_anchored",
                    notes,
                )
            )
    return rows


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
        "pit_usable": "true",
        "review_status": review_status,
        "notes": notes,
    }


def _parse_year_month(value: Any) -> date | None:
    if value is None:
        return None
    text = str(value).strip()
    if "." not in text:
        return None
    year_text, month_text = text.split(".", 1)
    try:
        year = int(year_text)
        month = int(float(month_text))
    except ValueError:
        return None
    if month < 1 or month > 12:
        return None
    return date(year, month, monthrange(year, month)[1])


def _next_month_25(day: date) -> date:
    year = day.year
    month = day.month + 1
    if month == 13:
        year += 1
        month = 1
    return date(year, month, 25)


def _parse_date(value: str) -> date:
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()


def _fmt(value: Any) -> str:
    if value in {None, "", "nan", "NaN", "None"}:
        return ""
    try:
        return f"{float(value):.10g}"
    except (TypeError, ValueError):
        return str(value)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-utilities-external-state")
    subparsers = parser.add_subparsers(dest="command", required=True)
    template_parser = subparsers.add_parser("template")
    template_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    collect_parser = subparsers.add_parser("collect")
    collect_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("csv_path", type=Path)
    args = parser.parse_args(argv)
    if args.command == "template":
        print(write_utilities_external_state_template(args.out_dir))
        return 0
    if args.command == "collect":
        print(collect_utilities_external_state(args.out_dir))
        return 0
    if args.command == "validate":
        print(json.dumps(validate_utilities_external_state(args.csv_path), ensure_ascii=False, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
