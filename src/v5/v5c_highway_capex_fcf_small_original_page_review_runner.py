from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5c_highway_capex_fcf_small_original_page_review") / "current"
FREEZE_DIR = Path("v5c_highway_ocf_risk_cap_rule_freeze") / "current"
CAPEX_DIR = Path("v5c_infra_capex_original_statement_extraction") / "current"
SIDECAR_DIR = Path("v5c_sidecar_observation_enhancement") / "current"
CYCLE_DIR = Path("v5c_cycle_sector_data_gate_queue") / "current"
RISK_CAP_DIR = Path("v5c_highway_ocf_risk_cap_v1_limited_engineering") / "current"

BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"
TASK = "v5c_highway_capex_fcf_small_original_page_review"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_v5c_highway_capex_fcf_small_original_page_review(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    blockers = _missing_inputs(root)
    if blockers:
        summary = _summary("blocked_missing_required_inputs", "blocked_missing_required_inputs", blockers)
        _write_json(out / "v5c_highway_capex_fcf_review_summary.json", summary)
        _write_csv(out / "v5c_highway_capex_fcf_blockers.csv", blockers)
        return summary

    review_queue = _read_csv(root / FREEZE_DIR / "v5c_highway_capex_fcf_original_page_review_queue.csv")
    strict_panel = _read_csv(root / CAPEX_DIR / "v5c_infra_capex_strict_panel.csv")
    capex_blockers = _read_csv(root / CAPEX_DIR / "v5c_infra_capex_blockers.csv")
    sidecar_queue = _read_csv(root / SIDECAR_DIR / "v5c_sidecar_observation_enhancement_queue.csv")
    cycle_queue = _read_csv(root / CYCLE_DIR / "v5c_cycle_sector_data_gate_queue.csv")
    risk_cap_summary = _optional_json(root / RISK_CAP_DIR / "v5c_highway_ocf_risk_cap_limited_summary.json")

    input_queue = _copy_input_queue(review_queue)
    review_rows = _review_original_pages(root, review_queue, strict_panel)
    pit_panel = _pit_gate_panel(review_rows)
    coverage = _coverage_audit(strict_panel, review_rows)
    sidecar = _sidecar_refresh(sidecar_queue)
    cycle = _cycle_refresh(cycle_queue)
    decision = _pm_gate_decision(review_rows, coverage, sidecar, cycle, risk_cap_summary)
    next_queue = _next_queue(decision)
    blockers_out = _blockers(review_rows, capex_blockers)

    _write_csv(out / "v5c_highway_capex_fcf_input_queue.csv", input_queue)
    _write_csv(out / "v5c_highway_capex_fcf_original_page_review.csv", review_rows)
    _write_csv(out / "v5c_highway_capex_fcf_pit_data_gate_panel.csv", pit_panel)
    _write_csv(out / "v5c_highway_capex_fcf_field_coverage_audit.csv", coverage)
    _write_csv(out / "v5c_sidecar_observation_refresh.csv", sidecar)
    _write_csv(out / "v5c_cycle_sector_pit_state_data_gate_refresh.csv", cycle)
    _write_csv(out / "v5c_highway_capex_fcf_pm_gate_decision.csv", decision)
    _write_csv(out / "v5c_highway_capex_fcf_next_queue.csv", next_queue)
    _write_csv(out / "v5c_highway_capex_fcf_blockers.csv", blockers_out)
    (out / "v5c_highway_capex_fcf_review_report.md").write_text(
        _report(review_rows, coverage, sidecar, cycle, decision),
        encoding="utf-8",
    )
    (out / "v5c_highway_capex_fcf_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    summary = _summary(
        "completed_data_gate_only",
        decision[0]["pm_gate_decision"],
        blockers_out,
        review_queue_count=len(review_queue),
        p0_review_count=sum(1 for row in review_rows if row["priority"] == "P0_sample_review"),
        source_missing_count=sum(1 for row in review_rows if row["review_status"] == "source_missing_not_model_ready"),
        pit_clean_available_count=sum(1 for row in pit_panel if str(row["data_gate_status"]).startswith("pit_clean_")),
        sidecar_rows=len(sidecar),
        cycle_rows=len(cycle),
    )
    _write_json(out / "v5c_highway_capex_fcf_review_summary.json", summary)
    return summary


def _copy_input_queue(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        out.append(
            {
                **row,
                "review_scope": "small_original_page_data_gate_only",
                "model_use_allowed": False,
                "accepted": False,
            }
        )
    return out


def _review_original_pages(root: Path, queue: list[dict[str, str]], strict_panel: list[dict[str, str]]) -> list[dict[str, Any]]:
    panel_index = _panel_index(strict_panel)
    rows: list[dict[str, Any]] = []
    for i, row in enumerate(queue, start=1):
        panel_row = _find_panel_row(panel_index, row)
        evidence = _pdf_evidence(root, row)
        status = _review_status(row, panel_row, evidence)
        visible_date = panel_row.get("capex_original_visible_date") or panel_row.get("cashflow_factor_visible_date", "") if panel_row else ""
        first_date = row.get("first_affected_trade_date", "")
        rows.append(
            {
                "review_id": f"highway_capex_fcf_review_{i:03d}",
                "priority": row.get("priority", ""),
                "code": row.get("code", ""),
                "sector_id": row.get("sector_id", ""),
                "report_period": row.get("report_period", ""),
                "first_affected_trade_date": first_date,
                "source_pdf": row.get("capex_source_pdf", ""),
                "source_page_number": row.get("capex_source_page_number", ""),
                "pdf_exists": evidence["pdf_exists"],
                "searched_pages": evidence["searched_pages"],
                "text_extract_status": evidence["text_extract_status"],
                "text_char_count": evidence["text_char_count"],
                "cash_flow_table_keyword_hit": evidence["cash_flow_table_keyword_hit"],
                "cfo_keyword_hit": evidence["cfo_keyword_hit"],
                "capex_keyword_hit": evidence["capex_keyword_hit"],
                "unit_keyword_hit": evidence["unit_keyword_hit"],
                "source_unit": panel_row.get("capex_source_unit", "") if panel_row else "",
                "capex_original_visible_date": visible_date,
                "pit_visible_date_pass": _pit_pass(visible_date, first_date),
                "strict_panel_status": panel_row.get("capex_fcf_status", "") if panel_row else "missing_strict_panel_row",
                "operating_cash_flow_net_original": panel_row.get("operating_cash_flow_net_original", "") if panel_row else "",
                "capex_cash_paid_original": panel_row.get("capex_cash_paid_original", "") if panel_row else "",
                "free_cash_flow_yield": panel_row.get("free_cash_flow_yield", "") if panel_row else "",
                "capex_burden": panel_row.get("capex_burden", "") if panel_row else "",
                "review_status": status,
                "model_use_allowed": False,
                "enters_v1_model": False,
                "accepted": False,
                "review_note": _review_note(status, evidence, panel_row),
            }
        )
    return rows


def _panel_index(rows: list[dict[str, str]]) -> dict[tuple[str, str], list[dict[str, str]]]:
    out: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        key = (row.get("code", ""), row.get("cashflow_report_period", ""))
        out.setdefault(key, []).append(row)
    return out


def _find_panel_row(index: dict[tuple[str, str], list[dict[str, str]]], queue_row: dict[str, str]) -> dict[str, str] | None:
    candidates = index.get((queue_row.get("code", ""), queue_row.get("report_period", "")), [])
    first = queue_row.get("first_affected_trade_date", "")
    if first:
        exact = [row for row in candidates if row.get("trade_date") == first]
        if exact:
            return exact[0]
    return candidates[0] if candidates else None


def _pdf_evidence(root: Path, row: dict[str, str]) -> dict[str, Any]:
    rel_pdf = row.get("capex_source_pdf", "")
    if not rel_pdf:
        return _empty_evidence("source_pdf_missing")
    pdf_path = root / rel_pdf
    if not pdf_path.exists():
        return _empty_evidence("source_pdf_missing")
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_path))
        page_number = _to_int(row.get("capex_source_page_number"))
        pages = _page_window(page_number, len(reader.pages))
        text_parts = []
        for page_idx in pages:
            text_parts.append(reader.pages[page_idx - 1].extract_text() or "")
        text = "\n".join(text_parts)
        hits = _keyword_hits(text)
        return {
            "pdf_exists": True,
            "searched_pages": ";".join(str(page) for page in pages),
            "text_extract_status": "text_extracted" if text else "text_empty",
            "text_char_count": len(text),
            **hits,
        }
    except Exception as exc:  # pragma: no cover - defensive against malformed PDFs.
        evidence = _empty_evidence("text_extract_error")
        evidence["pdf_exists"] = True
        evidence["text_extract_error"] = str(exc)[:180]
        return evidence


