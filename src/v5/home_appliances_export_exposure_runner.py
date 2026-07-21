from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from v5.credential_loader import load_tushare_token
from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.math_utils import fmt_float, ratio, to_float
from v5.paths import DEFAULT_PROCESSED_DIR


DEFAULT_PANEL = DEFAULT_PROCESSED_DIR / "home_appliances_true_state_v5a5d" / "panel_with_true_home_appliances_state.csv"
DEFAULT_OUT_DIR = DEFAULT_PROCESSED_DIR / "home_appliances_export_exposure_v5a5d"

EVIDENCE_FIELDS = [
    "code",
    "period",
    "visible_date",
    "overseas_revenue",
    "domestic_revenue",
    "segment_total_revenue",
    "overseas_revenue_share",
    "area_segment_item_count",
    "overseas_items",
    "domestic_items",
    "source_name",
    "source_url",
    "review_status",
    "notes",
]

PANEL_FIELDS = [
    "export_exposure_visible_date",
    "overseas_revenue_share",
    "overseas_revenue",
    "domestic_revenue",
    "export_exposure_source",
    "export_exposure_review_status",
]

OVERSEAS_KEYWORDS = ("国外", "境外", "海外", "国际", "外销", "出口")
DOMESTIC_KEYWORDS = ("国内", "中国大陆", "境内")


@dataclass(frozen=True)
class HomeAppliancesExportExposureResult:
    panel_csv: Path
    evidence_csv: Path
    raw_csv: Path
    summary_json: Path
    evidence_count: int
    panel_row_count: int
    status: str


