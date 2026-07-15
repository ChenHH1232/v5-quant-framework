from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_V4_EXTRACTED_VALUES = Path(
    r"D:\hh\codex\v4\phase_1_fundamental\eastmoney_bank_indicator_extracted_values.csv"
)
DEFAULT_DATABASE_DIR = Path("数据库")
DEFAULT_OUTPUT_DIR = DEFAULT_DATABASE_DIR / "processed"

LONG_FIELDS = [
    "code",
    "source_year",
    "report_date",
    "notice_date",
    "field_name",
    "value",
    "unit",
    "value_scope",
    "source_type",
    "source_file",
    "raw_snippet_reference",
    "extraction_method",
    "review_status",
    "confidence",
    "source_priority",
    "sanity_status",
]

QUALITY_FIELDS = [
    "code",
    "source_year",
    "asset_quality_trend",
    "provision_buffer",
    "capital_resilience",
    "npl_ratio",
    "npl_ratio_prev",
    "provision_coverage_ratio",
    "core_tier_1_capital_adequacy_ratio",
    "tier_1_capital_adequacy_ratio",
    "capital_adequacy_ratio",
    "notice_date",
    "review_status",
    "confidence",
    "source_note",
]


@dataclass(frozen=True)
class EastmoneyBankIndicatorResult:
    long_path: Path
    quality_path: Path
    manifest_path: Path


def collect_eastmoney_bank_indicators(
    source_csv: Path = DEFAULT_V4_EXTRACTED_VALUES,
    out_dir: Path = DEFAULT_OUTPUT_DIR,
    min_review_status: str = "needs_check",
) -> EastmoneyBankIndicatorResult:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = _read_csv(source_csv)
    allowed_status = _allowed_review_statuses(min_review_status)
    normalized_all = [_normalize_row(row) for row in rows]
    rejected_by_sanity_count = sum(
        1
        for row in normalized_all
        if row["raw_value"] is not None and row["sanity_status"] != "pass"
    )
    normalized = normalized_all
    normalized = [
        row
        for row in normalized
        if row["value"] is not None
        and row["sanity_status"] == "pass"
        and row["review_status"] in allowed_status
    ]

    normalized.sort(key=lambda item: (item["code"], item["source_year"], item["field_name"]))
    quality_rows = _build_quality_rows(normalized)

    long_path = out_dir / "eastmoney_bank_indicator_long.csv"
    quality_path = out_dir / "eastmoney_bank_quality_manual_csv.csv"
    manifest_path = out_dir / "eastmoney_bank_indicator_manifest.json"

    _write_csv(long_path, LONG_FIELDS, normalized)
    _write_csv(quality_path, QUALITY_FIELDS, quality_rows)

    manifest = {
        "source": "v4_eastmoney_annual_report_pdf_extraction",
        "source_csv": str(source_csv),
        "long_path": str(long_path),
        "quality_path": str(quality_path),
        "min_review_status": min_review_status,
        "input_row_count": len(rows),
        "accepted_long_row_count": len(normalized),
        "rejected_by_sanity_count": rejected_by_sanity_count,
        "quality_row_count": len(quality_rows),
        "bank_count": len({row["code"] for row in normalized}),
        "year_count": len({row["source_year"] for row in normalized}),
        "review_policy": (
            "Rows with needs_check are candidates for engineering tests. "
            "Only reviewed rows should be used for formal factor validation."
        ),
        "quality_mapping": {
            "asset_quality_trend": "previous_year_npl_ratio - current_year_npl_ratio; fallback to -current_year_npl_ratio",
            "provision_buffer": "provision_coverage_ratio only; provision_to_loan_ratio is kept separate because the unit differs",
            "capital_resilience": "core_tier_1_capital_adequacy_ratio, then tier_1_capital_adequacy_ratio, then capital_adequacy_ratio",
        },
        "point_in_time_rule": "Use notice_date as visibility date. Never align by report_date alone.",
        "source_limitations": [
            "V4 extraction was automatic and many rows are needs_check.",
            "Candidate values must be reviewed before formal Quant Validation.",
            "This runner does not download new reports; it migrates the V4 extraction artifact into V5 format.",
        ],
    }
    _write_json(manifest_path, manifest)
    return EastmoneyBankIndicatorResult(
        long_path=long_path,
        quality_path=quality_path,
        manifest_path=manifest_path,
    )


