from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.credential_loader import DEFAULT_CREDENTIAL_FILE, load_tushare_token


DEFAULT_DATABASE_DIR = Path("\u6570\u636e\u5e93")
DEFAULT_QUALITY_CSV = DEFAULT_DATABASE_DIR / "processed" / "v4_legacy_bank_quality.csv"

DISCLOSURE_FIELDS = [
    "code",
    "ts_code",
    "source_year",
    "report_period",
    "notice_date",
    "notice_date_source",
    "ann_date",
    "pre_date",
    "actual_date",
    "modify_date",
    "review_status",
    "confidence",
    "source_note",
]


@dataclass(frozen=True)
class TushareDisclosureResult:
    disclosure_path: Path
    manifest_path: Path
    row_count: int
    requested_count: int
    warning_count: int


def collect_tushare_disclosure_dates(
    quality_csv: Path = DEFAULT_QUALITY_CSV,
    out_dir: Path = DEFAULT_DATABASE_DIR / "processed" / "tushare_disclosure_dates",
    credential_file: Path = DEFAULT_CREDENTIAL_FILE,
    token_env: str = "TUSHARE_TOKEN",
) -> TushareDisclosureResult:
    out_dir.mkdir(parents=True, exist_ok=True)
    targets = _load_targets(quality_csv)
    disclosure_path = out_dir / "tushare_bank_annual_disclosure_dates.csv"
    manifest_path = out_dir / "tushare_bank_annual_disclosure_manifest.json"
    token = load_tushare_token(token_env, credential_file)
    warnings: list[str] = []
    rows: list[dict[str, Any]] = []

    if not token:
        warnings.append(f"Tushare token not found in {token_env} or credential file.")
    else:
        try:
            import tushare as ts

            pro = ts.pro_api(token)
            rows = _fetch_disclosure_rows(pro, targets, warnings)
        except Exception as exc:
            warnings.append(f"tushare disclosure_date collection failed: {type(exc).__name__}: {exc}")

    _write_csv(disclosure_path, DISCLOSURE_FIELDS, rows)
    manifest = {
        "dataset": "tushare_bank_annual_disclosure_dates",
        "quality_csv": str(quality_csv),
        "disclosure_path": str(disclosure_path),
        "requested_count": len(targets),
        "row_count": len(rows),
        "warning_count": len(warnings),
        "warnings": warnings,
        "credential_policy": f"Token loaded from {token_env} or local credential file. Token is never written.",
        "date_policy": "notice_date uses actual_date first, then ann_date, then pre_date. pre_date-only rows are marked low confidence.",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    _write_json(manifest_path, manifest)
    return TushareDisclosureResult(
        disclosure_path=disclosure_path,
        manifest_path=manifest_path,
        row_count=len(rows),
        requested_count=len(targets),
        warning_count=len(warnings),
    )


def _fetch_disclosure_rows(pro: Any, targets: set[tuple[str, str]], warnings: list[str]) -> list[dict[str, Any]]:
    by_ts_code: dict[str, set[str]] = {}
    for code, year in targets:
        by_ts_code.setdefault(_to_ts_code(code), set()).add(year)

    rows: list[dict[str, Any]] = []
    for ts_code, years in sorted(by_ts_code.items()):
        try:
            df = pro.disclosure_date(ts_code=ts_code)
        except Exception as exc:
            warnings.append(f"{ts_code}: disclosure_date failed: {type(exc).__name__}: {exc}")
            continue
        if df is None or getattr(df, "empty", True):
            warnings.append(f"{ts_code}: disclosure_date returned no rows")
            continue
        for raw in df.to_dict("records"):
            report_period = _date_text(raw.get("end_date"))
            if not report_period or not report_period.endswith("1231"):
                continue
            source_year = report_period[:4]
            if source_year not in years:
                continue
            ann_date = _date_text(raw.get("ann_date"))
            pre_date = _date_text(raw.get("pre_date"))
            actual_date = _date_text(raw.get("actual_date"))
            modify_date = _date_text(raw.get("modify_date"))
            notice_date, source, confidence = _choose_notice_date(actual_date, ann_date, pre_date)
            if not notice_date:
                warnings.append(f"{ts_code} {source_year}: missing actual/ann/pre date")
                continue
            rows.append(
                {
                    "code": _from_ts_code(ts_code),
                    "ts_code": ts_code,
                    "source_year": source_year,
                    "report_period": _format_date(report_period),
                    "notice_date": _format_date(notice_date),
                    "notice_date_source": source,
                    "ann_date": _format_date(ann_date),
                    "pre_date": _format_date(pre_date),
                    "actual_date": _format_date(actual_date),
                    "modify_date": _format_date(modify_date),
                    "review_status": "needs_check",
                    "confidence": confidence,
                    "source_note": "tushare.disclosure_date annual report disclosure schedule",
                }
            )
    return sorted(rows, key=lambda item: (item["code"], item["source_year"]))


def _load_targets(path: Path) -> set[tuple[str, str]]:
    targets: set[tuple[str, str]] = set()
    if not path.exists():
        return targets
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            code = (row.get("code") or "").strip()
            year = _year_text(row.get("source_year"))
            if code and year:
                targets.add((code, year))
    return targets


def _choose_notice_date(actual_date: str, ann_date: str, pre_date: str) -> tuple[str, str, str]:
    if actual_date:
        return actual_date, "actual_date", "high"
    if ann_date:
        return ann_date, "ann_date", "medium"
    if pre_date:
        return pre_date, "pre_date", "low"
    return "", "", "low"


def _to_ts_code(code: str) -> str:
    if code.endswith(".XSHE"):
        return code[:6] + ".SZ"
    if code.endswith(".XSHG"):
        return code[:6] + ".SH"
    return code


def _from_ts_code(ts_code: str) -> str:
    if ts_code.endswith(".SZ"):
        return ts_code[:6] + ".XSHE"
    if ts_code.endswith(".SH"):
        return ts_code[:6] + ".XSHG"
    return ts_code


def _date_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text or text.lower() == "nan":
        return ""
    return text[:10].replace("-", "")


def _format_date(value: str) -> str:
    text = _date_text(value)
    if len(text) != 8:
        return ""
    return f"{text[:4]}-{text[4:6]}-{text[6:]}"


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
    parser = argparse.ArgumentParser(prog="v5-tushare-disclosure-dates")
    parser.add_argument("--quality-csv", type=Path, default=DEFAULT_QUALITY_CSV)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_DATABASE_DIR / "processed" / "tushare_disclosure_dates")
    parser.add_argument("--credential-file", type=Path, default=DEFAULT_CREDENTIAL_FILE)
    parser.add_argument("--token-env", default="TUSHARE_TOKEN")
    args = parser.parse_args(argv)
    result = collect_tushare_disclosure_dates(args.quality_csv, args.out_dir, args.credential_file, args.token_env)
    print(result.disclosure_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
