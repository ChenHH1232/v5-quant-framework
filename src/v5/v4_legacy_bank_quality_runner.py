from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any


DEFAULT_V4_PHASE1_PANEL = Path(r"D:\hh\codex\v4\phase_1_fundamental\phase1_training_panel.csv")
DEFAULT_DATABASE_DIR = Path("数据库")

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
class V4LegacyBankQualityResult:
    quality_path: Path
    manifest_path: Path
    row_count: int
    code_count: int
    year_count: int


def collect_v4_legacy_bank_quality(
    source_panel: Path = DEFAULT_V4_PHASE1_PANEL,
    out_dir: Path = DEFAULT_DATABASE_DIR / "processed",
) -> V4LegacyBankQualityResult:
    rows = _read_csv(source_panel)
    snapshots = _build_snapshots(rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    quality_path = out_dir / "v4_legacy_bank_quality.csv"
    manifest_path = out_dir / "v4_legacy_bank_quality_manifest.json"
    _write_csv(quality_path, QUALITY_FIELDS, snapshots)
    manifest = {
        "dataset": "v4_legacy_bank_quality",
        "source": str(source_panel),
        "quality_path": str(quality_path),
        "row_count": len(snapshots),
        "code_count": len({row["code"] for row in snapshots}),
        "year_count": len({row["source_year"] for row in snapshots}),
        "source_years": sorted({row["source_year"] for row in snapshots}),
        "visibility_policy": "notice_date is the first rebalance_date where V4 phase1 panel used the bank_indicator source_year for that code.",
        "review_policy": (
            "Rows are marked needs_source_date_review. They are useful for long-history exploratory validation, "
            "but not final acceptance until original report announcement dates or JoinQuant PIT behavior are reviewed."
        ),
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    _write_json(manifest_path, manifest)
    return V4LegacyBankQualityResult(
        quality_path=quality_path,
        manifest_path=manifest_path,
        row_count=len(snapshots),
        code_count=len({row["code"] for row in snapshots}),
        year_count=len({row["source_year"] for row in snapshots}),
    )


def _build_snapshots(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        code = row.get("code") or ""
        source_year = _to_int(row.get("bank_indicator__Nonperforming_loan_rate__source_year"))
        if not code or source_year is None:
            continue
        grouped[(code, source_year)].append(row)

    base: dict[tuple[str, int], dict[str, Any]] = {}
    for (code, source_year), items in grouped.items():
        npl = _median_field(items, "bank_indicator__Nonperforming_loan_rate")
        provision = _median_field(items, "bank_indicator__non_performing_loan_provision_coverage")
        core_capital = _median_field(items, "bank_indicator__core_level_capital_adequacy_ratio")
        capital = _median_field(items, "bank_indicator__capital_adequacy_ratio")
        if npl is None and provision is None and core_capital is None and capital is None:
            continue
        notice_date = min(row["rebalance_date"] for row in items if row.get("rebalance_date"))
        base[(code, source_year)] = {
            "code": code,
            "source_year": source_year,
            "npl_ratio": npl,
            "provision_coverage_ratio": provision,
            "core_tier_1_capital_adequacy_ratio": core_capital,
            "tier_1_capital_adequacy_ratio": "",
            "capital_adequacy_ratio": capital,
            "notice_date": notice_date,
        }

    result = []
    for (code, source_year), item in sorted(base.items()):
        previous = base.get((code, source_year - 1), {})
        npl = item.get("npl_ratio")
        previous_npl = previous.get("npl_ratio")
        if npl is None:
            asset_quality_trend = None
        elif previous_npl is None:
            asset_quality_trend = -float(npl)
        else:
            asset_quality_trend = float(previous_npl) - float(npl)
        capital_resilience = _first_not_none(
            item.get("core_tier_1_capital_adequacy_ratio"),
            item.get("tier_1_capital_adequacy_ratio"),
            item.get("capital_adequacy_ratio"),
        )
        result.append(
            {
                **item,
                "asset_quality_trend": asset_quality_trend,
                "provision_buffer": item.get("provision_coverage_ratio"),
                "capital_resilience": capital_resilience,
                "npl_ratio_prev": previous_npl,
            "review_status": "needs_check",
                "confidence": "medium",
                "source_note": "v4_phase1_joinquant_bank_indicator; notice_date is first visible rebalance_date, not original report announcement date",
            }
        )
    return result


def _median_field(rows: list[dict[str, str]], field: str) -> float | None:
    values = [_to_float(row.get(field)) for row in rows]
    values = [value for value in values if value is not None]
    return median(values) if values else None


def _first_not_none(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def _to_int(value: str | None) -> int | None:
    numeric = _to_float(value)
    return int(numeric) if numeric is not None else None


def _to_float(value: str | None) -> float | None:
    if value in (None, "", "nan", "NaN", "None"):
        return None
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return None


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
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _csv_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-v4-legacy-bank-quality")
    parser.add_argument("--source-panel", type=Path, default=DEFAULT_V4_PHASE1_PANEL)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_DATABASE_DIR / "processed")
    args = parser.parse_args(argv)
    result = collect_v4_legacy_bank_quality(args.source_panel, args.out_dir)
    print(result.quality_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
