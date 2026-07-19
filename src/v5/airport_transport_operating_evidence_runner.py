from __future__ import annotations

import time
import json
import re
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.credential_loader import DEFAULT_CREDENTIAL_FILE, load_tushare_token
from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.math_utils import fmt_float, ratio, to_float


DEFAULT_OUT_DIR = Path("\u6570\u636e\u5e93") / "processed" / "airport_transport_operating_evidence_v58"

REPORT_DISCLOSURE_FIELDS = [
    "code",
    "ts_code",
    "report_period",
    "report_type",
    "notice_date",
    "notice_date_source",
    "ann_date",
    "pre_date",
    "actual_date",
    "modify_date",
    "source_name",
    "review_status",
    "notes",
]

SEGMENT_RAW_FIELDS = [
    "code",
    "eastmoney_code",
    "report_period",
    "mainop_type",
    "item_name",
    "main_business_income",
    "income_ratio",
    "main_business_cost",
    "cost_ratio",
    "main_business_profit",
    "profit_ratio",
    "gross_profit_ratio",
    "source_name",
    "source_url",
]

SEGMENT_EVIDENCE_FIELDS = [
    "code",
    "ts_code",
    "report_period",
    "report_type",
    "notice_date",
    "visible_date",
    "selected_mainop_type",
    "aviation_service_revenue_share",
    "airport_commercial_revenue_share",
    "airport_operator_revenue_share",
    "non_airport_revenue_share",
    "largest_non_airport_item",
    "largest_non_airport_revenue_ratio",
    "approved_airport_business_tag",
    "source_name",
    "source_url",
    "pit_usable",
    "review_status",
    "notes",
]

PANEL_EXTRA_FIELDS = [
    "airport_report_period",
    "airport_visible_date",
    "aviation_service_revenue_share",
    "airport_commercial_revenue_share",
    "airport_operator_revenue_share",
    "non_airport_revenue_share",
    "approved_airport_business_tag",
    "business_purity_gate",
    "business_purity_review_status",
]

OPERATING_ANNOUNCEMENT_FIELDS = [
    "code",
    "company_name",
    "announcement_date",
    "visible_date",
    "title",
    "matched_keyword",
    "report_month",
    "art_code",
    "source_name",
    "source_url",
    "pit_usable",
    "review_status",
    "notes",
]

OPERATING_STATE_VALUE_FIELDS = [
    "code",
    "company_name",
    "report_month",
    "visible_date",
    "source_title",
    "source_url",
    "pdf_url",
    "passenger_throughput",
    "passenger_unit",
    "passenger_throughput_yoy",
    "cargo_throughput",
    "cargo_unit",
    "cargo_throughput_yoy",
    "aircraft_movements",
    "aircraft_unit",
    "aircraft_movements_yoy",
    "page_size",
    "pit_usable",
    "extraction_status",
    "review_status",
    "evidence_snippet",
    "notes",
]

OPERATING_CONTENT_ERROR_FIELDS = [
    "code",
    "company_name",
    "report_month",
    "visible_date",
    "title",
    "art_code",
    "source_url",
    "error",
]

AVIATION_SERVICE_TERMS = (
    "\u673a\u573a",
    "\u822a\u7a7a\u6027",
    "\u822a\u7a7a\u6027\u6536\u5165",
    "\u822a\u7a7a\u4e3b\u4e1a",
    "\u822a\u7a7a\u670d\u52a1\u4e1a",
    "\u822a\u7a7a\u4e1a\u52a1",
    "\u822a\u7a7a\u4e1a\u52a1\u6536\u5165",
    "\u822a\u7a7a\u53ca\u76f8\u5173\u670d\u52a1",
    "\u822a\u7a7a\u670d\u52a1",
    "\u8d77\u964d",
    "\u5730\u9762\u670d\u52a1",
    "\u5730\u9762\u670d\u52a1\u6536\u5165",
    "\u5730\u52e4",
    "\u5019\u673a\u697c",
    "\u65c5\u5ba2\u670d\u52a1",
    "\u8d27\u90ae",
    "\u8d27\u7ad9",
    "\u8d27\u670d",
)
AIRPORT_COMMERCIAL_TERMS = (
    "\u975e\u822a\u7a7a\u6027",
    "\u5546\u4e1a",
    "\u514d\u7a0e",
    "\u79df\u8d41",
    "\u79df\u8d41\u53ca\u7279\u8bb8",
    "\u7279\u8bb8\u7ecf\u8425",
    "\u5e7f\u544a",
    "\u5546\u8d38",
    "\u8d35\u5bbe",
)
NON_AIRPORT_TERMS = (
    "\u623f\u5730\u4ea7",
    "\u7269\u4e1a",
    "\u9152\u5e97",
    "\u4f1a\u5c55",
    "\u7269\u6d41",
    "\u8d27\u8fd0\u4ee3\u7406",
    "\u822a\u7a7a\u8fd0\u8f93",
    "\u822a\u7a7a\u5ba2\u8fd0",
    "\u822a\u7a7a\u516c\u53f8",
    "\u8d38\u6613",
    "\u6295\u8d44",
)

OPERATING_ANNOUNCEMENT_KEYWORDS = (
    "\u8fd0\u8f93\u751f\u4ea7\u60c5\u51b5\u7b80\u62a5",
    "\u8fd0\u8425\u751f\u4ea7\u60c5\u51b5\u7b80\u62a5",
    "\u751f\u4ea7\u7ecf\u8425\u5feb\u62a5",
    "\u751f\u4ea7\u7ecf\u8425\u6570\u636e",
    "\u7ecf\u8425\u6570\u636e",
    "\u8fd0\u8f93\u751f\u4ea7",
    "\u65c5\u5ba2\u541e\u5410\u91cf",
    "\u8d27\u90ae\u541e\u5410\u91cf",
)


