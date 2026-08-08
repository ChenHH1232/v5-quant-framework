from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT = Path("v5j_pit_availability_boundary_closeout") / "current"
BANK_COVERAGE = Path("v5j_bank_2011_2012_regulatory_pdf_repair") / "current" / "v5j_bank_2011_2012_pit_coverage.csv"
BANK_TERMS = Path("v5j_bank_2011_2012_regulatory_pdf_repair") / "current" / "v5j_bank_2011_2012_term_candidates.csv"
ACTION_EVENTS = Path("v5j_material_action_original_notice_extract") / "current" / "v5j_material_action_event_review_progress.csv"
ACTION_CONTEXT = Path("v5j_material_action_original_notice_extract") / "current" / "v5j_material_action_original_notice_term_context.csv"
INFRA_DIAG = Path("v5j_infra_cashflow_parser_failure_diagnostic") / "current" / "v5j_infra_cashflow_parser_failure_diagnostic.csv"


def run_v5j_pit_availability_boundary_closeout(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT; out.mkdir(parents=True, exist_ok=True)
    paths = [root / path for path in (BANK_COVERAGE, BANK_TERMS, ACTION_EVENTS, ACTION_CONTEXT, INFRA_DIAG)]
    if any(not path.exists() for path in paths): raise FileNotFoundError("Missing PIT closeout evidence input")
    bank = _bank_review(_read(root / BANK_COVERAGE), _read(root / BANK_TERMS))
    actions = _action_review(_read(root / ACTION_EVENTS), _read(root / ACTION_CONTEXT))
    infra = _infra_registry(_read(root / INFRA_DIAG))
    decision = _decision(bank, actions, infra)
    summary = {"created_at_utc": _now(), "task": "v5j_pit_availability_boundary_closeout", "bank_page_evidence_rows": len(bank), "bank_genuine_disclosure_unavailable_count": sum(r["review_status"] == "genuine_quarterly_disclosure_unavailable" for r in bank), "action_original_notice_evidence_count": sum(r["original_notice_context_count"] > 0 for r in actions), "infra_availability_registry_count": len(infra), "pm_gate_decision": decision["pm_gate_decision"], "status": decision["status"], "accepted": False, "strategy_backtest_started": False}
    _write(out / "v5j_bank_original_page_review_log.csv", bank)
    _write(out / "v5j_material_action_original_notice_review_log.csv", actions)
    _write(out / "v5j_pit_genuine_disclosure_unavailable_registry.csv", infra)
    _write(out / "v5j_pit_availability_boundary_pm_decision.csv", [decision])
    (out / "v5j_pit_availability_boundary_closeout_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "v5j_pit_availability_boundary_closeout_report.md").write_text(_report(summary), encoding="utf-8")
    return summary


def _bank_review(coverage: list[dict[str, str]], terms: list[dict[str, str]]) -> list[dict[str, Any]]:
    evidence = defaultdict(list)
    for row in terms: evidence[(row["code"], row.get("report_period", ""))].append(row)
    out=[]
    for row in coverage:
        key=(row["code"],row.get("selected_report_period", "")); source=evidence.get(key, [])
        candidate_fields={item["field"] for item in source}
        all_found=set(("nonperforming_loan_rate","provision_coverage","core_tier_1_capital_adequacy_ratio")).issubset(candidate_fields)
        # The missing observations use the latest legal quarterly disclosure; no later
        # annual report is permitted to fill the omitted field.
        status="original_page_value_adjudication_required" if all_found else "genuine_quarterly_disclosure_unavailable"
        out.append({"rebalance_date":row["rebalance_date"],"code":row["code"],"report_period":key[1],"report_visible_date":row.get("selected_report_visible_date", ""),"candidate_field_count":len(candidate_fields),"candidate_page_count":len({item.get("page_number", "") for item in source}),"source_pdf_count":len({item.get("pdf_path", "") for item in source}),"review_status":status,"numeric_value_written":False,"legacy_basel_mapping_approved":False,"future_report_substitution_allowed":False,"usable_for_exact_target":False})
    return out


def _action_review(events: list[dict[str, str]], contexts: list[dict[str, str]]) -> list[dict[str, Any]]:
    by=defaultdict(list)
    for row in contexts: by[row["event_id"]].append(row)
    return [{"event_id":row["event_id"],"ranked_notice_count":row.get("ranked_notice_count", ""),"original_notice_context_count":len(by[row["event_id"]]),"source_pdf_count":len({item.get("source_pdf", "") for item in by[row["event_id"]]}),"review_status":"original_notice_terms_and_settlement_adjudication_required","terms_inferred_from_adjustment_factor":False,"usable_for_total_return":False,"accepted":False} for row in events]


def _infra_registry(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    result=[]
    for row in rows:
        kind=row.get("repair_class", "")
        status="genuine_disclosure_unavailable_candidate" if row.get("cfo_term_found")=="True" and not row.get("capex_terms_found") else ("needs_ocr_source_review" if kind=="likely_scanned_or_textless_pdf_needs_ocr" else "needs_original_table_layout_review")
        result.append({"code":row.get("code", ""),"report_period":row.get("report_period", ""),"sleeve_ids":row.get("sleeve_ids", ""),"source_pdf":row.get("pdf_path", ""),"availability_status":status,"future_annual_report_substitution_allowed":False,"price_proxy_allowed":False,"usable_for_exact_target":False})
    return result


def _decision(bank: list[dict[str, Any]], actions: list[dict[str, Any]], infra: list[dict[str, Any]]) -> dict[str, Any]:
    return {"pm_gate_decision":"exact_pre2021_v57f_reconstruction_unavailable", "status":"closed_unavailable_boundary_no_frozen_validation", "frozen_v5f_validation_permitted":False, "coverage_qualified_diagnostic_only_permitted":True, "proxy_or_future_fill_allowed":False, "forward_paper_tracking_continue":True, "accepted":False}


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle: return list(csv.DictReader(handle))
def _write(path: Path, rows: list[dict[str, Any]]) -> None:
    fields=list(dict.fromkeys(key for row in rows for key in row)) or ["empty"]
    with path.open("w",encoding="utf-8-sig",newline="") as handle: writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader();writer.writerows(rows)
def _now() -> str: return datetime.now(timezone.utc).isoformat(timespec="seconds")
def _report(summary: dict[str, Any]) -> str:
    return "\n".join(["# PIT availability boundary closeout", "", "- Original-page and notice evidence are logged, but no unresolved numeric value or settlement term is inferred.", "- Genuine early-quarter disclosure omissions, source-layout failures, and OCR cases are not eligible for future-report or price-proxy filling.", "- Exact pre-2021 V57f target reconstruction is closed unavailable; the frozen V5f validation remains not run.", "- A separately approved coverage-qualified diagnostic may be designed, but cannot be relabeled exact validation.", ""])


if __name__ == "__main__": print(json.dumps(run_v5j_pit_availability_boundary_closeout(), ensure_ascii=False, indent=2))