def _build_quality_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_code_year: dict[tuple[str, int], dict[str, dict[str, Any]]] = {}
    for row in rows:
        key = (row["code"], int(row["source_year"]))
        by_code_year.setdefault(key, {})[row["field_name"]] = row

    result: list[dict[str, Any]] = []
    for (code, year), fields in sorted(by_code_year.items()):
        npl = _field_value(fields, "non_performing_loan_ratio")
        previous_fields = by_code_year.get((code, year - 1), {})
        npl_prev = _field_value(previous_fields, "non_performing_loan_ratio")
        if npl is None:
            asset_quality_trend = None
        elif npl_prev is None:
            asset_quality_trend = -npl
        else:
            asset_quality_trend = npl_prev - npl

        provision = _field_value(fields, "provision_coverage_ratio")

        core_capital = _field_value(fields, "core_tier_1_capital_adequacy_ratio")
        tier1_capital = _field_value(fields, "tier_1_capital_adequacy_ratio")
        capital = _field_value(fields, "capital_adequacy_ratio")
        capital_resilience = _first_not_none(core_capital, tier1_capital, capital)

        if asset_quality_trend is None and provision is None and capital_resilience is None:
            continue

        field_rows = list(fields.values())
        statuses = sorted({str(item["review_status"]) for item in field_rows if item.get("review_status")})
        confidences = sorted({str(item["confidence"]) for item in field_rows if item.get("confidence")})
        notice_dates = sorted({str(item["notice_date"]) for item in field_rows if item.get("notice_date")})

        result.append(
            {
                "code": code,
                "source_year": year,
                "asset_quality_trend": asset_quality_trend,
                "provision_buffer": provision,
                "capital_resilience": capital_resilience,
                "npl_ratio": npl,
                "npl_ratio_prev": npl_prev,
                "provision_coverage_ratio": _field_value(fields, "provision_coverage_ratio"),
                "core_tier_1_capital_adequacy_ratio": core_capital,
                "tier_1_capital_adequacy_ratio": tier1_capital,
                "capital_adequacy_ratio": capital,
                "notice_date": notice_dates[-1] if notice_dates else "",
                "review_status": "|".join(statuses),
                "confidence": "|".join(confidences),
                "source_note": "eastmoney_annual_report_pdf; generated from V4 extraction; review before formal validation",
            }
        )
    return result


def _normalize_row(row: dict[str, str]) -> dict[str, Any]:
    field_name = (row.get("field_name_english") or "").strip()
    raw_value = _to_float(row.get("value"))
    value, sanity_status = _sanitize_value(field_name, raw_value)
    return {
        "code": (row.get("code") or "").strip(),
        "source_year": int(float((row.get("report_year") or "0").strip() or 0)),
        "report_date": (row.get("report_date") or "").strip(),
        "notice_date": (row.get("notice_date") or "").strip(),
        "field_name": field_name,
        "raw_value": raw_value,
        "value": value,
        "unit": (row.get("unit_or_percent") or "").strip(),
        "value_scope": (row.get("value_scope") or "").strip(),
        "source_type": (row.get("source_type") or "").strip(),
        "source_file": (row.get("source_file") or "").strip(),
        "raw_snippet_reference": (row.get("raw_snippet_reference") or "").strip(),
        "extraction_method": (row.get("extraction_method") or "").strip(),
        "review_status": (row.get("review_status") or "unreviewed").strip(),
        "confidence": (row.get("confidence") or "").strip(),
        "source_priority": _source_priority(field_name),
        "sanity_status": sanity_status,
    }


def _source_priority(field_name: str) -> str:
    if field_name in {
        "non_performing_loan_ratio",
        "provision_coverage_ratio",
        "provision_to_loan_ratio",
        "core_tier_1_capital_adequacy_ratio",
        "tier_1_capital_adequacy_ratio",
        "capital_adequacy_ratio",
    }:
        return "v2_required_quality"
    return "supplementary_bank_indicator"


def _allowed_review_statuses(min_review_status: str) -> set[str]:
    if min_review_status == "reviewed":
        return {"reviewed"}
    if min_review_status == "needs_check":
        return {"reviewed", "needs_check"}
    if min_review_status == "unreviewed":
        return {"reviewed", "needs_check", "unreviewed"}
    raise ValueError("min_review_status must be reviewed, needs_check, or unreviewed")


def _field_value(fields: dict[str, dict[str, Any]], name: str) -> float | None:
    item = fields.get(name)
    if not item:
        return None
    return item.get("value")


def _first_not_none(*values: float | None) -> float | None:
    for value in values:
        if value is not None:
            return value
    return None


def _to_float(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "").replace("%", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _sanitize_value(field_name: str, value: float | None) -> tuple[float | None, str]:
    if value is None:
        return None, "missing"
    bounds = {
        "non_performing_loan_ratio": (0.1, 10.0),
        "provision_coverage_ratio": (30.0, 1000.0),
        "provision_to_loan_ratio": (0.0, 20.0),
        "core_tier_1_capital_adequacy_ratio": (5.0, 50.0),
        "tier_1_capital_adequacy_ratio": (5.0, 50.0),
        "capital_adequacy_ratio": (5.0, 50.0),
        "liquidity_ratio": (0.0, 1000.0),
        "liquidity_matching_ratio": (0.0, 1000.0),
        "liquidity_coverage_ratio": (0.0, 1000.0),
        "single_largest_customer_loan_ratio": (0.0, 100.0),
        "top_ten_customer_loan_ratio": (0.0, 100.0),
        "single_group_credit_concentration_ratio": (0.0, 100.0),
    }
    low, high = bounds.get(field_name, (-1e12, 1e12))
    if value < low or value > high:
        return None, "out_of_bounds"
    return value, "pass"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _csv_value(row.get(field)) for field in fieldnames})


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _csv_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-csv", type=Path, default=DEFAULT_V4_EXTRACTED_VALUES)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--min-review-status",
        choices=["reviewed", "needs_check", "unreviewed"],
        default="needs_check",
    )
    args = parser.parse_args(argv)
    result = collect_eastmoney_bank_indicators(args.source_csv, args.out_dir, args.min_review_status)
    print(result.quality_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
