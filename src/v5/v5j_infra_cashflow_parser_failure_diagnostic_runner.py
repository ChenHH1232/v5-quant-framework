from __future__ import annotations

import csv,json,re
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

OUT=Path("v5j_infra_cashflow_parser_failure_diagnostic")/"current"
SOURCE=Path("v5j_pre2021_infra_original_cashflow_panel")/"current"/"v5j_infra_cashflow_original_statement_candidates.csv"
CFO="经营活动产生的现金流量净额"; CAPEX=("购建固定资产、无形资产和其他长期资产支付的现金","购建固定资产、无形资产和其他长期资产所支付的现金","购建固定资产")
def run_v5j_infra_cashflow_parser_failure_diagnostic(root:Path=Path("."))->dict[str,Any]:
 out=root/OUT;out.mkdir(parents=True,exist_ok=True);source=root/SOURCE
 if not source.exists():raise FileNotFoundError(source)
 rows=[r for r in _read(source) if r.get("download_status") in {"downloaded","cached"} and r.get("extraction_status")!="pass_original_statement_extracted"]
 audit=[_inspect(r) for r in rows];counts=Counter(r["repair_class"] for r in audit);summary={"created_at_utc":_now(),"task":"v5j_infra_cashflow_parser_failure_diagnostic","failure_pdf_count":len(audit),"repair_class_counts":dict(counts),"status":"parser_failure_repair_classes_ready","accepted":False}
 _write(out/"v5j_infra_cashflow_parser_failure_diagnostic.csv",audit);(out/"v5j_infra_cashflow_parser_failure_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");return summary
def _inspect(row:dict[str,str])->dict[str,Any]:
 try:
  import fitz  # type: ignore
  with fitz.open(row["resolved_pdf_path"]) as doc:text="\n".join(doc.load_page(i).get_text("text") or "" for i in range(len(doc)))
  cfo=CFO in text; capex_terms=[term for term in CAPEX if term in text];chars=len(re.sub(r"\s+","",text));klass="alternate_capex_term_parser_fix" if cfo and capex_terms and CAPEX[0] not in capex_terms else ("one_required_term_missing_or_table_layout_review" if chars>1000 else "likely_scanned_or_textless_pdf_needs_ocr")
  return {"code":row["code"],"report_period":row["report_period"],"sleeve_ids":row.get("sleeve_ids",""),"pdf_path":row["resolved_pdf_path"],"text_character_count":chars,"cfo_term_found":cfo,"capex_terms_found":";".join(capex_terms),"repair_class":klass,"accepted":False}
 except Exception as exc:return {"code":row["code"],"report_period":row["report_period"],"pdf_path":row.get("resolved_pdf_path",""),"repair_class":f"pdf_read_error:{type(exc).__name__}","accepted":False}
def _read(path:Path)->list[dict[str,str]]:
 with path.open(encoding="utf-8-sig",newline="")as h:return list(csv.DictReader(h))
def _write(path:Path,rows:list[dict[str,Any]])->None:
 fields=list(dict.fromkeys(k for r in rows for k in r))or["empty"]
 with path.open("w",encoding="utf-8-sig",newline="")as h:w=csv.DictWriter(h,fieldnames=fields);w.writeheader();w.writerows(rows)
def _now()->str:return datetime.now(timezone.utc).isoformat(timespec="seconds")
if __name__=="__main__":print(json.dumps(run_v5j_infra_cashflow_parser_failure_diagnostic(),ensure_ascii=False,indent=2))
