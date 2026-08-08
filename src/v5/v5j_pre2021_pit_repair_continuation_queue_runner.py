from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT=Path("v5j_pre2021_pit_repair_continuation_queue")/"current"
BANK=Path("v5j_bank_2011_2012_regulatory_pdf_repair")/"current"/"v5j_bank_2011_2012_pit_coverage.csv"
ACTION=Path("v5j_material_action_original_notice_extract")/"current"/"v5j_material_action_event_review_progress.csv"
FALLBACK=Path("v5j_material_action_unclassified_notice_fallback")/"current"/"v5j_unclassified_fallback_notice_titles.csv"
PLAN=Path("v5j_pre2021_infra_original_cashflow_panel")/"current"/"v5j_infra_cashflow_source_plan.csv"
EXTRACT=Path("v5j_pre2021_infra_original_cashflow_panel")/"current"/"v5j_infra_cashflow_original_statement_candidates.csv"

def run_v5j_pre2021_pit_repair_continuation_queue(root:Path=Path("."))->dict[str,Any]:
    out=root/OUT;out.mkdir(parents=True,exist_ok=True);required=[root/x for x in (BANK,ACTION,FALLBACK,PLAN,EXTRACT)]
    if any(not p.exists() for p in required):raise FileNotFoundError("Missing PIT repair output required for continuation queue")
    bank=[r for r in _read(root/BANK) if str(r.get("all_three_candidate_terms","")).lower()!="true"]
    actions=_read(root/ACTION);fallback=_read(root/FALLBACK);plan=_read(root/PLAN);extract=_read(root/EXTRACT)
    rows=[]
    rows += [{"workstream":"bank_regulatory","priority":"P0","item_id":f"{r['rebalance_date']}|{r['code']}","due_date":r["rebalance_date"],"status":"needs_original_page_value_and_old_nomenclature_review","source_or_context":f"selected_report={r.get('selected_report_year','')}; fields={r.get('candidate_fields','')}","required_evidence":"NPL, provision coverage, and Basel-version-equivalent core-capital definition with page/unit/visible date","target_reconstruction_permission":False} for r in bank]
    rows += [{"workstream":"corporate_action","priority":"P0","item_id":r["event_id"],"due_date":"","status":r["review_status"],"source_or_context":"original notice PDF term contexts available","required_evidence":"cash/stock/right terms, effective date, and merger/terminal settlement treatment","target_reconstruction_permission":False} for r in actions]
    rows += [{"workstream":"corporate_action_fallback","priority":"P0","item_id":r["event_id"],"due_date":r["effective_factor_date"],"status":"needs_manual_classification","source_or_context":r["announcement_title"],"required_evidence":"classify 股权分置改革 implementation and derive documented terms from source notice","target_reconstruction_permission":False} for r in fallback if "股权分置改革方案实施公告" in r.get("announcement_title","")]
    source_missing=[r for r in plan if r.get("source_status")=="missing_cninfo_pdf"]
    parser_missing=[r for r in extract if r.get("download_status") in {"downloaded","cached"} and r.get("extraction_status")!="pass_original_statement_extracted"]
    rows += [{"workstream":"infra_source","priority":"P0" if r["report_period"]<"2015-01-01" else "P1","item_id":f"{r['code']}|{r['report_period']}","due_date":min(str(r.get("rebalance_dates","")).split(";")),"status":"missing_cninfo_historical_report_source","source_or_context":r.get("sleeve_ids",""),"required_evidence":"original statement PDF plus publication/visible date","target_reconstruction_permission":False} for r in source_missing]
    rows += [{"workstream":"infra_parser","priority":"P1","item_id":f"{r['code']}|{r['report_period']}","due_date":min(str(r.get("rebalance_dates","")).split(";")),"status":"pdf_available_needs_cashflow_table_page_review_or_ocr","source_or_context":r.get("resolved_pdf_path",r.get("pdf_path","")),"required_evidence":"OCF and capex row values, unit, and statement page","target_reconstruction_permission":False} for r in parser_missing]
    rows=sorted(rows,key=lambda r:(r["priority"],r["due_date"],r["workstream"],r["item_id"]))
    summary={"created_at_utc":_now(),"task":"v5j_pre2021_pit_repair_continuation_queue","queue_item_count":len(rows),"bank_p0_count":len(bank),"corporate_action_p0_count":len(actions),"infra_missing_source_count":len(source_missing),"infra_parser_review_count":len(parser_missing),"status":"continuation_queue_ready_no_proxy_substitution","accepted":False}
    _write(out/"v5j_pre2021_pit_repair_continuation_queue.csv",rows);(out/"v5j_pre2021_pit_repair_continuation_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");return summary
def _read(path:Path)->list[dict[str,str]]:
    with path.open(encoding="utf-8-sig",newline="")as h:return list(csv.DictReader(h))
def _write(path:Path,rows:list[dict[str,Any]])->None:
    fields=list(dict.fromkeys(k for r in rows for k in r))or["empty"]
    with path.open("w",encoding="utf-8-sig",newline="")as h:w=csv.DictWriter(h,fieldnames=fields);w.writeheader();w.writerows(rows)
def _now()->str:return datetime.now(timezone.utc).isoformat(timespec="seconds")
if __name__=="__main__":print(json.dumps(run_v5j_pre2021_pit_repair_continuation_queue(),ensure_ascii=False,indent=2))
