from __future__ import annotations

import csv
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests


OUT=Path("v5j_material_action_unclassified_notice_fallback")/"current"
REVIEW=Path("v5j_material_corporate_action_notice_repair")/"current"/"v5j_material_action_original_terms_review_matrix.csv"
SEARCH="http://www.cninfo.com.cn/new/information/topSearch/query"; ANN="http://www.cninfo.com.cn/new/hisAnnouncement/query"; STATIC="http://static.cninfo.com.cn/"

def run_v5j_material_action_unclassified_notice_fallback(root:Path=Path("."))->dict[str,Any]:
    out=root/OUT;out.mkdir(parents=True,exist_ok=True); events=[r for r in _read(root/REVIEW) if r.get("review_status")=="no_candidate_notice_found"]
    notices,audit=_query(events); summary={"created_at_utc":_now(),"task":"v5j_material_action_unclassified_notice_fallback","unclassified_event_count":len(events),"fallback_notice_count":len(notices),"events_with_fallback_notices":len({r['event_id'] for r in notices}),"status":"fallback_notice_titles_ready_for_manual_classification","accepted":False,"strategy_backtest_started":False}
    _write(out/"v5j_unclassified_material_events.csv",events);_write(out/"v5j_unclassified_fallback_notice_titles.csv",notices);_write(out/"v5j_unclassified_fallback_query_audit.csv",audit);(out/"v5j_unclassified_fallback_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");return summary

def _query(events:list[dict[str,str]])->tuple[list[dict[str,Any]],list[dict[str,Any]]]:
    s=requests.Session();h={"User-Agent":"Mozilla/5.0","Referer":"http://www.cninfo.com.cn/"};out=[];audit=[]
    for e in events:
        code=e["code"];plain=code.split(".")[0]
        try:
            found=s.post(SEARCH,headers=h,data={"keyWord":plain,"maxNum":10},timeout=25).json();org=next((x.get("orgId") for x in found if str(x.get("code"))==plain and x.get("orgId")),"")
            day=date.fromisoformat(e["effective_factor_date"]);data=s.post(ANN,headers=h,data={"pageNum":1,"pageSize":100,"column":"sse" if code.endswith("XSHG") else "szse","tabName":"fulltext","plate":"","stock":f"{plain},{org}","searchkey":"","secid":"","category":"","trade":"","seDate":f"{(day-timedelta(days=180)).isoformat()}~{(day+timedelta(days=15)).isoformat()}","sortName":"","sortType":"","isHLtitle":"true"},timeout=25).json()
            rows=[]
            for x in data.get("announcements") or []:
                title=re.sub(r"<[^>]+>","",str(x.get("announcementTitle") or ""));visible=_date(x.get("announcementTime"));distance=abs((date.fromisoformat(visible)-day).days) if visible else 9999;url=str(x.get("adjunctUrl") or "")
                rows.append({"event_id":f"{code}|{e['effective_factor_date']}","code":code,"effective_factor_date":e["effective_factor_date"],"factor_change_ratio":e["factor_change_ratio"],"announcement_visible_date":visible,"days_from_effective":distance,"announcement_title":title,"announcement_url":STATIC+url if url else "","review_status":"needs_manual_classification_and_original_terms_review","accepted":False})
            out.extend(sorted(rows,key=lambda r:(r["days_from_effective"],r["announcement_visible_date"] ))[:15]);audit.append({"code":code,"effective_factor_date":e["effective_factor_date"],"status":"pass","returned_notice_count":len(rows)})
        except Exception as exc:audit.append({"code":code,"effective_factor_date":e["effective_factor_date"],"status":f"query_error:{type(exc).__name__}","detail":str(exc)})
    return out,audit
def _date(value:Any)->str:
    try:return datetime.fromtimestamp(int(value)/1000,tz=timezone.utc).date().isoformat()
    except (TypeError,ValueError,OSError):return ""
def _read(path:Path)->list[dict[str,str]]:
    with path.open(encoding="utf-8-sig",newline="")as h:return list(csv.DictReader(h))
def _write(path:Path,rows:list[dict[str,Any]])->None:
    fields=list(dict.fromkeys(k for r in rows for k in r))or["empty"]
    with path.open("w",encoding="utf-8-sig",newline="")as h:w=csv.DictWriter(h,fieldnames=fields);w.writeheader();w.writerows(rows)
def _now()->str:return datetime.now(timezone.utc).isoformat(timespec="seconds")
if __name__=="__main__":print(json.dumps(run_v5j_material_action_unclassified_notice_fallback(),ensure_ascii=False,indent=2))
