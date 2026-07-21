from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.paths import DEFAULT_PROCESSED_DIR


REPAIR_DATE = "2021-07-01"
DEFAULT_SOURCE_PANEL = DEFAULT_PROCESSED_DIR / "similar_sector_pit_panel_v55" / "gas_water_operators" / "panel.csv"
DEFAULT_CURRENT_PANEL = DEFAULT_PROCESSED_DIR / "gas_water_true_operating_state_panel_v59" / "panel_with_true_operating_state.csv"
DEFAULT_TRUE_EVIDENCE = Path("research_reports") / "gas_water_true_operating_state_v59_history_2020_2025" / "gas_water_true_operating_state_candidates.csv"
DEFAULT_SEGMENT_EVIDENCE = DEFAULT_PROCESSED_DIR / "gas_water_operating_evidence_v57" / "gas_water_segment_business_evidence_eastmoney.csv"
DEFAULT_OUT_DIR = DEFAULT_PROCESSED_DIR / "gas_water_2021_07_pit_repair_v59b"

PANEL_EXTRA_FIELDS = [
    "ocf_positive_guard",
    "dividend_positive_guard",
    "capex_burden_safe",
    "cash_collection_quality_safe",
    "debt_pressure_safe",
    "interest_coverage_safe",
    "low_price_to_book_safe",
    "pe_ratio_safe",
    "gas_water_data_quality_source",
    "gas_water_report_period",
    "gas_water_visible_date",
    "gas_revenue_share",
    "water_revenue_share",
    "operator_revenue_share",
    "project_engineering_revenue_share",
    "non_operator_revenue_share",
    "approved_gas_water_business_tag",
    "business_purity_gate",
    "business_purity_review_status",
]

TRUE_STATE_FIELDS = [
    "true_operating_state_available",
    "true_operating_report_period",
    "true_operating_visible_date",
    "true_operating_title",
    "true_operating_pdf_url",
    "true_operating_original_announcement_checked",
    "true_operating_review_status",
    "true_gas_pass_through_present",
    "true_gas_pass_through_term_count",
    "true_gas_pass_through_density_per_10k",
    "true_connection_install_present",
    "true_connection_install_term_count",
    "true_connection_install_density_per_10k",
    "true_water_tariff_present",
    "true_water_tariff_term_count",
    "true_water_tariff_density_per_10k",
    "true_receivables_collection_present",
    "true_receivables_collection_term_count",
    "true_receivables_collection_density_per_10k",
    "true_financing_debt_present",
    "true_financing_debt_term_count",
    "true_financing_debt_density_per_10k",
    "true_operating_state_notes",
]

AUDIT_FIELDS = [
    "trade_date",
    "code",
    "source_panel_present",
    "current_panel_present",
    "repair_decision",
    "approved_for_repair",
    "visible_date",
    "report_period",
    "evidence_source",
    "gas_revenue_share",
    "water_revenue_share",
    "operator_revenue_share",
    "project_engineering_revenue_share",
    "approved_gas_water_business_tag",
    "rationale",
]


