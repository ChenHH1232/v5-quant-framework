from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT = Path("v5j_pit_disclosure_trust_audit") / "current"
BANK_COVERAGE = Path("v5j_bank_2011_2012_regulatory_pdf_repair") / "current" / "v5j_bank_2011_2012_pit_coverage.csv"
BANK_TERMS = Path("v5j_bank_2011_2012_regulatory_pdf_repair") / "current" / "v5j_bank_2011_2012_term_candidates.csv"
INFRA = Path("v5j_infra_cashflow_parser_failure_diagnostic") / "current" / "v5j_infra_cashflow_parser_failure_diagnostic.csv"
ACTIONS = Path("v5j_material_action_original_notice_extract") / "current" / "v5j_material_action_event_review_progress.csv"


def run_v5j_pit_disclosure_trust_audit(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT; out.mkdir(parents=True, exist_ok=True)
    inputs=[root / path for path in (BANK_COVERAGE,BANK_TERMS,INFRA,ACTIONS)]
    if any(not path.exists() for path in inputs): raise FileNotFoundError("Missing evidence input for PIT disclosure trust audit")
    bank = _bank(_read(root / BANK_COVERAGE), _read(root / BANK_TERMS))
    infra = _infra(_read(root / INFRA))
    actions = _actions(_read(root / ACTIONS))
    labels = bank + infra + actions
    summary={"created_at_utc":_now(),"task":"v5j_pit_disclosure_trust_audit","bank_untrusted_missing_disclosure_count":sum(r["trust_label"]=="untrusted_missing_pit_regulatory_disclosure" for r in bank),"bank_legacy_nomenclature_count":sum(r["disclosure_reason"].startswith("legacy_regulatory_nomenclature_transition") for r in bank),"infra_untrusted_missing_disclosure_count":sum(r["trust_label"]=="untrusted_missing_pit_capex_disclosure" for r in infra),"action_untrusted_pending_terms_count":len(actions),"historical_reconstructed_candidate_pool_change_allowed":False,"v57f_core_modified":False,"accepted":False,"status":"disclosure_trust_sidecar_ready_no_core_change"}
    _write(out / "v5j_bank_early_regulatory_disclosure_reason_audit.csv",bank)
    _write(out / "v5j_infra_capex_disclosure_reason_audit.csv",infra)
    _write(out / "v5j_material_action_terms_trust_audit.csv",actions)
    _write(out / "v5j_historical_reconstruction_candidate_trust_labels.csv",labels)
    (out / "v5j_pit_disclosure_trust_audit_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (out / "v5j_pit_disclosure_trust_audit_report.md").write_text(_report(summary),encoding="utf-8")
    return summary


def _bank(coverage: list[dict[str,str]], terms: list[dict[str,str]]) -> list[dict[str,Any]]:
    by=defaultdict(set)
    for row in terms: by[(row["code"],row.get("report_period", ""))].add(row["field"])
    required={"nonperforming_loan_rate","provision_coverage","core_tier_1_capital_adequacy_ratio"};out=[]
    for row in coverage:
        fields=by[(row["code"],row.get("selected_report_period", ""))]
        missing=sorted(required-fields)
        if not missing: reason="all_terms_machine_located_needs_page_value_adjudication";label="review_pending_original_page_value"
        elif missing==["core_tier_1_capital_adequacy_ratio"] and {"nonperforming_loan_rate","provision_coverage"}.issubset(fields): reason="legacy_regulatory_nomenclature_transition_or_quarterly_core_capital_omission";label="untrusted_missing_pit_regulatory_disclosure"
        else: reason="quarterly_regulatory_field_not_disclosed_or_not_verifiable";label="untrusted_missing_pit_regulatory_disclosure"
        out.append({"record_type":"bank","rebalance_date":row["rebalance_date"],"code":row["code"],"sleeve_id":"bank","pit_report_period":row.get("selected_report_period", ""),"pit_visible_date":row.get("selected_report_visible_date", ""),"located_fields":";".join(sorted(fields)),"missing_fields":";".join(missing),"disclosure_reason":reason,"trust_label":label,"historical_reconstructed_candidate_allowed":False,"v57f_live_candidate_eligibility_changed":False})
    return out


def _infra(rows: list[dict[str,str]]) -> list[dict[str,Any]]:
    out=[]
    for row in rows:
        if row.get("cfo_term_found")=="True" and not row.get("capex_terms_found"): reason="cashflow_report_text_has_ocf_but_no_capex_line";label="untrusted_missing_pit_capex_disclosure"
        elif row.get("repair_class")=="likely_scanned_or_textless_pdf_needs_ocr": reason="source_not_text_verifiable";label="untrusted_pit_capex_unverified_ocr_required"
        else: reason="cashflow_table_layout_not_auto_verifiable";label="untrusted_pit_capex_unverified_table_review"
        out.append({"record_type":"infra","rebalance_date":"","code":row.get("code",""),"sleeve_id":row.get("sleeve_ids",""),"pit_report_period":row.get("report_period",""),"pit_visible_date":"","located_fields":"ocf" if row.get("cfo_term_found")=="True" else "","missing_fields":"capex_cash_paid_original","disclosure_reason":reason,"trust_label":label,"historical_reconstructed_candidate_allowed":False,"v57f_live_candidate_eligibility_changed":False})
    return out


def _actions(rows: list[dict[str,str]]) -> list[dict[str,Any]]:
    return [{"record_type":"corporate_action","rebalance_date":"","code":row["event_id"].split("|")[0],"sleeve_id":"","pit_report_period":"","pit_visible_date":"","located_fields":"original_notice_context","missing_fields":"action_terms;effective_date;settlement_treatment","disclosure_reason":"original_notice_terms_not_adjudicated","trust_label":"untrusted_total_return_terms_pending_review","historical_reconstructed_candidate_allowed":False,"v57f_live_candidate_eligibility_changed":False} for row in rows]


def _read(path:Path)->list[dict[str,str]]:
    with path.open(encoding="utf-8-sig",newline="")as h:return list(csv.DictReader(h))
def _write(path:Path,rows:list[dict[str,Any]])->None:
    fields=list(dict.fromkeys(k for r in rows for k in r))or["empty"]
    with path.open("w",encoding="utf-8-sig",newline="")as h:w=csv.DictWriter(h,fieldnames=fields);w.writeheader();w.writerows(rows)
def _now()->str:return datetime.now(timezone.utc).isoformat(timespec="seconds")
def _report(summary:dict[str,Any])->str:
    return "\n".join(["# PIT disclosure trust audit", "", "- This audit establishes report-level evidence only. It does not infer whether historical regulation was strict or lax without a rulebook source.", "- Any record whose contemporaneous PIT report omits or cannot verify a required field is untrusted for historical reconstructed-candidate selection.", "- These labels are a reconstruction sidecar; they do not change V57f core or live eligibility.", ""])
if __name__=="__main__":print(json.dumps(run_v5j_pit_disclosure_trust_audit(),ensure_ascii=False,indent=2))
