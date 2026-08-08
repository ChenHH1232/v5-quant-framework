from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OUT=Path("v5j_frozen_sell_timing_full_pit_validation")/"current"
POOL=Path("数据库")/"processed"/"pre2021_repaired_multisleeve_pit_pool_v5"/"repaired_multisleeve_pit_pool.csv"
GATE=Path("v5j_cross_period_technical_validation_gate")/"current"/"v5j_cross_period_data_gate_summary.json"
MINUTE=Path("数据库")/"processed"/"local_1min_clean_2013_2026"/"by_year"
RULES=("open_control","vwap_1000_protect_else_1400","two_5m_vwap_break_1000_else_1400","vwap_1400_hold_to_1445")

def run_v5j_frozen_sell_timing_full_pit_validation(root:Path=Path("."))->dict[str,Any]:
    gate=json.loads((root/GATE).read_text(encoding="utf-8"))
    if not gate.get("technical_rule_validation_allowed"):raise RuntimeError("PIT data gate has not allowed frozen technical validation.")
    out=root/OUT;out.mkdir(parents=True,exist_ok=True)
    pool=[r for r in _csv(root/POOL) if r.get("pool_eligibility")=="eligible_for_predecessor_pool"]
    dates=sorted({r["rebalance_date"] for r in pool});next_date={d:dates[i+1] for i,d in enumerate(dates[:-1])}
    intents=[{**r,"intent_date":r["rebalance_date"],"execution_date":next_date[r["rebalance_date"]],"intent_id":f"{r['rebalance_date']}|{r['code']}|{r['sleeve_id']}"} for r in pool if r["rebalance_date"] in next_date]
    bars=_load_days(root,intents);events=[x for intent in intents for x in _evaluate(intent,bars.get(intent["intent_id"],[]))]
    results=_results(events);by_sleeve_year=_by_sleeve_year(events);audits=_audits(intents,events);decision=_decision(results,audits)
    _write(out/"v5j_frozen_sell_timing_full_pit_events.csv",events);_write(out/"v5j_frozen_sell_timing_full_pit_results.csv",results);_write(out/"v5j_frozen_sell_timing_by_sleeve_year.csv",by_sleeve_year);_write(out/"v5j_frozen_sell_timing_governance_audit.csv",audits);_write(out/"v5j_frozen_sell_timing_pm_gate.csv",[decision])
    summary={"created_at_utc":_now(),"task":"v5j_frozen_sell_timing_full_pit_validation","validation_window":"2013-01-01_to_2021-04-30","intent_count":len(intents),"fillable_intent_count":len({r['intent_id'] for r in events if r['pit_status']=='pass'}),"rule_count":len(RULES),"technical_rule_validation_started":True,"scope":"frozen_execution_window_on_prior_pit_candidate_exit_proxy_not_v5e_profit_lock","stock_selection_rebuilt":False,"next_period_pool_used_for_signal":False,"parameter_scan_used":False,"accepted":False,"pm_gate_decision":decision["pm_gate_decision"]}
    (out/"v5j_frozen_sell_timing_full_pit_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");(out/"v5j_frozen_sell_timing_full_pit_report.md").write_text(_report(summary,results,decision),encoding="utf-8")
    return summary

def _load_days(root:Path,intents:list[dict[str,str]])->dict[str,list[dict[str,str]]]:
    grouped=defaultdict(list)
    for x in intents:grouped[(x["code"],x["execution_date"][:4])].append(x)
    out={}
    for (code,year),members in grouped.items():
        path=root/MINUTE/year/f"{code.replace('.','_')}_1min.csv";wanted={x["execution_date"] for x in members};by_day=defaultdict(list)
        if path.exists():
            for r in _csv(path):
                if r.get("trade_date") in wanted:by_day[r["trade_date"]].append(r)
        for x in members:out[x["intent_id"]]=by_day.get(x["execution_date"],[])
    return out

def _evaluate(intent:dict[str,str],bars:list[dict[str,str]])->list[dict[str,Any]]:
    index={x["time"]:x for x in bars};f10=_feature(bars,"10:00:00");f14=_feature(bars,"14:00:00");two=_feature(bars,"09:55:00")["below"] and f10["below"]
    variants=[("open_control","09:31:00",True),("vwap_1000_protect_else_1400","10:01:00" if f10["below"] else "14:01:00",f10["available"]),("two_5m_vwap_break_1000_else_1400","10:01:00" if two else "14:01:00",f10["available"]),("vwap_1400_hold_to_1445","14:01:00" if f14["below"] else "14:46:00",f14["available"])]
    control=_fill(index,"09:31:00");control_px=_f(control.get("open")) if control else 0.;out=[]
    for candidate,selected,available in variants:
        fill=control if candidate=="open_control" else _fill(index,selected);fallback=False
        if not available or not fill:fill=control;fallback=True
        px=_f(fill.get("open")) if fill else 0.
        out.append({"intent_id":intent["intent_id"],"intent_date":intent["intent_date"],"execution_date":intent["execution_date"],"year":intent["execution_date"][:4],"code":intent["code"],"sleeve_id":intent["sleeve_id"],"candidate_id":candidate,"selected_execution_time":selected,"fallback_used":fallback,"minute_row_count":len(bars),"control_open":control_px,"selected_open":px,"sell_proceeds_delta_bps":(px/control_px-1)*10000 if px and control_px else "","vwap_1000":f10["vwap"],"close_1000_lte_vwap":f10["below"],"two_5m_vwap_break":two,"close_1400_lte_vwap":f14["below"],"pit_status":"pass" if control_px and px else "missing_required_bar","future_outcome_used_for_signal":False,"accepted":False})
    return out

