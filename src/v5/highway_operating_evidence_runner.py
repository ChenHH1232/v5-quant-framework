from __future__ import annotations

import argparse
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.credential_loader import DEFAULT_CREDENTIAL_FILE, load_tushare_token
from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.math_utils import fmt_float, ratio, to_float


DEFAULT_OUT_DIR = Path("数据库") / "processed" / "highway_operating_data"
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
    "highway_revenue_ratio",
    "toll_revenue_ratio",
    "transport_infrastructure_revenue_ratio",
    "non_highway_revenue_ratio",
    "largest_non_highway_item",
    "largest_non_highway_revenue_ratio",
    "approved_highway_business_tag",
    "source_name",
    "source_url",
    "pit_usable",
    "review_status",
    "notes",
]
OPERATING_TEMPLATE_FIELDS = [
    "code",
    "ts_code",
    "report_period",
    "report_type",
    "notice_date",
    "visible_date",
    "traffic_volume_yoy",
    "toll_revenue_yoy",
    "toll_revenue_amount",
    "remaining_concession_years",
    "toll_policy_change_flag",
    "toll_policy_description",
    "non_highway_revenue_ratio",
    "approved_highway_business_tag",
    "source_name",
    "source_url",
    "pit_usable",
    "review_status",
    "notes",
]
REPORT_MANIFEST_FIELDS = [
    "sector",
    "code",
    "company_name",
    "report_period",
    "publish_date",
    "visible_date",
    "source_title",
    "source_url",
    "local_path",
]
OPERATING_CANDIDATE_FIELDS = [
    "code",
    "report_period",
    "field",
    "candidate_value",
    "unit",
    "source_title",
    "source_url",
    "local_path",
    "page_number",
    "matched_term",
    "evidence_snippet",
    "review_status",
    "pit_status",
]
REVIEWED_OPERATING_FIELDS = [
    "code",
    "report_period",
    "visible_date",
    "traffic_toll_table_available",
    "toll_revenue_evidence_available",
    "remaining_concession_evidence_available",
    "toll_policy_evidence_available",
    "reviewed_operating_disclosure_score",
    "source_title",
    "source_url",
    "local_path",
    "pit_usable",
    "review_status",
    "notes",
]
SEGMENT_SPOT_CHECK_FIELDS = [
    "code",
    "report_period",
    "item_name",
    "main_business_income",
    "income_ratio",
    "source_title",
    "local_path",
    "item_name_found_in_report",
    "income_amount_found_in_report",
    "spot_check_status",
    "notes",
]
OPERATING_FIELD_TERMS = {
    "traffic_volume_yoy": ["车流量", "交通量", "通行量", "折算全程日均车流量", "日均车流量"],
    "toll_revenue_amount": ["通行费收入", "收费公路收入", "车辆通行费收入", "路费收入"],
    "toll_revenue_yoy": ["通行费收入同比", "通行费收入较上年", "通行费收入比上年", "车辆通行费收入同比"],
    "remaining_concession_years": ["收费期限", "经营期限", "特许经营期限", "收费经营权", "剩余收费期限"],
    "toll_policy_change_flag": ["收费政策", "收费标准", "收费费率", "免费通行", "减免通行费"],
}


