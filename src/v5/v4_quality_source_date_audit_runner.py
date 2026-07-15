from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import date
from pathlib import Path
from statistics import mean
from typing import Any


def audit_v4_quality_source_dates(
    quality_csv: Path,
    out_dir: Path,
    strategy_id: str = "bank_high_dividend_sustainability_v3",
) -> Path:
    rows = _read_csv(quality_csv)
    out = out_dir / strategy_id
    out.mkdir(parents=True, exist_ok=True)
    audit_rows = [_audit_row(row) for row in rows]
    _write_csv(out / "v4_quality_source_date_audit.csv", list(audit_rows[0].keys()) if audit_rows else ["code"], audit_rows)
    status_counts = Counter(row["audit_status"] for row in audit_rows)
    severity_counts = Counter(row["severity"] for row in audit_rows)
    lags = [int(row["lag_days_after_fiscal_year_end"]) for row in audit_rows if row["lag_days_after_fiscal_year_end"] != ""]
    summary = {
        "strategy_id": strategy_id,
        "quality_csv": str(quality_csv),
        "row_count": len(audit_rows),
        "code_count": len({row.get("code") for row in audit_rows}),
        "source_year_count": len({row.get("source_year") for row in audit_rows}),
        "audit_status_counts": dict(status_counts),
        "severity_counts": dict(severity_counts),
        "mean_lag_days_after_fiscal_year_end": mean(lags) if lags else None,
        "min_lag_days_after_fiscal_year_end": min(lags) if lags else None,
        "max_lag_days_after_fiscal_year_end": max(lags) if lags else None,
        "decision": _decision(status_counts, severity_counts),
        "outputs": {
            "audit_csv": "v4_quality_source_date_audit.csv",
            "summary": "v4_quality_source_date_audit_summary.json",
            "report": "v4_quality_source_date_audit_report.md",
        },
        "limitations": [
            "This audit checks plausibility of the V4 bridge notice_date. It does not verify original exchange announcement files.",
            "Rows marked plausible are still needs_check until original annual-report or JoinQuant PIT visibility is independently verified.",
        ],
    }
    _write_json(out / "v4_quality_source_date_audit_summary.json", summary)
    _write_report(out / "v4_quality_source_date_audit_report.md", summary, audit_rows)
    return out / "v4_quality_source_date_audit_report.md"


def _audit_row(row: dict[str, str]) -> dict[str, Any]:
    source_year = _to_int(row.get("source_year"))
    notice = _parse_date(row.get("notice_date"))
    if source_year is None or notice is None:
        status = "needs_source_review"
        severity = "high"
        lag = ""
        expected_start = ""
        expected_end = ""
        reason = "missing source_year or notice_date"
    else:
        fiscal_year_end = date(source_year, 12, 31)
        expected_start_date = date(source_year + 1, 3, 1)
        expected_end_date = date(source_year + 1, 8, 31)
        lag_value = (notice - fiscal_year_end).days
        lag = lag_value
        expected_start = expected_start_date.isoformat()
        expected_end = expected_end_date.isoformat()
        if notice < expected_start_date:
            status = "needs_source_review"
            severity = "high"
            reason = "notice_date is earlier than normal annual-report visibility window"
        elif notice > expected_end_date:
            status = "needs_source_review"
            severity = "medium"
            reason = "notice_date is later than expected annual-report visibility window"
        else:
            status = "plausible_bridge_date"
            severity = "medium"
            reason = "notice_date falls in plausible annual-report visibility window but original announcement date is not verified"
    return {
        "code": row.get("code", ""),
        "source_year": row.get("source_year", ""),
        "notice_date": row.get("notice_date", ""),
        "expected_visibility_start": expected_start,
        "expected_visibility_end": expected_end,
        "lag_days_after_fiscal_year_end": lag,
        "audit_status": status,
        "severity": severity,
        "reason": reason,
        "review_status": row.get("review_status", ""),
        "confidence": row.get("confidence", ""),
        "source_note": row.get("source_note", ""),
    }


def _decision(status_counts: Counter[str], severity_counts: Counter[str]) -> str:
    if severity_counts.get("high", 0):
        return "blocked_until_high_severity_source_dates_reviewed"
    if status_counts.get("needs_source_review", 0):
        return "continue_research_but_not_acceptance"
    return "plausible_for_research_still_needs_original_source_verification"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_report(path: Path, summary: dict[str, Any], audit_rows: list[dict[str, Any]]) -> None:
    examples = [row for row in audit_rows if row["audit_status"] != "plausible_bridge_date"][:10]
    lines = [
        f"# V4 Quality Source-Date Audit: {summary['strategy_id']}",
        "",
        f"- Rows: `{summary['row_count']}`",
        f"- Codes: `{summary['code_count']}`",
        f"- Source years: `{summary['source_year_count']}`",
        f"- Status counts: `{summary['audit_status_counts']}`",
        f"- Severity counts: `{summary['severity_counts']}`",
        f"- Mean lag days: `{summary['mean_lag_days_after_fiscal_year_end']}`",
        f"- Decision: `{summary['decision']}`",
        "",
        "## Interpretation",
        "",
        "This audit checks whether the V4 bridge `notice_date` is plausible for annual-report visibility.",
        "It does not prove the original announcement date. Rows remain `needs_check` until original reports or JoinQuant PIT behavior are reviewed.",
        "",
    ]
    if examples:
        lines.extend(["## Review Examples", ""])
        for row in examples:
            lines.append(f"- `{row['code']}` source_year=`{row['source_year']}` notice_date=`{row['notice_date']}`: {row['reason']}")
        lines.append("")
    for item in summary["limitations"]:
        lines.append(f"- {item}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _to_int(value: str | None) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(float(str(value)))
    except ValueError:
        return None


def _parse_date(value: str | None) -> date | None:
    try:
        if value in (None, ""):
            return None
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-v4-quality-source-date-audit")
    parser.add_argument("quality_csv", type=Path)
    parser.add_argument("--out", type=Path, default=Path("validation_formal"))
    parser.add_argument("--strategy-id", default="bank_high_dividend_sustainability_v3")
    args = parser.parse_args(argv)
    print(audit_v4_quality_source_dates(args.quality_csv, args.out, args.strategy_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
