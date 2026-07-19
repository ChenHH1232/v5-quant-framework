from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.date_utils import parse_iso_date_or_none
from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.math_utils import to_float


REQUIRED_COLUMNS = [
    "sector",
    "code",
    "company_name",
    "report_period",
    "field",
    "value",
    "unit",
    "source_type",
    "source_title",
    "source_url",
    "publish_date",
    "visible_date",
    "pit_status",
    "missing_reason",
    "original_announcement_checked",
    "review_status",
    "notes",
]

CORE_FIELDS = {
    "embedded_value",
    "new_business_value",
    "core_solvency_ratio",
    "comprehensive_solvency_ratio",
    "total_investment_yield",
}
ENHANCEMENT_FIELDS = {
    "net_investment_yield",
}

PIT_USABLE_STATUSES = {"pit_usable"}
PIT_BLOCKED_STATUSES = {
    "not_pit_usable",
    "needs_original_announcement_check",
    "delayed_disclosure",
    "not_disclosed",
    "source_missing",
    "business_change",
    "poor_disclosure_quality",
}
ALLOWED_MISSING_REASONS = {
    "",
    "not_missing",
    "delayed_disclosure",
    "not_disclosed",
    "source_missing",
    "business_change",
    "poor_disclosure_quality",
    "database_backfilled_without_original_date",
    "manual_review_pending",
}


def audit_insurance_special_fields(
    source_csv: Path,
    out_dir: Path,
    *,
    strategy_id: str = "insurance_low_pb_only_v53c",
    min_core_code_count: int = 5,
    core_fields: set[str] | None = None,
) -> Path:
    rows = read_csv_rows(source_csv) if source_csv.exists() else []
    out = out_dir / strategy_id
    out.mkdir(parents=True, exist_ok=True)
    missing_columns = [column for column in REQUIRED_COLUMNS if rows and column not in rows[0]]
    if not rows:
        missing_columns = []

    audited_rows = [_audit_row(row, missing_columns) for row in rows]
    field_rows = _field_coverage_rows(audited_rows)
    active_core_fields = core_fields or CORE_FIELDS
    summary = _summary(source_csv, audited_rows, field_rows, missing_columns, strategy_id, min_core_code_count, active_core_fields)

    write_csv_rows(out / "insurance_special_fields_audit_rows.csv", _audit_fields(), audited_rows)
    write_csv_rows(out / "insurance_special_fields_field_coverage.csv", _field_fields(), field_rows)
    write_json_file(out / "insurance_special_fields_audit_summary.json", summary)
    (out / "insurance_special_fields_audit_report.md").write_text(_render_report(summary), encoding="utf-8")
    return out / "insurance_special_fields_audit_report.md"


def _audit_row(row: dict[str, str], missing_columns: list[str]) -> dict[str, Any]:
    issues = list(missing_columns)
    value = to_float(row.get("value"))
    publish_date = parse_iso_date_or_none(row.get("publish_date"))
    visible_date = parse_iso_date_or_none(row.get("visible_date"))
    pit_status = (row.get("pit_status") or "").strip().lower()
    missing_reason = (row.get("missing_reason") or "").strip().lower()
    original_checked = (row.get("original_announcement_checked") or "").strip().lower()
    review_status = (row.get("review_status") or "").strip().lower()
    if value is None:
        issues.append("missing_or_non_numeric_value")
    if not row.get("field"):
        issues.append("missing_field")
    if not row.get("code"):
        issues.append("missing_code")
    if not row.get("report_period"):
        issues.append("missing_report_period")
    if not row.get("source_type"):
        issues.append("missing_source_type")
    if not row.get("source_title"):
        issues.append("missing_source_title")
    if not row.get("source_url"):
        issues.append("missing_source_url")
    if publish_date is None:
        issues.append("missing_or_invalid_publish_date")
    if visible_date is None:
        issues.append("missing_or_invalid_visible_date")
    if publish_date and visible_date and visible_date < publish_date:
        issues.append("visible_date_before_publish_date")
    if pit_status not in PIT_USABLE_STATUSES | PIT_BLOCKED_STATUSES:
        issues.append("invalid_pit_status")
    if pit_status != "pit_usable":
        issues.append(f"pit_status_{pit_status or 'missing'}")
    if missing_reason not in ALLOWED_MISSING_REASONS:
        issues.append("invalid_missing_reason")
    if value is None and missing_reason in {"", "not_missing"}:
        issues.append("missing_reason_required_when_value_missing")
    if value is not None and missing_reason not in {"", "not_missing"}:
        issues.append("missing_reason_present_for_non_missing_value")
    if original_checked != "true":
        issues.append("original_announcement_not_checked")
    if review_status != "reviewed":
        issues.append("not_reviewed")
    pit_usable = not issues
    result = {column: row.get(column, "") for column in REQUIRED_COLUMNS}
    result.update(
        {
            "numeric_value": "" if value is None else f"{value:.10g}",
            "pit_usable": str(pit_usable).lower(),
            "issue_count": len(issues),
            "issues": ";".join(issues),
        }
    )
    return result