def collect_home_appliances_export_exposure(
    panel_csv: Path = DEFAULT_PANEL,
    out_dir: Path = DEFAULT_OUT_DIR,
    start_year: int = 2020,
    end_year: int = 2025,
    sleep_seconds: float = 0.08,
    resume_existing: bool = True,
    token_env: str = "TUSHARE_TOKEN",
) -> HomeAppliancesExportExposureResult:
    try:
        import tushare as ts
    except Exception as exc:  # pragma: no cover - optional dependency.
        raise RuntimeError("collect-home-appliances-export-exposure requires tushare") from exc

    token = load_tushare_token(token_env)
    pro = ts.pro_api(token)
    panel_rows = read_csv_rows(panel_csv)
    codes = sorted({str(row.get("code") or "") for row in panel_rows if row.get("code")})
    periods = _periods(start_year, end_year)

    evidence_csv = out_dir / "home_appliances_export_exposure_evidence.csv"
    raw_csv = out_dir / "home_appliances_export_exposure_raw.csv"
    existing_evidence = read_csv_rows(evidence_csv) if resume_existing and evidence_csv.exists() else []
    existing_keys = {(str(row.get("code") or ""), str(row.get("period") or "")) for row in existing_evidence}
    raw_rows: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = [dict(row) for row in existing_evidence]
    warnings: list[str] = []
    for code in codes:
        ts_code = _to_ts_code(code)
        for period in periods:
            if (code, _format_period(period)) in existing_keys:
                continue
            try:
                df = pro.fina_mainbz(ts_code=ts_code, period=period)
            except Exception as exc:
                warnings.append(f"{code}:{period}: {type(exc).__name__}: {exc}")
                continue
            records = [] if df is None or getattr(df, "empty", True) else df.to_dict("records")
            for record in records:
                raw_rows.append({"code": code, **record})
            evidence = _segment_evidence(code, period, records)
            if evidence is not None:
                evidence_rows.append(evidence)
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)

    evidence_by_code = _evidence_by_code(evidence_rows)
    enriched_rows = []
    for row in panel_rows:
        code = str(row.get("code") or "")
        trade_date = str(row.get("trade_date") or "")[:10]
        evidence = _latest_visible(evidence_by_code.get(code, []), trade_date)
        enriched = dict(row)
        enriched.update(_panel_fields(evidence))
        enriched_rows.append(enriched)

    out_dir.mkdir(parents=True, exist_ok=True)
    panel_out = out_dir / "panel_with_export_exposure.csv"
    summary_json = out_dir / "home_appliances_export_exposure_summary.json"
    write_csv_rows(evidence_csv, EVIDENCE_FIELDS, evidence_rows)
    write_csv_rows(raw_csv, _raw_fieldnames(raw_rows), raw_rows)
    write_csv_rows(panel_out, _merge_fieldnames(panel_rows, PANEL_FIELDS), enriched_rows)
    coverage = _coverage(enriched_rows)
    status = "export_exposure_enriched_needs_validation" if coverage >= 0.8 else "export_exposure_incomplete_needs_review"
    write_json_file(
        summary_json,
        {
            "dataset": "home_appliances_export_exposure_v5a5d",
            "panel_csv": str(panel_csv),
            "panel_with_export_exposure": str(panel_out),
            "evidence_csv": str(evidence_csv),
            "raw_csv": str(raw_csv),
            "code_count": len(codes),
            "period_count": len(periods),
            "evidence_count": len(evidence_rows),
            "resume_existing": resume_existing,
            "existing_evidence_count": len(existing_evidence),
            "panel_row_count": len(enriched_rows),
            "panel_coverage": coverage,
            "status": status,
            "warnings": warnings[:100],
            "warning_count": len(warnings),
            "pit_policy": "Use the latest Tushare fina_mainbz region-segment record with conservative visible_date <= trade_date.",
            "source_policy": "Licensed Tushare fina_mainbz segment data; credentials are never written.",
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return HomeAppliancesExportExposureResult(panel_out, evidence_csv, raw_csv, summary_json, len(evidence_rows), len(enriched_rows), status)


def _periods(start_year: int, end_year: int) -> list[str]:
    result = []
    for year in range(start_year, end_year + 1):
        result.append(f"{year}0630")
        result.append(f"{year}1231")
    return result


def _segment_evidence(code: str, period: str, records: list[dict[str, Any]]) -> dict[str, Any] | None:
    area_records = [record for record in records if str(record.get("bz_code") or "").upper() == "D"]
    if not area_records:
        return None
    overseas = []
    domestic = []
    for record in area_records:
        item = str(record.get("bz_item") or "")
        if any(keyword in item for keyword in OVERSEAS_KEYWORDS):
            overseas.append(record)
        elif any(keyword in item for keyword in DOMESTIC_KEYWORDS):
            domestic.append(record)
    overseas_revenue = sum(to_float(record.get("bz_sales")) or 0.0 for record in overseas)
    domestic_revenue = sum(to_float(record.get("bz_sales")) or 0.0 for record in domestic)
    total_revenue = sum(to_float(record.get("bz_sales")) or 0.0 for record in area_records)
    if total_revenue <= 0:
        return None
    visible_date = _conservative_visible_date(period)
    return {
        "code": code,
        "period": _format_period(period),
        "visible_date": visible_date,
        "overseas_revenue": fmt_float(overseas_revenue),
        "domestic_revenue": fmt_float(domestic_revenue),
        "segment_total_revenue": fmt_float(total_revenue),
        "overseas_revenue_share": fmt_float(ratio(overseas_revenue, total_revenue)),
        "area_segment_item_count": len(area_records),
        "overseas_items": ";".join(str(record.get("bz_item") or "") for record in overseas),
        "domestic_items": ";".join(str(record.get("bz_item") or "") for record in domestic),
        "source_name": "Tushare fina_mainbz",
        "source_url": "https://tushare.pro/document/2?doc_id=81",
        "review_status": "tushare_mainbz_conservative_visible_date",
        "notes": "Region-segment overseas revenue share; conservative visible_date is used instead of original announcement timestamp.",
    }


def _conservative_visible_date(period: str) -> str:
    year = int(period[:4])
    if period.endswith("0630"):
        return date(year, 8, 31).isoformat()
    return date(year + 1, 4, 30).isoformat()


def _format_period(period: str) -> str:
    return f"{period[:4]}-{period[4:6]}-{period[6:8]}"


def _evidence_by_code(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        result.setdefault(str(row["code"]), []).append(row)
    for values in result.values():
        values.sort(key=lambda row: str(row.get("visible_date") or ""))
    return result


def _latest_visible(rows: list[dict[str, Any]], trade_date: str) -> dict[str, Any] | None:
    visible = [row for row in rows if str(row.get("visible_date") or "")[:10] <= trade_date]
    return visible[-1] if visible else None


def _panel_fields(evidence: dict[str, Any] | None) -> dict[str, str]:
    if evidence is None:
        return {field: "" for field in PANEL_FIELDS}
    return {
        "export_exposure_visible_date": str(evidence.get("visible_date") or ""),
        "overseas_revenue_share": str(evidence.get("overseas_revenue_share") or ""),
        "overseas_revenue": str(evidence.get("overseas_revenue") or ""),
        "domestic_revenue": str(evidence.get("domestic_revenue") or ""),
        "export_exposure_source": str(evidence.get("source_name") or ""),
        "export_exposure_review_status": str(evidence.get("review_status") or ""),
    }


def _coverage(rows: list[dict[str, str]]) -> float:
    if not rows:
        return 0.0
    return sum(1 for row in rows if row.get("overseas_revenue_share") not in ("", None)) / len(rows)


def _to_ts_code(code: str) -> str:
    if code.endswith(".XSHG"):
        return code.replace(".XSHG", ".SH")
    if code.endswith(".XSHE"):
        return code.replace(".XSHE", ".SZ")
    return code


def _raw_fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for row in rows:
        for key in row:
            if key not in names:
                names.append(key)
    return names or ["code"]


def _merge_fieldnames(rows: list[dict[str, str]], extra: list[str]) -> list[str]:
    names: list[str] = []
    for row in rows:
        for key in row:
            if key not in names:
                names.append(key)
    for key in extra:
        if key not in names:
            names.append(key)
    return names