def collect_airport_report_disclosure_dates(
    panel_csv: Path,
    out_dir: Path = DEFAULT_OUT_DIR,
    credential_file: Path = DEFAULT_CREDENTIAL_FILE,
    token_env: str = "TUSHARE_TOKEN",
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    panel_rows = read_csv_rows(panel_csv)
    codes = sorted({row["code"] for row in panel_rows if row.get("code")})
    target_years = _target_report_years(panel_rows)
    warnings: list[str] = []
    rows: list[dict[str, Any]] = []
    token = load_tushare_token(token_env, credential_file)
    if not token:
        warnings.append(f"Tushare token not found in {token_env} or credential file.")
    else:
        try:
            import tushare as ts

            pro = ts.pro_api(token)
            rows = _fetch_disclosure_rows(pro, codes, target_years, warnings)
        except Exception as exc:
            warnings.append(f"tushare disclosure_date collection failed: {type(exc).__name__}: {exc}")

    out_path = out_dir / "airport_report_disclosure_dates.csv"
    write_csv_rows(out_path, REPORT_DISCLOSURE_FIELDS, rows)
    write_json_file(
        out_dir / "airport_report_disclosure_dates_manifest.json",
        {
            "dataset": "airport_report_disclosure_dates",
            "panel": str(panel_csv),
            "output": str(out_path),
            "code_count": len(codes),
            "target_years": sorted(target_years),
            "row_count": len(rows),
            "warning_count": len(warnings),
            "warnings": warnings,
            "source_policy": "Tushare disclosure_date supplies report timing only. It does not prove airport operating exposure.",
            "created_at_utc": _now_utc(),
        },
    )
    return out_path


def collect_eastmoney_airport_segment_evidence(
    panel_csv: Path,
    disclosure_csv: Path,
    out_dir: Path = DEFAULT_OUT_DIR,
    *,
    request_timeout_seconds: float = 15.0,
    sleep_seconds: float = 0.25,
    limit: int | None = None,
) -> Path:
    panel_rows = read_csv_rows(panel_csv)
    codes = sorted({row.get("code", "") for row in panel_rows if row.get("code")})
    if limit is not None:
        codes = codes[:limit]
    disclosures = _disclosures_by_code_period(disclosure_csv)
    raw_rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    for code in codes:
        try:
            records = _fetch_eastmoney_segment_records(code, request_timeout_seconds)
        except Exception as exc:
            warnings.append(f"{code}: Eastmoney segment fetch failed: {type(exc).__name__}: {exc}")
            continue
        if not records:
            warnings.append(f"{code}: Eastmoney segment fetch returned no zygcfx rows")
        raw_rows.extend(_normalize_eastmoney_segment_records(code, records))
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    evidence_rows = _build_segment_evidence_from_raw(raw_rows, disclosures)
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / "eastmoney_airport_segment_raw.csv"
    evidence_path = out_dir / "airport_segment_business_evidence_eastmoney.csv"
    write_csv_rows(raw_path, SEGMENT_RAW_FIELDS, raw_rows)
    write_csv_rows(evidence_path, SEGMENT_EVIDENCE_FIELDS, evidence_rows)
    usable = [row for row in evidence_rows if str(row.get("pit_usable", "")).lower() == "true"]
    tag_counts = Counter(row.get("approved_airport_business_tag", "") for row in evidence_rows)
    write_json_file(
        out_dir / "eastmoney_airport_segment_evidence_manifest.json",
        {
            "dataset": "eastmoney_airport_segment_evidence",
            "panel": str(panel_csv),
            "disclosure_csv": str(disclosure_csv),
            "raw_output": str(raw_path),
            "evidence_output": str(evidence_path),
            "requested_company_count": len(codes),
            "raw_row_count": len(raw_rows),
            "evidence_row_count": len(evidence_rows),
            "pit_usable_rows": len(usable),
            "covered_company_count": len({row["code"] for row in usable if row.get("code")}),
            "tag_counts": dict(sorted(tag_counts.items())),
            "warning_count": len(warnings),
            "warnings": warnings,
            "source_policy": "Eastmoney public F10 BusinessAnalysis/PageAjax via normal HTTP request with timeout and no anti-crawler bypass.",
            "pit_policy": "visible_date is joined from Tushare disclosure_date for the same report period when available.",
            "limitations": [
                "Eastmoney segment evidence is first-layer structured evidence only.",
                "Annual/interim report spot checks remain required before formal Engineering handoff.",
                "Passenger throughput, cargo throughput, international-route recovery and duty-free/rental terms are not certified by this file.",
            ],
            "created_at_utc": _now_utc(),
        },
    )
    return evidence_path


def build_airport_business_purity_panel(
    panel_csv: Path,
    evidence_csv: Path,
    out_dir: Path = DEFAULT_OUT_DIR / "business_purity_panel",
    *,
    min_operator_share: float = 0.5,
) -> Path:
    panel_rows = read_csv_rows(panel_csv)
    evidence_rows = read_csv_rows(evidence_csv)
    evidence_by_code: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in evidence_rows:
        if row.get("code") and row.get("visible_date"):
            evidence_by_code[row["code"]].append(row)
    for rows in evidence_by_code.values():
        rows.sort(key=lambda item: (item.get("visible_date", ""), item.get("report_period", "")))

    passed_rows: list[dict[str, Any]] = []
    removed_rows: list[dict[str, Any]] = []
    for row in panel_rows:
        visible = _latest_visible_evidence(evidence_by_code.get(row.get("code", ""), []), row.get("trade_date", ""))
        enriched = dict(row)
        gate = "missing_visible_business_evidence"
        if visible:
            for field in [
                "report_period",
                "visible_date",
                "aviation_service_revenue_share",
                "airport_commercial_revenue_share",
                "airport_operator_revenue_share",
                "non_airport_revenue_share",
                "approved_airport_business_tag",
                "review_status",
            ]:
                target = f"airport_{field}" if field in {"report_period", "visible_date"} else field
                enriched[target] = visible.get(field, "")
            operator_share = to_float(visible.get("airport_operator_revenue_share")) or 0.0
            tag = visible.get("approved_airport_business_tag", "")
            if operator_share >= min_operator_share and tag in {"core_airport_operator", "airport_commercial_mixed_operator"}:
                gate = "passed"
            else:
                gate = "failed_non_airport_contamination"
        for field in PANEL_EXTRA_FIELDS:
            enriched.setdefault(field, "")
        enriched["business_purity_gate"] = gate
        enriched["business_purity_review_status"] = "eastmoney_first_layer_needs_spot_check" if gate == "passed" else gate
        if gate == "passed":
            passed_rows.append(enriched)
        else:
            removed_rows.append(enriched)

    out_dir.mkdir(parents=True, exist_ok=True)
    fieldnames = list(panel_rows[0].keys()) + [field for field in PANEL_EXTRA_FIELDS if field not in panel_rows[0]]
    panel_path = out_dir / "panel_business_purity_passed.csv"
    write_csv_rows(panel_path, fieldnames, passed_rows)
    write_csv_rows(out_dir / "removed_by_business_purity_gate.csv", fieldnames, removed_rows)
    write_csv_rows(
        out_dir / "business_purity_coverage_by_rebalance.csv",
        ["trade_date", "total_rows", "passed_rows", "removed_rows", "coverage_ratio"],
        _coverage_rows(panel_rows, passed_rows, removed_rows),
    )
    write_json_file(
        out_dir / "business_purity_gate_manifest.json",
        {
            "dataset": "airport_business_purity_gate_v58",
            "source_panel": str(panel_csv),
            "evidence_csv": str(evidence_csv),
            "passed_panel": str(panel_path),
            "source_panel_rows": len(panel_rows),
            "passed_rows": len(passed_rows),
            "removed_rows_count": len(removed_rows),
            "passed_code_count": len({row["code"] for row in passed_rows if row.get("code")}),
            "min_operator_share": min_operator_share,
            "source_policy": "Eastmoney segment evidence is first-layer only; annual/interim report spot checks are still required.",
            "created_at_utc": _now_utc(),
        },
    )
    return panel_path


def collect_eastmoney_airport_operating_announcements(
    panel_csv: Path,
    out_dir: Path = DEFAULT_OUT_DIR,
    *,
    begin_date: str = "2021-01-01",
    end_date: str = "2026-05-31",
    request_timeout_seconds: float = 15.0,
    sleep_seconds: float = 0.25,
    limit: int | None = None,
) -> Path:
    panel_rows = read_csv_rows(panel_csv)
    code_names = _code_names(panel_rows)
    codes = sorted(code_names)
    if limit is not None:
        codes = codes[:limit]
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    for code in codes:
        try:
            records = _fetch_eastmoney_announcement_records(
                code,
                begin_date=begin_date,
                end_date=end_date,
                timeout_seconds=request_timeout_seconds,
            )
        except Exception as exc:
            warnings.append(f"{code}: Eastmoney announcement fetch failed: {type(exc).__name__}: {exc}")
            continue
        matched = _operating_announcement_rows(code, code_names.get(code, ""), records)
        rows.extend(matched)
        if not matched:
            warnings.append(f"{code}: no operating announcement title matched configured keywords")
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "eastmoney_airport_operating_announcement_index.csv"
    write_csv_rows(out_path, OPERATING_ANNOUNCEMENT_FIELDS, sorted(rows, key=lambda row: (row["code"], row["announcement_date"], row["title"])))
    write_json_file(
        out_dir / "eastmoney_airport_operating_announcement_index_manifest.json",
        {
            "dataset": "eastmoney_airport_operating_announcement_index",
            "panel": str(panel_csv),
            "output": str(out_path),
            "begin_date": begin_date,
            "end_date": end_date,
            "requested_company_count": len(codes),
            "matched_row_count": len(rows),
            "matched_company_count": len({row["code"] for row in rows}),
            "warning_count": len(warnings),
            "warnings": warnings,
            "source_policy": "Eastmoney notice index is used as announcement discovery and visible-date evidence only; PDF/content extraction is a separate review step.",
            "pit_policy": "visible_date is the announcement_date exposed by the public Eastmoney announcement index.",
            "limitations": [
                "This index does not certify passenger, cargo or aircraft movement values.",
                "The original exchange/CNINFO PDF still needs parsing or manual review before state values enter Quant validation.",
                "Title matching may miss announcements with unusual wording.",
            ],
            "created_at_utc": _now_utc(),
        },
    )
    return out_path


def extract_airport_operating_state_values(
    announcement_index_csv: Path,
    out_dir: Path = DEFAULT_OUT_DIR / "operating_state_values",
    *,
    request_timeout_seconds: float = 12.0,
    sleep_seconds: float = 0.15,
    max_workers: int = 1,
    content_cache_dir: Path | None = None,
    cache_only: bool = False,
    limit: int | None = None,
) -> Path:
    index_rows = [row for row in read_csv_rows(announcement_index_csv) if row.get("art_code") and row.get("report_month")]
    if limit is not None:
        index_rows = index_rows[:limit]
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    workers = max(1, max_workers)
    if workers == 1:
        for row in index_rows:
            value_row, warning = _extract_one_operating_value(row, request_timeout_seconds, content_cache_dir, cache_only)
            rows.append(value_row)
            if warning:
                warnings.append(warning)
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(_extract_one_operating_value, row, request_timeout_seconds, content_cache_dir, cache_only): row
                for row in index_rows
            }
            for future in as_completed(futures):
                value_row, warning = future.result()
                rows.append(value_row)
                if warning:
                    warnings.append(warning)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "airport_operating_state_value_candidates.csv"
    rows = sorted(rows, key=lambda row: (row.get("code", ""), row.get("report_month", ""), row.get("visible_date", "")))
    write_csv_rows(out_path, OPERATING_STATE_VALUE_FIELDS, rows)
    status_counts = Counter(row.get("extraction_status", "") for row in rows)
    write_json_file(
        out_dir / "airport_operating_state_value_extraction_manifest.json",
        {
            "dataset": "airport_operating_state_value_candidates",
            "announcement_index_csv": str(announcement_index_csv),
            "output": str(out_path),
            "input_row_count": len(index_rows),
            "max_workers": workers,
            "content_cache_dir": str(content_cache_dir) if content_cache_dir else "",
            "cache_only": cache_only,
            "output_row_count": len(rows),
            "complete_candidate_count": status_counts.get("complete_candidate", 0),
            "status_counts": dict(sorted(status_counts.items())),
            "warning_count": len(warnings),
            "warnings": warnings,
            "source_policy": "Eastmoney cnotice content API is used to extract text candidates from public operating announcements.",
            "pit_policy": "visible_date remains the announcement_date from the announcement index.",
            "review_policy": "Extracted values are candidates only. Research Agent must spot-check company PDF/original announcement rows before Quant validation.",
            "created_at_utc": _now_utc(),
        },
    )
    return out_path


