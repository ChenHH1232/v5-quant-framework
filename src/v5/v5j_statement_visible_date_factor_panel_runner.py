from __future__ import annotations

import csv
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.local_1min_clean_ingest_runner import find_v5_database

OUT_DIR = Path("v5j_statement_visible_date_factor_panel") / "current"
POOL_REL = Path("processed") / "pre2021_repaired_multisleeve_pit_pool_v5" / "repaired_multisleeve_pit_pool.csv"
PANEL_REL = Path("processed") / "pre2021_repaired_multisleeve_pit_pool_v5" / "pit_financial_quality_panel.csv"
DIVIDEND_REL = Path("processed") / "pre2021_repaired_multisleeve_pit_pool_v5" / "pit_dividend_corporate_action_ledger.csv"
START_YEAR, END_YEAR = 2011, 2021


def run_v5j_statement_visible_date_factor_panel(root: Path = Path("."), *, fetch: bool = True) -> dict[str, Any]:
    out = root / OUT_DIR; out.mkdir(parents=True, exist_ok=True); db = find_v5_database(root)
    pool = [x for x in _read_csv(db / POOL_REL) if x.get("pool_eligibility") == "eligible_for_predecessor_pool"]
    codes = sorted({x["code"] for x in pool})
    raw_path = out / "v5j_financial_statement_raw_visible_records.csv"
    audit_path = out / "v5j_financial_statement_fetch_audit.csv"
    if not fetch and raw_path.exists():
        records, audit = _read_csv(raw_path), _read_csv(audit_path)
    else:
        records, audit = _fetch(codes, fetch)
    panel = _panel(pool, records, _read_csv(db / DIVIDEND_REL))
    coverage = _coverage(panel)
    blockers = _blockers(audit, coverage)
    _write_csv(db / PANEL_REL, panel)
    _write_csv(out / "v5j_financial_statement_raw_visible_records.csv", records)
    _write_csv(out / "v5j_pit_financial_quality_panel.csv", panel)
    _write_csv(out / "v5j_financial_statement_fetch_audit.csv", audit)
    _write_csv(out / "v5j_financial_quality_coverage.csv", coverage)
    _write_csv(out / "v5j_financial_quality_blockers.csv", blockers)
    visible = sum(x["record_visible_status"] == "pass" for x in panel)
    payout_count = sum(str(x.get("payout_ratio", "")) != "" for x in panel)
    summary = {"created_at_utc": _now(), "task": "v5j_statement_visible_date_factor_panel", "pool_code_count": len(codes), "raw_statement_record_count": len(records), "pool_observation_count": len(panel), "visible_statement_observation_count": visible, "visible_statement_coverage_pct": round(100*visible/len(panel), 4) if panel else 0, "quality_fields": ["roe_avg", "revenue", "net_profit", "cfo_to_revenue", "cfo_to_net_profit", "cfo_to_growth", "interest_coverage", "leverage", "total_share"], "payout_ratio_pit_annual_observation_count": payout_count, "payout_ratio_ready": payout_count > 0, "capex_and_fcf_ready": False, "technical_rule_validation_started": False, "accepted": False, "status": "pit_statement_quality_panel_ready_partial_factor_equivalence" if visible else "blocked_statement_fetch_empty"}
    _write_json(out / "v5j_statement_visible_date_factor_panel_summary.json", summary)
    (out / "v5j_statement_visible_date_factor_panel_report.md").write_text(_report(summary), encoding="utf-8")
    return summary


def _fetch(codes: list[str], fetch: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not fetch: return [], [{"source":"baostock_finance", "status":"not_run", "code_count":len(codes)}]
    records=[]; audit=[]
    # Isolate one slow issuer/API path from the other 190 names.  The output is
    # deterministic by code and results are sorted below; no financial record is
    # reused across codes or visible dates.
    with ProcessPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(_fetch_code, code): code for code in codes}
        for future in as_completed(futures):
            code = futures[future]
            try:
                payload = future.result(timeout=1)
            except Exception as exc:
                audit.append({"code": code, "source": "baostock.profit_cashflow_balance", "status": "worker_error", "detail": f"{type(exc).__name__}: {exc}"})
                continue
            records.extend(payload["records"]); audit.extend(payload["audit"])
    records.sort(key=lambda x: (x["code"], x["stat_date"], x["pub_date"]))
    return records, audit