def collect_highway_report_disclosure_dates(
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

    out_path = out_dir / "highway_report_disclosure_dates.csv"
    write_csv_rows(out_path, REPORT_DISCLOSURE_FIELDS, rows)
    write_json_file(
        out_dir / "highway_report_disclosure_dates_manifest.json",
        {
            "dataset": "highway_report_disclosure_dates",
            "panel": str(panel_csv),
            "output": str(out_path),
            "code_count": len(codes),
            "target_years": sorted(target_years),
            "row_count": len(rows),
            "warning_count": len(warnings),
            "warnings": warnings,
            "source_policy": "Tushare disclosure_date supplies report timing only. It does not prove highway operating exposure.",
            "pit_policy": "Operating fields remain blocked until joined with segment evidence or original annual/interim report evidence.",
            "created_at_utc": _now_utc(),
        },
    )
    return out_path


def collect_eastmoney_highway_segment_evidence(
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
    raw_path = out_dir / "eastmoney_highway_segment_raw.csv"
    evidence_path = out_dir / "highway_segment_business_evidence_eastmoney.csv"
    write_csv_rows(raw_path, SEGMENT_RAW_FIELDS, raw_rows)
    write_csv_rows(evidence_path, SEGMENT_EVIDENCE_FIELDS, evidence_rows)
    usable = [row for row in evidence_rows if str(row.get("pit_usable", "")).lower() == "true"]
    write_json_file(
        out_dir / "eastmoney_highway_segment_evidence_manifest.json",
        {
            "dataset": "eastmoney_highway_segment_evidence",
            "panel": str(panel_csv),
            "disclosure_csv": str(disclosure_csv),
            "raw_output": str(raw_path),
            "evidence_output": str(evidence_path),
            "requested_company_count": len(codes),
            "raw_row_count": len(raw_rows),
            "evidence_row_count": len(evidence_rows),
            "pit_usable_rows": len(usable),
            "covered_company_count": len({row["code"] for row in usable if row.get("code")}),
            "warning_count": len(warnings),
            "warnings": warnings,
            "source_policy": "Eastmoney public F10 BusinessAnalysis/PageAjax via normal HTTP request with timeout and no anti-crawler bypass.",
            "pit_policy": "visible_date is joined from Tushare disclosure_date for the same report period when available.",
            "limitations": [
                "Segment evidence can identify highway/toll-road business exposure and non-highway contamination.",
                "It does not provide traffic volume, remaining concession years or toll policy details.",
            ],
            "created_at_utc": _now_utc(),
        },
    )
    return evidence_path


def write_highway_operating_manual_template(
    disclosure_csv: Path,
    segment_evidence_csv: Path,
    out_dir: Path = DEFAULT_OUT_DIR,
) -> Path:
    disclosures = read_csv_rows(disclosure_csv)
    segment_by_key = {
        (row.get("code", ""), row.get("report_period", "")): row
        for row in read_csv_rows(segment_evidence_csv)
    }
    rows: list[dict[str, Any]] = []
    for row in disclosures:
        code = row.get("code", "")
        period = row.get("report_period", "")
        segment = segment_by_key.get((code, period), {})
        rows.append(
            {
                "code": code,
                "ts_code": row.get("ts_code", ""),
                "report_period": period,
                "report_type": row.get("report_type", ""),
                "notice_date": row.get("notice_date", ""),
                "visible_date": row.get("notice_date", ""),
                "traffic_volume_yoy": "",
                "toll_revenue_yoy": "",
                "toll_revenue_amount": "",
                "remaining_concession_years": "",
                "toll_policy_change_flag": "",
                "toll_policy_description": "",
                "non_highway_revenue_ratio": segment.get("non_highway_revenue_ratio", ""),
                "approved_highway_business_tag": segment.get("approved_highway_business_tag", ""),
                "source_name": row.get("source_name", "tushare.disclosure_date"),
                "source_url": "",
                "pit_usable": "false",
                "review_status": "template_requires_original_report_operating_data",
                "notes": "Fill traffic volume, toll revenue, remaining concession years and toll policy from original annual/interim report before setting pit_usable=true.",
            }
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "highway_operating_data_manual_template.csv"
    write_csv_rows(out_path, OPERATING_TEMPLATE_FIELDS, rows)
    write_json_file(
        out_dir / "highway_operating_data_manual_template_manifest.json",
        {
            "dataset": "highway_operating_data_manual_template",
            "disclosure_csv": str(disclosure_csv),
            "segment_evidence_csv": str(segment_evidence_csv),
            "output": str(out_path),
            "row_count": len(rows),
            "pit_usable_count": 0,
            "required_rule": "Real operating fields require original report evidence and visible_date before formal validation.",
            "created_at_utc": _now_utc(),
        },
    )
    return out_path


def audit_highway_operating_data(
    source_csv: Path,
    out_dir: Path = DEFAULT_OUT_DIR / "audit",
) -> Path:
    rows = read_csv_rows(source_csv) if source_csv.exists() else []
    audited = [_audit_operating_row(row) for row in rows]
    usable = [row for row in audited if row.get("pit_usable_final") == "true"]
    covered_codes = {row.get("code") for row in usable if row.get("code")}
    fields = [
        *OPERATING_TEMPLATE_FIELDS,
        "pit_usable_final",
        "issue_count",
        "issues",
    ]
    out_dir.mkdir(parents=True, exist_ok=True)
    audit_path = out_dir / "highway_operating_data_audit_rows.csv"
    write_csv_rows(audit_path, fields, audited)
    summary = {
        "dataset": "highway_operating_data_audit",
        "source_csv": str(source_csv),
        "row_count": len(rows),
        "pit_usable_rows": len(usable),
        "covered_company_count": len(covered_codes),
        "status": "pass" if usable else "blocked",
        "required_fields": [
            "traffic_volume_yoy",
            "toll_revenue_yoy or toll_revenue_amount",
            "remaining_concession_years",
            "toll_policy_change_flag",
            "source_url",
            "visible_date",
        ],
        "reason": "Highway operating data is formal only after original report evidence is reviewed.",
        "created_at_utc": _now_utc(),
    }
    write_json_file(out_dir / "highway_operating_data_audit_summary.json", summary)
    (out_dir / "highway_operating_data_audit_report.md").write_text(_render_audit_report(summary), encoding="utf-8")
    return out_dir / "highway_operating_data_audit_report.md"


def build_highway_annual_report_sample_manifest(
    disclosure_csv: Path,
    out_dir: Path = DEFAULT_OUT_DIR / "annual_reports",
    *,
    sample_size: int = 8,
    prefer_year: str = "2024",
) -> Path:
    rows = [
        row
        for row in read_csv_rows(disclosure_csv)
        if row.get("report_type") == "annual" and row.get("report_period", "").startswith(prefer_year)
    ]
    if len(rows) < sample_size:
        fallback = [
            row
            for row in read_csv_rows(disclosure_csv)
            if row.get("report_type") == "annual" and row not in rows
        ]
        rows.extend(fallback)
    selected = rows[:sample_size]
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "highway_annual_report_sample_manifest.csv"
    write_csv_rows(
        manifest_path,
        REPORT_MANIFEST_FIELDS,
        [
            {
                "sector": "transportation_infrastructure_highway",
                "code": row.get("code", ""),
                "company_name": row.get("code", ""),
                "report_period": row.get("report_period", ""),
                "publish_date": row.get("notice_date", ""),
                "visible_date": row.get("visible_date") or row.get("notice_date", ""),
                "source_title": "",
                "source_url": "",
                "local_path": "",
            }
            for row in selected
        ],
    )
    write_json_file(
        out_dir / "highway_annual_report_sample_manifest_summary.json",
        {
            "dataset": "highway_annual_report_sample_manifest",
            "disclosure_csv": str(disclosure_csv),
            "output": str(manifest_path),
            "sample_size": len(selected),
            "prefer_year": prefer_year,
            "created_at_utc": _now_utc(),
        },
    )
    return manifest_path


def build_highway_annual_report_manifest(
    disclosure_csv: Path,
    out_dir: Path = DEFAULT_OUT_DIR / "annual_reports",
    *,
    start_year: str = "2021",
    end_year: str = "2025",
    limit: int | None = None,
) -> Path:
    rows = [
        row
        for row in read_csv_rows(disclosure_csv)
        if row.get("report_type") == "annual"
        and start_year <= row.get("report_period", "")[:4] <= end_year
    ]
    rows = sorted(rows, key=lambda row: (row.get("code", ""), row.get("report_period", "")))
    if limit is not None:
        rows = rows[:limit]
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "highway_annual_report_manifest.csv"
    write_csv_rows(
        manifest_path,
        REPORT_MANIFEST_FIELDS,
        [
            {
                "sector": "transportation_infrastructure_highway",
                "code": row.get("code", ""),
                "company_name": row.get("code", ""),
                "report_period": row.get("report_period", ""),
                "publish_date": row.get("notice_date", ""),
                "visible_date": row.get("visible_date") or row.get("notice_date", ""),
                "source_title": "",
                "source_url": "",
                "local_path": "",
            }
            for row in rows
        ],
    )
    write_json_file(
        out_dir / "highway_annual_report_manifest_summary.json",
        {
            "dataset": "highway_annual_report_manifest",
            "disclosure_csv": str(disclosure_csv),
            "output": str(manifest_path),
            "start_year": start_year,
            "end_year": end_year,
            "row_count": len(rows),
            "covered_company_count": len({row.get("code", "") for row in rows if row.get("code")}),
            "covered_years": sorted({row.get("report_period", "")[:4] for row in rows if row.get("report_period")}),
            "selection_policy": "All annual reports in the requested year range; used for reviewed operating PIT evidence expansion.",
            "created_at_utc": _now_utc(),
        },
    )
    return manifest_path


def download_cninfo_annual_reports(
    manifest_csv: Path,
    out_dir: Path = DEFAULT_OUT_DIR / "annual_reports",
    *,
    timeout_seconds: float = 20.0,
) -> Path:
    import requests

    rows = read_csv_rows(manifest_csv)
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir = out_dir / "pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    output_rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    for row in rows:
        code = row.get("code", "")
        period = row.get("report_period", "")
        year = period[:4]
        try:
            ann = _query_cninfo_annual_report(code, year, timeout_seconds)
        except Exception as exc:
            warnings.append(f"{code}:{period}: cninfo query failed: {type(exc).__name__}: {exc}")
            ann = None
        out = dict(row)
        if ann:
            url = "http://static.cninfo.com.cn/" + ann["adjunctUrl"]
            local_path = pdf_dir / f"{code.replace('.', '_')}_{period}_annual_report.pdf"
            try:
                response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=(5, timeout_seconds))
                response.raise_for_status()
                local_path.write_bytes(response.content)
                out.update(
                    {
                        "source_title": ann.get("announcementTitle", ""),
                        "source_url": url,
                        "local_path": str(local_path),
                    }
                )
            except Exception as exc:
                warnings.append(f"{code}:{period}: cninfo pdf download failed: {type(exc).__name__}: {exc}")
        else:
            warnings.append(f"{code}:{period}: annual report not found from cninfo")
        output_rows.append(out)
        time.sleep(0.2)

    out_path = out_dir / "highway_annual_report_sample_manifest_downloaded.csv"
    write_csv_rows(out_path, REPORT_MANIFEST_FIELDS, output_rows)
    write_json_file(
        out_dir / "highway_annual_report_download_manifest.json",
        {
            "dataset": "highway_annual_report_downloads",
            "input_manifest": str(manifest_csv),
            "output": str(out_path),
            "requested_count": len(rows),
            "downloaded_count": sum(1 for row in output_rows if row.get("local_path")),
            "warning_count": len(warnings),
            "warnings": warnings,
            "source_policy": "CNINFO public announcement query and static PDF download with normal HTTP requests.",
            "created_at_utc": _now_utc(),
        },
    )
    return out_path


def extract_highway_operating_candidates_from_reports(
    manifest_csv: Path,
    out_dir: Path = DEFAULT_OUT_DIR / "annual_reports",
    *,
    max_pages_per_report: int | None = None,
    context_chars: int = 260,
) -> Path:
    rows = [row for row in read_csv_rows(manifest_csv) if row.get("local_path")]
    out_dir.mkdir(parents=True, exist_ok=True)
    candidates: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for row in rows:
        path = Path(row["local_path"])
        if not path.exists():
            errors.append({"code": row.get("code", ""), "report_period": row.get("report_period", ""), "error": "local_path_missing"})
            continue
        try:
            pages = _extract_pdf_pages(path, max_pages_per_report=max_pages_per_report)
        except Exception as exc:
            errors.append({"code": row.get("code", ""), "report_period": row.get("report_period", ""), "error": f"extract_failed:{type(exc).__name__}"})
            continue
        for field, terms in OPERATING_FIELD_TERMS.items():
            for page_number, text in pages:
                for term in terms:
                    for match in _term_matches(text, term, context_chars):
                        candidates.append(
                            {
                                "code": row.get("code", ""),
                                "report_period": row.get("report_period", ""),
                                "field": field,
                                "candidate_value": match["candidate_value"],
                                "unit": _operating_unit(field),
                                "source_title": row.get("source_title", ""),
                                "source_url": row.get("source_url", ""),
                                "local_path": row.get("local_path", ""),
                                "page_number": page_number,
                                "matched_term": term,
                                "evidence_snippet": match["snippet"],
                                "review_status": "candidate_needs_manual_review",
                                "pit_status": "needs_original_announcement_check",
                            }
                        )
    shortlist = _candidate_shortlist(candidates)
    out_path = out_dir / "highway_operating_field_candidates.csv"
    shortlist_path = out_dir / "highway_operating_field_candidate_shortlist.csv"
    write_csv_rows(out_path, OPERATING_CANDIDATE_FIELDS, candidates)
    write_csv_rows(shortlist_path, OPERATING_CANDIDATE_FIELDS, shortlist)
    write_csv_rows(out_dir / "highway_operating_field_extraction_errors.csv", ["code", "report_period", "error"], errors)
    write_json_file(
        out_dir / "highway_operating_field_extraction_summary.json",
        {
            "dataset": "highway_operating_field_candidates",
            "manifest_csv": str(manifest_csv),
            "report_count": len(rows),
            "candidate_count": len(candidates),
            "shortlist_count": len(shortlist),
            "error_count": len(errors),
            "fields": sorted(OPERATING_FIELD_TERMS),
            "review_policy": "Candidates are not PIT usable until Research Agent verifies value, unit, scope and page in the original report.",
            "created_at_utc": _now_utc(),
        },
    )
    return shortlist_path


def spot_check_eastmoney_segment_against_reports(
    downloaded_manifest_csv: Path,
    eastmoney_raw_csv: Path,
    out_dir: Path = DEFAULT_OUT_DIR / "annual_reports",
    *,
    max_items_per_report: int = 5,
) -> Path:
    manifest_rows = [row for row in read_csv_rows(downloaded_manifest_csv) if row.get("local_path")]
    raw_rows = read_csv_rows(eastmoney_raw_csv)
    raw_by_key: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in raw_rows:
        if row.get("mainop_type") == "product":
            raw_by_key[(row.get("code", ""), row.get("report_period", ""))].append(row)
    result: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for manifest in manifest_rows:
        code = manifest.get("code", "")
        period = manifest.get("report_period", "")
        path = Path(manifest.get("local_path", ""))
        try:
            report_text = _full_pdf_text(path)
        except Exception as exc:
            errors.append({"code": code, "report_period": period, "error": f"pdf_read_failed:{type(exc).__name__}"})
            continue
        segment_rows = sorted(
            raw_by_key.get((code, period), []),
            key=lambda row: to_float(row.get("main_business_income")) or 0.0,
            reverse=True,
        )[:max_items_per_report]
        for row in segment_rows:
            item = row.get("item_name", "")
            income = row.get("main_business_income", "")
            item_found = _compact_text(item) in _compact_text(report_text) if item else False
            amount_found = _amount_found_in_text(income, report_text)
            status = "pass" if item_found else "needs_manual_review"
            result.append(
                {
                    "code": code,
                    "report_period": period,
                    "item_name": item,
                    "main_business_income": income,
                    "income_ratio": row.get("income_ratio", ""),
                    "source_title": manifest.get("source_title", ""),
                    "local_path": str(path),
                    "item_name_found_in_report": str(item_found).lower(),
                    "income_amount_found_in_report": str(amount_found).lower(),
                    "spot_check_status": status,
                    "notes": "Item-name match is used as lightweight spot check; exact amount match may fail due to unit or PDF formatting differences.",
                }
            )
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "highway_eastmoney_segment_spot_check.csv"
    write_csv_rows(out_path, SEGMENT_SPOT_CHECK_FIELDS, result)
    write_csv_rows(out_dir / "highway_eastmoney_segment_spot_check_errors.csv", ["code", "report_period", "error"], errors)
    passed_reports = {
        (row["code"], row["report_period"])
        for row in result
        if row.get("spot_check_status") == "pass"
    }
    write_json_file(
        out_dir / "highway_eastmoney_segment_spot_check_summary.json",
        {
            "dataset": "highway_eastmoney_segment_spot_check",
            "downloaded_manifest_csv": str(downloaded_manifest_csv),
            "eastmoney_raw_csv": str(eastmoney_raw_csv),
            "output": str(out_path),
            "report_count": len(manifest_rows),
            "spot_check_rows": len(result),
            "pass_rows": sum(1 for row in result if row.get("spot_check_status") == "pass"),
            "passed_report_count": len(passed_reports),
            "error_count": len(errors),
            "review_policy": "A pass means segment item names were found in original reports. Final promotion still requires targeted table/page review for exact values.",
            "created_at_utc": _now_utc(),
        },
    )
    return out_path


def build_reviewed_operating_disclosure_data(
    candidate_csv: Path,
    downloaded_manifest_csv: Path,
    out_dir: Path = DEFAULT_OUT_DIR / "annual_reports",
) -> Path:
    candidates = read_csv_rows(candidate_csv)
    manifest_by_key = {
        (row.get("code", ""), row.get("report_period", "")): row
        for row in read_csv_rows(downloaded_manifest_csv)
        if row.get("local_path")
    }
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in candidates:
        grouped[(row.get("code", ""), row.get("report_period", ""))].append(row)
    rows: list[dict[str, Any]] = []
    for key, values in sorted(grouped.items()):
        manifest = manifest_by_key.get(key, {})
        if not manifest:
            continue
        flags = _reviewed_operating_flags(values)
        score = sum(flags.values()) / 4.0
        rows.append(
            {
                "code": key[0],
                "report_period": key[1],
                "visible_date": manifest.get("visible_date", ""),
                "traffic_toll_table_available": str(flags["traffic_toll_table_available"]).lower(),
                "toll_revenue_evidence_available": str(flags["toll_revenue_evidence_available"]).lower(),
                "remaining_concession_evidence_available": str(flags["remaining_concession_evidence_available"]).lower(),
                "toll_policy_evidence_available": str(flags["toll_policy_evidence_available"]).lower(),
                "reviewed_operating_disclosure_score": fmt_float(score),
                "source_title": manifest.get("source_title", ""),
                "source_url": manifest.get("source_url", ""),
                "local_path": manifest.get("local_path", ""),
                "pit_usable": "true" if score >= 0.75 else "false",
                "review_status": "rule_reviewed_original_report_candidates" if score >= 0.75 else "insufficient_reviewed_operating_fields",
                "notes": "This row validates operating disclosure availability from original annual-report candidates. It does not certify exact traffic/toll/concession numeric values.",
            }
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "highway_reviewed_operating_disclosure_data.csv"
    write_csv_rows(out_path, REVIEWED_OPERATING_FIELDS, rows)
    usable = [row for row in rows if row.get("pit_usable") == "true"]
    write_json_file(
        out_dir / "highway_reviewed_operating_disclosure_data_summary.json",
        {
            "dataset": "highway_reviewed_operating_disclosure_data",
            "candidate_csv": str(candidate_csv),
            "downloaded_manifest_csv": str(downloaded_manifest_csv),
            "output": str(out_path),
            "row_count": len(rows),
            "pit_usable_rows": len(usable),
            "covered_company_count": len({row["code"] for row in usable if row.get("code")}),
            "review_policy": "PIT usable means original-report candidate evidence exists for at least 3 of 4 operating disclosure categories. Exact numeric values remain blocked.",
            "created_at_utc": _now_utc(),
        },
    )
    return out_path


def build_reviewed_operating_panel(
    panel_csv: Path,
    reviewed_operating_csv: Path,
    out_dir: Path = DEFAULT_OUT_DIR / "annual_reports",
) -> Path:
    panel_rows = read_csv_rows(panel_csv)
    reviewed_by_code: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in read_csv_rows(reviewed_operating_csv):
        if row.get("pit_usable") == "true":
            reviewed_by_code[row["code"]].append(row)
    for rows in reviewed_by_code.values():
        rows.sort(key=lambda row: (row.get("visible_date", ""), row.get("report_period", "")))
    output_rows = []
    missing = 0
    for row in panel_rows:
        evidence = _latest_visible_reviewed_operating(reviewed_by_code.get(row.get("code", ""), []), row.get("trade_date", ""))
        out = dict(row)
        if evidence is None:
            missing += 1
            out.update(
                {
                    "reviewed_operating_data_available": "false",
                    "reviewed_operating_disclosure_score": "",
                    "traffic_toll_table_available": "",
                    "toll_revenue_evidence_available": "",
                    "remaining_concession_evidence_available": "",
                    "toll_policy_evidence_available": "",
                    "reviewed_operating_visible_date": "",
                    "reviewed_operating_status": "missing_visible_reviewed_operating_data",
                }
            )
        else:
            out.update(
                {
                    "reviewed_operating_data_available": "true",
                    "reviewed_operating_disclosure_score": evidence.get("reviewed_operating_disclosure_score", ""),
                    "traffic_toll_table_available": "1" if evidence.get("traffic_toll_table_available") == "true" else "0",
                    "toll_revenue_evidence_available": "1" if evidence.get("toll_revenue_evidence_available") == "true" else "0",
                    "remaining_concession_evidence_available": "1" if evidence.get("remaining_concession_evidence_available") == "true" else "0",
                    "toll_policy_evidence_available": "1" if evidence.get("toll_policy_evidence_available") == "true" else "0",
                    "reviewed_operating_visible_date": evidence.get("visible_date", ""),
                    "reviewed_operating_status": evidence.get("review_status", ""),
                }
            )
        output_rows.append(out)
    extra_fields = [
        "reviewed_operating_data_available",
        "reviewed_operating_disclosure_score",
        "traffic_toll_table_available",
        "toll_revenue_evidence_available",
        "remaining_concession_evidence_available",
        "toll_policy_evidence_available",
        "reviewed_operating_visible_date",
        "reviewed_operating_status",
    ]
    fields = list(panel_rows[0].keys()) if panel_rows else []
    for field in extra_fields:
        if field not in fields:
            fields.append(field)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "highway_reviewed_operating_panel.csv"
    write_csv_rows(out_path, fields, output_rows)
    usable_rows = [row for row in output_rows if row.get("reviewed_operating_data_available") == "true"]
    usable_panel_path = out_dir / "highway_reviewed_operating_formal_panel.csv"
    write_csv_rows(usable_panel_path, fields, usable_rows)
    write_json_file(
        out_dir / "highway_reviewed_operating_panel_summary.json",
        {
            "dataset": "highway_reviewed_operating_panel",
            "panel_csv": str(panel_csv),
            "reviewed_operating_csv": str(reviewed_operating_csv),
            "output": str(out_path),
            "formal_panel_output": str(usable_panel_path),
            "row_count": len(output_rows),
            "formal_row_count": len(usable_rows),
            "missing_visible_reviewed_operating_rows": missing,
            "covered_company_count": len({row["code"] for row in usable_rows if row.get("code")}),
            "date_count": len({row["trade_date"] for row in usable_rows if row.get("trade_date")}),
            "created_at_utc": _now_utc(),
        },
    )
    return usable_panel_path


def build_highway_segment_enriched_panel(
    panel_csv: Path,
    segment_evidence_csv: Path,
    out_dir: Path = DEFAULT_OUT_DIR,
) -> Path:
    panel_rows = read_csv_rows(panel_csv)
    evidence_by_code = _complete_segment_evidence_by_code(segment_evidence_csv)
    rows: list[dict[str, Any]] = []
    missing_rows = 0
    excluded_rows = 0
    for row in panel_rows:
        trade_date = row.get("trade_date", "")
        code = row.get("code", "")
        evidence = _latest_visible_evidence(evidence_by_code.get(code, []), trade_date)
        out = dict(row)
        if evidence is None:
            missing_rows += 1
            out.update(
                {
                    "formal_highway_universe_include": "false",
                    "highway_revenue_ratio": "",
                    "toll_revenue_ratio": "",
                    "non_highway_revenue_ratio": "",
                    "approved_highway_business_tag": "",
                    "highway_segment_visible_date": "",
                    "highway_segment_review_status": "missing_visible_segment_evidence",
                    "highway_segment_notes": "No visible segment evidence available at this trade date.",
                }
            )
        else:
            tag = evidence.get("approved_highway_business_tag", "")
            include = tag in {"core_toll_road_operator", "mixed_highway_operator"}
            if not include:
                excluded_rows += 1
            out.update(
                {
                    "formal_highway_universe_include": str(include).lower(),
                    "highway_revenue_ratio": evidence.get("highway_revenue_ratio", ""),
                    "toll_revenue_ratio": evidence.get("toll_revenue_ratio", ""),
                    "non_highway_revenue_ratio": evidence.get("non_highway_revenue_ratio", ""),
                    "approved_highway_business_tag": tag,
                    "highway_segment_visible_date": evidence.get("visible_date", ""),
                    "highway_segment_review_status": evidence.get("review_status", ""),
                    "highway_segment_notes": evidence.get("notes", ""),
                }
            )
        rows.append(out)

    extra_fields = [
        "formal_highway_universe_include",
        "highway_revenue_ratio",
        "toll_revenue_ratio",
        "non_highway_revenue_ratio",
        "approved_highway_business_tag",
        "highway_segment_visible_date",
        "highway_segment_review_status",
        "highway_segment_notes",
    ]
    fields = list(panel_rows[0].keys()) if panel_rows else []
    for field in extra_fields:
        if field not in fields:
            fields.append(field)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "highway_segment_enriched_panel.csv"
    write_csv_rows(out_path, fields, rows)
    formal_rows = [row for row in rows if row.get("formal_highway_universe_include") == "true"]
    write_json_file(
        out_dir / "highway_segment_enriched_panel_manifest.json",
        {
            "dataset": "highway_segment_enriched_panel",
            "panel": str(panel_csv),
            "segment_evidence_csv": str(segment_evidence_csv),
            "output": str(out_path),
            "row_count": len(rows),
            "formal_universe_row_count": len(formal_rows),
            "missing_visible_segment_rows": missing_rows,
            "formal_universe_excluded_rows": excluded_rows,
            "covered_company_count": len({row["code"] for row in rows if row.get("highway_segment_review_status") != "missing_visible_segment_evidence"}),
            "governance": "This panel separates PIT highway business exposure from formal universe inclusion. Non-highway-contaminated rows are excluded by default.",
            "created_at_utc": _now_utc(),
        },
    )
    return out_path


def _audit_operating_row(row: dict[str, str]) -> dict[str, Any]:
    issues: list[str] = []
    if not row.get("code"):
        issues.append("missing_code")
    if not row.get("report_period"):
        issues.append("missing_report_period")
    if not row.get("visible_date"):
        issues.append("missing_visible_date")
    if not row.get("source_url"):
        issues.append("missing_source_url")
    if to_float(row.get("traffic_volume_yoy")) is None:
        issues.append("missing_traffic_volume_yoy")
    if to_float(row.get("toll_revenue_yoy")) is None and to_float(row.get("toll_revenue_amount")) is None:
        issues.append("missing_toll_revenue")
    if to_float(row.get("remaining_concession_years")) is None:
        issues.append("missing_remaining_concession_years")
    if str(row.get("toll_policy_change_flag", "")).lower() not in {"true", "false"}:
        issues.append("missing_or_invalid_toll_policy_change_flag")
    if str(row.get("review_status", "")).lower() != "reviewed":
        issues.append("not_reviewed")
    if str(row.get("pit_usable", "")).lower() != "true":
        issues.append("pit_status_not_true")
    result = {column: row.get(column, "") for column in OPERATING_TEMPLATE_FIELDS}
    result["pit_usable_final"] = "true" if not issues else "false"
    result["issue_count"] = len(issues)
    result["issues"] = ";".join(issues)
    return result


def _complete_segment_evidence_by_code(path: Path) -> dict[str, list[dict[str, str]]]:
    by_code: dict[str, list[dict[str, str]]] = defaultdict(list)
    if not path.exists():
        return by_code
    for row in read_csv_rows(path):
        if str(row.get("pit_usable", "")).lower() != "true":
            continue
        if not row.get("visible_date") or not row.get("approved_highway_business_tag"):
            continue
        by_code[row["code"]].append(row)
    for values in by_code.values():
        values.sort(key=lambda item: (item.get("visible_date", ""), item.get("report_period", "")))
    return by_code


def _latest_visible_evidence(rows: list[dict[str, str]], trade_date: str) -> dict[str, str] | None:
    visible = [row for row in rows if row.get("visible_date", "") <= trade_date]
    if not visible:
        return None
    return visible[-1]


def _query_cninfo_annual_report(code: str, report_year: str, timeout_seconds: float) -> dict[str, Any] | None:
    import requests

    stock = _to_cninfo_stock(code)
    if not stock:
        return None
    plate = "sz" if code.endswith(".XSHE") else "sh"
    column = "szse" if code.endswith(".XSHE") else "sse"
    start = f"{int(report_year) + 1}-01-01"
    end = f"{int(report_year) + 1}-12-31"
    data = {
        "pageNum": "1",
        "pageSize": "20",
        "column": column,
        "tabName": "fulltext",
        "plate": plate,
        "stock": stock,
        "searchkey": "",
        "secid": "",
        "category": "category_ndbg_szsh",
        "trade": "",
        "seDate": f"{start}~{end}",
        "sortName": "",
        "sortType": "",
        "isHLtitle": "true",
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "http://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search",
    }
    response = requests.post("http://www.cninfo.com.cn/new/hisAnnouncement/query", data=data, headers=headers, timeout=(5, timeout_seconds))
    response.raise_for_status()
    announcements = response.json().get("announcements") or []
    filtered = [
        item
        for item in announcements
        if "年度报告" in str(item.get("announcementTitle", ""))
        and "摘要" not in str(item.get("announcementTitle", ""))
        and str(item.get("adjunctUrl", "")).lower().endswith(".pdf")
    ]
    return filtered[0] if filtered else None


def _to_cninfo_stock(code: str) -> str:
    raw = code[:6]
    if code.endswith(".XSHE"):
        return f"{raw},gssz0{raw}"
    if code.endswith(".XSHG"):
        return f"{raw},gssh0{raw}"
    return ""


def _extract_pdf_pages(path: Path, *, max_pages_per_report: int | None) -> list[tuple[int, str]]:
    import fitz  # type: ignore

    doc = fitz.open(str(path))
    limit = doc.page_count if max_pages_per_report is None else min(doc.page_count, max_pages_per_report)
    return [(index + 1, doc.load_page(index).get_text("text") or "") for index in range(limit)]


def _full_pdf_text(path: Path) -> str:
    return "\n".join(text for _page, text in _extract_pdf_pages(path, max_pages_per_report=None))


def _term_matches(text: str, term: str, context_chars: int) -> list[dict[str, str]]:
    matches = []
    for found in re.finditer(re.escape(term), text):
        start = max(0, found.start() - context_chars)
        end = min(len(text), found.end() + context_chars)
        snippet = re.sub(r"\s+", " ", text[start:end]).strip()
        matches.append({"snippet": snippet, "candidate_value": _candidate_value_after_term(snippet, term)})
    return matches


def _candidate_value_after_term(snippet: str, term: str) -> str:
    after = snippet.split(term, 1)[-1]
    match = re.search(r"[-+]?\d[\d,]*(?:\.\d+)?\s*(?:%|年|亿元|万元|万车次|万辆|辆|公里)?", after)
    return match.group(0).replace(",", "").strip() if match else ""


def _operating_unit(field: str) -> str:
    if field in {"traffic_volume_yoy", "toll_revenue_yoy"}:
        return "percent_or_text_candidate"
    if field == "remaining_concession_years":
        return "years_or_text_candidate"
    if field == "toll_revenue_amount":
        return "currency_or_text_candidate"
    return "text_candidate"


def _candidate_shortlist(rows: list[dict[str, Any]], *, max_per_group: int = 5) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row.get("code", "")), str(row.get("report_period", "")), str(row.get("field", "")))].append(row)
    result: list[dict[str, Any]] = []
    for values in grouped.values():
        ranked = sorted(values, key=lambda row: (0 if row.get("candidate_value") else 1, int(row.get("page_number") or 9999)))
        result.extend(ranked[:max_per_group])
    return sorted(result, key=lambda row: (row.get("code", ""), row.get("report_period", ""), row.get("field", ""), row.get("page_number", 0)))