def _empty_evidence(status: str) -> dict[str, Any]:
    return {
        "pdf_exists": False,
        "searched_pages": "",
        "text_extract_status": status,
        "text_char_count": 0,
        "cash_flow_table_keyword_hit": False,
        "cfo_keyword_hit": False,
        "capex_keyword_hit": False,
        "unit_keyword_hit": False,
    }


def _keyword_hits(text: str) -> dict[str, bool]:
    return {
        "cash_flow_table_keyword_hit": "现金流量表" in text,
        "cfo_keyword_hit": "经营活动产生的现金流量净额" in text or "经营活动现金流量净额" in text,
        "capex_keyword_hit": "购建固定资产" in text or "其他长期资产支付的现金" in text,
        "unit_keyword_hit": "单位：元" in text or "单位:元" in text or "单位：人民币元" in text,
    }


def _page_window(page_number: int | None, page_count: int) -> list[int]:
    if not page_number or page_number < 1:
        return [1] if page_count else []
    start = max(1, page_number - 1)
    end = min(page_count, page_number + 1)
    return list(range(start, end + 1))


def _review_status(row: dict[str, str], panel_row: dict[str, str] | None, evidence: dict[str, Any]) -> str:
    if not evidence["pdf_exists"]:
        return "source_missing_not_model_ready"
    if panel_row is None:
        return "needs_review_no_strict_panel_row"
    if evidence["text_extract_status"] != "text_extracted":
        return "needs_manual_review_text_unavailable"
    if not evidence["cash_flow_table_keyword_hit"] or not evidence["unit_keyword_hit"]:
        return "needs_manual_review_keyword_gap"
    if _pit_pass(panel_row.get("capex_original_visible_date") or panel_row.get("cashflow_factor_visible_date", ""), row.get("first_affected_trade_date", "")) is False:
        return "needs_review_pit_visible_date_issue"
    if panel_row.get("capex_fcf_status") == "pass_pit_original_statement_extracted" and _has_number(panel_row.get("free_cash_flow_yield")) and _has_number(panel_row.get("capex_burden")):
        return "reviewed_pit_clean_capex_fcf_available_not_model_input"
    if (
        panel_row.get("capex_fcf_status") == "pass_pit_original_statement_extracted"
        and _has_number(panel_row.get("operating_cash_flow_net_original"))
        and _has_number(panel_row.get("capex_cash_paid_original"))
        and _has_number(panel_row.get("capex_burden"))
    ):
        return "reviewed_pit_clean_capex_available_fcf_incomplete_not_model_input"
    return "reviewed_source_present_keep_blocked"


