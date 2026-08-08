from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.local_1min_clean_ingest_runner import find_v5_database

OUT_DIR = Path("v5j_pit_dividend_corporate_action_ledger") / "current"
POOL_REL = Path("processed") / "pre2021_repaired_multisleeve_pit_pool_v5" / "repaired_multisleeve_pit_pool.csv"
LEDGER_REL = Path("processed") / "pre2021_repaired_multisleeve_pit_pool_v5" / "pit_dividend_corporate_action_ledger.csv"
START_YEAR, END_YEAR = 2012, 2021


def run_v5j_pit_dividend_corporate_action_ledger(root: Path = Path("."), *, fetch: bool = True) -> dict[str, Any]:
    out = root / OUT_DIR; out.mkdir(parents=True, exist_ok=True)
    db = find_v5_database(root)
    pool = [r for r in _read_csv(db / POOL_REL) if r.get("pool_eligibility") == "eligible_for_predecessor_pool"]
    codes = sorted({r["code"] for r in pool})
    ledger, fetch_audit = _fetch(codes, fetch)
    pit = _pit_eligibility(pool, ledger)
    reconciliation = _reconciliation(ledger, fetch_audit)
    blockers = _blockers(ledger, fetch_audit)
    _write_csv(db / LEDGER_REL, ledger)
    _write_csv(out / "v5j_pit_dividend_corporate_action_ledger.csv", ledger)
    _write_csv(out / "v5j_pit_dividend_fetch_audit.csv", fetch_audit)
    _write_csv(out / "v5j_pit_dividend_rebalance_visibility.csv", pit)
    _write_csv(out / "v5j_pit_dividend_corporate_action_reconciliation.csv", reconciliation)
    _write_csv(out / "v5j_pit_dividend_corporate_action_blockers.csv", blockers)
    complete = bool(ledger) and not any(r["severity"] == "fatal" for r in blockers)
    summary = {"created_at_utc": _now(), "task": "v5j_pit_dividend_corporate_action_ledger", "pool_code_count": len(codes), "ledger_event_count": len(ledger), "cash_dividend_event_count": sum(r["corporate_action_type"] == "cash_dividend" for r in ledger), "stock_action_event_count": sum(r["corporate_action_type"] == "stock_dividend_or_reserve_to_stock" for r in ledger), "rights_issue_explicitly_handled": False, "total_return_target_ready": False, "pit_visibility_panel_ready": complete, "technical_rule_validation_started": False, "accepted": False, "status": "pit_dividend_ledger_ready_rights_action_gate_open" if complete else "blocked_dividend_source_incomplete"}
    _write_json(out / "v5j_pit_dividend_corporate_action_summary.json", summary)
    (out / "v5j_pit_dividend_corporate_action_report.md").write_text(_report(summary), encoding="utf-8")
    return summary