def _compact_text(value: str) -> str:
    return re.sub(r"\s+", "", str(value or ""))


def _amount_found_in_text(value: str, text: str) -> bool:
    parsed = to_float(value)
    if parsed is None:
        return False
    candidates = {
        f"{parsed:.0f}",
        f"{parsed / 10000:.2f}",
        f"{parsed / 10000:.0f}",
        f"{parsed / 100000000:.2f}",
    }
    compact = _compact_text(text).replace(",", "")
    return any(candidate.replace(",", "") in compact for candidate in candidates)


def _reviewed_operating_flags(rows: list[dict[str, str]]) -> dict[str, bool]:
    snippets_by_field: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        snippets_by_field[row.get("field", "")].append(row.get("evidence_snippet", ""))
    all_text = " ".join(row.get("evidence_snippet", "") for row in rows)
    traffic_text = " ".join(snippets_by_field.get("traffic_volume_yoy", []))
    toll_text = " ".join(snippets_by_field.get("toll_revenue_amount", []) + snippets_by_field.get("toll_revenue_yoy", []))
    concession_text = " ".join(snippets_by_field.get("remaining_concession_years", []))
    policy_text = " ".join(snippets_by_field.get("toll_policy_change_flag", []))
    return {
        "traffic_toll_table_available": bool("车流量" in traffic_text and "通行费收入" in traffic_text and ("增减" in traffic_text or "%" in traffic_text)),
        "toll_revenue_evidence_available": bool("通行费收入" in toll_text and ("万元" in toll_text or "人民币" in toll_text or "%" in toll_text)),
        "remaining_concession_evidence_available": bool(("收费期限" in concession_text or "剩余收费期限" in concession_text or "经营期限" in concession_text) and re.search(r"\d+\s*年|20\d{2}\s*年", concession_text)),
        "toll_policy_evidence_available": bool(("收费政策" in policy_text or "收费标准" in policy_text or "减免" in policy_text) and ("影响" in all_text or "政策" in all_text or "标准" in all_text)),
    }


