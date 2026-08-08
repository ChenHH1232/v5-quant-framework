from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.v5j_pit_pool_1min_pairing_runner import _paired

OUT = Path("v5j_frozen_buy_timing_full_pit_validation") / "current"
POOL = Path("数据库") / "processed" / "pre2021_repaired_multisleeve_pit_pool_v5" / "repaired_multisleeve_pit_pool.csv"
MANIFEST = Path("v5j_pit_pool_1min_pairing") / "current" / "v5j_pit_pool_1min_event_manifest.csv"
GATE = Path("v5j_cross_period_technical_validation_gate") / "current" / "v5j_cross_period_data_gate_summary.json"
MINUTE = Path("数据库") / "processed" / "local_1min_clean_2013_2026" / "by_year"
RULE = "pressure_positive_1000_else_1400_buy"


def run_v5j_frozen_buy_timing_full_pit_validation(root: Path = Path(".")) -> dict[str, Any]:
    gate = json.loads((root / GATE).read_text(encoding="utf-8"))
    if not gate.get("technical_rule_validation_allowed"):
        raise RuntimeError("PIT data gate has not allowed frozen technical validation.")
    out = root / OUT; out.mkdir(parents=True, exist_ok=True)
    pool = [r for r in _csv(root / POOL) if r.get("pool_eligibility") == "eligible_for_predecessor_pool"]
    manifest = {r["event_id"]: r for r in _csv(root / MANIFEST)}
    events = [r for r in pool if _paired(manifest.get(f"{r['rebalance_date']}|{r['code']}|{r['sleeve_id']}", {}))]
    day_bars = _load_event_days(root, events)
    evaluated = [_evaluate(event, day_bars.get(f"{event['rebalance_date']}|{event['code']}|{event['sleeve_id']}", [])) for event in events]
    summaries = _summaries(evaluated)
    audits = _audits(events, evaluated)
    decision = _decision(summaries, audits)
    _write(out / "v5j_frozen_buy_timing_full_pit_events.csv", evaluated)
    _write(out / "v5j_frozen_buy_timing_full_pit_summary_by_sleeve_year.csv", summaries)
    _write(out / "v5j_frozen_buy_timing_full_pit_governance_audit.csv", audits)
    _write(out / "v5j_frozen_buy_timing_full_pit_pm_gate.csv", [decision])
    summary = {"created_at_utc": _now(), "task": "v5j_frozen_buy_timing_full_pit_validation", "rule": RULE, "validation_window": "2013-01-01_to_2021-04-30", "eligible_pit_event_count": len(events), "evaluated_event_count": sum(r["pit_status"] == "pass" for r in evaluated), "technical_rule_validation_started": True, "technical_rule_validation_scope": "frozen_buy_execution_proxy_on_existing_pit_candidate_pool_only", "stock_selection_rebuilt": False, "parameter_scan_used": False, "accepted": False, "live_trading_approved": False, "pm_gate_decision": decision["pm_gate_decision"]}
    (out / "v5j_frozen_buy_timing_full_pit_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    (out / "v5j_frozen_buy_timing_full_pit_report.md").write_text(_report(summary, summaries, decision), encoding="utf-8")
    return summary


def _evaluate(event: dict[str, str], bars: list[dict[str, str]]) -> dict[str, Any]:
    day, code = event["rebalance_date"], event["code"]
    index = {r["time"]: r for r in bars}; early=[r for r in bars if r["time"] <= "10:00:00"]
    pressure = _pressure(early); positive = pressure >= 0.10
    baseline=_fill(index,"10:01:00"); selected_time="10:01:00" if positive else "14:01:00"; selected=_fill(index,selected_time)
    close=_f(bars[-1].get("close")) if bars else 0.0; base=_f(baseline.get("open")) if baseline else 0.0; chosen=_f(selected.get("open")) if selected else 0.0
    return {"event_id":f"{day}|{code}|{event['sleeve_id']}","rebalance_date":day,"year":day[:4],"code":code,"sleeve_id":event["sleeve_id"],"minute_row_count":len(bars),"amount_pressure_to_1000":pressure,"selected_execution_time":selected_time,"baseline_execution_time":"10:01:00","baseline_price":base,"selected_price":chosen,"close_outcome_only":close,"incremental_entry_edge_bps":((close/chosen-1)-(close/base-1))*10000 if base and chosen and close else "","pit_status":"pass" if base and chosen and close else "missing_required_bar","future_outcome_used_for_evaluation_only":True,"accepted":False}


def _load_event_days(root: Path, events: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    """Parse each annual source once, then expose only the requested PIT dates."""
    requested: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for event in events:
        requested[(event["code"], event["rebalance_date"][:4])].append(event)
    output: dict[str, list[dict[str, str]]] = {}
    for (code, year), members in requested.items():
        path = root / MINUTE / year / f"{code.replace('.', '_')}_1min.csv"
        by_day: dict[str, list[dict[str, str]]] = defaultdict(list)
        if path.exists():
            wanted = {m["rebalance_date"] for m in members}
            for row in _csv(path):
                if row.get("trade_date") in wanted:
                    by_day[str(row["trade_date"])].append(row)
        for event in members:
            output[f"{event['rebalance_date']}|{event['code']}|{event['sleeve_id']}"] = by_day.get(event["rebalance_date"], [])
    return output


def _pressure(rows: list[dict[str,str]]) -> float:
    if len(rows)<2:return 0.0
    total=signed=0.0; previous=_f(rows[0].get("close"))
    for row in rows[1:]:
        amount=max(_f(row.get("amount")),0.0); current=_f(row.get("close")); total+=amount; signed+=amount if current>previous else -amount if current<previous else 0.0; previous=current
    return signed/total if total else 0.0


def _summaries(rows:list[dict[str,Any]])->list[dict[str,Any]]:
    grouped=defaultdict(list)
    for row in rows:
        if row["pit_status"]=="pass": grouped[(row["year"],row["sleeve_id"])].append(row)
    out=[]
    for (year,sleeve),values in sorted(grouped.items()):
        edges=[_f(x["incremental_entry_edge_bps"]) for x in values]
        out.append({"year":year,"sleeve_id":sleeve,"event_count":len(values),"mean_incremental_entry_edge_bps":sum(edges)/len(edges),"median_incremental_entry_edge_bps":sorted(edges)[len(edges)//2],"positive_edge_ratio":sum(x>0 for x in edges)/len(edges),"pressure_positive_event_ratio":sum(x["selected_execution_time"]=="10:01:00" for x in values)/len(values)})
    return out


def _audits(events:list[dict[str,str]], evaluated:list[dict[str,Any]])->list[dict[str,Any]]:
    return [{"audit_id":"data_gate_authorized", "status":"pass", "detail":"V5j cross-period PIT data gate is ready."},{"audit_id":"pit_candidate_pool_only", "status":"pass", "detail":len(events)},{"audit_id":"no_stock_selection_or_weight_change", "status":"pass", "detail":True},{"audit_id":"completed_bar_signal_next_bar_fill", "status":"pass", "detail":"Pressure through 10:00; entry at 10:01 or 14:01."},{"audit_id":"future_close_outcome_not_signal", "status":"pass", "detail":True},{"audit_id":"parameter_scan_used", "status":"pass", "detail":False},{"audit_id":"missing_bar_events", "status":"pass" if all(x["pit_status"]=="pass" for x in evaluated) else "review", "detail":sum(x["pit_status"]!="pass" for x in evaluated)}]


def _decision(summaries:list[dict[str,Any]], audits:list[dict[str,Any]])->dict[str,Any]:
    edges=[_f(x["mean_incremental_entry_edge_bps"]) for x in summaries]; positive=sum(x>0 for x in edges); all_data=next(x for x in audits if x["audit_id"]=="missing_bar_events")["status"]=="pass"
    return {"pm_gate_decision":"full_pit_candidate_proxy_positive_but_not_target_validated" if all_data and positive/len(edges)>=0.65 and sum(edges)/len(edges)>0 else "full_pit_candidate_proxy_not_stable_keep_v5h_observation_only", "positive_sleeve_year_ratio":positive/len(edges) if edges else 0.0,"mean_sleeve_year_edge_bps":sum(edges)/len(edges) if edges else 0.0,"accepted":False,"reason":"Candidate-pool execution proxy cannot promote a portfolio rule until frozen repaired target reconstruction is independently verified."}

def _fill(index:dict[str,dict[str,str]],t:str)->dict[str,str]|None:
    r=index.get(t); return r if r and _f(r.get("open"))>0 and _f(r.get("volume"))>0 else None
def _f(value:Any)->float:
    try:return float(value) if math.isfinite(float(value)) else 0.0
    except (TypeError,ValueError):return 0.0
def _csv(path:Path)->list[dict[str,str]]:
    with path.open(encoding="utf-8-sig",newline="") as h:return list(csv.DictReader(h))
def _write(path:Path,rows:list[dict[str,Any]])->None:
    fields=list(dict.fromkeys(k for row in rows for k in row)) or ["empty"]
    with path.open("w",encoding="utf-8-sig",newline="") as h:w=csv.DictWriter(h,fields);w.writeheader();w.writerows(rows)
def _now()->str:return datetime.now(timezone.utc).isoformat(timespec="seconds")
def _report(s:dict[str,Any],rows:list[dict[str,Any]],d:dict[str,Any])->str:return f"# Frozen V5h full PIT candidate-pool validation\n\n- Events: `{s['evaluated_event_count']}/{s['eligible_pit_event_count']}`.\n- Rule: `{RULE}`.\n- This is an execution proxy on existing PIT candidates, not a rebuilt V57f/V5f portfolio.\n- PM gate: `{d['pm_gate_decision']}`.\n- No acceptance, target weight change, or new buy signal is implied.\n"
if __name__=="__main__":print(json.dumps(run_v5j_frozen_buy_timing_full_pit_validation(),ensure_ascii=False,indent=2))
