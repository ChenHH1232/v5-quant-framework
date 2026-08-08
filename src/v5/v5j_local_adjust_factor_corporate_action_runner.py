from __future__ import annotations

import csv
import io
import json
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.local_1min_clean_ingest_runner import find_local_minute_package, find_v5_database, jq_to_local

OUT = Path("v5j_local_adjust_factor_corporate_action") / "current"
POOL = Path("processed") / "pre2021_repaired_multisleeve_pit_pool_v5" / "repaired_multisleeve_pit_pool.csv"
DAILY = Path("processed") / "pre2021_repaired_multisleeve_pit_pool_v5" / "daily_price_valuation_history.csv"
DIVIDENDS = Path("processed") / "pre2021_repaired_multisleeve_pit_pool_v5" / "pit_dividend_corporate_action_ledger.csv"

def run_v5j_local_adjust_factor_corporate_action(root: Path = Path(".")) -> dict[str, Any]:
    out=root/OUT; out.mkdir(parents=True,exist_ok=True); db=find_v5_database(root)
    pool=[r for r in _csv(db/POOL) if r.get("pool_eligibility")=="eligible_for_predecessor_pool"]
    codes=sorted({r["code"] for r in pool}); factors, audit=_factors(codes)
    dividend=_csv(db/DIVIDENDS); actions=_action_reconciliation(factors, dividend); terminal=_terminal_events(pool, _csv(db/DAILY), factors)
    _write(out/"v5j_local_adjust_factor_panel.csv",factors); _write(out/"v5j_local_adjust_factor_extract_audit.csv",audit); _write(out/"v5j_adjust_factor_corporate_action_reconciliation.csv",actions); _write(out/"v5j_corporate_action_terminal_events.csv",terminal)
    summary={"created_at_utc":_now(),"task":"v5j_local_adjust_factor_corporate_action","pool_code_count":len(codes),"factor_row_count":len(factors),"factor_jump_count":sum(r["factor_jump"] for r in factors),"terminal_event_count":len(terminal),"effective_factor_events_without_dividend_match":sum(r["reconciliation_status"]=="effective_factor_event_recorded_no_dividend_match" for r in actions),"pit_dividend_ledger_linked":True,"price_adjustment_effective_date_ledger_ready":True,"terminal_events_explicitly_recorded":True,"technical_rule_validation_started":False,"accepted":False,"status":"local_adjust_factor_corporate_action_ledger_ready"}
    (out/"v5j_local_adjust_factor_corporate_action_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (out/"v5j_local_adjust_factor_corporate_action_report.md").write_text("# Local PIT corporate-action reconciliation\n\n- Local adjustment factors are an effective-date reconciliation source, not an announcement-date signal source.\n- Dividend/stock actions remain PIT-visible only from their announced ledger rows.\n- Terminal non-tradable periods are explicit and are never filled with later bars.\n",encoding="utf-8")
    return summary

def _factors(codes:list[str])->tuple[list[dict[str,Any]],list[dict[str,Any]]]:
    minute_dir=find_local_minute_package(); zips=[p for p in minute_dir.parent.glob("*.zip") if p.name != ""]
    archive=None
    for candidate in zips:
        with zipfile.ZipFile(candidate) as z:
            if any(e.filename.endswith("/000916.SZ.csv") for e in z.infolist()):
                sample=next(e for e in z.infolist() if e.filename.endswith("/000916.SZ.csv")); text=z.read(sample).decode("utf-8-sig",errors="ignore")
                if "adj_factor" in text[:100]: archive=candidate; break
    if archive is None: raise FileNotFoundError("Local adjustment-factor zip was not found")
    rows=[]; audit=[]
    with zipfile.ZipFile(archive) as z:
        names={e.filename:e for e in z.infolist()}
        for code in codes:
            local=jq_to_local(code); match=next((n for n in names if n.endswith("/"+local+".csv")),None)
            if not match: audit.append({"code":code,"status":"missing_factor_entry"});continue
            records=list(csv.DictReader(io.TextIOWrapper(z.open(match),encoding="utf-8-sig")))
            previous=None
            for r in records:
                day=str(r.get("date", "")); factor=_float(r.get("adj_factor"))
                if len(day)!=8 or factor is None or day < "20121201" or day > "20210430": continue
                jump=previous is not None and abs(factor/previous-1)>1e-10
                rows.append({"code":code,"local_code":local,"trade_date":f"{day[:4]}-{day[4:6]}-{day[6:]}","adjust_factor":factor,"previous_adjust_factor":previous if previous is not None else "","factor_jump":jump,"factor_change_ratio":factor/previous-1 if jump else 0.0,"source":"local_adjust_factor_archive","effective_date_only_not_pit_announcement" : True})
                previous=factor
            audit.append({"code":code,"status":"pass","factor_row_count":len(records),"archive":str(archive)})
    return rows,audit

def _action_reconciliation(factors:list[dict[str,Any]],dividend:list[dict[str,str]])->list[dict[str,Any]]:
    by=defaultdict(list)
    for r in factors:
        if r["factor_jump"]: by[r["code"]].append(r)
    result=[]
    for code,jumps in by.items():
        events=[x for x in dividend if x["code"]==code]
        for j in jumps:
            matched=next((x for x in events if x.get("ex_or_operate_date") and abs((_ordinal(j["trade_date"])-_ordinal(x["ex_or_operate_date"])))<=3),None)
            result.append({"code":code,"effective_factor_date":j["trade_date"],"factor_change_ratio":j["factor_change_ratio"],"matched_ledger_event_id":matched.get("event_id","") if matched else "","matched_action_type":matched.get("corporate_action_type","") if matched else "","reconciliation_status":"matched_to_announced_ledger_event" if matched else "effective_factor_event_recorded_no_dividend_match","pit_signal_use":"false_effective_date_is_reconciliation_only"})
    return result

def _terminal_events(pool:list[dict[str,str]],daily:list[dict[str,str]],factors:list[dict[str,Any]])->list[dict[str,Any]]:
    # A terminal suspension/delisting is a data state, not permission to invent a later minute bar.
    last_daily={}
    for r in daily:
        if r.get("date"): last_daily[r["code"]]=max(last_daily.get(r["code"],""),r["date"])
    dates=sorted({r["rebalance_date"] for r in pool}); next_date={d:dates[i+1] if i+1<len(dates) else "2021-04-30" for i,d in enumerate(dates)}
    factors_by=defaultdict(list)
    for r in factors:factors_by[r["code"]].append(r["trade_date"])
    out=[]
    for r in pool:
        end=next_date[r["rebalance_date"]]; last=last_daily.get(r["code"],"")
        if last and r["rebalance_date"] <= last < end:
            factor_last=max((x for x in factors_by[r["code"]] if x<=end),default="")
            out.append({"event_id":f"{r['rebalance_date']}|{r['code']}|{r['sleeve_id']}","code":r["code"],"sleeve_id":r["sleeve_id"],"rebalance_date":r["rebalance_date"],"scheduled_period_end":end,"last_observed_daily_trade_date":last,"last_adjust_factor_date":factor_last,"terminal_status":"nontradable_after_last_observed_date_pending_corporate_action_terms","minute_source_policy":"no_post_terminal_bar_expected; do_not_fill_or_substitute","technical_rule_use":"blocked_until_total_return_action_terms_are_reconciled"})
    return out

def _ordinal(s:str)->int:
    from datetime import date
    try:return date.fromisoformat(s[:10]).toordinal()
    except ValueError:return -99999
def _float(v:Any)->float|None:
    try:return float(v)
    except (TypeError,ValueError):return None
def _csv(p:Path)->list[dict[str,str]]:
    with p.open(encoding="utf-8-sig",newline="") as h:return list(csv.DictReader(h))
def _write(p:Path,rows:list[dict[str,Any]])->None:
    fields=list(dict.fromkeys(k for r in rows for k in r)) or ["empty"]
    with p.open("w",encoding="utf-8-sig",newline="") as h:w=csv.DictWriter(h,fields);w.writeheader();w.writerows(rows)
def _now()->str:return datetime.now(timezone.utc).isoformat(timespec="seconds")
if __name__=="__main__":print(json.dumps(run_v5j_local_adjust_factor_corporate_action(),ensure_ascii=False,indent=2))
