from __future__ import annotations

import argparse
import calendar
import csv
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Iterable

from v5.coal_external_state_runner import STATE_FIELDS, validate_coal_external_state
from v5.credential_loader import DEFAULT_CREDENTIAL_FILE, load_tushare_token


DEFAULT_DATABASE_DIR = Path("数据库")
DEFAULT_PROCESSED_DIR = DEFAULT_DATABASE_DIR / "processed"
DEFAULT_MANIFEST_DIR = DEFAULT_DATABASE_DIR / "manifests"

MANUAL_STATE_TEMPLATE_ROWS = [
    {
        "visible_date": "",
        "state_date": "",
        "state_scope": "national",
        "sub_industry": "all_coal",
        "metric": "coal_inventory_or_output_state",
        "value": "",
        "unit": "10k_ton_or_percent",
        "source_name": "National Bureau of Statistics",
        "source_url": "https://www.stats.gov.cn/sj/zxfb/",
        "source_publication_date": "",
        "pit_usable": "false",
        "review_status": "manual_template",
        "notes": "Monthly raw coal output or raw coal output YoY. Fill from NBS Energy Production Situation release with conservative visible_date.",
    },
    {
        "visible_date": "",
        "state_date": "",
        "state_scope": "circulation_market",
        "sub_industry": "thermal_coal",
        "metric": "thermal_coal_price_state",
        "value": "",
        "unit": "cny_per_ton",
        "source_name": "National Bureau of Statistics",
        "source_url": "https://www.stats.gov.cn/sj/zxfb/",
        "source_publication_date": "",
        "pit_usable": "false",
        "review_status": "manual_template",
        "notes": "NBS circulation production-material price, e.g. Shanxi mixed coal or ordinary mixed coal.",
    },
    {
        "visible_date": "",
        "state_date": "",
        "state_scope": "circulation_market",
        "sub_industry": "coking_coal",
        "metric": "coking_coal_price_state",
        "value": "",
        "unit": "cny_per_ton",
        "source_name": "National Bureau of Statistics",
        "source_url": "https://www.stats.gov.cn/sj/zxfb/",
        "source_publication_date": "",
        "pit_usable": "false",
        "review_status": "manual_template",
        "notes": "NBS circulation production-material price for coking coal if available.",
    },
    {
        "visible_date": "",
        "state_date": "",
        "state_scope": "port_or_market",
        "sub_industry": "thermal_coal",
        "metric": "thermal_coal_price_state",
        "value": "",
        "unit": "cny_per_ton_or_index",
        "source_name": "CCTD / Qinhuangdao coal market / national coal trading center",
        "source_url": "",
        "source_publication_date": "",
        "pit_usable": "false",
        "review_status": "manual_template_license_check_required",
        "notes": "Use only if licensed/manual download is permitted. Do not scrape blocked or paywalled pages.",
    },
    {
        "visible_date": "",
        "state_date": "",
        "state_scope": "port_or_market",
        "sub_industry": "all_coal",
        "metric": "coal_inventory_or_output_state",
        "value": "",
        "unit": "10k_ton_or_days",
        "source_name": "CCTD / port inventory / coal association / NDRC",
        "source_url": "",
        "source_publication_date": "",
        "pit_usable": "false",
        "review_status": "manual_template_license_check_required",
        "notes": "Inventory, port inventory, or inventory days. Use only with clear publication date and access permission.",
    },
]

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

SEGMENT_EVIDENCE_FIELDS = [
    "code",
    "ts_code",
    "report_period",
    "report_type",
    "notice_date",
    "visible_date",
    "coal_revenue_ratio",
    "coal_profit_ratio",
    "power_revenue_ratio",
    "coal_chemical_revenue_ratio",
    "approved_coal_business_tag",
    "source_name",
    "source_url",
    "pit_usable",
    "review_status",
    "notes",
]