REPAIR_DECISIONS: dict[str, dict[str, Any]] = {
    "600008.XSHG": {
        "approved": True,
        "report_period": "2020-12-31",
        "visible_date": "2021-04-07",
        "gas_revenue_share": 0.0,
        "water_revenue_share": 0.4630,
        "operator_revenue_share": 0.4630,
        "project_engineering_revenue_share": 0.2087,
        "approved_gas_water_business_tag": "broad_water_environment_operator",
        "evidence_source": "cninfo_2020_annual_report_segment_table_manual_review",
        "rationale": "2020 annual report disclosed water/wastewater/water-environment concession operations before 2021-07-01. Include only as broad water/environment operator with contamination warning.",
    },
    "600461.XSHG": {
        "approved": True,
        "report_period": "2020-12-31",
        "visible_date": "2021-04-22",
        "gas_revenue_share": 0.2114,
        "water_revenue_share": 0.2971,
        "operator_revenue_share": 0.5085,
        "project_engineering_revenue_share": 0.4855,
        "approved_gas_water_business_tag": "mixed_utility_operator_project_contamination_warning",
        "evidence_source": "cninfo_2020_annual_report_segment_table_manual_review",
        "rationale": "2020 annual report operator revenue from water/wastewater/gas exceeded 50% before 2021-07-01, but project revenue was high; include as PIT repair with explicit contamination warning.",
    },
    "600635.XSHG": {
        "approved": True,
        "report_period": "2020-12-31",
        "visible_date": "2021-03-31",
        "gas_revenue_share": 0.8450,
        "water_revenue_share": 0.0701,
        "operator_revenue_share": 0.9151,
        "project_engineering_revenue_share": 0.0444,
        "approved_gas_water_business_tag": "core_gas_operator",
        "evidence_source": "cninfo_2020_annual_report_segment_table_manual_review",
        "rationale": "2020 annual report disclosed gas sales and wastewater operations above 90% of revenue before 2021-07-01.",
    },
    "601139.XSHG": {
        "approved": True,
        "report_period": "2020-12-31",
        "visible_date": "2021-04-28",
        "gas_revenue_share": 0.5480,
        "water_revenue_share": 0.0,
        "operator_revenue_share": 0.5480,
        "project_engineering_revenue_share": 0.1754,
        "approved_gas_water_business_tag": "core_gas_operator",
        "evidence_source": "cninfo_2020_annual_report_segment_table_manual_review",
        "rationale": "2020 annual report disclosed pipeline gas revenue above 50% of revenue before 2021-07-01; broader city-gas segment is higher but pipeline-gas-only is used conservatively.",
    },
    "000421.XSHE": {"approved": False, "rationale": "Latest visible 2020 annual evidence before 2021-07-01 showed property development as largest business and operator share below 50%."},
    "000605.XSHE": {"approved": False, "rationale": "Latest visible 2020 annual evidence before 2021-07-01 showed engineering/heat/non-water operations dominated and operator share below 50%."},
    "000685.XSHE": {"approved": False, "rationale": "No reviewed segment evidence available before 2021-07-01; later reports show water operations below 50% with engineering/solid-waste contamination."},
    "600642.XSHG": {"approved": False, "rationale": "Latest visible 2020 annual evidence before 2021-07-01 was dominated by coal/power/oil-gas pipeline exposure, not gas/water utility operations."},
    "603393.XSHG": {"approved": False, "rationale": "Latest visible 2020 annual evidence before 2021-07-01 was dominated by coalbed-gas upstream exposure; exclude from regulated gas/water operator universe."},
    "603689.XSHG": {"approved": False, "rationale": "Latest visible 2020 annual evidence before 2021-07-01 was dominated by long-distance pipeline/CNG-LNG exposure; exclude from city gas/water operator universe."},
    "603706.XSHG": {"approved": False, "rationale": "Latest visible 2020 annual evidence before 2021-07-01 was dominated by heat/thermal operations; gas operations were below 50%."},
}