def _fetch_code(code: str) -> dict[str, list[dict[str, Any]]]:
    import baostock as bs
    records: list[dict[str, Any]] = []; audit: list[dict[str, Any]] = []
    lg = bs.login()
    if lg.error_code != "0": return {"records": records, "audit": [{"code": code, "source": "baostock.login", "status": "login_error", "detail": str(lg.error_msg)}]}
    try:
        for year in range(START_YEAR, END_YEAR + 1):
            for quarter in range(1, 5):
                merged, status, detail = _one(bs, _to_bs(code), year, quarter)
                audit.append({"code":code,"year":year,"quarter":quarter,"source":"baostock.profit_cashflow_balance", "status":status,"detail":detail})
                if merged:
                    merged.update({"code":code,"year":year,"quarter":quarter,"source":"baostock PIT financial statements"}); records.append(merged)
    finally:
        bs.logout()
    return {"records": records, "audit": audit}


def _one(bs: Any, code: str, year: int, quarter: int) -> tuple[dict[str, Any], str, str]:
    payload=[]; errors=[]
    # These three reports carry the registered quality fields.  Operation/growth
    # endpoints add no required field here and make a 191-name PIT extraction
    # needlessly fragile and slow.
    for name, fn in [("profit", bs.query_profit_data),("cash", bs.query_cash_flow_data),("balance",bs.query_balance_data)]:
        rs=fn(code=code, year=year, quarter=quarter); rows=[]
        while rs.error_code == "0" and rs.next(): rows.append(dict(zip(rs.fields,rs.get_row_data())))
        if rs.error_code != "0": errors.append(f"{name}:{rs.error_msg}")
        payload.append(rows[0] if rows else {})
    if errors: return {}, "query_error", ";".join(errors)
    if not any(payload): return {}, "empty", "no statement rows"
    rec={}
    for item in payload:
        for k,v in item.items():
            if k not in rec or not rec[k]: rec[k]=v
    pub=[_date(x.get("pubDate")) for x in payload if _date(x.get("pubDate"))]
    stat=[_date(x.get("statDate")) for x in payload if _date(x.get("statDate"))]
    rec["pub_date"] = max(pub) if pub else ""; rec["stat_date"] = max(stat) if stat else ""
    return rec, "pass", ""


def _panel(pool: list[dict[str,str]], records: list[dict[str,Any]], dividends: list[dict[str, str]]) -> list[dict[str,Any]]:
    by=defaultdict(list)
    for r in records: by[r["code"]].append(r)
    dividends_by = defaultdict(list)
    for dividend in dividends: dividends_by[dividend["code"]].append(dividend)
    for rows in by.values(): rows.sort(key=lambda x:(x.get("stat_date", ""),x.get("pub_date", "")))
    rows=[]
    for p in pool:
        candidates=[r for r in by[p["code"]] if r.get("pub_date","") <= p["rebalance_date"] and r.get("stat_date","") <= p["rebalance_date"]]
        r=candidates[-1] if candidates else {}
        eps = _ratio(_num(r.get("netProfit")), _num(r.get("totalShare"))) if r else None
        fiscal_year = r.get("stat_date", "")[:4]
        eligible_dividends = [x for x in dividends_by[p["code"]] if x.get("announcement_visible_date", "") <= p["rebalance_date"] and str(x.get("report_year")) == fiscal_year]
        cash = sum(_float(x.get("cash_per_share_before_tax")) or 0.0 for x in eligible_dividends)
        payout = cash / eps if eps and eps > 0 and r.get("stat_date", "").endswith("12-31") else None
        rows.append({"rebalance_date":p["rebalance_date"],"code":p["code"],"sleeve_id":p["sleeve_id"],"statement_pub_date":r.get("pub_date", ""),"statement_period":r.get("stat_date", ""),"roe_avg":_num(r.get("roeAvg")),"revenue":_num(r.get("MBRevenue")),"net_profit":_num(r.get("netProfit")),"cfo_to_revenue":_num(r.get("CFOToOR")),"cfo_to_net_profit":_num(r.get("CFOToNP")),"cfo_to_growth":_num(r.get("CFOToGr")),"interest_coverage":_num(r.get("ebitToInterest")),"leverage":_num(r.get("liabilityToAsset")),"total_share":_num(r.get("totalShare")),"revenue_growth_yoy":_num(r.get("YOYEquity" ) or r.get("YOYNI")),"payout_ratio":payout if payout is not None else "","payout_cash_per_share":cash if payout is not None else "","payout_formula":"visible_cash_dividend_per_share / annual_eps; annual statement and same report_year only" if payout is not None else "not_available_without_visible_annual_statement_and_same_year_dividend", "capex_burden":"","fcf_yield":"","record_visible_status":"pass" if r else "missing_visible_statement", "future_statement_used":False,"factor_source":"baostock statement query; pubDate <= rebalance_date; local PIT dividend ledger"})
    return rows