EASTMONEY_SEGMENT_RAW_FIELDS = [
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

OFFICIAL_STATE_SEED_ROWS = [
    {
        "visible_date": "2026-06-16",
        "state_date": "2026-05-31",
        "state_scope": "national",
        "sub_industry": "all_coal",
        "metric": "coal_inventory_or_output_state",
        "value": "-1.7",
        "unit": "percent_yoy_raw_coal_output",
        "source_name": "National Bureau of Statistics energy production release",
        "source_url": "https://www.stats.gov.cn/sj/zxfb/202606/t20260616_1963948.html",
        "source_publication_date": "2026-06-16",
        "pit_usable": "true",
        "review_status": "official_seed_reviewed",
        "notes": "Official NBS May 2026 energy production release. Value is raw coal output YoY. Raw output volume should be added as a separate reviewed row if needed.",
    },
    {
        "visible_date": "2026-06-24",
        "state_date": "2026-06-20",
        "state_scope": "circulation_market",
        "sub_industry": "thermal_coal",
        "metric": "thermal_coal_price_state",
        "value": "862.0",
        "unit": "cny_per_ton",
        "source_name": "National Bureau of Statistics production-material circulation price release",
        "source_url": "https://www.stats.gov.cn/sj/zxfb/202606/t20260623_1963989.html",
        "source_publication_date": "2026-06-24",
        "pit_usable": "true",
        "review_status": "official_seed_reviewed",
        "notes": "NBS circulation-market Shanxi mixed coal 5500 kcal price for mid-June 2026. NBS adjusted coal item specifications in 2026, so long history must document item changes.",
    },
    {
        "visible_date": "2026-06-24",
        "state_date": "2026-06-20",
        "state_scope": "circulation_market",
        "sub_industry": "coking_coal",
        "metric": "coking_coal_price_state",
        "value": "1912.5",
        "unit": "cny_per_ton",
        "source_name": "National Bureau of Statistics production-material circulation price release",
        "source_url": "https://www.stats.gov.cn/sj/zxfb/202606/t20260623_1963989.html",
        "source_publication_date": "2026-06-24",
        "pit_usable": "true",
        "review_status": "official_seed_reviewed",
        "notes": "NBS circulation-market coking coal main coking coal price for mid-June 2026.",
    },
]


def write_coal_manual_state_template(out_dir: Path = DEFAULT_PROCESSED_DIR / "coal_external_state") -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    template_path = out_dir / "coal_manual_state_import_template.csv"
    _write_csv(template_path, STATE_FIELDS, MANUAL_STATE_TEMPLATE_ROWS)
    _write_json(
        out_dir / "coal_manual_state_import_manifest.json",
        {
            "dataset": "coal_manual_state_import_template",
            "template": str(template_path),
            "fields": STATE_FIELDS,
            "row_count": len(MANUAL_STATE_TEMPLATE_ROWS),
            "required_rule": "Set pit_usable=true only when source_publication_date and visible_date are filled and visible_date <= rebalance date.",
            "anti_crawler_rule": "Manual download is allowed only from sources with permitted access. Do not bypass login, paywall, robots policy, or anti-crawler controls.",
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return template_path


def write_coal_official_state_seed(out_dir: Path = DEFAULT_PROCESSED_DIR / "coal_external_state") -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    seed_path = out_dir / "coal_official_state_seed.csv"
    _write_csv(seed_path, STATE_FIELDS, OFFICIAL_STATE_SEED_ROWS)
    validation = validate_coal_external_state(seed_path)
    _write_json(
        out_dir / "coal_official_state_seed_manifest.json",
        {
            "dataset": "coal_official_state_seed",
            "output": str(seed_path),
            "row_count": len(OFFICIAL_STATE_SEED_ROWS),
            "validation": validation,
            "coverage_limitation": "Seed rows prove the official import path but do not cover the full 2015-2026 validation history.",
            "source_policy": "Only official, manually reviewed NBS rows are included. Do not treat proxy futures rows as formal thermal coal price evidence.",
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return seed_path


def write_nbs_historical_state_template(
    out_dir: Path = DEFAULT_PROCESSED_DIR / "coal_external_state",
    start_year: int = 2015,
    end_year: int = 2026,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            if year == 2026 and month > 6:
                continue
            state_date = _month_end_date(year, month)
            rows.append(
                _template_state_row(
                    state_date,
                    "national",
                    "all_coal",
                    "coal_inventory_or_output_state",
                    "10k_ton_or_percent_yoy",
                    "National Bureau of Statistics energy production release",
                    "https://www.stats.gov.cn/sj/zxfb/",
                    "Fill monthly raw coal output or YoY from NBS Energy Production Situation. Use publication date as conservative visible_date.",
                )
            )
            for period_day, period_name in [(10, "early"), (20, "middle"), (_month_end_day(year, month), "late")]:
                state_date = f"{year:04d}-{month:02d}-{period_day:02d}"
                for metric, sub_industry, unit, notes in [
                    (
                        "thermal_coal_price_state",
                        "thermal_coal",
                        "cny_per_ton",
                        "Fill Shanxi mixed coal / ordinary mixed coal / documented stitchable thermal coal item. Document item changes.",
                    ),
                    (
                        "coking_coal_price_state",
                        "coking_coal",
                        "cny_per_ton",
                        "Fill coking coal main coking coal item if available.",
                    ),
                ]:
                    rows.append(
                        _template_state_row(
                            state_date,
                            "circulation_market",
                            sub_industry,
                            metric,
                            unit,
                            "National Bureau of Statistics production-material circulation price release",
                            "https://www.stats.gov.cn/sj/zxfb/",
                            f"NBS {period_name}-period production-material circulation price. {notes}",
                        )
                    )
    out_path = out_dir / "coal_nbs_historical_state_import_template.csv"
    _write_csv(out_path, STATE_FIELDS, rows)
    _write_json(
        out_dir / "coal_nbs_historical_state_import_manifest.json",
        {
            "dataset": "coal_nbs_historical_state_import_template",
            "output": str(out_path),
            "start_year": start_year,
            "end_year": end_year,
            "row_count": len(rows),
            "pit_usable_count": 0,
            "required_rule": "Rows become PIT usable only after visible_date, source_publication_date, value and item notes are manually reviewed.",
            "item_change_warning": "NBS coal price specifications changed in 2026; historical stitching must document item identity and any breaks.",
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return out_path


def merge_coal_manual_state(
    base_state_csv: Path,
    manual_state_csv: Path,
    out_dir: Path = DEFAULT_PROCESSED_DIR / "coal_external_state",
) -> Path:
    base_rows = _read_csv(base_state_csv) if base_state_csv.exists() else []
    manual_rows = _read_csv(manual_state_csv)
    merged_rows = base_rows + manual_rows
    merged_rows = sorted(merged_rows, key=lambda row: (row.get("visible_date", ""), row.get("metric", ""), row.get("sub_industry", "")))
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "coal_external_state_enriched.csv"
    _write_csv(out_path, STATE_FIELDS, merged_rows)
    validation = validate_coal_external_state(out_path)
    _write_json(
        out_dir / "coal_external_state_enriched_manifest.json",
        {
            "dataset": "coal_external_state_enriched",
            "base_state_csv": str(base_state_csv),
            "manual_state_csv": str(manual_state_csv),
            "output": str(out_path),
            "row_count": len(merged_rows),
            "manual_row_count": len(manual_rows),
            "validation": validation,
            "governance": "Manual rows require source review before formal candidate promotion.",
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return out_path


def merge_coal_state_sources(
    out_dir: Path,
    *state_csvs: Path,
) -> Path:
    rows: list[dict[str, str]] = []
    for path in state_csvs:
        if path.exists():
            rows.extend(_read_csv(path))
    rows = sorted(rows, key=lambda row: (row.get("visible_date", ""), row.get("state_date", ""), row.get("metric", ""), row.get("sub_industry", "")))
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "coal_external_state_formal_candidate.csv"
    _write_csv(out_path, STATE_FIELDS, rows)
    validation = validate_coal_external_state(out_path)
    coverage = _state_coverage_summary(rows)
    _write_json(
        out_dir / "coal_external_state_formal_candidate_manifest.json",
        {
            "dataset": "coal_external_state_formal_candidate",
            "sources": [str(path) for path in state_csvs],
            "output": str(out_path),
            "row_count": len(rows),
            "validation": validation,
            "coverage": coverage,
            "status": "needs_review" if coverage["formal_history_ready"] is False else "ready_for_quant_review",
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return out_path


def write_coal_business_tag_visible_date_template(
    panel_csv: Path,
    out_dir: Path = DEFAULT_PROCESSED_DIR / "coal_business_tags",
) -> Path:
    rows = _read_csv(panel_csv)
    by_code: dict[str, dict[str, Any]] = {}
    for row in rows:
        code = row.get("code", "")
        if not code:
            continue
        item = by_code.setdefault(
            code,
            {
                "code": code,
                "company_name": row.get("company_name", ""),
                "current_manual_coal_business_tag": row.get("coal_business_tag", ""),
                "first_panel_trade_date": row.get("trade_date", ""),
                "last_panel_trade_date": row.get("trade_date", ""),
                "visible_date": "",
                "report_period": "",
                "report_publication_date": "",
                "evidence_type": "annual_or_interim_report_segment",
                "coal_revenue_ratio": "",
                "coal_profit_ratio": "",
                "power_revenue_ratio": "",
                "coal_chemical_revenue_ratio": "",
                "approved_coal_business_tag": "",
                "source_name": "",
                "source_url": "",
                "pit_usable": "false",
                "review_status": "template_requires_company_report_evidence",
                "notes": "Fill with company-report publication date and segment revenue/profit evidence. Current manual tag must not be used as PIT evidence.",
            },
        )
        item["first_panel_trade_date"] = min(str(item["first_panel_trade_date"]), str(row.get("trade_date", "")))
        item["last_panel_trade_date"] = max(str(item["last_panel_trade_date"]), str(row.get("trade_date", "")))
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "coal_business_tag_visible_date_template.csv"
    fields = [
        "code",
        "company_name",
        "current_manual_coal_business_tag",
        "first_panel_trade_date",
        "last_panel_trade_date",
        "visible_date",
        "report_period",
        "report_publication_date",
        "evidence_type",
        "coal_revenue_ratio",
        "coal_profit_ratio",
        "power_revenue_ratio",
        "coal_chemical_revenue_ratio",
        "approved_coal_business_tag",
        "source_name",
        "source_url",
        "pit_usable",
        "review_status",
        "notes",
    ]
    template_rows = sorted(by_code.values(), key=lambda row: row["code"])
    _write_csv(out_path, fields, template_rows)
    _write_json(
        out_dir / "coal_business_tag_visible_date_manifest.json",
        {
            "dataset": "coal_business_tag_visible_date_template",
            "panel": str(panel_csv),
            "output": str(out_path),
            "company_count": len(template_rows),
            "pit_usable_count": 0,
            "status": "template_requires_company_report_evidence",
            "required_rule": "Set pit_usable=true only when visible_date equals or follows the report publication date and segment evidence supports the approved tag.",
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return out_path


def write_coal_segment_evidence_template(
    disclosure_csv: Path,
    out_dir: Path = DEFAULT_PROCESSED_DIR / "coal_business_tags",
) -> Path:
    disclosures = _read_csv(disclosure_csv)
    rows = []
    for row in disclosures:
        rows.append(
            {
                "code": row.get("code", ""),
                "ts_code": row.get("ts_code", ""),
                "report_period": row.get("report_period", ""),
                "report_type": row.get("report_type", ""),
                "notice_date": row.get("notice_date", ""),
                "visible_date": row.get("notice_date", ""),
                "coal_revenue_ratio": "",
                "coal_profit_ratio": "",
                "power_revenue_ratio": "",
                "coal_chemical_revenue_ratio": "",
                "approved_coal_business_tag": "",
                "source_name": row.get("source_name", "tushare.disclosure_date"),
                "source_url": "",
                "pit_usable": "false",
                "review_status": "template_requires_segment_revenue_profit_evidence",
                "notes": "Fill segment revenue/profit evidence from the visible report before setting pit_usable=true.",
            }
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "coal_segment_business_evidence_template.csv"
    _write_csv(out_path, SEGMENT_EVIDENCE_FIELDS, rows)
    _write_json(
        out_dir / "coal_segment_business_evidence_manifest.json",
        {
            "dataset": "coal_segment_business_evidence_template",
            "disclosure_csv": str(disclosure_csv),
            "output": str(out_path),
            "row_count": len(rows),
            "pit_usable_count": 0,
            "required_rule": "PIT business tags require report visible_date and segment revenue/profit evidence.",
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return out_path


def audit_coal_segment_evidence(
    evidence_csv: Path,
    out_dir: Path = DEFAULT_MANIFEST_DIR / "coal_segment_evidence_audit",
) -> Path:
    rows = _read_csv(evidence_csv)
    usable = [row for row in rows if str(row.get("pit_usable", "")).lower() == "true"]
    complete = [
        row
        for row in usable
        if row.get("visible_date")
        and row.get("approved_coal_business_tag")
        and (row.get("coal_revenue_ratio") or row.get("coal_profit_ratio"))
    ]
    by_code = {row.get("code", "") for row in complete if row.get("code")}
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "dataset": "coal_segment_evidence_audit",
        "evidence_csv": str(evidence_csv),
        "row_count": len(rows),
        "pit_usable_rows": len(usable),
        "complete_rows": len(complete),
        "covered_company_count": len(by_code),
        "status": "pass" if len(by_code) >= 37 and len(complete) >= 37 else "blocked",
        "reason": "Business tags require segment revenue/profit evidence for all coal companies before formal candidate promotion.",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    _write_json(out_dir / "coal_segment_evidence_audit_summary.json", summary)
    _write_report(out_dir / "coal_segment_evidence_audit_report.md", "Coal Segment Evidence Audit", summary)
    return out_dir / "coal_segment_evidence_audit_report.md"


def collect_eastmoney_coal_segment_evidence(
    panel_csv: Path,
    disclosure_csv: Path,
    out_dir: Path = DEFAULT_PROCESSED_DIR / "coal_business_tags",
    request_timeout_seconds: float = 15.0,
    sleep_seconds: float = 0.25,
    limit: int | None = None,
) -> Path:
    panel_rows = _read_csv(panel_csv)
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
    raw_path = out_dir / "eastmoney_coal_segment_raw.csv"
    evidence_path = out_dir / "coal_segment_business_evidence_eastmoney.csv"
    _write_csv(raw_path, EASTMONEY_SEGMENT_RAW_FIELDS, raw_rows)
    _write_csv(evidence_path, SEGMENT_EVIDENCE_FIELDS, evidence_rows)
    complete_rows = [
        row
        for row in evidence_rows
        if str(row.get("pit_usable", "")).lower() == "true"
        and row.get("approved_coal_business_tag")
        and (row.get("coal_revenue_ratio") or row.get("coal_profit_ratio"))
    ]
    _write_json(
        out_dir / "eastmoney_coal_segment_evidence_manifest.json",
        {
            "dataset": "eastmoney_coal_segment_evidence",
            "panel": str(panel_csv),
            "disclosure_csv": str(disclosure_csv),
            "raw_output": str(raw_path),
            "evidence_output": str(evidence_path),
            "requested_company_count": len(codes),
            "raw_row_count": len(raw_rows),
            "evidence_row_count": len(evidence_rows),
            "complete_rows": len(complete_rows),
            "covered_company_count": len({row["code"] for row in complete_rows}),
            "warning_count": len(warnings),
            "warnings": warnings,
            "source_policy": "Eastmoney public F10 BusinessAnalysis/PageAjax via normal HTTP request with timeout and no anti-crawler bypass.",
            "pit_policy": "visible_date is joined from Tushare disclosure_date for the same report period when available.",
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return evidence_path


def collect_tushare_coal_segment_evidence(
    panel_csv: Path,
    disclosure_csv: Path,
    out_dir: Path = DEFAULT_PROCESSED_DIR / "coal_business_tags",
    codes: list[str] | None = None,
    sleep_seconds: float = 0.25,
) -> Path:
    panel_rows = _read_csv(panel_csv)
    panel_codes = sorted({row.get("code", "") for row in panel_rows if row.get("code")})
    target_codes = sorted(codes or panel_codes)
    disclosure_rows = _read_csv(disclosure_csv)
    target_periods = [
        row
        for row in disclosure_rows
        if row.get("code") in target_codes and row.get("report_period")
    ]
    disclosures = _disclosures_by_code_period(disclosure_csv)
    raw_rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    try:
        import tushare as ts
    except Exception as exc:
        raise RuntimeError("tushare is required for coal segment fallback collection") from exc
    token = load_tushare_token()
    if not token:
        raise RuntimeError("Tushare token is not available for coal segment fallback collection")
    pro = ts.pro_api(token)
    for item in target_periods:
        code = item["code"]
        report_period = item["report_period"]
        try:
            records = _fetch_tushare_segment_records(pro, code, report_period)
        except Exception as exc:
            warnings.append(f"{code}:{report_period}: Tushare fina_mainbz failed: {type(exc).__name__}: {exc}")
            continue
        if not records:
            warnings.append(f"{code}:{report_period}: Tushare fina_mainbz returned no rows")
        raw_rows.extend(_normalize_tushare_segment_records(code, report_period, records))
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)
    evidence_rows = _build_segment_evidence_from_raw(raw_rows, disclosures)
    for row in evidence_rows:
        row["source_name"] = "Tushare fina_mainbz + Tushare disclosure_date"
        row["review_status"] = _tushare_segment_review_status(row)
        row["notes"] = _tushare_segment_notes(row)
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / "tushare_coal_segment_raw.csv"
    evidence_path = out_dir / "coal_segment_business_evidence_tushare.csv"
    _write_csv(raw_path, EASTMONEY_SEGMENT_RAW_FIELDS, raw_rows)
    _write_csv(evidence_path, SEGMENT_EVIDENCE_FIELDS, evidence_rows)
    complete_rows = [
        row
        for row in evidence_rows
        if str(row.get("pit_usable", "")).lower() == "true"
        and row.get("approved_coal_business_tag")
        and (row.get("coal_revenue_ratio") or row.get("coal_profit_ratio"))
    ]
    _write_json(
        out_dir / "tushare_coal_segment_evidence_manifest.json",
        {
            "dataset": "tushare_coal_segment_evidence",
            "panel": str(panel_csv),
            "disclosure_csv": str(disclosure_csv),
            "raw_output": str(raw_path),
            "evidence_output": str(evidence_path),
            "requested_company_count": len(target_codes),
            "requested_period_count": len(target_periods),
            "raw_row_count": len(raw_rows),
            "evidence_row_count": len(evidence_rows),
            "complete_rows": len(complete_rows),
            "covered_company_count": len({row["code"] for row in complete_rows}),
            "warning_count": len(warnings),
            "warnings": warnings,
            "source_policy": "Tushare fina_mainbz is used as a licensed structured fallback for Eastmoney segment gaps. Credentials are never written.",
            "pit_policy": "visible_date is joined from Tushare disclosure_date for the same report period when available.",
            "research_rule": "Coal trade exposure without coal mining/selection business is not upgraded to core coal. It remains mixed_or_special_review or non_core_or_review for Research Agent judgment.",
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return evidence_path


def merge_coal_segment_evidence_sources(
    eastmoney_csv: Path,
    fallback_csv: Path,
    out_dir: Path = DEFAULT_PROCESSED_DIR / "coal_business_tags",
) -> Path:
    eastmoney_rows = _read_csv(eastmoney_csv)
    fallback_rows = _read_csv(fallback_csv)
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for row in fallback_rows:
        if _segment_row_complete(row):
            merged[(row["code"], row["report_period"])] = row
    for row in eastmoney_rows:
        if _segment_row_complete(row):
            key = (row["code"], row["report_period"])
            merged[key] = row
    rows = [merged[key] for key in sorted(merged)]
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "coal_segment_business_evidence_reviewed.csv"
    _write_csv(out_path, SEGMENT_EVIDENCE_FIELDS, rows)
    source_counts = {}
    for row in rows:
        source = row.get("source_name", "")
        source_counts[source] = source_counts.get(source, 0) + 1
    _write_json(
        out_dir / "coal_segment_business_evidence_reviewed_manifest.json",
        {
            "dataset": "coal_segment_business_evidence_reviewed",
            "eastmoney_csv": str(eastmoney_csv),
            "fallback_csv": str(fallback_csv),
            "output": str(out_path),
            "row_count": len(rows),
            "covered_company_count": len({row["code"] for row in rows if row.get("code")}),
            "source_counts": source_counts,
            "governance": "Eastmoney is preferred where complete; Tushare fills Eastmoney gaps. Research Agent must review trade-only, shell, ST, delisted, or non-disclosure cases before formal acceptance.",
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return out_path


def build_coal_reviewed_business_tag_panel(
    panel_csv: Path,
    evidence_csv: Path,
    out_dir: Path = DEFAULT_PROCESSED_DIR / "coal_business_tags",
) -> Path:
    panel_rows = _read_csv(panel_csv)
    evidence_by_code = _complete_segment_evidence_by_code(evidence_csv)
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
                    "formal_coal_universe_include": "false",
                    "reviewed_coal_business_tag": "",
                    "business_tag_review_status": "missing_visible_segment_evidence",
                    "business_tag_evidence_report_period": "",
                    "business_tag_notes": "No visible segment evidence available at this trade date.",
                }
            )
        else:
            tag = evidence.get("approved_coal_business_tag", "")
            include = _formal_coal_universe_include(tag, evidence)
            if not include:
                excluded_rows += 1
            out["coal_business_tag"] = tag
            out["is_core_coal_numeric"] = "1" if tag == "core_coal" else "0"
            out["business_tag_visible_date"] = evidence.get("visible_date", "")
            out["business_tag_source"] = evidence.get("source_name", "")
            out.update(
                {
                    "formal_coal_universe_include": "true" if include else "false",
                    "reviewed_coal_business_tag": tag,
                    "business_tag_review_status": evidence.get("review_status", ""),
                    "business_tag_evidence_report_period": evidence.get("report_period", ""),
                    "business_tag_notes": evidence.get("notes", ""),
                }
            )
        rows.append(out)
    fields = list(panel_rows[0].keys()) if panel_rows else []
    for field in [
        "formal_coal_universe_include",
        "reviewed_coal_business_tag",
        "business_tag_review_status",
        "business_tag_evidence_report_period",
        "business_tag_notes",
    ]:
        if field not in fields:
            fields.append(field)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "coal_business_tag_pit_reviewed_panel.csv"
    formal_rows = [row for row in rows if row.get("formal_coal_universe_include") == "true"]
    formal_path = out_dir / "coal_business_tag_pit_formal_universe_panel.csv"
    _write_csv(out_path, fields, rows)
    _write_csv(formal_path, fields, formal_rows)
    _write_json(
        out_dir / "coal_business_tag_pit_reviewed_panel_manifest.json",
        {
            "dataset": "coal_business_tag_pit_reviewed_panel",
            "panel_csv": str(panel_csv),
            "evidence_csv": str(evidence_csv),
            "output": str(out_path),
            "formal_universe_output": str(formal_path),
            "row_count": len(rows),
            "formal_universe_row_count": len(formal_rows),
            "missing_visible_segment_rows": missing_rows,
            "formal_universe_excluded_rows": excluded_rows,
            "formal_universe_included_rows": len(rows) - missing_rows - excluded_rows,
            "covered_company_count": len({row["code"] for row in rows if row.get("business_tag_review_status") != "missing_visible_segment_evidence"}),
            "governance": "This reviewed panel separates PIT business exposure from formal universe inclusion. Non-core, shell, trade-only and disclosure-risk rows are excluded from formal coal universe by default.",
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return out_path


def collect_coal_report_disclosure_dates(
    panel_csv: Path,
    out_dir: Path = DEFAULT_PROCESSED_DIR / "coal_business_tags",
    credential_file: Path = DEFAULT_CREDENTIAL_FILE,
    token_env: str = "TUSHARE_TOKEN",
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    panel_rows = _read_csv(panel_csv)
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
            rows = _fetch_coal_disclosure_rows(pro, codes, target_years, warnings)
        except Exception as exc:
            warnings.append(f"tushare disclosure_date collection failed: {type(exc).__name__}: {exc}")

    out_path = out_dir / "coal_report_disclosure_dates.csv"
    _write_csv(out_path, REPORT_DISCLOSURE_FIELDS, rows)
    _write_json(
        out_dir / "coal_report_disclosure_dates_manifest.json",
        {
            "dataset": "coal_report_disclosure_dates",
            "panel": str(panel_csv),
            "output": str(out_path),
            "code_count": len(codes),
            "target_years": sorted(target_years),
            "row_count": len(rows),
            "warning_count": len(warnings),
            "warnings": warnings,
            "source_policy": "Tushare disclosure_date supplies report timing only. It does not prove coal segment exposure.",
            "pit_policy": "Business tags remain blocked until report-date rows are joined with segment revenue/profit evidence.",
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return out_path


def audit_coal_business_tags(panel_csv: Path, out_dir: Path = DEFAULT_MANIFEST_DIR / "coal_business_tag_audit") -> Path:
    rows = _read_csv(panel_csv)
    out_dir.mkdir(parents=True, exist_ok=True)
    by_code: dict[str, dict[str, Any]] = {}
    for row in rows:
        code = row.get("code", "")
        if not code:
            continue
        item = by_code.setdefault(
            code,
            {
                "code": code,
                "company_name": row.get("company_name", ""),
                "coal_business_tag": row.get("coal_business_tag", ""),
                "first_trade_date": row.get("trade_date", ""),
                "last_trade_date": row.get("trade_date", ""),
                "row_count": 0,
                "business_tag_source": row.get("business_tag_source", ""),
                "business_tag_visible_date_min": row.get("business_tag_visible_date", ""),
                "formal_pit_usable": "false",
                "audit_status": "blocked_manual_current_classification",
                "required_action": "Audit annual/interim report publication dates and segment revenue/profit exposure before formal use.",
            },
        )
        item["row_count"] += 1
        item["first_trade_date"] = min(str(item["first_trade_date"]), str(row.get("trade_date", "")))
        item["last_trade_date"] = max(str(item["last_trade_date"]), str(row.get("trade_date", "")))
        if row.get("coal_business_tag") != item["coal_business_tag"]:
            item["audit_status"] = "blocked_tag_changes_need_review"
    audit_rows = list(by_code.values())
    audit_path = out_dir / "coal_business_tag_audit.csv"
    _write_csv(audit_path, list(audit_rows[0].keys()) if audit_rows else ["code"], audit_rows)
    summary = {
        "dataset": "coal_business_tag_audit",
        "panel": str(panel_csv),
        "row_count": len(audit_rows),
        "formal_pit_usable_count": sum(1 for row in audit_rows if row["formal_pit_usable"] == "true"),
        "blocked_count": sum(1 for row in audit_rows if row["formal_pit_usable"] != "true"),
        "status": "blocked",
        "reason": "Current coal_business_tag values are manual classifications without company-report visible-date audit.",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    _write_json(out_dir / "coal_business_tag_audit_summary.json", summary)
    _write_report(out_dir / "coal_business_tag_audit_report.md", "Coal Business Tag Audit", summary)
    return out_dir / "coal_business_tag_audit_report.md"


def audit_coal_capex_fcf(panel_csv: Path, out_dir: Path = DEFAULT_MANIFEST_DIR / "coal_capex_fcf_audit") -> Path:
    rows = _read_csv(panel_csv)
    audit_rows = []
    capex_burdens = []
    fcf_yields = []
    ocf_yields = []
    for row in rows:
        ocf_yield = _to_float(row.get("operating_cash_flow_yield"))
        fcf_yield = _to_float(row.get("free_cash_flow_yield"))
        capex_burden = _to_float(row.get("capex_burden"))
        if ocf_yield is not None:
            ocf_yields.append(ocf_yield)
        if fcf_yield is not None:
            fcf_yields.append(fcf_yield)
        if capex_burden is not None:
            capex_burdens.append(capex_burden)
        flags = []
        if capex_burden is None:
            flags.append("missing_capex_burden")
        elif capex_burden < 0:
            flags.append("negative_capex_burden")
        elif capex_burden > 1:
            flags.append("capex_exceeds_ocf")
        if ocf_yield is not None and fcf_yield is not None and fcf_yield > ocf_yield:
            flags.append("fcf_greater_than_ocf")
        if fcf_yield is not None and fcf_yield < 0:
            flags.append("negative_fcf_yield")
        if flags:
            audit_rows.append(
                {
                    "trade_date": row.get("trade_date", ""),
                    "code": row.get("code", ""),
                    "company_name": row.get("company_name", ""),
                    "coal_business_tag": row.get("coal_business_tag", ""),
                    "operating_cash_flow_yield": row.get("operating_cash_flow_yield", ""),
                    "free_cash_flow_yield": row.get("free_cash_flow_yield", ""),
                    "capex_burden": row.get("capex_burden", ""),
                    "flags": ";".join(flags),
                }
            )

    out_dir.mkdir(parents=True, exist_ok=True)
    audit_path = out_dir / "coal_capex_fcf_audit_flags.csv"
    _write_csv(
        audit_path,
        ["trade_date", "code", "company_name", "coal_business_tag", "operating_cash_flow_yield", "free_cash_flow_yield", "capex_burden", "flags"],
        audit_rows,
    )
    summary = {
        "dataset": "coal_capex_fcf_audit",
        "panel": str(panel_csv),
        "panel_rows": len(rows),
        "flagged_rows": len(audit_rows),
        "flagged_ratio": _ratio(len(audit_rows), len(rows)),
        "ocf_yield_median": _median(ocf_yields),
        "fcf_yield_median": _median(fcf_yields),
        "capex_burden_median": _median(capex_burdens),
        "capex_burden_p90": _quantile(capex_burdens, 0.9),
        "negative_fcf_rows": sum(1 for row in audit_rows if "negative_fcf_yield" in row["flags"]),
        "capex_exceeds_ocf_rows": sum(1 for row in audit_rows if "capex_exceeds_ocf" in row["flags"]),
        "status": "needs_review" if audit_rows else "pass",
        "interpretation": "FCF yield is useful only if capex outliers and negative FCF cases are reviewed before formal candidate promotion.",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    _write_json(out_dir / "coal_capex_fcf_audit_summary.json", summary)
    _write_report(out_dir / "coal_capex_fcf_audit_report.md", "Coal Capex / FCF Audit", summary)
    return out_dir / "coal_capex_fcf_audit_report.md"


def build_coal_capex_policy_panel(
    panel_csv: Path,
    out_dir: Path = DEFAULT_PROCESSED_DIR / "coal_pit_panel_capex_policy",
) -> Path:
    rows = _read_csv(panel_csv)
    output_rows = []
    for row in rows:
        capex_burden = _to_float(row.get("capex_burden"))
        fcf_yield = _to_float(row.get("free_cash_flow_yield"))
        ocf_yield = _to_float(row.get("operating_cash_flow_yield"))
        flags = []
        if capex_burden is None:
            flags.append("capex_missing")
        elif capex_burden > 1:
            flags.append("capex_exceeds_ocf")
        elif capex_burden > 0.75:
            flags.append("high_capex_burden")
        if fcf_yield is not None and fcf_yield < 0:
            flags.append("negative_fcf_yield")
        if ocf_yield is None:
            flags.append("missing_ocf_yield")
        reviewed = dict(row)
        reviewed["fcf_use_policy"] = "auxiliary_only_until_capex_review"
        reviewed["ocf_use_policy"] = "primary_cashflow_factor_candidate"
        reviewed["capex_policy_flags"] = ";".join(flags)
        reviewed["fcf_policy_score"] = "" if flags else row.get("free_cash_flow_yield", "")
        output_rows.append(reviewed)

    out_dir.mkdir(parents=True, exist_ok=True)
    fields = list(output_rows[0].keys()) if output_rows else []
    out_path = out_dir / "panel_capex_policy.csv"
    _write_csv(out_path, fields, output_rows)
    flagged_rows = sum(1 for row in output_rows if row.get("capex_policy_flags"))
    _write_json(
        out_dir / "capex_policy_manifest.json",
        {
            "dataset": "coal_pit_panel_capex_policy",
            "source_panel": str(panel_csv),
            "output": str(out_path),
            "row_count": len(output_rows),
            "flagged_rows": flagged_rows,
            "flagged_ratio": _ratio(flagged_rows, len(output_rows)),
            "decision": "OCF remains primary. FCF is auxiliary until capex policy flags are reviewed.",
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return out_path


def _write_report(path: Path, title: str, summary: dict[str, Any]) -> None:
    lines = [f"# {title}", ""]
    for key, value in summary.items():
        lines.append(f"- {key}: `{value}`")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _template_state_row(
    state_date: str,
    state_scope: str,
    sub_industry: str,
    metric: str,
    unit: str,
    source_name: str,
    source_url: str,
    notes: str,
) -> dict[str, str]:
    return {
        "visible_date": "",
        "state_date": state_date,
        "state_scope": state_scope,
        "sub_industry": sub_industry,
        "metric": metric,
        "value": "",
        "unit": unit,
        "source_name": source_name,
        "source_url": source_url,
        "source_publication_date": "",
        "pit_usable": "false",
        "review_status": "manual_import_required",
        "notes": notes,
    }


def _month_end_date(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}-{_month_end_day(year, month):02d}"


def _month_end_day(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def _state_coverage_summary(rows: list[dict[str, str]]) -> dict[str, Any]:
    usable = [row for row in rows if str(row.get("pit_usable", "")).lower() == "true"]
    by_metric: dict[str, set[str]] = {}
    for row in usable:
        metric = row.get("metric", "")
        state_date = row.get("state_date", "")
        if metric and state_date:
            by_metric.setdefault(metric, set()).add(state_date[:7])
    required = ["coal_inventory_or_output_state", "thermal_coal_price_state", "coking_coal_price_state"]
    metric_month_counts = {metric: len(by_metric.get(metric, set())) for metric in required}
    return {
        "metric_month_counts": metric_month_counts,
        "formal_history_ready": all(count >= 80 for count in metric_month_counts.values()),
        "minimum_required_months_per_metric": 80,
    }


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


def _fetch_tushare_segment_records(pro: Any, code: str, report_period: str) -> list[dict[str, Any]]:
    period = report_period.replace("-", "")
    df = pro.fina_mainbz(ts_code=_to_ts_code(code), period=period)
    if df is None or getattr(df, "empty", True):
        return []
    return df.to_dict("records")


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
                "main_business_income": _fmt_float(record.get("MAIN_BUSINESS_INCOME")),
                "income_ratio": _fmt_float(record.get("MBI_RATIO")),
                "main_business_cost": _fmt_float(record.get("MAIN_BUSINESS_COST")),
                "cost_ratio": _fmt_float(record.get("MBC_RATIO")),
                "main_business_profit": _fmt_float(record.get("MAIN_BUSINESS_RPOFIT")),
                "profit_ratio": _fmt_float(record.get("MBR_RATIO")),
                "gross_profit_ratio": _fmt_float(record.get("GROSS_RPOFIT_RATIO")),
                "source_name": "Eastmoney F10 BusinessAnalysis",
                "source_url": f"https://emweb.securities.eastmoney.com/PC_HSF10/BusinessAnalysis/Index?type=web&code={_to_eastmoney_code(code)}",
            }
        )
    return rows


def _normalize_tushare_segment_records(code: str, report_period: str, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        row_period = _format_date(_date_text(record.get("end_date"))) or report_period
        rows.append(
            {
                "code": code,
                "eastmoney_code": _to_eastmoney_code(code),
                "report_period": row_period,
                "mainop_type": _tushare_bz_type_name(record.get("bz_code")),
                "item_name": str(record.get("bz_item") or "").strip(),
                "main_business_income": _fmt_float(record.get("bz_sales")),
                "income_ratio": "",
                "main_business_cost": _fmt_float(record.get("bz_cost")),
                "cost_ratio": "",
                "main_business_profit": _fmt_float(record.get("bz_profit")),
                "profit_ratio": "",
                "gross_profit_ratio": "",
                "source_name": "Tushare fina_mainbz",
                "source_url": "https://tushare.pro/document/2?doc_id=81",
            }
        )
    return rows


def _build_segment_evidence_from_raw(
    raw_rows: list[dict[str, Any]],
    disclosures: dict[tuple[str, str], dict[str, str]],
) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in raw_rows:
        by_key.setdefault((row["code"], row["report_period"]), []).append(row)
    evidence_rows = []
    for (code, report_period), rows in sorted(by_key.items()):
        selected = [row for row in rows if row.get("mainop_type") == "product"]
        if not selected:
            selected = [row for row in rows if row.get("mainop_type") == "industry"]
        if not selected:
            selected = rows
        selected = [row for row in selected if not _is_segment_subitem(str(row.get("item_name") or ""))]
        ratios = _segment_ratios(selected)
        disclosure = disclosures.get((code, report_period), {})
        visible_date = disclosure.get("notice_date", "")
        context = _segment_context(rows)
        tag = _approved_coal_business_tag(
            ratios["coal_revenue_ratio"],
            ratios["coal_profit_ratio"],
            ratios["power_revenue_ratio"],
            ratios["coal_chemical_revenue_ratio"],
            context,
        )
        evidence_rows.append(
            {
                "code": code,
                "ts_code": _to_ts_code(code),
                "report_period": report_period,
                "report_type": "semiannual" if report_period.endswith("-06-30") else "annual" if report_period.endswith("-12-31") else "other",
                "notice_date": visible_date,
                "visible_date": visible_date,
                "coal_revenue_ratio": _fmt_float(ratios["coal_revenue_ratio"]),
                "coal_profit_ratio": _fmt_float(ratios["coal_profit_ratio"]),
                "power_revenue_ratio": _fmt_float(ratios["power_revenue_ratio"]),
                "coal_chemical_revenue_ratio": _fmt_float(ratios["coal_chemical_revenue_ratio"]),
                "approved_coal_business_tag": tag,
                "source_name": "Eastmoney F10 BusinessAnalysis + Tushare disclosure_date",
                "source_url": f"https://emweb.securities.eastmoney.com/PC_HSF10/BusinessAnalysis/Index?type=web&code={_to_eastmoney_code(code)}",
                "pit_usable": "true" if visible_date and tag else "false",
                "review_status": "eastmoney_segment_needs_spot_check" if visible_date and tag else "missing_disclosure_or_segment_tag",
                "notes": _segment_evidence_notes(context),
            }
        )
    return evidence_rows


def _segment_ratios(rows: list[dict[str, Any]]) -> dict[str, float]:
    result = {
        "coal_revenue_ratio": 0.0,
        "coal_profit_ratio": 0.0,
        "power_revenue_ratio": 0.0,
        "coal_chemical_revenue_ratio": 0.0,
    }
    total_income = sum(_to_float(row.get("main_business_income")) or 0.0 for row in rows)
    profit_values = [_to_float(row.get("main_business_profit")) for row in rows]
    total_profit = sum(value for value in profit_values if value is not None)
    for row in rows:
        bucket = _segment_bucket(str(row.get("item_name") or ""))
        income_ratio = _to_float(row.get("income_ratio"))
        if income_ratio is None:
            income_value = _to_float(row.get("main_business_income"))
            income_ratio = _ratio(income_value, total_income) if income_value is not None else 0.0
            income_ratio = income_ratio or 0.0
        profit_ratio = _to_float(row.get("profit_ratio"))
        if profit_ratio is None:
            profit_value = _to_float(row.get("main_business_profit"))
            profit_ratio = _ratio(profit_value, total_profit) if profit_value is not None else 0.0
            profit_ratio = profit_ratio or 0.0
        if bucket == "coal":
            result["coal_revenue_ratio"] += income_ratio
            result["coal_profit_ratio"] += profit_ratio
        elif bucket == "power":
            result["power_revenue_ratio"] += income_ratio
        elif bucket == "coal_chemical":
            result["coal_chemical_revenue_ratio"] += income_ratio
    return {key: min(1.0, max(0.0, value)) for key, value in result.items()}


def _is_segment_subitem(item_name: str) -> bool:
    text = item_name.strip()
    return text.startswith("其中") or text.startswith("其中:") or text.startswith("其中：")


def _segment_bucket(item_name: str) -> str:
    text = item_name.lower()
    if any(keyword in item_name for keyword in ["煤化工", "化工", "甲醇", "尿素", "烯烃", "焦化", "焦炭"]):
        return "coal_chemical"
    if any(keyword in item_name for keyword in ["电力", "发电", "供电", "热力", "供热"]):
        return "power"
    if any(keyword in item_name for keyword in ["煤", "煤炭", "原煤", "洗煤", "选煤", "焦煤", "动力煤"]):
        return "coal"
    if "coal" in text:
        return "coal"
    return "other"


def _segment_context(rows: list[dict[str, Any]]) -> dict[str, bool]:
    names = " ".join(str(row.get("item_name") or "") for row in rows)
    return {
        "coal_mining_or_washing": any(keyword in names for keyword in ["煤炭采选", "煤炭开采", "煤炭洗选", "采煤", "洗煤", "选煤"]),
        "coal_trade": any(keyword in names for keyword in ["贸易", "大宗贸易", "贸易业务", "贸易煤"]),
        "medical_or_game": any(keyword in names for keyword in ["医疗", "网络游戏", "手游", "端游", "广告", "媒体平台"]),
        "manufacturing_or_potash": any(keyword in names for keyword in ["键合材料", "钾肥", "纺织", "花岗岩", "供电"]),
    }


def _approved_coal_business_tag(coal_revenue: float, coal_profit: float, power_revenue: float, coal_chemical_revenue: float, context: dict[str, bool] | None = None) -> str:
    context = context or {}
    if context.get("medical_or_game") and coal_revenue < 0.4 and coal_profit < 0.4:
        return "non_core_or_review"
    if context.get("manufacturing_or_potash") and coal_revenue < 0.4 and coal_profit < 0.4:
        return "non_core_or_review"
    coal_core = max(coal_revenue, coal_profit) >= 0.7
    if coal_core and context.get("coal_trade") and not context.get("coal_mining_or_washing"):
        return "mixed_or_special_review"
    if coal_core and power_revenue >= 0.15:
        return "mixed_power_coal"
    if coal_core and coal_chemical_revenue >= 0.15:
        return "mixed_coal_chemical"
    if coal_core:
        return "core_coal"
    if coal_revenue >= 0.4 or coal_profit >= 0.4:
        return "mixed_or_special_review"
    return "non_core_or_review"


def _segment_evidence_notes(context: dict[str, bool]) -> str:
    notes = ["Ratios use product classification where available, otherwise industry classification. Coal chemical is classified before coal to avoid double-counting."]
    if context.get("coal_trade") and not context.get("coal_mining_or_washing"):
        notes.append("Coal exposure appears to be trade-oriented rather than mining/operation; Research Agent must not upgrade it to core coal without report support.")
    if context.get("medical_or_game") or context.get("manufacturing_or_potash"):
        notes.append("Non-coal operating segments are material; treat as non-core or special-review exposure.")
    return " ".join(notes)


def _tushare_segment_review_status(row: dict[str, Any]) -> str:
    tag = row.get("approved_coal_business_tag", "")
    notes = row.get("notes", "")
    if tag in {"non_core_or_review", "mixed_or_special_review"} and ("trade-oriented" in notes or "Non-coal" in notes):
        return "research_disclosure_risk_review"
    return "reviewed_segment_evidence_tushare_mainbz"


def _tushare_segment_notes(row: dict[str, Any]) -> str:
    base = row.get("notes", "")
    tag = row.get("approved_coal_business_tag", "")
    if tag in {"non_core_or_review", "mixed_or_special_review"}:
        return base + " Tushare fallback resolves Eastmoney gap but keeps the company out of formal core-coal acceptance unless Research Agent approves inclusion."
    return base + " Tushare fallback resolves Eastmoney gap with structured main-business composition."


def _segment_row_complete(row: dict[str, Any]) -> bool:
    return (
        str(row.get("pit_usable", "")).lower() == "true"
        and bool(row.get("visible_date"))
        and bool(row.get("approved_coal_business_tag"))
        and bool(row.get("coal_revenue_ratio") or row.get("coal_profit_ratio"))
    )


def _complete_segment_evidence_by_code(evidence_csv: Path) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = {}
    for row in _read_csv(evidence_csv):
        if _segment_row_complete(row):
            result.setdefault(row["code"], []).append(row)
    for rows in result.values():
        rows.sort(key=lambda item: (item.get("visible_date", ""), item.get("report_period", "")))
    return result


def _latest_visible_evidence(rows: list[dict[str, str]], trade_date: str) -> dict[str, str] | None:
    candidates = [row for row in rows if row.get("visible_date", "") <= trade_date]
    if not candidates:
        return None
    return candidates[-1]


def _formal_coal_universe_include(tag: str, evidence: dict[str, Any]) -> bool:
    if tag in {"core_coal", "mixed_power_coal", "mixed_coal_chemical", "integrated_coal_power_transport"}:
        return True
    notes = evidence.get("notes", "")
    if "trade-oriented" in notes or "Non-coal" in notes:
        return False
    return tag == "mixed_or_special_review"


def _mainop_type_name(value: Any) -> str:
    return {"1": "industry", "2": "product", "3": "region"}.get(str(value), str(value or ""))


def _tushare_bz_type_name(value: Any) -> str:
    return {"I": "industry", "P": "product", "D": "region"}.get(str(value or ""), str(value or ""))


def _to_eastmoney_code(code: str) -> str:
    if code.endswith(".XSHG"):
        return "SH" + code[:6]
    if code.endswith(".XSHE"):
        return "SZ" + code[:6]
    if code.endswith(".SH"):
        return "SH" + code[:6]
    if code.endswith(".SZ"):
        return "SZ" + code[:6]
    return code


def _disclosures_by_code_period(disclosure_csv: Path) -> dict[tuple[str, str], dict[str, str]]:
    result = {}
    if not disclosure_csv.exists():
        return result
    for row in _read_csv(disclosure_csv):
        code = row.get("code", "")
        report_period = row.get("report_period", "")
        if code and report_period:
            result[(code, report_period)] = row
    return result


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


def _fetch_coal_disclosure_rows(pro: Any, codes: list[str], target_years: set[str], warnings: list[str]) -> list[dict[str, Any]]:
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
                    "review_status": "report_date_only_segment_evidence_required",
                    "notes": "Use this as report timing evidence only; business tag still requires segment exposure review.",
                }
            )
    return sorted(rows, key=lambda row: (row["code"], row["report_period"], row["report_type"]))


def _choose_notice_date(actual_date: str, ann_date: str, pre_date: str) -> tuple[str, str]:
    if actual_date:
        return actual_date, "actual_date"
    if ann_date:
        return ann_date, "ann_date"
    if pre_date:
        return pre_date, "pre_date"
    return "", ""


def _to_ts_code(code: str) -> str:
    if code.endswith(".XSHE"):
        return code[:6] + ".SZ"
    if code.endswith(".XSHG"):
        return code[:6] + ".SH"
    return code


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


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _to_float(value: Any) -> float | None:
    if value in {None, "", "nan", "NaN", "None"}:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric) or math.isinf(numeric):
        return None
    return numeric


def _fmt_float(value: Any) -> str:
    numeric = _to_float(value)
    if numeric is None:
        return ""
    return f"{numeric:.10g}"


def _ratio(numerator: float | int, denominator: float | int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _median(values: list[float]) -> float | None:
    return median(values) if values else None


def _quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * q))))
    return ordered[index]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-coal-data-audit")
    subparsers = parser.add_subparsers(dest="command", required=True)
    template_parser = subparsers.add_parser("manual-state-template")
    template_parser.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_external_state")
    nbs_template_parser = subparsers.add_parser("nbs-historical-template")
    nbs_template_parser.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_external_state")
    nbs_template_parser.add_argument("--start-year", type=int, default=2015)
    nbs_template_parser.add_argument("--end-year", type=int, default=2026)
    seed_parser = subparsers.add_parser("official-state-seed")
    seed_parser.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_external_state")
    merge_sources_parser = subparsers.add_parser("merge-state-sources")
    merge_sources_parser.add_argument("state_csvs", type=Path, nargs="+")
    merge_sources_parser.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_external_state")
    merge_parser = subparsers.add_parser("merge-manual-state")
    merge_parser.add_argument("base_state_csv", type=Path)
    merge_parser.add_argument("manual_state_csv", type=Path)
    merge_parser.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_external_state")
    tag_parser = subparsers.add_parser("audit-business-tags")
    tag_parser.add_argument("panel", type=Path)
    tag_parser.add_argument("--out-dir", type=Path, default=DEFAULT_MANIFEST_DIR / "coal_business_tag_audit")
    tag_template_parser = subparsers.add_parser("business-tag-template")
    tag_template_parser.add_argument("panel", type=Path)
    tag_template_parser.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_business_tags")
    disclosure_parser = subparsers.add_parser("collect-report-disclosures")
    disclosure_parser.add_argument("panel", type=Path)
    disclosure_parser.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_business_tags")
    disclosure_parser.add_argument("--credential-file", type=Path, default=DEFAULT_CREDENTIAL_FILE)
    disclosure_parser.add_argument("--token-env", default="TUSHARE_TOKEN")
    segment_template_parser = subparsers.add_parser("segment-evidence-template")
    segment_template_parser.add_argument("disclosure_csv", type=Path)
    segment_template_parser.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_business_tags")
    segment_audit_parser = subparsers.add_parser("audit-segment-evidence")
    segment_audit_parser.add_argument("evidence_csv", type=Path)
    segment_audit_parser.add_argument("--out-dir", type=Path, default=DEFAULT_MANIFEST_DIR / "coal_segment_evidence_audit")
    eastmoney_parser = subparsers.add_parser("collect-eastmoney-segments")
    eastmoney_parser.add_argument("panel", type=Path)
    eastmoney_parser.add_argument("disclosure_csv", type=Path)
    eastmoney_parser.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_business_tags")
    eastmoney_parser.add_argument("--request-timeout-seconds", type=float, default=15.0)
    eastmoney_parser.add_argument("--sleep-seconds", type=float, default=0.25)
    eastmoney_parser.add_argument("--limit", type=int)
    tushare_parser = subparsers.add_parser("collect-tushare-segments")
    tushare_parser.add_argument("panel", type=Path)
    tushare_parser.add_argument("disclosure_csv", type=Path)
    tushare_parser.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_business_tags")
    tushare_parser.add_argument("--codes", nargs="*", default=None)
    tushare_parser.add_argument("--sleep-seconds", type=float, default=0.25)
    merge_segment_parser = subparsers.add_parser("merge-segment-evidence")
    merge_segment_parser.add_argument("eastmoney_csv", type=Path)
    merge_segment_parser.add_argument("fallback_csv", type=Path)
    merge_segment_parser.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_business_tags")
    reviewed_panel_parser = subparsers.add_parser("build-reviewed-business-tag-panel")
    reviewed_panel_parser.add_argument("panel", type=Path)
    reviewed_panel_parser.add_argument("evidence_csv", type=Path)
    reviewed_panel_parser.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_business_tags")
    capex_parser = subparsers.add_parser("audit-capex-fcf")
    capex_parser.add_argument("panel", type=Path)
    capex_parser.add_argument("--out-dir", type=Path, default=DEFAULT_MANIFEST_DIR / "coal_capex_fcf_audit")
    capex_policy_parser = subparsers.add_parser("capex-policy-panel")
    capex_policy_parser.add_argument("panel", type=Path)
    capex_policy_parser.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_pit_panel_capex_policy")
    args = parser.parse_args(argv)
    if args.command == "manual-state-template":
        print(write_coal_manual_state_template(args.out_dir))
        return 0
    if args.command == "nbs-historical-template":
        print(write_nbs_historical_state_template(args.out_dir, args.start_year, args.end_year))
        return 0
    if args.command == "official-state-seed":
        print(write_coal_official_state_seed(args.out_dir))
        return 0
    if args.command == "merge-state-sources":
        print(merge_coal_state_sources(args.out_dir, *args.state_csvs))
        return 0
    if args.command == "merge-manual-state":
        print(merge_coal_manual_state(args.base_state_csv, args.manual_state_csv, args.out_dir))
        return 0
    if args.command == "audit-business-tags":
        print(audit_coal_business_tags(args.panel, args.out_dir))
        return 0
    if args.command == "business-tag-template":
        print(write_coal_business_tag_visible_date_template(args.panel, args.out_dir))
        return 0
    if args.command == "collect-report-disclosures":
        print(collect_coal_report_disclosure_dates(args.panel, args.out_dir, args.credential_file, args.token_env))
        return 0
    if args.command == "segment-evidence-template":
        print(write_coal_segment_evidence_template(args.disclosure_csv, args.out_dir))
        return 0
    if args.command == "audit-segment-evidence":
        print(audit_coal_segment_evidence(args.evidence_csv, args.out_dir))
        return 0
    if args.command == "collect-eastmoney-segments":
        print(
            collect_eastmoney_coal_segment_evidence(
                args.panel,
                args.disclosure_csv,
                args.out_dir,
                args.request_timeout_seconds,
                args.sleep_seconds,
                args.limit,
            )
        )
        return 0
    if args.command == "collect-tushare-segments":
        print(
            collect_tushare_coal_segment_evidence(
                args.panel,
                args.disclosure_csv,
                args.out_dir,
                args.codes,
                args.sleep_seconds,
            )
        )
        return 0
    if args.command == "merge-segment-evidence":
        print(merge_coal_segment_evidence_sources(args.eastmoney_csv, args.fallback_csv, args.out_dir))
        return 0
    if args.command == "build-reviewed-business-tag-panel":
        print(build_coal_reviewed_business_tag_panel(args.panel, args.evidence_csv, args.out_dir))
        return 0
    if args.command == "audit-capex-fcf":
        print(audit_coal_capex_fcf(args.panel, args.out_dir))
        return 0
    if args.command == "capex-policy-panel":
        print(build_coal_capex_policy_panel(args.panel, args.out_dir))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