def _review_note(status: str, evidence: dict[str, Any], panel_row: dict[str, str] | None) -> str:
    if status == "reviewed_pit_clean_capex_fcf_available_not_model_input":
        return "original text and PIT capex/FCF fields are available, but capex/FCF remain excluded from v1"
    if status == "reviewed_pit_clean_capex_available_fcf_incomplete_not_model_input":
        return "original text and PIT capex burden are available; FCF yield remains incomplete and excluded from v1"
    if status == "reviewed_source_present_keep_blocked":
        panel_status = panel_row.get("capex_fcf_status", "") if panel_row else ""
        return f"source text present; strict panel status={panel_status}; keep as data gate only"
    if status == "source_missing_not_model_ready":
        return "PDF source missing; retry source search or provide report before formal use"
    if status == "needs_manual_review_keyword_gap":
        return "PDF text layer exists but cash-flow/unit keywords are incomplete on searched pages"
    return "manual review required before any formal capex/FCF use"


def _pit_gate_panel(review_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in review_rows:
        if row["review_status"] == "reviewed_pit_clean_capex_fcf_available_not_model_input":
            gate = "pit_clean_capex_fcf_available_reviewed"
        elif row["review_status"] == "reviewed_pit_clean_capex_available_fcf_incomplete_not_model_input":
            gate = "pit_clean_capex_available_fcf_incomplete_reviewed"
        elif row["review_status"] == "reviewed_source_present_keep_blocked":
            gate = "source_reviewed_but_not_model_ready"
        elif row["review_status"] == "source_missing_not_model_ready":
            gate = "source_missing_not_model_ready"
        else:
            gate = "manual_review_required_not_model_ready"
        out.append(
            {
                "code": row["code"],
                "sector_id": row["sector_id"],
                "report_period": row["report_period"],
                "first_affected_trade_date": row["first_affected_trade_date"],
                "capex_original_visible_date": row["capex_original_visible_date"],
                "pit_visible_date_pass": row["pit_visible_date_pass"],
                "operating_cash_flow_net_original": row["operating_cash_flow_net_original"],
                "capex_cash_paid_original": row["capex_cash_paid_original"],
                "free_cash_flow_yield": row["free_cash_flow_yield"],
                "capex_burden": row["capex_burden"],
                "source_unit": row["source_unit"],
                "source_pdf": row["source_pdf"],
                "source_page_number": row["source_page_number"],
                "data_gate_status": gate,
                "model_use_allowed": False,
                "enters_v1_model": False,
                "accepted": False,
            }
        )
    return out


def _coverage_audit(strict_panel: list[dict[str, str]], review_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    highway = [row for row in strict_panel if row.get("sector_id") == "highway_infrastructure"]
    reviewed_p0 = [row for row in review_rows if row["priority"] == "P0_sample_review"]
    return [
        _coverage_row("strict_panel_highway_rows", len(highway), len(highway), 1.0, "reference"),
        _coverage_row("strict_panel_fcf_yield_nonmissing", sum(1 for row in highway if _has_number(row.get("free_cash_flow_yield"))), len(highway), None, "data_gate_only"),
        _coverage_row("strict_panel_capex_burden_nonmissing", sum(1 for row in highway if _has_number(row.get("capex_burden"))), len(highway), None, "data_gate_only"),
        _coverage_row("strict_panel_pass_original_extracted", sum(1 for row in highway if row.get("capex_fcf_status") == "pass_pit_original_statement_extracted"), len(highway), None, "data_gate_only"),
        _coverage_row("small_review_queue_rows", len(review_rows), len(review_rows), 1.0, "review_scope"),
        _coverage_row("p0_review_rows", len(reviewed_p0), len(review_rows), None, "review_scope"),
        _coverage_row("p0_pdf_source_exists", sum(1 for row in reviewed_p0 if row["pdf_exists"]), len(reviewed_p0), None, "data_gate_only"),
        _coverage_row("p0_pit_clean_capex_available_reviewed", sum(1 for row in reviewed_p0 if row["review_status"].startswith("reviewed_pit_clean_capex")), len(reviewed_p0), None, "data_gate_only"),
        _coverage_row("p0_pit_clean_capex_fcf_available_reviewed", sum(1 for row in reviewed_p0 if row["review_status"] == "reviewed_pit_clean_capex_fcf_available_not_model_input"), len(reviewed_p0), None, "data_gate_only"),
    ]


def _coverage_row(metric: str, numerator: int, denominator: int, value: float | None, status: str) -> dict[str, Any]:
    ratio = value if value is not None else (numerator / denominator if denominator else 0.0)
    return {
        "metric": metric,
        "numerator": numerator,
        "denominator": denominator,
        "coverage_ratio": ratio,
        "status": status,
        "model_use_allowed": False,
    }


def _sidecar_refresh(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [
        {
            "sidecar_id": row.get("sidecar_id", ""),
            "sector_id": row.get("sector_id", ""),
            "prior_status": row.get("status", ""),
            "updated_status": "continue_sidecar_observation_only",
            "allowed_fields": row.get("allowed_fields", ""),
            "allowed_action": row.get("allowed_action", ""),
            "blocked_action": row.get("blocked_action", ""),
            "limited_engineering_allowed": False,
            "backtest_allowed": False,
            "accepted": False,
        }
        for row in rows
    ]


def _cycle_refresh(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [
        {
            "sector_id": row.get("sector_id", ""),
            "prior_status": row.get("status", ""),
            "updated_status": "continue_pit_state_data_gate_only_no_backtest",
            "required_state_data": row.get("required_state_data", ""),
            "blocked_action": row.get("blocked_action", ""),
            "backtest_allowed": False,
            "accepted": False,
        }
        for row in rows
    ]


def _pm_gate_decision(
    review_rows: list[dict[str, Any]],
    coverage: list[dict[str, Any]],
    sidecar: list[dict[str, Any]],
    cycle: list[dict[str, Any]],
    risk_cap_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    source_missing = sum(1 for row in review_rows if row["review_status"] == "source_missing_not_model_ready")
    pit_clean = sum(1 for row in review_rows if str(row["review_status"]).startswith("reviewed_pit_clean_"))
    return [
        {
            "pm_gate_decision": "capex_fcf_small_original_page_review_completed_data_gate_only",
            "highway_capex_fcf_model_use_allowed": False,
            "highway_capex_fcf_enters_v1": False,
            "risk_cap_v1_gate_reference": risk_cap_summary.get("pm_gate_decision", "not_read"),
            "risk_cap_v1_forward_observation": False,
            "small_review_rows": len(review_rows),
            "pit_clean_available_reviewed_rows": pit_clean,
            "source_missing_rows": source_missing,
            "sidecar_decision": "continue_sidecar_observation_only",
            "sidecar_rows": len(sidecar),
            "cycle_decision": "continue_pit_state_data_gate_only_no_backtest",
            "cycle_rows": len(cycle),
            "v57f_core_modified": False,
            "v5f_primary_modified": False,
            "backtest_started": False,
            "threshold_scan_used": False,
            "accepted": False,
            "live_trading_approved": False,
        }
    ]


def _next_queue(decision: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "priority": "P0",
            "task_id": "keep_internal_subsleeve_mom12_70_30_as_v5f_primary",
            "status": "ready",
            "allowed_action": "continue_forward_paper_tracking",
        },
        {
            "priority": "P1",
            "task_id": "retry_missing_highway_source_reports_only_if_needed",
            "status": "optional",
            "allowed_action": "data_gate_source_repair_only_no_model",
        },
        {
            "priority": "S1",
            "task_id": "v5c_gas_water_telecom_sidecar_observation_refresh",
            "status": "continue",
            "allowed_action": decision[0]["sidecar_decision"],
        },
        {
            "priority": "C1",
            "task_id": "v5c_cycle_sector_pit_state_data_gate_repair",
            "status": "continue",
            "allowed_action": decision[0]["cycle_decision"],
        },
    ]


def _blockers(review_rows: list[dict[str, Any]], capex_blockers: list[dict[str, str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in review_rows:
        if row["review_status"] in {"source_missing_not_model_ready", "needs_manual_review_text_unavailable", "needs_manual_review_keyword_gap", "needs_review_no_strict_panel_row"}:
            out.append(
                {
                    "blocker_id": row["review_status"],
                    "severity": "nonfatal",
                    "code": row["code"],
                    "report_period": row["report_period"],
                    "detail": row["review_note"],
                    "required_action": "keep capex/FCF out of v1; repair only if future model spec needs it",
                }
            )
    for row in capex_blockers:
        if row.get("blocker_id") == "financial_report_pdf_unavailable":
            out.append(
                {
                    "blocker_id": row.get("blocker_id", ""),
                    "severity": "nonfatal",
                    "code": row.get("code", ""),
                    "report_period": row.get("report_period", ""),
                    "detail": row.get("detail", ""),
                    "required_action": "source retry optional; no backtest before PIT data gate",
                }
            )
    return out or [{"blocker_id": "none", "severity": "none", "code": "", "report_period": "", "detail": "data gate refresh completed", "required_action": ""}]


def _summary(
    status: str,
    pm_gate_decision: str,
    blockers: list[dict[str, Any]],
    review_queue_count: int = 0,
    p0_review_count: int = 0,
    source_missing_count: int = 0,
    pit_clean_available_count: int = 0,
    sidecar_rows: int = 0,
    cycle_rows: int = 0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": TASK,
        "status": status,
        "formal_backtest_scope_start": BACKTEST_START,
        "formal_backtest_scope_end": BACKTEST_END,
        "review_queue_count": review_queue_count,
        "p0_review_count": p0_review_count,
        "source_missing_count": source_missing_count,
        "pit_clean_available_reviewed_count": pit_clean_available_count,
        "sidecar_rows": sidecar_rows,
        "cycle_rows": cycle_rows,
        "highway_capex_fcf_model_use_allowed": False,
        "highway_capex_fcf_enters_v1": False,
        "sidecar_observation_only": True,
        "cycle_sector_data_gate_only": True,
        "v57f_core_modified": False,
        "v5f_primary_modified": False,
        "backtest_started": False,
        "threshold_scan_used": False,
        "accepted": False,
        "live_trading_approved": False,
        "fatal_blocker_count": sum(1 for row in blockers if row.get("severity") == "fatal"),
        "nonfatal_blocker_count": sum(1 for row in blockers if row.get("severity") == "nonfatal"),
        "pm_gate_decision": pm_gate_decision,
    }


def _report(
    review_rows: list[dict[str, Any]],
    coverage: list[dict[str, Any]],
    sidecar: list[dict[str, Any]],
    cycle: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    p0 = [row for row in review_rows if row["priority"] == "P0_sample_review"]
    return "\n".join(
        [
            "# V5c Highway Capex / FCF Small Original Page Review",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            "- Scope: data gate only; no backtest and no model merge.",
            "- V5f primary remains `internal_subsleeve_mom12_70_30`.",
            "- `highway_ocf_risk_cap_v1` remains diagnostic and does not enter forward observation.",
            "",
            "## Highway Capex / FCF Review",
            f"- Queue rows: `{len(review_rows)}`",
            f"- P0 rows reviewed: `{len(p0)}`",
            f"- PIT-clean reviewed rows: `{sum(1 for row in review_rows if str(row['review_status']).startswith('reviewed_pit_clean_'))}`",
            f"- Source-missing rows: `{sum(1 for row in review_rows if row['review_status'] == 'source_missing_not_model_ready')}`",
            "- Capex/FCF remain excluded from v1 model input.",
            "",
            "## Coverage",
            *[
                f"- `{row['metric']}`: {row['numerator']}/{row['denominator']} ({float(row['coverage_ratio']):.2%})"
                for row in coverage
            ],
            "",
            "## Sidecar",
            f"- Rows: `{len(sidecar)}`; gas/water and telecom continue observation only.",
            "",
            "## Cycle Sectors",
            f"- Rows: `{len(cycle)}`; cycle sectors continue PIT state data gate only, no backtest.",
            "",
        ]
    )


def _rules() -> str:
    return """# Agent Execution Rules

- Do only `v5c_highway_capex_fcf_small_original_page_review`.
- Capex / FCF stay data-gate fields and do not enter current v1.
- Do not backtest, tune thresholds, or modify V57f/V5f.
- Gas/water and telecom remain sidecar observation only.
- Cycle sectors remain PIT state data gate only; no backtest before state evidence.
- Do not mark accepted or live approved.
"""


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        FREEZE_DIR / "v5c_highway_capex_fcf_original_page_review_queue.csv",
        CAPEX_DIR / "v5c_infra_capex_strict_panel.csv",
        CAPEX_DIR / "v5c_infra_capex_blockers.csv",
        SIDECAR_DIR / "v5c_sidecar_observation_enhancement_queue.csv",
        CYCLE_DIR / "v5c_cycle_sector_data_gate_queue.csv",
    ]
    return [
        {
            "blocker_id": "missing_required_input",
            "severity": "fatal",
            "path": str(path),
            "required_action": "restore local V5c data-gate input before continuing",
        }
        for path in required
        if not (root / path).exists()
    ]


def _pit_pass(visible_date: str, trade_date: str) -> bool | str:
    if not visible_date or not trade_date:
        return "unknown"
    return str(visible_date)[:10] <= str(trade_date)[:10]


def _has_number(value: Any) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number)


def _to_int(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    summary = run_v5c_highway_capex_fcf_small_original_page_review(Path(args.root))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