def cache_airport_operating_announcement_contents(
    announcement_index_csv: Path,
    out_dir: Path = DEFAULT_OUT_DIR / "operating_content_cache",
    *,
    request_timeout_seconds: float = 12.0,
    sleep_seconds: float = 0.15,
    max_workers: int = 1,
    limit: int | None = None,
    code: str | None = None,
    start_month: str | None = None,
    end_month: str | None = None,
    retry_failed: bool = False,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = _filtered_operating_index_rows(
        announcement_index_csv,
        limit=limit,
        code=code,
        start_month=start_month,
        end_month=end_month,
    )
    workers = max(1, max_workers)
    work_rows = [row for row in rows if retry_failed or not _content_cache_path(out_dir, row["art_code"]).exists()]
    errors: list[dict[str, Any]] = []
    fetched = 0
    skipped = len(rows) - len(work_rows)
    if workers == 1:
        for row in work_rows:
            ok, error = _cache_one_operating_content(row, out_dir, request_timeout_seconds)
            fetched += 1 if ok else 0
            if error:
                errors.append(error)
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(_cache_one_operating_content, row, out_dir, request_timeout_seconds): row
                for row in work_rows
            }
            for future in as_completed(futures):
                ok, error = future.result()
                fetched += 1 if ok else 0
                if error:
                    errors.append(error)

    error_path = out_dir / "airport_operating_content_cache_errors.csv"
    write_csv_rows(error_path, OPERATING_CONTENT_ERROR_FIELDS, errors)
    manifest_path = out_dir / "airport_operating_content_cache_manifest.json"
    write_json_file(
        manifest_path,
        {
            "dataset": "airport_operating_content_cache",
            "announcement_index_csv": str(announcement_index_csv),
            "cache_dir": str(out_dir),
            "selected_row_count": len(rows),
            "work_row_count": len(work_rows),
            "skipped_cached_count": skipped,
            "fetched_count": fetched,
            "error_count": len(errors),
            "max_workers": workers,
            "filters": {
                "code": code or "",
                "start_month": start_month or "",
                "end_month": end_month or "",
                "limit": limit,
                "retry_failed": retry_failed,
            },
            "source_policy": "Eastmoney public cnotice content endpoint is cached per announcement art_code. Cache is a data-ingestion reliability layer, not research validation.",
            "review_policy": "Cached content and extracted values remain candidates until original announcement/PDF spot checks pass.",
            "created_at_utc": _now_utc(),
        },
    )
    return manifest_path