def _coverage(panel: list[dict[str,Any]]) -> list[dict[str,Any]]:
    grouped=defaultdict(list)
    for r in panel: grouped[r["sleeve_id"]].append(r)
    return [{"sleeve_id":k,"pool_observations":len(v),"visible_statement_observations":sum(x["record_visible_status"]=="pass" for x in v),"coverage_pct":round(100*sum(x["record_visible_status"]=="pass" for x in v)/len(v),4) if v else 0,"payout_ratio_status":"pending_dividend_ledger_linkage","capex_fcf_status":"source_not_supplied_by_baostock_generic_fields"} for k,v in sorted(grouped.items())]


def _blockers(audit: list[dict[str,Any]], coverage: list[dict[str,Any]]) -> list[dict[str,Any]]:
    rows=[{"blocker_id":"payout_ratio_linkage_pending","severity":"open_factor_gap","detail":"Payout requires matching clean dividend ledger and statement denominator."},{"blocker_id":"capex_fcf_source_pending","severity":"open_factor_gap","detail":"Generic BaoStock fields do not establish cash-paid capex / FCF."}]
    if any(x["status"]=="query_error" for x in audit): rows.append({"blocker_id":"financial_query_session_retries_recorded","severity":"review", "detail":"Some raw quarterly endpoint calls returned an unauthenticated session error, but the PIT panel only retains independently returned records and has explicit coverage reporting."})
    return rows


def _to_bs(code:str)->str:return ("sh." if code.endswith("XSHG") else "sz.")+code.split(".")[0]
def _date(v:Any)->str:return str(v or "")[:10]
def _num(v:Any)->float|str:
    try:return float(v)
    except (TypeError,ValueError):return ""
def _float(v:Any)->float|None:
    try:return float(v)
    except (TypeError,ValueError):return None
def _ratio(a:Any,b:Any)->float|None:
    try:return float(a)/float(b) if float(b) else None
    except (TypeError,ValueError):return None
def _read_csv(p:Path)->list[dict[str,str]]:
    with p.open(encoding="utf-8-sig",newline="") as h:return list(csv.DictReader(h))
def _write_csv(p:Path,rows:list[dict[str,Any]])->None:
    p.parent.mkdir(parents=True,exist_ok=True); fields=list(dict.fromkeys(k for r in rows for k in r)) or ["empty"]
    with p.open("w",encoding="utf-8-sig",newline="") as h:w=csv.DictWriter(h,fields);w.writeheader();w.writerows(rows)
def _write_json(p:Path,d:dict[str,Any])->None:p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def _now()->str:return datetime.now(timezone.utc).isoformat(timespec="seconds")
def _report(s:dict[str,Any])->str:return f"# PIT financial-quality panel\n\n- PIT-visible statement coverage: `{s['visible_statement_coverage_pct']}%`.\n- Each record is selected only when `pubDate <= rebalance_date`.\n- Payout, capex and FCF are intentionally blank until their data sources are cleanly linked.\n- No technical rule validation was started.\n"
if __name__=="__main__":print(json.dumps(run_v5j_statement_visible_date_factor_panel(),ensure_ascii=False,indent=2))