def repair_gas_water_2021_07_pit_coverage(
    source_panel: Path = DEFAULT_SOURCE_PANEL,
    current_panel: Path = DEFAULT_CURRENT_PANEL,
    true_evidence_csv: Path = DEFAULT_TRUE_EVIDENCE,
    segment_evidence_csv: Path = DEFAULT_SEGMENT_EVIDENCE,
    out_dir: Path = DEFAULT_OUT_DIR,
) -> Path:
    source_rows = read_csv_rows(source_panel)
    current_rows = read_csv_rows(current_panel)
    true_rows = read_csv_rows(true_evidence_csv)
    segment_rows = read_csv_rows(segment_evidence_csv)

    source_by_code = {row["code"]: row for row in source_rows if row.get("trade_date") == REPAIR_DATE and row.get("code")}
    current_codes = {row["code"] for row in current_rows if row.get("trade_date") == REPAIR_DATE and row.get("code")}
    missing_codes = sorted(set(source_by_code) - current_codes)
    true_by_code = _latest_true_evidence_by_code(true_rows, REPAIR_DATE)
    segment_by_code = _latest_segment_evidence_by_code(segment_rows, REPAIR_DATE)

    repaired_rows = list(current_rows)
    audit_rows: list[dict[str, Any]] = []
    added_codes: list[str] = []
    for code in missing_codes:
        decision = REPAIR_DECISIONS.get(code, {"approved": False, "rationale": "No explicit repair decision."})
        approved = bool(decision.get("approved"))
        audit_rows.append(_audit_row(code, source_by_code, current_codes, decision, segment_by_code))
        if not approved:
            continue
        row = dict(source_by_code[code])
        _apply_factor_safety_fields(row)
        _apply_manual_business_fields(row, decision)
        _apply_true_state_fields(row, true_by_code.get(code))
        repaired_rows.append(row)
        added_codes.append(code)

    repaired_rows.sort(key=lambda item: (item.get("trade_date", ""), item.get("code", "")))
    out_dir.mkdir(parents=True, exist_ok=True)
    repaired_panel = out_dir / "panel_with_true_operating_state_repaired_2021_07.csv"
    audit_csv = out_dir / "repair_audit_2021_07.csv"
    fieldnames = _fieldnames(current_rows, source_rows)
    write_csv_rows(repaired_panel, fieldnames, repaired_rows)
    write_csv_rows(audit_csv, AUDIT_FIELDS, audit_rows)
    coverage = _coverage(repaired_rows)
    write_json_file(
        out_dir / "repair_manifest_2021_07.json",
        {
            "dataset": "gas_water_v59b_2021_07_pit_coverage_repair",
            "repair_date": REPAIR_DATE,
            "source_panel": str(source_panel),
            "current_panel": str(current_panel),
            "true_evidence_csv": str(true_evidence_csv),
            "segment_evidence_csv": str(segment_evidence_csv),
            "output_panel": str(repaired_panel),
            "audit_csv": str(audit_csv),
            "missing_from_current_panel": missing_codes,
            "added_codes": added_codes,
            "excluded_codes": [row["code"] for row in audit_rows if row["approved_for_repair"] == 0],
            "coverage_before": {
                "repair_date_count": len(current_codes),
            },
            "coverage_after": coverage,
            "pit_policy": "Only evidence with visible_date <= 2021-07-01 is allowed. 2021 semiannual reports are not used.",
            "status": "coverage_contract_repaired" if coverage.get(REPAIR_DATE, {}).get("row_count", 0) >= 32 else "coverage_contract_still_blocked",
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return repaired_panel


def _latest_true_evidence_by_code(rows: list[dict[str, str]], trade_date: str) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        code = row.get("code", "")
        visible = row.get("visible_date", "")
        if not code or not visible or visible > trade_date or row.get("original_announcement_checked") != "true":
            continue
        if code not in result or (visible, row.get("report_period", "")) > (result[code].get("visible_date", ""), result[code].get("report_period", "")):
            result[code] = row
    return result


def _latest_segment_evidence_by_code(rows: list[dict[str, str]], trade_date: str) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        code = row.get("code", "")
        visible = row.get("visible_date", "")
        if not code or not visible or visible > trade_date:
            continue
        if code not in result or (visible, row.get("report_period", "")) > (result[code].get("visible_date", ""), result[code].get("report_period", "")):
            result[code] = row
    return result


def _apply_factor_safety_fields(row: dict[str, Any]) -> None:
    row["ocf_positive_guard"] = 1 if _to_float(row.get("operating_cash_flow_yield")) and _to_float(row.get("operating_cash_flow_yield")) > 0 else 0
    row["dividend_positive_guard"] = 1 if _to_float(row.get("dividend_yield")) and _to_float(row.get("dividend_yield")) > 0 else 0
    row["capex_burden_safe"] = row.get("capex_burden") if _to_float(row.get("capex_burden")) and _to_float(row.get("capex_burden")) >= 0 else 999
    row["cash_collection_quality_safe"] = row.get("cash_collection_quality") or ""
    row["debt_pressure_safe"] = row.get("asset_liability_ratio") or ""
    row["interest_coverage_safe"] = row.get("interest_coverage") or ""
    row["low_price_to_book_safe"] = row.get("low_price_to_book") or ""
    row["pe_ratio_safe"] = row.get("pe_ratio") or ""


def _apply_manual_business_fields(row: dict[str, Any], decision: dict[str, Any]) -> None:
    row["gas_water_data_quality_source"] = "v59b_2021_07_pit_repair_manual_annual_report_review"
    row["gas_water_report_period"] = decision.get("report_period", "")
    row["gas_water_visible_date"] = decision.get("visible_date", "")
    for field in ["gas_revenue_share", "water_revenue_share", "operator_revenue_share", "project_engineering_revenue_share"]:
        row[field] = decision.get(field, "")
    operator_share = _to_float(decision.get("operator_revenue_share")) or 0.0
    row["non_operator_revenue_share"] = max(0.0, 1.0 - operator_share)
    row["approved_gas_water_business_tag"] = decision.get("approved_gas_water_business_tag", "")
    row["business_purity_gate"] = "passed_pit_repair_2021_07"
    row["business_purity_review_status"] = "manual_annual_report_reviewed_for_2021_07_pit_repair"


def _apply_true_state_fields(row: dict[str, Any], evidence: dict[str, str] | None) -> None:
    if not evidence:
        for field in TRUE_STATE_FIELDS:
            row[field] = ""
        row["true_operating_state_available"] = 0
        row["true_operating_state_notes"] = "No CNINFO true operating-state text evidence visible before repair date."
        return
    row["true_operating_state_available"] = 1
    row["true_operating_report_period"] = evidence.get("report_period", "")
    row["true_operating_visible_date"] = evidence.get("visible_date", "")
    row["true_operating_title"] = evidence.get("title", "")
    row["true_operating_pdf_url"] = evidence.get("pdf_url", "")
    row["true_operating_original_announcement_checked"] = evidence.get("original_announcement_checked", "")
    row["true_operating_review_status"] = evidence.get("review_status", "")
    for group in ["gas_pass_through", "connection_install", "water_tariff", "receivables_collection", "financing_debt"]:
        row[f"true_{group}_present"] = 1 if group in str(evidence.get("hit_groups") or "").split("|") else 0
        row[f"true_{group}_term_count"] = evidence.get(f"{group}_term_count", "")
        row[f"true_{group}_density_per_10k"] = evidence.get(f"{group}_density_per_10k", "")
    row["true_operating_state_notes"] = "visible_2020_annual_cninfo_pdf_text_evidence"


def _audit_row(
    code: str,
    source_by_code: dict[str, dict[str, str]],
    current_codes: set[str],
    decision: dict[str, Any],
    segment_by_code: dict[str, dict[str, str]],
) -> dict[str, Any]:
    segment = segment_by_code.get(code, {})
    return {
        "trade_date": REPAIR_DATE,
        "code": code,
        "source_panel_present": int(code in source_by_code),
        "current_panel_present": int(code in current_codes),
        "repair_decision": "add" if decision.get("approved") else "exclude",
        "approved_for_repair": int(bool(decision.get("approved"))),
        "visible_date": decision.get("visible_date") or segment.get("visible_date", ""),
        "report_period": decision.get("report_period") or segment.get("report_period", ""),
        "evidence_source": decision.get("evidence_source") or segment.get("source_name", ""),
        "gas_revenue_share": decision.get("gas_revenue_share", segment.get("gas_revenue_share", "")),
        "water_revenue_share": decision.get("water_revenue_share", segment.get("water_revenue_share", "")),
        "operator_revenue_share": decision.get("operator_revenue_share", segment.get("operator_revenue_share", "")),
        "project_engineering_revenue_share": decision.get("project_engineering_revenue_share", segment.get("project_engineering_revenue_share", "")),
        "approved_gas_water_business_tag": decision.get("approved_gas_water_business_tag", segment.get("approved_gas_water_business_tag", "")),
        "rationale": decision.get("rationale", ""),
    }


def _coverage(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        day = str(row.get("trade_date") or "")
        if not day:
            continue
        result.setdefault(day, {"row_count": 0})
        result[day]["row_count"] += 1
    max_count = max((item["row_count"] for item in result.values()), default=0)
    required = int(max_count * 0.8)
    if max_count and required < max_count * 0.8:
        required += 1
    for item in result.values():
        item["max_date_coverage"] = max_count
        item["required_80pct_count"] = required
        item["coverage_passed"] = item["row_count"] >= required
    return result


def _fieldnames(*row_groups: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for rows in row_groups:
        for row in rows[:1]:
            for key in row:
                if key not in names:
                    names.append(key)
    for field in [*PANEL_EXTRA_FIELDS, *TRUE_STATE_FIELDS]:
        if field not in names:
            names.append(field)
    return names


def _to_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None