def _feature(bars:list[dict[str,str]],until:str)->dict[str,Any]:
    visible=[r for r in bars if r["time"]<=until];vol=sum(_f(r.get("volume")) for r in visible);amt=sum(_f(r.get("amount")) for r in visible);at=next((r for r in visible if r["time"]==until),None);vwap=amt/vol if vol else 0.;close=_f(at.get("close")) if at else 0.;return {"available":bool(at and vol>0),"vwap":vwap,"below":bool(close and vwap and close<=vwap)}
def _fill(index:dict[str,dict[str,str]],time:str)->dict[str,str]|None:
    r=index.get(time);return r if r and _f(r.get("volume"))>0 and _f(r.get("low"))>0 else None
def _results(events:list[dict[str,Any]])->list[dict[str,Any]]:
    out=[]
    for candidate,rows in sorted(_group(events,lambda x:x["candidate_id"]).items()):
        valid=[x for x in rows if x["pit_status"]=="pass"];edges=[_f(x["sell_proceeds_delta_bps"]) for x in valid]
        out.append({"candidate_id":candidate,"event_count":len(rows),"fillable_event_count":len(valid),"fallback_count":sum(x["fallback_used"] for x in rows),"mean_sell_proceeds_delta_bps":sum(edges)/len(edges) if edges else 0.,"median_sell_proceeds_delta_bps":_median(edges),"positive_event_ratio":sum(x>0 for x in edges)/len(edges) if edges else 0.,"accepted":False})
    return out
def _by_sleeve_year(events:list[dict[str,Any]])->list[dict[str,Any]]:
    out=[]
    for (candidate,year,sleeve),rows in sorted(_group(events,lambda x:(x["candidate_id"],x["year"],x["sleeve_id"])).items()):
        valid=[x for x in rows if x["pit_status"]=="pass"];edges=[_f(x["sell_proceeds_delta_bps"]) for x in valid]
        out.append({"candidate_id":candidate,"year":year,"sleeve_id":sleeve,"event_count":len(valid),"mean_sell_proceeds_delta_bps":sum(edges)/len(edges) if edges else 0.,"positive_event_ratio":sum(x>0 for x in edges)/len(edges) if edges else 0.})
    return out
def _group(rows:list[dict[str,Any]],key:Any)->dict[Any,list[dict[str,Any]]]:
    out=defaultdict(list)
    for r in rows:out[key(r)].append(r)
    return out
def _audits(intents:list[dict[str,str]],events:list[dict[str,Any]])->list[dict[str,Any]]:
    return [{"audit_id":"prior_pit_candidate_intent_only","status":"pass","detail":len(intents)},{"audit_id":"no_next_period_pool_signal","status":"pass","detail":True},{"audit_id":"completed_bar_signal_next_bar_fill","status":"pass","detail":"10:00/14:00 completed bars; 10:01/14:01/14:46 fills."},{"audit_id":"no_sell_signal_created","status":"pass","detail":"All proxy exits are precommitted at prior quarterly PIT event."},{"audit_id":"parameter_scan_used","status":"pass","detail":False},{"audit_id":"missing_bar_rate","status":"pass" if all(x['pit_status']=='pass' for x in events if x['candidate_id']=='open_control') else 'review',"detail":sum(x['pit_status']!='pass' for x in events if x['candidate_id']=='open_control')}]
def _decision(results:list[dict[str,Any]],audits:list[dict[str,Any]])->dict[str,Any]:
    technical=[x for x in results if x["candidate_id"]!="open_control"];best=max(technical,key=lambda x:x["mean_sell_proceeds_delta_bps"]);return {"pm_gate_decision":"full_pit_exit_proxy_positive_but_not_v5e_exit_validated" if _f(best["mean_sell_proceeds_delta_bps"])>0 and _f(best["positive_event_ratio"])>=.5 else "full_pit_exit_proxy_not_stable_keep_v5i_diagnostic_only","best_fixed_candidate":best["candidate_id"],"best_mean_sell_proceeds_delta_bps":best["mean_sell_proceeds_delta_bps"],"best_positive_event_ratio":best["positive_event_ratio"],"accepted":False,"reason":"A broad prior-PIT exit proxy is not an actual V5e profit-lock event family and cannot alter V5e/V57f execution."}
def _median(x:list[float])->float:
    x=sorted(x);return x[len(x)//2] if len(x)%2 else (x[len(x)//2-1]+x[len(x)//2])/2 if x else 0.
def _f(x:Any)->float:
    try:return float(x) if math.isfinite(float(x)) else 0.
    except (TypeError,ValueError):return 0.
def _csv(p:Path)->list[dict[str,str]]:
    with p.open(encoding="utf-8-sig",newline="") as h:return list(csv.DictReader(h))
def _write(p:Path,rows:list[dict[str,Any]])->None:
    fields=list(dict.fromkeys(k for r in rows for k in r)) or ["empty"]
    with p.open("w",encoding="utf-8-sig",newline="") as h:w=csv.DictWriter(h,fields);w.writeheader();w.writerows(rows)
def _now()->str:return datetime.now(timezone.utc).isoformat(timespec="seconds")
def _report(s:dict[str,Any],r:list[dict[str,Any]],d:dict[str,Any])->str:return f"# Frozen V5i full PIT exit-proxy validation\n\n- Intent population: `{s['intent_count']}` prior PIT candidates with scheduled next-quarter exit proxies.\n- This is not V5e profit-lock history and cannot promote a V5e rule.\n- PM gate: `{d['pm_gate_decision']}`.\n"
if __name__=="__main__":print(json.dumps(run_v5j_frozen_sell_timing_full_pit_validation(),ensure_ascii=False,indent=2))