def _fetch(codes: list[str], fetch: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not fetch: return [], [{"source": "baostock.query_dividend_data", "status": "not_run", "code_count": len(codes)}]
    import baostock as bs
    login = bs.login()
    if login.error_code != "0": return [], [{"source": "baostock.login", "status": "error", "detail": str(login.error_msg)}]
    ledger: list[dict[str, Any]] = []; audit: list[dict[str, Any]] = []
    try:
        for code in codes:
            for year in range(START_YEAR, END_YEAR + 1):
                rs = bs.query_dividend_data(_to_bs(code), year=year, yearType="report"); rows = []
                while rs.error_code == "0" and rs.next(): rows.append(dict(zip(rs.fields, rs.get_row_data())))
                audit.append({"source": "baostock.query_dividend_data", "code": code, "report_year": year, "status": "pass" if rs.error_code == "0" else "query_error", "row_count": len(rows), "detail": "" if rs.error_code == "0" else str(rs.error_msg)})
                for rec in rows:
                    event = _event(code, year, rec)
                    if event: ledger.append(event)
    finally: bs.logout()
    ledger.sort(key=lambda x: (x["code"], x["announcement_visible_date"], x["report_year"]))
    return ledger, audit


def _event(code: str, year: int, rec: dict[str, str]) -> dict[str, Any] | None:
    cash = _float(rec.get("dividCashPsBeforeTax")); stock = _float(rec.get("dividStockMarketDate")); reserve = _float(rec.get("dividReserveToStock"))
    if cash is None and stock is None and reserve is None: return None
    visible = _first(rec, "dividPlanAnnounceDate", "dividAgmPumDate", "dividPlanDate", "dividRegistDate", "dividOperateDate", "dividPayDate")
    if not visible: return None
    action = "cash_dividend" if (cash or 0) > 0 else "stock_dividend_or_reserve_to_stock"
    return {"event_id": f"{code}|{year}|{visible}|{rec.get('dividRegistDate','')}", "code": code, "report_year": year, "announcement_visible_date": visible, "plan_announce_date": _date(rec.get("dividPlanAnnounceDate")), "agm_date": _date(rec.get("dividAgmPumDate")), "registration_date": _date(rec.get("dividRegistDate")), "ex_or_operate_date": _date(rec.get("dividOperateDate")), "pay_date": _date(rec.get("dividPayDate")), "cash_per_share_before_tax": cash if cash is not None else "", "cash_per_share_after_tax": _float(rec.get("dividCashPsAfterTax")) or "", "stock_dividend_per_share": stock if stock is not None else "", "reserve_to_stock_per_share": reserve if reserve is not None else "", "corporate_action_type": action, "source": "baostock.query_dividend_data", "raw_record_available": True, "rights_issue_status": "not_provided_by_dividend_endpoint; explicit_rights_action_gate_remains_open", "reconciliation_status": "source_recorded_not_total_return_adjusted"}


def _pit_eligibility(pool: list[dict[str, str]], ledger: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by = {}
    for x in ledger: by.setdefault(x["code"], []).append(x)
    rows = []
    for p in pool:
        visible = [x for x in by.get(p["code"], []) if x["announcement_visible_date"] <= p["rebalance_date"]]
        rows.append({"rebalance_date": p["rebalance_date"], "code": p["code"], "sleeve_id": p["sleeve_id"], "visible_event_count": len(visible), "latest_visible_announcement_date": max((x["announcement_visible_date"] for x in visible), default=""), "future_event_used": False, "pit_status": "pass"})
    return rows


def _reconciliation(ledger: list[dict[str, Any]], audit: list[dict[str, Any]]) -> list[dict[str, Any]]:
    status = Counter(r["status"] for r in audit)
    return [{"source": "baostock.query_dividend_data", "queried_code_year_count": len(audit), "query_pass_count": status.get("pass", 0), "ledger_event_count": len(ledger), "cash_events": sum(x["corporate_action_type"] == "cash_dividend" for x in ledger), "stock_actions": sum(x["corporate_action_type"] != "cash_dividend" for x in ledger), "total_return_reconciled": False, "reason": "Rights issues and price adjustment reconciliation are separate explicit gates."}]


def _blockers(ledger: list[dict[str, Any]], audit: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [{"blocker_id": "rights_issue_and_price_adjustment_reconciliation_pending", "severity": "blocks_total_return_target", "detail": "Dividend endpoint does not establish complete rights/split-adjusted total-return history."}]
    if not ledger: rows.append({"blocker_id": "dividend_fetch_empty", "severity": "fatal", "detail": "No dividend/corporate-action ledger events were returned."})
    if any(x["status"] != "pass" for x in audit): rows.append({"blocker_id": "dividend_query_incomplete", "severity": "fatal", "detail": "At least one code-year query failed."})
    return rows


def _to_bs(code: str) -> str: return ("sh." if code.endswith("XSHG") else "sz.") + code.split(".")[0]
def _date(v: Any) -> str: return str(v or "")[:10]
def _first(rec: dict[str, str], *names: str) -> str: return next((_date(rec.get(n)) for n in names if _date(rec.get(n))), "")
def _float(v: Any) -> float | None:
    try: return float(v)
    except (TypeError, ValueError): return None
def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as h: return list(csv.DictReader(h))
def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(dict.fromkeys(k for x in rows for k in x)) or ["empty"]; path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as h: w=csv.DictWriter(h, fields); w.writeheader(); w.writerows(rows)
def _write_json(path: Path, data: dict[str, Any]) -> None: path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
def _now() -> str: return datetime.now(timezone.utc).isoformat(timespec="seconds")
def _report(s: dict[str, Any]) -> str: return f"# PIT dividend / corporate-action ledger\n\n- Events: `{s['ledger_event_count']}`.\n- PIT visibility is recorded at every dated pool observation.\n- This is not a total-return reconstruction: rights issues and price-adjustment reconciliation remain open.\n- No technical rule validation was started.\n"
if __name__ == "__main__": print(json.dumps(run_v5j_pit_dividend_corporate_action_ledger(), ensure_ascii=False, indent=2))
