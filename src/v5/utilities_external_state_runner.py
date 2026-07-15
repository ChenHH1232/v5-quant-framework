from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
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
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("csv_path", type=Path)
    args = parser.parse_args(argv)
    if args.command == "template":
        print(write_utilities_external_state_template(args.out_dir))
        return 0
    if args.command == "validate":
        print(json.dumps(validate_utilities_external_state(args.csv_path), ensure_ascii=False, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
