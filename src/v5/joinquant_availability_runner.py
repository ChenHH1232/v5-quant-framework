from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_DATABASE_DIR = Path("\u6570\u636e\u5e93")
DEFAULT_V4_QUALITY_CSV = DEFAULT_DATABASE_DIR / "processed" / "v4_legacy_bank_quality.csv"

AVAILABILITY_FIELDS = [
    "code",
    "source_year",
    "joinquant_available_date",
    "availability_type",
    "review_status",
    "confidence",
    "source_note",
]


@dataclass(frozen=True)
class JoinQuantAvailabilityResult:
    availability_path: Path
    manifest_path: Path
    row_count: int


def build_joinquant_availability_proxy(
    v4_quality_csv: Path = DEFAULT_V4_QUALITY_CSV,
    out_dir: Path = DEFAULT_DATABASE_DIR / "processed" / "joinquant_availability",
) -> JoinQuantAvailabilityResult:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for row in _read_csv_if_exists(v4_quality_csv):
        code = (row.get("code") or "").strip()
        source_year = _year_text(row.get("source_year"))
        date_text = (row.get("notice_date") or "").strip()
        if not code or not source_year or not date_text:
            continue
        rows.append(
            {
                "code": code,
                "source_year": source_year,
                "joinquant_available_date": date_text,
                "availability_type": "v4_first_visible_proxy",
                "review_status": "proxy",
                "confidence": "low",
                "source_note": "V4 first visible rebalance date proxy; not verified from current JoinQuant API because bank_indicator is unavailable.",
            }
        )
    rows.sort(key=lambda item: (item["code"], item["source_year"]))
    availability_path = out_dir / "joinquant_bank_quality_availability_proxy.csv"
    manifest_path = out_dir / "joinquant_bank_quality_availability_proxy_manifest.json"
    _write_csv(availability_path, AVAILABILITY_FIELDS, rows)
    manifest = {
        "dataset": "joinquant_bank_quality_availability_proxy",
        "availability_path": str(availability_path),
        "v4_quality_csv": str(v4_quality_csv),
        "row_count": len(rows),
        "availability_type": "v4_first_visible_proxy",
        "formal_policy": "This proxy is useful for platform-lineage diagnostics but is not sufficient for formal PIT acceptance.",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    _write_json(manifest_path, manifest)
    return JoinQuantAvailabilityResult(availability_path, manifest_path, len(rows))


def _read_csv_if_exists(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _year_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        return str(int(float(text)))
    except ValueError:
        return text


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-joinquant-availability-proxy")
    parser.add_argument("--v4-quality-csv", type=Path, default=DEFAULT_V4_QUALITY_CSV)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_DATABASE_DIR / "processed" / "joinquant_availability")
    args = parser.parse_args(argv)
    result = build_joinquant_availability_proxy(args.v4_quality_csv, args.out_dir)
    print(result.availability_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
