from __future__ import annotations

import csv
import json
import math
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import pstdev
from typing import Any


OUT_DIR = Path("v5j_repaired_multisleeve_pit_pool") / "current"
DB_DIR = Path("数据库") / "processed" / "pre2021_repaired_multisleeve_pit_pool_v5"
START_DATE = "2013-01-01"
END_DATE = "2021-04-30"
MIN_HISTORY_OBSERVATIONS = 120

SLEEVES = {
    "bank": ("货币金融", "J66", "银行"),
    "utilities_electricity": ("电力、热力", "D44", "电力生产"),
    "highway_infrastructure": ("道路运输", "G54"),
    "port_rail_infrastructure": ("水上运输", "铁路运输", "G53", "G55"),
}


def run_v5j_repaired_multisleeve_pit_pool(
    root: Path = Path("."), *, fetch: bool = True
) -> dict[str, Any]:
    """Rebuild a dated predecessor pool; this intentionally does not backtest."""
    out = root / OUT_DIR
    cache = root / DB_DIR
    out.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)

    dates = _rebalance_dates(fetch)
    universe_rows, universe_audit = _historical_universe(dates, fetch)
    price_rows, price_audit = _daily_history(sorted({row["code"] for row in universe_rows}), fetch)
    pool_rows, coverage = _build_pool(universe_rows, price_rows)
    pit_audit = _pit_audit(universe_rows, pool_rows)
    corporate_action_gate = _corporate_action_gate(pool_rows)
    blockers = _blockers(pool_rows, corporate_action_gate, fetch)
    gate = _gate(pool_rows, corporate_action_gate, blockers)
    queue = _queue(gate["pm_gate_decision"])

    _write_csv(cache / "quarterly_rebalance_calendar.csv", dates)
    _write_csv(cache / "historical_industry_universe.csv", universe_rows)
    _write_csv(cache / "daily_price_valuation_history.csv", price_rows)
    _write_csv(cache / "repaired_multisleeve_pit_pool.csv", pool_rows)
    _write_csv(out / "v5j_repaired_pool_rebalance_calendar.csv", dates)
    _write_csv(out / "v5j_repaired_pool_historical_industry_universe.csv", universe_rows)
    _write_csv(out / "v5j_repaired_pool_price_coverage.csv", coverage)
    _write_csv(out / "v5j_repaired_pool_pit_audit.csv", pit_audit)
    _write_csv(out / "v5j_repaired_pool_source_audit.csv", universe_audit + price_audit)
    _write_csv(out / "v5j_repaired_pool_corporate_action_gate.csv", corporate_action_gate)
    _write_csv(out / "v5j_repaired_pool_blockers.csv", blockers)
    _write_csv(out / "v5j_repaired_pool_next_queue.csv", queue)
    _write_csv(out / "v5j_repaired_pool_pm_gate.csv", [gate])
    summary = {
        "created_at_utc": _now(),
        "task": "v5j_repaired_multisleeve_pit_pool",
        "status": gate["status"],
        "validation_window": f"{START_DATE}_to_{END_DATE}",
        "rebalance_date_count": len(dates),
        "historical_universe_row_count": len(universe_rows),
        "pool_row_count": len(pool_rows),
        "sleeves_with_eligible_rows": sorted({row["sleeve_id"] for row in pool_rows if row["pool_eligibility"] == "eligible_for_predecessor_pool"}),
        "corporate_action_total_return_ready": False,
        "full_v57f_factor_equivalent": False,
        "technical_rule_validation_started": False,
        "v57f_core_modified": False,
        "accepted": False,
        "network_fetch_started": fetch,
        "pm_gate_decision": gate["pm_gate_decision"],
    }
    _write_json(out / "v5j_repaired_pool_summary.json", summary)
    (out / "v5j_repaired_pool_report.md").write_text(
        _report(summary, gate, corporate_action_gate, blockers), encoding="utf-8"
    )
    (out / "v5j_repaired_pool_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")
    return summary


def _rebalance_dates(fetch: bool) -> list[dict[str, Any]]:
    if not fetch:
        return []
    import baostock as bs

    login = bs.login()
    if login.error_code != "0":
        return []
    try:
        rs = bs.query_trade_dates(start_date=START_DATE, end_date=END_DATE)
        trading: list[str] = []
        while rs.error_code == "0" and rs.next():
            rec = dict(zip(rs.fields, rs.get_row_data()))
            if rec.get("is_trading_day") == "1":
                trading.append(str(rec.get("calendar_date"))[:10])
    finally:
        bs.logout()
    selected: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()
    for day in trading:
        parsed = date.fromisoformat(day)
        key = (parsed.year, parsed.month)
        if parsed.month not in {1, 4, 7, 10} or key in seen:
            continue
        seen.add(key)
        selected.append({"rebalance_date": day, "calendar_rule": "first_trading_day_of_quarter", "data_scope": "pre2021_train_validation"})
    return selected


