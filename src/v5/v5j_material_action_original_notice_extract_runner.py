from __future__ import annotations

import csv
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


OUT = Path("v5j_material_action_original_notice_extract") / "current"
CANDIDATES = Path("v5j_material_corporate_action_notice_repair") / "current" / "v5j_material_action_notice_candidates.csv"
TERMS = ("每10股", "派发", "送", "转增", "配股", "比例", "换股", "现金选择权", "终止上市")


def run_v5j_material_action_original_notice_extract(root: Path = Path("."), *, per_event_limit: int = 3) -> dict[str, Any]:
    out = root / OUT; pdf_dir = out / "pdf"; out.mkdir(parents=True, exist_ok=True); pdf_dir.mkdir(exist_ok=True)
    source = root / CANDIDATES
    if not source.exists(): raise FileNotFoundError(f"Missing material action candidates: {source}")
    ranked = _rank(_read(source), per_event_limit)
    downloads = _download(ranked, pdf_dir)
    pages = _extract(downloads)
    event_summary = _event_summary(ranked, pages)
    blockers = _blockers(event_summary)
    summary = {"created_at_utc": _now(), "task": "v5j_material_action_original_notice_extract", "event_count": len(event_summary), "ranked_notice_count": len(ranked), "downloaded_or_cached_pdf_count": sum(r["download_status"] in {"downloaded", "cached"} for r in downloads), "term_context_count": len(pages), "events_with_original_notice_context": sum(r["original_notice_context_found"] for r in event_summary), "status": "original_notice_context_candidates_ready_for_manual_terms_review", "accepted": False, "strategy_backtest_started": False}
    _write(out / "v5j_material_action_ranked_notice_queue.csv", ranked)
    _write(out / "v5j_material_action_notice_download_audit.csv", downloads)
    _write(out / "v5j_material_action_original_notice_term_context.csv", pages)
    _write(out / "v5j_material_action_event_review_progress.csv", event_summary)
    _write(out / "v5j_material_action_original_notice_blockers.csv", blockers)
    (out / "v5j_material_action_original_notice_extract_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def _rank(rows: list[dict[str, str]], limit: int) -> list[dict[str, Any]]:
    by: dict[str, list[dict[str, str]]] = {}
    for row in rows: by.setdefault(row["event_id"], []).append(row)
    out=[]
    for event_id, items in by.items():
        def score(row: dict[str,str]) -> tuple[int, str]:
            title=row.get("announcement_title", ""); day=row.get("announcement_visible_date", ""); types=row.get("candidate_types", "")
            return (sum(term in title for term in TERMS)*5 + ("cash_dividend_or_ex_right" in types)*2 + ("stock_dividend_or_conversion" in types)*2 + ("rights_issue" in types)*2, day)
        for idx,row in enumerate(sorted(items, key=score, reverse=True)[:limit], start=1): out.append({**row, "review_rank":idx, "ranking_rule":"title_term_score_then_latest_visible_date", "terms_inferred_from_factor":False, "accepted":False})
    return sorted(out,key=lambda r:(r["event_id"],r["review_rank"]))


def _download(rows: list[dict[str,Any]], pdf_dir:Path)->list[dict[str,Any]]:
    session=requests.Session(); headers={"User-Agent":"Mozilla/5.0","Referer":"http://www.cninfo.com.cn/"}; out=[]
    for row in rows:
        safe=re.sub(r"[^A-Za-z0-9_.-]","_",f"{row['event_id']}_{row['review_rank']}"); path=pdf_dir/f"{safe}.pdf"; status="cached" if path.exists() and path.stat().st_size>1024 else ""; error=""
        if not status and row.get("announcement_url"):
            try: response=session.get(row["announcement_url"],headers=headers,timeout=35);response.raise_for_status();path.write_bytes(response.content);status="downloaded"
            except Exception as exc: status,error=f"download_error:{type(exc).__name__}",str(exc)
        if not status: status="source_url_missing"
        out.append({**row,"pdf_path":str(path),"download_status":status,"error":error});time.sleep(.1)
    return out


def _extract(rows:list[dict[str,Any]])->list[dict[str,Any]]:
    import fitz  # type: ignore
    out=[]
    for row in rows:
        if row["download_status"] not in {"downloaded","cached"}: continue
        try:
            doc=fitz.open(row["pdf_path"])
            for index in range(len(doc)):
                text=doc.load_page(index).get_text("text") or ""
                compact=re.sub(r"\s+"," ",text)
                hits=[term for term in TERMS if term in compact]
                if hits:
                    first=min((compact.find(term) for term in hits if compact.find(term)>=0),default=0);context=compact[max(0,first-280):first+700]
                    out.append({"event_id":row["event_id"],"code":row["code"],"effective_factor_date":row["effective_factor_date"],"review_rank":row["review_rank"],"announcement_visible_date":row["announcement_visible_date"],"announcement_title":row["announcement_title"],"source_pdf":row["pdf_path"],"page_number":index+1,"matched_terms":";".join(hits),"context":context,"review_status":"needs_manual_term_and_treatment_confirmation","accepted":False})
            doc.close()
        except Exception as exc: out.append({"event_id":row["event_id"],"code":row["code"],"review_rank":row["review_rank"],"review_status":f"pdf_extract_error:{type(exc).__name__}","accepted":False})
    return out


def _event_summary(ranked:list[dict[str,Any]], pages:list[dict[str,Any]])->list[dict[str,Any]]:
    events=sorted({r["event_id"] for r in ranked}); found={r["event_id"] for r in pages if r.get("context")}
    return [{"event_id":event,"ranked_notice_count":sum(r["event_id"]==event for r in ranked),"original_notice_context_found":event in found,"review_status":"needs_manual_term_and_treatment_confirmation" if event in found else "original_notice_context_not_found","usable_for_total_return":False,"accepted":False} for event in events]


def _blockers(rows:list[dict[str,Any]])->list[dict[str,Any]]:
    missing=sum(not r["original_notice_context_found"] for r in rows);return [{"blocker_id":"material_action_original_terms_manual_review","severity":"blocking_for_total_return_reconciliation","detail":"All original-notice contexts need term, effective-date, and settlement-treatment confirmation."}]+([{"blocker_id":"material_action_original_notice_context_missing","severity":"review","detail":f"{missing} events have no extracted original-notice term context."}] if missing else [])
def _read(path:Path)->list[dict[str,str]]:
    with path.open(encoding="utf-8-sig",newline="") as h:return list(csv.DictReader(h))
def _write(path:Path,rows:list[dict[str,Any]])->None:
    fields=list(dict.fromkeys(k for r in rows for k in r)) or ["empty"]
    with path.open("w",encoding="utf-8-sig",newline="") as h:w=csv.DictWriter(h,fieldnames=fields);w.writeheader();w.writerows(rows)
def _now()->str:return datetime.now(timezone.utc).isoformat(timespec="seconds")
if __name__=="__main__":print(json.dumps(run_v5j_material_action_original_notice_extract(),ensure_ascii=False,indent=2))