def _field_coverage_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_field: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_field[str(row.get("field", ""))].append(row)
    result = []
    for field, values in sorted(by_field.items()):
        if not field:
            continue
        usable = [row for row in values if row.get("pit_usable") == "true"]
        codes = {row.get("code") for row in values if row.get("code")}
        usable_codes = {row.get("code") for row in usable if row.get("code")}
        result.append(
            {
                "field": field,
                "row_count": len(values),
                "pit_usable_rows": len(usable),
                "code_count": len(codes),
                "pit_usable_code_count": len(usable_codes),
                "pit_usable_ratio": (len(usable) / len(values)) if values else 0.0,
                "is_core_v53d_field": str(field in CORE_FIELDS).lower(),
                "is_enhancement_v53d_field": str(field in ENHANCEMENT_FIELDS).lower(),
                "status": "usable" if usable else "blocked",
            }
        )
    return result


def _summary(
    source_csv: Path,
    rows: list[dict[str, Any]],
    field_rows: list[dict[str, Any]],
    missing_columns: list[str],
    strategy_id: str,
    min_core_code_count: int,
    core_fields: set[str],
) -> dict[str, Any]:
    pit_rows = [row for row in rows if row.get("pit_usable") == "true"]
    usable_core = {
        row["field"]
        for row in field_rows
        if row["field"] in core_fields and row["status"] == "usable" and int(row["pit_usable_code_count"]) >= min_core_code_count
    }
    missing_core = sorted(core_fields - usable_core)
    coverage_blocked_core_fields = [
        row["field"]
        for row in field_rows
        if row["field"] in core_fields and row["status"] == "usable" and int(row["pit_usable_code_count"]) < min_core_code_count
    ]
    blocker_count = len(missing_columns) + len(missing_core)
    status = "insurance_special_fields_source_repair_passed" if blocker_count == 0 else "insurance_special_fields_source_repair_blocked"
    return {
        "strategy_id": strategy_id,
        "status": status,
        "source_csv": str(source_csv),
        "row_count": len(rows),
        "pit_usable_rows": len(pit_rows),
        "field_count": len(field_rows),
        "usable_core_fields": sorted(usable_core),
        "active_core_fields": sorted(core_fields),
        "missing_core_fields": missing_core,
        "coverage_blocked_core_fields": sorted(coverage_blocked_core_fields),
        "min_core_code_count": min_core_code_count,
        "missing_columns": missing_columns,
        "pit_blocked_rows": len([row for row in rows if row.get("pit_usable") != "true"]),
        "blocker_count": blocker_count,
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "next_gate": "v53d_research_hypothesis_design" if status.endswith("_passed") else "insurance_special_fields_source_repair",
    }


def _render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Insurance Special Fields Audit",
        "",
        f"Status: `{summary['status']}`",
        "",
        "## Summary",
        "",
        f"- Rows: `{summary['row_count']}`",
        f"- PIT usable rows: `{summary['pit_usable_rows']}`",
        f"- Field count: `{summary['field_count']}`",
        f"- PIT blocked rows: `{summary['pit_blocked_rows']}`",
        f"- Blockers: `{summary['blocker_count']}`",
        f"- Missing core fields: `{', '.join(summary['missing_core_fields']) if summary['missing_core_fields'] else 'none'}`",
        f"- Coverage-blocked core fields: `{', '.join(summary['coverage_blocked_core_fields']) if summary['coverage_blocked_core_fields'] else 'none'}`",
        f"- Minimum core code count: `{summary['min_core_code_count']}`",
        f"- Next gate: `{summary['next_gate']}`",
        "",
        "This audit checks source completeness only. It does not validate any strategy.",
        "",
    ]
    return "\n".join(lines)


def _audit_fields() -> list[str]:
    return [*REQUIRED_COLUMNS, "numeric_value", "pit_usable", "issue_count", "issues"]


def _field_fields() -> list[str]:
    return [
        "field",
        "row_count",
        "pit_usable_rows",
        "code_count",
        "pit_usable_code_count",
        "pit_usable_ratio",
        "is_core_v53d_field",
        "is_enhancement_v53d_field",
        "status",
    ]