def _historical_universe(
    dates: list[dict[str, Any]], fetch: bool
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not fetch:
        return [], [{"audit_type": "industry_snapshot", "status": "not_run", "detail": "fetch disabled"}]
    import baostock as bs

    login = bs.login()
    if login.error_code != "0":
        return [], [{"audit_type": "industry_snapshot", "status": "login_failed", "detail": str(login.error_msg)}]
    rows: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    try:
        for item in dates:
            day = item["rebalance_date"]
            active = _active_stock_map(bs, day)
            rs = bs.query_stock_industry(date=day)
            matched = 0
            total = 0
            while rs.error_code == "0" and rs.next():
                total += 1
                rec = dict(zip(rs.fields, rs.get_row_data()))
                bs_code = str(rec.get("code") or "")
                active_rec = active.get(bs_code)
                if not active_rec:
                    continue
                sleeve = _sleeve_for_industry(str(rec.get("industry") or ""))
                if not sleeve:
                    continue
                name = str(active_rec.get("code_name") or rec.get("code_name") or "")
                if _is_special_treatment(name):
                    continue
                update_date = str(rec.get("updateDate") or "")[:10]
                if update_date and update_date > day:
                    continue
                rows.append({
                    "rebalance_date": day,
                    "code": _bs_to_jq(bs_code),
                    "bs_code": bs_code,
                    "code_name": name,
                    "sleeve_id": sleeve,
                    "industry_snapshot": str(rec.get("industry") or ""),
                    "industry_update_date": update_date,
                    "industry_visibility_status": "pass_historical_snapshot",
                    "trade_status": str(active_rec.get("tradeStatus") or ""),
                    "universe_source": "baostock_query_stock_industry_and_query_all_stock_as_of_rebalance_date",
                })
                matched += 1
            audit.append({
                "audit_type": "industry_snapshot",
                "rebalance_date": day,
                "source": "baostock",
                "source_row_count": total,
                "eligible_security_count": matched,
                "status": "pass" if matched else "empty",
                "detail": "Historical industry snapshot joined to same-date tradable stock list; current membership was not backfilled.",
            })
    finally:
        bs.logout()
    return rows, audit


def _active_stock_map(bs: Any, day: str) -> dict[str, dict[str, str]]:
    rs = bs.query_all_stock(day)
    result: dict[str, dict[str, str]] = {}
    while rs.error_code == "0" and rs.next():
        rec = dict(zip(rs.fields, rs.get_row_data()))
        if str(rec.get("tradeStatus") or "") == "1":
            result[str(rec.get("code") or "")] = rec
    return result


def _daily_history(codes: list[str], fetch: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not fetch:
        return [], [{"audit_type": "daily_price_valuation", "status": "not_run", "detail": "fetch disabled"}]
    import baostock as bs

    login = bs.login()
    if login.error_code != "0":
        return [], [{"audit_type": "daily_price_valuation", "status": "login_failed", "detail": str(login.error_msg)}]
    rows: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    try:
        for index, code in enumerate(codes, start=1):
            rs = bs.query_history_k_data_plus(
                _jq_to_bs(code),
                "date,code,close,peTTM,pbMRQ,pcfNcfTTM,volume,amount,tradeStatus,isST",
                start_date="2012-06-01",
                end_date=END_DATE,
                frequency="d",
                adjustflag="3",
            )
            code_rows = []
            while rs.error_code == "0" and rs.next():
                rec = dict(zip(rs.fields, rs.get_row_data()))
                day = str(rec.get("date") or "")[:10]
                close = _float_or_none(rec.get("close"))
                if not day or close is None or close <= 0 or rec.get("tradeStatus") != "1":
                    continue
                code_rows.append({
                    "date": day,
                    "code": code,
                    "close": close,
                    "pe_ttm": _float_or_none(rec.get("peTTM")),
                    "pb_mrq": _float_or_none(rec.get("pbMRQ")),
                    "pcf_ncf_ttm": _float_or_none(rec.get("pcfNcfTTM")),
                    "volume": _float_or_none(rec.get("volume")),
                    "amount": _float_or_none(rec.get("amount")),
                    "is_st": str(rec.get("isST") or ""),
                    "price_adjustment": "raw_unadjusted_adjustflag_3",
                    "price_source": "baostock_query_history_k_data_plus_as_of_daily_record",
                    "valuation_visibility_status": "vendor_historical_daily_snapshot",
                })
            rows.extend(code_rows)
            audit.append({
                "audit_type": "daily_price_valuation",
                "code": code,
                "source": "baostock",
                "row_count": len(code_rows),
                "status": "pass" if code_rows else "empty",
                "detail": f"{index}/{len(codes)} raw price and dated valuation history retrieved.",
            })
    finally:
        bs.logout()
    return rows, audit


def _build_pool(universe: list[dict[str, Any]], prices: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_code: dict[str, list[dict[str, Any]]] = {}
    for row in prices:
        by_code.setdefault(row["code"], []).append(row)
    for series in by_code.values():
        series.sort(key=lambda row: row["date"])
    pool: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    for item in universe:
        series = by_code.get(item["code"], [])
        day = item["rebalance_date"]
        prior = [row for row in series if row["date"] <= day]
        current = prior[-1] if prior and prior[-1]["date"] == day else None
        window = prior[-MIN_HISTORY_OBSERVATIONS:]
        returns = _returns(window)
        history_ok = len(window) >= MIN_HISTORY_OBSERVATIONS and len(returns) >= MIN_HISTORY_OBSERVATIONS - 1
        st_ok = bool(current) and str(current.get("is_st") or "0") in {"0", ""}
        valuation_ok = bool(current) and _float_or_none(current.get("pb_mrq")) is not None
        eligible = bool(current) and history_ok and st_ok and valuation_ok
        pool.append({
            **item,
            "close": current.get("close") if current else "",
            "pb_mrq": current.get("pb_mrq") if current else "",
            "pe_ttm": current.get("pe_ttm") if current else "",
            "pcf_ncf_ttm": current.get("pcf_ncf_ttm") if current else "",
            "price_history_observations": len(window),
            "low_volatility_120d": round(pstdev(returns), 10) if len(returns) >= 2 else "",
            "low_vol_factor_visible_date": day if history_ok else "",
            "valuation_visible_date": day if valuation_ok else "",
            "financial_factor_scope": "pb_mrq_only_vendor_daily_snapshot; statement_quality_fields_not_yet_equivalent",
            "corporate_action_treatment": "not_ready_raw_unadjusted_price_only",
            "pool_eligibility": "eligible_for_predecessor_pool" if eligible else "ineligible_missing_price_history_or_valuation_or_st_filter",
        })
    for sleeve in SLEEVES:
        for day in sorted({row["rebalance_date"] for row in universe}):
            rows = [row for row in pool if row["sleeve_id"] == sleeve and row["rebalance_date"] == day]
            coverage.append({
                "rebalance_date": day,
                "sleeve_id": sleeve,
                "historical_industry_members": len(rows),
                "eligible_predecessor_pool_members": sum(row["pool_eligibility"] == "eligible_for_predecessor_pool" for row in rows),
                "status": "pass" if any(row["pool_eligibility"] == "eligible_for_predecessor_pool" for row in rows) else "empty",
            })
    return pool, coverage


def _pit_audit(universe: list[dict[str, Any]], pool: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in pool:
        industry_ok = item.get("industry_update_date", "") <= item["rebalance_date"]
        price_ok = item.get("valuation_visible_date", "") == item["rebalance_date"]
        rows.append({
            "rebalance_date": item["rebalance_date"],
            "code": item["code"],
            "sleeve_id": item["sleeve_id"],
            "industry_snapshot_pit": industry_ok,
            "tradability_pit": item.get("trade_status") == "1",
            "price_valuation_snapshot_pit": price_ok,
            "current_membership_backfill_used": False,
            "future_financial_statement_used": False,
            "status": "pass" if industry_ok and price_ok else "needs_review",
        })
    return rows


def _corporate_action_gate(pool: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{
        "gate_id": "PIT_CORPORATE_ACTION_TOTAL_RETURN",
        "scope": "2013-01-01_to_2021-04-30",
        "price_source": "BaoStock adjustflag=3 raw_unadjusted",
        "dividend_panel_available": False,
        "split_rights_panel_available": False,
        "total_return_validation_allowed": False,
        "status": "blocked",
        "detail": "Pool membership and raw-price low-vol fields are reconstructed, but a dated dividend/corporate-action ledger is required before total-return or full V57f-equivalent target validation.",
    }]


def _blockers(pool: list[dict[str, Any]], corporate: list[dict[str, Any]], fetch: bool) -> list[dict[str, Any]]:
    dates = {row["rebalance_date"] for row in pool}
    sleeves = {row["sleeve_id"] for row in pool if row["pool_eligibility"] == "eligible_for_predecessor_pool"}
    rows = []
    if not fetch or not dates:
        rows.append({"blocker_id": "historical_source_fetch_failed", "severity": "fatal", "detail": "No historical industry/price snapshot was built."})
    if set(SLEEVES) - sleeves:
        rows.append({"blocker_id": "one_or_more_sleeves_empty", "severity": "blocking", "detail": "At least one sleeve has no eligible historical rows on the rebuilt panel."})
    rows.append({"blocker_id": "pit_dividend_and_corporate_action_ledger_missing", "severity": "blocking_for_total_return_validation", "detail": corporate[0]["detail"]})
    rows.append({"blocker_id": "financial_statement_quality_fields_incomplete", "severity": "blocking_for_full_v57f_equivalence", "detail": "The new pool uses historical PB snapshots and low-vol history; cashflow, payout and quality statement panels still require report-visible-date reconstruction."})
    return rows


def _gate(pool: list[dict[str, Any]], corporate: list[dict[str, Any]], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    fatal = any(row["severity"] == "fatal" for row in blockers)
    all_sleeves = set(SLEEVES).issubset({row["sleeve_id"] for row in pool if row["pool_eligibility"] == "eligible_for_predecessor_pool"})
    if fatal:
        return {"status": "blocked_historical_source_fetch_failed", "pm_gate_decision": "blocked_before_predecessor_pool"}
    if all_sleeves:
        return {"status": "historical_pool_membership_rebuilt_financial_total_return_gates_open", "pm_gate_decision": "admit_membership_and_price_pool_to_financial_pit_repair_only"}
    return {"status": "partial_historical_pool_rebuilt", "pm_gate_decision": "remain_data_gate_only"}


def _queue(decision: str) -> list[dict[str, Any]]:
    return [
        {"priority": 1, "task_id": "v5j_pit_dividend_corporate_action_ledger", "status": "ready", "reason": "Required before total-return validation."},
        {"priority": 2, "task_id": "v5j_statement_visible_date_factor_panel", "status": "ready", "reason": "Rebuild payout, OCF and quality fields from dated reports."},
        {"priority": 3, "task_id": "v5j_repaired_targets_2013_2021", "status": "blocked_until_p1_p2", "reason": "No target reconstruction before corporate-action and statement PIT fields pass."},
        {"priority": 4, "task_id": "v5i_frozen_technical_rule_independent_validation", "status": "blocked_until_repaired_targets", "reason": "Do not test any technical rule yet."},
    ]


def _sleeve_for_industry(industry: str) -> str:
    # Older CSRC labels share a broad electricity/gas/water prefix. Only the
    # terminal sub-industry can admit a name to the electricity sleeve.
    if "水的生产" in industry or "燃气生产" in industry or ("燃气及水" in industry and "电力、热力生产" not in industry):
        return ""
    for sleeve, markers in SLEEVES.items():
        if any(marker in industry for marker in markers):
            return sleeve
    return ""


def _returns(rows: list[dict[str, Any]]) -> list[float]:
    values = [float(row["close"]) for row in rows if _float_or_none(row.get("close"))]
    return [math.log(curr / prev) for prev, curr in zip(values, values[1:]) if prev > 0 and curr > 0]


def _is_special_treatment(name: str) -> bool:
    upper = name.upper().replace("*", "")
    return upper.startswith("ST") or "退" in name


def _bs_to_jq(code: str) -> str:
    return code[3:9] + (".XSHG" if code.startswith("sh.") else ".XSHE")


def _jq_to_bs(code: str) -> str:
    return ("sh." if code.endswith("XSHG") else "sz.") + code[:6]


def _float_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _report(summary: dict[str, Any], gate: dict[str, Any], corporate: list[dict[str, Any]], blockers: list[dict[str, Any]]) -> str:
    lines = [
        "# V5j Repaired Multi-sleeve PIT Pool",
        "",
        "- Window: `2013-01-01` to `2021-04-30`, training/independent-validation only.",
        "- Membership source: historical BaoStock industry snapshot plus same-day tradability; no current-membership backfill.",
        "- Price source: raw daily BaoStock records, with a 120-observation low-vol history gate.",
        f"- PM gate: `{gate['pm_gate_decision']}`.",
        "- This is a pool rebuild, not a V57f-equivalent backtest and not a technical-rule test.",
        "",
        "## Remaining gates",
        "",
    ]
    for row in corporate + blockers:
        lines.append(f"- `{row.get('gate_id') or row.get('blocker_id')}`: {row.get('detail')}")
    return "\n".join(lines) + "\n"


def _rules() -> str:
    return "\n".join([
        "# Execution Rules",
        "",
        "1. The 2013-2021-04-30 window is training/independent validation, never the formal 2021-05-01 to 2026-05-31 backtest.",
        "2. Historical industry snapshots and same-date tradability define membership; current industry membership cannot be backfilled.",
        "3. Raw prices are insufficient for total-return validation until dividends, splits and rights are PIT-repaired.",
        "4. Do not construct targets, rerun technical rules, modify V57f, or promote a model from this pool alone.",
        "",
    ])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    print(json.dumps(run_v5j_repaired_multisleeve_pit_pool(), ensure_ascii=False, indent=2))