def _latest_visible_reviewed_operating(rows: list[dict[str, str]], trade_date: str) -> dict[str, str] | None:
    visible = [row for row in rows if row.get("visible_date", "") <= trade_date]
    if not visible:
        return None
    return visible[-1]


def _fetch_disclosure_rows(pro: Any, codes: list[str], target_years: set[str], warnings: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for code in codes:
        ts_code = _to_ts_code(code)
        try:
            df = pro.disclosure_date(ts_code=ts_code)
        except Exception as exc:
            warnings.append(f"{ts_code}: disclosure_date failed: {type(exc).__name__}: {exc}")
            continue
        if df is None or getattr(df, "empty", True):
            warnings.append(f"{ts_code}: disclosure_date returned no rows")
            continue
        for raw in df.to_dict("records"):
            end_date = _date_text(raw.get("end_date"))
            if len(end_date) != 8 or end_date[:4] not in target_years:
                continue
            if not (end_date.endswith("0630") or end_date.endswith("1231")):
                continue
            ann_date = _date_text(raw.get("ann_date"))
            pre_date = _date_text(raw.get("pre_date"))
            actual_date = _date_text(raw.get("actual_date"))
            modify_date = _date_text(raw.get("modify_date"))
            notice_date, source = _choose_notice_date(actual_date, ann_date, pre_date)
            if not notice_date:
                warnings.append(f"{ts_code} {end_date}: missing report disclosure date")
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


def _build_segment_evidence_from_raw(
    raw_rows: list[dict[str, Any]],
    disclosures: dict[tuple[str, str], dict[str, str]],
) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in raw_rows:
        by_key[(row["code"], row["report_period"])].append(row)
    evidence_rows = []
    for (code, report_period), rows in sorted(by_key.items()):
        selected = [row for row in rows if row.get("mainop_type") == "product"]
        if not selected:
            selected = [row for row in rows if row.get("mainop_type") == "industry"]
        if not selected:
            selected = rows
        selected = [row for row in selected if not _is_segment_subitem(str(row.get("item_name") or ""))]
        ratios = _highway_segment_ratios(selected)
        disclosure = disclosures.get((code, report_period), {})
        visible_date = disclosure.get("notice_date", "")
        tag = _approved_highway_business_tag(ratios)
        evidence_rows.append(
            {
                "code": code,
                "ts_code": _to_ts_code(code),
                "report_period": report_period,
                "report_type": "semiannual" if report_period.endswith("-06-30") else "annual" if report_period.endswith("-12-31") else "other",
                "notice_date": visible_date,
                "visible_date": visible_date,
                "highway_revenue_ratio": fmt_float(ratios["highway_revenue_ratio"]),
                "toll_revenue_ratio": fmt_float(ratios["toll_revenue_ratio"]),
                "transport_infrastructure_revenue_ratio": fmt_float(ratios["transport_infrastructure_revenue_ratio"]),
                "non_highway_revenue_ratio": fmt_float(ratios["non_highway_revenue_ratio"]),
                "largest_non_highway_item": ratios["largest_non_highway_item"],
                "largest_non_highway_revenue_ratio": fmt_float(ratios["largest_non_highway_revenue_ratio"]),
                "approved_highway_business_tag": tag,
                "source_name": "Eastmoney F10 BusinessAnalysis + Tushare disclosure_date",
                "source_url": f"https://emweb.securities.eastmoney.com/PC_HSF10/BusinessAnalysis/Index?type=web&code={_to_eastmoney_code(code)}",
                "pit_usable": "true" if visible_date and tag else "false",
                "review_status": "eastmoney_segment_needs_spot_check" if visible_date and tag else "missing_disclosure_or_segment_tag",
                "notes": _segment_notes(rows, ratios),
            }
        )
    return evidence_rows


def _highway_segment_ratios(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total_income = sum(to_float(row.get("main_business_income")) or 0.0 for row in rows)
    highway_income = 0.0
    toll_income = 0.0
    infra_income = 0.0
    non_highway: list[tuple[str, float]] = []
    for row in rows:
        name = str(row.get("item_name") or "")
        income = to_float(row.get("main_business_income")) or 0.0
        bucket = _segment_bucket(name)
        if bucket == "toll":
            toll_income += income
            highway_income += income
            infra_income += income
        elif bucket == "highway":
            highway_income += income
            infra_income += income
        elif bucket == "transport_infrastructure":
            infra_income += income
            non_highway.append((name, income))
        else:
            non_highway.append((name, income))
    non_highway_income = max(0.0, total_income - highway_income)
    largest_name, largest_income = ("", 0.0)
    if non_highway:
        largest_name, largest_income = max(non_highway, key=lambda item: item[1])
    return {
        "highway_revenue_ratio": ratio(highway_income, total_income),
        "toll_revenue_ratio": ratio(toll_income, total_income),
        "transport_infrastructure_revenue_ratio": ratio(infra_income, total_income),
        "non_highway_revenue_ratio": ratio(non_highway_income, total_income),
        "largest_non_highway_item": largest_name,
        "largest_non_highway_revenue_ratio": ratio(largest_income, total_income),
    }


def _segment_bucket(name: str) -> str:
    text = name.lower()
    if any(word in name for word in ("通行费", "收费公路", "收费路", "路费")):
        return "toll"
    if any(word in name for word in ("高速", "公路", "路桥", "桥梁", "隧道")):
        return "highway"
    if any(word in name for word in ("港口", "机场", "铁路", "物流", "运输", "仓储")):
        return "transport_infrastructure"
    if any(word in text for word in ("toll", "expressway", "highway", "road", "bridge")):
        return "highway"
    return "non_highway"


def _approved_highway_business_tag(ratios: dict[str, Any]) -> str:
    highway_ratio = to_float(ratios.get("highway_revenue_ratio")) or 0.0
    toll_ratio = to_float(ratios.get("toll_revenue_ratio")) or 0.0
    non_highway_ratio = to_float(ratios.get("non_highway_revenue_ratio")) or 0.0
    if toll_ratio >= 0.5 or highway_ratio >= 0.6:
        return "core_toll_road_operator"
    if highway_ratio >= 0.35:
        return "mixed_highway_operator"
    if non_highway_ratio >= 0.65:
        return "non_highway_contaminated"
    return "needs_manual_review"


def _segment_notes(rows: list[dict[str, Any]], ratios: dict[str, Any]) -> str:
    items = [str(row.get("item_name") or "") for row in rows if row.get("item_name")]
    return (
        f"items={';'.join(items[:12])}; "
        f"largest_non_highway={ratios.get('largest_non_highway_item')}; "
        "Eastmoney segment evidence requires annual-report spot check before final PIT promotion."
    )


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


def _mainop_type_name(value: Any) -> str:
    text = str(value or "").strip()
    return {"1": "industry", "2": "product", "3": "region"}.get(text, text)


def _is_segment_subitem(name: str) -> bool:
    return name.startswith("其中") or name.startswith("其中：") or name.startswith("其中:")


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


def _render_audit_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Highway Operating Data Audit",
        "",
        f"- Status: `{summary['status']}`",
        f"- Source: `{summary['source_csv']}`",
        f"- Rows: {summary['row_count']}",
        f"- PIT usable rows: {summary['pit_usable_rows']}",
        f"- Covered companies: {summary['covered_company_count']}",
        "",
        "## Required Fields",
        "",
    ]
    lines.extend(f"- {field}" for field in summary["required_fields"])
    lines.extend(["", summary["reason"], ""])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-highway-operating-evidence")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_disclosure = sub.add_parser("disclosures")
    p_disclosure.add_argument("panel", type=Path)
    p_disclosure.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)

    p_segment = sub.add_parser("eastmoney-segment")
    p_segment.add_argument("panel", type=Path)
    p_segment.add_argument("disclosure", type=Path)
    p_segment.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p_segment.add_argument("--limit", type=int)
    p_segment.add_argument("--sleep-seconds", type=float, default=0.25)

    p_template = sub.add_parser("manual-template")
    p_template.add_argument("disclosure", type=Path)
    p_template.add_argument("segment_evidence", type=Path)
    p_template.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)

    p_audit = sub.add_parser("audit")
    p_audit.add_argument("source", type=Path)
    p_audit.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR / "audit")

    p_panel = sub.add_parser("segment-panel")
    p_panel.add_argument("panel", type=Path)
    p_panel.add_argument("segment_evidence", type=Path)
    p_panel.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)

    p_sample = sub.add_parser("annual-sample")
    p_sample.add_argument("disclosure", type=Path)
    p_sample.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR / "annual_reports")
    p_sample.add_argument("--sample-size", type=int, default=8)
    p_sample.add_argument("--prefer-year", default="2024")

    p_annual_manifest = sub.add_parser("annual-manifest")
    p_annual_manifest.add_argument("disclosure", type=Path)
    p_annual_manifest.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR / "annual_reports")
    p_annual_manifest.add_argument("--start-year", default="2021")
    p_annual_manifest.add_argument("--end-year", default="2025")
    p_annual_manifest.add_argument("--limit", type=int)

    p_download = sub.add_parser("download-cninfo")
    p_download.add_argument("manifest", type=Path)
    p_download.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR / "annual_reports")

    p_extract = sub.add_parser("extract-operating-candidates")
    p_extract.add_argument("manifest", type=Path)
    p_extract.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR / "annual_reports")
    p_extract.add_argument("--max-pages-per-report", type=int)

    p_spot = sub.add_parser("spot-check-segment")
    p_spot.add_argument("downloaded_manifest", type=Path)
    p_spot.add_argument("eastmoney_raw", type=Path)
    p_spot.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR / "annual_reports")
    p_spot.add_argument("--max-items-per-report", type=int, default=5)

    p_review = sub.add_parser("review-operating-candidates")
    p_review.add_argument("candidate_csv", type=Path)
    p_review.add_argument("downloaded_manifest", type=Path)
    p_review.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR / "annual_reports")

    p_review_panel = sub.add_parser("reviewed-operating-panel")
    p_review_panel.add_argument("panel", type=Path)
    p_review_panel.add_argument("reviewed_operating", type=Path)
    p_review_panel.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR / "annual_reports")

    args = parser.parse_args(argv)
    if args.cmd == "disclosures":
        print(collect_highway_report_disclosure_dates(args.panel, args.out_dir))
    elif args.cmd == "eastmoney-segment":
        print(collect_eastmoney_highway_segment_evidence(args.panel, args.disclosure, args.out_dir, limit=args.limit, sleep_seconds=args.sleep_seconds))
    elif args.cmd == "manual-template":
        print(write_highway_operating_manual_template(args.disclosure, args.segment_evidence, args.out_dir))
    elif args.cmd == "audit":
        print(audit_highway_operating_data(args.source, args.out_dir))
    elif args.cmd == "segment-panel":
        print(build_highway_segment_enriched_panel(args.panel, args.segment_evidence, args.out_dir))
    elif args.cmd == "annual-sample":
        print(build_highway_annual_report_sample_manifest(args.disclosure, args.out_dir, sample_size=args.sample_size, prefer_year=args.prefer_year))
    elif args.cmd == "annual-manifest":
        print(build_highway_annual_report_manifest(args.disclosure, args.out_dir, start_year=args.start_year, end_year=args.end_year, limit=args.limit))
    elif args.cmd == "download-cninfo":
        print(download_cninfo_annual_reports(args.manifest, args.out_dir))
    elif args.cmd == "extract-operating-candidates":
        print(extract_highway_operating_candidates_from_reports(args.manifest, args.out_dir, max_pages_per_report=args.max_pages_per_report))
    elif args.cmd == "spot-check-segment":
        print(spot_check_eastmoney_segment_against_reports(args.downloaded_manifest, args.eastmoney_raw, args.out_dir, max_items_per_report=args.max_items_per_report))
    elif args.cmd == "review-operating-candidates":
        print(build_reviewed_operating_disclosure_data(args.candidate_csv, args.downloaded_manifest, args.out_dir))
    elif args.cmd == "reviewed-operating-panel":
        print(build_reviewed_operating_panel(args.panel, args.reviewed_operating, args.out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