def _extract_one_operating_value(
    row: dict[str, str],
    request_timeout_seconds: float,
    content_cache_dir: Path | None = None,
    cache_only: bool = False,
) -> tuple[dict[str, Any], str]:
    try:
        content = _read_cached_operating_content(content_cache_dir, row["art_code"]) if content_cache_dir else None
        if content is None and cache_only:
            return (
                _operating_value_error_row(row, "content_cache_missing"),
                f"{row.get('code')} {row.get('report_month')}: content cache missing",
            )
        if content is None:
            content = _fetch_eastmoney_announcement_content(row["art_code"], timeout_seconds=request_timeout_seconds)
    except Exception as exc:
        return (
            _operating_value_error_row(row, f"content_fetch_failed:{type(exc).__name__}"),
            f"{row.get('code')} {row.get('report_month')}: content fetch failed: {type(exc).__name__}: {exc}",
        )
    return _operating_value_row(row, content), ""


def _build_segment_evidence_from_raw(raw_rows: list[dict[str, Any]], disclosures: dict[tuple[str, str], dict[str, str]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in raw_rows:
        code = str(row.get("code") or "")
        report_period = str(row.get("report_period") or "")
        if code and report_period:
            by_key[(code, report_period)].append(row)

    evidence_rows = []
    for (code, report_period), rows in sorted(by_key.items()):
        selected_type, selected = _select_segment_layer(rows)
        ratios = _airport_segment_ratios(selected)
        disclosure = disclosures.get((code, report_period), {})
        visible_date = disclosure.get("notice_date", "")
        tag = _approved_airport_business_tag(ratios)
        pit_usable = bool(visible_date and tag != "non_airport_or_needs_review")
        evidence_rows.append(
            {
                "code": code,
                "ts_code": _to_ts_code(code),
                "report_period": report_period,
                "report_type": "semiannual" if report_period.endswith("-06-30") else "annual" if report_period.endswith("-12-31") else "other",
                "notice_date": visible_date,
                "visible_date": visible_date,
                "selected_mainop_type": selected_type,
                "aviation_service_revenue_share": fmt_float(ratios["aviation_service_revenue_share"]),
                "airport_commercial_revenue_share": fmt_float(ratios["airport_commercial_revenue_share"]),
                "airport_operator_revenue_share": fmt_float(ratios["airport_operator_revenue_share"]),
                "non_airport_revenue_share": fmt_float(ratios["non_airport_revenue_share"]),
                "largest_non_airport_item": ratios["largest_non_airport_item"],
                "largest_non_airport_revenue_ratio": fmt_float(ratios["largest_non_airport_revenue_ratio"]),
                "approved_airport_business_tag": tag,
                "source_name": "Eastmoney F10 BusinessAnalysis/PageAjax + Tushare disclosure_date",
                "source_url": f"https://emweb.securities.eastmoney.com/PC_HSF10/BusinessAnalysis/Index?type=web&code={_to_eastmoney_code(code)}",
                "pit_usable": "true" if pit_usable else "false",
                "review_status": "eastmoney_segment_needs_spot_check" if pit_usable else "needs_review_or_not_core",
                "notes": _segment_notes(selected, ratios),
            }
        )
    return evidence_rows


def _select_segment_layer(rows: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    for mainop_type in ("product", "industry"):
        selected = [row for row in rows if row.get("mainop_type") == mainop_type and not _is_segment_subitem(str(row.get("item_name") or ""))]
        if selected:
            return mainop_type, selected
    selected = [row for row in rows if not _is_segment_subitem(str(row.get("item_name") or ""))]
    return "all_non_region" if selected else "all", selected or rows


def _airport_segment_ratios(rows: list[dict[str, Any]]) -> dict[str, Any]:
    weights = [_segment_weight(row) for row in rows]
    total = sum(weight for weight in weights if weight > 0)
    aviation_total = 0.0
    commercial_total = 0.0
    non_airport: list[tuple[str, float]] = []
    for row, amount in zip(rows, weights):
        name = str(row.get("item_name") or "")
        bucket = _segment_bucket(name)
        if bucket == "aviation_service":
            aviation_total += amount
        elif bucket == "airport_commercial":
            commercial_total += amount
        else:
            non_airport.append((name, amount))
    airport_total = aviation_total + commercial_total
    largest_non_name, largest_non_amount = ("", 0.0)
    if non_airport:
        largest_non_name, largest_non_amount = max(non_airport, key=lambda item: item[1])
    return {
        "aviation_service_revenue_share": ratio(aviation_total, total),
        "airport_commercial_revenue_share": ratio(commercial_total, total),
        "airport_operator_revenue_share": ratio(airport_total, total),
        "non_airport_revenue_share": ratio(max(0.0, total - airport_total), total),
        "largest_non_airport_item": largest_non_name,
        "largest_non_airport_revenue_ratio": ratio(largest_non_amount, total),
    }


def _segment_bucket(name: str) -> str:
    if any(term in name for term in NON_AIRPORT_TERMS):
        return "non_airport"
    if any(term in name for term in AIRPORT_COMMERCIAL_TERMS):
        return "airport_commercial"
    if any(term in name for term in AVIATION_SERVICE_TERMS):
        return "aviation_service"
    return "non_airport"


def _approved_airport_business_tag(ratios: dict[str, Any]) -> str:
    aviation_share = to_float(ratios.get("aviation_service_revenue_share")) or 0.0
    commercial_share = to_float(ratios.get("airport_commercial_revenue_share")) or 0.0
    operator_share = to_float(ratios.get("airport_operator_revenue_share")) or 0.0
    if aviation_share >= 0.5:
        return "core_airport_operator"
    if operator_share >= 0.5 and commercial_share > 0:
        return "airport_commercial_mixed_operator"
    return "non_airport_or_needs_review"


def _fetch_disclosure_rows(pro: Any, codes: list[str], target_years: set[str], warnings: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for code in codes:
        ts_code = _to_ts_code(code)
        try:
            df = pro.disclosure_date(ts_code=ts_code)
        except Exception as exc:
            warnings.append(f"{code}: tushare disclosure_date failed: {type(exc).__name__}: {exc}")
            continue
        if df is None or getattr(df, "empty", True):
            warnings.append(f"{code}: tushare disclosure_date returned empty")
            continue
        for raw in df.to_dict("records"):
            end_date = _date_text(raw.get("end_date"))
            if not end_date or end_date[:4] not in target_years:
                continue
            if not (end_date.endswith("1231") or end_date.endswith("0630")):
                continue
            ann_date = _date_text(raw.get("ann_date"))
            pre_date = _date_text(raw.get("pre_date"))
            actual_date = _date_text(raw.get("actual_date"))
            modify_date = _date_text(raw.get("modify_date"))
            notice_date, source = _choose_notice_date(actual_date, ann_date, pre_date)
            if not notice_date:
                warnings.append(f"{code} {end_date}: missing report disclosure date")
                continue
            rows.append(
                {
                    "code": code,
                    "ts_code": ts_code,
                    "report_period": _format_date(end_date),
                    "report_type": "semiannual" if end_date.endswith("0630") else "annual",
                    "notice_date": _format_date(notice_date),
                    "notice_date_source": source,
                    "ann_date": _format_date(ann_date),
                    "pre_date": _format_date(pre_date),
                    "actual_date": _format_date(actual_date),
                    "modify_date": _format_date(modify_date),
                    "source_name": "tushare.disclosure_date",
                    "review_status": "report_date_only_operating_evidence_required",
                    "notes": "Use this as report timing evidence only; operating fields still require original report review.",
                }
            )
    return sorted(rows, key=lambda row: (row["code"], row["report_period"], row["report_type"]))


def _fetch_eastmoney_segment_records(code: str, timeout_seconds: float) -> list[dict[str, Any]]:
    import requests

    eastmoney_code = _to_eastmoney_code(code)
    url = "https://emweb.securities.eastmoney.com/PC_HSF10/BusinessAnalysis/PageAjax"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": f"https://emweb.securities.eastmoney.com/PC_HSF10/BusinessAnalysis/Index?type=web&code={eastmoney_code}",
    }
    response = requests.get(url, params={"code": eastmoney_code}, headers=headers, timeout=(5, timeout_seconds))
    response.raise_for_status()
    payload = response.json()
    records = payload.get("zygcfx") or []
    return records if isinstance(records, list) else []


def _fetch_eastmoney_announcement_records(
    code: str,
    *,
    begin_date: str,
    end_date: str,
    timeout_seconds: float,
) -> list[dict[str, Any]]:
    import requests

    url = "https://np-anotice-stock.eastmoney.com/api/security/ann"
    params = {
        "sr": "-1",
        "page_size": "100",
        "page_index": "1",
        "ann_type": "A",
        "client_source": "web",
        "stock_list": code[:6],
        "f_node": "0",
        "s_node": "0",
        "begin_time": begin_date,
        "end_time": end_date,
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": f"https://data.eastmoney.com/notices/stock/{code[:6]}.html",
    }
    first = requests.get(url, params=params, headers=headers, timeout=(5, timeout_seconds))
    first.raise_for_status()
    payload = first.json()
    data = payload.get("data") or {}
    total_hits = int(data.get("total_hits") or 0)
    total_pages = max(1, (total_hits + 99) // 100)
    records: list[dict[str, Any]] = []
    for page in range(1, total_pages + 1):
        params["page_index"] = str(page)
        response = first if page == 1 else requests.get(url, params=params, headers=headers, timeout=(5, timeout_seconds))
        response.raise_for_status()
        page_payload = response.json()
        page_records = (page_payload.get("data") or {}).get("list") or []
        if isinstance(page_records, list):
            records.extend(page_records)
    return records


def _fetch_eastmoney_announcement_content(art_code: str, *, timeout_seconds: float) -> dict[str, Any]:
    import requests

    response = requests.get(
        "https://np-cnotice-stock.eastmoney.com/api/content/ann",
        params={"art_code": art_code, "client_source": "web", "page_index": "1"},
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://data.eastmoney.com/notices/"},
        timeout=(5, timeout_seconds),
    )
    response.raise_for_status()
    payload = response.json()
    data = payload.get("data") or {}
    if not isinstance(data, dict) or not data.get("notice_title"):
        raise ValueError("announcement content missing notice_title")
    return data


def _filtered_operating_index_rows(
    announcement_index_csv: Path,
    *,
    limit: int | None,
    code: str | None,
    start_month: str | None,
    end_month: str | None,
) -> list[dict[str, str]]:
    rows = [row for row in read_csv_rows(announcement_index_csv) if row.get("art_code") and row.get("report_month")]
    if code:
        rows = [row for row in rows if row.get("code") == code]
    if start_month:
        rows = [row for row in rows if row.get("report_month", "") >= start_month]
    if end_month:
        rows = [row for row in rows if row.get("report_month", "") <= end_month]
    rows = sorted(rows, key=lambda row: (row.get("code", ""), row.get("report_month", ""), row.get("visible_date", "")))
    if limit is not None:
        rows = rows[:limit]
    return rows


def _content_cache_path(cache_dir: Path, art_code: str) -> Path:
    safe_art_code = re.sub(r"[^A-Za-z0-9_.-]", "_", art_code)
    return cache_dir / f"{safe_art_code}.json"


def _cache_one_operating_content(row: dict[str, str], cache_dir: Path, request_timeout_seconds: float) -> tuple[bool, dict[str, Any] | None]:
    try:
        content = _fetch_eastmoney_announcement_content(row["art_code"], timeout_seconds=request_timeout_seconds)
        payload = {
            "art_code": row.get("art_code", ""),
            "code": row.get("code", ""),
            "company_name": row.get("company_name", ""),
            "report_month": row.get("report_month", ""),
            "visible_date": row.get("visible_date", ""),
            "source_url": row.get("source_url", ""),
            "cached_at_utc": _now_utc(),
            "content": content,
        }
        write_json_file(_content_cache_path(cache_dir, row["art_code"]), payload)
        return True, None
    except Exception as exc:
        error = {
            "code": row.get("code", ""),
            "company_name": row.get("company_name", ""),
            "report_month": row.get("report_month", ""),
            "visible_date": row.get("visible_date", ""),
            "title": row.get("title", ""),
            "art_code": row.get("art_code", ""),
            "source_url": row.get("source_url", ""),
            "error": f"{type(exc).__name__}: {exc}",
        }
        return False, error


def _read_cached_operating_content(cache_dir: Path | None, art_code: str) -> dict[str, Any] | None:
    if cache_dir is None:
        return None
    path = _content_cache_path(cache_dir, art_code)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    content = payload.get("content") if isinstance(payload, dict) else None
    if not isinstance(content, dict):
        raise ValueError(f"cached content missing content object: {path}")
    return content


def _operating_announcement_rows(code: str, company_name: str, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        title = str(record.get("title") or "").strip()
        matched = _matched_operating_keyword(title)
        if not matched:
            continue
        announcement_date = _format_date(_date_text(record.get("notice_date")))
        art_code = str(record.get("art_code") or "").strip()
        report_month = _infer_report_month(title)
        rows.append(
            {
                "code": code,
                "company_name": company_name,
                "announcement_date": announcement_date,
                "visible_date": announcement_date,
                "title": title,
                "matched_keyword": matched,
                "report_month": report_month,
                "art_code": art_code,
                "source_name": "Eastmoney announcement index",
                "source_url": f"https://data.eastmoney.com/notices/detail/{code[:6]}/{art_code}.html" if art_code else "",
                "pit_usable": "true" if announcement_date and report_month else "false",
                "review_status": "announcement_index_only_pdf_value_extraction_required",
                "notes": "Use this row to locate the original operating briefing; passenger/cargo/aircraft movement values are not extracted here.",
            }
        )
    return rows


def _operating_value_row(index_row: dict[str, str], content: dict[str, Any]) -> dict[str, Any]:
    text = str(content.get("notice_content") or "")
    parsed = _parse_airport_operating_text(text)
    status = "complete_candidate" if _parsed_complete(parsed) else "partial_candidate_needs_review"
    return {
        "code": index_row.get("code", ""),
        "company_name": index_row.get("company_name", ""),
        "report_month": index_row.get("report_month", ""),
        "visible_date": index_row.get("visible_date", ""),
        "source_title": str(content.get("notice_title") or index_row.get("title", "")),
        "source_url": index_row.get("source_url", ""),
        "pdf_url": str(content.get("attach_url_web") or _first_attach_url(content)),
        "passenger_throughput": parsed.get("passenger_throughput", ""),
        "passenger_unit": parsed.get("passenger_unit", ""),
        "passenger_throughput_yoy": parsed.get("passenger_throughput_yoy", ""),
        "cargo_throughput": parsed.get("cargo_throughput", ""),
        "cargo_unit": parsed.get("cargo_unit", ""),
        "cargo_throughput_yoy": parsed.get("cargo_throughput_yoy", ""),
        "aircraft_movements": parsed.get("aircraft_movements", ""),
        "aircraft_unit": parsed.get("aircraft_unit", ""),
        "aircraft_movements_yoy": parsed.get("aircraft_movements_yoy", ""),
        "page_size": str(content.get("page_size") or ""),
        "pit_usable": "false",
        "extraction_status": status,
        "review_status": "candidate_needs_original_pdf_spot_check",
        "evidence_snippet": parsed.get("evidence_snippet", ""),
        "notes": "Candidate extracted from Eastmoney announcement text. Keep out of formal Quant validation until spot-checked against original PDF/content.",
    }


def _operating_value_error_row(index_row: dict[str, str], status: str) -> dict[str, Any]:
    return {
        "code": index_row.get("code", ""),
        "company_name": index_row.get("company_name", ""),
        "report_month": index_row.get("report_month", ""),
        "visible_date": index_row.get("visible_date", ""),
        "source_title": index_row.get("title", ""),
        "source_url": index_row.get("source_url", ""),
        "pit_usable": "false",
        "extraction_status": status,
        "review_status": "content_fetch_failed",
        "notes": "Announcement index row exists, but content could not be fetched.",
    }


def _parse_airport_operating_text(text: str) -> dict[str, str]:
    lines = [_clean_line(line) for line in text.splitlines()]
    lines = [line for line in lines if line]
    parsed: dict[str, str] = {}
    _merge_field_line(parsed, lines, "passenger", ("旅客吞吐量",))
    _merge_field_line(parsed, lines, "cargo", ("货邮吞吐量",))
    _merge_field_line(parsed, lines, "aircraft", ("航班起降架次", "飞机起降架次", "飞机起降", "起降架次"))
    if not _parsed_complete(parsed):
        _merge_total_row_table(parsed, lines)
    return parsed


def _merge_field_line(parsed: dict[str, str], lines: list[str], kind: str, labels: tuple[str, ...]) -> None:
    for line in lines:
        if not any(label in line for label in labels) or "其中" in line:
            continue
        numbers = _numbers(line)
        if not numbers:
            continue
        value, yoy = _value_and_yoy(numbers)
        unit = _unit_from_line(line, kind)
        if kind == "passenger":
            parsed.update({"passenger_throughput": value, "passenger_unit": unit, "passenger_throughput_yoy": yoy})
        elif kind == "cargo":
            parsed.update({"cargo_throughput": value, "cargo_unit": unit, "cargo_throughput_yoy": yoy})
        else:
            parsed.update({"aircraft_movements": value, "aircraft_unit": unit, "aircraft_movements_yoy": yoy})
        parsed.setdefault("evidence_snippet", line[:500])
        return


def _merge_total_row_table(parsed: dict[str, str], lines: list[str]) -> None:
    for index, line in enumerate(lines):
        if not (line.startswith("总计") or line.startswith("合计")):
            continue
        context = " ".join(lines[max(0, index - 3) : index + 1])
        if not all(term in context for term in ("旅客吞吐量", "货邮吞吐量")):
            continue
        numbers = _numbers(line)
        if len(numbers) < 6:
            continue
        parsed.setdefault("aircraft_movements", numbers[0])
        parsed.setdefault("aircraft_movements_yoy", numbers[1])
        parsed.setdefault("aircraft_unit", "架次")
        parsed.setdefault("passenger_throughput", numbers[2])
        parsed.setdefault("passenger_throughput_yoy", numbers[3])
        parsed.setdefault("passenger_unit", "万人次")
        parsed.setdefault("cargo_throughput", numbers[4])
        parsed.setdefault("cargo_throughput_yoy", numbers[5])
        parsed.setdefault("cargo_unit", "万吨")
        parsed.setdefault("evidence_snippet", context[:500])
        return


def _value_and_yoy(numbers: list[str]) -> tuple[str, str]:
    value = numbers[0]
    yoy = ""
    for item in numbers[1:]:
        if item.endswith("%"):
            yoy = item
            break
    return value, yoy


def _numbers(text: str) -> list[str]:
    return [match.group(0).replace(",", "") for match in re.finditer(r"-?\d[\d,]*(?:\.\d+)?%?", text)]


def _unit_from_line(line: str, kind: str) -> str:
    match = re.search(r"\uff08([^）]+)\uff09|\(([^)]+)\)", line)
    if match:
        return match.group(1) or match.group(2) or ""
    defaults = {"passenger": "万人次", "cargo": "万吨", "aircraft": "架次"}
    return defaults[kind]


def _clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.replace("\u3000", " ")).strip()


def _parsed_complete(parsed: dict[str, str]) -> bool:
    return all(parsed.get(field) for field in ("passenger_throughput", "cargo_throughput", "aircraft_movements"))


def _first_attach_url(content: dict[str, Any]) -> str:
    for key in ("attach_list", "attach_list_ch"):
        values = content.get(key) or []
        if isinstance(values, list):
            for item in values:
                if isinstance(item, dict) and item.get("attach_url"):
                    return str(item["attach_url"])
    return ""


def _normalize_eastmoney_segment_records(code: str, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        report_period = _format_date(_date_text(record.get("REPORT_DATE")))
        if not report_period:
            continue
        rows.append(
            {
                "code": code,
                "eastmoney_code": _to_eastmoney_code(code),
                "report_period": report_period,
                "mainop_type": _mainop_type_name(record.get("MAINOP_TYPE")),
                "item_name": str(record.get("ITEM_NAME") or "").strip(),
                "main_business_income": fmt_float(record.get("MAIN_BUSINESS_INCOME")),
                "income_ratio": fmt_float(record.get("MBI_RATIO")),
                "main_business_cost": fmt_float(record.get("MAIN_BUSINESS_COST")),
                "cost_ratio": fmt_float(record.get("MBC_RATIO")),
                "main_business_profit": fmt_float(record.get("MAIN_BUSINESS_RPOFIT")),
                "profit_ratio": fmt_float(record.get("MBR_RATIO")),
                "gross_profit_ratio": fmt_float(record.get("GROSS_RPOFIT_RATIO")),
                "source_name": "Eastmoney F10 BusinessAnalysis",
                "source_url": f"https://emweb.securities.eastmoney.com/PC_HSF10/BusinessAnalysis/Index?type=web&code={_to_eastmoney_code(code)}",
            }
        )
    return rows


def _matched_operating_keyword(title: str) -> str:
    for keyword in OPERATING_ANNOUNCEMENT_KEYWORDS:
        if keyword in title:
            return keyword
    return ""


def _infer_report_month(title: str) -> str:
    match = re.search(r"(?P<year>20\d{2})\s*\u5e74\s*(?P<month>1[0-2]|0?[1-9])\s*\u6708", title)
    if not match:
        match = re.search(r"(?P<year>20\d{2})\s*\u5e74[^\d]{0,6}(?P<month>1[0-2]|0?[1-9])\s*\u6708", title)
    if not match:
        return ""
    return f"{match.group('year')}-{int(match.group('month')):02d}"


def _code_names(rows: list[dict[str, str]]) -> dict[str, str]:
    names: dict[str, str] = {}
    for row in rows:
        code = row.get("code", "")
        if not code:
            continue
        names.setdefault(code, row.get("name") or row.get("company_name") or "")
    return names


def _segment_weight(row: dict[str, Any]) -> float:
    amount = to_float(row.get("main_business_income"))
    if amount is not None and amount > 0:
        return amount
    income_ratio = to_float(row.get("income_ratio"))
    if income_ratio is None:
        return 0.0
    return income_ratio * 100.0 if income_ratio <= 1.5 else income_ratio


def _latest_visible_evidence(rows: list[dict[str, str]], trade_date: str) -> dict[str, str] | None:
    visible = None
    trade_key = str(trade_date)[:10]
    for row in rows:
        if str(row.get("visible_date", ""))[:10] <= trade_key:
            visible = row
        else:
            break
    return visible


def _coverage_rows(panel_rows: list[dict[str, str]], passed_rows: list[dict[str, Any]], removed_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    total_by_date = Counter(row.get("trade_date", "") for row in panel_rows)
    passed_by_date = Counter(row.get("trade_date", "") for row in passed_rows)
    removed_by_date = Counter(row.get("trade_date", "") for row in removed_rows)
    rows = []
    for trade_date in sorted(total_by_date):
        total = total_by_date[trade_date]
        passed = passed_by_date[trade_date]
        rows.append(
            {
                "trade_date": trade_date,
                "total_rows": total,
                "passed_rows": passed,
                "removed_rows": removed_by_date[trade_date],
                "coverage_ratio": fmt_float(ratio(passed, total)),
            }
        )
    return rows


def _target_report_years(rows: list[dict[str, str]]) -> set[str]:
    years = set()
    for row in rows:
        text = str(row.get("trade_date", ""))[:4]
        if not text.isdigit():
            continue
        year = int(text)
        years.add(str(year))
        years.add(str(year - 1))
    return {year for year in years if "2013" <= year <= "2026"}


def _disclosures_by_code_period(disclosure_csv: Path) -> dict[tuple[str, str], dict[str, str]]:
    result = {}
    if not disclosure_csv.exists():
        return result
    for row in read_csv_rows(disclosure_csv):
        code = row.get("code", "")
        report_period = row.get("report_period", "")
        if code and report_period:
            result[(code, report_period)] = row
    return result


def _choose_notice_date(actual_date: str, ann_date: str, pre_date: str) -> tuple[str, str]:
    if actual_date:
        return actual_date, "actual_date"
    if ann_date:
        return ann_date, "ann_date"
    if pre_date:
        return pre_date, "pre_date"
    return "", ""


def _segment_notes(rows: list[dict[str, Any]], ratios: dict[str, Any]) -> str:
    items = [str(row.get("item_name") or "") for row in rows if row.get("item_name")]
    return (
        f"selected_items={'|'.join(items[:12])}; "
        f"largest_non_airport={ratios.get('largest_non_airport_item')}; "
        "Eastmoney structured segment evidence requires original annual/interim report spot check before final PIT promotion."
    )


def _is_segment_subitem(name: str) -> bool:
    return name.startswith("\u5176\u4e2d") or name.startswith("\u5176\u4e2d\uff1a") or name.startswith("\u5176\u4e2d:")


def _mainop_type_name(value: Any) -> str:
    text = str(value or "").strip()
    return {"1": "industry", "2": "product", "3": "region"}.get(text, text)


def _to_ts_code(code: str) -> str:
    if code.endswith(".XSHE"):
        return code[:6] + ".SZ"
    if code.endswith(".XSHG"):
        return code[:6] + ".SH"
    return code


def _to_eastmoney_code(code: str) -> str:
    if code.endswith(".XSHE"):
        return "SZ" + code[:6]
    if code.endswith(".XSHG"):
        return "SH" + code[:6]
    return code


def _date_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text or text.lower() == "nan":
        return ""
    return "".join(ch for ch in text[:10] if ch.isdigit())


def _format_date(value: str) -> str:
    text = _date_text(value)
    if len(text) != 8:
        return ""
    return f"{text[:4]}-{text[4:6]}-{text[6:8]}"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
