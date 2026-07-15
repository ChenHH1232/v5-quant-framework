from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_DATABASE_DIR = Path("\u6570\u636e\u5e93")
DEFAULT_V4_QUALITY_CSV = DEFAULT_DATABASE_DIR / "processed" / "v4_legacy_bank_quality.csv"
DEFAULT_EASTMONEY_QUALITY_CSV = DEFAULT_DATABASE_DIR / "processed" / "eastmoney_bank_quality_manual_csv.csv"

ALIGNMENT_FIELDS = [
    "code",
    "source_year",
    "eastmoney_notice_date",
    "joinquant_available_date",
    "local_first_use_date",
    "conservative_visible_date",
    "formal_pit_usable",
    "date_alignment_status",
    "missing_date_types",
    "date_gap_notes",
    "review_status",
    "confidence",
    "source_notes",
]


@dataclass(frozen=True)
class BankQualityDateAlignmentResult:
    alignment_path: Path
    manifest_path: Path
    report_path: Path
    row_count: int
    formal_usable_count: int
    blocked_count: int


def align_bank_quality_dates(
    out_dir: Path,
    v4_quality_csv: Path = DEFAULT_V4_QUALITY_CSV,
    eastmoney_quality_csv: Path = DEFAULT_EASTMONEY_QUALITY_CSV,
    joinquant_availability_csv: Path | None = None,
) -> BankQualityDateAlignmentResult:
    out_dir.mkdir(parents=True, exist_ok=True)
    sources: dict[tuple[str, str], dict[str, Any]] = {}

    for row in _read_csv_if_exists(v4_quality_csv):
        code = _normalize_code(row.get("code"))
        year = _normalize_year(row.get("source_year"))
        if not code or not year:
            continue
        item = sources.setdefault((code, year), _empty_item(code, year))
        item["local_first_use_date"] = _latest_date(item.get("local_first_use_date"), row.get("notice_date"))
        item["review_statuses"].add(row.get("review_status") or "")
        item["confidences"].add(row.get("confidence") or "")
        item["source_notes"].add(row.get("source_note") or "v4_legacy_bank_quality")

    for row in _read_csv_if_exists(eastmoney_quality_csv):
        code = _normalize_code(row.get("code"))
        year = _normalize_year(row.get("source_year"))
        if not code or not year:
            continue
        item = sources.setdefault((code, year), _empty_item(code, year))
        item["eastmoney_notice_date"] = _latest_date(item.get("eastmoney_notice_date"), row.get("notice_date"))
        item["review_statuses"].add(row.get("review_status") or "")
        item["confidences"].add(row.get("confidence") or "")
        item["source_notes"].add(row.get("source_note") or "eastmoney_bank_quality")

    if joinquant_availability_csv:
        for row in _read_csv_if_exists(joinquant_availability_csv):
            code = _normalize_code(row.get("code"))
            year = _normalize_year(row.get("source_year") or row.get("report_year"))
            jq_date = (
                row.get("joinquant_available_date")
                or row.get("jq_available_date")
                or row.get("available_date")
                or row.get("notice_date")
            )
            if not code or not year:
                continue
            item = sources.setdefault((code, year), _empty_item(code, year))
            item["joinquant_available_date"] = _latest_date(item.get("joinquant_available_date"), jq_date)
            item["review_statuses"].add(row.get("review_status") or "needs_check")
            item["confidences"].add(row.get("confidence") or "")
            item["source_notes"].add(row.get("source_note") or "joinquant_availability_csv")

    rows = [_finalize_item(item) for _, item in sorted(sources.items())]
    alignment_path = out_dir / "bank_quality_date_alignment.csv"
    manifest_path = out_dir / "bank_quality_date_alignment_manifest.json"
    report_path = out_dir / "bank_quality_date_alignment_report.md"
    _write_csv(alignment_path, ALIGNMENT_FIELDS, rows)

    status_counts: dict[str, int] = {}
    for row in rows:
        status_counts[row["date_alignment_status"]] = status_counts.get(row["date_alignment_status"], 0) + 1
    formal_usable_count = sum(1 for row in rows if row["formal_pit_usable"] == "true")
    blocked_count = len(rows) - formal_usable_count

    manifest = {
        "dataset": "bank_quality_date_alignment",
        "alignment_path": str(alignment_path),
        "v4_quality_csv": str(v4_quality_csv),
        "eastmoney_quality_csv": str(eastmoney_quality_csv),
        "joinquant_availability_csv": str(joinquant_availability_csv) if joinquant_availability_csv else "",
        "row_count": len(rows),
        "formal_usable_count": formal_usable_count,
        "blocked_count": blocked_count,
        "status_counts": status_counts,
        "alignment_rule": "conservative_visible_date = max(eastmoney_notice_date, joinquant_available_date, local_first_use_date) when all three are known.",
        "formal_policy": "Rows are formal PIT usable only when original announcement date, JoinQuant availability date, and local first-use date are all present.",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    _write_json(manifest_path, manifest)
    _write_report(report_path, manifest, rows)

    return BankQualityDateAlignmentResult(
        alignment_path=alignment_path,
        manifest_path=manifest_path,
        report_path=report_path,
        row_count=len(rows),
        formal_usable_count=formal_usable_count,
        blocked_count=blocked_count,
    )


def _empty_item(code: str, year: str) -> dict[str, Any]:
    return {
        "code": code,
        "source_year": year,
        "eastmoney_notice_date": "",
        "joinquant_available_date": "",
        "local_first_use_date": "",
        "review_statuses": set(),
        "confidences": set(),
        "source_notes": set(),
    }


def _finalize_item(item: dict[str, Any]) -> dict[str, str]:
    eastmoney_date = item.get("eastmoney_notice_date") or ""
    jq_date = item.get("joinquant_available_date") or ""
    local_date = item.get("local_first_use_date") or ""
    known_dates = [_parse_date(value) for value in [eastmoney_date, jq_date, local_date] if value]
    conservative = max(known_dates).isoformat() if known_dates else ""

    missing = []
    if not eastmoney_date:
        missing.append("eastmoney_notice_date")
    if not jq_date:
        missing.append("joinquant_available_date")
    if not local_date:
        missing.append("local_first_use_date")

    notes = []
    if eastmoney_date and local_date:
        delta = (_parse_date(local_date) - _parse_date(eastmoney_date)).days
        notes.append(f"local_minus_eastmoney_days={delta}")
    if jq_date and eastmoney_date:
        delta = (_parse_date(jq_date) - _parse_date(eastmoney_date)).days
        notes.append(f"joinquant_minus_eastmoney_days={delta}")
    if jq_date and local_date:
        delta = (_parse_date(local_date) - _parse_date(jq_date)).days
        notes.append(f"local_minus_joinquant_days={delta}")

    if not missing:
        status = "aligned_formal_pit_ready"
        formal_usable = "true"
    elif len(missing) == 3:
        status = "no_date_evidence"
        formal_usable = "false"
    else:
        status = "blocked_missing_" + "_and_".join(missing)
        formal_usable = "false"

    return {
        "code": item["code"],
        "source_year": item["source_year"],
        "eastmoney_notice_date": eastmoney_date,
        "joinquant_available_date": jq_date,
        "local_first_use_date": local_date,
        "conservative_visible_date": conservative,
        "formal_pit_usable": formal_usable,
        "date_alignment_status": status,
        "missing_date_types": ";".join(missing),
        "date_gap_notes": ";".join(notes),
        "review_status": "|".join(sorted(value for value in item["review_statuses"] if value)),
        "confidence": "|".join(sorted(value for value in item["confidences"] if value)),
        "source_notes": " || ".join(sorted(value for value in item["source_notes"] if value)),
    }


def _write_report(path: Path, manifest: dict[str, Any], rows: list[dict[str, str]]) -> None:
    examples = rows[:]
    blocked_examples = [row for row in examples if row["formal_pit_usable"] != "true"][:10]
    lines = [
        "# Bank Quality Date Alignment Report",
        "",
        f"Generated: {manifest['created_at_utc']}",
        "",
        "## Alignment Rule",
        "",
        "`conservative_visible_date = max(eastmoney_notice_date, joinquant_available_date, local_first_use_date)`",
        "",
        "A row is formal PIT usable only when all three dates are known. Missing dates are kept explicit instead of being filled from another source.",
        "",
        "## Summary",
        "",
        f"- rows: {manifest['row_count']}",
        f"- formal usable rows: {manifest['formal_usable_count']}",
        f"- blocked rows: {manifest['blocked_count']}",
        "",
        "## Status Counts",
        "",
    ]
    for status, count in sorted(manifest["status_counts"].items()):
        lines.append(f"- `{status}`: {count}")
    lines.extend(["", "## Blocked Examples", ""])
    if not blocked_examples:
        lines.append("No blocked examples.")
    else:
        lines.extend(["| Code | Year | Missing Dates | Conservative Date | Notes |", "| --- | ---: | --- | --- | --- |"])
        for row in blocked_examples:
            lines.append(
                f"| {row['code']} | {row['source_year']} | {row['missing_date_types']} | {row['conservative_visible_date']} | {row['date_gap_notes']} |"
            )
    lines.extend(
        [
            "",
            "## PM Decision Rule",
            "",
            "Project Manager Agent must block formal strategy acceptance if a candidate depends on rows whose `formal_pit_usable` is not `true`.",
            "Platform replication may still use JoinQuant-specific visibility modes, but those runs must stay in `platform_replication`.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _latest_date(current: str | None, incoming: str | None) -> str:
    current_text = (current or "").strip()
    incoming_text = (incoming or "").strip()
    if not incoming_text:
        return current_text
    if not current_text:
        return incoming_text
    return max(_parse_date(current_text), _parse_date(incoming_text)).isoformat()


def _parse_date(value: str) -> date:
    return date.fromisoformat(str(value).strip()[:10])


def _normalize_code(value: str | None) -> str:
    text = (value or "").strip()
    if text.endswith(".SZ"):
        return text[:-3] + ".XSHE"
    if text.endswith(".SS") or text.endswith(".SH"):
        return text.split(".")[0] + ".XSHG"
    return text


def _normalize_year(value: str | None) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    try:
        return str(int(float(text)))
    except ValueError:
        return text


def _read_csv_if_exists(path: Path) -> list[dict[str, str]]:
    if not path or not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-bank-quality-date-alignment")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_DATABASE_DIR / "processed" / "bank_quality_date_alignment")
    parser.add_argument("--v4-quality-csv", type=Path, default=DEFAULT_V4_QUALITY_CSV)
    parser.add_argument("--eastmoney-quality-csv", type=Path, default=DEFAULT_EASTMONEY_QUALITY_CSV)
    parser.add_argument("--joinquant-availability-csv", type=Path)
    args = parser.parse_args(argv)
    result = align_bank_quality_dates(
        args.out_dir,
        v4_quality_csv=args.v4_quality_csv,
        eastmoney_quality_csv=args.eastmoney_quality_csv,
        joinquant_availability_csv=args.joinquant_availability_csv,
    )
    print(result.alignment_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
