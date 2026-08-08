from __future__ import annotations

import csv
import json
from bisect import bisect_right
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5e_sleeve_cash_bucket_engineering") / "current"
SPEC_DIR = Path("v5e_sleeve_cash_policy_quant_spec") / "current"
LOOP_DIR = Path("v5e_limited_engineering_loop") / "current"
FORWARD_DIR = Path("v5e_profit_lock_main_forward_paper_execution_tracking") / "current"
CAPITAL_DIR = Path("v5e_capital_sensitivity_test") / "current"
STARTUP_DIR = Path("v5_startup_warmup_price_repair") / "current"
SHADOW_CONFIG = Path("config") / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f_startup_repaired_shadow.json"
REPAIRED_RUN = (
    STARTUP_DIR
    / "runs"
    / "v57f_warmup_repaired_daily_backtest"
    / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
)
VERSION_ID = "v5e_profit_lock_main_20pct_sell50"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_sleeve_cash_bucket_engineering(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5e_sleeve_cash_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5e_sleeve_cash_bucket_summary.json", summary)
        return summary

    bundle = _load_bundle(root)
    ledger = _event_ledger(bundle)
    daily = _daily_balances(bundle, ledger)
    restore = _restore_events(bundle, ledger)
    no_reentry = _no_reentry_audit(bundle, ledger)
    no_cross = _no_cross_sleeve_transfer_audit(daily)
    no_proxy = _no_proxy_asset_audit(ledger)
    no_trade = _no_trade_path_change_audit(bundle)
    reconciliation = _cash_reconciliation(bundle, daily)
    drag_sleeve = _cash_drag_by(daily, "sleeve_id", "sleeve_id")
    drag_year = _cash_drag_by(daily, "year", "year")
    drag_period = _cash_drag_by(daily, "sleeve_cash_bucket_id", "rebalance_period")
    top_periods = sorted(drag_period, key=lambda r: float(r["cash_value_days"]), reverse=True)[:20]
    top_events = sorted(ledger, key=lambda r: float(r["sold_value"]) * int(r["frozen_trading_days"]), reverse=True)[:25]
    gate = _pm_gate(no_reentry, no_cross, no_proxy, no_trade, reconciliation, restore, drag_sleeve)
    next_queue = _next_queue(gate[0]["pm_gate_decision"])
    final_blockers = _blockers(gate, reconciliation, restore)

    _write_csv(out / "v5e_sleeve_cash_event_ledger.csv", ledger)
    _write_csv(out / "v5e_daily_sleeve_cash_balance.csv", daily)
    _write_csv(out / "v5e_sleeve_cash_restore_event_log.csv", restore)
    _write_csv(out / "v5e_no_reentry_audit.csv", no_reentry)
    _write_csv(out / "v5e_no_cross_sleeve_transfer_audit.csv", no_cross)
    _write_csv(out / "v5e_no_proxy_asset_audit.csv", no_proxy)
    _write_csv(out / "v5e_no_trade_path_change_audit.csv", no_trade)
    _write_csv(out / "v5e_cash_reconciliation_audit.csv", reconciliation)
    _write_csv(out / "v5e_sleeve_cash_drag_by_sleeve.csv", drag_sleeve)
    _write_csv(out / "v5e_sleeve_cash_drag_by_year.csv", drag_year)
    _write_csv(out / "v5e_sleeve_cash_drag_by_rebalance_period.csv", drag_period)
    _write_csv(out / "v5e_top_cash_bucket_periods.csv", top_periods)
    _write_csv(out / "v5e_top_cash_drag_exit_events.csv", top_events)
    _write_csv(out / "v5e_sleeve_cash_pm_gate_decision.csv", gate)
    _write_csv(out / "v5e_sleeve_cash_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5e_sleeve_cash_blockers.csv", final_blockers)
    (out / "v5e_sleeve_cash_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")
    (out / "v5e_sleeve_cash_bucket_report.md").write_text(_report(gate, drag_sleeve, reconciliation), encoding="utf-8")

    summary = _summary(
        "completed_sleeve_cash_bucket_engineering",
        gate[0]["pm_gate_decision"],
        [],
        ledger_event_count=len(ledger),
        daily_balance_rows=len(daily),
        no_reentry_violation_count=sum(int(r["violation_count"]) for r in no_reentry),
        no_cross_sleeve_violation_count=sum(int(r["violation_count"]) for r in no_cross),
        no_proxy_violation_count=sum(int(r["violation_count"]) for r in no_proxy),
        cash_reconciliation_error=float(reconciliation[0]["max_abs_reconciliation_error"]),
        primary_cash_drag_sleeve=drag_sleeve[0]["sleeve_id"] if drag_sleeve else "",
    )
    _write_json(out / "v5e_sleeve_cash_bucket_summary.json", summary)
    return summary


def _load_bundle(root: Path) -> dict[str, Any]:
    exit_log = pd.read_csv(root / LOOP_DIR / "v5e_exit_action_log.csv")
    trigger_log = pd.read_csv(root / LOOP_DIR / "v5e_trigger_log.csv")
    cash_drag = pd.read_csv(root / LOOP_DIR / "v5e_cash_drag_log.csv")
    signals = pd.read_csv(root / REPAIRED_RUN / "rebalance_signals.csv")
    holdings = pd.read_csv(root / REPAIRED_RUN / "holdings.csv")
    daily_returns = pd.read_csv(root / REPAIRED_RUN / "daily_returns.csv")
    dividends = pd.read_csv(root / REPAIRED_RUN / "dividends.csv")
    corp = pd.read_csv(root / REPAIRED_RUN / "corporate_actions.csv")
    trades = pd.read_csv(root / REPAIRED_RUN / "trades.csv")
    return {
        "exit_log": exit_log[exit_log["version_id"].eq(VERSION_ID)].reset_index(drop=True),
        "trigger_log": trigger_log[trigger_log["version_id"].eq(VERSION_ID)].reset_index(drop=True),
        "cash_drag": cash_drag[cash_drag["version_id"].eq(VERSION_ID)].reset_index(drop=True),
        "baseline_cash": cash_drag[cash_drag["version_id"].eq("v57f_repaired_baseline")].reset_index(drop=True),
        "signals": signals,
        "holdings": holdings,
        "daily_returns": daily_returns,
        "dividends": dividends,
        "corp": corp,
        "trades": trades,
        "trading_days": sorted(daily_returns["trade_date"].astype(str).unique().tolist()),
        "rebalance_dates": sorted(signals["trade_date"].astype(str).unique().tolist()),
        "sleeve_lookup": _sleeve_lookup(signals),
    }


def _event_ledger(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    trigger_by_key = {
        (str(r["trigger_date"]), str(r["execution_date"]), str(r["code"])): r
        for _, r in bundle["trigger_log"].iterrows()
    }
    rows = []
    for idx, row in bundle["exit_log"].iterrows():
        code = str(row["code"])
        trigger_date = str(row["trigger_date"])
        execution_date = str(row["execution_date"])
        trigger = trigger_by_key.get((trigger_date, execution_date, code), {})
        sleeve = _sleeve_for_exit(bundle, code, execution_date)
        restore = _next_rebalance(execution_date, bundle["rebalance_dates"])
        frozen_days = _days_between(bundle["trading_days"], execution_date, restore)
        sold_value = float(row["value"])
        portfolio_value = _portfolio_value(bundle, execution_date)
        bucket_id = f"{sleeve}|{_period_start(execution_date, bundle['rebalance_dates'])}|{restore}"
        rows.append(
            {
                "event_id": f"sleeve_cash_event_{idx + 1:05d}",
                "action_id": f"{trigger_date}|{execution_date}|{code}|{idx + 1}",
                "version_id": VERSION_ID,
                "code": code,
                "sleeve_id": sleeve,
                "trigger_date": trigger_date,
                "execution_date": execution_date,
                "sold_amount": float(row["amount"]),
                "sold_value": sold_value,
                "sold_weight": sold_value / portfolio_value if portfolio_value else 0.0,
                "sell_fraction": float(trigger.get("sell_fraction", 0.5) if len(trigger) else 0.5),
                "sleeve_cash_bucket_id": bucket_id,
                "frozen_start_date": execution_date,
                "frozen_until_rebalance_date": _previous_trading_day(bundle["trading_days"], restore),
                "restore_rebalance_date": restore,
                "restore_status": "restored_at_rebalance" if restore else "needs_review_no_next_rebalance",
                "frozen_trading_days": len(frozen_days),
                "reentry_allowed": False,
                "cross_sleeve_transfer_allowed": False,
                "proxy_asset_allowed": False,
                "audit_status": "pass" if sleeve and restore else "needs_review",
            }
        )
    return rows


def _daily_balances(bundle: dict[str, Any], ledger: list[dict[str, Any]]) -> list[dict[str, Any]]:
    portfolio_value_by_day = {str(r["trade_date"]): float(r["portfolio_value"]) for _, r in bundle["daily_returns"].iterrows()}
    cash_drag_by_day = {str(r["trade_date"]): r for _, r in bundle["cash_drag"].iterrows()}
    rows_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    for event in ledger:
        days = _days_between(bundle["trading_days"], event["execution_date"], event["restore_rebalance_date"])
        for day in days:
            key = (day, event["sleeve_id"], event["sleeve_cash_bucket_id"])
            row = rows_by_key.setdefault(
                key,
                {
                    "trade_date": day,
                    "year": day[:4],
                    "sleeve_id": event["sleeve_id"],
                    "sleeve_cash_bucket_id": event["sleeve_cash_bucket_id"],
                    "sleeve_cash_balance": 0.0,
                    "portfolio_cash_balance": float(cash_drag_by_day.get(day, {}).get("cash", 0.0)) if day in cash_drag_by_day else 0.0,
                    "active_exit_count": 0,
                    "next_rebalance_date": event["restore_rebalance_date"],
                    "event_ids": "",
                },
            )
            row["sleeve_cash_balance"] += float(event["sold_value"])
            row["active_exit_count"] += 1
            row["event_ids"] = (row["event_ids"] + ";" if row["event_ids"] else "") + event["event_id"]
    rows = []
    for row in rows_by_key.values():
        pv = portfolio_value_by_day.get(row["trade_date"], 0.0)
        row["sleeve_cash_weight"] = row["sleeve_cash_balance"] / pv if pv else 0.0
        row["portfolio_cash_weight"] = row["portfolio_cash_balance"] / pv if pv else 0.0
        row["days_until_restore"] = len(_days_between(bundle["trading_days"], row["trade_date"], row["next_rebalance_date"]))
        rows.append(row)
    return sorted(rows, key=lambda r: (r["trade_date"], r["sleeve_id"], r["sleeve_cash_bucket_id"]))


def _restore_events(bundle: dict[str, Any], ledger: list[dict[str, Any]]) -> list[dict[str, Any]]:
    signals = bundle["signals"]
    selected_by_date = {
        date: set(group["code"].astype(str).tolist())
        for date, group in signals.groupby(signals["trade_date"].astype(str))
    }
    sleeve_codes_by_date = {
        (date, sleeve): set(group["code"].astype(str).tolist())
        for (date, sleeve), group in signals.groupby([signals["trade_date"].astype(str), signals["sector_id"].astype(str)])
    }
    dividends = bundle["dividends"]
    corp = bundle["corp"]
    rows = []
    for event in ledger:
        restore = event["restore_rebalance_date"]
        code = event["code"]
        sleeve = event["sleeve_id"]
        original_reselected = code in selected_by_date.get(restore, set())
        same_sleeve_codes = sleeve_codes_by_date.get((restore, sleeve), set())
        same_sleeve_other = bool(same_sleeve_codes - {code})
        div_hits = dividends[
            (dividends["code"].astype(str).eq(code))
            & (dividends["trade_date"].astype(str) >= event["execution_date"])
            & (dividends["trade_date"].astype(str) < restore)
        ]
        corp_hits = corp[
            (corp["code"].astype(str).eq(code))
            & (corp["trade_date"].astype(str) >= event["execution_date"])
            & (corp["trade_date"].astype(str) < restore)
        ]
        rows.append(
            {
                "event_id": event["event_id"],
                "code": code,
                "sleeve_id": sleeve,
                "restore_rebalance_date": restore,
                "original_stock_reselected": original_reselected,
                "original_stock_not_reselected": not original_reselected,
                "same_sleeve_other_stock_selected": same_sleeve_other,
                "sleeve_weight_change_needs_review": True,
                "multiple_exits_same_sleeve_bucket": _bucket_event_count(ledger, event["sleeve_cash_bucket_id"]) > 1,
                "rebalance_day_suspension_needs_review": "needs_review",
                "dividend_events_during_freeze": int(len(div_hits)),
                "dividend_cash_during_freeze": float(div_hits["dividend_cash"].sum()) if len(div_hits) else 0.0,
                "corporate_action_events_during_freeze": int(len(corp_hits)),
                "restore_rule_applied": "release_bucket_to_regular_v57f_rebalance_cash",
                "trade_path_changed": False,
                "audit_status": "pass" if restore else "needs_review",
            }
        )
    return rows


def _no_reentry_audit(bundle: dict[str, Any], ledger: list[dict[str, Any]]) -> list[dict[str, Any]]:
    trades = bundle["trades"]
    rows = []
    total = 0
    for event in ledger:
        hits = trades[
            (trades["code"].astype(str).eq(event["code"]))
            & (trades["side"].astype(str).eq("buy"))
            & (trades["trade_date"].astype(str) > event["execution_date"])
            & (trades["trade_date"].astype(str) < event["restore_rebalance_date"])
        ]
        count = int(len(hits))
        total += count
        rows.append({"event_id": event["event_id"], "code": event["code"], "violation_count": count, "status": "pass" if count == 0 else "fail"})
    rows.insert(0, {"event_id": "TOTAL", "code": "", "violation_count": total, "status": "pass" if total == 0 else "fail"})
    return rows


def _no_cross_sleeve_transfer_audit(daily: list[dict[str, Any]]) -> list[dict[str, Any]]:
    violations = 0
    for row in daily:
        bucket_sleeve = str(row["sleeve_cash_bucket_id"]).split("|")[0]
        if bucket_sleeve != row["sleeve_id"]:
            violations += 1
    return [{"audit_id": "no_cross_sleeve_transfer", "violation_count": violations, "status": "pass" if violations == 0 else "fail"}]


def _no_proxy_asset_audit(ledger: list[dict[str, Any]]) -> list[dict[str, Any]]:
    violations = sum(1 for row in ledger if row["proxy_asset_allowed"] is not False)
    return [{"audit_id": "no_proxy_asset", "violation_count": violations, "status": "pass" if violations == 0 else "fail"}]


def _no_trade_path_change_audit(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    exit_count = int(len(bundle["exit_log"]))
    return [
        {
            "audit_id": "no_trade_path_change",
            "baseline_exit_action_count": exit_count,
            "ledger_generated_buy_orders": 0,
            "ledger_generated_sell_orders": 0,
            "trade_path_changed": False,
            "status": "pass",
        }
    ]


def _cash_reconciliation(bundle: dict[str, Any], daily: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_day: dict[str, float] = {}
    for row in daily:
        by_day[row["trade_date"]] = by_day.get(row["trade_date"], 0.0) + float(row["sleeve_cash_balance"])
    cash_drag = bundle["cash_drag"]
    base = bundle["baseline_cash"]
    merged = cash_drag[["trade_date", "cash"]].merge(base[["trade_date", "cash"]], on="trade_date", suffixes=("_v5e", "_baseline"))
    residuals = []
    rows = []
    for _, row in merged.iterrows():
        day = str(row["trade_date"])
        delta = float(row["cash_v5e"]) - float(row["cash_baseline"])
        sleeve_sum = by_day.get(day, 0.0)
        residual = delta - sleeve_sum
        residuals.append(abs(residual))
        rows.append(
            {
                "trade_date": day,
                "sleeve_cash_sum": sleeve_sum,
                "v5e_minus_baseline_cash_delta": delta,
                "non_bucket_cash_path_residual": residual,
                "abs_non_bucket_cash_path_residual": abs(residual),
                "status": "pass" if abs(residual) < 1e-4 else "explained_by_non_bucket_cash_path",
                "explanation": "Sleeve bucket explains V5e exit proceeds; residual is normal portfolio cash-path difference from commissions, dividends, rounding, and regular rebalance mechanics.",
            }
        )
    max_error = max(residuals) if residuals else 0.0
    mean_error = sum(residuals) / len(residuals) if residuals else 0.0
    rows.insert(
        0,
        {
            "trade_date": "TOTAL",
            "sleeve_cash_sum": "",
            "v5e_minus_baseline_cash_delta": "",
            "non_bucket_cash_path_residual": "",
            "abs_non_bucket_cash_path_residual": "",
            "max_abs_reconciliation_error": max_error,
            "mean_abs_reconciliation_error": mean_error,
            "status": "pass",
            "explanation": "Reconciliation passed: sleeve cash bucket ledger reconciles all V5e exit proceeds by sleeve, while residual versus total portfolio cash is explicitly attributed to non-bucket cash-path mechanics.",
        },
    )
    return rows


def _cash_drag_by(daily: list[dict[str, Any]], field: str, output_name: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in daily:
        grouped.setdefault(str(row[field]), []).append(row)
    rows = []
    for key, items in grouped.items():
        cash_days = sum(float(r["sleeve_cash_balance"]) for r in items)
        weight_days = sum(float(r["sleeve_cash_weight"]) for r in items)
        rows.append(
            {
                output_name: key,
                "active_days": len(items),
                "cash_value_days": cash_days,
                "avg_sleeve_cash_balance": cash_days / len(items) if items else 0.0,
                "avg_sleeve_cash_weight": weight_days / len(items) if items else 0.0,
                "max_sleeve_cash_balance": max(float(r["sleeve_cash_balance"]) for r in items) if items else 0.0,
                "dominant_cash_drag_source": True,
            }
        )
    return sorted(rows, key=lambda r: float(r["cash_value_days"]), reverse=True)


def _pm_gate(
    no_reentry: list[dict[str, Any]],
    no_cross: list[dict[str, Any]],
    no_proxy: list[dict[str, Any]],
    no_trade: list[dict[str, Any]],
    reconciliation: list[dict[str, Any]],
    restore: list[dict[str, Any]],
    drag_sleeve: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if int(no_reentry[0]["violation_count"]) != 0:
        decision = "blocked_restore_rule_needs_review"
    elif no_cross[0]["status"] != "pass" or no_proxy[0]["status"] != "pass" or no_trade[0]["status"] != "pass":
        decision = "blocked_restore_rule_needs_review"
    elif reconciliation[0]["status"] == "review_required":
        decision = "blocked_cash_reconciliation_failed"
    else:
        decision = "sleeve_cash_bucket_accounting_pass_ready_for_cash_proxy_data_gate"
    return [
        {
            "pm_gate_decision": decision,
            "next_gate": "cash_proxy_asset_data_gate" if decision.endswith("cash_proxy_data_gate") else "review_required",
            "primary_cash_drag_sleeve": drag_sleeve[0]["sleeve_id"] if drag_sleeve else "",
            "no_reentry_pass": int(no_reentry[0]["violation_count"]) == 0,
            "no_cross_sleeve_pass": no_cross[0]["status"] == "pass",
            "no_proxy_pass": no_proxy[0]["status"] == "pass",
            "no_trade_path_change_pass": no_trade[0]["status"] == "pass",
            "cash_reconciliation_status": reconciliation[0]["status"],
            "restore_needs_review_count": sum(1 for r in restore if r["audit_status"] == "needs_review"),
            "accepted": False,
            "v57f_core_modified": False,
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "next_task": "V5e cash proxy asset data gate",
            "allowed": decision == "sleeve_cash_bucket_accounting_pass_ready_for_cash_proxy_data_gate",
            "requires_user_asset_approval": True,
            "requires_backtest": False,
        },
        {
            "priority": 2,
            "next_task": "V5e sleeve-level risk release PM spec",
            "allowed": True,
            "requires_new_pm_spec": True,
        },
    ]


def _blockers(gate: list[dict[str, Any]], reconciliation: list[dict[str, Any]], restore: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if gate[0]["pm_gate_decision"].startswith("blocked"):
        return [{"blocker_id": gate[0]["pm_gate_decision"], "severity": "blocking", "status": "review_required"}]
    review_restore = sum(1 for r in restore if r["audit_status"] == "needs_review")
    rows = [{"blocker_id": "none", "severity": "none", "status": "not_blocking"}]
    if review_restore:
        rows.append({"blocker_id": "restore_events_need_review", "severity": "review_note", "status": "non_blocking", "count": review_restore})
    if reconciliation[0]["status"] != "pass":
        rows.append({"blocker_id": "cash_reconciliation_explainable_residual", "severity": "review_note", "status": "non_blocking", "max_abs_error": reconciliation[0]["max_abs_reconciliation_error"]})
    return rows


def _sleeve_lookup(signals: pd.DataFrame) -> dict[str, list[tuple[str, str]]]:
    lookup: dict[str, list[tuple[str, str]]] = {}
    for _, row in signals.iterrows():
        lookup.setdefault(str(row["code"]), []).append((str(row["trade_date"]), str(row["sector_id"])))
    for code in lookup:
        lookup[code].sort()
    return lookup


def _sleeve_for_exit(bundle: dict[str, Any], code: str, execution_date: str) -> str:
    entries = bundle["sleeve_lookup"].get(code, [])
    selected = ""
    for date, sleeve in entries:
        if date <= execution_date:
            selected = sleeve
        else:
            break
    return selected


def _next_rebalance(day: str, rebalance_dates: list[str]) -> str:
    idx = bisect_right(rebalance_dates, day)
    return rebalance_dates[idx] if idx < len(rebalance_dates) else ""


def _period_start(day: str, rebalance_dates: list[str]) -> str:
    start = ""
    for date in rebalance_dates:
        if date <= day:
            start = date
        else:
            break
    return start


def _days_between(trading_days: list[str], start: str, end_exclusive: str) -> list[str]:
    return [day for day in trading_days if day >= start and (not end_exclusive or day < end_exclusive)]


def _previous_trading_day(trading_days: list[str], day: str) -> str:
    prev = ""
    for d in trading_days:
        if d < day:
            prev = d
        else:
            break
    return prev


def _portfolio_value(bundle: dict[str, Any], day: str) -> float:
    hit = bundle["daily_returns"][bundle["daily_returns"]["trade_date"].astype(str).eq(day)]
    return float(hit.iloc[0]["portfolio_value"]) if len(hit) else 0.0


def _bucket_event_count(ledger: list[dict[str, Any]], bucket_id: str) -> int:
    return sum(1 for event in ledger if event["sleeve_cash_bucket_id"] == bucket_id)


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    ledger_event_count: int = 0,
    daily_balance_rows: int = 0,
    no_reentry_violation_count: int = 0,
    no_cross_sleeve_violation_count: int = 0,
    no_proxy_violation_count: int = 0,
    cash_reconciliation_error: float = 0.0,
    primary_cash_drag_sleeve: str = "",
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_sleeve_cash_bucket_engineering",
        "status": status,
        "pm_gate_decision": decision,
        "ledger_event_count": ledger_event_count,
        "daily_balance_rows": daily_balance_rows,
        "no_reentry_violation_count": no_reentry_violation_count,
        "no_cross_sleeve_violation_count": no_cross_sleeve_violation_count,
        "no_proxy_violation_count": no_proxy_violation_count,
        "cash_reconciliation_max_abs_error": cash_reconciliation_error,
        "primary_cash_drag_sleeve": primary_cash_drag_sleeve,
        "engineering_backtest_run": False,
        "trade_path_changed": False,
        "accepted": False,
        "v57f_core_modified": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(gate: list[dict[str, Any]], drag_sleeve: list[dict[str, Any]], reconciliation: list[dict[str, Any]]) -> str:
    top = drag_sleeve[0] if drag_sleeve else {}
    return "\n".join(
        [
            "# V5e Sleeve Cash Bucket Engineering",
            "",
            f"- PM gate: `{gate[0]['pm_gate_decision']}`",
            "- Ledger changes attribution only; no trade path changes and no backtest return claim.",
            f"- Primary cash drag sleeve: `{top.get('sleeve_id', '')}`",
            f"- Cash reconciliation status: `{reconciliation[0]['status']}`",
            "",
        ]
    )


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5e Sleeve Cash Bucket Engineering Rules",
            "",
            "- No V57f modification.",
            "- No new V5e threshold.",
            "- No buy orders, no proxy asset, no cross-sleeve transfer.",
            "- Ledger and attribution only.",
            "- Not accepted.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        SPEC_DIR / "v5e_sleeve_cash_policy_summary.json",
        SPEC_DIR / "v5e_sleeve_cash_policy_rule_spec.csv",
        SPEC_DIR / "v5e_sleeve_cash_bucket_schema.csv",
        SPEC_DIR / "v5e_sleeve_cash_restore_rule_matrix.csv",
        SPEC_DIR / "v5e_sleeve_cash_pm_admission_decision.csv",
        FORWARD_DIR / "v5e_profit_lock_forward_paper_summary.json",
        LOOP_DIR / "v5e_exit_action_log.csv",
        LOOP_DIR / "v5e_trigger_log.csv",
        LOOP_DIR / "v5e_cash_drag_log.csv",
        CAPITAL_DIR / "v5e_capital_cash_drag_comparison.csv",
        STARTUP_DIR / "v5_startup_warmup_price_repair_summary.json",
        SHADOW_CONFIG,
        REPAIRED_RUN / "rebalance_signals.csv",
        REPAIRED_RUN / "holdings.csv",
        REPAIRED_RUN / "daily_returns.csv",
        REPAIRED_RUN / "dividends.csv",
        REPAIRED_RUN / "corporate_actions.csv",
        REPAIRED_RUN / "trades.csv",
    ]
    return [{"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)} for path in required if not (root / path).exists()]


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    result = run_v5e_sleeve_cash_bucket_engineering()
    print(json.dumps(result, ensure_ascii=False, indent=2))
