from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_DATABASE_DIR = Path("数据库")
DEFAULT_DIVIDEND_PROCESSED = DEFAULT_DATABASE_DIR / "processed" / "bank_cash_dividends.csv"


@dataclass(frozen=True)
class DividendCollectionResult:
    processed_path: Path
    raw_path: Path
    manifest_path: Path
    code_count: int
    event_count: int
    warning_count: int


def collect_bank_dividends(
    panel_path: Path,
    database_dir: Path = DEFAULT_DATABASE_DIR,
    start_date: str | None = None,
    end_date: str | None = None,
    output_prefix: str = "",
) -> DividendCollectionResult:
    try:
        import akshare as ak
        import pandas as pd
    except Exception as exc:  # pragma: no cover - exercised only when optional dependency is missing.
        raise RuntimeError("collect-bank-dividends requires akshare and pandas in the local Python environment") from exc

    codes = _load_codes_from_panel(panel_path)
    raw_dir = database_dir / "raw" / "dividends"
    processed_dir = database_dir / "processed"
    manifest_dir = database_dir / "manifests"
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    raw_frames = []
    processed_rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    start = _optional_date(start_date)
    end = _optional_date(end_date)

    for code in codes:
        symbol = _to_plain_symbol(code)
        try:
            raw_df = ak.stock_fhps_detail_em(symbol=symbol)
        except Exception as exc:
            warnings.append(f"{code}: {repr(exc)}")
            continue
        if raw_df is None or raw_df.empty:
            warnings.append(f"{code}: no dividend rows returned")
            continue

        raw_copy = raw_df.copy()
        raw_copy.insert(0, "code", code)
        raw_copy.insert(1, "symbol", symbol)
        raw_frames.append(raw_copy)

        for row in raw_df.to_dict(orient="records"):
            event = _normalize_akshare_dividend_row(code, row)
            if event is None:
                continue
            event_date = _parse_date(event["ex_date"])
            if start and event_date < start:
                continue
            if end and event_date > end:
                continue
            processed_rows.append(event)

    safe_prefix = _safe_output_prefix(output_prefix)
    raw_path = raw_dir / (f"{safe_prefix}akshare_dividends_raw.csv" if safe_prefix else "akshare_bank_dividends_raw.csv")
    if raw_frames:
        pd.concat(raw_frames, ignore_index=True).to_csv(raw_path, index=False, encoding="utf-8-sig")
    else:
        raw_path.write_text("", encoding="utf-8")

    processed_rows.sort(key=lambda item: (item["ex_date"], item["code"]))
    processed_path = processed_dir / (f"{safe_prefix}cash_dividends.csv" if safe_prefix else "bank_cash_dividends.csv")
    _write_csv(
        processed_path,
        [
            "code",
            "report_period",
            "announce_date",
            "record_date",
            "ex_date",
            "cash_per_10_shares",
            "cash_per_share",
            "dividend_yield_reported",
            "plan_status",
            "source",
        ],
        processed_rows,
    )

    manifest = {
        "dataset": "bank_cash_dividends",
        "source": "akshare.stock_fhps_detail_em",
        "panel": str(panel_path),
        "database_dir": str(database_dir),
        "output_prefix": safe_prefix,
        "raw_path": str(raw_path),
        "processed_path": str(processed_path),
        "code_count": len(codes),
        "event_count": len(processed_rows),
        "start_date": start_date,
        "end_date": end_date,
        "warnings": warnings,
        "schema": {
            "cash_per_10_shares": "Cash dividend amount per 10 shares, tax included when reported by the source.",
            "cash_per_share": "cash_per_10_shares / 10. Used by V5 total-return construction.",
            "ex_date": "Ex-dividend date used to assign cash dividends to holding periods.",
            "announce_date": "Latest announcement date used for point-in-time trailing dividend yield.",
        },
        "agent_access": ["Quant Validation Agent", "Engineering Agent"],
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    manifest_path = manifest_dir / (f"{safe_prefix}cash_dividends_manifest.json" if safe_prefix else "bank_cash_dividends_manifest.json")
    _write_json(manifest_path, manifest)

    return DividendCollectionResult(
        processed_path=processed_path,
        raw_path=raw_path,
        manifest_path=manifest_path,
        code_count=len(codes),
        event_count=len(processed_rows),
        warning_count=len(warnings),
    )


def _load_codes_from_panel(panel_path: Path) -> list[str]:
    with panel_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = csv.DictReader(handle)
        codes = sorted({str(row.get("code", "")).strip() for row in rows if row.get("code")})
    return [code for code in codes if code]


def _normalize_akshare_dividend_row(code: str, row: dict[str, Any]) -> dict[str, str] | None:
    cash_per_10 = _to_float(row.get("现金分红-现金分红比例"))
    ex_date = _date_text(row.get("除权除息日"))
    if cash_per_10 is None or cash_per_10 <= 0 or not ex_date:
        return None
    announce_date = _date_text(row.get("最新公告日期") or row.get("业绩披露日期") or row.get("预案公告日"))
    return {
        "code": code,
        "report_period": str(row.get("报告期") or ""),
        "announce_date": announce_date,
        "record_date": _date_text(row.get("股权登记日")),
        "ex_date": ex_date,
        "cash_per_10_shares": _fmt_float(cash_per_10),
        "cash_per_share": _fmt_float(cash_per_10 / 10.0),
        "dividend_yield_reported": _fmt_float(_to_float(row.get("现金分红-股息率"))),
        "plan_status": str(row.get("方案进度") or ""),
        "source": "akshare.stock_fhps_detail_em",
    }


def _to_plain_symbol(code: str) -> str:
    return code.split(".", 1)[0]


def _safe_output_prefix(value: str) -> str:
    if not value:
        return ""
    cleaned = "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in value.strip())
    if cleaned and not cleaned.endswith(("_", "-")):
        cleaned += "_"
    return cleaned


def _optional_date(value: str | None):
    if not value:
        return None
    return _parse_date(value)


def _parse_date(value: str):
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()


def _date_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    if not text or text == "NaT" or text.lower() == "nan":
        return ""
    try:
        return _parse_date(text).isoformat()
    except ValueError:
        return ""


def _to_float(value: Any) -> float | None:
    if value in {None, "", "nan", "NaN", "None"}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fmt_float(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.10g}"


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-dividends")
    parser.add_argument("panel", type=Path)
    parser.add_argument("--database-dir", type=Path, default=DEFAULT_DATABASE_DIR)
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--output-prefix", default="")
    args = parser.parse_args(argv)

    result = collect_bank_dividends(args.panel, args.database_dir, args.start_date, args.end_date, args.output_prefix)
    print(result.processed_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
